# o3de-rpm — build / lint / distribute
#
# Common targets:
#   make lint                         rpmlint + desktop + metainfo + spec parse
#   make srpm                         build SRPM (stable mode)
#   make srpm-snapshot                build SRPM (snapshot mode; uses spec's pinned commit)
#   make snapshot REF=<git-ref>       fetch+build snapshot tarball, paste pins yourself
#   make srpm-snapshot-ref REF=<ref>  fetch tarball from ref + build SRPM in one step
#                                     (no spec edits; uses --define overrides). Default REF=development
#   make srpm-snapshot-qt6            convenience alias: srpm-snapshot-ref REF=qt6
#   make srpm-snapshot-development    convenience alias: srpm-snapshot-ref REF=development
#   make rpm                          full -bb (stable, profile only — main package)
#   make rpm-snapshot                 full -bb (snapshot, profile only)
#   make rpm-debug                    full -bb (stable) + o3de-debug subpackage
#   make rpm-snapshot-debug           full -bb (snapshot) + o3de-debug subpackage
#   make copr-stabilization           upload SRPM to hellaenergy/o3de-stabilization (testers)
#   make copr-development             upload SRPM to hellaenergy/o3de-development (always dev branch)
#   make copr-experimental            upload SRPM to hellaenergy/o3de-experimental
#   make copr-stable                  upload current stable SRPM to hellaenergy/o3de
#   make copr-stabilization-and-test  copr-stabilization + watch-build + trigger CI tests
#   make copr-development-and-test    copr-development + watch + trigger
#   make copr-experimental-and-test   copr-experimental + watch + trigger
#   make trigger-tests BUILD_ID=N     fire test-installed.yml against an existing COPR build
#                                     (default project: o3de-stabilization;
#                                      override with COPR_PROJECT=o3de-experimental etc.)
#   make clean                        rm -rf rpmbuild/{BUILD,BUILDROOT,RPMS,SRPMS} (NOT SOURCES)
#
# Variables:
#   REF=stabilization/26100              git ref for `make snapshot` (default)
#   COPR_OWNER=hellaenergy                COPR owner
#   COPR_PROJECT_STABLE=o3de                          tagged stable releases
#   COPR_PROJECT_STABILIZATION=o3de-stabilization     testers' channel; pre-release validation
#                                                     from upstream stabilization/<X> branch
#   COPR_PROJECT_DEVELOPMENT=o3de-development         builds from upstream development branch
#                                                     (rare other-ref builds get a dedicated COPR
#                                                     project, e.g. o3de-qt6)
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
# branch — that's what `make snapshot` regenerates the spec's snapshot pin
# against. The o3de-development channel always targets the development
# branch (via `make copr-development`, which calls srpm-snapshot-development
# explicitly). For ad-hoc other-ref builds (e.g. qt6), create a dedicated
# COPR project and fire srpm-snapshot-ref REF=<other> at it via copr-cli.
REF                          ?= stabilization/26100
COPR_OWNER                   ?= hellaenergy
COPR_PROJECT_STABLE          ?= o3de
COPR_PROJECT_TESTING         ?= o3de-testing
COPR_PROJECT_STABILIZATION   ?= o3de-stabilization
COPR_PROJECT_DEVELOPMENT     ?= o3de-development
COPR_PROJECT_EXPERIMENTAL    ?= o3de-experimental
# Debug-config sibling channels. Each mirrors its namesake's with_opts
# (set on the chroots) PLUS the `debug` bcond, so the build emits the
# o3de2605-debug subpackage (-O0 + full symbols) for tester crash
# reports. The -debug subpackage hard-Requires the EXACT NVR of the
# main package (Requires: %{name}%{?_isa} = %{version}-%{release}), so a
# debug channel MUST be refreshed from the same SRPM / NVR as its
# sibling or `dnf install o3de2605-debug` breaks. AppStream is off on
# these so the duplicate main package doesn't show as a second app.
COPR_PROJECT_TESTING_DEBUG       ?= o3de-testing-debug
COPR_PROJECT_DEVELOPMENT_DEBUG   ?= o3de-development-debug
# COPR_PROJECT picks which project trigger-tests targets (defaults to
# the stabilization channel testers consume; override on the command line:
#     make trigger-tests BUILD_ID=N COPR_PROJECT=o3de-experimental
COPR_PROJECT                 ?= $(COPR_PROJECT_STABILIZATION)

RPMBUILD_DEFINES = \
	--define "_sourcedir $(PWD)/sources" \
	--define "_specdir   $(PWD)"

.PHONY: help lint spec-parse spec-parse-snapshot spec-parse-stabilization spec-parse-experimental spec-parse-development \
        print-pkgname \
        snapshot srpm srpm-snapshot srpm-snapshot-ref srpm-snapshot-qt6 srpm-snapshot-development \
        srpm-stabilization srpm-experimental \
        rpm rpm-snapshot rpm-debug rpm-snapshot-debug rpm-experimental rpm-local-development \
        copr-stable copr-development copr-stabilization copr-experimental \
        copr-testing copr-testing-debug copr-development-debug \
        copr-development-and-test copr-stabilization-and-test copr-experimental-and-test _copr-and-test \
        trigger-tests copr-init \
        copr-metadata-pull copr-metadata-diff copr-metadata-push \
        check-deps-drift check-qt6-merge qt6-merge-gate \
        test test-setup test-full test-ui test-ui-full test-asset-bake test-ap-spawn test-multiplayer-sample test-newspaper-delivery test-branch clean

help:
	@awk '/^# / { sub(/^# /,"",$$0); print } /^[a-z][a-z0-9_-]*:/ && $$0 !~ /^\./' Makefile | head -40

# ── Lint / parse ────────────────────────────────────────────────────────────

lint: spec-parse spec-parse-snapshot spec-parse-stabilization spec-parse-experimental
	@echo ">> rpmlint o3de.spec (changelog inlined via textual splice; tracked spec keeps %include)"
	@TMPDIR=$$(mktemp -d /tmp/o3de.lint.XXXXXX); \
	  awk '/^%include %{SOURCE99}$$/{ while ((getline l < "sources/o3de.changelog") > 0) print l; next } {print}' o3de.spec > $$TMPDIR/o3de.spec; \
	  cp .rpmlintrc $$TMPDIR/ 2>/dev/null || true; \
	  ( cd $$TMPDIR && rpmlint o3de.spec ); \
	  RC=$$?; rm -rf $$TMPDIR; exit $$RC
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
	    --define "_with_system_assimp 1" \
	    --define "_with_system_cityhash 1" \
	    --define "_with_system_dxc 1" \
	    --define "_with_system_expat 1" \
	    --define "_with_system_freetype 1" \
	    --define "_with_system_googlebenchmark 1" \
	    --define "_with_system_libsamplerate 1" \
	    --define "_with_system_lua 1" \
	    --define "_with_system_mcpp 1" \
	    --define "_with_system_mikkelsen 1" \
	    --define "_with_system_png 1" \
	    --define "_with_system_poly2tri 1" \
	    --define "_with_system_rapidjson 1" \
	    --define "_with_system_spirvcross 1" \
	    --define "_with_system_sqlite 1" \
	    --define "_with_system_tiff 1" \
	    --define "_with_system_xxhash 1" \
	    --define "_with_system_zlib 1" -q o3de.spec

# ── Snapshot tarball ────────────────────────────────────────────────────────

snapshot:
	cd sources && ./make-snapshot-tarball.sh "$(REF)"
	@echo
	@echo ">> Paste the printed snapshot_commit / snapshot_date / snapshot_sha256"
	@echo ">> values into o3de.spec, then run 'make srpm-snapshot' or 'make rpm-snapshot'."

# ── SRPM builds ─────────────────────────────────────────────────────────────

# Clean stale SRPMs for THIS package before each rpmbuild -bs so the
# downstream "~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm" glob in our COPR
# targets can only match the freshly-built one. Without this, prior
# snapshot SRPMs sitting in ~/rpmbuild/SRPMS/ get swept into the same
# copr-cli build invocation and produce spurious "failed" builds on
# stale source trees. (Caught 2026-05-12 -- builds 10447330/32 were
# such accidents from older SRPMs lying around.)
SRPM_CLEAN := rm -f ~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

srpm:
	$(SRPM_CLEAN)
	rpmbuild -bs --without snapshot $(RPMBUILD_DEFINES) o3de.spec

srpm-snapshot:
	$(SRPM_CLEAN)
	rpmbuild -bs --with snapshot $(RPMBUILD_DEFINES) o3de.spec

# srpm-snapshot-ref: build an SRPM from an arbitrary o3de/o3de branch
# WITHOUT modifying o3de.spec's hardcoded snapshot_commit/date/sha256.
# Generates a fresh tarball from REF, parses the printed commit/date/sha
# values, and overrides the spec macros via --define at rpmbuild time.
# Doesn't touch the spec on disk so the main stabilization/26100 flow
# isn't disturbed.
#
# Usage:
#   make srpm-snapshot-ref REF=qt6                       # qt6 migration branch
#   make srpm-snapshot-ref REF=development               # bleeding-edge HEAD
#   make srpm-snapshot-ref REF=<commit-sha>              # pinned commit
#
# Output: ~/rpmbuild/SRPMS/o3de2605-<NVR>.src.rpm with the snapshot
# macros pointing at REF's HEAD. For development branch builds, use
# `make copr-development` (wraps srpm-snapshot-development + upload).
# For other refs (rare), create a dedicated COPR project and fire:
# `copr-cli build hellaenergy/o3de-<ref> ~/rpmbuild/SRPMS/...`.
#
# Output of make-snapshot-tarball.sh is parsed via grep -- format:
#   "  %global snapshot_commit <sha>"
#   "  %global snapshot_date   <YYYYMMDD>"
#   "  %global snapshot_sha256 <sha256>"
srpm-snapshot-ref: REF ?= development
# Extra bcond flags appended to the rpmbuild line. Default empty.
# srpm-snapshot-development sets this to `--with development_snapshot`
# so the 6 carry-patches whose upstream equivalents have merged into
# o3de/development get gated off (otherwise %prep fails-to-apply).
# See o3de.spec's `%bcond_with development_snapshot` comment block.
SNAPSHOT_REF_EXTRA_BCOND ?=
srpm-snapshot-ref:
	$(SRPM_CLEAN)
	@echo ">> Generating snapshot tarball from o3de/o3de:$(REF)"
	@( cd sources && ./make-snapshot-tarball.sh "$(REF)" ) > /tmp/snapshot-vars.$$$$.txt 2>&1; \
	cat /tmp/snapshot-vars.$$$$.txt; \
	commit=$$(grep -E '^  %global snapshot_commit' /tmp/snapshot-vars.$$$$.txt | awk '{print $$3}'); \
	date=$$(grep -E '^  %global snapshot_date' /tmp/snapshot-vars.$$$$.txt | awk '{print $$3}'); \
	sha=$$(grep -E '^  %global snapshot_sha256' /tmp/snapshot-vars.$$$$.txt | awk '{print $$3}'); \
	rm -f /tmp/snapshot-vars.$$$$.txt; \
	if [ -z "$$commit" ] || [ -z "$$date" ] || [ -z "$$sha" ]; then \
	  echo ">> ERROR: could not parse commit/date/sha from snapshot output" >&2; \
	  exit 1; \
	fi; \
	echo ">> Baking snapshot_commit=$$commit snapshot_date=$$date into a temp spec copy"; \
	cp $(PWD)/o3de.spec /tmp/o3de-snapshot-ref.$$$$.spec; \
	sed -i \
	    -e "s|^%{?!snapshot_commit:%global snapshot_commit .*$$|%{?!snapshot_commit:%global snapshot_commit $$commit}|" \
	    -e "s|^%{?!snapshot_date:%global snapshot_date .*$$|%{?!snapshot_date:%global snapshot_date $$date}|" \
	    -e "s|^%{?!snapshot_sha256:%global snapshot_sha256 .*$$|%{?!snapshot_sha256:%global snapshot_sha256 $$sha}|" \
	    /tmp/o3de-snapshot-ref.$$$$.spec; \
	echo ">> Building SRPM (--define overrides apply at SRPM-build; baked values survive COPR's re-eval)"; \
	rpmbuild -bs --with snapshot $(SNAPSHOT_REF_EXTRA_BCOND) \
	  --define "snapshot_commit $$commit" \
	  --define "snapshot_date $$date" \
	  --define "snapshot_sha256 $$sha" \
	  $(RPMBUILD_DEFINES) /tmp/o3de-snapshot-ref.$$$$.spec; \
	rm -f /tmp/o3de-snapshot-ref.$$$$.spec

# Convenience aliases for the two common upstream-migration tracking targets.
srpm-snapshot-qt6:
	$(MAKE) srpm-snapshot-ref REF=qt6

srpm-snapshot-development:
	$(MAKE) srpm-snapshot-ref REF=development SNAPSHOT_REF_EXTRA_BCOND="--with development_snapshot"

# srpm-stabilization: snapshot + the stabilization channel marker. This
# is what the community testers' channel ships. The marker is what
# differentiates "stabilization-branch build" (uploaded to o3de-stabilization)
# from a "development-branch build" (uploaded to o3de-development via
# `make copr-development`).
srpm-stabilization:
	$(SRPM_CLEAN)
	rpmbuild -bs $(SRPM_STABILIZATION_FLAGS) $(RPMBUILD_DEFINES) o3de.spec

# srpm-stabilization: snapshot + stabilization + Stage 1 14-pack +
# Stage 2 3-pack (mcpp/dxc/spirvcross). Stage 2 promoted 2026-05-14
# after experimental soak from 2026-05-08; all three PoCs ✓ GREEN in
# experimental builds since 2026-05-08. Promotion timeline:
#   7-pack -> 12-pack: 2026-05-11
#   12-pack -> 13-pack: 2026-05-11 (googlebenchmark)
#   13-pack -> 14-pack: 2026-05-14 (vulkan_validation_layers via Patch0013 v4)
#   14-pack + Stage 2 3-pack: 2026-05-14
# Mirrors the o3de-stabilization COPR chroot config exactly so the
# SRPM faithfully shows what activations the binary build will fire.
# The Stage 2 swaps require additional_repos=copr://hellaenergy/o3de-dependencies
# on each stabilization chroot (one-time copr-cli edit-chroot --repos call;
# done 2026-05-14).
# development_snapshot added 2026-08-11 when the channel repointed from
# stabilization/26050 to stabilization/26100. 26100 was cut from development
# tip, so the seven TIMEBOMB carry-patches (0001/0002/0004/0005/0007/0008/0012)
# plus Patch0009 -- whose upstream equivalents are in development but were not
# in 26050 -- are now present in the 26100 source; applying them would reject
# at %prep. This gate drops them, exactly the documented "retires when the
# channel rebases onto the 26.10 base" retirement. Channel marker stays
# -stabilization (priority order: stabilization beats development_snapshot).
# NOTE: the o3de-stabilization COPR chroots need a matching
# `--rpmbuild-with development_snapshot` (see copr-init); --with here does not
# propagate to the binary build. PENDING per-patch four-check verification
# against 26100 before the first real build.
SRPM_STABILIZATION_FLAGS = --with snapshot \
                           --with stabilization \
                           --with development_snapshot \
                           --with system_assimp \
                           --with system_dxc \
                           --with system_expat \
                           --with system_freetype \
                           --with system_googlebenchmark \
                           --with system_libsamplerate \
                           --with system_lua \
                           --with system_lz4 \
                           --with system_mcpp \
                           --with system_mikkelsen \
                           --with system_openexr \
                           --with system_png \
                           --with system_poly2tri \
                           --with system_spirvcross \
                           --with system_sqlite \
                           --with system_vulkan_validation_layers \
                           --with system_zlib

# DEPRECATED / UNWIRED as of 2026-07-24: o3de-experimental was realigned
# onto o3de/development + monolithic (srpm-experimental now aliases
# srpm-snapshot-development, rpm-experimental builds development+monolithic),
# so this Stage-1 system-swap flag set is no longer referenced by any target.
# Kept only because the trailing comments below document individual swaps
# (system_dxc, swap_hook, ...) that other channels (stabilization/stable)
# still care about. Do NOT re-wire experimental to these; if a future channel
# needs a Stage-1 swap set, give it its own flags var.
SRPM_EXPERIMENTAL_FLAGS = --with snapshot \
                          --with stabilization \
                          --with system_assimp \
                          --with system_cityhash \
                          --with system_dxc \
                          --with system_expat \
                          --with system_freetype \
                          --with system_googlebenchmark \
                          --with system_libsamplerate \
                          --with system_lua \
                          --with system_lz4 \
                          --with system_mcpp \
                          --with system_mikkelsen \
                          --with system_openexr \
                          --with system_png \
                          --with system_poly2tri \
                          --with system_rapidjson \
                          --with system_spirvcross \
                          --with system_sqlite \
                          --with system_tiff \
                          --with system_vulkan_validation_layers \
                          --with system_xxhash \
                          --with system_zlib \
                          --with swap_hook
# swap_hook added 2026-06-03: the central system-swap download hook
# prototype (Patch0014/0015 in place of Patch0006/0013; see the
# swap_hook bcond comment in o3de.spec). Mirrors the flag on the
# o3de-experimental chroots; the binary-build activation lives there.
# system_dxc added 2026-05-08 (Stage 2 binary-only swap, sibling to
# system_spirvcross). Engine treats DXC as a binary executable
# shellout, not a library link (per `project_dxc_binary_only_dependency.md`
# memory and Nick_L's 2026-05-05 sig-build comment: "engine doesn't
# link DXC at all, just shells out to the dxc binary"). Three install
# paths to overlay (engine-side):
#   Builders/DirectXShaderCompiler/bin/dxc          -> /usr/bin/dxc
#   Builders/DirectXShaderCompiler/bin/dxsc         -> /usr/bin/dxsc
#   Builders/DirectXShaderCompiler/lib/libdxcompiler.so -> /usr/lib64/libdxcompiler.so
# All three from the o3de-dxc-spirv COPR package (built from
# o3de/DirectXShaderCompiler at tag release-1.8.2505.1-o3de;
# license-clean Linux/SPIR-V-only build; ✓ green PoC build 10435628
# since 2026-05-08; functional verification confirmed
# `dxc -spirv -T ps_6_0` produces valid SPIR-V output).
#
# system_spirvcross added 2026-05-08 (Stage 2 binary-only swap, first
# of its kind). Engine treats spirv-cross as a binary executable
# shellout, not a library link (per audit 2026-05-07,
# /tmp/o3de-assimp-audit/SPIRVCROSS_INVESTIGATION_NOTES.md).
# Implementation: %install creates a symlink at the engine's expected
# runtime path
# (/opt/O3DE/<v>/bin/Linux/profile/Default/Builders/SPIRVCross/spirv-cross)
# pointing to /usr/bin/spirv-cross from the o3de-spirv-cross COPR
# package (built from KhronosGroup/SPIRV-Cross at vulkan-sdk-1.3.275.0,
# license-clean Apache-2.0 OR MIT). The bundled spirv-cross fetch from
# packages.o3de.org still happens at cmake time (it ships a
# FindSPIRVCross.cmake the engine needs at config time); the symlink
# at install time overlays it. Future cleanup: write a
# Findspirvcross-system.cmake shim, gate Patch0006, drop the upstream
# fetch entirely.
#
# system_assimp added 2026-05-08 (Stage 1 12-pack). Audit (2026-05-07,
# /tmp/o3de-assimp-audit/INVESTIGATION_NOTES.md) confirmed Stage 1
# candidate: consumers exclusively in Code/Tools/SceneAPI/ (asset-
# pipeline 3D-model importer); zero refs in Gems/, zero in core
# Code/Framework/. All 27 unique types + 7 processing flags engine
# consumes are public ai* C-API and Assimp::Importer C++ class; 100%
# present in Fedora 6.0.4 headers. Engine include style
# `<assimp/header.h>` matches Fedora layout exactly. FBX importer
# compiled into Fedora's libassimp.so.6.0.4. Findassimp-system.cmake
# follows mikkelsen pattern (Fedora's assimpConfig.cmake creates
# `assimp::assimp` as a side-effect IMPORTED target which trips
# O3DE's runtime walker — same reason as the FindZLIB / FindSQLite
# shims). Caveat: 5.4 → 6.0 major version delta; symbols verified ✓
# but runtime FBX-import behavior on tricky inputs is unverified.
# Mitigation: pair with a Tier 6 integration test that bakes a known
# FBX from AutomatedTesting Gem (FOLLOW_UPS.md item).
#
# system_libsamplerate added 2026-05-08 (Stage 1 11-pack). Audit
# (2026-05-07, /tmp/o3de-assimp-audit/LIBSAMPLERATE_INVESTIGATION_NOTES.md)
# confirmed lowest-risk Stage 1 swap to date — engine consumes
# libsamplerate exclusively in Gems/Microphone/, and the Linux PAL is a
# None stub (do-nothing impl). Zero src_* function calls in the Linux
# runtime path; the Gem's CMakeLists.txt unconditionally LINKS the lib
# but no engine code on Linux exercises it at runtime. 0.2.1 → 0.2.2
# point-version increment within libsamplerate's 23-year ABI-stable major.
#
# system_sqlite added 2026-05-08 (Stage 1 10-pack). Audit (2026-05-07,
# /tmp/o3de-assimp-audit/SQLITE_INVESTIGATION_NOTES.md) found SQLite is
# the cleanest Stage 1 candidate to date: consumers exclusively in
# Code/Framework/AzToolsFramework/SQLite/ + Code/Tools/AssetProcessor/
# AssetDatabase/ (editor/tool framework, not runtime engine); all 29
# unique sqlite3_* symbols are core public C-API and 100% present in
# Fedora 3.51.2 headers; zero extension-only API used (no FTS5/RTREE/
# JSON1/SEE) so Fedora's standard sqlite-libs is sufficient; 3.37 → 3.51
# is point-version increment within SQLite's 21-year ABI-stable major.
# FindSQLite-system.cmake follows the mikkelsen pattern (direct
# find_path/find_library, creates 3rdParty::SQLite directly) — necessary
# because cmake's stock FindSQLite3.cmake creates SQLite::SQLite3 as a
# side-effect IMPORTED target which trips O3DE's runtime walker (same
# reason as FindZLIB shim).
#
# system_poly2tri added 2026-05-07 (Stage 1 8-pack). Audit (issue #7,
# 2026-05-07) found poly2tri consumers exclusively in Gems/PhysX/
# (Editor's PolygonPrismMeshUtils for polygon-prism shape colliders),
# zero references in core Code/. Engine uses public p2t:: namespace
# API only; no internal-symbol coupling. Fedora's poly2tri-devel ships
# from Mason Green's BSD-3-Clause original (commit 26242d0a, May 2013) —
# license-clean and independent of the bundled fork's attribution
# issue. Findpoly2tri-system.cmake bridges the engine's `<poly2tri.h>`
# include syntax to Fedora's /usr/include/poly2tri/poly2tri.h layout
# via include-path adjustment. Patch0009 ships separately from
# Patch0006 because poly2tri's bundle anchor lives in PhysX-Gem-internal
# PAL files (Gems/PhysX/Core/PhysX{4,5}/Source/Platform/Linux/
# PAL_linux.cmake), not the standard BuiltInPackages_linux_x86_64.cmake.
# Audit-track confirmation: same playbook that delivered the AzCore Lua
# PR (#19733) and the OpenEXR shim split. squish-ccr (the other half of
# issue #7's restricted scope) was audited in the same pass and stays
# restricted: BC7 patent encumbrance + squish-ccr-specific API surface
# (Fedora ships only upstream libsquish, which lacks BC7 / different ABI).
#
# system_openexr added 2026-05-06 (Stage 2a — first cross-stage step).
# OpenEXR's bundle declares both TARGETS OpenEXR + Imath; single
# FindOpenEXR-system.cmake shim creates both 3rdParty::OpenEXR (links
# libOpenEXR family) and 3rdParty::Imath (links libImath). Engine
# consumers use `#include <OpenEXR/Imf*.h>` verbatim — matches Fedora's
# openexr-devel + imath-devel layout exactly. Per Nick_L's 2026-05-05
# response, OpenEXR version pins are not hard (3.1 → 3.2 is back-compat
# per OpenEXR semver). The openimageio-opencolorio sibling Stage 2b
# track is NOT activated here — blocked on Stage 3 (Python migration)
# per the Python C Module ABI chain.
#
# system_lz4 added 2026-05-05. Findlz4-system.cmake follows mikkelsen
# pattern; engine consumers (Gems/MultiplayerCompression,
# Code/Framework/AzFramework Archive) use `#include <lz4.h>` /
# `<lz4hc.h>` / `<lz4frame.h>` verbatim, which match Fedora's
# lz4-devel layout exactly — no wrapper-header bridging needed.
#
# system_expat / system_freetype / system_png / system_zlib re-activated
# 2026-05-04 after refactoring the 4 Find<X>-system.cmake shims to the
# mikkelsen pattern (commits 92bde6e / cba5059 / 6b14ffa / 0ca58e8).
# Each refactored shim does its own find_path + find_library lookup and
# does NOT `include()` cmake's stock module — so the side-effect upper-
# namespace target (`ZLIB::ZLIB`, `PNG::PNG`, `Freetype::Freetype`,
# `EXPAT::EXPAT`) that previously failed O3DE's runtime walker is no
# longer created by the stock module. The shims provide those
# upper-namespace names as ALIASes of `3rdParty::<X>` so upstream
# consumers (notably the bundled freetype's FindFreetype.cmake doing
# `target_link_libraries(... ZLIB::ZLIB)`) still resolve. Each was
# validated individually via isolated `rpmbuild --with system_<X>`
# builds; combined 6-pack validation lands with the same commit that
# adds system_lz4.
#
# system_tiff Option C (Bundling Library Exception path, 2026-05-05) —
# Patch0008 narrow-guard attempt failed because CryCommon's own internal
# headers (Cry_ValidNumber.h's DoubleU64 macros) use `uint64` directly,
# transitively included from EditorDefs.h before <tiffio.h>. Reordering
# the includes ABI-mismatches at link time. Engine-wide CryCommon C99
# migration ruled out as out-of-scope. Bundle stays.
#
# system_lua added 2026-05-07 (Stage 1 9-pack). Patch0008 carry-patch
# (commit d69bb9c) drops AzCore ScriptContext.cpp's include of Lua's
# internal <Lua/lobject.h> — the only symbol it pulled in (LUAI_MAXALIGN)
# is already public Lua API via luaconf.h's transitive include from
# lauxlib.h. Behavior-preserving; bundled-Lua builds also benefit. With
# Patch0008 applied unconditionally, Fedora's lua-devel (which ships
# only the public API: lua.h, lauxlib.h, lualib.h, luaconf.h) is now
# sufficient. Patch0008 was also submitted upstream as o3de/o3de PR
# #19733 (approved by nick-l-o3de 2026-05-07, awaiting merge); when
# that lands, our Patch0008 becomes redundant and can drop.

# srpm-experimental: o3de-experimental was realigned 2026-07-24 onto
# o3de/development + the monolithic permutation, off its old Stage-1
# system-swap base (26050 shipped as 26.05.0 and is frozen; the stabilization
# channel repointed to stabilization/26100, cut from development tip 2026-08-11).
# It now builds the SAME development-snapshot SRPM as copr-development; the
# experimental chroots carry `development_snapshot qt6 monolithic` (set via
# edit-chroot), so the only per-channel difference from o3de-development is
# the monolithic bcond. Alias kept so the copr-experimental* targets that
# depend on it keep working.
srpm-experimental: srpm-snapshot-development

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

# Local mirror of the experimental COPR build: development snapshot + Qt6 +
# monolithic, built end-to-end on this host. Mirrors the o3de-experimental
# chroot config (development_snapshot qt6 monolithic). Use it to validate
# spec changes faster than the COPR round-trip. Doesn't exercise the
# F44 + rawhide + CS10 chroot matrix that COPR provides — that part still
# needs the COPR build.
rpm-experimental:
	$(MAKE) srpm-snapshot-ref REF=development SNAPSHOT_REF_EXTRA_BCOND="--with development_snapshot"
	rpmbuild --rebuild --with snapshot --with development_snapshot --with qt6 --with monolithic \
	    ~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# rpm-local-development: build the development-branch RPM on THIS host and
# leave it in ~/rpmbuild/RPMS for local install/test. After the qt6 merge,
# development IS Qt6, so this mirrors the validated qt6 local build (2026-06-09)
# with REF swapped to development: an all-patches SRPM, builddep the Qt6 build
# deps (dbus-devel + patchelf, exposed only with --with qt6), then --rebuild
# with the full qt6 bcond set. ~70 min on a 32 GB workstation.
# RUN ONLY AFTER the qt6 merge + chroot flip: before the merge development is
# still Qt5 and --with qt6 against a Qt5 tree is wrong (same reason we cannot
# pre-flip the chroots). Install hint printed at the end (the -devel subpackage
# pins the exact NVR, so install main + devel together with --allow-downgrade).
rpm-local-development:
	$(MAKE) srpm-snapshot-ref REF=development
	sudo dnf builddep -y o3de.spec \
	    --define "_sourcedir $(PWD)/sources" \
	    --define "_with_snapshot 1" \
	    --define "_with_development_snapshot 1" \
	    --define "_with_qt6 1"
	rpmbuild --rebuild --with snapshot --with development_snapshot --with qt6 \
	    ~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm
	@echo ">> Built. To install (run main + devel together; --allow-downgrade for same-NVR swap):"
	@echo "   sudo dnf install --allow-downgrade ~/rpmbuild/RPMS/x86_64/$(PKGNAME)-*.rpm"

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
	@echo "      --chroot centos-stream-10-x86_64 \\"
	@echo "      --enable-net on --appstream on \\"
	@echo "      --description 'Open 3D Engine -- tagged stable releases'"
	@echo
	@echo "# 2. Stabilization (community-tester) project — pre-release validation"
	@echo "#    builds from upstream's stabilization/<release> branch:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_STABILIZATION) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on --appstream on \\"
	@echo "      --description 'O3DE pre-release validation builds from stabilization/<release>'"
	@echo
	@echo "# 3. Development-branch project — always tracks upstream o3de/development."
	@echo "#    Ad-hoc cadence. For other arbitrary refs (rare; e.g. qt6 migration"
	@echo "#    work), create a separate dedicated COPR project rather than"
	@echo "#    overloading this one:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_DEVELOPMENT) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on \\"
	@echo "      --description 'O3DE development-branch builds (upstream o3de/development tip)'"
	@echo
	@echo "# 4. Experimental (in-flight migration) project:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --enable-net on \\"
	@echo "      --description 'O3DE experimental builds — Stage 1 migration work'"
	@echo
	@echo "# Wire o3de-dependencies into each chroot for all four engine projects:"
	@echo "  for proj in $(COPR_PROJECT_STABLE) $(COPR_PROJECT_STABILIZATION) $(COPR_PROJECT_DEVELOPMENT) $(COPR_PROJECT_EXPERIMENTAL); do \\"
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
	@echo "# WARNING: 'copr-cli edit-chroot ... --rpmbuild-with X' REPLACES the"
	@echo "# chroot's entire with_opts list with [X]; it does NOT append. Always"
	@echo "# pass the FULL intended list of --rpmbuild-with flags in a single"
	@echo "# invocation. After the edit, verify with 'copr-cli get-chroot ...'"
	@echo "# (jq .with_opts) before considering the change done. Caught the"
	@echo "# hard way 2026-05-08 -- single-flag edit nuked the experimental"
	@echo "# chroot's 16-entry list down to 1 entry. See memory note"
	@echo "# feedback_copr_edit_chroot_replaces.md."
	@echo
	@echo "#    a. Stabilization-channel marker on o3de-stabilization chroots"
	@echo "#       (drives the GUI '-stabilization.<commit>' channel suffix):"
	@echo "  for chroot in fedora-44-x86_64 fedora-rawhide-x86_64; do \\"
	@echo "      copr-cli edit-chroot $(COPR_OWNER)/$(COPR_PROJECT_STABILIZATION)/\$$chroot \\"
	@echo "          --rpmbuild-with stabilization \\"
	@echo "          --rpmbuild-with system_expat \\"
	@echo "          --rpmbuild-with system_freetype \\"
	@echo "          --rpmbuild-with system_lz4 \\"
	@echo "          --rpmbuild-with system_mikkelsen \\"
	@echo "          --rpmbuild-with system_openexr \\"
	@echo "          --rpmbuild-with system_png \\"
	@echo "          --rpmbuild-with system_zlib; \\"
	@echo "  done"
	@echo
	@echo "#    b. o3de-experimental (realigned 2026-07-24 onto development +"
	@echo "#       monolithic; off the old Stage-1 system-swap base). Same as the"
	@echo "#       o3de-development chroots plus the monolithic bcond, which ships"
	@echo "#       the release/Monolithic static libs for release game export."
	@echo "  for chroot in fedora-44-x86_64 fedora-rawhide-x86_64 centos-stream-10-x86_64; do \\"
	@echo "      copr-cli edit-chroot $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL)/\$$chroot \\"
	@echo "          --rpmbuild-with development_snapshot \\"
	@echo "          --rpmbuild-with qt6 \\"
	@echo "          --rpmbuild-with monolithic; \\"
	@echo "  done"
	@echo
	@echo "#    c. o3de-development chroots set --rpmbuild-with development_snapshot"
	@echo "#       (gates off the carry-patches whose upstream equivalents have"
	@echo "#       already landed in development; also drives the -development"
	@echo "#       channel marker in the GUI). No system_* swaps on this channel"
	@echo "#       so dev-branch builds aren't masked by packaging variations."
	@echo "  for chroot in fedora-44-x86_64 fedora-rawhide-x86_64; do \\"
	@echo "      copr-cli edit-chroot $(COPR_OWNER)/$(COPR_PROJECT_DEVELOPMENT)/\$$chroot \\"
	@echo "          --rpmbuild-with development_snapshot; \\"
	@echo "  done"
	@echo
	@echo "# After a Stage 1 batch validates on o3de-experimental and is approved"
	@echo "# to ship to testers, mirror the SAME --rpmbuild-with system_<lib>"
	@echo "# flags onto the o3de-stabilization chroots. And whenever the o3de"
	@echo "# (stable) project ships its first migrated build, the SAME flags"
	@echo "# need to land there too — otherwise stable RPMs default the bconds"
	@echo "# off and ship the bundled libraries instead of the system ones,"
	@echo "# even though the spec carries the gates. Same goes for the"
	@echo "# centos-stream-10 chroot (in stable's chroot list above). Rules:"
	@echo "#   - Every engine project that ships migrations needs every"
	@echo "#     --rpmbuild-with flag for those migrations on every chroot."
	@echo "#   - When a new migration activates (new system_<lib> bcond),"
	@echo "#     run the chroot edit on every shipping project, not just"
	@echo "#     experimental."
	@echo "#   - When a new chroot joins the matrix (e.g., fedora-45 ships),"
	@echo "#     copy the --rpmbuild-with flag set onto the new chroot."
	@echo "#   - The 'stabilization' bcond stays on o3de-stabilization +"
	@echo "#     o3de-experimental chroots only; o3de (stable) and"
	@echo "#     o3de-development do NOT get it."
	@echo
	@echo "# 6. Auto-enable o3de-dependencies for end users. Without this,"
	@echo "# 'dnf copr enable hellaenergy/<engine-project>' alone leaves users"
	@echo "# unable to resolve Requires:mikkelsen and similar swapped deps."
	@echo "# Apply to every engine project:"
	@echo "  for proj in $(COPR_PROJECT_STABLE) $(COPR_PROJECT_STABILIZATION) $(COPR_PROJECT_DEVELOPMENT) $(COPR_PROJECT_EXPERIMENTAL); do \\"
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
	@echo
	@echo "# 7. Debug-config sibling projects ($(COPR_PROJECT_TESTING_DEBUG),"
	@echo "# $(COPR_PROJECT_DEVELOPMENT_DEBUG)). Each mirrors its namesake's"
	@echo "# chroot with_opts PLUS the 'debug' bcond, emitting o3de2605-debug"
	@echo "# (-O0 + full symbols) for tester crash reports. Create with"
	@echo "# --appstream off (the duplicate main package must not register as a"
	@echo "# second GNOME Software app) and --auto-prune on (debug artifacts are"
	@echo "# large). Wire each chroot with the SAME --repos + --rpmbuild-with"
	@echo "# list as its namesake (section 5) and append --rpmbuild-with debug:"
	@echo "  copr-cli create $(COPR_OWNER)/$(COPR_PROJECT_TESTING_DEBUG) \\"
	@echo "      --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \\"
	@echo "      --chroot centos-stream-10-x86_64 \\"
	@echo "      --enable-net on --appstream off --auto-prune on \\"
	@echo "      --description 'O3DE debug-config binaries mirroring hellaenergy/o3de-testing'"
	@echo "# (then edit-chroot each with o3de-testing's with_opts + debug; CS10"
	@echo "#  also needs the EPEL-10 repo. Same shape for $(COPR_PROJECT_DEVELOPMENT_DEBUG)"
	@echo "#  but with the development_snapshot + debug pair, all-bundled.)"
	@echo "# Refresh via 'make copr-testing-debug' / 'make copr-development-debug',"
	@echo "# always from the SAME NVR as the sibling channel (lockstep -- the"
	@echo "# -debug subpackage hard-Requires the main package's exact NVR)."

copr-stable: srpm
	copr-cli build --timeout 28800 $(COPR_OWNER)/$(COPR_PROJECT_STABLE) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# o3de-testing is the pre-promotion soak channel for stable. Same SRPM
# as stable (same release tag + same with_opts via chroot config); the
# difference is the destination project. Promotion flow:
# main HEAD -> copr-testing-and-test (soak ~48h) -> copr-stable.
# Mirrors Fedora's updates-testing semantics.
copr-testing: srpm
	copr-cli build --timeout 28800 $(COPR_OWNER)/$(COPR_PROJECT_TESTING) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# release-stable: post-release-ceremony helper. Verifies the spec's
# stable_tag has a real (non-placeholder) sha256 and tarball before
# firing the COPR build. Intended use is when an upstream release
# has just been tagged on main and the spec has been updated per
# POST_RELEASE.md. Fails early if the runbook's steps 1-5 haven't
# been completed.
#
# Usage: edit o3de.spec (stable_tag, stable_sha256, %changelog),
# bump the SBOM, commit + push, then `make release-stable`.
release-stable:
	@set -e; \
	tag=$$(rpmspec --without snapshot $(RPMBUILD_DEFINES) -q --qf '%{VERSION}\n' o3de.spec 2>/dev/null | head -1); \
	sha=$$(awk '/^%global stable_sha256/ {print $$3; exit}' o3de.spec); \
	if [ "$$tag" = "%{stable_tag}" ] || [ -z "$$tag" ]; then \
	    echo "ERROR: could not resolve stable_tag from spec"; exit 2; fi; \
	if [ "$$sha" = "0000000000000000000000000000000000000000000000000000000000000000" ]; then \
	    echo "ERROR: stable_sha256 is still the placeholder; update spec per POST_RELEASE.md step 3"; \
	    exit 2; fi; \
	if [ -z "$$sha" ] || [ $${#sha} -ne 64 ]; then \
	    echo "ERROR: stable_sha256 is empty or wrong length ($$sha)"; exit 2; fi; \
	tarball=$(PWD)/sources/o3de-$${tag}-lfs.tar.gz; \
	if [ ! -f $$tarball ]; then \
	    echo "ERROR: release tarball $$tarball not in $(PWD)/sources/ - pull it per POST_RELEASE.md step 2"; \
	    echo "(2605.0+ uses dashes in the filename; earlier releases used underscores -- check if that's the issue)"; \
	    exit 2; fi; \
	actual_sha=$$(sha256sum $$tarball | awk '{print $$1}'); \
	if [ "$$actual_sha" != "$$sha" ]; then \
	    echo "ERROR: spec sha256 ($$sha) does not match tarball ($$actual_sha)"; \
	    exit 2; fi; \
	echo "release-stable pre-flight clean: tag=$$tag sha256=ok tarball=present"; \
	echo "Building SRPM + firing to $(COPR_OWNER)/$(COPR_PROJECT_STABLE) ..."; \
	$(MAKE) copr-stable

# copr-development: always builds from upstream's development branch
# (via srpm-snapshot-development, which sets REF=development +
# --with development_snapshot to gate off the carry-patches whose
# upstream equivalents have already landed in development). Its chroots
# carry `development_snapshot qt6 monolithic` (the monolithic bcond was
# promoted here from o3de-experimental on 2026-08-03), so the build ships
# the release/Monolithic static libs and a release game export works from
# the installed RPM (see FOLLOW_UPS "monolithic"). For arbitrary other-ref
# builds (rare; e.g., qt6), create a dedicated COPR project and fire
# srpm-snapshot-ref at it directly via copr-cli.
copr-development: srpm-snapshot-development
	@$(MAKE) --no-print-directory qt6-merge-gate
	copr-cli build --timeout 28800 $(COPR_OWNER)/$(COPR_PROJECT_DEVELOPMENT) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# copr-stabilization: the regular community-tester channel. This is the
# project the test-installed.yml cron polls for new builds.
copr-stabilization: srpm-stabilization
	copr-cli build --timeout 28800 $(COPR_OWNER)/$(COPR_PROJECT_STABILIZATION) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# o3de-experimental: realigned 2026-07-24 onto o3de/development + the
# monolithic permutation (chroots carry `development_snapshot qt6 monolithic`).
# Builds the SAME dev-snapshot SRPM as copr-development (via the
# srpm-experimental alias); the only per-channel difference is the monolithic
# bcond, which ships the release/Monolithic static libs so a release game
# export works (see FOLLOW_UPS "monolithic"). Our sandbox for work not yet
# ready for the community channels. qt6-merge-gate hard-stops if development
# is on Qt6 but the experimental chroots lack the qt6 bcond.
copr-experimental: srpm-experimental
	@$(MAKE) --no-print-directory qt6-merge-gate GATE_PROJECT=$(COPR_PROJECT_EXPERIMENTAL)
	copr-cli build --timeout 28800 $(COPR_OWNER)/$(COPR_PROJECT_EXPERIMENTAL) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# Debug-config sibling builds. Same SRPM as the namesake channel; the
# `debug` bcond lives on the project's chroots (so the binary build
# emits o3de2605-debug). Higher --timeout (64800 = 18h) because the
# debug config roughly doubles build time, and --nowait because (a) an
# 18h build isn't worth blocking on and (b) it sidesteps the large-SRPM
# client wedge (see feedback_copr_cli_hangs_after_large_srpm_upload).
# Sizing: the first testing-debug validation (build 10532647, 2026-06-01)
# took 10h48m against a 12h cap -- only ~1h12m of headroom -- and the
# development-debug build is HEAVIER still (all-bundled compiles the 3p
# from source instead of linking the system swaps), so 12h was too close.
# 18h gives margin; the cap is a ceiling, not a duration, so finishing
# early costs nothing.
#
# LOCKSTEP: fire these from the SAME spec state (same NVR) as their
# sibling channel, ideally back-to-back, e.g.
#     make copr-testing && make copr-testing-debug
# Both reuse the same on-disk $(PKGNAME)-*.src.rpm, so the NVRs match
# and `dnf install o3de2605-debug` resolves against the channel's main
# package. If you bump Release between the two, they drift and the
# debug subpackage won't install.
copr-testing-debug: srpm
	copr-cli build --timeout 64800 --nowait $(COPR_OWNER)/$(COPR_PROJECT_TESTING_DEBUG) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

copr-development-debug: srpm-snapshot-development
	@$(MAKE) --no-print-directory qt6-merge-gate GATE_PROJECT=$(COPR_PROJECT_DEVELOPMENT_DEBUG)
	copr-cli build --timeout 64800 --nowait $(COPR_OWNER)/$(COPR_PROJECT_DEVELOPMENT_DEBUG) \
		~/rpmbuild/SRPMS/$(PKGNAME)-*.src.rpm

# 28800s = 8 hr. Default COPR project timeout is 5 hr (18000s); build
# 10439258 hit it at exactly 18141s on F44 with the full Stage 1+Stage 2
# build, despite the Makefile passing --timeout 25200 (the build was
# resubmitted via raw copr-cli without the flag, defaulting to 5h and
# being killed at the "Checking for unpackaged file(s)" finalization
# step). Bumped to 28800 to give rawhide (10-30% slower than F44) and
# CS10 (compile cost unknown until first successful end-to-end run)
# usable headroom over F44's 5h2m baseline.

# Submit to COPR, watch until completion, fire a repository_dispatch
# event at the GitHub Actions test-installed.yml workflow on success.
# Requires `gh` CLI authenticated for repo write access. The workflow
# resolves the F44 RPM URL from the build_id by listing the COPR
# results directory, so we only need to pass the build_id along.
#
# Three "build + watch + trigger CI tests" variants; pick by the
# destination project. copr-development for dev-branch tracking,
# copr-stabilization for the testers' channel, copr-experimental for
# in-flight migration work.
copr-development-and-test: srpm-snapshot-development
	@$(MAKE) --no-print-directory qt6-merge-gate
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_DEVELOPMENT)

copr-stabilization-and-test: srpm-stabilization
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_STABILIZATION)

copr-experimental-and-test: srpm-experimental
	@$(MAKE) --no-print-directory qt6-merge-gate GATE_PROJECT=$(COPR_PROJECT_EXPERIMENTAL)
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_EXPERIMENTAL)

# copr-testing-and-test: build the stable SRPM, push to o3de-testing,
# watch + trigger CI tests. Same SRPM as copr-stable; difference is
# the destination project. Used for the routine "soak before stable"
# cadence on packaging-side fixes.
copr-testing-and-test: srpm
	@$(MAKE) _copr-and-test COPR_TARGET=$(COPR_PROJECT_TESTING)

# Internal helper: parameterized build-then-watch-then-trigger-tests.
# Not a normal entry point; called from copr-{development,stabilization,experimental}-and-test.
_copr-and-test:
	@[ -n "$(COPR_TARGET)" ] || { echo "_copr-and-test requires COPR_TARGET="; exit 2; }
	@set -e ; \
	build_output=$$(copr-cli build --timeout 28800 \
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
	rpm_rel=$$(curl -fsSL "$$repo/$$primary" | gunzip -c | grep -oE 'href="Packages/o/o3de[0-9]+-[0-9][^"^]+\.x86_64\.rpm"' | sed 's/^href="//; s/"$$//' | sort -V | tail -1) ; \
	if [ -z "$$rpm_rel" ]; then \
	    echo "ERROR: no F44 o3de RPM in repodata at $$repo" ; exit 1 ; \
	fi ; \
	rpm_url="$${repo}/$${rpm_rel}" ; \
	echo ">> Triggering test-installed.yml for $$rpm_url" ; \
	gh api -X POST repos/$(GITHUB_REPO)/dispatches \
	    -f event_type=copr-build-succeeded \
	    -F client_payload[rpm_url]="$$rpm_url" \
	    -F client_payload[build_id]="$(BUILD_ID)"

# ── COPR project metadata sync ──────────────────────────────────────────────
# The description / instructions / homepage / contact blocks shown on each
# hellaenergy/<project> COPR page are user-facing docs. We mirror them into
# copr-metadata/<project>/ so drift surfaces as a code-reviewable diff
# (matches the feedback_keep_copr_metadata_current memory note).
#
# Workflow:
#   make copr-metadata-pull    # COPR -> repo (use to capture out-of-band edits)
#   make copr-metadata-diff    # compare; non-zero exit on drift
#   make copr-metadata-push    # repo -> COPR (requires copr-cli auth)
#
# To touch a single project, drop into the script directly:
#   scripts/copr-metadata.sh push o3de-stabilization
copr-metadata-pull:
	@scripts/copr-metadata.sh pull

copr-metadata-diff:
	@scripts/copr-metadata.sh diff

copr-metadata-push:
	@scripts/copr-metadata.sh push

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

# Asset-bake regression (Tier 7): bake a known FBX through the full
# AssetProcessor pipeline (which uses assimp exclusively) and smoke
# the .azmodel + .azmaterial output. Pairs with the system_assimp
# Stage 1 swap to catch 5 -> 6 major-version behavior deltas.
test-asset-bake:
	tests/asset-bake-test.sh

# AssetProcessor runtime smoke (Tier 8): spawn AP, verify at least one
# AssetBuilder reaches and sustains "alive" state across a 5s
# persistence window. Catches process-lifecycle bugs that build-time
# + linkage checks miss. Motivating example: Patch0012 v1
# (m_tetherLifetime / prctl) was build-green on three chroots but
# every AssetBuilder got SIGTERM'd within 21 ms of fork at runtime.
test-ap-spawn:
	tests/ap-spawn-smoke-test.sh

# MultiplayerSample build smoke (Tier 9): clone o3de-multiplayersample,
# register against installed engine, cmake configure + ninja build the
# GameLauncher, full project asset bake, headless launcher smoke (when
# DISPLAY available). Catches regressions that the cube.fbx Tier 7 bake
# can't see -- this exercises the project-build pipeline + multi-level
# asset tree on a real community project. Cost: ~10-30 min cold, ~5-15
# min warm. NOT part of `make test`; explicit-only because of the
# build/disk footprint. Env overrides documented at the top of the
# script.
test-multiplayer-sample:
	tests/multiplayersample-build-test.sh

# Tier 10 -- NewspaperDeliveryGame (Paper_Kid) build+bake smoke. Sister
# tier to Tier 9 but a different project shape: script_only=true, single-
# player, heavy LyShine + LandscapeCanvas + WhiteBox + EMotionFX surface,
# no native C++ gem code. Clones from nickschuetz/NewspaperDeliveryGame
# (fork) at a pinned SHA. Lower cost than Tier 9 (no native link).
# NOT part of `make test`; explicit-only.
test-newspaper-delivery:
	tests/newspaper-delivery-build-test.sh

# Tier 11 -- Post-load liveness smoke. Runs an installed sample's
# GameLauncher for LIVENESS_SECONDS (default 60s) after LEVEL_LOAD_END
# and verifies the engine survives without crashing or freezing.
# Catches "level loaded but engine froze" -- a failure mode Tier 9/10
# can't see because they only check the level-load success marker.
# Requires Tier 9 or Tier 10 to have run first (project cache must be
# baked). NOT part of `make test`; explicit-only.
#
# Usage:
#   make test-tier11                       # default: NewspaperDeliveryGame, 60s
#   make test-tier11-multiplayer           # MultiplayerSample variant
#   LIVENESS_SECONDS=120 make test-tier11  # extended window
test-tier11:
	tests/post-load-liveness-test.sh

test-tier11-multiplayer:
	PROJECT=multiplayer tests/post-load-liveness-test.sh

# ── MultiplayerSample manual-play helpers ───────────────────────────────────
# Targets for running the actual game (not the smoke tests). Requires Tier 9
# to have run at least once so the project is cloned + built + baked.
#
# Stable interactive config: headless server + windowed client.
# Graphical ServerLauncher works for dev/debug but crashes when the client's
# settings menu fires a resolution-toggle broadcast (see FOLLOW_UPS.md MPS
# entry for the diagnosis). Headless server has no rendering pipeline to
# reconfigure, so the settings-menu path is safe with it.
#
# Vars (override via env if your clone lives elsewhere):
MPSAMPLE_PLAY_DIR  ?= $(HOME)/PROJECTS/o3de-multiplayersample
MPSAMPLE_ENGINE    ?= /opt/O3DE/26.05.0
MPSAMPLE_BIN       := $(MPSAMPLE_PLAY_DIR)/build/linux/bin/profile
MPSAMPLE_REGSETS   := \
    --regset="/O3DE/Autoexec/ConsoleCommands/bg_ConnectToAssetProcessor=0"

play-mps-host:
	@[ -x "$(MPSAMPLE_BIN)/MultiplayerSample.HeadlessServerLauncher" ] \
	    || { echo "ERROR: HeadlessServerLauncher not built. Run 'make test-multiplayer-sample' first."; exit 2; }
	@echo "Starting headless MultiplayerSample server (NewStarbase, UDP 33450)..."
	@setsid "$(MPSAMPLE_BIN)/MultiplayerSample.HeadlessServerLauncher" \
	    --project-path="$(MPSAMPLE_PLAY_DIR)" \
	    --engine-path="$(MPSAMPLE_ENGINE)" \
	    --console-command-file="$(MPSAMPLE_PLAY_DIR)/launch_server.cfg" \
	    $(MPSAMPLE_REGSETS) \
	    </dev/null >/tmp/mps-server.log 2>&1 & \
	    disown 2>/dev/null || true; \
	    sleep 2; \
	    pid=$$(pgrep -f 'MultiplayerSample.HeadlessServerLauncher' | head -1); \
	    echo "Headless server PID: $$pid"; \
	    echo "Stdout log: /tmp/mps-server.log"

play-mps-client:
	@[ -x "$(MPSAMPLE_BIN)/MultiplayerSample.GameLauncher" ] \
	    || { echo "ERROR: GameLauncher not built. Run 'make test-multiplayer-sample' first."; exit 2; }
	@echo "Starting windowed MultiplayerSample client (connects to 127.0.0.1)..."
	@setsid "$(MPSAMPLE_BIN)/MultiplayerSample.GameLauncher" \
	    --project-path="$(MPSAMPLE_PLAY_DIR)" \
	    --engine-path="$(MPSAMPLE_ENGINE)" \
	    --console-command-file="$(MPSAMPLE_PLAY_DIR)/launch_client.cfg" \
	    $(MPSAMPLE_REGSETS) \
	    --regset="/O3DE/Autoexec/ConsoleCommands/r_fullscreen=0" \
	    </dev/null >/tmp/mps-client.log 2>&1 & \
	    disown 2>/dev/null || true; \
	    sleep 2; \
	    pid=$$(pgrep -f 'MultiplayerSample.GameLauncher' | head -1); \
	    echo "Windowed client PID: $$pid"; \
	    echo "Stdout log: /tmp/mps-client.log"

play-mps-stop:
	@pkill -f "MultiplayerSample\.(Game|Headless|Server)Launcher" 2>/dev/null || true
	@sleep 1
	@if pgrep -f "MultiplayerSample\.(Game|Headless|Server)Launcher" >/dev/null; then \
	    echo "Some processes still running:"; \
	    pgrep -af "MultiplayerSample\.(Game|Headless|Server)Launcher" | grep -v $$$$; \
	else \
	    echo "All MultiplayerSample processes stopped."; \
	fi

# End-to-end driver: build a snapshot RPM from <REF> and test it.
# Usage: make test-branch REF=stabilization/26100
test-branch:
	@[ -n "$(REF)" ] || { echo "usage: make test-branch REF=<git-ref>"; exit 2; }
	tests/test-branch.sh $(REF)

# ── 3rdParty dependency-drift audit ─────────────────────────────────────────

# Compare engine BuiltInPackages_linux_x86_64.cmake pins, our COPR
# o3de-dependencies versions, and o3de/3p-package-source build_config.json
# pins. Prints a Markdown table to stdout. Exits 1 if any "out-of-date"
# entries are found, 0 otherwise. The .github/workflows/check-deps-drift.yml
# runs this weekly and sticky-issues the result.
check-deps-drift:
	python3 tools/check-deps-drift.py

# ── qt6-merge watch ─────────────────────────────────────────────────────────

# Has the o3de/o3de qt6 branch merged into development yet? Watches the Linux
# x86_64 3rdParty Qt association for the Qt5 -> Qt6/PySide6 flip. Exit 0 =
# not-yet, 10 = MERGED (run the FOLLOW_UPS.md chroot flip before the next
# o3de-development cron), 2 = UNKNOWN (fetch/parse failed, re-probe). Outage is
# reported as UNKNOWN, never not-merged.
check-qt6-merge:
	python3 tools/check-qt6-merge.py

# qt6-merge-gate: safety interlock the development build targets run BEFORE
# firing a COPR build. If the qt6 branch has merged into o3de/development
# (probe exit 10) but the target project's chroots do NOT yet carry the `qt6`
# bcond, HARD-STOP -- otherwise the cron links against Qt6 without the qt6
# gates (dbus-devel BR, dangling-Requires excludes, PySide6 rpath cleanup) and
# fails at link or ships dangling requires. NOT-YET (exit 0) proceeds; an
# upstream fetch outage (exit 2, UNKNOWN) WARNS but proceeds -- outage is not
# drift (feedback_drift_detector_outage_vs_drift). See FOLLOW_UPS.md "TRIGGER:
# qt6 merges into o3de/development".
GATE_PROJECT ?= $(COPR_PROJECT_DEVELOPMENT)
qt6-merge-gate:
	@set -u; \
	python3 tools/check-qt6-merge.py; rc=$$?; \
	if [ $$rc -eq 0 ]; then \
	  echo "qt6-merge-gate: development still Qt5, proceeding."; \
	elif [ $$rc -eq 2 ]; then \
	  echo "qt6-merge-gate: WARNING -- probe UNKNOWN (could not verify upstream). Proceeding WITHOUT the gate; re-run 'make check-qt6-merge' once GitHub is reachable."; \
	elif [ $$rc -eq 10 ]; then \
	  echo "qt6-merge-gate: development is MERGED to Qt6 -- checking $(GATE_PROJECT) chroots for the qt6 bcond..."; \
	  missing=""; \
	  for ch in fedora-44-x86_64 fedora-rawhide-x86_64 centos-stream-10-x86_64; do \
	    opts=$$(copr-cli get-chroot $(COPR_OWNER)/$(GATE_PROJECT)/$$ch 2>/dev/null | python3 -c 'import sys,json; print(",".join(json.load(sys.stdin).get("with_opts",[])))' 2>/dev/null); \
	    case ",$$opts," in *,qt6,*) : ;; *) missing="$$missing $$ch";; esac; \
	  done; \
	  if [ -n "$$missing" ]; then \
	    echo "ERROR: qt6 has merged into development but these $(GATE_PROJECT) chroots lack the qt6 bcond:$$missing"; \
	    echo "Flip them BEFORE building (edit-chroot REPLACES -- pass the FULL list):"; \
	    for ch in $$missing; do \
	      echo "  copr-cli edit-chroot $(COPR_OWNER)/$(GATE_PROJECT)/$$ch --rpmbuild-with 'development_snapshot qt6'"; \
	    done; \
	    echo "Verify: copr-cli get-chroot $(COPR_OWNER)/$(GATE_PROJECT)/<chroot>"; \
	    echo "Runbook: FOLLOW_UPS.md 'TRIGGER: qt6 merges into o3de/development'."; \
	    exit 2; \
	  fi; \
	  echo "qt6-merge-gate: $(GATE_PROJECT) chroots already carry qt6, proceeding."; \
	else \
	  echo "qt6-merge-gate: WARNING -- unexpected probe exit $$rc; proceeding."; \
	fi

# ── Clean ───────────────────────────────────────────────────────────────────

clean:
	rm -rf ~/rpmbuild/BUILD ~/rpmbuild/BUILDROOT ~/rpmbuild/RPMS/x86_64/$(PKGNAME)-* ~/rpmbuild/SRPMS/$(PKGNAME)-*
