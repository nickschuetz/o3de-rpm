################################################################################
# O3DE (Open 3D Engine) RPM spec — Fedora 44 / rpm 4.20+
#
# Build the stable release:
#     rpmbuild -bb \
#         --define "_sourcedir $PWD/sources" \
#         --define "_specdir   $PWD" \
#         o3de.spec
#
# Build a development-branch snapshot:
#     ./sources/make-snapshot-tarball.sh development
#     # paste the printed snapshot_commit / snapshot_date / snapshot_sha256
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
%bcond_with debug_only

# Per-3rdParty-package toggles. Add more as you add Source10x lines below.
%bcond_with thirdparty_physx
%bcond_with thirdparty_openexr

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

# Snapshot pin — populated by sources/make-snapshot-tarball.sh.
# Pinned to stabilization/26050 tip for end-to-end build test.
%global snapshot_commit 246b46f500e06eb819421e12644745e95872bb28
%global snapshot_date   20260425
%global snapshot_sha256 80142f1934c3938cf9422f8f4376426084a0443df3ed80c400ff1b0610c98718
%global shortcommit %(c=%{snapshot_commit}; echo ${c:0:7})

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

# Uncompressed cpio at the spec level — final payload still gets the
# rpm-config compression. Empirically faster builds on slow disks; size
# tradeoff measured separately (see FEDORA_ROADMAP.md).
%global _source_payload w0.ufdio
%global _binary_payload w0.ufdio

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

Name:           o3de
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
Source13:       o3de.cdx.json
Source14:       o3de.metainfo.xml
# NoDisplay association entry: maps the Editor's WM_CLASS to o3de icon.
Source15:       o3de-editor.desktop

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
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  python3-devel
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

# ── Runtime dependencies ─────────────────────────────────────────────────────
# RPM auto-Requires picks up every actual link target by walking the
# binaries with ldd. Only declare what auto-Requires can't see:
#   - mesa-libGL provides libGL.so.1 / libGLX.so.0 / libOpenGL.so.0 (auto-detected)
#     but we list it explicitly so plain `dnf install o3de` resolves cleanly.
#   - cmake is invoked by /usr/bin/o3de (the launcher wrapper) for engine-id
#     calculation; it's a shell-script dep that auto-Requires won't see.
# Everything else (Qt5*, libxcb-*, libxkbcommon, fontconfig, freetype,
# libunwind, libzstd, libatomic, libpython3.10, libpyside2, …) comes
# from auto-Requires walking /opt/o3de/.
Requires:       mesa-libGL
Requires:       cmake
Requires:       python3

%description
The Open 3D Engine (O3DE) is an Apache-licensed, real-time, multi-platform
3D engine for building AAA games, cinema-quality 3D worlds, and
high-fidelity simulations.

%if %{with snapshot}
This build is a development snapshot at commit %{shortcommit} (%{snapshot_date}).
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

%if %{with debug_only}
%global _o3de_configs debug
%else
%global _o3de_configs debug;profile
%endif

# FindThreads' compiler feature-tests false-fail when O3DE's bundled qt5
# .prl processing triggers find_package(Threads) re-entry. Force the
# pthread result so configure proceeds.
cmake \
    -S . -B build \
    -G "Ninja Multi-Config" \
    -DCMAKE_CONFIGURATION_TYPES="%{_o3de_configs}" \
    -DCMAKE_INSTALL_PREFIX=/opt/o3de \
    -DLY_3RDPARTY_PATH=%{_builddir}/%{o3de_source_dir}/3rdParty \
    -DO3DE_INSTALL_ENGINE_NAME=o3de \
    -DO3DE_INSTALL_VERSION_STRING=%{engine_cmake_version} \
    -DO3DE_INSTALL_DISPLAY_VERSION_STRING=%{engine_cmake_version} \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=OFF \
    -DTHREADS_PREFER_PTHREAD_FLAG=ON \
    -DCMAKE_THREAD_LIBS_INIT=-lpthread \
    -DCMAKE_HAVE_THREADS_LIBRARY=1 \
    -DCMAKE_USE_PTHREADS_INIT=1 \
    -DCMAKE_EXE_LINKER_FLAGS_INIT="-Wl,-z,relro -Wl,-z,now" \
    -DCMAKE_SHARED_LINKER_FLAGS_INIT="-Wl,-z,relro -Wl,-z,now"

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

cmake --build build --config debug --parallel %{_smp_build_ncpus}
%if %{without debug_only}
cmake --build build --config profile --parallel %{_smp_build_ncpus}
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
#   DEFAULT_DEBUG    debug-config binaries
#   DEFAULT_PROFILE  profile-config binaries (default ship config)
DESTDIR=%{buildroot} cmake --install build --config debug --component CORE
DESTDIR=%{buildroot} cmake --install build --config debug --component DEFAULT
%if %{with debug_only}
DESTDIR=%{buildroot} cmake --install build --config debug --component DEFAULT_DEBUG
%else
DESTDIR=%{buildroot} cmake --install build --config profile --component DEFAULT_PROFILE
%endif

# Normalize ambiguous '#!/usr/bin/env python' shebangs to 'python3' across
# the entire engine tree so brp-mangle-shebangs accepts them. We deliberately
# keep '/usr/bin/env' (not a hardcoded /usr/bin/python3) so the bundled
# Python venv is found via PATH when the launcher activates it.
find %{buildroot}/opt/o3de -type f -name '*.py' \
    -exec sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

# Editor expects engine.json + python relative to the binary's location.
# Only create symlinks for the config we actually installed.
%if %{with debug_only}
%global _installed_config debug
%else
%global _installed_config profile
%endif
ln -s ../../../../python      %{buildroot}/opt/o3de/bin/Linux/%{_installed_config}/Default/python
ln -s ../../../../engine.json %{buildroot}/opt/o3de/bin/Linux/%{_installed_config}/Default/engine.json

# Launcher wrapper + desktop entries from real Source files. The
# o3de.desktop entry (Source11) is the user-visible menu launcher
# (Project Manager). The o3de-editor.desktop entry (Source15) is
# NoDisplay=true and exists only so GNOME/KDE can match the Editor's
# running window to our installed o3de icon — without it, the dock
# falls through to Qt's internal icon for the Editor.
install -D -m 0755 %{SOURCE10} %{buildroot}%{_bindir}/o3de
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{SOURCE11}
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{SOURCE15}

# AppStream metainfo for GNOME Software / KDE Discover. Required for
# Fedora-distributed GUI applications.
install -D -m 0644 %{SOURCE14} \
    %{buildroot}%{_metainfodir}/o3de.metainfo.xml

# Hicolor icon theme — six standard sizes from the upstream master ICO.
for SZ in 16 32 48 64 128 256; do
    case $SZ in
        16)  SRC=%{SOURCE20} ;; 32)  SRC=%{SOURCE21} ;;
        48)  SRC=%{SOURCE22} ;; 64)  SRC=%{SOURCE23} ;;
        128) SRC=%{SOURCE24} ;; 256) SRC=%{SOURCE25} ;;
    esac
    install -D -m 0644 "$SRC" \
        %{buildroot}%{_datadir}/icons/hicolor/${SZ}x${SZ}/apps/o3de.png
done

# Ship the SBOM next to the license/docs so it's discoverable post-install.
install -D -m 0644 %{SOURCE13} %{buildroot}%{_datadir}/o3de/sbom/o3de.cdx.json

# ── CHECK ────────────────────────────────────────────────────────────────────
%check
desktop-file-validate %{buildroot}%{_datadir}/applications/o3de.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/o3de-editor.desktop
appstream-util validate-relax --nonet \
    %{buildroot}%{_metainfodir}/o3de.metainfo.xml

# ── FILES ────────────────────────────────────────────────────────────────────
%files
%license LICENSE.txt LICENSE_APACHE2.TXT LICENSE_MIT.TXT
%doc README.md CODE_OF_CONDUCT.md CONTRIBUTING.md
/opt/o3de
%{_bindir}/o3de
%{_datadir}/applications/o3de.desktop
%{_datadir}/applications/o3de-editor.desktop
%{_metainfodir}/o3de.metainfo.xml
%{_datadir}/icons/hicolor/16x16/apps/o3de.png
%{_datadir}/icons/hicolor/32x32/apps/o3de.png
%{_datadir}/icons/hicolor/48x48/apps/o3de.png
%{_datadir}/icons/hicolor/64x64/apps/o3de.png
%{_datadir}/icons/hicolor/128x128/apps/o3de.png
%{_datadir}/icons/hicolor/256x256/apps/o3de.png
%{_datadir}/o3de/sbom/o3de.cdx.json

# ── Scriptlets ───────────────────────────────────────────────────────────────
%post
if [ -x /opt/o3de/scripts/o3de.sh ]; then
    /opt/o3de/scripts/o3de.sh register --this-engine || :
fi
/usr/bin/update-desktop-database -q %{_datadir}/applications &>/dev/null || :
/usr/bin/gtk-update-icon-cache --quiet --force \
    %{_datadir}/icons/hicolor &>/dev/null || :

cat <<'EOF'

O3DE installed at /opt/o3de.

Finalize the per-user Python venv before first launch:

    /opt/o3de/python/get_python.sh

Then run the editor:

    o3de                              # profile build (default)
    O3DE_BUILD_CONFIG=debug o3de      # debug build

EOF

%postun
/usr/bin/update-desktop-database -q %{_datadir}/applications &>/dev/null || :
/usr/bin/gtk-update-icon-cache --quiet --force \
    %{_datadir}/icons/hicolor &>/dev/null || :

# ── Changelog ────────────────────────────────────────────────────────────────
%changelog
* Thu Apr 30 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2605.0-6
- Re-enable cmake's Unity build. The clang 22.1.2 codegen bug (Greedy
  Register Allocator SIGSEGV on heavily-templated AZStd containers at
  -O2) is fixed in clang 22.1.4 (Fedora 44 update on 2026-04-30).
  Verified via stress-test compile of representative templates.

* Thu Apr 30 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2605.0-5
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

* Thu Apr 30 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2605.0-4
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

* Thu Apr 30 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2605.0-3
- Restore %%__requires_exclude for libclang-12 / libtinfo.so.6 — required
  by O3DE's bundled DirectXShaderCompiler (RPATH-resolved internally).
  Without it, dnf install fails with "nothing provides libclang-12.so.1".

* Wed Apr 29 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2605.0-2
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

* Wed Apr 29 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2605.0-1
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

* Wed Apr 29 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2510.2-1
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

* Tue Jan 27 2026 Nicholas Schuetz <nschuetz@redhat.com> - 2510.2-0
- New point release build for 25.10.2

* Wed Dec 10 2025 Nicholas Schuetz <nschuetz@redhat.com> - 2510.1-1
- New point release build for 25.10.1

* Sat Nov 22 2025 Nicholas Schuetz <nschuetz@redhat.com> - 2510.0-1
- Rewritten RPM package for O3DE v25.10.0

* Thu Aug 24 2023 Roddie Kieley <roddie@kieley.ca> - 2305.1-1
- Updated for v23.05.1 release

* Fri Aug 04 2023 Nicholas Frizzell <nfrizzel@redhat.com> - 2305.0-6
- Misc. cleanup and documentation
