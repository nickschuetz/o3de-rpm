# O3DE (Open 3D Engine) RPM Spec File for Fedora 43
# For main branch

%global debug_package %{nil}
%global _build_id_links none
%global __requires_exclude ^libclang-12\\.so.*|^libtinfo\\.so\\.6.*
%global commit ece239c0113d988907edea0022f7609387ae7baa
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global commitdate 20251015

Name:           o3de
Version:        25100.0.1
Release:        1.%{commitdate}git%{shortcommit}%{?dist}
Summary:        Open 3D Engine - A real-time, multi-platform 3D game engine

License:        Apache-2.0 OR MIT
URL:            https://o3de.org
Source0:        https://github.com/o3de/o3de/archive/%{commit}/o3de-%{shortcommit}.tar.gz

# Build requirements
BuildRequires:  cmake >= 3.24.0
BuildRequires:  gcc-c++
BuildRequires:  ninja-build
BuildRequires:  git
BuildRequires:  git-lfs
BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-pip

# Qt5 dependencies
BuildRequires:  qt5-qtbase-devel
BuildRequires:  qt5-qtdeclarative-devel
BuildRequires:  qt5-qtsvg-devel
BuildRequires:  qt5-qttools-devel
BuildRequires:  qt5-qtx11extras-devel

# Graphics and windowing dependencies
BuildRequires:  mesa-libGL-devel
BuildRequires:  mesa-libGLU-devel
BuildRequires:  libX11-devel
BuildRequires:  libXcursor-devel
BuildRequires:  libXi-devel
BuildRequires:  libXinerama-devel
BuildRequires:  libXrandr-devel
BuildRequires:  libxcb-devel
BuildRequires:  xcb-util-devel
BuildRequires:  xcb-util-image-devel
BuildRequires:  xcb-util-keysyms-devel
BuildRequires:  xcb-util-renderutil-devel
BuildRequires:  xcb-util-wm-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  libxkbcommon-x11-devel

# System libraries
BuildRequires:  zlib-devel
BuildRequires:  libcurl-devel
BuildRequires:  openssl-devel
BuildRequires:  fontconfig-devel
BuildRequires:  freetype-devel
BuildRequires:  libunwind-devel
BuildRequires:  libzstd-devel
BuildRequires:  pcre2-devel

# Optional: Vulkan support
BuildRequires:  vulkan-headers
BuildRequires:  vulkan-loader-devel
BuildRequires:  spirv-tools-devel

# Runtime requirements
Requires:       qt5-qtbase
Requires:       qt5-qtdeclarative
Requires:       qt5-qtsvg
Requires:       mesa-libGL
Requires:       mesa-libGLU
Requires:       libX11
Requires:       libXcursor
Requires:       libXi
Requires:       libXinerama
Requires:       libXrandr
Requires:       libxcb
Requires:       libxkbcommon
Requires:       libxkbcommon-x11
Requires:       zlib
Requires:       libcurl
Requires:       openssl
Requires:       fontconfig
Requires:       freetype
Requires:       libunwind
Requires:       libzstd
Requires:       python3 >= 3.10
Requires:       vulkan-loader

%description
O3DE (Open 3D Engine) is an open-source, real-time, multi-platform 3D engine
that enables developers and content creators to build AAA games, cinema-quality
3D worlds, and high-fidelity simulations without any fees or commercial obligations.

This package is built from the main branch.

%prep
%autosetup -n o3de-%{commit}

%build
# Remove any existing build directory to ensure clean configuration
rm -rf build

# Create build directory
mkdir -p build

# Override hardened build specs that interfere with O3DE's build system
unset CFLAGS
unset CXXFLAGS
unset LDFLAGS

# Configure with CMake - limit to profile configuration only
cmake \
    -S . \
    -B build \
    -G Ninja \
    -DCMAKE_BUILD_TYPE=profile \
    -DCMAKE_CONFIGURATION_TYPES=profile \
    -DCMAKE_INSTALL_PREFIX=/usr/o3de \
    -DLY_3RDPARTY_PATH=%{_builddir}/o3de-%{commit}/build/3rdParty \
    -DO3DE_INSTALL_ENGINE_NAME=o3de \
    -DO3DE_INSTALL_VERSION_STRING=%{version} \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=ON \
    -DCMAKE_THREAD_LIBS_INIT="-lpthread" \
    -DCMAKE_HAVE_THREADS_LIBRARY=1 \
    -DCMAKE_USE_PTHREADS_INIT=1 \
    -DTHREADS_PREFER_PTHREAD_FLAG=ON

# Build
cmake --build build --parallel %{_smp_build_ncpus}

# Generate o3de.egg-info for Python package metadata (required for install)
cd scripts/o3de
python3 setup.py egg_info
cd ../..

%install
# Install from the build directory
# Install all components (CORE, DEFAULT, and DEFAULT_PROFILE) to get scripts, python, cmake, and engine.json
# CMake requires separate install commands for each component
DESTDIR=%{buildroot} cmake --install build --component CORE
DESTDIR=%{buildroot} cmake --install build --component DEFAULT
DESTDIR=%{buildroot} cmake --install build --component DEFAULT_PROFILE

# Fix Python shebangs
find %{buildroot} -type f -name "*.py" -exec sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

# Create desktop entry
mkdir -p %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/o3de-editor.desktop <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=O3DE Editor
Comment=Open 3D Engine Editor
Exec=%{_bindir}/o3de-editor
Icon=o3de
Terminal=false
Categories=Development;3DGraphics;Game;
Keywords=game;engine;3d;development;
EOF

# Create icon directories (placeholder - actual icons would need to be extracted)
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
mkdir -p %{buildroot}%{_datadir}/pixmaps

# Create symlinks for common executables
mkdir -p %{buildroot}%{_bindir}

# Set up environment script
mkdir -p %{buildroot}%{_sysconfdir}/profile.d
cat > %{buildroot}%{_sysconfdir}/profile.d/o3de.sh <<'EOF'
# O3DE Environment Setup
export O3DE_HOME=/usr/o3de
export PATH=$PATH:$O3DE_HOME/bin
EOF

%files
%license LICENSE.txt LICENSE_APACHE2.TXT LICENSE_MIT.TXT
%doc README.md CODE_OF_CONDUCT.md CONTRIBUTING.md
/usr/o3de/*
%{_datadir}/applications/o3de-editor.desktop
%config(noreplace) %{_sysconfdir}/profile.d/o3de.sh
%{_datadir}/icons/hicolor/256x256/apps/
%{_datadir}/pixmaps/

%post
# Register the engine after installation
if [ -x /usr/o3de/scripts/o3de.sh ]; then
    /usr/o3de/scripts/o3de.sh register --this-engine || true
fi

# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database -q %{_datadir}/applications || true
fi

%postun
# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database -q %{_datadir}/applications || true
fi

%changelog
* Mon Oct 06 2025 Package Builder <nscheutz@redhat.com> - 25100.0.1
- Initial RPM package for O3DE from main branch
- Built for Fedora 43
- Commit: ece239c0113d988907edea0022f7609387ae7baa
