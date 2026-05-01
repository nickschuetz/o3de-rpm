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
        copr-stable copr-snapshot copr-init \
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
