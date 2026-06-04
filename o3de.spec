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
# (uploaded to o3de-development, weekly cadence via the
# snapshot-development workflow, or ad-hoc via `make copr-development`):
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
# without --with stabilization, and ship to o3de-development).
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
%bcond_with system_cityhash
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
%bcond_with system_rapidjson
%bcond_with system_rapidxml
%bcond_with system_spirvcross
%bcond_with system_sqlite
%bcond_with system_tiff
%bcond_with system_vulkan_validation_layers
%bcond_with system_xxhash
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

# Qt6 forward-test gate. The o3de/o3de:qt6 branch swaps the custom Qt 5.15
# bundle for vanilla Qt6 + PySide6, and its 3rdParty brings build deps and
# binary quirks the Qt5 bundle does not. This bcond fences those off so the
# Qt5 channels (stable / testing / development) are untouched: it pulls the
# bundled-Qt6 link dep (dbus-devel) and runs an %%install rpath cleanup on the
# PySide6 binaries. Set ONLY on the o3de-development-qt6 forward-test chroots
# (--rpmbuild-with qt6). 26.10-track; qt6 is NOT backported to 26.05.
# See project_o3de_bundles_custom_qt.md.
%bcond_with qt6

# Prototype gate for the central system-swap download hook (Patch0014).
# When set, Patch0014 wraps ly_download_associated_package() in a
# per-package LY_USE_SYSTEM_<NAME> opt-out, and Patch0006 (the per-line
# BuiltInPackages gating it replaces) is skipped. Patch0009 and
# Patch0013 are deliberately KEPT: 0009 is a gem-local gate that
# coexists, and 0013 carries non-download hunks (VULKAN_VALIDATION_LAYER
# unset + VK_LAYER_PATH SetEnv) the hook does not cover. Default OFF so
# every shipping channel is unchanged; exercised on the o3de-experimental
# chroots as the validation build for the upstream hook proposal
# discussed with nick-l-o3de 2026-06-03. See the Patch0014 header and
# project_system_swap_shim_two_mechanisms.md.
%bcond_with swap_hook

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
%if %{with qt6}
# qt6 builds additionally ship Qt's lupdate (LinguistTools), which links
# libQt6Qml.so.6 (it parses QML for translatable strings), but the qt 3p
# package's deploy list ships no Qml libraries. The dangling auto-Require
# (incl. the Qt_6_PRIVATE_API versioned symbol) makes the RPM
# dnf-uninstallable. lupdate is the only payload binary linking Qml
# (verified by a full payload NEEDED scan, 2026-06-04) and the PySide6
# QtQml module is not shipped, so nothing can dlopen it either. Drop the
# Require until upstream either deploys libQt6Qml or drops lupdate from
# the installed image.
%global __requires_exclude ^libclang-12\\.so.*|^libtinfo\\.so\\.6.*|^libQt6Qml\\.so\\.6.*
%else
%global __requires_exclude ^libclang-12\\.so.*|^libtinfo\\.so\\.6.*
%endif

Name:           %{o3de_pkgname}
%if %{with snapshot}
# Tilde (~) is the RPM pre-release delimiter, so the snapshot version
# compares LESS than the bare release tag. This is the correct semantic:
# a snapshot built from stabilization/26050 ahead of 2605.0 ships as
# 2605.0~<date>git<sha> which auto-upgrades to 2605.0-1 once the stable
# release lands. Previously this used `^` (the post-release delimiter)
# which inverted the comparison and blocked snapshot-to-stable upgrades.
# Caught 2026-05-28 when dnf refused to upgrade from 2605.0^...8e75050
# to 2605.0-1. See FOLLOW_UPS.md ("Packaging correctness") for context.
Version:        %{stable_tag}~%{snapshot_date}git%{shortcommit}
%else
Version:        %{stable_tag}
%endif
Release:        100%{?dist}
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
# Standalone Editor entry. Currently NoDisplay=true (commit e112bf6,
# 2026-05-26, "desktop: hide Editor/ME/MC entries"): cold-launching
# Editor outside a project context turned out to have known issues
# vs the Windows installer's all-visible layout. The desktop file
# still ships so WM_CLASS / dock-icon attachment works when Editor
# is launched from inside Project Manager (Edit Project button).
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

# Changelog body lives in a separate source file (see end of spec for
# %include). Keeps the spec body lean while preserving full changelog
# history in the SRPM. Common Fedora pattern for active downstream
# packaging where Release: bumps are frequent.
Source99:       o3de.changelog

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
# o3de-development COPR project intentionally has no `system_*` swaps active
# (see make-snapshot-tarball.sh + edit-chroot config) so the gate-flags
# aren't needed there anyway.
%if %{without development_snapshot} && %{without swap_hook}
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

# Lua 5.5 compat patches (0010 + 0011). Gated on system_lua because Lua
# 5.5 is only ever reached via the system swap (the bundled package is
# Lua-5.4.4-rev1, and F44's system Lua is 5.4.8 -- only rawhide's system
# Lua is 5.5). All-bundled builds (development, qt6, stable-without-swap)
# build against 5.4.4 where the 2-arg lua_newstate / LUA_NUMTAGS exist
# natively, so these shims are inert there AND need not apply -- which
# also stops them breaking %%prep when an all-bundled branch (e.g. qt6)
# reworks one of the patched files. See project_lua_5_5_newstate_break.md.
%if %{with system_lua}

# Lua 5.5 added a required third parameter to `lua_newstate` (a hash-seed
# randomization parameter). Engine's ScriptContext.cpp:4359 still calls
# the 5.4 two-arg form, which fails compilation on any distro shipping
# Lua 5.5+. Patch wraps the call in a `#if LUA_VERSION_NUM >= 505` guard
# that passes seed=0 on Lua 5.5+ and falls through to the original
# two-arg form on Lua 5.4. Behavior-preserving
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
%endif

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
%if %{without development_snapshot} && %{without swap_hook}
Patch0013:      0013-vulkan-validationlayers-gate-on-system.patch
%endif

# Patch0015 -- swap_hook variant of Patch0013: the two runtime hunks
# (PAL_linux.cmake dependency removal + Instance.cpp VK_LAYER_PATH
# SetEnv flip) WITHOUT the BuiltInPackages associate-gate hunk. That
# hunk's context assumed Patch0006 had already rewritten the file, and
# under the lazy model it is unnecessary anyway: ly_associate_package
# only registers, and with the reference removed the resolver never
# fires for it. See the patch header.
%if %{without development_snapshot} && %{with swap_hook}
Patch0015:      0015-vulkan-validationlayers-system-runtime-hunks.patch
%endif

# Patch0014 -- the central system-swap download hook (prototype). One
# guard inside ly_download_associated_package() replaces Patch0006's
# per-line gating; the trailing find_package at every call site then
# resolves our Find<X>.cmake shims. See the patch header for the call
# site sweep and the Imath multi-target note. Applied only with the
# swap_hook bcond (o3de-experimental validation builds).
%if %{with swap_hook}
Patch0014:      0014-3rdpartypackages-system-swap-download-hook.patch
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
Source46:       FindRapidXML-system.cmake
Source47:       FindRapidJSON-system.cmake
Source48:       Findxxhash-system.cmake
Source49:       Findcityhash-system.cmake

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

# D-Bus: the bundled Qt6's libQt6DBus.so.6 carries versioned references to
# libdbus-1 (@LIBDBUS_1_3) and must resolve them at link time. Fedora's
# minimal mock buildroot does not pull libdbus in by default, so the link
# fails ("undefined reference to dbus_*"); o3de's own Ubuntu CI passes only
# because its base image already has libdbus present. Gated on the qt6
# bcond so the Qt5 channels do not pull it. patchelf is used by the qt6
# %%install rpath cleanup below. Caught on the first qt6 test builds
# (o3de-development-qt6 builds 10541804 + 10549660, 2026-06-02).
%if %{with qt6}
BuildRequires:  dbus-devel
BuildRequires:  patchelf
%endif

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
%if %{with system_rapidjson}
BuildRequires:  rapidjson-devel
%endif
%if %{with system_rapidxml}
BuildRequires:  rapidxml-devel
%endif
%if %{with system_xxhash}
BuildRequires:  xxhash-devel
%endif
%if %{with system_cityhash}
# Stage 1 swap: replace the bundled cityhash-1.1-multiplatform fetch with
# our license-clean COPR rebuild o3de2605-cityhash-devel from
# hellaenergy/o3de-dependencies. cityhash is not in Fedora; the rebuild
# tracks upstream google/cityhash at commit f5dc541 (2022-07-19).
BuildRequires:  o3de2605-cityhash-devel
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

# Project Manager build + tooling the editor shells out to:
#   - ninja-build: the PM 'Build' action (ProjectManager's
#     FindSupportedNinja) and `cmake --build` use the Ninja generator.
#     It was a BuildRequires for the engine build but was missing from
#     the runtime project-build deps, so 'Build' fails on a clean
#     install. Upstream's .deb declares ninja-build for the same reason.
#   - cmake-gui: the PM 'Open CMake GUI' action execs the system
#     cmake-gui binary. On Fedora that is a SEPARATE package from cmake
#     (cmake-gui), so a clean install that has cmake still fails 'Open
#     CMake GUI' with "Failed to start CMake GUI". Community-verified
#     2026-05-29. Upstream's .deb/Snap declare neither cmake-gui nor a
#     Tk runtime, so these tools are broken on a clean Debian/Ubuntu
#     install too (see the upstream-drafts/ note).
#   - xdg-utils: the PM 'Open Project folder' action and the
#     "open build log" / "open export output" links use Qt's
#     QDesktopServices::openUrl, which on Linux shells out to xdg-open
#     (from xdg-utils). Without it those actions silently no-op on a
#     minimal install (no error dialog, just a qDebug). Lower severity
#     than the others but the same missing-tool class.
Recommends:     ninja-build
Recommends:     cmake-gui
Recommends:     xdg-utils

# The -devel subpackage ships the static archives (*.a) every project
# build links: libAzGameFramework.a, libAzCore (Object/Static variants),
# libAtomCore.a, libAssetBuilderSDK.a, and the rest of the AzFramework /
# AzNetworking / AssetProcessor.Static surfaces. Any project that runs
# `cmake --build .../GameLauncher` will fail at the ninja link step
# without -devel installed (caught 2026-05-28 by a community report).
# We Recommend rather than Require so the (rare) headless-runtime-only
# use case can still opt out via `--setopt=install_weak_deps=False`.
Recommends:     %{name}-devel = %{version}-%{release}

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
%if %{with system_cityhash}
Requires:       o3de2605-cityhash
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
#   - xcb-util-*-devel: the XCB util suite Qt's xcb platform plugin
#     pulls in at compile time. We already BuildRequire all five for
#     the engine build; a consumer project that links the same Qt needs
#     the same headers. xcb-util-keysyms-devel was the field-confirmed
#     miss (2026-05-29 alex7900 report: project build failed in a clean
#     Fedora Toolbox until it was installed by hand); the other four are
#     listed alongside it to match the BuildRequires set so the next
#     header isn't a second surprise.
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
Recommends:     xcb-util-devel
Recommends:     xcb-util-image-devel
Recommends:     xcb-util-keysyms-devel
Recommends:     xcb-util-renderutil-devel
Recommends:     xcb-util-wm-devel
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

# Two of the Project Manager's helper dialogs (Open Export Settings,
# Open Android Project Generator) drive the editor's bundled Python via
# tkinter. (Open CMake GUI is NOT one of them; it execs the system
# cmake-gui binary -- see the cmake-gui Recommends above.)
# That bundled Python's _tkinter is built against Tk 8.6 and is
# DT_NEEDED-linked to libtk8.6.so + libtcl8.6.so. Fedora 44 moved the
# default tk/tcl to 9.x and split the 8.6 runtime into the tk8 / tcl8
# packages, so a clean install no longer has libtk8.6.so and these tools
# fail with "ImportError: libtk8.6.so: cannot open shared object file".
# The bundled Python is fetched per-user by get_python.sh after install,
# so rpm's auto-Requires never scans its _tkinter.so and can't detect
# these; list them explicitly.
#
# Export Settings additionally uses tkinter.tix, which needs the system
# Tix package (tix). tix alone isn't enough: Fedora installs Tix to
# /usr/lib64/tcl/ which the bundled Tcl's auto_path doesn't cover, so the
# launcher also adds that dir to TCLLIBPATH (sources/o3de-launcher.sh).
# Community report 2026-05-29 (adwglds, F44): libtk8.6.so ImportError on
# Android Project Generator; Export Settings stuck on the missing Tix
# package even after installing tix by hand. Both reproduced + verified
# fixed locally against the bundled python 3.10.
Recommends:     tk8
Recommends:     tcl8
Recommends:     tix

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
%if %{with system_rapidjson}
Recommends:     rapidjson-devel
%endif
%if %{with system_rapidxml}
Recommends:     rapidxml-devel
%endif
%if %{with system_xxhash}
Recommends:     xxhash-devel
%endif
%if %{with system_cityhash}
Recommends:     o3de2605-cityhash-devel
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
%if %{with system_rapidjson}
cp %{SOURCE47} cmake/3rdParty/FindRapidJSON.cmake
%endif
%if %{with system_rapidxml}
cp %{SOURCE46} cmake/3rdParty/FindRapidXML.cmake
%endif
%if %{with system_xxhash}
cp %{SOURCE48} cmake/3rdParty/Findxxhash.cmake
%endif
%if %{with system_cityhash}
cp %{SOURCE49} cmake/3rdParty/Findcityhash.cmake
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
    %{?with_system_cityhash:-DLY_USE_SYSTEM_CITYHASH=ON} \
    %{?with_system_expat:-DLY_USE_SYSTEM_EXPAT=ON} \
    %{?with_system_freetype:-DLY_USE_SYSTEM_FREETYPE=ON} \
    %{?with_system_googlebenchmark:-DLY_USE_SYSTEM_GOOGLEBENCHMARK=ON} \
    %{?with_system_libsamplerate:-DLY_USE_SYSTEM_LIBSAMPLERATE=ON} \
    %{?with_system_lua:-DLY_USE_SYSTEM_LUA=ON} \
    %{?with_system_lz4:-DLY_USE_SYSTEM_LZ4=ON} \
    %{?with_system_mcpp:-DLY_USE_SYSTEM_MCPP=ON} \
    %{?with_system_mikkelsen:-DLY_USE_SYSTEM_MIKKELSEN=ON} \
    %{?with_system_openexr:-DLY_USE_SYSTEM_OPENEXR=ON -DLY_USE_SYSTEM_IMATH=ON} \
    %{?with_system_png:-DLY_USE_SYSTEM_PNG=ON} \
    %{?with_system_poly2tri:-DLY_USE_SYSTEM_POLY2TRI=ON} \
    %{?with_system_rapidjson:-DLY_USE_SYSTEM_RAPIDJSON=ON} \
    %{?with_system_rapidxml:-DLY_USE_SYSTEM_RAPIDXML=ON} \
    %{?with_system_sqlite:-DLY_USE_SYSTEM_SQLITE=ON} \
    %{?with_system_tiff:-DLY_USE_SYSTEM_TIFF=ON} \
    %{?with_system_vulkan_validation_layers:-DLY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS=ON} \
    %{?with_system_xxhash:-DLY_USE_SYSTEM_XXHASH=ON} \
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

%if %{with qt6}
# Qt6 PySide6 rpath cleanup. The bundled pyside6 3rdParty package ships
# shiboken6 + the libpyside6 / *.abi3.so binaries with their build-machine
# RUNPATH baked in (an absolute /home/runner/... o3de CI path) and $ORIGIN
# at the wrong position. Fedora's check-rpaths QA (ERROR 0002 invalid
# runpath + ERROR 0008 $ORIGIN position) rejects them in %%install. The
# absolute CI path is dead on any real machine anyway, so strip every
# non-$ORIGIN entry and keep only the $ORIGIN-relative ones (which also
# puts $ORIGIN first, clearing 0008). Self-limited to files that actually
# carry the CI path, so clean engine binaries are untouched. Upstream fix
# belongs in o3de/3p-package-source's pyside6 recipe.
find %{buildroot}%{o3de_install_prefix} -type f \
        \( -name 'shiboken6' -o -name '*.abi3.so*' -o -name 'libpyside6*' -o -name 'libshiboken6*' \) \
        | while read -r f; do
    rp=$(patchelf --print-rpath "$f" 2>/dev/null) || continue
    case "$rp" in
        *home/runner/*)
            clean=$(printf '%s' "$rp" | tr ':' '\n' | grep -E '^\$ORIGIN' | paste -sd:)
            [ -z "$clean" ] && clean='$ORIGIN'
            patchelf --set-rpath "$clean" "$f"
            echo "qt6 rpath-cleaned: ${f#%{buildroot}}"
            ;;
    esac
done
%endif

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

# Changelog is %included from sources/o3de.changelog (Source99). See the
# Source99 comment above for the rationale. The included file begins with
# its own %changelog header; do not duplicate it here.
%include %{SOURCE99}
