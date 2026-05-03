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
#   make copr-stabilization           upload SRPM to hellaenergy/o3de-stabilization (testers)
#   make copr-snapshot                upload SRPM to hellaenergy/o3de-snapshot (one-off dev builds)
#   make copr-experimental            upload SRPM to hellaenergy/o3de-experimental
#   make copr-stable                  upload current stable SRPM to hellaenergy/o3de
#   make copr-stabilization-and-test  copr-stabilization + watch-build + trigger CI tests
#   make copr-snapshot-and-test       copr-snapshot + watch + trigger
#   make copr-experimental-and-test   copr-experimental + watch + trigger
#   make trigger-tests BUILD_ID=N     fire test-installed.yml against an existing COPR build
#                                     (default project: o3de-stabilization;
#                                      override with COPR_PROJECT=o3de-experimental etc.)
#   make clean                        rm -rf rpmbuild/{BUILD,BUILDROOT,RPMS,SRPMS} (NOT SOURCES)
#
# Variables:
#   REF=stabilization/26050              git ref for `make snapshot` (default)
#   COPR_OWNER=hellaenergy                COPR owner
#   COPR_PROJECT_STABLE=o3de                          tagged stable releases
#   COPR_PROJECT_STABILIZATION=o3de-stabilization     testers' channel; pre-release validation
#                                                     from upstream stabilization/<X> branch
#   COPR_PROJECT_SNAPSHOT=o3de-snapshot               one-off dev-branch / arbitrary-ref builds
#   COPR_PROJECT_EXPERIMENTAL=o3de-experimental       in-flight Stage 1 migration validation
#   COPR_PROJECT=$(COPR_PROJECT_STABILIZATION)        default project for trigger-tests
#
# All rpmbuild invocations point _sourcedir/_specdir at this checkout, so no
# files get copied into ~/rpmbuild/SOURCES/.

SHELL := /bin/bash
PWD   := $(shell pwd)

# Derive the RPM package name from the spec — single source of truth.
# Today this resolves to `o3de2605` (from `%global stable_tag 2605.0`);
# bump stable_tag to 2610.0 in the future and the same Make targets
# automatically build/test/upload `o3de2610` instead. Keeps SRPM/RPM
# glob patterns in sync with whatever the spec is currently pinned to.
PKGNAME := $(shell rpmspec --define "_sourcedir $(PWD)/sources" --define "_specdir $(PWD)" -q --qf '%{NAME}\n' o3de.spec 2>/dev/null | head -1)

# Default REF for `make snapshot` is the current next-release stabilization
# branch — that's what o3de-snapshot ships to community testers. Pass
# REF=development for the bleeding-edge integration branch, or any other
# git ref. Bump this default when O3DE moves to the next release branch
# (the spec's stable_tag value tells you the upcoming release version).
REF                          ?= stabilization/26050
COPR_OWNER                   ?= hellaenergy
COPR_PROJECT_STABLE          ?= o3de
COPR_PROJECT_STABILIZATION   ?= o3de-stabilization
COPR_PROJECT_SNAPSHOT        ?= o3de-snapshot
COPR_PROJECT_EXPERIMENTAL    ?= o3de-experimental
# COPR_PROJECT picks which project trigger-tests targets (defaults to
# the stabilization channel testers consume; override on the command line:
#     make trigger-tests BUILD_ID=N COPR_PROJECT=o3de-experimental
COPR_PROJECT                 ?= $(COPR_PROJECT_STABILIZATION)

RPMBUILD_DEFINES = \
	--define "_sourcedir $(PWD)/sources" \
	--define "_specdir   $(PWD)"

.PHONY: help lint spec-parse spec-parse-snapshot spec-parse-stabilization spec-parse-experimental \
        print-pkgname \
        snapshot srpm srpm-snapshot srpm-stabilization srpm-experimental \
        rpm rpm-snapshot rpm-debug rpm-snapshot-debug \
        copr-stable copr-snapshot copr-stabilization copr-experimental \
        copr-snapshot-and-test copr-stabilization-and-test copr-experimental-and-test _copr-and-test \
        trigger-tests copr-init \
        test test-setup test-full test-ui test-ui-full test-branch clean

help:
	@awk '/^# / { sub(/^# /,"",$$0); print } /^[a-z][a-z0-9_-]*:/ && $$0 !~ /^\./' Makefile | head -40

# ── Lint / parse ────────────────────────────────────────────────────────────

lint: spec-parse spec-parse-snapshot spec-parse-stabilization spec-parse-experimental
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

print-pkgname:
	@echo "$(PKGNAME)"

spec-parse:
	@rpmspec $(RPMBUILD_DEFINES) -q o3de.spec

spec-parse-snapshot:
	@rpmspec $(RPMBUILD_DEFINES) --define "_with_snapshot 1" -q o3de.spec

spec-parse-stabilization:
	@rpmspec $(RPMBUILD_DEFINES) --define "_with_snapshot 1" \
	    --define "_with_stabilization 1" -q o3de.spec

spec-parse-experimental:
	@rpmspec $(RPMBUILD_DEFINES) --define "_with_snapshot 1" \
	    --define "_with_stabilization 1" \
	    --define "_with_system_expat 1" \
	    --define "_with_system_freetype 1" \
	    --define "_with_system_mikkelsen 1" \
	    --define "_with_system_png 1" \
	    --define "_with_system_tiff 1" \
	    --define "_with_system_zlib 1" -q o3de.spec
# system_lua intentionally absent here — see SRPM_EXPERIMENTAL_FLAGS comment.

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

# srpm-stabilization: snapshot + the stabilization channel marker. This
# is what the community testers' channel ships. The marker is what
# differentiates "stabilization-branch build" (uploaded to o3de-stabilization)
# from a "one-off development-branch build" (uploaded to o3de-snapshot,
# plain --with snapshot only).
srpm-stabilization:
	rpmbuild -bs --with snapshot --with stabilization $(RPMBUILD_DEFINES) o3de.spec

# srpm-experimental: snapshot + every active Stage 1 system-library
# swap. Add new --with flags here as each migration is activated.
#
# IMPORTANT — the --with flags here only affect SRPM-build evaluation
# (which Sources/Patches make it into the .src.rpm); they do NOT
# propagate to COPR's binary build. For the bcond-gated BR/Requires/
# %prep/%build content to fire on COPR, the experimental project's
# chroots also need `--rpmbuild-with system_<lib>` set via
# `copr-cli edit-chroot`. See `make copr-init` for the one-time
# command. Keep the SRPM flags in sync with the chroot config so the
# SRPM faithfully shows what activations are intended even if a
# reviewer downloads the SRPM directly.
SRPM_EXPERIMENTAL_FLAGS = --with snapshot \
                          --with stabilization \
                          --with system_expat \
                          --with system_freetype \
                          --with system_mikkelsen \
                          --with system_png \
                          --with system_zlib
# system_tiff deferred: in addition to the deprecation-warning migration
# Patch0007 already addresses, libtiff's <tiff.h> conflicts with
# Code/Legacy/CryCommon/BaseTypes.h on the int64/uint64 typedef
# (libtiff: int64 → int64_t aka long; CryCommon: int64 → slonglong aka
# long long — same size, distinct C++ types → typedef redefinition error
# in any TU including both, surfaced by the Unity build merging multiple
# .cpp files). Real fix is migrating CryCommon's typedefs to the C99
# names, which is a foundational header change with audit cost across
# the engine. Park as a separate Stage 1 item.
#
# system_lua deferred: AzCore's ScriptContext.cpp #includes Lua's internal
# <Lua/lobject.h> which Fedora's lua-devel doesn't ship (only public API:
# lua.h, lauxlib.h, lualib.h, luaconf.h). Activating system_lua needs a
# carry-patch that replaces lobject.h usage with the public API, or a
# different way to expose Lua's internal type definitions. Bcond + find
# shim + Source declaration stay in place for future activation.

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
	@echo "# 2. Stabilization (community-tester) project — pre-release validation"
	@echo "#    builds from upstream's stabilization/<release> branch:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_STABILIZATION) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on --appstream on \\"
	@echo "      --description 'O3DE pre-release validation builds from stabilization/<release>'"
	@echo
	@echo "# 3. Snapshot (one-off / development-branch) project — ad-hoc cadence,"
	@echo "#    used when someone wants to build from upstream development or a"
	@echo "#    specific commit without disrupting the regular tester channel:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on \\"
	@echo "      --description 'O3DE one-off development-branch builds'"
	@echo
	@echo "# 4. Experimental (in-flight migration) project:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on \\"
	@echo "      --description 'O3DE experimental builds — Stage 1 migration work'"
	@echo
	@echo "# Wire o3de-dependencies into each chroot for all four engine projects:"
	@echo "  for proj in $(COPR_PROJECT_STABLE) $(COPR_PROJECT_STABILIZATION) $(COPR_PROJECT_SNAPSHOT) $(COPR_PROJECT_EXPERIMENTAL); do \\"
	@echo "      for chroot in fedora-44-x86_64 fedora-rawhide-x86_64; do \\"
	@echo "          copr-cli edit-chroot $(COPR_OWNER)/\$$proj/\$$chroot \\"
	@echo "              --repos 'copr://$(COPR_OWNER)/o3de-dependencies'; \\"
	@echo "      done; \\"
	@echo "  done"
	@echo
	@echo "# 5. Per-chroot --rpmbuild-with flags. copr-cli's --with at SRPM-build"
	@echo "# time does NOT propagate to its binary-build (where bcond_with fires),"
	@echo "# so each channel-specific bcond is set on the relevant chroots instead."
	@echo "# Three groups of flags:"
	@echo
	@echo "#    a. Stabilization-channel marker on o3de-stabilization chroots"
	@echo "#       (drives the GUI '-stabilization.<commit>' channel suffix):"
	@echo "  for chroot in fedora-44-x86_64 fedora-rawhide-x86_64; do \\"
	@echo "      copr-cli edit-chroot $(COPR_OWNER)/$(COPR_PROJECT_STABILIZATION)/\$$chroot \\"
	@echo "          --rpmbuild-with stabilization; \\"
	@echo "  done"
	@echo
	@echo "#    b. Stage 1 system-library swaps + stabilization marker on"
	@echo "#       o3de-experimental chroots. Add per migration as the list grows:"
	@echo "  for chroot in fedora-44-x86_64 fedora-rawhide-x86_64; do \\"
	@echo "      copr-cli edit-chroot $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL)/\$$chroot \\"
	@echo "          --rpmbuild-with stabilization \\"
	@echo "          --rpmbuild-with system_expat \\"
	@echo "          --rpmbuild-with system_freetype \\"
	@echo "          --rpmbuild-with system_mikkelsen \\"
	@echo "          --rpmbuild-with system_png \\"
	@echo "          --rpmbuild-with system_tiff \\"
	@echo "          --rpmbuild-with system_zlib; \\"
	@echo "  done"
	@echo "#       (system_lua deferred — depends on a carry-patch that replaces"
	@echo "#        AzCore ScriptContext.cpp's use of <Lua/lobject.h> with the"
	@echo "#        public API. Add system_lua back when the patch lands.)"
	@echo
	@echo "#    c. o3de-snapshot stays unflagged. Plain --with snapshot at the"
	@echo "#       SRPM level marks the build as a one-off dev-branch snapshot;"
	@echo "#       no chroot --rpmbuild-with needed."
	@echo
	@echo "# After a Stage 1 batch validates on o3de-experimental and is approved"
	@echo "# to ship to testers, mirror the SAME --rpmbuild-with system_<lib>"
	@echo "# flags onto the o3de-stabilization chroots. And whenever the o3de"
	@echo "# (stable) project ships its first migrated build, the SAME flags"
	@echo "# need to land there too — otherwise stable RPMs default the bconds"
	@echo "# off and ship the bundled libraries instead of the system ones,"
	@echo "# even though the spec carries the gates. Same goes for any future"
	@echo "# epel-10 chroot (already in stable's chroot list above). Rules:"
	@echo "#   - Every engine project that ships migrations needs every"
	@echo "#     --rpmbuild-with flag for those migrations on every chroot."
	@echo "#   - When a new migration activates (new system_<lib> bcond),"
	@echo "#     run the chroot edit on every shipping project, not just"
	@echo "#     experimental."
	@echo "#   - When a new chroot joins the matrix (e.g., fedora-45 ships),"
	@echo "#     copy the --rpmbuild-with flag set onto the new chroot."
	@echo "#   - The 'stabilization' bcond stays on o3de-stabilization +"
	@echo "#     o3de-experimental chroots only; o3de (stable) and"
	@echo "#     o3de-snapshot do NOT get it."
	@echo
	@echo "# 6. Auto-enable o3de-dependencies for end users. Without this,"
	@echo "# 'dnf copr enable hellaenergy/<engine-project>' alone leaves users"
	@echo "# unable to resolve Requires:mikkelsen and similar swapped deps."
	@echo "# Apply to every engine project:"
	@echo "  for proj in $(COPR_PROJECT_STABLE) $(COPR_PROJECT_STABILIZATION) $(COPR_PROJECT_SNAPSHOT) $(COPR_PROJECT_EXPERIMENTAL); do \\"
	@echo "      copr-cli modify $(COPR_OWNER)/\$$proj \\"
	@echo "          --runtime-repo-dependency 'copr://$(COPR_OWNER)/o3de-dependencies'; \\"
	@echo "  done"
	@echo
	@echo "# 6. User-facing project metadata (homepage / contact / instructions)."
	@echo "# These show on the COPR project's Overview tab and are how testers"
	@echo "# learn what the project is and where to file issues. Keep current"
	@echo "# as project audience and currently-active features evolve."
	@echo "# copr-cli supports --description and --instructions; --homepage"
	@echo "# and --contact need the API directly (see CONTRIBUTING.md)."

copr-stable: srpm
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

copr-snapshot: srpm-snapshot
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_SNAPSHOT) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# copr-stabilization: the regular community-tester channel. This is the
# project the test-installed.yml cron polls for new builds.
copr-stabilization: srpm-stabilization
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_STABILIZATION) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# Parallel project for in-flight migration / structural work that isn't
# ready to expose to o3de-stabilization's community testers. Same chroots
# and same enable_net + o3de-dependencies repo wiring as the stabilization
# project; different audience: only us until a change is validated.
copr-experimental: srpm-experimental
	copr-cli build --timeout 25200 $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

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

copr-stabilization-and-test: srpm-stabilization
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_STABILIZATION)

copr-experimental-and-test: srpm-experimental
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_EXPERIMENTAL)

# Internal helper: parameterized build-then-watch-then-trigger-tests.
# Not a normal entry point; called from copr-{snapshot,experimental}-and-test.
_copr-and-test:
	@[ -n "$(COPR_TARGET)" ] || { echo "_copr-and-test requires COPR_TARGET="; exit 2; }
	@set -e ; \
	build_output=$$(copr-cli build --timeout 25200 \
	    $(COPR_OWNER)/$(COPR_TARGET) \
	    ~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm) ; \
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
	rpm_rel=$$(curl -fsSL "$$repo/$$primary" | gunzip -c | grep -oE 'href="Packages/o/o3de[0-9]+-[^"]+\.x86_64\.rpm"' | grep -v -- '-debug-' | head -1 | sed 's/^href="//; s/"$$//') ; \
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
	rm -rf ~/rpmbuild/BUILD ~/rpmbuild/BUILDROOT ~/rpmbuild/RPMS/x86_64/$(PKGNAME)-* ~/rpmbuild/SRPMS/$(PKGNAME)-*
