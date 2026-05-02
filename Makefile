# o3de-rpm — build / lint / distribute
#
# Common targets:
#   make lint                         rpmlint + desktop + metainfo + spec parse
#   make srpm                         build SRPM (stable mode)
#   make srpm-snapshot                build SRPM (snapshot mode)
#   make snapshot REF=<git-ref>       fetch+build snapshot tarball, paste pins yourself
#   make rpm                          full -bb (stable, profile only — main package)
#   make rpm-snapshot                 full -bb (snapshot, profile only)
#   make rpm-debug                    full -bb (stable) + o3de-debug subpackage
#   make rpm-snapshot-debug           full -bb (snapshot) + o3de-debug subpackage
#   make copr-snapshot                upload current snapshot SRPM to hellaenergy/o3de-snapshot
#   make copr-stable                  upload current stable SRPM to hellaenergy/o3de
#   make copr-snapshot-and-test       copr-snapshot + watch-build + trigger CI tests on success
#   make trigger-tests BUILD_ID=N     fire test-installed.yml against an existing COPR build
#   make clean                        rm -rf rpmbuild/{BUILD,BUILDROOT,RPMS,SRPMS} (NOT SOURCES)
#
# Variables:
#   REF=stabilization/26050           git ref for `make snapshot`
#   COPR_OWNER=hellaenergy             COPR owner
#   COPR_PROJECT_STABLE=o3de           project name for stable builds
#   COPR_PROJECT_SNAPSHOT=o3de-snapshot
#
# All rpmbuild invocations point _sourcedir/_specdir at this checkout, so no
# files get copied into ~/rpmbuild/SOURCES/.

SHELL := /bin/bash
PWD   := $(shell pwd)

REF                   ?= development
COPR_OWNER            ?= hellaenergy
COPR_PROJECT_STABLE   ?= o3de
COPR_PROJECT_SNAPSHOT ?= o3de-snapshot

RPMBUILD_DEFINES = \
	--define "_sourcedir $(PWD)/sources" \
	--define "_specdir   $(PWD)"

.PHONY: help lint spec-parse spec-parse-snapshot \
        snapshot srpm srpm-snapshot rpm rpm-snapshot rpm-debug rpm-snapshot-debug \
        copr-stable copr-snapshot copr-snapshot-and-test trigger-tests copr-init \
        test test-setup test-full test-ui test-ui-full test-branch clean

help:
	@awk '/^# / { sub(/^# /,"",$$0); print } /^[a-z][a-z0-9_-]*:/ && $$0 !~ /^\./' Makefile | head -40

# ── Lint / parse ────────────────────────────────────────────────────────────

lint: spec-parse spec-parse-snapshot
	@echo ">> rpmlint o3de.spec"
	@rpmlint o3de.spec
	@echo ">> desktop-file-validate"
	@desktop-file-validate sources/o3de.desktop
	@echo ">> appstream-util validate"
	@appstream-util validate-relax --nonet sources/o3de.metainfo.xml
	@echo ">> bash -n on shell sources"
	@for f in sources/*.sh; do bash -n "$$f" && echo "    $$f OK"; done
	@echo "All lints passed."

spec-parse:
	@rpmspec $(RPMBUILD_DEFINES) -q o3de.spec

spec-parse-snapshot:
	@rpmspec $(RPMBUILD_DEFINES) --define "_with_snapshot 1" -q o3de.spec

# ── Snapshot tarball ────────────────────────────────────────────────────────

snapshot:
	cd sources && ./make-snapshot-tarball.sh "$(REF)"
	@echo
	@echo ">> Paste the printed snapshot_commit / snapshot_date / snapshot_sha256"
	@echo ">> values into o3de.spec, then run 'make srpm-snapshot' or 'make rpm-snapshot'."

# ── SRPM builds ─────────────────────────────────────────────────────────────

srpm:
	rpmbuild -bs $(RPMBUILD_DEFINES) o3de.spec

srpm-snapshot:
	rpmbuild -bs --with snapshot $(RPMBUILD_DEFINES) o3de.spec

# ── RPM builds ──────────────────────────────────────────────────────────────
# Default: profile-config only (one RPM, ~70 min on a 32GB workstation).
# `*-debug` variants additionally build the debug-config binaries and emit
# the o3de-debug subpackage — roughly doubles build time and disk.

rpm:
	rpmbuild -bb $(RPMBUILD_DEFINES) o3de.spec

rpm-snapshot:
	rpmbuild -bb --with snapshot $(RPMBUILD_DEFINES) o3de.spec

rpm-debug:
	rpmbuild -bb --with debug $(RPMBUILD_DEFINES) o3de.spec

rpm-snapshot-debug:
	rpmbuild -bb --with snapshot --with debug $(RPMBUILD_DEFINES) o3de.spec

# ── COPR upload ─────────────────────────────────────────────────────────────
# Requires `copr-cli` configured (~/.config/copr) with API token.
# The o3de project on COPR must have enable_net=true (so cmake can fetch
# O3DE's CDN packages at configure time). The o3de-dependencies project
# stays enable_net=false — Fedora-clean.

copr-init:
	@echo "Run these once per COPR project:"
	@echo
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --chroot epel-10-x86_64 \\"
	@echo "      --enable-net true --appstream true --description 'Open 3D Engine'"
	@echo
	@echo "  copr-cli edit-chroot $(COPR_OWNER)/$(COPR_PROJECT_STABLE)/fedora-44-x86_64 \\"
	@echo "      --repos 'copr://$(COPR_OWNER)/o3de-dependencies'"

copr-stable: srpm
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

copr-snapshot: srpm-snapshot
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

# 25200s = 7 hr. Default COPR project timeout is 5 hr; F44 chroot ate
# ~4 hr in build 10414894 (which completed all 2173 compile steps), so
# rawhide — typically 10-30% slower than F44 — would risk timeout.

# Submit to COPR, watch until completion, fire a repository_dispatch
# event at the GitHub Actions test-installed.yml workflow on success.
# Requires `gh` CLI authenticated for repo write access. The workflow
# resolves the F44 RPM URL from the build_id by listing the COPR
# results directory, so we only need to pass the build_id along.
copr-snapshot-and-test: srpm-snapshot
	@set -e ; \
	build_output=$$(copr-cli build --timeout 25200 \
	    $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \
	    ~/rpmbuild/SRPMS/o3de-*.src.rpm) ; \
	echo "$$build_output" ; \
	build_id=$$(echo "$$build_output" | grep -oE 'Created builds: [0-9]+' \
	    | tail -1 | awk '{print $$3}') ; \
	if [ -z "$$build_id" ]; then \
	    echo "ERROR: could not parse build_id from copr-cli output" ; exit 1 ; \
	fi ; \
	echo ">> Watching COPR build $$build_id (likely 4-5 hours)" ; \
	copr-cli watch-build "$$build_id" ; \
	$(MAKE) trigger-tests BUILD_ID=$$build_id

# Fire the repository_dispatch event for the latest succeeded COPR
# build. Useful for kicking off tests against the most recent build,
# e.g.  `make trigger-tests BUILD_ID=10415468` (the BUILD_ID is just a
# label for the dedup cache and run banner — the RPM URL is resolved
# from repodata, which always points at the latest build).
#
# COPR no longer hosts the per-build directory's RPMs directly: that
# dir holds logs only after rsync moves the artifacts into the
# createrepo-managed Packages/o/ tree at the repo root. So we resolve
# the RPM URL via the F44 repo metadata.
GITHUB_REPO ?= nickschuetz/o3de-rpm
trigger-tests:
	@[ -n "$(BUILD_ID)" ] || { echo "usage: make trigger-tests BUILD_ID=<copr-build-id>"; exit 2; }
	@repo="https://download.copr.fedorainfracloud.org/results/$(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT)/fedora-44-x86_64" ; \
	primary=$$(curl -fsSL "$$repo/repodata/repomd.xml" | grep -oE 'repodata/[a-f0-9]+-primary\.xml\.gz' | head -1) ; \
	rpm_rel=$$(curl -fsSL "$$repo/$$primary" | gunzip -c | grep -oE 'href="Packages/o/o3de-[^"]+\.x86_64\.rpm"' | grep -v -- '-debug-' | head -1 | sed 's/^href="//; s/"$$//') ; \
	if [ -z "$$rpm_rel" ]; then \
	    echo "ERROR: no F44 o3de RPM in repodata at $$repo" ; exit 1 ; \
	fi ; \
	rpm_url="$${repo}/$${rpm_rel}" ; \
	echo ">> Triggering test-installed.yml for $$rpm_url" ; \
	gh api -X POST repos/$(GITHUB_REPO)/dispatches \
	    -f event_type=copr-build-succeeded \
	    -F client_payload[rpm_url]="$$rpm_url" \
	    -F client_payload[build_id]="$(BUILD_ID)"

# ── Tests against an installed RPM ──────────────────────────────────────────
# Tier 1+2+4: read-only checks. Tier 3 (--setup) modifies ~/.o3de.
# Tier 5 (--with-project) builds a sample project. See tests/README.md.

test:
	tests/integration-test.sh

test-setup:
	tests/integration-test.sh --setup

test-full:
	tests/integration-test.sh --setup --with-project

# UI smoke (Tier 6): Project Manager launches under Xvfb without crashing.
# Add --editor (test-ui-full) to also run Editor scripted automation.
test-ui:
	tests/ui-smoke-test.sh --screenshot

test-ui-full:
	tests/ui-smoke-test.sh --screenshot --editor

# End-to-end driver: build a snapshot RPM from <REF> and test it.
# Usage: make test-branch REF=stabilization/26050
test-branch:
	@[ -n "$(REF)" ] || { echo "usage: make test-branch REF=<git-ref>"; exit 2; }
	tests/test-branch.sh $(REF)

# ── Clean ───────────────────────────────────────────────────────────────────

clean:
	rm -rf ~/rpmbuild/BUILD ~/rpmbuild/BUILDROOT ~/rpmbuild/RPMS/x86_64/o3de-* ~/rpmbuild/SRPMS/o3de-*
