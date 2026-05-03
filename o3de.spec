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
%bcond_with system_expat
%bcond_with system_freetype
%bcond_with system_lua
%bcond_with system_mikkelsen
%bcond_with system_png
%bcond_with system_tiff
%bcond_with system_zlib

# ── Version pinning ──────────────────────────────────────────────────────────
%global stable_tag      2605.0
# Compute with: sha256sum o3de_<tag>_lfs.tar.gz
%global stable_sha256   0000000000000000000000000000000000000000000000000000000000000000

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

# Snapshot pin — populated by sources/make-snapshot-tarball.sh.
# Pinned to stabilization/26050 tip for end-to-end build test.
%global snapshot_commit 246b46f500e06eb819421e12644745e95872bb28
%global snapshot_date   20260425
%global snapshot_sha256 80142f1934c3938cf9422f8f4376426084a0443df3ed80c400ff1b0610c98718
%global shortcommit %(c=%{snapshot_commit}; echo ${c:0:7})

# Channel-identifying suffix for the version strings the GUI displays.
# Without this, every build (stable / snapshot / experimental) shows
# "26.05.0" / "Version 2605.0" — a tester can't tell from the GUI which
# RPM they have. We compute one suffix here and apply it to BOTH
# DISPLAY_VERSION_STRING (PM titlebar via Patch0005) and BUILD_VERSION
# (Editor splash) so the two surfaces stay consistent.
#
# Channel marker, chosen in priority order:
#   experimental   any Stage 1 system_<X> bcond active (chroot --rpmbuild-with)
#   stabilization  --with stabilization (the pre-release tester channel)
#   snapshot       --with snapshot only (one-off development-branch build)
#   stable         neither (tagged release tarball)
# `%%{with X}` is the canonical bcond-aware truthiness test — it returns
# 1 when the bcond is on, 0 when off (NOT undefined). Add new
# system_<X> bconds to the experimental OR-chain as the Stage 1
# migration list grows.
%global _o3de_channel %{nil}
%if %{with system_expat} || %{with system_freetype} || %{with system_lua} || %{with system_mikkelsen} || %{with system_png} || %{with system_tiff} || %{with system_zlib}
%global _o3de_channel -experimental
%else
%if %{with stabilization}
%global _o3de_channel -stabilization
%else
%if %{with snapshot}
%global _o3de_channel -snapshot
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
Source0:        https://github.com/o3de/o3de/releases/download/%{stable_tag}/o3de_%{stable_tag}_lfs.tar.gz
%endif

# Auxiliary sources kept alongside the spec.
Source10:       o3de-launcher.sh
Source11:       o3de.desktop
Source12:       make-snapshot-tarball.sh
Source13:       %{o3de_pkgname}.cdx.json
Source14:       o3de.metainfo.xml
# NoDisplay association entry: maps the Editor's WM_CLASS to o3de icon.
Source15:       o3de-editor.desktop
# Thin wrapper exposing the engine's scripts/o3de.sh CLI on $PATH as
# %%{o3de_pkgname}-cli (versioned binary name; multiple installed majors
# get distinct PATH entries).
Source16:       o3de-cli

# App icons in hicolor sizes. Extracted from upstream's
# cmake/Platform/Windows/Packaging/product_icon.ico (256x256 master,
# downsampled with imagemagick).
Source20:       o3de-16x16.png
Source21:       o3de-32x32.png
Source22:       o3de-48x48.png
Source23:       o3de-64x64.png
Source24:       o3de-128x128.png
Source25:       o3de-256x256.png

# Patches against the upstream tree (apply with -p1).
Patch0001:      0001-clang21-warning-suppressions.patch
Patch0002:      0002-manifest-py-engine-path-detection.patch
Patch0003:      0003-get-python-sh-rpm-venv-fixes.patch
Patch0004:      0004-lypython-non-editable-pip-for-installed-engine.patch
Patch0005:      0005-windowdecorationwrapper-propagate-initial-title.patch

# Migrate every remaining legacy libtiff typedef use (uint8/uint16/uint32)
# to the standard C99 (`*_t`) names across O3DE's two <tiffio.h> consumers:
#   - Gems/Atom/Asset/ImageProcessingAtom/.../TIFFLoader.cpp (modern Atom)
#   - Code/Editor/Util/ImageTIF.cpp (legacy Editor)
# libtiff 4.5+ marks the legacy typedef as __attribute__((deprecated));
# combined with O3DE's -Werror, every stale use becomes a hard build
# failure. Mechanical type rename; behavior unchanged. Applies
# unconditionally so the source tree stays consistent whether libtiff
# resolves from the upstream CDN bundle or from system tiff-devel.
Patch0007:      0007-libtiff-c99-typedefs.patch

# Stage 1 system-library swap patches — each gates one upstream
# ly_associate_package(...) line on a new LY_USE_SYSTEM_<X> cmake var,
# and pairs with a corresponding system Find<X>.cmake (Source30+ below).
Patch0006:      0006-builtinpackages-gate-mikkelsen-on-system.patch

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
# clang in %build below to match. gcc-c++ stays in BR because some
# host-build tools (ispc, pre-built shaders) still expect a GCC stub.
BuildRequires:  clang
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  python3-devel
# `python3 setup.py sdist` (used in %build to pre-build the three Python
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

# Vulkan — engine dlopen()s the loader, but headers/loader-devel are
# needed at configure time for find_package(Vulkan).
BuildRequires:  vulkan-headers
BuildRequires:  vulkan-loader-devel

# Stage 1 system-library swaps — only pulled in when the matching
# bcond is enabled (--with system_<lib>). Most live in Fedora proper
# already (zlib-devel, freetype-devel, libpng-devel, libtiff-devel,
# expat-devel, lua-devel); mikkelsen lives in hellaenergy/o3de-dependencies
# on COPR until it's accepted into Fedora.
%if %{with system_expat}
BuildRequires:  expat-devel
%endif
%if %{with system_freetype}
BuildRequires:  freetype-devel
%endif
%if %{with system_lua}
BuildRequires:  lua-devel
%endif
%if %{with system_mikkelsen}
BuildRequires:  mikkelsen-devel
%endif
%if %{with system_png}
BuildRequires:  libpng-devel
%endif
%if %{with system_tiff}
BuildRequires:  libtiff-devel
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
Requires:       cmake
Requires:       python3

# Stage 1 system-library runtime side. RPM auto-Requires picks up the
# .so.N dependencies by ldd-walking engine binaries, but listing the
# package names explicitly is clearer for reviewers (and survives if a
# future build statically links and the auto-dep disappears).
%if %{with system_expat}
Requires:       expat
%endif
%if %{with system_freetype}
Requires:       freetype
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
%if %{with system_tiff}
Requires:       libtiff
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

# TODO(devel-split): Split lib/Linux/profile/Default/*.a (~4 GB of static
# archives) out into a %%{name}-devel subpackage (resolves to o3de2605-devel,
# o3de2610-devel, etc. — versioned automatically via %%package devel
# inheriting %%{name}). Those archives are only needed by people
# C++-linking against the engine to write native gems — Lua/ScriptCanvas
# project authors and runtime users never touch them. Roughly halves the
# main package on top of the compression switch. Care needed for which
# cmake/<...>Targets.cmake files travel with the static libs vs. stay
# with the runtime cmake of the main package.

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

%autosetup -n %{o3de_source_dir} -p1

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
cmake \
    -S . -B build \
    -G "Ninja Multi-Config" \
    -DCMAKE_C_COMPILER=clang \
    -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_CONFIGURATION_TYPES="%{_o3de_configs}" \
    -DCMAKE_INSTALL_PREFIX=%{o3de_install_prefix} \
    -DLY_3RDPARTY_PATH=%{_builddir}/%{o3de_source_dir}/3rdParty \
    -DO3DE_INSTALL_ENGINE_NAME=%{o3de_pkgname} \
    -DO3DE_INSTALL_VERSION_STRING=%{engine_cmake_version} \
    -DO3DE_INSTALL_DISPLAY_VERSION_STRING='"%{_o3de_display_version}"' \
    -DO3DE_INSTALL_BUILD_VERSION='"%{_o3de_build_version}"' \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=OFF \
    -DTHREADS_PREFER_PTHREAD_FLAG=ON \
    -DCMAKE_THREAD_LIBS_INIT=-lpthread \
    -DCMAKE_HAVE_THREADS_LIBRARY=1 \
    -DCMAKE_USE_PTHREADS_INIT=1 \
    -DCMAKE_EXE_LINKER_FLAGS_INIT="-Wl,-z,relro -Wl,-z,now" \
    -DCMAKE_SHARED_LINKER_FLAGS_INIT="-Wl,-z,relro -Wl,-z,now" \
    %{?with_system_expat:-DLY_USE_SYSTEM_EXPAT=ON} \
    %{?with_system_freetype:-DLY_USE_SYSTEM_FREETYPE=ON} \
    %{?with_system_lua:-DLY_USE_SYSTEM_LUA=ON} \
    %{?with_system_mikkelsen:-DLY_USE_SYSTEM_MIKKELSEN=ON} \
    %{?with_system_png:-DLY_USE_SYSTEM_PNG=ON} \
    %{?with_system_tiff:-DLY_USE_SYSTEM_TIFF=ON} \
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
# %install time:
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

# Editor association entry — NoDisplay=true; exists only so dock-icon
# attachment finds our icon when the Editor's Qt window class shows up.
desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    --set-key=Exec --set-value=%{o3de_install_prefix}/bin/Linux/profile/Default/Editor \
    --set-key=Icon --set-value=%{o3de_pkgname} \
    --set-key=Name --set-value="O3DE %{engine_cmake_version} Editor" \
    --set-key=StartupWMClass --set-value="O3DE-%{o3de_major_tag} Editor" \
    %{SOURCE15}
mv %{buildroot}%{_datadir}/applications/o3de-editor.desktop \
   %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-editor.desktop

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

# Hicolor icon theme — six standard sizes from the upstream master ICO.
# Versioned filenames so multiple majors don't clobber each other's icon.
for SZ in 16 32 48 64 128 256; do
    case $SZ in
        16)  SRC=%{SOURCE20} ;; 32)  SRC=%{SOURCE21} ;;
        48)  SRC=%{SOURCE22} ;; 64)  SRC=%{SOURCE23} ;;
        128) SRC=%{SOURCE24} ;; 256) SRC=%{SOURCE25} ;;
    esac
    install -D -m 0644 "$SRC" \
        %{buildroot}%{_datadir}/icons/hicolor/${SZ}x${SZ}/apps/%{o3de_pkgname}.png
done

# Ship the SBOM next to the license/docs so it's discoverable post-install.
install -D -m 0644 %{SOURCE13} \
    %{buildroot}%{_datadir}/%{o3de_pkgname}/sbom/%{o3de_pkgname}.cdx.json

# ── CHECK ────────────────────────────────────────────────────────────────────
%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{o3de_pkgname}.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/%{o3de_pkgname}-editor.desktop
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
# in the %{name}-debug subpackage, not the main one.
%exclude %{o3de_install_prefix}/bin/Linux/debug
%exclude %{o3de_install_prefix}/lib/Linux/debug
%endif
%{_bindir}/%{o3de_pkgname}
%{_bindir}/%{o3de_pkgname}-cli
%{_datadir}/applications/%{o3de_pkgname}.desktop
%{_datadir}/applications/%{o3de_pkgname}-editor.desktop
%{_metainfodir}/%{o3de_pkgname}.metainfo.xml
%{_datadir}/icons/hicolor/16x16/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/32x32/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/48x48/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/64x64/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/128x128/apps/%{o3de_pkgname}.png
%{_datadir}/icons/hicolor/256x256/apps/%{o3de_pkgname}.png
%{_datadir}/%{o3de_pkgname}/sbom/%{o3de_pkgname}.cdx.json

%if %{with debug}
%files debug
%{o3de_install_prefix}/bin/Linux/debug
%{o3de_install_prefix}/lib/Linux/debug
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
- Add `BuildRequires: python3-setuptools`. The %build sdist-builder
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
