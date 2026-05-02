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
#   make copr-experimental            upload current snapshot SRPM to hellaenergy/o3de-experimental
#   make copr-stable                  upload current stable SRPM to hellaenergy/o3de
#   make copr-snapshot-and-test       copr-snapshot + watch-build + trigger CI tests on success
#   make copr-experimental-and-test   copr-experimental + watch-build + trigger CI tests
#   make trigger-tests BUILD_ID=N     fire test-installed.yml against an existing COPR build
#                                     (override target with COPR_PROJECT=o3de-experimental)
#   make clean                        rm -rf rpmbuild/{BUILD,BUILDROOT,RPMS,SRPMS} (NOT SOURCES)
#
# Variables:
#   REF=stabilization/26050              git ref for `make snapshot`
#   COPR_OWNER=hellaenergy                COPR owner
#   COPR_PROJECT_STABLE=o3de              project for tagged stable builds
#   COPR_PROJECT_SNAPSHOT=o3de-snapshot   community testers' channel — hands off mid-window
#   COPR_PROJECT_EXPERIMENTAL=o3de-experimental    in-flight migration / structural work
#   COPR_PROJECT=$(COPR_PROJECT_SNAPSHOT) which project trigger-tests targets
#
# All rpmbuild invocations point _sourcedir/_specdir at this checkout, so no
# files get copied into ~/rpmbuild/SOURCES/.

SHELL := /bin/bash
PWD   := $(shell pwd)

REF                       ?= development
COPR_OWNER                ?= hellaenergy
COPR_PROJECT_STABLE       ?= o3de
COPR_PROJECT_SNAPSHOT     ?= o3de-snapshot
COPR_PROJECT_EXPERIMENTAL ?= o3de-experimental
# COPR_PROJECT picks which project trigger-tests targets (defaults to
# the snapshot channel testers consume; override on the command line:
#     make trigger-tests BUILD_ID=N COPR_PROJECT=o3de-experimental
COPR_PROJECT              ?= $(COPR_PROJECT_SNAPSHOT)

RPMBUILD_DEFINES = \
	--define "_sourcedir $(PWD)/sources" \
	--define "_specdir   $(PWD)"

.PHONY: help lint spec-parse spec-parse-snapshot spec-parse-experimental \
        snapshot srpm srpm-snapshot srpm-experimental \
        rpm rpm-snapshot rpm-debug rpm-snapshot-debug \
        copr-stable copr-snapshot copr-experimental \
        copr-snapshot-and-test copr-experimental-and-test _copr-and-test \
        trigger-tests copr-init \
        test test-setup test-full test-ui test-ui-full test-branch clean

help:
	@awk '/^# / { sub(/^# /,"",$$0); print } /^[a-z][a-z0-9_-]*:/ && $$0 !~ /^\./' Makefile | head -40

# ── Lint / parse ────────────────────────────────────────────────────────────

lint: spec-parse spec-parse-snapshot spec-parse-experimental
	@echo ">> rpmlint o3de.spec"
	@rpmlint o3de.spec
	@echo ">> desktop-file-validate"
	@desktop-file-validate sources/o3de.desktop
	@echo ">> appstream-util validate"
	@appstream-util validate-relax --nonet sources/o3de.metainfo.xml
	@echo ">> bash -n on shell sources"
	@# Pick up *.sh + extensionless scripts (e.g. /usr/bin/o3de-cli).
	@for f in sources/*.sh $$(file sources/* 2>/dev/null | grep -l 'shell script' 2>/dev/null; \
	                          for x in sources/*; do [ -f "$$x" ] && head -1 "$$x" 2>/dev/null \
	                                | grep -q '^#!.*\(bash\|sh\)' && [ "$${x%.sh}" = "$$x" ] && echo "$$x"; done); do \
	    [ -f "$$f" ] && bash -n "$$f" && echo "    $$f OK"; \
	done | sort -u
	@echo "All lints passed."

spec-parse:
	@rpmspec $(RPMBUILD_DEFINES) -q o3de.spec

spec-parse-snapshot:
	@rpmspec $(RPMBUILD_DEFINES) --define "_with_snapshot 1" -q o3de.spec

spec-parse-experimental:
	@rpmspec $(RPMBUILD_DEFINES) --define "_with_snapshot 1" \
	    --define "_with_system_mikkelsen 1" -q o3de.spec

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

# srpm-experimental: snapshot + every active Stage 1 system-library
# swap. Add new --with flags here as each migration is activated. The
# experimental COPR project consumes these SRPMs.
SRPM_EXPERIMENTAL_FLAGS = --with snapshot --with system_mikkelsen

srpm-experimental:
	rpmbuild -bs $(SRPM_EXPERIMENTAL_FLAGS) $(RPMBUILD_DEFINES) o3de.spec

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
	@echo "Run these once per COPR project (note: copr-cli takes 'on'/'off',"
	@echo "not 'true'/'false', for boolean flags as of copr-cli 2.x):"
	@echo
	@echo "# 1. Stable (tagged-release) project:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --chroot epel-10-x86_64 \\"
	@echo "      --enable-net on --appstream on \\"
	@echo "      --description 'Open 3D Engine — tagged stable releases'"
	@echo
	@echo "# 2. Snapshot (community-tester) project:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on --appstream on \\"
	@echo "      --description 'O3DE development snapshot for community testers'"
	@echo
	@echo "# 3. Experimental (in-flight migration) project:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on \\"
	@echo "      --description 'O3DE experimental builds — Stage 1 migration work'"
	@echo
	@echo "# Wire o3de-dependencies into each chroot for all three engine projects:"
	@echo "  for proj in $(COPR_PROJECT_STABLE) $(COPR_PROJECT_SNAPSHOT) $(COPR_PROJECT_EXPERIMENTAL); do \\"
	@echo "      for chroot in fedora-44-x86_64 fedora-rawhide-x86_64; do \\"
	@echo "          copr-cli edit-chroot $(COPR_OWNER)/\$$proj/\$$chroot \\"
	@echo "              --repos 'copr://$(COPR_OWNER)/o3de-dependencies'; \\"
	@echo "      done; \\"
	@echo "  done"

copr-stable: srpm
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

copr-snapshot: srpm-snapshot
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

# Parallel project for in-flight migration / structural work that isn't
# ready to expose to o3de-snapshot's community testers. Same chroots and
# same enable_net + o3de-dependencies repo wiring as the snapshot project,
# different audience: only us until a change is validated.
copr-experimental: srpm-experimental
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

# 25200s = 7 hr. Default COPR project timeout is 5 hr; F44 chroot ate
# ~4 hr in build 10414894 (which completed all 2173 compile steps), so
# rawhide — typically 10-30% slower than F44 — would risk timeout.

# Submit to COPR, watch until completion, fire a repository_dispatch
# event at the GitHub Actions test-installed.yml workflow on success.
# Requires `gh` CLI authenticated for repo write access. The workflow
# resolves the F44 RPM URL from the build_id by listing the COPR
# results directory, so we only need to pass the build_id along.
#
# Default targets the snapshot project. To exercise the experimental
# project end-to-end, use `make copr-experimental-and-test` instead.
copr-snapshot-and-test: srpm-snapshot
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_SNAPSHOT)

copr-experimental-and-test: srpm-experimental
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_EXPERIMENTAL)

# Internal helper: parameterized build-then-watch-then-trigger-tests.
# Not a normal entry point; called from copr-{snapshot,experimental}-and-test.
_copr-and-test:
	@[ -n "$(COPR_TARGET)" ] || { echo "_copr-and-test requires COPR_TARGET="; exit 2; }
	@set -e ; \
	build_output=$$(copr-cli build --timeout 25200 \
	    $(COPR_OWNER)/$(COPR_TARGET) \
	    ~/rpmbuild/SRPMS/o3de-*.src.rpm) ; \
	echo "$$build_output" ; \
	build_id=$$(echo "$$build_output" | grep -oE 'Created builds: [0-9]+' \
	    | tail -1 | awk '{print $$3}') ; \
	if [ -z "$$build_id" ]; then \
	    echo "ERROR: could not parse build_id from copr-cli output" ; exit 1 ; \
	fi ; \
	echo ">> Watching COPR build $$build_id (likely 4-5 hours)" ; \
	copr-cli watch-build "$$build_id" ; \
	$(MAKE) trigger-tests BUILD_ID=$$build_id COPR_PROJECT=$(COPR_TARGET)

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
	@[ -n "$(BUILD_ID)" ] || { echo "usage: make trigger-tests BUILD_ID=<copr-build-id> [COPR_PROJECT=<project>]"; exit 2; }
	@repo="https://download.copr.fedorainfracloud.org/results/$(COPR_OWNER)/$(COPR_PROJECT)/fedora-44-x86_64" ; \
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
