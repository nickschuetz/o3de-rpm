# o3de-rpm — build / lint / distribute
#
# Common targets:
#   make lint                         rpmlint + desktop + metainfo + spec parse
#   make srpm                         build SRPM (stable mode, expects o3de_<TAG>_lfs.tar.gz in sources/)
#   make srpm-snapshot                build SRPM (snapshot mode)
#   make snapshot REF=<git-ref>       fetch+build snapshot tarball, paste pins yourself
#   make rpm                          full -bb (stable), debug_only (skips profile config)
#   make rpm-snapshot                 full -bb (snapshot), debug_only
#   make rpm-full                     full -bb (stable), debug+profile (the default ship config)
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
        snapshot srpm srpm-snapshot rpm rpm-snapshot rpm-full \
        copr-stable copr-snapshot copr-init clean

help:
	@awk '/^# / { sub(/^# /,"",$$0); print } /^[a-z][a-z0-9_-]*:/ && $$0 !~ /^\./' Makefile | head -40

# ── Lint / parse ────────────────────────────────────────────────────────────

lint: spec-parse spec-parse-snapshot
	@echo ">> rpmlint o3de.spec"
	@rpmlint o3de.spec
	@echo ">> desktop-file-validate"
	@desktop-file-validate sources/o3de-editor.desktop
	@echo ">> appstream-util validate"
	@appstream-util validate-relax --nonet sources/o3de-editor.metainfo.xml
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

rpm:
	rpmbuild -bb --with debug_only $(RPMBUILD_DEFINES) o3de.spec

rpm-snapshot:
	rpmbuild -bb --with snapshot --with debug_only $(RPMBUILD_DEFINES) o3de.spec

rpm-full:
	rpmbuild -bb $(RPMBUILD_DEFINES) o3de.spec

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
	copr-cli build $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

copr-snapshot: srpm-snapshot
	copr-cli build $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \
		~/rpmbuild/SRPMS/o3de-*.src.rpm

# ── Clean ───────────────────────────────────────────────────────────────────

clean:
	rm -rf ~/rpmbuild/BUILD ~/rpmbuild/BUILDROOT ~/rpmbuild/RPMS/x86_64/o3de-* ~/rpmbuild/SRPMS/o3de-*
