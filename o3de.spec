################################################################################
# O3DE (Open 3D Engine) RPM spec — Fedora 44 / rpm 4.20+
#
# Build the stable release (profile binaries only):
#     rpmbuild -bb \
#         --define "_sourcedir $PWD/sources" \
#         --define "_specdir   $PWD" \
#         o3de.spec
#
# Build with the debug subpackage too (opt-in, ~2x build time):
#     rpmbuild -bb --with debug \
#         --define "_sourcedir $PWD/sources" \
#         --define "_specdir   $PWD" \
#         o3de.spec
#
# Build for the community-tester channel (stabilization/<release> branch
# — what o3de-stabilization on COPR ships):
#     ./sources/make-snapshot-tarball.sh stabilization/26050
#     # paste the printed snapshot_commit / snapshot_date / snapshot_sha256
#     rpmbuild -bb --with snapshot --with stabilization ...
# Build a one-off from upstream's bleeding-edge `development` branch
# (or any specific commit — uploaded to o3de-snapshot, ad-hoc cadence):
#     ./sources/make-snapshot-tarball.sh development
#     rpmbuild -bb --with snapshot ...                # no `--with stabilization`
#     # into the macros below, copy the tarball to $PWD/sources, then:
#     rpmbuild -bb --with snapshot \
#         --define "_sourcedir $PWD/sources" \
#         --define "_specdir   $PWD" \
#         o3de.spec
#
# Build with selected O3DE 3rdParty packages bundled:
#     rpmbuild -bb --with thirdparty_physx --with thirdparty_openexr ...
#
# See README.md for the full pattern.
################################################################################

# ── Build-mode toggles ───────────────────────────────────────────────────────
%bcond_with snapshot
# Stabilization marks a snapshot as coming from upstream's stabilization/<X>
# branch (the pre-release branch that becomes the next tagged release).
# Set on the o3de-stabilization COPR project's chroots via --rpmbuild-with;
# the spec uses it only for the GUI channel marker (see _o3de_channel
# below) so testers can tell stabilization-channel builds apart from
# one-off development-branch builds (which use plain --with snapshot
# without --with stabilization, and ship to o3de-snapshot).
%bcond_with stabilization
# Experimental marks a snapshot as in-flight migration work shipping via the
# o3de-experimental COPR (NOT the stab tester channel or the stable channel).
# Set on o3de-experimental chroots via --rpmbuild-with; the spec uses it only
# for the GUI channel marker (see _o3de_channel below). This was previously
# inferred from "any system_* swap is active" but that inference broke when
# system swaps graduated from experimental to standard in the stab + stable
# channels too: it would force the -experimental marker on builds that were
# actually shipping to o3de-stabilization or hellaenergy/o3de.
%bcond_with experimental
# `--with debug` additionally builds the debug-config engine binaries and
# ships them as the `o3de-debug` subpackage. End-user game development
# only needs the profile config (the default), so building debug is opt-in
# to avoid roughly doubling build time and disk usage. Install both with
# `dnf install o3de o3de-debug` if you need to step through engine code.
%bcond_with debug

# Per-3rdParty-package toggles. Add more as you add Source10x lines below.
%bcond_with thirdparty_physx
%bcond_with thirdparty_openexr

# Stage 1 system-library swaps. Each `system_<lib>` toggle replaces an
# upstream-bundled 3rdParty package with its system equivalent (provided
# by Fedora's own repos, or by hellaenergy/o3de-dependencies on COPR for
# packages not yet in Fedora). All default-off; enable per-build via
# `--with system_<lib>` on the rpmbuild command line PLUS a matching
# `--rpmbuild-with system_<lib>` on the COPR project's chroots (the
# binary-build phase doesn't inherit `--with` from the SRPM build —
# see CONTRIBUTING.md / FEDORA_ROADMAP.md for the gotcha and the
# Makefile's `make copr-init` target for the chroot-config commands).
%bcond_with system_assimp
%bcond_with system_dxc
%bcond_with system_expat
%bcond_with system_freetype
%bcond_with system_googlebenchmark
%bcond_with system_libsamplerate
%bcond_with system_lua
%bcond_with system_lz4
%bcond_with system_mcpp
%bcond_with system_mikkelsen
%bcond_with system_openexr
%bcond_with system_png
%bcond_with system_poly2tri
%bcond_with system_spirvcross
%bcond_with system_sqlite
%bcond_with system_tiff
%bcond_with system_vulkan_validation_layers
%bcond_with system_zlib

# Snapshot-against-o3de/development builds must skip the carry-patches whose
# upstream equivalents have already landed in development. Each such patch is
# wrapped below in `%%if %%{without development_snapshot}` so its declaration
# (and %%autosetup application) drops out when this flag is set. Default OFF
# so stabilization / snapshot / experimental channels (which build against
# stabilization/26050, where these merges have NOT yet been cherry-picked)
# remain unchanged. Wired into the Makefile's `copr-snapshot-development`
# target only -- other ref-based snapshot builds (e.g., qt6) still apply
# every patch unless their own audit says otherwise. See
# project_branch_alignment_before_retirement.md for the gotcha pattern that
# motivated this gate.
%bcond_with development_snapshot

# ── Version pinning ──────────────────────────────────────────────────────────
%global stable_tag      2605.0
# Compute with: sha256sum o3de-<tag>-lfs.tar.gz  (2605.0+ naming convention;
# earlier releases used o3de_<tag>_lfs.tar.gz with underscores)
%global stable_sha256   f23c46eaf60fd7359279781f4abefa1b7f0d88091fd37ce9bff31431927c3f1e

# CMake's project(VERSION) and O3DE's cmake/Version.cmake split the
# version string by '.' and require MAJOR.MINOR.PATCH (3 components).
# stable_tag is YYMM.PATCH (2 components) — derive a 3-component form:
#   2605.0  →  26.05.0
#   2510.2  →  25.10.2
%global engine_cmake_version %(awk -F. '{ printf "%%d.%%02d.%%d", int($1/100), $1%%100, $2 }' <<< "%{stable_tag}")

# Versioned package layout (postgresql-style major-keyed naming + upstream-
# aligned install path). Lets multiple O3DE major releases coexist on one
# system: o3de2605 (26.05 line) at /opt/O3DE/26.05.0/, o3de2610 (26.10 line)
# at /opt/O3DE/26.10.0/, etc. Different majors = different engine lines = not
# auto-upgradable. The /opt/O3DE/<v>/ path matches upstream's .deb (Debian)
# and .msi (Windows) install layout exactly — cross-platform consistency.
#   stable_tag           2605.0  (or 2610.0, 2705.0, …)
#   o3de_major_tag       2605
#   o3de_pkgname         o3de2605
#   o3de_install_prefix  /opt/O3DE/26.05.0
%global o3de_major_tag      %(awk -F. '{ print $1 }' <<< "%{stable_tag}")
%global o3de_pkgname        o3de%{o3de_major_tag}
%global o3de_install_prefix /opt/O3DE/%{engine_cmake_version}

# Snapshot pin -- populated by sources/make-snapshot-tarball.sh.
# Pinned to stabilization/26050 tip for end-to-end build test.
#
# The %%{?!foo:%%global foo BAR} idiom makes each pin conditional:
# rpmbuild's --define on the command line takes precedence, the spec's
# defaults only apply if no --define was passed. Lets parameterized
# targets like `make srpm-snapshot-ref REF=qt6` override the snapshot
# pin via --define snapshot_commit=... without editing the spec.
%{?!snapshot_commit:%global snapshot_commit 8e750500f23c9c45f08266200463fd31996638b7}
%{?!snapshot_date:%global snapshot_date 20260523}
%{?!snapshot_sha256:%global snapshot_sha256 d6470fdb233b218c12c4ce23d6448927fe13be717e80a8b455fe1ef2040d64b2}
%global shortcommit %(c=%{snapshot_commit}; echo ${c:0:7})

# Channel-identifying suffix for the version strings the GUI displays.
# Without this, every build (stable / snapshot / experimental) shows
# "26.05.0" / "Version 2605.0" — a tester can't tell from the GUI which
# RPM they have. We compute one suffix here and apply it to BOTH
# DISPLAY_VERSION_STRING (PM titlebar via Patch0005) and BUILD_VERSION
# (Editor splash) so the two surfaces stay consistent.
#
# Channel marker, chosen in priority order:
#   experimental   --with experimental         (o3de-experimental chroots)
#   stabilization  --with stabilization        (o3de-stabilization chroots)
#   development    --with development_snapshot (o3de-development chroots --
#                  the default destination for snapshots from upstream's
#                  development branch; carry-patches already merged
#                  upstream are gated off when this bcond is set)
#   snapshot       --with snapshot only        (rare arbitrary-ref one-off
#                  builds going to a dedicated COPR project, e.g.
#                  hellaenergy/o3de-qt6 if a qt6 testing channel is set up)
#   (none)         no channel bcond set; tagged release going to hellaenergy/o3de
# Marker reflects the destination project's channel, not the feature set.
# Early Stage 1 work used to infer -experimental from "any system_<X>
# bcond is on" but that broke when system swaps graduated into stab + stable
# channels too (it would force -experimental on builds shipping to
# o3de-stabilization and to hellaenergy/o3de).
%global _o3de_channel %{nil}
%if %{with experimental}
%global _o3de_channel -experimental
%else
%if %{with stabilization}
%global _o3de_channel -stabilization
%else
%if %{with development_snapshot}
%global _o3de_channel -development
%else
%if %{with snapshot}
%global _o3de_channel -snapshot
%endif
%endif
%endif
%endif

# Commit marker (only meaningful in snapshot mode — stable mode pulls
# from a tagged release tarball, no per-build commit identification).
%if %{with snapshot}
%global _o3de_commit_marker .%{shortcommit}
%else
%global _o3de_commit_marker %{nil}
%endif

# Final display values:
#   _o3de_display_version  → PM titlebar      (e.g. "26.05.0-snapshot.246b46f")
#   _o3de_build_version    → Editor splash    (e.g. "2605.0-snapshot.246b46f")
# Both use the same channel + commit suffixes so testers see a coherent
# story; the numeric prefix differs because that's the established
# convention each surface uses (dotted vs compact 4-digit).
%global _o3de_display_version %{engine_cmake_version}%{_o3de_channel}%{_o3de_commit_marker}
%global _o3de_build_version   %{stable_tag}%{_o3de_channel}%{_o3de_commit_marker}

# Auto-detect snapshot mode when only the snapshot tarball is in _sourcedir.
# COPR's pipeline rebuilds the SRPM with `rpmbuild -bs` after upload, which
# evaluates the spec WITHOUT preserving the `--with snapshot` flag passed to
# our local SRPM build, and would otherwise look for the (non-shipped) stable
# tarball and fail. Skip the override if the user passed `--without snapshot`
# explicitly (they want stable mode even if the tarball happens to be there).
# Stable-mode SRPMs ship o3de_<tag>_lfs.tar.gz; snapshot-mode SRPMs ship
# o3de-<commit>.tar.gz; never both — so the file check is unambiguous.
%if %(test -f %{_sourcedir}/o3de-%{snapshot_commit}.tar.gz && echo 1 || echo 0)
%{!?_without_snapshot:%{!?with_snapshot:%global with_snapshot 1}}
%endif

%if %{with snapshot}
%global o3de_source_dir o3de-%{snapshot_commit}
%global o3de_source_sha %{snapshot_sha256}
%else
%global o3de_source_dir o3de
%global o3de_source_sha %{stable_sha256}
%endif

# ── RPM build behavior ───────────────────────────────────────────────────────
# debug_package is suppressed because rpmbuild's debug-symbol extraction
# trips on O3DE's binary layout. A real -debuginfo subpackage is on the
# Fedora-inclusion roadmap (see FEDORA_ROADMAP.md, stage 5).
%global debug_package %{nil}
%global _build_id_links none
%global __jar_repack 0

# Source payload uncompressed: the SRPM mostly carries the already-gzipped
# upstream o3de tarball, so re-compressing wastes CPU for ~zero size gain.
%global _source_payload w0.ufdio
# Binary payload: keep Fedora's default zstd-19. Earlier revisions of this
# spec set w0.ufdio here ("uncompressed, faster on slow disks") but that
# made the binary RPM ~3-4x bigger than necessary — the static .a archives
# and unstripped .so binaries that dominate the payload compress extremely
# well. Trade ~5 minutes of rpmbuild CPU for ~5 GB less for every install.

# Bundled Python series — comes from O3DE's package CDN's
# python-X.Y.Z-revN-linux tarball. Used for venv site-packages
# directory name and shebang fix-ups. Bump when O3DE bumps.
%global o3de_bundled_python 3.10

# DXC is structurally a fork of Clang/LLVM, so its bundled libdxcompiler.so
# links against its own internal libclang-12.so.1 (and transitively libtinfo)
# under Builders/DirectXShaderCompiler/lib/. RPATH resolves them; they never
# need to come from the system. Without this, auto-Requires demands
# libclang-12 (Fedora 44 ships clang 22) and a libtinfo with a versioned
# symbol that doesn't match the system's — `dnf install` fails with
# "nothing provides".
#
# This goes away when Stage 5 of FEDORA_ROADMAP.md ships a license-clean
# DXC rebuilt against system clang. Don't add new entries to this regex
# without checking — most Requires we'd want to drop are real.
%global __requires_exclude ^libclang-12\\.so.*|^libtinfo\\.so\\.6.*

Name:           %{o3de_pkgname}
%if %{with snapshot}
Version:        %{stable_tag}^%{snapshot_date}git%{shortcommit}
%else
Version:        %{stable_tag}
%endif
Release:        1%{?dist}
Summary:        Open 3D Engine — real-time, multi-platform 3D engine

License:        Apache-2.0 OR MIT
URL:            https://o3de.org

%if %{with snapshot}
Source0:        o3de-%{snapshot_commit}.tar.gz
%else
Source0:        https://github.com/o3de/o3de/releases/download/%{stable_tag}/o3de-%{stable_tag}-lfs.tar.gz
%endif

# Auxiliary sources kept alongside the spec.
Source10:       o3de-launcher.sh
Source11:       o3de.desktop
Source12:       make-snapshot-tarball.sh
Source13:       %{o3de_pkgname}.cdx.json
Source14:       o3de.metainfo.xml
# Standalone Editor entry. Visible in the menu as of 2026-05-24 to match
# the Windows installer's layout (PM + Editor + Material Editor + Material
# Canvas all visible). Previously NoDisplay=true.
Source15:       o3de-editor.desktop
# Thin wrapper exposing the engine's scripts/o3de.sh CLI on $PATH as
# %%{o3de_pkgname}-cli (versioned binary name; multiple installed majors
# get distinct PATH entries).
Source16:       o3de-cli
# Standalone Material Editor + Material Canvas menu entries. Added
# 2026-05-24 to match Windows where these tools have their own Start menu
# entries.
Source17:       o3de-material-editor.desktop
Source18:       o3de-material-canvas.desktop

# App icons in hicolor sizes. Per-tool series, each extracted from the
# corresponding upstream Windows .ico file (icotool -x). Matches the
# Windows installer's per-app icon assignment so Linux and Windows menus
# look identical:
#   o3de            -> ProjectManager-Icon.ico   (Code/Tools/ProjectManager/Resources/)
#   o3de-editor     -> o3de_editor.ico           (Code/Editor/res/)
#   o3de-material-editor -> MaterialEditor.ico   (Gems/Atom/Tools/MaterialEditor/Code/Source/Platform/Windows/)
#   o3de-material-canvas -> MaterialCanvas.ico   (Gems/Atom/Tools/MaterialCanvas/Code/Source/Platform/Windows/)
#                          (single-resolution upstream; resized to hicolor sizes via imagemagick)
Source20:       o3de-16x16.png
Source21:       o3de-32x32.png
Source22:       o3de-48x48.png
Source23:       o3de-64x64.png
Source24:       o3de-128x128.png
Source25:       o3de-256x256.png
Source50:       o3de-editor-16x16.png
Source51:       o3de-editor-32x32.png
Source52:       o3de-editor-48x48.png
Source53:       o3de-editor-64x64.png
Source54:       o3de-editor-128x128.png
Source55:       o3de-editor-256x256.png
Source56:       o3de-material-editor-16x16.png
Source57:       o3de-material-editor-32x32.png
Source58:       o3de-material-editor-48x48.png
Source59:       o3de-material-editor-64x64.png
Source60:       o3de-material-editor-128x128.png
Source61:       o3de-material-editor-256x256.png
Source62:       o3de-material-canvas-16x16.png
Source63:       o3de-material-canvas-32x32.png
Source64:       o3de-material-canvas-48x48.png
Source65:       o3de-material-canvas-64x64.png
Source66:       o3de-material-canvas-128x128.png
Source67:       o3de-material-canvas-256x256.png

# Patches against the upstream tree (apply with -p1).
# Patch0001 -- merged upstream as o3de/o3de#19748 (in development, NOT in
# stabilization/26050). Active for stabilization builds; gated off when
# building development snapshots so it doesn't fail-to-apply against a tree
# that already contains the change.
%if %{without development_snapshot}
Patch0001:      0001-clang21-warning-suppressions.patch
%endif
# Patch0002 -- merged upstream as o3de/o3de#19751 (development only).
%if %{without development_snapshot}
Patch0002:      0002-manifest-py-engine-path-detection.patch
%endif
Patch0003:      0003-get-python-sh-rpm-venv-fixes.patch
Patch0004:      0004-lypython-non-editable-pip-for-installed-engine.patch
# Patch0005 -- merged upstream as o3de/o3de#19750 (development only).
%if %{without development_snapshot}
Patch0005:      0005-windowdecorationwrapper-propagate-initial-title.patch
%endif

# Migrate every remaining legacy libtiff typedef use (uint8/uint16/uint32)
# to the standard C99 (`*_t`) names across O3DE's two <tiffio.h> consumers:
#   - Gems/Atom/Asset/ImageProcessingAtom/.../TIFFLoader.cpp (modern Atom)
#   - Code/Editor/Util/ImageTIF.cpp (legacy Editor)
# libtiff 4.5+ marks the legacy typedef as __attribute__((deprecated));
# combined with O3DE's -Werror, every stale use becomes a hard build
# failure. Mechanical type rename; behavior unchanged. Applies
# unconditionally so the source tree stays consistent whether libtiff
# resolves from the upstream CDN bundle or from system tiff-devel.
#
# TIMEBOMB: upstream MERGED PR o3de/o3de#19734 (commit dda736e0,
# 2026-05-08) into `development` but NOT into `stabilization/26050`.
# Our snapshot pin currently sources from stabilization/26050 (commit
# 246b46f), which still has the legacy typedefs. When stabilization
# absorbs #19734 (either via cherry-pick to 26050 or when a new
# stabilization branch is cut from development with #19734 in it),
# this patch becomes dead code and retires. Until then it must stay.
# Earlier-2026-05-12 retirement attempt was reverted after grepping
# stabilization/26050 still showed 9+33 legacy typedef hits in the
# two target files. See project_branch_alignment_before_retirement.md
# memory note for the gotcha pattern.
%if %{without development_snapshot}
Patch0007:      0007-libtiff-c99-typedefs.patch
%endif

# Stage 1 system-library swap patches — each gates one upstream
# ly_associate_package(...) line on a new LY_USE_SYSTEM_<X> cmake var,
# and pairs with a corresponding system Find<X>.cmake (Source30+ below).
#
# Patch0006 conflicts against o3de/development since 2026-03-10 because PR
# o3de/o3de#19365 ("Assimp as FetchPackage") removed the
# `assimp-5.4.3-rev3-linux` ly_associate_package line, which is one of the
# anchored lines Patch0006 expected. Stabilization/26050 still has the
# line, so the patch applies cleanly on the stabilization channel. Gated
# under %%without development_snapshot so dev-snapshot builds skip it; the
# o3de-snapshot COPR project intentionally has no `system_*` swaps active
# (see make-snapshot-tarball.sh + edit-chroot config) so the gate-flags
# aren't needed there anyway.
%if %{without development_snapshot}
Patch0006:      0006-builtinpackages-gate-mikkelsen-on-system.patch
%endif

# Drop AzCore's redundant `#include <Lua/lobject.h>` in ScriptContext.cpp.
# The only thing it pulls in is the `LUAI_MAXALIGN` macro, which is
# already public Lua API -- defined in `luaconf.h` and used in `lauxlib.h`'s
# `luaL_Buffer`. AzCore already includes <Lua/lualib.h> and <Lua/lauxlib.h>
# in the same extern "C" block, both of which transitively include
# luaconf.h, so LUAI_MAXALIGN is in scope without lobject.h. This is the
# single blocker for system_lua activation on Fedora (Fedora's lua-devel
# only ships the public API headers -- lua.h, lualib.h, lauxlib.h,
# luaconf.h -- never lobject.h, lstate.h, etc.). Behavior-preserving.
# Applies unconditionally -- bundled-Lua builds also benefit (one fewer
# brittle internal-header dependency).
#
# TIMEBOMB: upstream MERGED PR o3de/o3de#19733 (commit 3e715c61,
# 2026-05-08) into `development` but NOT into `stabilization/26050`.
# Same retirement-gating story as Patch0007 -- stays active until
# stabilization absorbs the upstream change. See
# project_branch_alignment_before_retirement.md memory note.
%if %{without development_snapshot}
Patch0008:      0008-azcore-drop-lua-lobject-include.patch
%endif

# Gate poly2tri's bundled fetcher in the PhysX Gem PAL files (PhysX4 + PhysX5,
# Linux x86_64) on `LY_USE_SYSTEM_POLY2TRI`. Pairs with Findpoly2tri-system.cmake
# (Source40). poly2tri's bundle anchor lives in PhysX-Gem-internal PAL files
# rather than the standard `cmake/3rdParty/Platform/Linux/BuiltInPackages…`,
# so this gate ships as its own patch instead of extending Patch0006.
# Engine consumes only the public p2t:: namespace API
# (Gems/PhysX/Core/Code/Editor/PolygonPrismMeshUtils.h triangulates 2D
# polygons for polygon-prism shape colliders); no internal-symbol coupling.
# Fedora's poly2tri-devel ships from Mason Green's BSD-3-Clause original tree —
# license-clean and independent of the bundled fork's attribution issue.
# Applies unconditionally; bundled-poly2tri builds also benefit from a
# uniform LY_USE_SYSTEM_<X> gate convention.
#
# TIMEBOMB: this patch has hunks against BOTH PhysX4 AND PhysX5 PAL_linux.cmake.
# o3de/o3de PR #19726 (PhysX 4 retirement) has now landed in o3de/development
# (verified 2026-05-21: Gems/PhysX/Core/PhysX4/ tree gone). The PhysX4 hunk
# fails-to-apply on dev tip. Stabilization/26050 still has PhysX4, so the
# patch applies cleanly there. Gated under %%without development_snapshot.
# Eventual proper fix when stabilization absorbs the PhysX4 retirement:
# drop the PhysX4 hunk from this patch and regenerate with only PhysX5.
%if %{without development_snapshot}
Patch0009:      0009-physx-pal-gate-poly2tri-on-system.patch
%endif

# Lua 5.5 added a required third parameter to `lua_newstate` (a hash-seed
# randomization parameter). Engine's ScriptContext.cpp:4359 still calls
# the 5.4 two-arg form, which fails compilation on any distro shipping
# Lua 5.5+. Patch wraps the call in a `#if LUA_VERSION_NUM >= 505` guard
# that passes seed=0 on Lua 5.5+ and falls through to the original
# two-arg form on Lua 5.4. Applies unconditionally; behavior-preserving
# on Lua 5.4 (the #if branch evaluates false) so bundled-Lua builds are
# unaffected. Caught on COPR build 10436540 (o3de-experimental 14-pack
# fedora-rawhide chroot, 2026-05-08); Fedora 44 still ships Lua 5.4.8
# so the issue is rawhide-only at present, but every distro on rawhide's
# Lua 5.5 trajectory (Fedora 45+, Debian unstable, Alpine edge, Arch)
# will hit it.
Patch0010:      0010-azcore-script-lua-5-5-newstate-signature-compat.patch

# Sibling Lua 5.5 compat fix to Patch0010, but in a different file
# (Code/Tools/LuaIDE/Source/LUA/WatchesPanel.cpp). Lua 5.5 dropped the
# LUA_NUMTAGS public macro that 5.4 retained as a deprecation-alias for
# LUA_NUMTYPES; this patch restores the alias on 5.5+ via a one-line
# `#define LUA_NUMTAGS LUA_NUMTYPES` near the lua.h include so the two
# existing call sites compile unchanged. Behavior-preserving on Lua 5.4
# (the #if branch evaluates false and the upstream alias is in scope).
# Caught on COPR build 10437498 (o3de-experimental, fedora-rawhide
# chroot, 2026-05-08); Patch0010 alone wasn't sufficient because the
# LuaIDE compile happens later in the build than ScriptContext.cpp.
# Memory: project_lua_5_5_newstate_break.md.
Patch0011:      0011-luaide-watchespanel-lua-5-5-numtags-compat.patch

# Patch0012 v2 -- AssetBuilder child-side parent-death watchdog.
#
# Original v1 attempt (2605.0-50) enabled the engine's existing
# m_tetherLifetime mechanism, which uses prctl(PR_SET_PDEATHSIG, SIGTERM)
# on Linux. Built clean but on runtime test every spawned AssetBuilder
# received SIGTERM within ~21 ms of fork: the kernel binds PDEATHSIG to
# the THREAD that called fork(), not the parent PROCESS, and
# BuilderManager forks builders from short-lived TaskWorker threads.
# Documented in detail in project_prctl_pdeathsig_thread_gotcha.md.
#
# v2 (this patch) takes a child-side approach: AssetBuilder's main()
# starts a detached watchdog thread that polls getppid() every 2
# seconds; when the parent PID changes (reparented to PID 1 / systemd-
# user because AP died), the builder _exit(0)'s cleanly. Independent of
# the launching thread's lifetime; ~12 LOC of watchdog + ~5 LOC of
# call-in; POSIX (Linux/Mac) implementation only (Windows port can
# follow).
#
# Original v1 patch file 0012-assetprocessor-tether-resident-builders.patch
# is retained in sources/ as a reference for the failed approach.
# Memory: project_assetbuilder_orphan_lifecycle_bug.md +
# project_prctl_pdeathsig_thread_gotcha.md.
#
# Merged upstream as o3de/o3de#19747 (in development, NOT in stabilization/26050).
%if %{without development_snapshot}
Patch0012:      0012-v2-assetbuilder-parent-watchdog.patch
%endif

# Patch0013 -- Stage 1 system_vulkan_validation_layers swap.
# Gates the bundled vulkan-validationlayers ly_associate_package line
# on a new LY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS cmake variable AND
# fixes a companion VK_LAYER_PATH-overwrite bug in
# Gems/Atom/RHI/Vulkan/.../Instance.cpp so that distro-packager-set
# VK_LAYER_PATH (pointing at system loader paths like
# /usr/share/vulkan/explicit_layer.d) is respected. The two changes
# travel together because the cmake gate alone leaves engine code
# clobbering the system VK_LAYER_PATH. Validation layers are
# runtime-only (no headers, no compile-time linkage); Fedora's
# vulkan-validation-layers ships
# /usr/lib64/libVkLayer_khronos_validation.so +
# /usr/share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json.
# Pitched upstream for the convention to land cleanly.
#
# Patch0013's third hunk (against BuiltInPackages_linux_x86_64.cmake)
# hits the same context-drift as Patch0006: o3de/o3de#19365 ("Assimp
# as FetchPackage") shifted line numbers and changed surrounding
# context. Stabilization/26050 still has the original layout, so all
# three hunks apply cleanly there. Gated under %%without
# development_snapshot for the same reason as Patch0006.
%if %{without development_snapshot}
Patch0013:      0013-vulkan-validationlayers-gate-on-system.patch
%endif

# Stage 1 system-library find modules. Copied into cmake/3rdParty/
# during %%prep when the matching `--with system_<lib>` is enabled.
# Most Stage 1 swaps don't need a custom find module (cmake ships
# stock ones for ZLIB / Freetype / PNG / TIFF / Lua, so Patch0006's
# else-branch directly calls find_package and aliases the result).
# These two are exceptions:
#   - Findmikkelsen-system.cmake — mikkelsen has no cmake-stock find
#     module; the shim locates system mikktspace and bridges the
#     <mikkelsen/mikktspace.h> include path.
#   - Findexpat-system.cmake — case-bridging. Some bundled find files
#     (notably openimageio-opencolorio's FindOpenColorIO.cmake) call
#     find_package(expat) lowercase, which won't find cmake's stock
#     uppercase FindEXPAT.cmake on a case-sensitive filesystem. The
#     shim is named Findexpat.cmake and delegates to FindEXPAT.
Source30:       Findmikkelsen-system.cmake
Source31:       Findexpat-system.cmake
Source32:       FindZLIB-system.cmake
Source33:       FindFreetype-system.cmake
Source34:       FindPNG-system.cmake
Source35:       FindTIFF-system.cmake
Source36:       FindLua-system.cmake
Source37:       Findlz4-system.cmake
Source38:       FindOpenEXR-system.cmake
Source39:       FindImath-system.cmake
Source40:       Findpoly2tri-system.cmake
Source41:       FindSQLite-system.cmake
Source42:       Findlibsamplerate-system.cmake
Source43:       Findassimp-system.cmake
Source44:       Findmcpp-system.cmake
Source45:       FindGoogleBenchmark-system.cmake

# Pre-built O3DE 3rdParty bundles — declare a Source10x and a matching
# bcond above, then add an extract line in %%prep. Templates:
#Source101:      physx-5.1.1-rev1-linux.tar.xz
#Source102:      openexr-3.2.4-rev1-linux.tar.xz

ExclusiveArch:  x86_64 aarch64

# ── Build dependencies ───────────────────────────────────────────────────────
# O3DE bundles its own Qt 5.15-rev9, OpenSSL, zlib, freetype, OpenEXR,
# Python 3.10, etc. from its package CDN — those are NOT system BRs even
# though the engine's auto-Requires picks up the bundled libQt5*.so.5,
# libpython3.10.so.1.0, etc. (resolved internally via Provides:).
BuildRequires:  cmake
BuildRequires:  ninja-build
# Clang is the validated toolchain. Patch0001 specifically targets
# clang 21+ warnings-as-errors, and the engine's bundled FetchContent
# subprojects (libogg's CheckSizes etc.) have been observed to break
# under GCC's stricter Fedora hardening defaults. CC/CXX are forced to
# clang in %%build below to match. gcc-c++ stays in BR because some
# host-build tools (ispc, pre-built shaders) still expect a GCC stub.
BuildRequires:  clang
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  python3-devel
# `python3 setup.py sdist` (used in %%build to pre-build the three Python
# packages O3DE would otherwise pip-install editable into the read-only
# engine root — see Patch0004) requires setuptools at host build time.
# Local Fedora pulls it transitively via the workstation Python stack;
# COPR mock chroots are minimal and only install explicit BuildRequires.
# pip + wheel are defensive — newer setuptools sometimes invokes them
# via the PEP 517 build path even for `setup.py sdist`.
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

# Graphics / windowing — system OpenGL + X11/XCB stack the bundled Qt
# links against at runtime.
BuildRequires:  pkgconfig(gl)
BuildRequires:  pkgconfig(glu)
BuildRequires:  pkgconfig(x11)
BuildRequires:  pkgconfig(xcb)
BuildRequires:  libXcursor-devel
BuildRequires:  libXi-devel
BuildRequires:  libXinerama-devel
BuildRequires:  libXrandr-devel
BuildRequires:  xcb-util-devel
BuildRequires:  xcb-util-image-devel
BuildRequires:  xcb-util-keysyms-devel
BuildRequires:  xcb-util-renderutil-devel
BuildRequires:  xcb-util-wm-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  libxkbcommon-x11-devel

# System libs — validated against auto-Requires from the built binaries.
BuildRequires:  pkgconfig(fontconfig)
BuildRequires:  pkgconfig(libunwind)
BuildRequires:  pkgconfig(libzstd)

# libatomic dev symlink. F44+rawhide ship the `libatomic.so` symlink
# inside the base `libatomic` (or `libatomic-static`) package and the
# linker finds it automatically. CS10 with the gcc-toolset-15 SCL puts
# its SCL-prefixed linker on the build path, and the SCL's linker can't
# resolve `-latomic` from the base CS10 install -- the symlink under
# /opt/rh/gcc-toolset-15/root/usr/lib64/libatomic.so isn't shipped by
# the SCL's runtime package. Pulling the SCL's -libatomic-devel pulls
# in the missing symlink. Gated on %%{?rhel} so we don't add the
# package to Fedora chroots that don't need it (or have it named
# differently).
# Reference: COPR build 10447331 CS10 chroot, first time CS10 got past
# dnf-builddep -- failed at libAzCore.so link step with
# "ld: cannot find -latomic". See
# project_cs10_engine_build_blockers.md, blocker #5.
%if 0%{?rhel}
BuildRequires:  gcc-toolset-15-libatomic-devel
%endif

# Vulkan — engine dlopen()s the loader, but headers/loader-devel are
# needed at configure time for find_package(Vulkan).
BuildRequires:  vulkan-headers
BuildRequires:  vulkan-loader-devel

# Stage 1 system-library swaps — only pulled in when the matching
# bcond is enabled (--with system_<lib>). Most live in Fedora proper
# already (zlib-devel, freetype-devel, libpng-devel, libtiff-devel,
# expat-devel, lua-devel); mikkelsen lives in hellaenergy/o3de-dependencies
# on COPR until it's accepted into Fedora.
%if %{with system_assimp}
BuildRequires:  assimp-devel
%endif
%if %{with system_dxc}
# Stage 2 binary-only dependency: o3de2605-dxc-spirv from
# hellaenergy/o3de-dependencies COPR (sibling project, auto-enabled
# alongside this one). Ships /usr/bin/dxc, /usr/bin/dxsc,
# /usr/lib64/libdxcompiler.so. The %%install step below symlinks the
# engine's expected runtime paths
# (Builders/DirectXShaderCompiler/{bin/dxc,bin/dxsc,lib/libdxcompiler.so}
# under the install prefix) to the system locations, so the engine's
# asset-build pipeline shells out to the system binary instead of the
# bundled fetch. Versioned-major naming: o3de2605-dxc-spirv covers the
# whole 26.05.x line (matches the engine package's o3de2605 convention);
# a future o3de2610-dxc-spirv co-exists in the same COPR project for
# the 26.10.x line. Memory: project_o3de_3p_versioning_research.md.
BuildRequires:  o3de2605-dxc-spirv
%endif
%if %{with system_expat}
BuildRequires:  expat-devel
%endif
%if %{with system_freetype}
BuildRequires:  freetype-devel
%endif
%if %{with system_googlebenchmark}
# Stage 1 swap: replace the bundled googlebenchmark-1.7.0-rev1-linux
# tarball fetch with Fedora's google-benchmark-devel (currently 1.9.5 in
# F44). gbench is a build+ship dep of the engine even when our spec sets
# LY_DISABLE_TEST_MODULES=ON: AzTestRunner + AzTest ship unconditionally
# so external gem developers can write benchmarks against them. Per
# project_az_test_runner_architecture.md, this design intent was
# confirmed by Nick_L on PR #19738. Static->shared linkage variance is
# expected; Fedora's package ships only libbenchmark.so (no -static
# subpackage), so AzTestRunner ends up dynamically linked rather than
# having gbench compiled in.
BuildRequires:  google-benchmark-devel
%endif
%if %{with system_libsamplerate}
BuildRequires:  libsamplerate-devel
%endif
%if %{with system_mcpp}
# Stage 2 library-link dependency: o3de2605-mcpp-az from
# hellaenergy/o3de-dependencies COPR (sibling project, auto-enabled
# alongside this one). Library-link variant of the DXC-class binary-only
# pattern. Ships /usr/lib64/libmcpp.so + /usr/include/mcpp_lib.h via the
# -devel subpackage; the engine #includes <mcpp_lib.h> and links into
# the binary at build time. License-clean rebuild of upstream mcpp 2.7.2
# (BSD-2-Clause, abandonware-class) + o3de/3p-package-source's _az.2
# patch series. Versioned-major naming -- see system_dxc block above.
BuildRequires:  o3de2605-mcpp-az-devel
%endif
%if %{with system_lua}
BuildRequires:  lua-devel
%endif
%if %{with system_lz4}
BuildRequires:  lz4-devel
%endif
%if %{with system_mikkelsen}
BuildRequires:  mikkelsen-devel
%endif
%if %{with system_openexr}
BuildRequires:  openexr-devel
BuildRequires:  imath-devel
%endif
%if %{with system_png}
BuildRequires:  libpng-devel
%endif
%if %{with system_poly2tri}
BuildRequires:  poly2tri-devel
%endif
%if %{with system_sqlite}
BuildRequires:  sqlite-devel
%endif
%if %{with system_spirvcross}
# Stage 2 binary-only dependency: o3de2605-spirv-cross from
# hellaenergy/o3de-dependencies COPR (sibling project, auto-enabled
# alongside this one). Ships /usr/bin/spirv-cross. The %%install step
# below symlinks the engine's expected runtime path
# (Builders/SPIRVCross/spirv-cross under the install prefix) to
# /usr/bin/spirv-cross, so the engine's asset-build pipeline shells
# out to the system binary instead of the bundled fetch. Versioned-major
# naming -- see system_dxc block above.
BuildRequires:  o3de2605-spirv-cross
%endif
%if %{with system_tiff}
BuildRequires:  libtiff-devel
%endif
%if %{with system_vulkan_validation_layers}
# No BuildRequires -- validation layers are runtime-only (no headers,
# no compile-time linkage). The Patch0013 cmake gate skips the
# bundled package fetcher; the engine never find_packages or
# target_link_libraries against the validation layers (they are
# loader-discovered at runtime). vulkan-validation-layers-devel does
# not exist in Fedora for the same reason.
%endif
%if %{with system_zlib}
BuildRequires:  zlib-devel
%endif

# ── Runtime dependencies ─────────────────────────────────────────────────────
# RPM auto-Requires picks up every actual link target by walking the
# binaries with ldd. Only declare what auto-Requires can't see:
#   - mesa-libGL provides libGL.so.1 / libGLX.so.0 / libOpenGL.so.0 (auto-detected)
#     but we list it explicitly so plain `dnf install o3de` resolves cleanly.
#   - cmake is invoked by /usr/bin/o3de (the launcher wrapper) for engine-id
#     calculation; it's a shell-script dep that auto-Requires won't see.
#   - vulkan-loader provides libvulkan.so.1; the engine dlopen()s it at runtime,
#     so auto-Requires (which scans dynamic linker tables) misses it.
# Everything else (Qt5*, libxcb-*, libxkbcommon, fontconfig, freetype,
# libunwind, libzstd, libatomic, libpython3.10, libpyside2, …) comes
# from auto-Requires walking /opt/o3de/.
Requires:       mesa-libGL
Requires:       vulkan-loader
Requires:       python3
# cmake is Recommends, not Requires: the launcher uses cmake -P to compute
# the engine-path-id (which keys the per-user Python venv). The detection
# chain in sources/o3de-launcher.sh tries (1) system cmake on PATH, (2)
# bundled cmake at <engineRoot>/cmake/runtime/bin/cmake (not currently
# shipped — placeholder for future), (3) graceful degrade with empty
# ENGINE_ID (engine still runs; per-engine venv functionality degrades
# silently). Default install pulls cmake; minimal installs can opt out
# via `dnf install --setopt=install_weak_deps=False`.
Recommends:     cmake

# Stage 1 system-library runtime side. RPM auto-Requires picks up the
# .so.N dependencies by ldd-walking engine binaries, but listing the
# package names explicitly is clearer for reviewers (and survives if a
# future build statically links and the auto-dep disappears).
%if %{with system_assimp}
Requires:       assimp
%endif
%if %{with system_dxc}
Requires:       o3de2605-dxc-spirv
%endif
%if %{with system_expat}
Requires:       expat
%endif
%if %{with system_freetype}
Requires:       freetype
%endif
%if %{with system_googlebenchmark}
Requires:       google-benchmark
%endif
%if %{with system_libsamplerate}
Requires:       libsamplerate
%endif
%if %{with system_mcpp}
Requires:       o3de2605-mcpp-az
%endif
%if %{with system_lua}
Requires:       lua-libs
%endif
%if %{with system_mikkelsen}
Requires:       mikkelsen
%endif
%if %{with system_png}
Requires:       libpng
%endif
%if %{with system_poly2tri}
Requires:       poly2tri
%endif
%if %{with system_sqlite}
Requires:       sqlite-libs
%endif
%if %{with system_spirvcross}
Requires:       o3de2605-spirv-cross
%endif
%if %{with system_lz4}
Requires:       lz4-libs
%endif
%if %{with system_openexr}
Requires:       openexr-libs
Requires:       imath
%endif
%if %{with system_tiff}
Requires:       libtiff
%endif
%if %{with system_vulkan_validation_layers}
Requires:       vulkan-validation-layers
%endif
%if %{with system_zlib}
Requires:       zlib
%endif

# Provide the unversioned `o3de` capability so external packages with a
# legacy `Requires: o3de` keep resolving against whichever versioned
# package is installed (o3de2605, o3de2610, …). Each versioned package
# Provides this; dnf's normal capability-resolution picks one. Note: this
# is NOT a meta-package — there is no unversioned `o3de` package to
# `dnf install o3de` against; users must explicitly type `dnf install
# o3de2605` (or whatever major they want).
Provides:       o3de = %{version}-%{release}

# ── Project-build dependencies (weak deps) ───────────────────────────────────
# Surfaced 2026-05-04 by Mike Cromer (O3DE sig-build chair) on a clean
# Fedora 44 install: `dnf install o3de2605` succeeded and Project Manager
# launched, but compiling a user project from source via
# `o3de2605-cli create-project ... && cmake -B build/linux -S .`
# required ~13 additional *-devel packages (the same set we BuildRequires
# for our own engine build, just on the user's side now).
#
# These are Recommends, not Requires, on purpose: a user installing
# o3de2605 just to launch Project Manager and run pre-built games
# doesn't need *-devel headers. dnf installs them by default; users who
# only want runtime can `dnf install --setopt=install_weak_deps=False`.
#
# Note: the %%{name}-devel subpackage (which carries engine static
# archives for native C++ gem development) is a separate concern — it
# does NOT cover these project-build deps. Project-build deps stay as
# Recommends on the main package so they're installed by default for
# typical project authors, regardless of whether they install -devel.
#
# What we're listing — and why each is here:
#   - clang: O3DE projects compile with clang on Linux
#   - mesa-libGL-devel + mesa-libGLU-devel: OpenGL headers
#   - libxcb-devel: XCB (X11 protocol bindings)
#   - libxkbcommon-devel + libxkbcommon-x11-devel: keyboard layout headers
#   - fontconfig-devel: font config headers
#   - libunwind-devel: stack unwinding headers
#   - libzstd-devel: zstd compression headers
#   - libcurl-devel + pcre2-devel + openssl-devel: O3DE bundles its own
#     copies, but consumer projects often link their own code against
#     these and need system headers (Mike's clean-install findings)
#   - zlib-devel: same — also already a BuildRequires when system_zlib
#     is active, listed here unconditionally for the user-build case
#   - vim-common: provides /usr/bin/xxd, which O3DE's build invokes
#     to embed binary blobs as C arrays
Recommends:     clang
Recommends:     mesa-libGL-devel
Recommends:     mesa-libGLU-devel
Recommends:     libxcb-devel
Recommends:     libxkbcommon-devel
Recommends:     libxkbcommon-x11-devel
Recommends:     fontconfig-devel
Recommends:     libunwind-devel
Recommends:     libzstd-devel
Recommends:     libcurl-devel
Recommends:     pcre2-devel
Recommends:     openssl-devel
Recommends:     zlib-devel
Recommends:     vim-common

# Stage 1 system-library swap activations also expose their *-devel as
# project-build dependencies. When `--with system_<X>` is on, the engine's
# cmake exports point at the system library path, so user projects need
# the matching -devel headers to compile against the engine. Without these,
# user-project cmake configure fails with "find_package(<X>) — Could NOT
# find <X>" or compile-time "fatal error: <header> not found".
#
# Surfaced 2026-05-04 by Mike Cromer for mikkelsen specifically (the
# system-mikkelsen swap was promoted in 10422296; user-project build
# needed mikkelsen-devel that the bundled 3p doesn't satisfy). Same
# logic applies to the other 4 swaps after 10423836 promotes.
%if %{with system_assimp}
Recommends:     assimp-devel
%endif
%if %{with system_expat}
Recommends:     expat-devel
%endif
%if %{with system_freetype}
Recommends:     freetype-devel
%endif
%if %{with system_libsamplerate}
Recommends:     libsamplerate-devel
%endif
%if %{with system_lz4}
Recommends:     lz4-devel
%endif
%if %{with system_mikkelsen}
Recommends:     mikkelsen-devel
%endif
%if %{with system_openexr}
Recommends:     openexr-devel
Recommends:     imath-devel
%endif
%if %{with system_png}
Recommends:     libpng-devel
%endif
%if %{with system_poly2tri}
Recommends:     poly2tri-devel
%endif
%if %{with system_sqlite}
Recommends:     sqlite-devel
%endif
%if %{with system_tiff}
Recommends:     libtiff-devel
%endif
%if %{with system_lua}
Recommends:     lua-devel
%endif
%if %{with system_googlebenchmark}
Recommends:     google-benchmark-devel
%endif
%if %{with system_mcpp}
# Stage 2 library-link swap: end-user cmake-configure of native projects
# needs mcpp_lib.h headers via Findmcpp-system.cmake. The Requires line
# below pulls in libmcpp.so.0 (runtime); this Recommends pulls in the
# headers for project-build use. (dxc + spirvcross are binary shellouts
# -- no header surface for downstream consumers -- so they don't need
# parallel -devel Recommends entries.)
Recommends:     o3de2605-mcpp-az-devel
%endif

%description
The Open 3D Engine (O3DE) is an Apache-licensed, real-time, multi-platform
3D engine for building AAA games, cinema-quality 3D worlds, and
high-fidelity simulations.

This package ships the profile-config engine binaries, which is what
end-user game development needs. To step through engine code in a
debugger, additionally install %{name}-debug.

%if %{with snapshot}
This build is a development snapshot at commit %{shortcommit} (%{snapshot_date}).
%endif

%package devel
Summary:        Open 3D Engine — static archives for native C++ development
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
Static archives (.a) for native C++ development against the Open 3D
Engine. Install this in addition to %{name} when writing native gems
with O3DE-specific APIs that need static linking against engine
internals, or when building the engine's own static-only test
infrastructure.

End users running games, Lua/ScriptCanvas project authors, and most
native C++ project authors do NOT need this package — the main
%{name} runtime ships engine .so's and the per-target cmake config
files those projects link against. Install %{name}-devel only if
your project's cmake configure errors with `IMPORTED_LOCATION not
found` on a static-archive path under %{o3de_install_prefix}/lib/
or %{o3de_install_prefix}/lib64/.

The %{name}-devel package contains:
  - %{o3de_install_prefix}/lib/Linux/profile/Default/*.a — engine static
    archives (~4 GB, 173 files): AzCoreTestCommon, AzGameFramework,
    AzManipulatorTestFramework, AzNetworking, AzTest, RecastNavigation
    helpers, gem builders, etc. Mostly testing/builder targets and
    static-only engine internals.
  - %{o3de_install_prefix}/lib64/ — Recast/Detour bundled static archives
    (~2 MB, from the RecastNavigation gem) plus their pkgconfig files.

Splitting these out roughly halves the on-disk size of %{name} for
runtime-only users, CI test containers, and game distribution servers
where static-link development against the engine isn't needed.

%if %{with debug}
%package debug
Summary:        Open 3D Engine — debug-config binaries
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description debug
Debug-config (-O0 + full debug symbols) binaries for the Open 3D Engine.

These binaries live alongside the profile binaries shipped by the main
%{name} package, under %{o3de_install_prefix}/bin/Linux/debug/. Install
this package when you need to step through engine internals in a
debugger; for plain game development the profile build in %{name} is
sufficient.

Set O3DE_BUILD_CONFIG=debug in the environment, or pass `--build-config
debug` to %{_bindir}/%{name}, to launch the debug engine in place of
profile.
%endif

# ── PREP ─────────────────────────────────────────────────────────────────────
%prep
# Source integrity check before extraction.
echo "%{o3de_source_sha}  %{SOURCE0}" | sha256sum -c -

# Tarball-layout selector (avoid rpm-macro syntax in this comment;
# rpm's parser expands macros inside comments and an earlier draft of
# this block accidentally invoked autosetup via comment text):
#   Snapshot tarballs from make-snapshot-tarball.sh wrap content in
#     a versioned directory (e.g., o3de-<commit>/), so the standard
#     autosetup with -n pointed at that name works.
#   Stable release tarballs starting with 2605.0 ship content directly
#     at the root (no wrapping directory); earlier releases (2510.x
#     and prior) wrapped in o3de/. The -c flag on autosetup creates
#     the named dir and chdirs into it before extraction, which is
#     exactly the shape the 2605.0 tarball expects.
%if %{with snapshot}
%autosetup -n %{o3de_source_dir} -p1
%else
%autosetup -c -n %{o3de_source_dir} -p1
%endif

# Pre-populate LY_3RDPARTY_PATH from bundled 3rdParty source tarballs.
%if %{with thirdparty_physx} || %{with thirdparty_openexr}
mkdir -p %{_builddir}/%{o3de_source_dir}/3rdParty
%endif
%{?with_thirdparty_physx:tar -xf %{SOURCE101} -C %{_builddir}/%{o3de_source_dir}/3rdParty}
%{?with_thirdparty_openexr:tar -xf %{SOURCE102} -C %{_builddir}/%{o3de_source_dir}/3rdParty}

# Stage 1 system-library find modules. Patch0006 already gates the
# upstream ly_associate_package(...) line on LY_USE_SYSTEM_<X>; we
# additionally drop a Find<X>.cmake into cmake/3rdParty/ so that when
# the gate flips, cmake's standard find_package() pathway resolves the
# 3rdParty::<X> target from the system library.
%if %{with system_mikkelsen}
cp %{SOURCE30} cmake/3rdParty/Findmikkelsen.cmake
%endif
%if %{with system_expat}
cp %{SOURCE31} cmake/3rdParty/Findexpat.cmake
%endif
%if %{with system_zlib}
cp %{SOURCE32} cmake/3rdParty/FindZLIB.cmake
%endif
%if %{with system_freetype}
cp %{SOURCE33} cmake/3rdParty/FindFreetype.cmake
%endif
%if %{with system_png}
cp %{SOURCE34} cmake/3rdParty/FindPNG.cmake
%endif
%if %{with system_tiff}
cp %{SOURCE35} cmake/3rdParty/FindTIFF.cmake
%endif
%if %{with system_lua}
cp %{SOURCE36} cmake/3rdParty/FindLua.cmake
%endif
%if %{with system_lz4}
cp %{SOURCE37} cmake/3rdParty/Findlz4.cmake
%endif
%if %{with system_openexr}
cp %{SOURCE38} cmake/3rdParty/FindOpenEXR.cmake
cp %{SOURCE39} cmake/3rdParty/FindImath.cmake
%endif
%if %{with system_poly2tri}
cp %{SOURCE40} cmake/3rdParty/Findpoly2tri.cmake
%endif
%if %{with system_sqlite}
cp %{SOURCE41} cmake/3rdParty/FindSQLite.cmake
%endif
%if %{with system_libsamplerate}
cp %{SOURCE42} cmake/3rdParty/Findlibsamplerate.cmake
%endif
%if %{with system_assimp}
cp %{SOURCE43} cmake/3rdParty/Findassimp.cmake
%endif
%if %{with system_mcpp}
cp %{SOURCE44} cmake/3rdParty/Findmcpp.cmake
%endif
%if %{with system_googlebenchmark}
cp %{SOURCE45} cmake/3rdParty/FindGoogleBenchmark.cmake
%endif

# ── BUILD ────────────────────────────────────────────────────────────────────
%build
mkdir -p build

# O3DE sets its own _FORTIFY_SOURCE / -fstack-protector / -fvisibility etc.
# in cmake/Platform/Common/Configurations_*.cmake. Fedora's CFLAGS bundle
# layers a different set on top and trips the engine's -Werror. LDFLAGS
# pulls in /usr/lib/rpm/redhat/redhat-annobin-cc1 specs which expect a
# GCC plugin that clang doesn't have, breaking cmake compiler-feature
# tests (FindThreads, libogg CheckSizes). Drop all three; O3DE's own
# Configurations_*.cmake supplies the equivalents (RELRO, BIND_NOW,
# stack-protector, _FORTIFY_SOURCE).
unset CFLAGS CXXFLAGS LDFLAGS

%if %{with debug}
%global _o3de_configs profile;debug
%else
%global _o3de_configs profile
%endif

# FindThreads' compiler feature-tests false-fail when O3DE's bundled qt5
# .prl processing triggers find_package(Threads) re-entry. Force the
# pthread result so configure proceeds.
#
# O3DE_INSTALL_ENGINE_NAME=o3de (NOT %{o3de_pkgname}): the engine.json
# engine_name field is a SEPARATE identity from the RPM package name.
#   - The versioned RPM name (o3de2605) handles dnf's package identity
#     (multi-major install, dnf swap, dnf remove).
#   - engine.json's engine_name is what gem manifests' compatible_engines
#     list matches against. Third-party gems hard-code "o3de" or
#     "o3de-sdk" in their compatible_engines (e.g. WarehouseAssets:
#     ["o3de-sdk>=2.3.0", "o3de>=2.3.0"]). If we set engine_name to
#     "o3de2605", PM rejects every existing third-party gem.
# Setting engine_name=o3de matches upstream's pristine engine.json AND
# upstream's .deb default — so gems work out of the box.
#
# Trade-off: the manifest's `engines_path` map keys by engine_name, so
# multiple installs of o3deNNNN all collide on the "o3de" key. Only one
# is "registered" at a time; switching uses scripts/o3de.sh
# register --this-engine from the desired install root. This is
# exactly upstream's multi-install UX on .deb. Multi-install on disk
# still works (paths versioned at /opt/O3DE/<v>/); only the active
# registration is single-slot.
cmake \
    -S . -B build \
    -G "Ninja Multi-Config" \
    -DCMAKE_C_COMPILER=clang \
    -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_CONFIGURATION_TYPES="%{_o3de_configs}" \
    -DCMAKE_INSTALL_PREFIX=%{o3de_install_prefix} \
    -DLY_3RDPARTY_PATH=%{_builddir}/%{o3de_source_dir}/3rdParty \
    -DO3DE_INSTALL_ENGINE_NAME=o3de \
    -DO3DE_INSTALL_VERSION_STRING=%{engine_cmake_version} \
    -DO3DE_INSTALL_DISPLAY_VERSION_STRING=%{_o3de_display_version} \
    -DO3DE_INSTALL_BUILD_VERSION='"%{_o3de_build_version}"' \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=OFF \
    -DTHREADS_PREFER_PTHREAD_FLAG=ON \
    -DCMAKE_THREAD_LIBS_INIT=-lpthread \
    -DCMAKE_HAVE_THREADS_LIBRARY=1 \
    -DCMAKE_USE_PTHREADS_INIT=1 \
    -DCMAKE_EXE_LINKER_FLAGS_INIT="-Wl,-z,relro -Wl,-z,now" \
    -DCMAKE_SHARED_LINKER_FLAGS_INIT="-Wl,-z,relro -Wl,-z,now" \
    %{?with_system_assimp:-DLY_USE_SYSTEM_ASSIMP=ON} \
    %{?with_system_expat:-DLY_USE_SYSTEM_EXPAT=ON} \
    %{?with_system_freetype:-DLY_USE_SYSTEM_FREETYPE=ON} \
    %{?with_system_googlebenchmark:-DLY_USE_SYSTEM_GOOGLEBENCHMARK=ON} \
    %{?with_system_libsamplerate:-DLY_USE_SYSTEM_LIBSAMPLERATE=ON} \
    %{?with_system_lua:-DLY_USE_SYSTEM_LUA=ON} \
    %{?with_system_lz4:-DLY_USE_SYSTEM_LZ4=ON} \
    %{?with_system_mcpp:-DLY_USE_SYSTEM_MCPP=ON} \
    %{?with_system_mikkelsen:-DLY_USE_SYSTEM_MIKKELSEN=ON} \
    %{?with_system_openexr:-DLY_USE_SYSTEM_OPENEXR=ON} \
    %{?with_system_png:-DLY_USE_SYSTEM_PNG=ON} \
    %{?with_system_poly2tri:-DLY_USE_SYSTEM_POLY2TRI=ON} \
    %{?with_system_sqlite:-DLY_USE_SYSTEM_SQLITE=ON} \
    %{?with_system_tiff:-DLY_USE_SYSTEM_TIFF=ON} \
    %{?with_system_vulkan_validation_layers:-DLY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS=ON} \
    %{?with_system_zlib:-DLY_USE_SYSTEM_ZLIB=ON}

# googletest is fetched via FetchContent during cmake configure and so
# can't be patched in %%prep. Append our warning suppressions afterwards
# and re-run cmake to regenerate the build files.
gtest_cmake=build/_deps/googletest-src/googletest/CMakeLists.txt
if [ -f "$gtest_cmake" ]; then
    cat >> "$gtest_cmake" <<'EOF'

# clang 21+ compatibility (added by Fedora RPM build).
foreach(_t IN ITEMS gtest gtest_main)
    if(TARGET ${_t})
        target_compile_options(${_t} PRIVATE
            -Wno-error=character-conversion
            -Wno-error=deprecated-volatile)
    endif()
endforeach()
EOF
    cmake -S . -B build
fi

# Cap compile parallelism to avoid OOM. Unity TUs at -O2 can consume
# ~4-6 GB of RAM per concurrent clang process; 16-way parallel on a
# 32 GB RAM box busts memory budget on profile-config compile of
# heavy AZStd-template-laden gems. Heuristic: 1 job per 4 GB of RAM,
# clamped to ncpus. Override on a different host with --define.
%global o3de_build_jobs %(\\
    mem_gb=$(awk '/MemTotal/{printf "%d", $2/1024/1024}' /proc/meminfo); \\
    cpus=%{_smp_build_ncpus}; \\
    by_mem=$((mem_gb / 4)); \\
    [ $by_mem -lt 1 ] && by_mem=1; \\
    [ $by_mem -lt $cpus ] && echo $by_mem || echo $cpus)

cmake --build build --config profile --parallel %{o3de_build_jobs}
%if %{with debug}
cmake --build build --config debug --parallel %{o3de_build_jobs}
%endif

# Build sdists for the Python packages O3DE's LYPython.cmake would
# otherwise try to `pip install -e` from inside the read-only engine
# tree. Patch0004 makes the cmake function prefer dist/<name>-X.Y.Z.tar.gz
# over the source dir when it exists. This avoids pip writing
# .egg-info/ into /opt/o3de/Tools/... at user-project-configure time.
for pkg in scripts/o3de Tools/LyTestTools Tools/RemoteConsole/ly_remote_console; do
    ( cd "$pkg" && %{__python3} setup.py sdist )
done

# ── INSTALL ──────────────────────────────────────────────────────────────────
%install
# O3DE's install components split by config:
#   CORE             cmake config files / engine.json (config-independent)
#   DEFAULT          scripts / Tools / python (config-independent)
#   DEFAULT_PROFILE  profile-config binaries (always shipped → main package)
#   DEFAULT_DEBUG    debug-config binaries (opt-in → o3de-debug subpackage)
# Config-independent components are invoked with --config profile (the
# config that's always built) so the install target is guaranteed to exist.
DESTDIR=%{buildroot} cmake --install build --config profile --component CORE
DESTDIR=%{buildroot} cmake --install build --config profile --component DEFAULT
DESTDIR=%{buildroot} cmake --install build --config profile --component DEFAULT_PROFILE
%if %{with debug}
DESTDIR=%{buildroot} cmake --install build --config debug --component DEFAULT_DEBUG
%endif

# Normalize ambiguous '#!/usr/bin/env python' shebangs to 'python3' across
# the entire engine tree so brp-mangle-shebangs accepts them. We deliberately
# keep '/usr/bin/env' (not a hardcoded /usr/bin/python3) so the bundled
# Python venv is found via PATH when the launcher activates it.
find %{buildroot}%{o3de_install_prefix} -type f -name '*.py' \
    -exec sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

%if %{with system_spirvcross}
# Stage 2 binary-only swap: replace the bundled spirv-cross binary
# (which the engine fetched from packages.o3de.org during cmake
# configure and `cmake --install` just copied to its expected runtime
# path) with a symlink to /usr/bin/spirv-cross from the
# o3de2605-spirv-cross COPR package. The engine's runtime path resolution
# (RHI::ExecuteShaderCompiler in
# Gems/Atom/RHI/Code/Source/RHI.Edit/Utils.cpp) follows the symlink
# transparently.
#
# Per the audit (2026-05-07,
# /tmp/o3de-assimp-audit/SPIRVCROSS_INVESTIGATION_NOTES.md) the engine
# treats spirv-cross as a binary executable shellout, not a library
# link, so swapping the binary at install time is sufficient. No engine
# code changes needed.
#
# Why not gate the upstream fetch via Patch0006: the bundled package
# contains a FindSPIRVCross.cmake that creates the 3rdParty::SPIRVCross
# cmake target the engine needs at configure time; gating the fetch
# without providing an equivalent target shape would break cmake config.
# Future cleanup: write a Findspirvcross-system.cmake shim that creates
# the IMPORTED EXECUTABLE target, gate Patch0006, drop the upstream
# fetch entirely. For the PoC this overlay approach is enough.
ln -sf /usr/bin/spirv-cross \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/profile/Default/Builders/SPIRVCross/spirv-cross
%if %{with debug}
ln -sf /usr/bin/spirv-cross \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/debug/Default/Builders/SPIRVCross/spirv-cross
%endif
%endif

%if %{with system_dxc}
# Stage 2 binary-only swap: same shape as system_spirvcross above, but
# DXC has three install paths to overlay (dxc, dxsc, libdxcompiler.so).
# COPR-built /usr/bin/dxc + /usr/bin/dxsc + /usr/lib64/libdxcompiler.so
# from the o3de2605-dxc-spirv package (license-clean Linux/SPIR-V-only
# rebuild from o3de/DirectXShaderCompiler at tag release-1.8.2505.1-o3de;
# ✓ green PoC build 10435628 since 2026-05-08; functional verification
# confirmed `dxc -spirv -T ps_6_0 -E main shader.hlsl` produces valid
# SPIR-V output).
#
# Engine's per-platform DXC path is set in
# Gems/Atom/RHI/Vulkan/Code/Source/Platform/Linux/Vulkan_Traits_Linux.h:10
# as "Builders/DirectXShaderCompiler/bin/dxc" and consumed via
# RHI::ExecuteShaderCompiler. Same install-overlay pattern as
# spirv-cross above; see SPIRV-Cross block for the architectural
# rationale.
ln -sf /usr/bin/dxc \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/profile/Default/Builders/DirectXShaderCompiler/bin/dxc
ln -sf /usr/bin/dxsc \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/profile/Default/Builders/DirectXShaderCompiler/bin/dxsc
ln -sf /usr/lib64/libdxcompiler.so \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/profile/Default/Builders/DirectXShaderCompiler/lib/libdxcompiler.so
%if %{with debug}
ln -sf /usr/bin/dxc \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/debug/Default/Builders/DirectXShaderCompiler/bin/dxc
ln -sf /usr/bin/dxsc \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/debug/Default/Builders/DirectXShaderCompiler/bin/dxsc
ln -sf /usr/lib64/libdxcompiler.so \
    %{buildroot}%{o3de_install_prefix}/bin/Linux/debug/Default/Builders/DirectXShaderCompiler/lib/libdxcompiler.so
%endif
%endif

# Editor expects engine.json + python relative to the binary's location.
# Profile binaries are always present; debug only when --with debug.
ln -s ../../../../python      %{buildroot}%{o3de_install_prefix}/bin/Linux/profile/Default/python
ln -s ../../../../engine.json %{buildroot}%{o3de_install_prefix}/bin/Linux/profile/Default/engine.json
%if %{with debug}
ln -s ../../../../python      %{buildroot}%{o3de_install_prefix}/bin/Linux/debug/Default/python
ln -s ../../../../engine.json %{buildroot}%{o3de_install_prefix}/bin/Linux/debug/Default/engine.json
%endif

# Launcher wrapper + desktop entries from real Source files. The
# o3de.desktop entry (Source11) is the user-visible menu launcher
# (Project Manager). The o3de-editor.desktop entry (Source15) is
# NoDisplay=true and exists only so GNOME/KDE can match the Editor's
# running window to our installed icon — without it, the dock falls
# through to Qt's internal icon for the Editor.
#
# Source files (sources/o3de-launcher.sh, sources/o3de-cli, sources/
# o3de.desktop, sources/o3de-editor.desktop) stay statically named and
# pass desktop-file-validate as-is. Per-version mutation lands here at
# install time (note: avoid literal %%install in comments inside this
# section -- CS10's RPM 4.19 misparses unescaped %%install as a section
# marker; F44/rawhide RPM 6.x ignores it):
#   - launcher / o3de-cli paths → %{o3de_install_prefix} via sed
#   - launcher Qt -name arg → "O3DE-%{o3de_major_tag}" (matches StartupWMClass)
#   - desktop file Exec / Icon / Name / StartupWMClass keys overridden
#     via desktop-file-install --set-key
#   - file rename: o3de.desktop → %{o3de_pkgname}.desktop, etc.
install -D -m 0755 %{SOURCE10} %{buildroot}%{_bindir}/%{o3de_pkgname}
install -D -m 0755 %{SOURCE16} %{buildroot}%{_bindir}/%{o3de_pkgname}-cli
# Substitute the @O3DE_INSTALL_PREFIX@ placeholder both source files
# define for their default engine path, and version the launcher's Qt
# `-name "O3DE"` arg so WM_CLASS matches the desktop file's
# StartupWMClass=O3DE-<major>. Targeted substitution preserves
# literal /opt/o3de occurrences in the launcher's legacy_prefixes
# list (used for one-time user-state migration from pre-versioning
# installs).
sed -i \
    -e 's|@O3DE_INSTALL_PREFIX@|%{o3de_install_prefix}|g' \
    -e 's|-name "O3DE"|-name "O3DE-%{o3de_major_tag}"|g' \
    %{buildroot}%{_bindir}/%{o3de_pkgname} \
    %{buildroot}%{_bindir}/%{o3de_pkgname}-cli

# Project Manager menu entry — mutate visible Name, Icon, Exec, and
# StartupWMClass at install. Two installed versions need distinct
# (Name, Icon, StartupWMClass, file path) tuples to avoid collision.
desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    --set-key=Exec --set-value=%{_bindir}/%{o3de_pkgname} \
    --set-key=Icon --set-value=%{o3de_pkgname} \
    --set-key=Name --set-value="O3DE %{engine_cmake_version}" \
    --set-key=StartupWMClass --set-value="O3DE-%{o3de_major_tag}" \
    %{SOURCE11}
mv %{buildroot}%{_datadir}/applications/o3de.desktop \
   %{buildroot}%{_datadir}/applications/%{o3de_pkgname}.desktop

# Editor / Material Editor / Material Canvas menu entries.
#
# StartupWMClass values match what each binary's Qt setApplicationName()
# sets at runtime, NOT a versioned form. Each tool's Application.cpp sets:
#   Editor:          setApplicationName("O3DE Editor")
#   MaterialEditor:  setApplicationName("O3DE Material Editor")
#   MaterialCanvas:  setApplicationName("O3DE Material Canvas")
# Qt translates that into the X11 WM_CLASS res_class. The desktop entry's
# StartupWMClass must match exactly for the dock to attach our icon to
# the running window. This also makes PM-launched Editor (which exec's
# the binary directly, bypassing the desktop file) attach correctly --
# the canonical user flow.
#
# Tradeoff: two installed majors (o3de2605 + future o3de2610) share these
# WM_CLASS values, so the dock will associate to whichever desktop entry
# the WM finds first when both are installed. Accepted -- multi-major is
# theoretical until 26.10.x ships, and PM-launched dock attachment is the
# canonical path that must work today.

# Editor menu entry — visible (matching the Windows installer layout
# as of 2026-05-24).
desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    --set-key=Exec --set-value=%{o3de_install_prefix}/bin/Linux/profile/Default/Editor \
    --set-key=Icon --set-value=%{o3de_pkgname}-editor \
    --set-key=Name --set-value="O3DE %{engine_cmake_version} Editor" \
    --set-key=StartupWMClass --set-value="O3DE Editor" \
    %{SOURCE15}
mv %{buildroot}%{_datadir}/applications/o3de-editor.desktop \
   %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-editor.desktop

# Material Editor menu entry — standalone material authoring tool.
desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    --set-key=Exec --set-value=%{o3de_install_prefix}/bin/Linux/profile/Default/MaterialEditor \
    --set-key=Icon --set-value=%{o3de_pkgname}-material-editor \
    --set-key=Name --set-value="O3DE %{engine_cmake_version} Material Editor" \
    --set-key=StartupWMClass --set-value="O3DE Material Editor" \
    %{SOURCE17}
mv %{buildroot}%{_datadir}/applications/o3de-material-editor.desktop \
   %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-material-editor.desktop

# Material Canvas menu entry — node-based material authoring complement.
desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    --set-key=Exec --set-value=%{o3de_install_prefix}/bin/Linux/profile/Default/MaterialCanvas \
    --set-key=Icon --set-value=%{o3de_pkgname}-material-canvas \
    --set-key=Name --set-value="O3DE %{engine_cmake_version} Material Canvas" \
    --set-key=StartupWMClass --set-value="O3DE Material Canvas" \
    %{SOURCE18}
mv %{buildroot}%{_datadir}/applications/o3de-material-canvas.desktop \
   %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-material-canvas.desktop

# AppStream metainfo for GNOME Software / KDE Discover. Required for
# Fedora-distributed GUI applications. Mutate component ID + launchable
# + binary + name to versioned forms so two installed majors appear as
# separate apps in the GUI app store.
install -D -m 0644 %{SOURCE14} \
    %{buildroot}%{_metainfodir}/o3de.metainfo.xml
sed -i \
    -e 's|<id>org.o3de.O3DE</id>|<id>org.o3de.O3DE%{o3de_major_tag}</id>|' \
    -e 's|<launchable type="desktop-id">o3de.desktop</launchable>|<launchable type="desktop-id">%{o3de_pkgname}.desktop</launchable>|' \
    -e 's|<binary>o3de</binary>|<binary>%{o3de_pkgname}</binary>|' \
    -e 's|<name>O3DE</name>|<name>O3DE %{engine_cmake_version}</name>|' \
    %{buildroot}%{_metainfodir}/o3de.metainfo.xml
mv %{buildroot}%{_metainfodir}/o3de.metainfo.xml \
   %{buildroot}%{_metainfodir}/%{o3de_pkgname}.metainfo.xml

# Hicolor icon theme — four per-tool icon series, each in six standard
# sizes. Each tool gets its own icon name (versioned per major) so two
# installed majors don't clobber each other's icons.
for SZ in 16 32 48 64 128 256; do
    case $SZ in
        16)  PM=%{SOURCE20} ED=%{SOURCE50} ME=%{SOURCE56} MC=%{SOURCE62} ;;
        32)  PM=%{SOURCE21} ED=%{SOURCE51} ME=%{SOURCE57} MC=%{SOURCE63} ;;
        48)  PM=%{SOURCE22} ED=%{SOURCE52} ME=%{SOURCE58} MC=%{SOURCE64} ;;
        64)  PM=%{SOURCE23} ED=%{SOURCE53} ME=%{SOURCE59} MC=%{SOURCE65} ;;
        128) PM=%{SOURCE24} ED=%{SOURCE54} ME=%{SOURCE60} MC=%{SOURCE66} ;;
        256) PM=%{SOURCE25} ED=%{SOURCE55} ME=%{SOURCE61} MC=%{SOURCE67} ;;
    esac
    install -D -m 0644 "$PM" %{buildroot}%{_datadir}/icons/hicolor/${SZ}x${SZ}/apps/%{o3de_pkgname}.png
    install -D -m 0644 "$ED" %{buildroot}%{_datadir}/icons/hicolor/${SZ}x${SZ}/apps/%{o3de_pkgname}-editor.png
    install -D -m 0644 "$ME" %{buildroot}%{_datadir}/icons/hicolor/${SZ}x${SZ}/apps/%{o3de_pkgname}-material-editor.png
    install -D -m 0644 "$MC" %{buildroot}%{_datadir}/icons/hicolor/${SZ}x${SZ}/apps/%{o3de_pkgname}-material-canvas.png
done

# Ship the SBOM next to the license/docs so it's discoverable post-install.
install -D -m 0644 %{SOURCE13} \
    %{buildroot}%{_datadir}/%{o3de_pkgname}/sbom/%{o3de_pkgname}.cdx.json

# ── CHECK ────────────────────────────────────────────────────────────────────
%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{o3de_pkgname}.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-editor.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-material-editor.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-material-canvas.desktop
appstream-util validate-relax --nonet \
    %{buildroot}%{_metainfodir}/%{o3de_pkgname}.metainfo.xml

# ── FILES ────────────────────────────────────────────────────────────────────
%files
%license LICENSE.txt LICENSE_APACHE2.TXT LICENSE_MIT.TXT
%doc README.md CODE_OF_CONDUCT.md CONTRIBUTING.md
%{o3de_install_prefix}
%if %{with debug}
# DEFAULT_DEBUG installs both runtime binaries (bin/Linux/debug/) and
# debug-config archives + shared libs (lib/Linux/debug/) — both belong
# in the %%{name}-debug subpackage, not the main one.
%exclude %{o3de_install_prefix}/bin/Linux/debug
%exclude %{o3de_install_prefix}/lib/Linux/debug
%endif
# Static archives + lib64/ (Recast/Detour bundled) → %%{name}-devel.
# Three exclude patterns cover all .a archives under the engine prefix:
#   - lib/Linux/profile/Default/*.a — engine + gem static archives
#     (~173 files, the bulk of the carve-out at ~4 GB)
#   - lib/Linux/profile/*.a — bundled 3rdParty archives one level up
#     (gmock, gtest, miniaudio, ogg, vorbis — ~13 files)
#   - lib64/ — Recast/Detour bundled archives + pkgconfig metadata
#     (5 files, ~2 MB; whole dir moves since it's exclusively
#     devel-side content). Gone on o3de/development as of 2026-05-21
#     after a Gems/RecastNavigation/3rdParty/FindRecastNavigation.cmake
#     shim landed and the bundled-install path stopped emitting lib64/.
#     Stabilization/26050 still has the old layout, so lib64/ is
#     still present there. Gate both the exclude and the devel files
#     line on %%without development_snapshot.
%exclude %{o3de_install_prefix}/lib/Linux/profile/*.a
%exclude %{o3de_install_prefix}/lib/Linux/profile/Default/*.a
%if %{without development_snapshot}
%exclude %{o3de_install_prefix}/lib64
%endif
%{_bindir}/%{o3de_pkgname}
%{_bindir}/%{o3de_pkgname}-cli
%{_datadir}/applications/%{o3de_pkgname}.desktop
%{_datadir}/applications/%{o3de_pkgname}-editor.desktop
%{_datadir}/applications/%{o3de_pkgname}-material-editor.desktop
%{_datadir}/applications/%{o3de_pkgname}-material-canvas.desktop
%{_metainfodir}/%{o3de_pkgname}.metainfo.xml
%{_datadir}/icons/hicolor/16x16/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/32x32/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/48x48/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/64x64/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/128x128/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/256x256/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/16x16/apps/%{o3de_pkgname}-editor.png
%{_datadir}/icons/hicolor/32x32/apps/%{o3de_pkgname}-editor.png
%{_datadir}/icons/hicolor/48x48/apps/%{o3de_pkgname}-editor.png
%{_datadir}/icons/hicolor/64x64/apps/%{o3de_pkgname}-editor.png
%{_datadir}/icons/hicolor/128x128/apps/%{o3de_pkgname}-editor.png
%{_datadir}/icons/hicolor/256x256/apps/%{o3de_pkgname}-editor.png
%{_datadir}/icons/hicolor/16x16/apps/%{o3de_pkgname}-material-editor.png
%{_datadir}/icons/hicolor/32x32/apps/%{o3de_pkgname}-material-editor.png
%{_datadir}/icons/hicolor/48x48/apps/%{o3de_pkgname}-material-editor.png
%{_datadir}/icons/hicolor/64x64/apps/%{o3de_pkgname}-material-editor.png
%{_datadir}/icons/hicolor/128x128/apps/%{o3de_pkgname}-material-editor.png
%{_datadir}/icons/hicolor/256x256/apps/%{o3de_pkgname}-material-editor.png
%{_datadir}/icons/hicolor/16x16/apps/%{o3de_pkgname}-material-canvas.png
%{_datadir}/icons/hicolor/32x32/apps/%{o3de_pkgname}-material-canvas.png
%{_datadir}/icons/hicolor/48x48/apps/%{o3de_pkgname}-material-canvas.png
%{_datadir}/icons/hicolor/64x64/apps/%{o3de_pkgname}-material-canvas.png
%{_datadir}/icons/hicolor/128x128/apps/%{o3de_pkgname}-material-canvas.png
%{_datadir}/icons/hicolor/256x256/apps/%{o3de_pkgname}-material-canvas.png
%{_datadir}/%{o3de_pkgname}/sbom/%{o3de_pkgname}.cdx.json

%if %{with debug}
%files debug
%{o3de_install_prefix}/bin/Linux/debug
%{o3de_install_prefix}/lib/Linux/debug
%endif

%files devel
%{o3de_install_prefix}/lib/Linux/profile/*.a
%{o3de_install_prefix}/lib/Linux/profile/Default/*.a
%if %{without development_snapshot}
%{o3de_install_prefix}/lib64
%endif

# ── Scriptlets ───────────────────────────────────────────────────────────────
%post
if [ -x %{o3de_install_prefix}/scripts/o3de.sh ]; then
    %{o3de_install_prefix}/scripts/o3de.sh register --this-engine || :
fi
/usr/bin/update-desktop-database -q %{_datadir}/applications &>/dev/null || :
/usr/bin/gtk-update-icon-cache --quiet --force \
    %{_datadir}/icons/hicolor &>/dev/null || :

cat <<EOF

O3DE %{engine_cmake_version} installed at %{o3de_install_prefix}
(profile-config binaries).

This package is %{name} — multiple O3DE majors can coexist on one
system (e.g., o3de2605 alongside a future o3de2610), each at its
own /opt/O3DE/<version>/ install root. Project Manager auto-routes
each project to the engine version pinned in its project.json.

To step through engine code in a debugger, also install the debug
subpackage if available:

    sudo dnf install %{name}-debug

For native C++ gem development that needs to static-link against
engine internals (test framework, builder targets, etc.), also
install the devel subpackage:

    sudo dnf install %{name}-devel

Most user projects (Lua/ScriptCanvas, native C++ projects against
engine .so's) do not need %{name}-devel.

The per-user Python venv bootstraps on first launch automatically;
to pre-bootstrap it manually run:

    %{o3de_install_prefix}/python/get_python.sh

Launch the editor (Project Manager GUI):

    %{name}                            # profile build (default)
    O3DE_BUILD_CONFIG=debug %{name}    # debug build (requires %{name}-debug)

Use the command-line tool for project / gem / engine management:

    %{name}-cli --help                 # list sub-commands
    %{name}-cli register --this-engine # one-time per-user setup
    %{name}-cli create-project --project-path ~/MyGame --project-name MyGame

EOF

%postun
/usr/bin/update-desktop-database -q %{_datadir}/applications &>/dev/null || :
/usr/bin/gtk-update-icon-cache --quiet --force \
    %{_datadir}/icons/hicolor &>/dev/null || :

# ── Changelog ────────────────────────────────────────────────────────────────
%changelog
* Wed May 27 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-79
- Fix release-day build (10517399, all three chroots failed).
  Two independent root causes, both diagnosed locally:
  1. Stable-mode %%prep replaced the rpm 6.x autosetup macro with
     manual `mkdir + cd + tar -xf` extraction in -77, because the
     earlier failure mode looked like a macro mis-expansion bug.
     Re-tested rpm 6.0.1 locally with three forms (literal name,
     macro %%{name}, %%global-then-ref): all expanded correctly.
     The mis-expansion hypothesis was wrong. Manual extraction
     bypassed rpmbuild's source-dir registration, so %%doc/%%license
     in %%files couldn't resolve README.md / LICENSE.txt / etc. and
     %%files exploded after a 4hr+ build (all three chroots).
     Reverted to `%%autosetup -c -n %%{o3de_source_dir} -p1` for
     stable mode (the -c flag handles the 2605.0 wrapping-dir-less
     tarball layout correctly). Removed the redundant `cd
     %%{o3de_source_dir}` workarounds from %%build and %%install.
  2. FindOpenEXR-system.cmake's find_path returned /usr/include (the
     parent of the namespaced OpenEXR/ subdir) and added only that
     to the 3rdParty::OpenEXR interface. Worked fine on F44 (openexr
     3.2.4) and on rawhide pre-2026-05-27 (also 3.2.4). Rawhide
     bumped to openexr 3.4.12 on 2026-05-27; the 3.4 release added
     a new umbrella openexr.h that everything transitively pulls
     in, and that header chains into openexr_config.h which does an
     unprefixed `#include <IlmThreadConfig.h>`. IlmThreadConfig.h
     lives at /usr/include/OpenEXR/IlmThreadConfig.h, so consumers
     now also need -I/usr/include/OpenEXR on the interface. Added
     a second find_path for IlmThreadConfig.h and appended its
     resolved path to the include directories. Verified locally
     against rawhide podman container with openexr-devel-3.4.12-1.fc45.

* Wed May 27 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-78
- Fix two cascading consequences of the stable-mode manual extraction
  introduced in -77. Build 10517337 reached the %%build step (so
  %%prep is finally clean) but failed at "CMake Error: The source
  directory does not appear to contain CMakeLists.txt." With autosetup
  the macro auto-chdir's into the source subdir for subsequent steps;
  the manual extract doesn't do that, so %%build and %%install have
  to chdir explicitly. Added `cd %{o3de_source_dir}` to the top of
  both sections, gated on `%%{without snapshot}` so snapshot-mode
  still rides on the autosetup chdir.
  Separately, the cmake invocation in 10517337 used a
  `-DO3DE_INSTALL_DISPLAY_VERSION_STRING=26.05.0-stabilization` channel
  marker which is wrong for hellaenergy/o3de (the stable channel
  should have no marker). Traced to hellaenergy/o3de chroots'
  `with_opts` still carrying the `stabilization` flag from an
  earlier alignment with the stab channel's 18-flag swap set.
  Removed the `stabilization` flag from all three o3de chroots (now
  17 flags: all the system_* swaps without the channel marker).

* Wed May 27 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-77
- Stable-mode %%prep rewrite. Build 10517309 failed at %%prep because
  the rpm 6.x autosetup macro with the -c -n flags mis-expanded the
  target directory name (placeholder "<dir>" leaked through instead
  of "o3de"). Compounding the failure, an earlier draft of the
  surrounding spec comment contained literal autosetup invocation
  syntax that rpm's macro engine treated as a live macro call (rpm
  parses macros inside shell-style comments).
  Two fixes:
    * Replace the setup-family extract step in stable mode with
      straight shell (mkdir, cd, tar) plus autopatch for patch
      application. The setup-family macros simply don't reliably
      handle the new "tarball ships content at root" layout when the
      target directory name comes from a macro reference.
    * Rewrite the comment block so it doesn't contain macro syntax,
      preventing future drafts from re-triggering the comment-as-macro
      misbehavior. Macro-name references in the changelog body also
      escaped with %% so the changelog itself doesn't trip the same
      pattern.
  Verified locally: rpmbuild -bp completes cleanly, all 13 carry-
  patches apply, the patched tree contains the expected file content.

* Wed May 27 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-76
- 26.05.0 release day. Upstream tagged 2605.0 at commit
  3db6943249d8bd7960b9ed7e9aee310b7668586e (PR #19783, "Release Day
  Only -- Merge stabilization to main 26.05 (26050, v 2.6.0)") on
  2026-05-27T17:01:43Z, with release-tarball sha256
  f23c46eaf60fd7359279781f4abefa1b7f0d88091fd37ce9bff31431927c3f1e.
  Switch from snapshot-mode builds (against stab/26050 tip 8e75050)
  to stable-mode builds against the tagged release.
  Defensive `patch --dry-run` confirmed all 13 carry-patches still
  apply cleanly against the tagged source. The 6 TIMEBOMB patches
  remain active: the tag is on main (stab merged into main), so the
  development-branch merges that retire those patches haven't reached
  main yet either.
  Two upstream-side conventions changed since 2510.x that the spec
  needed to handle:
    * Release tarball filename is `o3de-<TAG>-lfs.tar.gz` with dashes
      (was `o3de_<TAG>_lfs.tar.gz` with underscores). Source0 URL
      updated accordingly; comment in stable_sha256 area refreshed.
    * Release tarball ships content at the root (no wrapping `o3de/`
      directory). Spec's `%autosetup` now uses `-c -n` in stable mode
      to create the wrapping directory at extract time, matching the
      previous snapshot-mode path where the tarball already wraps.
  Makefile updates: `srpm` target now passes `--without snapshot` so
  auto-detect doesn't force snapshot mode when both tarballs are
  present in sources/. `release-stable` target's preflight tarball
  check now points at `sources/o3de-<tag>-lfs.tar.gz` (the actual
  path with the new naming convention) instead of `~/rpmbuild/SOURCES/`.

* Mon May 25 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-75
- Hide Editor, Material Editor, Material Canvas desktop entries
  (NoDisplay=true). Only Project Manager remains visible in the
  application menu. Discovered while running the freshly-installed
  build: clicking the standalone tool entries cold from the menu
  produces broken UX. Material Editor + Material Canvas error with
  "is not a valid project path" because the binaries need a project
  context. Editor binary cold-launches gracefully -- it falls back to
  launching Project Manager as a project picker -- but that makes the
  Editor menu entry behaviorally identical to the PM menu entry, two
  duplicate-result entries that confuse users.
  Hidden entries keep their desktop files installed so the dock can
  pair our per-tool icons (extracted from upstream's Windows .ico files)
  to running windows via StartupWMClass matching, when those tools are
  launched from inside the running Editor (the canonical path that
  inherits project context). The menu surface lands at a single PM
  entry, matching what Debian + Snap installs ship.
  Diverges from the literal Windows Start menu shape (which ships
  visible Editor + ME shortcuts) but Windows's shortcuts have the same
  broken-or-redundant cold-launch behavior we confirmed in
  cmake/Platform/Windows/Packaging/Shortcuts.wxs -- so we're matching
  upstream's behavior, not its surface.

* Mon May 25 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-74
- Regenerate 8e750500 snapshot tarball with LFS objects expanded.
  The 2026-05-23 tarball pull used the GitHub archive endpoint
  (https://github.com/o3de/o3de/archive/<sha>.tar.gz) which serves git-
  LFS pointer files for any LFS-tracked content, NOT the actual binary
  payloads. Result: 1,359 LFS placeholder files made it into builds
  10507773 + 10510733, the engine binaries linked fine but asset bakes
  cascaded into 500+ failures whenever the dependency chain touched a
  font / texture stored in LFS. Sample-project bakes (Tier 9 + Tier 10)
  surfaced this.
  Replaced the 39MB GitHub-archive tarball with a proper 1.9GB output
  from sources/make-snapshot-tarball.sh (git clone + git lfs pull +
  tar). New sha256 d6470fdb... Same upstream commit
  8e750500f23c9c45f08266200463fd31996638b7; only the LFS payloads
  changed (added).
  Going forward: always use sources/make-snapshot-tarball.sh for
  snapshot bumps. Direct curl from GitHub archive silently strips LFS.

* Mon May 25 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-73
- Revert StartupWMClass versioning + -name additions for Editor / Material
  Editor / Material Canvas. The previous attempt (2605.0-71 + -72) set
  StartupWMClass to versioned forms ("O3DE-2605 Editor" etc.) and added
  `-name "O3DE-<major> <Tool>"` to each Exec= to compensate. That fixed
  the menu-launched case but BROKE the canonical PM-launched flow, where
  Project Manager exec's the tool's binary directly (bypassing the desktop
  file's Exec=). When PM-launched, each binary's internal Qt
  setApplicationName ("O3DE Editor" / "O3DE Material Editor" / "O3DE
  Material Canvas") sets WM_CLASS to the unversioned form, which mismatched
  our versioned StartupWMClass, and the dock fell back to the engine's
  internal icon. The PM-launched-Editor regression was caught by Tier 2's
  Editor StartupWMClass check (which has a verified xprop reading
  documenting WM_CLASS = "Editor", "O3DE Editor"). Reverting to
  unversioned StartupWMClass matches both PM-launched AND menu-launched
  paths cleanly. Tradeoff: two installed majors share these WM_CLASS
  tokens; multi-major dock collision is theoretical until 26.10 ships.

* Sun May 24 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-72
- Desktop entries (Editor / Material Editor / Material Canvas): pass
  `-name "O3DE-<major> <Tool>"` to Qt via the desktop Exec= so the
  running window's X11 WM_CLASS matches the StartupWMClass. Without this,
  Qt would use the engine's internal setApplicationName ("O3DE Editor",
  etc.) which differs from our versioned StartupWMClass, the dock can't
  attach our menu icon to the running window, and the dock falls back to
  the small SVG that the engine bakes via setWindowIcon. Mirrors the
  existing PM launcher pattern that's already passing -name "O3DE-NNNN"
  to Qt via sources/o3de-launcher.sh.
  Effect: minimized / docked Editor / Material Editor / Material Canvas
  windows now show the per-tool Windows-extracted icon instead of the
  small in-binary fallback. The Material Editor / Material Canvas TITLE
  BAR icon still falls back to the small SVG because the engine's
  setWindowIcon points at :/Icons/application.svg (a 65x64 asset) for
  those two tools; that's engine-side, not packaging-side. Upstream
  follow-up post-release.

* Sun May 24 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-71
- Desktop layout: match Windows-installer intent. All four user-facing
  tools visible in the menu with their own per-tool Windows-extracted
  icons: Project Manager, Editor (unhidden; previously NoDisplay=true),
  Material Editor (new), Material Canvas (new). Icons extracted via
  icotool from upstream's per-tool .ico files in Code/Editor/res,
  Code/Tools/ProjectManager/Resources, Gems/Atom/Tools/MaterialEditor/...
  and Gems/Atom/Tools/MaterialCanvas/... (the last one only had a single
  203x200 source so it was resized to standard hicolor sizes via magick).
  Per-tool versioned naming throughout: %{o3de_pkgname}.desktop +
  %{o3de_pkgname}-{editor,material-editor,material-canvas}.desktop, with
  matching Icon names and StartupWMClass tokens so two installed majors
  don't collide. Discovered en route that our existing "o3de" icon was
  byte-identical to upstream's Editor .ico contents; the new layout
  routes that file to the Editor entry and gives PM its own correct
  upstream icon.

* Sat May 23 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-70
- Rename hellaenergy/o3de-snapshot -> hellaenergy/o3de-development to make
  the always-tracks-development-branch intent explicit. The old "snapshot"
  name overloaded two distinct meanings (source-mode "non-tagged-tarball
  snapshot" vs the COPR project name); the project-name half now reflects
  what the channel actually does. For arbitrary other refs (rare; e.g. a
  hypothetical qt6 migration channel) a dedicated COPR project per branch
  gets created rather than overloading o3de-development.
  Spec: add a fourth elif to _o3de_channel for --with development_snapshot
  -> "-development.<sha>" marker. The bcond was already in use for
  patch-gating; now drives the GUI marker too. The --with snapshot only
  branch still resolves to "-snapshot.<sha>" for arbitrary-ref builds.
  Makefile: COPR_PROJECT_SNAPSHOT renamed to COPR_PROJECT_DEVELOPMENT;
  copr-snapshot renamed to copr-development (now depends on
  srpm-snapshot-development so it always pulls dev tip); copr-snapshot-ref,
  copr-snapshot-qt6, copr-snapshot-development targets removed (rare other
  refs get dedicated COPR projects per branch). srpm-snapshot* targets
  unchanged (source-mode build mechanism).
  CI workflow: comment updates only (cron continues to poll o3de-stabilization).
  tests/ui-smoke-test.sh: recognizes both -development.<sha> and legacy
  -snapshot.<sha> markers.
  COPR: hellaenergy/o3de-development created via copr-cli fork (preserves
  build history); chroot config preserved. Old hellaenergy/o3de-snapshot
  description set to deprecation notice; project not deleted (pending Nick's
  call).
  Docs: README, CONTRIBUTING, ARCHITECTURE Mermaid, POST_RELEASE, FEDORA_ROADMAP
  refreshed. Memory note project_snapshot_branch.md rewritten for the new
  topology.

* Sat May 23 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-69
- Decouple the channel marker (-experimental / -stabilization / -snapshot)
  from the active system_* swap set. The old logic forced -experimental on
  any build with any system swap active, which was correct in early Stage 1
  but broke once the swaps graduated into the stab + stable channels too --
  the marker would have stamped -experimental on the 26.05.0 release going
  to hellaenergy/o3de (which carries the full 18-swap set).
  Add %bcond_with experimental; channel marker now reflects the destination
  project. Stable mode (no channel bcond) -> "26.05.0" clean; stabilization
  -> "26.05.0-stabilization"; experimental -> "26.05.0-experimental.<sha>".
  o3de-experimental chroots updated to set --rpmbuild-with experimental.
  Verified via rpmspec across all four modes.

* Sat May 23 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-68
- Bump stabilization/26050 snapshot pin to 8e750500 (2026-05-23 release-final
  tip), absorbing the final two pre-release-blessing commits on top of
  d86e2cb6: o3de/o3de#19778 (engine internal version bump to 2.6.0,
  per the sig-release Internal Version Number convention) and
  o3de/o3de#19779 (Editor splashscreen updated for 26.05.0). With these
  in, the stabilization/26050 tip is essentially what 2605.0 will ship.
  Carry-patch set unchanged from -67 (no new overlap with stab tip).
  Building experimental first, then promoting to o3de-stabilization
  ahead of the 2026-05-27 release.

* Sat May 23 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-67
- Bump stabilization/26050 snapshot pin to d86e2cb6 (2026-05-23 tip),
  picking up 5 days of cherry-picks landed since 2956111 (2026-05-18):
  o3de/o3de#19772 (UV-transform Vulkan fix), #19776 (AssetProcessor
  search-bar field restored), #19777 (MSVC 14.50 stdext compat;
  closes the 26.05.0 release-blocker tracked at o3de/o3de#19754).
  None of our carry-patches retire as part of this bump -- the new
  stab cherry-picks don't overlap with the Patch00XX series. Carry
  set unchanged (Patch0001/0002/0005/0007/0008/0012 remain merged-in
  -development but not-yet-in-stabilization; Patch0010/0011 are rawhide
  Lua 5.5 forward-compat; Patch0003/0004/0006/0009/0013 are
  packaging-internal).

* Thu May 21 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-66
- Gate `%%files devel`'s `lib64/` entry (and its companion `%%exclude`)
  on `%%without development_snapshot`. Upstream o3de/development added
  `Gems/RecastNavigation/3rdParty/FindRecastNavigation.cmake` and
  stopped emitting `/opt/O3DE/26.05.0/lib64/` from the bundled install
  path; only `lib/Linux/profile/*.a` patterns survive. Stabilization/
  26050 still has the lib64 layout intact, so the gate keeps stable
  channel behavior unchanged. Build 10492367 caught the drift after
  4h+ of compilation finishing successfully then failing at %%files.

* Thu May 21 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-65
- Extend `--with development_snapshot` bcond to cover Patch0009
  (`physx-pal-gate-poly2tri-on-system`) and Patch0013
  (`vulkan-validationlayers-gate-on-system`). Audit against o3de
  development tip 5bdb8cc (2026-05-21) found two additional
  conflicts: Patch0009 fails because o3de/o3de#19726 (PhysX 4
  retirement) has landed in development and `Gems/PhysX/Core/PhysX4/`
  no longer exists; Patch0013's third hunk hits the same
  BuiltInPackages context drift as Patch0006 (assimp removed via
  PR #19365). Stabilization/26050 still has both PhysX4 and the
  pre-assimp-removal BuiltInPackages layout, so both patches apply
  cleanly there. Total dev-snapshot-gated patches now: 9 (0001 +
  0002 + 0005 + 0006 + 0007 + 0008 + 0009 + 0012 + 0013); 4 patches
  remain active on dev-snapshot (0003 + 0004 + 0010 + 0011).

* Thu May 21 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-64
- Extend `--with development_snapshot` bcond to cover Patch0006
  (`builtinpackages-gate-mikkelsen-on-system`). Patch0006's hunk
  anchors on the `assimp-5.4.3-rev3-linux` ly_associate_package line
  which o3de/o3de#19365 ("Assimp as FetchPackage", 2026-03-10) removed
  from development. Stabilization/26050 still has the line, so
  Patch0006 stays active there. Build 10492252 caught the conflict.
  The `o3de-snapshot` COPR project intentionally has no `system_*`
  swaps active, so the LY_USE_SYSTEM_<X> gates the patch provides
  aren't needed on the dev-snapshot channel anyway.

* Mon May 18 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-63
- snapshot_commit bump to stabilization/26050 tip 295611159e6b (2026-05-18).
  Absorbs three cherry-picks that landed today: #19757 (preWarm particle
  migrated to new OPS formats), #19758 (MSVC 2026 compile fixes -- the
  26.05.0 release-blocker per #19754), #19739 (project-local AzTestRunner
  for SDK-installed builds).
- Add `--with development_snapshot` bcond that gates the 6 carry-patches
  whose upstream equivalents have merged into o3de/development:
  Patch0001 (#19748 clang21), Patch0002 (#19751 manifest.py engine path),
  Patch0005 (#19750 AzQtComponents title), Patch0007 (#19734 libtiff
  C99), Patch0008 (#19733 Lua lobject), Patch0012 (#19747 AssetBuilder
  watchdog). Default OFF so stabilization / snapshot / experimental
  channels continue to apply all 13 patches. Wire into Makefile so
  `make copr-snapshot-development` sets the flag automatically.

* Fri May 15 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-62
- Tag Patch0012 v2 (AssetBuilder parent-death watchdog) as TIMEBOMB
  after upstream merge: o3de/o3de#19747 landed on development
  2026-05-15 (commit 6fd830546c72). nick-l-o3de said "okay with
  accepting this for now" on 2026-05-13 informally; formal approval
  + merge today.
- TIMEBOMB count goes from 5 to 6 (Patch0001/0002/0005/0007/0008/0012).
  All six retire when our snapshot pin moves to a base that contains
  these merges, expected post-2605.0 release (date AT RISK per
  o3de/o3de#19754; see project_2605_release_date.md).
- README + CONTRIBUTING patch tables + ARCHITECTURE Mermaid all
  updated.

* Thu May 14 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-61
- Tag three more carry-patches as TIMEBOMB after upstream merges
  landed on development today (2026-05-14):
  - Patch0001 (clang21 -Wno-error=) <- o3de/o3de#19748 (commit c2486d165441)
  - Patch0002 (manifest.py O3DE_ENGINE_PATH) <- o3de/o3de#19751 (commit 0281a9bbc492)
  - Patch0005 (AzQtComponents title) <- o3de/o3de#19750 (commit d8d1c9aeb1c6)
  All three target `development`; none has been cherry-picked into
  `stabilization/26050` (our snapshot source branch), so the local
  patches stay active until our snapshot pin re-pins post-2605.0
  release. nick-l-o3de informally flagged #19748 (Patch0001) as a
  possible stabilization cherry-pick for 2605.0 ("we may need this one
  for this release"); if that cherry-pick lands, Patch0001 retires
  early once we re-snapshot stabilization tip.
- TIMEBOMB total goes from 2 (Patch0007 + Patch0008, from 2026-05-08
  merges) to 5. README + CONTRIBUTING patch tables updated with the
  new TIMEBOMB notes + merge-commit cross-refs.

* Thu May 14 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-60
- Promote Stage 1 14-pack + Stage 2 3-pack to stabilization in one push.
  First superseded attempt (10459564, Stage 1 only) was cancelled when
  the decision shifted to bundle Stage 2 in the same promotion.
- Stage 1 14-pack: system_vulkan_validation_layers added on top of the
  13-pack already in stabilization (Patch0013 v4 + experimental build
  10457745 GREEN across all three chroots 2026-05-14 04:03 UTC).
- Stage 2 3-pack: system_dxc + system_spirvcross + system_mcpp promoted
  from experimental after 6+ days of green soak (all three PoCs ✓ GREEN
  since 2026-05-08). Requires the o3de-dependencies COPR repo to be
  pulled in via additional_repos at chroot config (set 2026-05-14 via
  one-time `copr-cli edit-chroot --repos copr://hellaenergy/o3de-dependencies`
  on all three stabilization chroots).
- Net stabilization chroot state: 18 with_opts per chroot (stabilization
  + 14 Stage 1 + 3 Stage 2); F44/rawhide/CS10 all in parity. CS10
  with_opts gap fully closed earlier today.
- CI updates landed in same commit to keep test workflows consuming the
  expanded build correctly.

* Thu May 14 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-59
- (Superseded by 2605.0-60.) Stage 1 14-pack only stabilization promotion;
  build 10459564 cancelled before terminal state when decision shifted
  to bundle Stage 2 in the same push.

* Wed May 13 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-58
- Patch0013 v4: add third hunk gating the
  Gems/Atom/RHI/Vulkan/Code/Source/Platform/Linux/PAL_linux.cmake
  VULKAN_VALIDATION_LAYER variable on LY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS.
  Build 10456101 (v3) failed at cmake configure with
  "Findvulkan-validationlayers.cmake must either be part of this project
  itself..." because the gem's BUILD_DEPENDENCIES list referenced
  ${VULKAN_VALIDATION_LAYER} which was still set to
  3rdParty::vulkan-validationlayers. ly_parse_third_party_dependencies
  walked the list and called find_package(vulkan-validationlayers), no
  shim found, configure aborted. v4 leaves VULKAN_VALIDATION_LAYER unset
  in system mode so the BUILD_DEPENDENCIES list expansion has no
  validation-layer entry at all.
- Bonus: build 10456101's CS10 chroot went GREEN with 17 system swaps
  active (first end-to-end CS10 validation of the Stage 1 + Stage 2
  stack). Stage 1 viability on CentOS Stream 10 confirmed.

* Wed May 13 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-57
- Add Patch0013 + system_vulkan_validation_layers Stage 1 swap. Engine
  gets a two-hunk carry-patch (gate the bundled vulkan-validationlayers
  ly_associate_package on LY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS, plus
  flip the Atom RHI Vulkan Instance.cpp SetEnv("VK_LAYER_PATH", ..., 1)
  to overwrite=0 so packager-set VK_LAYER_PATH is respected). Validation
  layers are runtime-only -- no BuildRequires needed; only Requires
  vulkan-validation-layers when the bcond is active.
- Launcher wrapper (sources/o3de-launcher.sh) now sets
  VK_LAYER_PATH=/usr/share/vulkan/explicit_layer.d when not already set
  AND that directory exists. Pairs with the Patch0013 overwrite=0 fix
  so the system Vulkan loader's standard layer-discovery path wins
  over the engine's exeDirectory default. No-op when VK_LAYER_PATH is
  user-set (preserves developer overrides) or the system path doesn't
  exist (bundled-engine installs unaffected).
- 14th Stage 1 system swap candidate. NOT activated in stabilization
  by default for the mid-release-window rule; ships as bcond, opt-in
  via `--with system_vulkan_validation_layers` on experimental chroot.
  Upstream pitch pending Nick's "fully baked" green-light.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-56
- REVERT the same-turn retirements of Patch0007 (libtiff C99 migration)
  and Patch0008 (drop Lua/lobject.h include) made in 2605.0-54 and
  2605.0-55. Both retirements were premature: upstream merged PRs
  #19734 and #19733 into `development` on 2026-05-08, but neither was
  cherry-picked to `stabilization/26050`, which is the branch our
  snapshot pin (246b46f) sources from.
- Verified by grepping `upstream/stabilization/26050`: TIFFLoader.cpp
  still has 9 legacy uint8/uint16/uint32 typedef hits, ImageTIF.cpp
  has 33, and ScriptContext.cpp still has `#include <Lua/lobject.h>`
  on line 28. Without these patches, our builds against the
  stabilization snapshot would hit the original compile failures
  (clang -Werror on the deprecated typedefs + system_lua activation
  blocker on the bundled-Lua internal header).
- Patch directives restored; spec is back to 12 active patches. Both
  patch bodies now carry TIMEBOMB notes documenting the merge-but-
  not-backported situation and the retirement condition (when
  stabilization/26050 absorbs the upstream change, OR when our
  snapshot pin advances onto a development-based commit that
  includes both PRs).
- Gotcha captured as memory note
  project_branch_alignment_before_retirement.md so future "carry-
  patch retired by upstream merge" decisions verify the merge
  landed on the SAME branch the snapshot sources from -- not just
  in `development`. Sweep order for safe retirement:
  (1) confirm PR merged upstream -> (2) confirm the merge commit is
  reachable from the branch our snapshot pin is on -> (3) grep the
  target file on that branch to confirm the change is present ->
  (4) only then retire the carry-patch.
- README + CONTRIBUTING patch tables restored to show 0007 + 0008
  ACTIVE with TIMEBOMB notes. Active patch count back to 12.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-55
- Retire Patch0008 (AzCore/Script drop redundant Lua/lobject.h
  include). Upstream landed PR o3de/o3de#19733 (commit 3e715c61) on
  2026-05-08 with the identical change. Our carry-patch is now dead
  code; directive commented out in spec so %%autosetup skips it.
  Patch file retained in sources/ for historical reference.
- Discovered during a sweep for already-upstreamed carry-patches
  alongside today's deps-drift + upstream-pitch preparation. Second
  retirement today after Patch0007 (libtiff C99 typedefs) earlier;
  both upstream landings were on 2026-05-08 -- a productive day for
  the Fedora-packaging compatibility track. README + CONTRIBUTING
  patch tables updated to mark 0008 RETIRED with cross-link to
  #19733.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-54
- Retire Patch0007 (libtiff C99 typedef migration). Upstream landed
  the equivalent change on 2026-05-08 as PR o3de/o3de#19734
  (dda736e0, "libtiff: migrate legacy typedefs to C99 standard
  types"); our carry-patch is now dead code. Directive commented out
  in spec so %autosetup skips it. Patch file retained in sources/ as
  historical reference.
- Discovered during the upstream-pitch preparation pass: rebasing our
  libtiff-c99-typedef-migration branch onto current upstream/development
  caused git to report "skipped previously applied commit" via
  cherry-pick equivalence detection. Verified by grepping
  upstream/development for the legacy uint8/uint16/uint32 typedefs
  (none remain) + reading the resulting upstream commit message.
- README + CONTRIBUTING patch tables updated to show 0007 RETIRED.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-53
- Add `BuildRequires: gcc-toolset-15-libatomic-devel` gated on
  `%%if 0%%{?rhel}`. CS10 engine compile reached step 44/2173
  (libAzCore.so link) in build 10447331 for the first time and failed
  with `ld: cannot find -latomic` -- the SCL's linker can't resolve
  the bare -latomic without the SCL's libatomic dev symlink, which
  ships in the -libatomic-devel package. Fedora chroots don't need
  this gate (base libatomic / libatomic-static covers the bare -l).
- Memory: project_cs10_engine_build_blockers.md blocker #5.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-52
- Reapply Patch0012 with v2 approach: child-side parent-death watchdog
  in AssetBuilder/main.cpp instead of the engine's m_tetherLifetime /
  prctl(PR_SET_PDEATHSIG) mechanism.
- v1 (2605.0-50) misused prctl which binds the death signal to the
  forking thread's TID rather than the parent process; AssetProcessor
  forks builders from short-lived TaskWorker threads, so v1 SIGTERM'd
  every spawned builder within ~21 ms of fork. Editor hung at "Asset
  Processor working...".
- v2 sidesteps the thread-lifetime trap entirely: the spawned
  AssetBuilder polls getppid() on a detached thread every 2 seconds
  and _exit(0)s when reparented. ~12 LOC of watchdog in
  Code/Tools/AssetProcessor/AssetBuilder/main.cpp. Cross-platform
  POSIX (Linux + Mac); Windows port deferred.
- Upstream-drafts (issue + 2 PRs) staged in upstream-drafts/ -- not
  filed until v2 passes the kill -9 + orphan-count runtime test
  locally.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-51
- WITHDRAW Patch0012 after empirical runtime validation. Build was green
  on F44 + rawhide (COPR 10447331), but on `dnf reinstall` + AP launch
  the kernel killed every spawned AssetBuilder with SIGTERM within ~21 ms
  of fork. AP could never establish its resident pool; Editor hung at
  "Asset Processor working...".
- Root cause: PR_SET_PDEATHSIG (which m_tetherLifetime sets on Linux)
  fires when the THREAD that called fork() terminates, not when the
  parent process terminates. AssetProcessor forks builders from
  short-lived BuilderManager worker threads; the launching thread
  retires as soon as the builder is spawned, the kernel signals the
  freshly-spawned builder, builder dies, AP gives up. The Multiplayer
  gem's use of m_tetherLifetime works because it forks from a long-lived
  UI thread.
- Spec keeps the Patch0012 file in sources/ for reference; the directive
  is commented out so %autosetup skips it. README + CONTRIBUTING patch
  tables annotated as WITHDRAWN.
- Replacement under design: watchdog approach -- have AssetBuilder poll
  getppid() in its main loop and exit when it returns 1 (reparented).
  Cross-platform safe and independent of the launching thread's
  lifetime. Tracked in FOLLOW_UPS.md.

* Tue May 12 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-50
- Add Patch0012: AssetProcessor tethers its resident AssetBuilder
  children via ProcessLauncher's existing m_tetherLifetime flag, so
  the kernel sends SIGTERM to each builder when AP dies. Fixes orphan
  accumulation across AP restarts (saw 18 in one batch + 3 more in the
  next AP-restart cycle during the 2026-05-12 ROS2_Project session).
- The engine's ProcessWatcher already implements this on Linux
  (prctl(PR_SET_PDEATHSIG)), Windows, and Mac; only the Multiplayer
  gem was opting in. AssetProcessor's Builder::LaunchProcess just
  needed the same single-line opt-in.
- One-line cross-platform engine change; no Linux-specific guards in
  our carry-patch. Memory note:
  project_assetbuilder_orphan_lifecycle_bug.md.
- Pitched upstream as a tidy-up rather than a Linux-only workaround;
  if accepted, this carry-patch retires.

* Mon May 11 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-49
- Add missing `Recommends: o3de2605-mcpp-az-devel` for the system_mcpp
  gate. Same class of issue as 2605.0-48 (system_googlebenchmark
  Recommends gap) -- caught when Nick's cmake-configure of his ROS2
  project hit `Findmcpp (system stub): could not locate mcpp_lib.h`.
  The mcpp Stage 2 swap is a LIBRARY-LINK variant (engine #includes
  <mcpp_lib.h>); end-user cmake-configure of native projects that go
  through Findmcpp-system.cmake needs the headers. The runtime
  libmcpp.so.0 was already pulled via Requires; this fills the
  parallel Recommends gap.
- The other two Stage 2 swaps (system_dxc + system_spirvcross) are
  BINARY-SHELLOUT variants -- they ship CLI executables (dxc,
  spirv-cross) that the engine invokes as subprocesses; no header
  surface for downstream consumers; no parallel -devel Recommends
  needed.
- Quick unblock for users hitting this on 18-pack installed before
  this commit: `sudo dnf install o3de2605-mcpp-az-devel`.

* Mon May 11 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-48
- Add missing `Recommends: google-benchmark-devel` for the
  system_googlebenchmark gate. Caught when a tester's CMake configure
  failed with `FindGoogleBenchmark (system stub): could not locate
  benchmark/benchmark.h` against the freshly-installed 18-pack
  (build 10444166); the spec already had BuildRequires (for the
  engine's own build) and Requires (for runtime libbenchmark.so.1)
  but NOT Recommends, so end users got the runtime .so via auto-
  Requires but were missing the headers needed for native gem
  cmake-configure (which uses Fedora's google-benchmark-devel via
  FindGoogleBenchmark-system.cmake). The other 12 active Stage 1
  swaps all have Recommends entries for their *-devel packages;
  this is the parallel entry for the 13th swap.

* Mon May 11 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-47
- system_googlebenchmark Stage 1 swap ACTIVATED in experimental
  (plumbing landed 2026-05-08 as 2605.0-43 but bcond was OFF). Added
  to SRPM_EXPERIMENTAL_FLAGS in Makefile and to the o3de-experimental
  COPR chroot config (F44 + rawhide; CS10 paused per FOLLOW_UPS).
  Replaces the closed PR #19738's intent in the architecturally-
  correct shape -- the engine still ships AzTest + AzTestRunner + the
  googletest/googlemock/googlebenchmark stack (per
  `project_az_test_runner_architecture.md`), but the linkage now
  pulls Fedora's `google-benchmark-devel` instead of the bundled
  fetch. Linkage variance: Fedora ships only libbenchmark.so (no
  libbenchmark.a), so AzTestRunner ends up dynamically linked rather
  than statically. gbench's API is stable across the 1.7.0 (engine
  pin) -> 1.9.5 (Fedora ship) range.
- Stabilization channel promoted 7-pack -> 12-pack on 2026-05-11
  (added system_assimp + system_libsamplerate + system_lua +
  system_poly2tri + system_sqlite to the existing 7). Mirrors what
  was already validated end-to-end on experimental as of
  2026-05-08 (builds 10433646 12-pack + later 14-pack at 10442708).
  Per `project_active_community_testers.md` the 7-pack has had >1
  week soak with no community-reported regressions. Mechanical:
  extended `o3de-stabilization` F44 + rawhide chroots' with_opts list
  + added explicit `SRPM_STABILIZATION_FLAGS` to Makefile so
  `make srpm-stabilization` produces an SRPM that matches the chroot.
  Stage 2 swaps (mcpp/dxc/spirvcross) deliberately stay in
  experimental until they soak longer.

* Sun May 10 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-46
- CS10 / RPM 4.19 fix (round 2): bulk-escape literal section-keyword
  tokens (%%install / %%build / %%files / %%prep / %%check / %%package /
  %%description / %%post / %%postun / %%clean / %%changelog) ANYWHERE
  they appear in comments + changelog, not just inside the active
  %%install block. The 2605.0-45 fix only addressed the one comment at
  line 1087 that was tripping CS10 build 10439258. Empirical evidence
  from mcpp CS10 build 10442715 (rev9, post-fix-attempt) shows RPM 4.19
  misparses unescaped section tokens ANYWHERE in the spec -- the next
  build would have tripped on my own 2605.0-45 changelog entry which
  itself contained six unescaped %%install references while describing
  the fix. RPM 6.x (F44 + rawhide) is lax about in-comment tokens and
  parses cleanly. 26 lines total bulk-escaped in this pass via a regex
  transform that preserves real section headers (lines starting with
  `%%<keyword>` followed by whitespace or EOL).
- This commit is companion to the mcpp rev10 spec change (same shape,
  same root cause). Memory note `project_cs10_debuginfo_quirk.md`
  updated with the broader scope.

* Sun May 10 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-45
- CS10 RPM 4.19 spec-parse fix: rephrase a comment inside the %%install
  block that contained the literal token "%%install" (in the phrase
  "Per-version mutation lands here at %%install time:"). RPM 4.19 (which
  CentOS Stream 10 ships) parses unescaped "%%install" anywhere inside an
  active %%install block as a section-start marker, producing
  `error: line 1087: second %%install` at SRPM build. RPM 6.x (F44 +
  rawhide) ignores the in-comment token and parses cleanly. Caught on
  build 10439258 CS10 chroot (failed at SRPM-prep in 134s; F44 +
  rawhide of the same build instead progressed to the engine-build
  + packaging finish line before hitting the 5h COPR wall-clock).
- Comment rephrased to drop the percent sign and now also documents the
  RPM 4.19 quirk inline so future edits don't reintroduce the pattern.
- Other "%%install" tokens elsewhere in the spec (lines 455, 524, and the
  changelog itself) sit outside the active %%install block and are not
  affected by the RPM 4.19 parser bug. No change needed there.
- No code changes; documentation-only fix in the spec.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-44
- Patch0011: Lua 5.5 LUA_NUMTAGS compat fix in
  Code/Tools/LuaIDE/Source/LUA/WatchesPanel.cpp. Sibling to Patch0010
  (lua_newstate signature) but covers a separate Lua 5.5 API break:
  the LUA_NUMTAGS public macro was dropped in 5.5 (had been retained
  in 5.4 as a deprecation-alias for LUA_NUMTYPES). WatchesPanel.cpp
  references LUA_NUMTAGS at two sites (a `c > LUA_NUMTAGS` bounds
  check and a `static_assert` on typeStringLUT size). Patch adds a
  one-line `#define LUA_NUMTAGS LUA_NUMTYPES` shim guarded on
  `#if LUA_VERSION_NUM >= 505 && !defined(LUA_NUMTAGS)` right after
  the lua.h include, so existing call sites compile unchanged.
- Caught on COPR build 10437498 (o3de-experimental, fedora-rawhide
  chroot, 2026-05-08; the chain-built validation run for the Stage 2
  rename + Patch0010 + system_mcpp). Patch0010 covered the engine
  link in ScriptContext.cpp but the build progressed past that to
  trip on this LuaIDE compile site. F44 chroot of the same build
  separately failed with "Build root is locked by another process"
  (transient COPR/mock infrastructure flake; not our code) -- the
  next experimental build should succeed on F44 cleanly.
- Caveat: there may be MORE Lua 5.5 break sites in the engine that
  we haven't tripped on yet because they live in even-later-built
  source files. Right way to find them all is `grep -rn LUA_NUMTAGS
  Code/ Gems/` against the engine source on a CS10/F45-class
  lua-devel-5.5 sysroot. Phase 2 (CS10 iteration) work; not blocking
  this fix.
- SBOM bumped 2605.0-43 -> 2605.0-44.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-43
- Add system_googlebenchmark Stage 1 swap (PLUMBING ONLY -- bcond is OFF
  by default; not yet activated in SRPM_EXPERIMENTAL_FLAGS or any chroot
  config). Replaces what closed PR #19738 was originally trying to
  achieve, but in the architecturally-correct shape Nick_L pointed us
  toward: gbench is a build+ship dep of the engine even with
  LY_DISABLE_TEST_MODULES=ON because AzTestRunner + AzTest ship
  unconditionally for external gem developers. So the right move isn't
  to GATE the bundled fetch on test modules; it's to SWAP the bundled
  fetch for Fedora's google-benchmark-devel.
- Plumbing wired: %bcond_with system_googlebenchmark, OR-chain extension,
  Source45 declaration of FindGoogleBenchmark-system.cmake, conditional
  cp in %%prep, BR google-benchmark-devel, Requires google-benchmark,
  cmake -DLY_USE_SYSTEM_GOOGLEBENCHMARK=ON, Patch0006 hunk gating the
  ly_associate_package(googlebenchmark-1.7.0-rev1-linux). Hunk header
  bumped -17,30 +17,82 -> -17,30 +17,86 (+4 lines for the gate).
- Linkage variance noted: Fedora ships ONLY libbenchmark.so (no -static
  subpackage), so AzTestRunner ends up dynamically linked rather than
  having gbench compiled in statically. gbench's API is stable across
  1.7.0 (engine pin) -> 1.9.5 (Fedora ship) and the consumed surface
  (BENCHMARK macros + benchmark::internal::InitializeStreams) is core
  public API, so the variance is acceptable.
- Activation deferred: this commit is plumbing-only so today's chain-
  built 15-pack experimental (10437498, validating rename + Patch0010 +
  system_mcpp) is not affected. The bcond can be flipped on in a
  separate commit once that build lands green and we've smoke-tested
  the swap independently.
- Drift-script side: dep-map.yaml updated to add googlebenchmark to
  spec_bcond_aliases and to remove it from ignore_engine_packages so
  the next drift run reclassifies the GoogleBenchmark engine pin as
  covered-by-spec.
- Sibling note: the missing-libbenchmark.a-archive bug surfaced 2026-05-08
  and filed as o3de/o3de#19740 is a SEPARATE issue. With the system swap
  on, an external gem developer can satisfy benchmark links via Fedora's
  google-benchmark-devel directly even if the engine's own install set
  is missing libbenchmark.a -- partial mitigation, but #19740 is still
  the right fix on the engine side.
- SBOM bumped 2605.0-42 -> 2605.0-43.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-42
- Versioned-major rename of the Stage 2 COPR-shipped 3rdParty deps to
  match the engine package's o3deNNNN naming convention:
    o3de-spirv-cross  -> o3de2605-spirv-cross    (rev2 -> rev3)
    o3de-dxc-spirv    -> o3de2605-dxc-spirv      (rev12 -> rev13)
    o3de-mcpp-az      -> o3de2605-mcpp-az        (rev7 -> rev8)
    o3de-mcpp-az-devel -> o3de2605-mcpp-az-devel
  Each renamed package carries Obsoletes + Provides headers so dnf
  upgrade transitions seamlessly from PoC iterations on the unversioned
  names. Same shape as Fedora's postgresql10/postgresql10-server family
  pattern, mirroring upstream's CDN model where multiple engine-major
  lines pin different package versions side-by-side.
- Engine-side spec updates: BuildRequires + Requires lines for the three
  Stage 2 deps now reference the o3de2605-* names. The Find shims
  (Findmcpp-system.cmake) are unchanged -- they query system paths
  (/usr/include, /usr/lib64), not COPR package names.
- Why now: the three Stage 2 PoCs landed within the past 36 hours
  (spirv-cross 2026-05-07, dxc + mcpp 2026-05-08); naming convention had
  not yet hardened anywhere. Cost of changing now (~10 testers, three
  packages, ~50 min runner time) is dramatically lower than after 26.10
  ships and forces a hot migration. Empirical research + decision
  rationale captured in memory note
  `project_o3de_3p_versioning_research.md`.
- 26.05.x point releases (26.05.0, 26.05.1, ...) all share the same
  o3de2605-<dep> packages. Engine-team's empirical 3p-pin update cadence
  is a few times per year, not per release; within-major drift is
  near-zero. Same as how postgresql10 covers 10.0 through 10.23 over
  its support window.
- SBOM bumped 2605.0-41 -> 2605.0-42.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-41
- Patch0010: Lua 5.5 lua_newstate signature compat. Lua 5.5 (released
  ahead of Fedora 45) added a required third `seed` parameter to
  `lua_newstate`; engine's `Code/Framework/AzCore/AzCore/Script/
  ScriptContext.cpp:4359` calls the 5.4 two-arg form. Patch wraps in
  `#if LUA_VERSION_NUM >= 505` guard, passes seed=0 on 5.5+, falls
  through to original on 5.4. Behavior-preserving on bundled-Lua
  builds; lifts the rawhide compile failure caught on build 10436540
  (o3de-experimental 14-pack, fedora-rawhide chroot, 2026-05-08;
  F44 succeeded with bundled lua-5.4.8, rawhide failed at
  ScriptContext.cpp:4359 with "no matching function for call to
  'lua_newstate' ... requires 3 arguments, but 2 were provided").
- Independent of `system_lua` bcond: applies unconditionally, fires
  whether the engine links bundled Lua or system Lua. Sibling to
  Patch0008 (Lua/lobject.h include cleanup) but addresses a separate
  concern (API signature drift across Lua majors).
- Memory note: `project_lua_5_5_newstate_break.md`. Worth pitching
  upstream once the patch shape settles -- benefits every distro on
  the rawhide Lua 5.5 trajectory (Fedora 45+, Debian unstable,
  Alpine edge, Arch).
- SBOM bumped 2605.0-40 -> 2605.0-41.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-40
- Stage 2 third swap: activate system_mcpp. Library-link variant of
  the DXC-class binary-only pattern (vs. system_spirvcross +
  system_dxc which are binary shellouts). Routes the engine's mcpp
  consumption (Gems/Atom/Asset/Shader/Code/Source/Editor/CommonFiles/
  Preprocessor.cpp's mcpp_lib_main / mcpp_set_out_func /
  mcpp_set_report_include_callback calls) to the system libmcpp.so
  from o3de-mcpp-az-devel (license-clean rebuild of upstream mcpp
  2.7.2 + o3de/3p-package-source's _az.2 patch series; ✓ green PoC
  build 10436752 since 2026-05-08, F44 + rawhide).
- Implementation pattern: same as system_assimp / system_libsamplerate
  / system_sqlite (mikkelsen-style Find shim + Patch0006 gate). Unlike
  system_spirvcross / system_dxc, mcpp is linked into the engine
  binary at build time rather than shelled out to at runtime, so the
  install-overlay approach does not apply. We need a real Find shim
  + cmake gate to skip the bundled fetch and link against the system
  library at configure time.
- Patch0006 extension: add `LY_USE_SYSTEM_MCPP` gate hunk for the
  mcpp-2.7.2_az.2-rev1-linux ly_associate_package. Hunk header bumped
  -17,30 +17,78 -> -17,30 +17,82 (+4 lines: if/else/find_package/endif).
- New sources/Findmcpp-system.cmake (Source44), mikkelsen pattern
  creating 3rdParty::mcpp directly via find_path / find_library on
  /usr/include/mcpp_lib.h + /usr/lib64/libmcpp.so. No cmake-stock
  Findmcpp module exists (mcpp is abandonware-class) so direct lookup
  is the only option.
- Spec wires: %bcond_with system_mcpp, OR-chain extension, Source44
  declaration, conditional cp in %%prep, BuildRequires o3de-mcpp-az-devel,
  Requires o3de-mcpp-az, conditional cmake -DLY_USE_SYSTEM_MCPP=ON.
- Makefile: add system_mcpp to spec-parse-experimental's --define list,
  to SRPM_EXPERIMENTAL_FLAGS, and to copr-init's chroot --rpmbuild-with
  hint. Engine now consumes 12 Stage 1 system libs + 3 Stage 2 PoC-
  rebuilt COPR deps (spirvcross + dxc binary, mcpp library) for a
  15-pack experimental config (was 14-pack before today's commit).
- This completes the Stage 2 swap set: two binary shellouts
  (spirvcross + dxc) + one library link (mcpp). Both architectural
  variants now have working engine-side glue.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-39
- Stage 2 second binary-only swap: activate system_dxc. Routes the
  engine's runtime DXC invocations to the COPR-built /usr/bin/dxc
  (and dxsc, libdxcompiler.so) from the o3de-dxc-spirv package
  (sibling COPR project hellaenergy/o3de-dependencies, license-clean
  NCSA + Apache-2.0 with LLVM-exception, ✓ green PoC build 10435628
  since 2026-05-08).
- Implementation: %%install creates symlinks at the engine's expected
  runtime paths (Builders/DirectXShaderCompiler/{bin/dxc, bin/dxsc,
  lib/libdxcompiler.so} under the install prefix) to the system
  locations. Same install-overlay pattern as system_spirvcross
  (2605.0-38) but with three paths instead of one. Engine's path
  resolution (RHI::ExecuteShaderCompiler in
  Gems/Atom/RHI/Code/Source/RHI.Edit/Utils.cpp) follows the symlinks
  transparently; engine code unchanged. Per
  `project_dxc_binary_only_dependency.md` memory + Nick_L's 2026-05-05
  sig-build comment, the engine doesn't link DXC -- shells out to the
  binary. So binary swap at install time is sufficient.
- Spec wires: %bcond_with system_dxc, OR-chain extension, conditional
  BR/Requires o3de-dxc-spirv, conditional %%install symlinks (3 paths
  for profile config + 3 for debug under --with debug).
- This completes the Stage 2 binary-only set (SPIRV-Cross + DXC).
  Both PoC builds in hellaenergy/o3de-dependencies now have engine-side
  glue to consume them via system installs. The mcpp PoC (library-link
  variant per audit 2026-05-08) follows the same pattern but stays
  deferred per FOLLOW_UPS.md.
- SBOM bumped 2605.0-38 -> 2605.0-39.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-38
- Stage 2 first binary-only swap: activate system_spirvcross. Routes
  the engine's runtime spirv-cross invocations to the COPR-built
  /usr/bin/spirv-cross from the o3de-spirv-cross package
  (sibling COPR project hellaenergy/o3de-dependencies, license-clean
  Apache-2.0 OR MIT, ✓ green PoC build 10434617 since 2026-05-07).
- Implementation: %%install creates a symlink at the engine's expected
  runtime path
  (%{o3de_install_prefix}/bin/Linux/profile/Default/Builders/SPIRVCross/spirv-cross)
  to /usr/bin/spirv-cross. Engine's path resolution
  (RHI::ExecuteShaderCompiler in
  Gems/Atom/RHI/Code/Source/RHI.Edit/Utils.cpp) follows the symlink
  transparently. Per the 2026-05-07 audit, the engine treats
  spirv-cross as a binary executable shellout (zero #include lines for
  SPIRV-Cross C++ headers anywhere in Code/ or Gems/), so binary
  swap at install time is sufficient -- no engine code changes needed.
- Why not gate the upstream fetch via Patch0006: the bundled package
  contains a FindSPIRVCross.cmake that creates the 3rdParty::SPIRVCross
  cmake target the engine needs at configure time; gating the fetch
  without an equivalent target shape would break cmake config. Future
  cleanup: write a Findspirvcross-system.cmake shim that creates the
  IMPORTED EXECUTABLE target, gate Patch0006, drop the upstream fetch
  entirely. For the PoC, the install-time overlay is enough to validate
  the engine -> COPR PoC integration path end-to-end.
- Spec wires: %bcond_with system_spirvcross, OR-chain extension,
  conditional BR/Requires o3de-spirv-cross, conditional %%install
  symlink (profile + debug configs).
- This is the FIRST Stage 2 binary-only swap activation. DXC PoC
  rev12 (✓ green 2026-05-08) follows the same shape; engine-side
  glue for it lands as a future commit (same install-overlay
  approach for /usr/bin/dxc + /usr/lib64/libdxcompiler.so).
- SBOM bumped 2605.0-37 -> 2605.0-38.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-37
- Stage 1 12-pack: activate system_assimp. Audit (2026-05-07,
  /tmp/o3de-assimp-audit/INVESTIGATION_NOTES.md) confirmed: engine
  consumes assimp exclusively in Code/Tools/SceneAPI/SceneBuilder/
  + Code/Tools/SceneAPI/SDKWrapper/ (asset-pipeline 3D-model importer
  for FBX/glTF/OBJ/Collada); zero refs in Gems/, zero in core
  Code/Framework/. All 27 unique types + 7 processing flags consumed
  are public ai* C-API and Assimp::Importer C++ class; 100% present
  in Fedora 6.0.4 headers. Engine include style `<assimp/header.h>`
  matches Fedora's `/usr/include/assimp/header.h` layout exactly —
  no path-bridging needed. FBX importer compiled into Fedora's
  libassimp.so.6.0.4 (verified via importer-descriptor strings).
- Patch0006 extension: add `LY_USE_SYSTEM_ASSIMP` gate hunk for the
  assimp line in BuiltInPackages_linux_x86_64.cmake.
- New sources/Findassimp-system.cmake (Source43), mikkelsen pattern
  (direct find_path/find_library, creates 3rdParty::assimp directly).
  Necessary because Fedora's `assimpConfig.cmake` creates `assimp::assimp`
  as a side-effect IMPORTED target which trips O3DE's runtime walker
  (same reason as ZLIB/SQLite shims). Mikkelsen-pattern shim sidesteps.
- Caveat: 5.4 → 6.0 major version delta. Symbols verified ✓; runtime
  FBX-import behavior on tricky inputs (subdivision surfaces, layered
  animations, embedded textures) is **unverified**. Mitigation: pair
  with a Tier 6 integration test that bakes a known FBX from
  AutomatedTesting Gem (FOLLOW_UPS.md item; not in this commit).
- Spec wires: %bcond_with system_assimp, OR-chain extension, Source43
  declaration, conditional BR/Recommends assimp-devel, conditional
  Requires assimp, conditional cmake -DLY_USE_SYSTEM_ASSIMP=ON,
  conditional %%prep cp.
- License: assimp is BSD-3-Clause, Fedora-acceptable.
- SBOM bumped 2605.0-36 → 2605.0-37.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-36
- Stage 1 11-pack: activate system_libsamplerate. Audit (2026-05-07,
  /tmp/o3de-assimp-audit/LIBSAMPLERATE_INVESTIGATION_NOTES.md) confirmed
  this is the lowest-risk Stage 1 swap to date — engine consumes
  libsamplerate exclusively in Gems/Microphone/, and the Microphone
  Gem's Linux PAL points to MicrophoneSystemComponent_None.cpp (a
  do-nothing stub). Zero `src_*` function calls in the Linux runtime
  path; the Gem's CMakeLists.txt:25 unconditionally LINKS
  3rdParty::libsamplerate but no engine code path on Linux exercises
  the library at runtime.
- Patch0006 extension: add `LY_USE_SYSTEM_LIBSAMPLERATE` gate hunk
  for the libsamplerate line in BuiltInPackages_linux_x86_64.cmake.
- New sources/Findlibsamplerate-system.cmake (Source42), mikkelsen
  pattern: direct find_path/find_library, creates
  3rdParty::libsamplerate directly. libsamplerate doesn't ship a
  stock cmake module (pkg-config available at
  /usr/lib64/pkgconfig/samplerate.pc as a fallback).
- Spec wires: %bcond_with system_libsamplerate, OR-chain extension,
  Source42 declaration, conditional BR/Recommends libsamplerate-devel,
  conditional Requires libsamplerate, conditional cmake -DLY_USE_SYSTEM_LIBSAMPLERATE=ON,
  conditional %%prep cp.
- 0.2.1 → 0.2.2 is patch-version increment within libsamplerate's
  23-year ABI-stable major (since 0.1.0, 2002). License: BSD-2-Clause
  (Erik de Castro Lopo, libsndfile author) — Fedora-acceptable.
- Upstream-PR follow-on (not in this commit): gate the
  3rdParty::libsamplerate dependency in Microphone's CMakeLists.txt
  on a PAL_TRAIT_MICROPHONE_USES_LIBSAMPLERATE flag (FALSE on
  Linux/None, TRUE elsewhere) — drops the dependency entirely on
  Linux. Same shape as the AzCore Lua PR (#19733).
- SBOM bumped 2605.0-35 → 2605.0-36.

* Fri May 08 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-35
- Stage 1 10-pack: activate system_sqlite. Audit (2026-05-07) confirmed
  SQLite is the cleanest Stage 1 candidate to date — consumers
  exclusively in Code/Framework/AzToolsFramework/SQLite/ + Code/Tools/
  AssetProcessor/AssetDatabase/ (editor/tool framework, not runtime
  engine). All 29 unique sqlite3_* symbols are core public C-API; 100%
  present in Fedora 3.51.2 headers. Zero extension-only API used
  (no FTS5/RTREE/JSON1/SEE). 3.37 → 3.51 is point-version increment
  within SQLite's 21-year ABI-stable major (since 3.0.0, 2004).
- Patch0006 extension: add `LY_USE_SYSTEM_SQLITE` gate hunk for the
  SQLite line in BuiltInPackages_linux_x86_64.cmake. Same shape as the
  existing 9 gates (mikkelsen, expat, zlib, freetype, png, tiff, lua,
  lz4, openexr — and via Patch0009 as a sibling, poly2tri).
- New FindSQLite-system.cmake (Source41): mikkelsen pattern — direct
  find_path/find_library, creates 3rdParty::SQLite directly. Necessary
  because cmake's stock FindSQLite3.cmake creates SQLite::SQLite3 as a
  side-effect IMPORTED target which trips O3DE's runtime walker (same
  pattern as FindZLIB shim). Engine consumes `3rdParty::SQLite` from
  Code/Framework/AzToolsFramework/CMakeLists.txt:54 and
  Code/Tools/AssetProcessor/CMakeLists.txt:37.
- Spec wires: `%bcond_with system_sqlite`, OR-chain extension, Source41
  declaration, conditional BR/Recommends `sqlite-devel`, conditional
  Requires `sqlite-libs`, conditional `cmake -DLY_USE_SYSTEM_SQLITE=ON`,
  conditional %%prep cp.
- Engine has an exact-match `sqlite3_libversion_number() ==
  SQLITE_VERSION_NUMBER` runtime assertion in
  AzToolsFramework/SQLite/SQLiteConnection.cpp — automatically satisfied
  by paired system header+library; not a blocker.
- SBOM bumped 2605.0-34 → 2605.0-35. Channel-marker OR-chain extended.

* Thu May 07 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-34
- Docs sharpen: BUNDLED_LIBRARIES.md absorbs the SQLite + libsamplerate +
  SPIRVCross audit findings (2026-05-07). No code/build changes; spec
  change is the changelog entry only.
- SQLite (cleanest Stage 1 candidate to date): consumers in
  AzToolsFramework/SQLite/ + AssetProcessor/AssetDatabase/ only;
  all 29 sqlite3_* symbols are public C-API and 100% present in Fedora
  3.51.2 headers; stock cmake FindSQLite3 ships — no Find shim needed;
  point-version increment within SQLite's 21-year ABI-stable major.
- libsamplerate: Stage 1 viable + upstream-PR opportunity (same shape
  as the AzCore Lua PR #19733). Single Gem (Microphone); engine actually
  calls src_* functions only on Windows. Linux PAL is a do-nothing stub
  — zero libsamplerate function calls in the Linux runtime path.
- SPIRVCross reclassified out of "Migrate to system Fedora libs (Stage
  1)" into a new "Binary-only / DXC-class dependencies" section. Audit
  found: (a) Fedora F44 doesn't ship SPIRV-Cross at all (the previous
  "Fedora 1.3.x — trivial flip" annotation was wrong); (b) engine
  treats SPIRV-Cross as an executable, not a library — zero #include
  lines for SPIRV-Cross C++ headers anywhere; (c) license is
  Apache-2.0 (Fedora-acceptable in principle), so blocker is
  availability not license — different category from DXC's DXIL-signing
  blocker. Path: license-clean COPR rebuild as o3de-spirv-cross,
  sibling track to o3de-dxc-spirv PoC.
- Audit-pattern reliability tracker (2026-05-07): seven audits, three
  outcome categories — Stage 1 swap (assimp/SQLite/libsamplerate/poly2tri),
  carry-patch+PR (Lua, libsamplerate follow-on), stays out of Stage 1
  with sharpened framing (squish-ccr, SPIRVCross). The "stays out"
  results are the highest-value find: SPIRVCross specifically would
  have caused a failed --with system_spirvcross build immediately if
  we'd taken the prior "trivial flip" annotation at face value.

* Thu May 07 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-33
- Docs sharpen: NvCloth status + Patch0009 PhysX4 timebomb annotation +
  assimp Stage 1 audit summary. No code/build changes; spec changes are
  comment-only (Patch0009 declaration block + this changelog entry).
- NvCloth confirmed standalone via three independent evidence types
  (2026-05-06 + 2026-05-07): Cheddarspice runtime test (chicken prefab
  with PhysX 4 removed + PhysX 5.6.1 active), Steve P [Amazon] code
  review ("no direct references to physx4 library in any of the nvcloth
  code"), and Cheddarspice structural fact ("NvCloth has its own
  standalone PxShared library and Foundation"). Option A (drop the Gem)
  is now well-supported, not tentative. PR #19726 (PhysX 4 retirement)
  is imminent.
- Patch0009 timebomb annotated in both the spec declaration block and
  the patch file header: when PR #19726 merges upstream, the PhysX4
  hunk fails to apply (PhysX4/ tree disappears). Fix is mechanical:
  drop the PhysX4 hunk; regenerate Patch0009 with only the PhysX5 hunk.
  Schedule for the same commit that pulls a fresh post-#19726 snapshot.
- assimp audit (2026-05-07): clean Stage 1 candidate, all 27 types +
  7 processing flags engine consumes are public C-API and 100% present
  in Fedora 6.0.4 headers. Engine include style matches Fedora layout
  exactly — no path-bridging needed. Fedora ships assimpConfig.cmake
  config-mode export — no Find shim needed either. Major version delta
  (5.4 → 6.0) is the only caveat; mitigation is pairing activation with
  a Tier 6 FBX-bake integration test. Documented in BUNDLED_LIBRARIES.md.

* Thu May 07 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-32
- Stage 1 9-pack: activate system_lua (no spec change — all wiring was
  already in place since the original deferral; this commit just flips
  the Makefile flag list and refreshes the lockstep docs).
- Patch0008 (commit d69bb9c, in the spec since 2605.0-30) drops AzCore
  ScriptContext.cpp's #include <Lua/lobject.h>. Audit identified the
  only symbol consumed (LUAI_MAXALIGN) is already public Lua API via
  luaconf.h's transitive include from lauxlib.h. Behavior-preserving.
- With Patch0008 applied unconditionally, Fedora's lua-devel (which
  ships only the public API: lua.h, lauxlib.h, lualib.h, luaconf.h)
  is now sufficient. The "DEFERRED" framing in BUNDLED_LIBRARIES.md
  is reframed accordingly; FEDORA_ROADMAP.md issue-#1 marked RESOLVED.
- Same patch submitted upstream as o3de/o3de PR #19733 (approved by
  nick-l-o3de 2026-05-07, awaiting merge); when that lands, our
  Patch0008 becomes redundant and can drop.
- Audit-pattern reliability tracker: Lua + poly2tri (8-pack, 2605.0-31)
  + system_lua activation (9-pack, this commit) — three same-day
  audit-track wins on 2026-05-07.

* Thu May 07 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-31
- Stage 1 system_poly2tri swap (Patch0009 + Findpoly2tri-system.cmake).
  poly2tri's bundle anchor lives in PhysX-Gem-internal PAL files
  (Gems/PhysX/Core/PhysX{4,5}/Source/Platform/Linux/PAL_linux.cmake),
  not in the standard cmake/3rdParty/Platform/Linux/BuiltInPackages…
  surface — Patch0009 ships separately from Patch0006 for that reason.
- Audit (issue #7, 2026-05-07): poly2tri consumers are exclusively in
  Gems/PhysX/ (Editor's PolygonPrismMeshUtils for polygon-prism shape
  colliders), zero references in core Code/. Engine uses public p2t::
  namespace API only — no internal-symbol coupling.
- Fedora's poly2tri-devel ships from Mason Green's BSD-3-Clause original
  (commit 26242d0a, May 2013); license-clean and independent of the
  bundled fork's attribution issue. Path-bridging in Findpoly2tri-system
  adds /usr/include/poly2tri to include-dir so engine's `<poly2tri.h>`
  consumer syntax resolves cleanly against Fedora's layout.
- Activates --with system_poly2tri (BR poly2tri-devel,
  Recommends poly2tri-devel, Requires poly2tri,
  -DLY_USE_SYSTEM_POLY2TRI=ON, %%prep cp). Per-chroot
  --rpmbuild-with system_poly2tri applied separately in COPR.
- Channel-marker OR-chain extended; --with system_poly2tri now
  triggers experimental channel labeling.
- Audit-track confirmation: same playbook that delivered the AzCore Lua
  PR (#19733) and the OpenEXR shim split now flips poly2tri from
  "off-limits restricted bundle" to "Stage 1 swap candidate" — a
  significantly better outcome than the original handling-options
  framing in FEDORA_ROADMAP.md suggested.

* Thu May 07 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-30
- Patch0008 (carry-patch, upstream-track candidate): drop AzCore's
  redundant `#include <Lua/lobject.h>` in ScriptContext.cpp. Audit
  finding 2026-05-07: the only symbol AzCore needs from that internal
  header is `LUAI_MAXALIGN`, which is part of Lua's public API
  (defined in luaconf.h, used in lauxlib.h's `luaL_Buffer`).
  Empirically verified against Fedora 44's lua-devel-5.4.8: the
  same `union L_Umaxalign { LUAI_MAXALIGN; };` line compiles cleanly
  with only public Lua headers. Carry-patch applies unconditionally
  (bundled-Lua builds also benefit). Activates `system_lua` on
  Fedora — Stage 1 scaffolding (bcond, FindLua-system.cmake,
  Source36, conditional BR/Recommends/Requires/cmake -D, %%prep cp)
  was already in place; only the engine-side patch was missing.
  Upstream PR drafted; submission to o3de/o3de gated on
  fully-baked signal per project_no_upstream_until_baked memory.
- Issue [#1](https://github.com/nickschuetz/o3de-rpm/issues/1)
  comment posted with full audit findings + the empirical compile
  test that backs the change.

* Wed May 06 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-29
- Stage 2a 7-pack: add system_openexr (extends the 6-pack with
  OpenEXR + Imath; first cross-stage step). The OpenEXR bundle
  (OpenEXR-3.1.3-rev4-linux on packages.o3de.org) declares both
  TARGETS OpenEXR and Imath in a single ly_associate_package line —
  the new FindOpenEXR-system.cmake shim mirrors that and creates
  both 3rdParty::OpenEXR (linking system libOpenEXR + libOpenEXRCore
  + libIex + libIlmThread) and 3rdParty::Imath (linking system
  libImath) as INTERFACE IMPORTED targets. Engine consumers
  (Gems/Atom/Asset/ImageProcessingAtom/Code/.../ExrLoader.cpp) use
  `#include <OpenEXR/Imf*.h>` verbatim, matching Fedora's openexr-devel
  layout exactly — no wrapper-header bridging needed.
- Per Nick_L (sig-build, 2026-05-05, issue #5), OpenEXR's version
  pin in the engine is not hard; Fedora's openexr-3.2.4 + imath-3.1.12
  are API-compatible with the bundle's 3.1.3 (3.1 → 3.2 is OpenEXR
  back-compat). Patch0006 extended with LY_USE_SYSTEM_OPENEXR gate
  (9 gates total now). Engine binaries auto-Require libOpenEXR-3_2.so.31
  + libImath-3_1.so.29 + ancillary OpenEXR-family libs.
- This is the OpenEXR + Imath sub-track of Stage 2 only. The
  OpenImageIO + OpenColorIO sub-track (also in Stage 2) stays blocked
  on Stage 3 (Python migration) per Nick_L's circular-dependency +
  Python C Module ABI explanation.

* Tue May 05 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-28
- Stage 1 6-pack: add system_lz4. Findlz4-system.cmake follows the
  mikkelsen pattern (direct find_path/find_library, no stock-cmake
  include — cmake doesn't ship a FindLZ4.cmake module so there's no
  side-effect target to avoid). Engine consumers (Gems/MultiplayerCompression,
  Code/Framework/AzFramework Archive, Code/Legacy/CrySystem) use
  `#include <lz4.h>` / `<lz4hc.h>` / `<lz4frame.h>` verbatim, matching
  Fedora's lz4-devel layout exactly — no wrapper-header bridging
  needed. Patch0006 extended with the LY_USE_SYSTEM_LZ4 gate hunk
  (8 gates total now). Engine binaries auto-Require liblz4.so.1.
  Per-chroot `--rpmbuild-with system_lz4` applied separately.

* Tue May 05 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-27
- system_tiff Stage 1 swap: Option A (narrow guard macro) confirmed
  structurally infeasible. Patch0008 attempt (commit cda6b7b, reverted
  by 9f2f099) gated CryCommon's int64/uint64 typedefs in BaseTypes.h
  behind O3DE_SYSTEM_LIBTIFF_COMPAT, with SKIP_UNITY_BUILD_INCLUSION
  on the two TIFF .cpp files. Local rpmbuild -bb --with system_tiff
  failed at compile time in Cry_ValidNumber.h (transitively included
  from EditorDefs.h via Cry_Math.h):
    error: use of undeclared identifier 'uint64'
        #define DoubleU64(x)   (*((uint64*) &(x)))
  Cry_ValidNumber.h's own DoubleU64/DoubleU64ExpMask/DoubleU64FracMask
  macros use `uint64` directly. The guard suppresses CryCommon's
  typedef but libtiff's <tiffio.h> hadn't yet been included when
  Cry_ValidNumber.h was parsed. Reordering tiffio.h ahead of the
  engine includes would compile (libtiff's typedefs become visible
  first), but introduces a `long` (LP64 libtiff) vs `long long`
  (CryCommon engine ABI) mismatch — CryGetTicks() and other engine
  symbols mangling differ -> unresolved-symbol link errors. Both
  paths fail; Option A is dead.
- Decision: switch to Option C — leave system_tiff parked
  indefinitely, ship the bundled libtiff-4.2.0.15-rev3 from
  packages.o3de.org, file a permanent Bundling Library Exception in
  the Fedora package review (Stage 5 of FEDORA_ROADMAP). The
  "narrow guard" approach is incompatible with CryCommon's internal
  int64/uint64 usage; the only clean alternative is Option B (engine-
  wide CryCommon C99 migration) which Nick previously ruled out as
  too invasive for the Fedora packaging track. Patch0007 stays in
  place (the deprecation-warning migration is required regardless of
  system_tiff). FindTIFF-system.cmake reverted to the pre-refactor
  form; bcond + Source declaration stay declared but defaulted off.
- Documentation: BUNDLED_LIBRARIES libtiff row updated to "Option C —
  Bundling Library Exception"; FEDORA_ROADMAP Stage 1 status keeps
  "5-pack" (libtiff exits the Stage 1 candidate list). Plan file
  squeezing-typeface-tiffany.md gets a closeout addendum.

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-26
- Editor dock icon: drop version from o3de2605-editor.desktop's
  StartupWMClass. Project Manager's launcher passes Qt -name
  "O3DE-2605" so PM's WM_CLASS matches o3de2605.desktop's
  StartupWMClass=O3DE-2605 cleanly (versioned dock icon for PM).
  But the Editor is launched by PM via direct exec — bypasses our
  launcher — so Editor's WM_CLASS comes from Qt's internal
  setApplicationName("O3DE Editor") = "Editor", "O3DE Editor"
  (no version). Verified live with xprop on a running Editor
  window:
    WM_CLASS(STRING) = "Editor", "O3DE Editor"
  Setting o3de2605-editor.desktop's StartupWMClass to versioned
  "O3DE-2605 Editor" doesn't match, so the WM falls back to a
  generic Qt icon in the dock when Editor launches. Drop the
  version: StartupWMClass="O3DE Editor". Two installed majors'
  Editors share the same dock icon (same engine, same class
  string upstream) but Project Manager retains its versioned
  identity which is the user-facing distinction.

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-25
- cmake demoted from Requires: to Recommends: (Mike Cromer feedback
  2026-05-04). The launcher uses cmake -P only for engine-path-id
  calculation (keys the per-user Python venv); the detection chain
  in sources/o3de-launcher.sh tries (1) cmake on PATH, (2) bundled
  cmake at <engineRoot>/cmake/runtime/bin/cmake (placeholder for
  future when we ship a bundled cmake), (3) graceful degrade with
  empty ENGINE_ID (engine still runs; per-engine venv functionality
  degrades silently). Default install still pulls cmake; minimal
  installs (`dnf install --setopt=install_weak_deps=False`) opt out.
  Saves ~30-100 MB on minimal-install scenarios (CI test containers,
  game distribution servers without development tooling).
- Launcher cmake-detection logic hardened: was hardcoded /usr/bin/cmake
  with a `|| true` swallow; now uses `command -v cmake` lookup with
  bundled-fallback path search and explicit empty-ENGINE_ID branch.

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-24
- Revert engine_name to upstream default "o3de" (was "o3de2605"). Surfaced
  2026-05-04 by Nick: PM rejected adding the WarehouseAssets gem to a
  project with:
    Project may not be compatible with this engine
    The following dependency requirements could not be satisfied:
    WarehouseAssets is incompatible because: o3de2605 26.05.0 does not
    match any version specifiers in the list of compatible engines:
    ['o3de-sdk>=2.3.0', 'o3de>=2.3.0']
  The gem's compatible_engines list hard-codes "o3de" / "o3de-sdk" as
  the engine identity. Our previous override of
  -DO3DE_INSTALL_ENGINE_NAME=%%{o3de_pkgname} (=o3de2605) made the
  installed engine.json's engine_name "o3de2605", which doesn't match
  any existing third-party gem's compat list — every gem fails the
  check. Trace through cmake/Version.cmake in upstream confirms the
  pristine default is engine_name="o3de" (read from the source's
  engine.json), and CPACK's .deb output ships unversioned engine_name.
  Match upstream by setting -DO3DE_INSTALL_ENGINE_NAME=o3de literally.
  Other versioned identities stay (RPM name o3de2605, install path
  /opt/O3DE/26.05.0, desktop files o3de2605.desktop, AppStream id
  org.o3de.O3DE2605, dock WM_CLASS O3DE-2605, SBOM o3de2605.cdx.json):
  these don't enter the gem-compat check, only engine.json's
  engine_name does.
- Trade-off accepted: the manifest's `engines_path` map keys by
  engine_name, so multiple installed o3deNNNN majors all collide on
  the "o3de" key. Only one is "registered" at a time; switching uses
  scripts/o3de.sh register --this-engine from the desired install
  root. This matches upstream's .deb multi-install UX exactly. Files
  for multiple majors still coexist on disk (paths versioned); only
  active registration is single-slot.

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-23
- Devel split: introduce %{name}-devel subpackage carrying the engine's
  static archives. Carves out two file sets from the main package:
    * %{o3de_install_prefix}/lib/Linux/profile/Default/*.a
      — 173 .a files, ~4 GB (test framework, builder targets, static
      engine internals)
    * %{o3de_install_prefix}/lib64/
      — 5 .a files (~2 MB) plus pkgconfig metadata for Recast/Detour
      from the RecastNavigation gem
  Fulfills the long-standing TODO(devel-split) block above %%package
  debug. Roughly halves on-disk size of %{name} for runtime-only
  users (CI test containers, game distribution servers, Lua/ScriptCanvas
  project authors). Native C++ gem developers writing static-link
  code against engine internals install both: `dnf install %{name}
  %{name}-devel`. The %{name}-devel package hard-Requires the same
  NVR of %{name} so they always upgrade in lockstep.
- Note that the project-build *-devel system packages (clang,
  mesa-libGL[U]-devel, libxcb-devel, etc., from commit aa767e0) and
  the conditional system_<X>-devel packages (mikkelsen-devel etc.,
  from commit 84c021b) stay as Recommends on the main %{name}
  package. Their consumer is user-project compilation against the
  engine's .so's — that path doesn't need %{name}-devel's static
  archives. Keeping these on main means `dnf install %{name}` (with
  default weak deps) gets the build experience working for the
  common case; %{name}-devel layers on the static-archive scenario.
- Update %%post user-facing message to mention %{name}-devel alongside
  the existing %{name}-debug pointer.

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-22
- Add Recommends: for project-build *-devel matching active system_<X>
  swaps. Mike Cromer (sig-build chair) follow-up 2026-05-04: when
  system_mikkelsen is active, the engine's cmake exports point at the
  system mikkelsen path — so user projects need mikkelsen-devel to
  compile against the engine, NOT the bundled 3p mikkelsen. The package
  currently Requires `mikkelsen` (runtime) only; build users hit
  "find_package(mikkelsen) — Could NOT find mikkelsen" without
  mikkelsen-devel. Same logic applies to the other 4 Stage 1 swaps
  (expat, freetype, libpng, zlib — zlib-devel was already in the
  unconditional list from Mike's first finding) plus the deferred
  tiff/lua swaps when those activate.
- Conditional Recommends keyed off the matching `--with system_<X>`
  bcond so the spec stays internally consistent: when an SRPM is
  built with a swap activated, the produced RPM Recommends both the
  runtime package (already there, hard Require) and the *-devel
  package (now Recommends, soft).

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-21
- Add Recommends: block for project-build *-devel deps. Surfaced by
  Mike Cromer (O3DE sig-build chair) on a clean Fedora 44 install:
  `dnf install o3de2605` succeeded and Project Manager launched, but
  compiling a user project from source needed clang +
  mesa-libGL[U]-devel + libxcb-devel + libxkbcommon[-x11]-devel +
  fontconfig-devel + libunwind-devel + libzstd-devel + libcurl-devel +
  pcre2-devel + openssl-devel + zlib-devel + vim-common (for xxd).
  Recommends rather than Requires so runtime-only users
  (`dnf install --setopt=install_weak_deps=False`) can opt out;
  default install pulls them in so the build experience just works.
  These deps move to a future o3de2605-devel subpackage when the
  devel-split lands; this block is the bridge until then.
- File the cmake-bundled-fallback as a launcher FIXME (Mike noted
  cmake is now part of get_python.sh's bundled toolchain, so we
  could drop the runtime Requires once the launcher learns to fall
  back to the bundled cmake at <engineRoot>/cmake/runtime/bin/cmake).

* Mon May 04 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-20
- Stage 1 5-pack reactivated and validated. After refactoring all four
  ZLIB-class Find<X>-system.cmake shims to the mikkelsen pattern in
  separate commits (92bde6e / cba5059 / 6b14ffa / 0ca58e8), the
  combined 5-pack of system_X swaps (mikkelsen + expat + freetype +
  png + zlib) builds cleanly via `make rpm-experimental` (47 min
  combined; each individual shim previously validated in 47-52 min
  isolated builds). Auto-Requires confirms all five system .so's
  show up in the engine's link-time deps: libmikktspace.so.0,
  libexpat.so.1, libfreetype.so.6, libpng16.so.16, libz.so.1.
  Restores SRPM_EXPERIMENTAL_FLAGS to the full 5-pack and updates the
  comment block. The o3de-experimental chroot config (rpmbuild-with
  flags on F44 + rawhide) is also synced to the 5-pack via
  copr-cli edit-chroot. system_tiff (CryCommon int64 conflict) and
  system_lua (AzCore lobject.h carry-patch) remain parked separately.

* Sun May 03 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-19
- Fix doubled-quote in installed engine.json's display_version field.
  The two cmake vars feed DIFFERENT upstream consumers and have
  ASYMMETRIC quoting requirements:
  * O3DE_INSTALL_DISPLAY_VERSION_STRING → cmake/install/engine.json.in
    has `"display_version": "@var@",` (template supplies JSON quotes)
    → value must be UNQUOTED. Previously '"...":'  produced
    `""26.05.0-experimental.246b46f""` — invalid JSON, surfaced by
    Tier 2's display_version test on the o3de2605 install (test
    correctly reported the malformed field as "still '00.00'"
    because the field's actual value parsed as an empty string).
  * O3DE_INSTALL_BUILD_VERSION → both
    cmake/install/engine.json.in (`"build": @var@,` — no template
    quotes; the field expects either a number or a quoted string
    raw) AND Code/Editor/CMakeLists.txt's
    `O3DE_BUILD_VERSION=${O3DE_INSTALL_BUILD_VERSION}` COMPILE_DEFINITION
    (preprocessor needs a string literal, not bare tokens). Both
    require the value to include quotes. Surfaced by build take 5
    failing in CryEdit.cpp at compile time with
    "use of undeclared identifier 'experimental'" because the
    unquoted preprocessor expansion `2605.0-experimental.246b46f`
    parsed as bare tokens.
  Net change: drop quotes from the DISPLAY_VERSION_STRING line only,
  keep them on BUILD_VERSION. engine.json now has a properly-quoted
  display_version JSON string AND the build field stays as our
  channel-marker quoted string (pre-existing behavior — upstream
  expects a number here but the channel-marker convention has been
  using a quoted string since the channel-marker work landed; that
  schema mismatch is a separate FIXME for a future engine.json
  schema review).

* Sun May 03 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-18
- Stage 1 baseline reduced to mikkelsen-only. Build 10421133 (5-pack:
  expat, freetype, libpng, mikkelsen, zlib — system_tiff already parked)
  failed at cmake configure-time:
    UNKNOWN_LIBRARY Library ZLIB::ZLIB specified
      MAP_IMPORTED_CONFIG_DEBUG = DEBUG; but did not have any of
      IMPORTED_LOCATION_xxxx set
  Root cause: each of the four `Find<X>-system.cmake` shims for
  expat/freetype/libpng/zlib delegates library/header lookup to
  cmake's stock `FindZLIB.cmake`/`FindPNG.cmake`/etc. via include().
  That stock include creates a side-effect target (e.g. ZLIB::ZLIB)
  with MAP_IMPORTED_CONFIG_* set but no per-config IMPORTED_LOCATION,
  which O3DE's runtime walker iterates and dies on. Mikkelsen alone
  works because Findmikkelsen-system.cmake does its lookup directly
  via find_path/find_library — no stock-module include, no
  side-effect target. Parking the four ZLIB-class swaps; future Stage
  1 PR will refactor each shim to the mikkelsen pattern. Bcond +
  Source declarations stay in place for future activation. Patch0006's
  gating in BuiltInPackages_linux_x86_64.cmake is already correct
  for all of them.

* Sun May 03 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-17
- Park system_tiff Stage 1 swap. Build 10420962 (Patch0007 v2 in place)
  surfaced a deeper conflict: libtiff's <tiff.h> defines int64/uint64
  as int64_t/uint64_t (long on LP64); CryCommon/BaseTypes.h defines
  them as slonglong/ulonglong (long long). Same size, distinct C++
  types → typedef redefinition error in any TU including both. Fix
  needs CryCommon migration to C99 typedefs — foundational header,
  out of scope for the current rename validation. Drop --with
  system_tiff from SRPM_EXPERIMENTAL_FLAGS and from the experimental
  chroot's --rpmbuild-with config. Patch0007 stays in place; it's
  required for any modern-libtiff build (bundled or system) regardless
  of whether the system_tiff bcond is activated.

* Sun May 03 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-16
- Patch0007 (broader scope): also patches Code/Editor/Util/ImageTIF.cpp
  in addition to TIFFLoader.cpp. Build 10420621 surfaced the second
  consumer at compile-step ~2.5h (uint8/uint16/uint32 in Editor's
  legacy TIF path). Finished the libtiff legacy-typedef migration
  across both <tiffio.h>-using files; the third upstream tiffio.h
  consumer (FrameCaptureSystemComponent.cpp) was already on C99 types.
  Patch file renamed sources/0007-tiffloader-c99-typedefs.patch →
  0007-libtiff-c99-typedefs.patch.

* Sun May 03 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-15
- Patch0007: migrate TIFFLoader.cpp's nine remaining legacy libtiff
  `uint32` typedefs to standard C99 `uint32_t`. libtiff 4.5+ marks the
  legacy typedef __attribute__((deprecated)); combined with O3DE's
  -Werror, every stale use is a hard build failure. Adjacent code in
  the same file already uses uint32_t (partial migration upstream) —
  this finishes it. Required for any build against modern libtiff,
  unlocks the `--with system_tiff` Stage 1 swap (and benefits bundled-
  libtiff builds too as the bundle ages).

* Sun May 03 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-14
- Rename package o3de → o3de2605 (postgresql-style major-keyed naming).
  Multiple O3DE majors can now coexist on one system: o3de2605 (26.05
  line) at /opt/O3DE/26.05.0/, future o3de2610 at /opt/O3DE/26.10.0/,
  etc. Different majors are different engine lines, intentionally NOT
  cross-major auto-upgradable. Path layout matches upstream's .deb and
  Windows .msi install layout — cross-platform consistency. Subpackages
  follow the same versioning automatically: o3de2605-debug today,
  o3de2605-devel when the queued split lands. Single Provides: o3de
  for any external Requires: o3de that needs to resolve. New macros:
  o3de_major_tag, o3de_pkgname, o3de_install_prefix.
- Per-version desktop entries: o3de2605.desktop with Name="O3DE 26.05.0",
  Icon=o3de2605, StartupWMClass=O3DE-2605. Two installed majors appear
  as separate menu entries with distinct dock identities.
- AppStream component IDs versioned: org.o3de.O3DE2605, org.o3de.O3DE2610.
  GNOME Software / KDE Discover treat each version as its own installable
  app.

* Fri May 01 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-13
- Defensive: also BR python3-pip and python3-wheel. Newer setuptools
  versions sometimes invoke pip + wheel through the PEP 517 build
  path even for plain `setup.py sdist`, and COPR mock chroots only
  install explicit BuildRequires. Cheap insurance against another
  4-hour-build-then-fail iteration.
- Bump per-build COPR timeout to 25200 s (7 hr) via `make copr-*`.
  F44 chroot took 4 hr in 10414894 (2173/2173 compile steps);
  rawhide would risk hitting the default 5 hr timeout.

* Fri May 01 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-12
- Add `BuildRequires: python3-setuptools`. The %%build sdist-builder
  step (introduced for Patch0004) runs `python3 setup.py sdist` for
  three engine-side Python packages, which requires setuptools at
  build time. Local Fedora workstations pull it in transitively; COPR
  mock chroots are minimal and don't, so build 10414933 failed in the
  sdist step after a successful 4-hour compile of all 2173 profile
  binaries.

* Fri May 01 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-11
- Force the build to use clang. Local builds happened to pick clang 22
  via cmake auto-detection because that's the default cc on the dev
  workstation, but Fedora 44's mock chroots (and COPR) default to GCC
  16, where the engine's FetchContent-pulled libogg fails CheckSizes
  with "No 16 bit type found on this platform!" — a try_compile()
  test that succeeds under clang and fails under GCC's stricter
  hardening defaults. Pass -DCMAKE_C_COMPILER=clang and -DCMAKE_CXX_
  COMPILER=clang++ to cmake, and add `BuildRequires: clang`. Patch0001
  is already clang-targeted, so this just makes the implicit dependency
  explicit. gcc-c++ stays in BR for host-build tooling that still
  assumes it.

* Fri May 01 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-10
- Add /opt/o3de/lib/Linux/debug to the o3de-debug subpackage. Upstream's
  Install_common.cmake routes ARCHIVE (.a), LIBRARY (.so), and RUNTIME
  files for each configuration into a single DEFAULT_<CONF> component,
  so DEFAULT_DEBUG installs land in both bin/Linux/debug/ AND
  lib/Linux/debug/. The previous %%files split only excluded bin/, so
  debug-config archives + shared libs were leaking into the main o3de
  package. Move them to o3de-debug where they belong.

* Fri May 01 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-9
- Pass O3DE_INSTALL_BUILD_VERSION="<stable_tag>" to cmake so the Editor's
  splash, About dialog, and main-window title render "Version 2605.0"
  instead of the hardcoded "Development Build" placeholder. Matches the
  format on the Windows O3DE-SDK distribution, which displays the
  compact stable-tag string in the Editor while the Project Manager
  title bar continues to use the dotted display_version (26.05.0).
  Engine.json's "build" field consequently emits as a JSON string
  ("build": "2605.0") rather than the upstream-default integer 0.
- Add Patch0005 so Project Manager's titlebar shows the engine version
  on Linux. AzQtComponents::WindowDecorationWrapper::setGuest() in
  OptionDisabled mode (Linux/Mac, WM-drawn titlebar) connects the
  guest's windowTitleChanged signal but doesn't copy the guest's
  *current* title. ProjectManagerWindow sets its title in its
  constructor — before Application.cpp's setGuest() call — so the
  initial title was being lost and the WM ended up displaying the
  QApplication name "O3DE" alone. The patch adds the same one-line
  copy that the non-disabled (Windows custom-titlebar) branch already
  performs.

* Thu Apr 30 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-8
- Split debug-config binaries into a separate `o3de-debug` subpackage,
  produced opt-in via `rpmbuild --with debug`. The default build now
  ships only the profile-config binaries (the practical config for
  end-user game development), roughly halving build time and the
  installed footprint for the common case. Drop the obsolete
  `--with debug_only` toggle; the subpackage model replaces it.

* Thu Apr 30 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-7
- Pass --engine-path=$ENGINE_PATH to the engine binary from the launcher.
  Without it the engine's C++ scan-up resolved engine root to a path
  that hashed to a different SHA1 first-32-bits than what get_python.sh
  computes (which hashes /opt/o3de/), so Project Manager looked for the
  per-user venv at the wrong ~/.o3de/Python/venv/<id>/ and raised
  "Failed to start Python" on every launch. With --engine-path passed,
  both sides agree on the engine ID and the engine's own RunGetPythonScript
  fallback also runs the right /opt/o3de/python/get_python.sh on first
  launch.

* Thu Apr 30 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-6
- Re-enable cmake's Unity build. The clang 22.1.2 codegen bug (Greedy
  Register Allocator SIGSEGV on heavily-templated AZStd containers at
  -O2) is fixed in clang 22.1.4 (Fedora 44 update on 2026-04-30).
  Verified via stress-test compile of representative templates.

* Thu Apr 30 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-5
- Set O3DE_INSTALL_DISPLAY_VERSION_STRING=26.05.0 (was 00.00 placeholder
  inherited from upstream's engine.json), so the editor splash and
  window title show 26.05.0 instead of "Development Build". The string
  is compiled into the binary at build time, so this only takes effect
  in a fresh build.
- Add second .desktop entry (o3de-editor.desktop, NoDisplay=true,
  StartupWMClass=O3DE Editor) so GNOME/KDE associate the Editor's
  running window to our installed o3de icon. The Editor is launched
  from inside Project Manager, not the menu, so NoDisplay=true keeps
  it from cluttering the app menu while still being indexed for
  window-class matching.

* Thu Apr 30 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-4
- Fix user-project cmake configure failures against installed engine:
  - Pass 3-component version (26.05.0) via new %%{engine_cmake_version}
    macro derived from %%{stable_tag}; previously baked stable_tag's
    YYMM.PATCH (2 components) into engine.json which broke
    cmake/Version.cmake's MAJOR.MINOR.PATCH parser.
  - Add Patch0004 to gate ly_pip_install_local_package_editable on
    INSTALLED_ENGINE — drops the -e flag so pip doesn't try to write
    .egg-info into read-only /opt/o3de/Tools/.
- Add StartupWMClass=O3DE to the desktop entry and pass -name O3DE from
  the launcher so the dock icon links to the installed hicolor icon
  instead of the engine's internal Qt fallback.

* Thu Apr 30 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-3
- Restore %%__requires_exclude for libclang-12 / libtinfo.so.6 — required
  by O3DE's bundled DirectXShaderCompiler (RPATH-resolved internally).
  Without it, dnf install fails with "nothing provides libclang-12.so.1".

* Wed Apr 29 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-2
- Ship app icons in six hicolor sizes (16, 32, 48, 64, 128, 256), extracted
  from upstream's product_icon.ico master and downsampled with imagemagick
- Add AppStream metainfo (org.o3de.O3DE) for GNOME Software / KDE Discover
  with %%check appstream-util validation
- Drop dead %%__requires_exclude — auto-Requires no longer matches it on
  the cleaned build (libclang-*/libtinfo.so.6 don't appear)
- Parameterize the bundled-Python series as %%global o3de_bundled_python
  (3.10 today) used by the launcher; eases the eventual 3.13 system-Python
  migration in the Fedora roadmap
- Replace the launcher's sed-based engine_path migration with an inline
  python3 JSON edit — resilient to whitespace / sibling keys / trailing
  commas in user/project.json
- Document why %%debug_package %%nil is set, with a roadmap pointer to the
  proper -debuginfo subpackage work
- Add gtk-update-icon-cache calls in %%post / %%postun for the new icon set

* Wed Apr 29 2026 Nick Schuetz <nschuetz@redhat.com> - 2605.0-1
- Validated end-to-end on stabilization/26050 (commit 246b46f)
- Drop obsolete gem-reorg machinery (Source12 + %%install loop + TSV file);
  gems now install hierarchically under /opt/o3de/Gems/ directly
- Drop confirmed-cruft BuildRequires now that auto-Requires has been
  validated against the built binaries: pkgconfig(Qt5*), qt5-qttools-devel,
  qt5-qtx11extras-devel, pkgconfig(zlib), pkgconfig(openssl),
  pkgconfig(libcurl), pkgconfig(freetype2), pkgconfig(libpcre2-8),
  spirv-tools-devel, git-lfs, python3-pip, python3-rpm-macros
- Replace hand-curated Requires with the minimal set rpm auto-Requires
  cannot derive: mesa-libGL, cmake (for the launcher's engine-id calc),
  python3 (no version floor)
- Drop the cmake>=3.24 floor (F44 ships 4.x) and python3>=3.10 floor
- Launcher: add idempotent first-run migration that rewrites
  <project>/user/project.json engine_path overrides from /usr/o3de or
  legacy /opt/o3de paths to the active install prefix; gated by a
  per-prefix marker file under ~/.o3de/

* Wed Apr 29 2026 Nick Schuetz <nschuetz@redhat.com> - 2510.2-1
- Major spec refactor for Fedora 44 / rpm 4.20+:
- Add %%bcond_with snapshot for development-branch builds (sources/make-snapshot-tarball.sh)
- Extract embedded heredocs to Source files (launcher, desktop entry, gem reorg manifest)
- Replace inline sed transforms with proper Patch files (clang21, manifest.py, get_python.sh)
- Move install prefix from non-FHS /usr/o3de to /opt/o3de
- Drop world-writable chmod on /opt; rely on per-user venv non-editable install
- Add SHA256 source verification in %%prep
- Add ExclusiveArch x86_64/aarch64
- Add %%check with desktop-file-validate
- Add %%bcond_with thirdparty_* hooks for opt-in 3rdParty package bundling
- Ship CycloneDX SBOM under %%{_datadir}/o3de/sbom/

* Tue Jan 27 2026 Nick Schuetz <nschuetz@redhat.com> - 2510.2-0
- New point release build for 25.10.2

* Wed Dec 10 2025 Nick Schuetz <nschuetz@redhat.com> - 2510.1-1
- New point release build for 25.10.1

* Sat Nov 22 2025 Nick Schuetz <nschuetz@redhat.com> - 2510.0-1
- Rewritten RPM package for O3DE v25.10.0

* Thu Aug 24 2023 Roddie Kieley <roddie@kieley.ca> - 2305.1-1
- Updated for v23.05.1 release

* Fri Aug 04 2023 Nicholas Frizzell <nfrizzel@redhat.com> - 2305.0-6
- Misc. cleanup and documentation
