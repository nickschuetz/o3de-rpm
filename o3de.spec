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

# Patch O3DE's Clang configuration to add warning suppressions for clang 21+
sed -i '/Wno-dllexport-explicit-instantiation-decl/a\        -Wno-error=deprecated-volatile  # clang 21+ compatibility\n        -Wno-error=character-conversion  # clang 21+ compatibility' cmake/Platform/Common/Clang/Configurations_clang.cmake

%build
# Remove any existing build directory to ensure clean configuration
rm -rf build

# Create build directory
mkdir -p build

# Override hardened build specs that interfere with O3DE's build system
unset CFLAGS
unset CXXFLAGS
unset LDFLAGS

# Configure with CMake - debug configuration
cmake \
    -S . \
    -B build \
    -G Ninja \
    -DCMAKE_BUILD_PARALLEL_LEVEL=$(nproc) \
    -DCMAKE_BUILD_TYPE=debug \
    -DCMAKE_CONFIGURATION_TYPES=debug \
    -DCMAKE_INSTALL_PREFIX=/usr/o3de \
    -DLY_3RDPARTY_PATH=%{_builddir}/o3de-%{commit}/build/3rdParty \
    -DO3DE_INSTALL_ENGINE_NAME=o3de \
    -DO3DE_INSTALL_VERSION_STRING=%{version} \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=OFF \
    -DCMAKE_THREAD_LIBS_INIT="-lpthread" \
    -DCMAKE_HAVE_THREADS_LIBRARY=1 \
    -DCMAKE_USE_PTHREADS_INIT=1 \
    -DTHREADS_PREFER_PTHREAD_FLAG=ON

# Patch googletest to add compiler flags for clang 21+ compatibility
if [ -f build/_deps/googletest-src/googletest/CMakeLists.txt ]; then
    echo "Patching googletest CMakeLists.txt for clang 21+ compatibility..."
    cat >> build/_deps/googletest-src/googletest/CMakeLists.txt <<'GTEST_EOF'

# Fix for clang 21+ warnings
if(TARGET gtest)
  target_compile_options(gtest PRIVATE -Wno-error=character-conversion -Wno-error=deprecated-volatile)
endif()
if(TARGET gtest_main)
  target_compile_options(gtest_main PRIVATE -Wno-error=character-conversion -Wno-error=deprecated-volatile)
endif()
GTEST_EOF
    # Reconfigure to pick up the changes
    cmake build
fi

# Build
cmake --build build --parallel %{_smp_build_ncpus}

# Create a source distribution package for the o3de Python scripts
# This allows get_python.sh to install it without needing write access to /usr/o3de
cd scripts/o3de
python3 setup.py sdist
cd ../..

%install
# Install from the build directory
# Install all components (CORE, DEFAULT, and DEFAULT_DEBUG) to get scripts, python, cmake, and engine.json
# CMake requires separate install commands for each component
DESTDIR=%{buildroot} cmake --install build --component CORE
DESTDIR=%{buildroot} cmake --install build --component DEFAULT
DESTDIR=%{buildroot} cmake --install build --component DEFAULT_DEBUG

# Fix Python shebangs
find %{buildroot} -type f -name "*.py" -exec sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' {} +

# Create symlinks in the binary location
# O3DE binaries expect certain files to be relative to their location
ln -s ../../../../python %{buildroot}/usr/o3de/bin/Linux/debug/Default/python
ln -s ../../../../engine.json %{buildroot}/usr/o3de/bin/Linux/debug/Default/engine.json

# Patch get_python.sh to NOT install the o3de package in the venv
# Installing it in the venv causes manifest.py to incorrectly detect the engine path
# as the venv lib directory instead of /usr/o3de. We rely on PYTHONPATH instead.
sed -i 's|^\(\s*\)\$DIR/pip.sh install.*o3de.*$|\1# O3DE package installation disabled - using PYTHONPATH instead\n\1# \0|' %{buildroot}/usr/o3de/python/get_python.sh
sed -i '/echo "Failed to install.*o3de into python/d' %{buildroot}/usr/o3de/python/get_python.sh

# Patch get_python.sh to create engine.json symlink and Python path config
# This is required for O3DE to find the engine configuration and modules
sed -i '$i\
# Create engine.json symlink and .pth file in venv (RPM package fix)\
if [ -d "$HOME/.o3de/Python/venv" ]; then\
    for venv_dir in $HOME/.o3de/Python/venv/*/; do\
        if [ -d "$venv_dir" ]; then\
            # Create engine.json symlink\
            if [ ! -f "${venv_dir}lib/engine.json" ]; then\
                ln -sf "$DIR/../engine.json" "${venv_dir}lib/engine.json" 2>/dev/null || true\
            fi\
            # Create .pth file so embedded Python can find o3de module\
            mkdir -p "$HOME/.local/lib/python3.10/site-packages" 2>/dev/null\
            echo "${venv_dir}lib/python3.10/site-packages" > "$HOME/.local/lib/python3.10/site-packages/o3de-venv.pth"\
        fi\
    done\
fi\
\
# Fix for engine path ID mismatch between get_python.sh and O3DE binary\
# The O3DE binary calculates engine ID from bin/Linux/debug/Default/python/..\
# while get_python.sh uses the direct engine path, resulting in different hashes\
if [ -x "$(command -v cmake)" ]; then\
    STANDARD_ENGINE_ID=$(cmake -P $DIR/../cmake/CalculateEnginePathId.cmake "$DIR/.." 2>/dev/null | tail -1)\
    ALTERNATE_ENGINE_ID=$(cmake -P $DIR/../cmake/CalculateEnginePathId.cmake "$DIR/../bin/Linux/debug/Default/python/.." 2>/dev/null | tail -1)\
    if [ -n "$STANDARD_ENGINE_ID" ] && [ -n "$ALTERNATE_ENGINE_ID" ] && [ "$STANDARD_ENGINE_ID" != "$ALTERNATE_ENGINE_ID" ]; then\
        if [ -d "$HOME/.o3de/Python/venv/$STANDARD_ENGINE_ID" ] && [ ! -e "$HOME/.o3de/Python/venv/$ALTERNATE_ENGINE_ID" ]; then\
            ln -s "$STANDARD_ENGINE_ID" "$HOME/.o3de/Python/venv/$ALTERNATE_ENGINE_ID" 2>/dev/null || true\
        elif [ -d "$HOME/.o3de/Python/venv/$ALTERNATE_ENGINE_ID" ] && [ ! -e "$HOME/.o3de/Python/venv/$STANDARD_ENGINE_ID" ]; then\
            ln -s "$ALTERNATE_ENGINE_ID" "$HOME/.o3de/Python/venv/$STANDARD_ENGINE_ID" 2>/dev/null || true\
        fi\
    fi\
fi\
' %{buildroot}/usr/o3de/python/get_python.sh

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

# Create O3DE wrapper script with proper environment setup
cat > %{buildroot}%{_bindir}/o3de << 'O3DE_WRAPPER_EOF'
#!/bin/bash
# O3DE Launcher Wrapper - Sets up environment for O3DE

# Calculate engine ID (matches how python.sh calculates it with trailing slash)
ENGINE_ID=$(/usr/bin/cmake -P /usr/o3de/cmake/CalculateEnginePathId.cmake "/usr/o3de/python/.." 2>/dev/null | tail -1)

# Set PYTHONPATH to include O3DE scripts and venv site-packages
if [ -d "$HOME/.o3de/Python/venv/$ENGINE_ID" ]; then
    export PYTHONPATH="/usr/o3de/scripts:$HOME/.o3de/Python/venv/$ENGINE_ID/lib/python3.10/site-packages:$PYTHONPATH"
else
    export PYTHONPATH="/usr/o3de/scripts:$PYTHONPATH"
fi

# Set LD_LIBRARY_PATH for O3DE libraries
export LD_LIBRARY_PATH="/usr/o3de/bin/Linux/debug/Default:$LD_LIBRARY_PATH"

# Launch O3DE
exec /usr/o3de/bin/Linux/debug/Default/o3de "$@"
O3DE_WRAPPER_EOF
chmod +x %{buildroot}%{_bindir}/o3de

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
%{_bindir}/o3de
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

# Display post-installation instructions
cat << 'POSTINSTALL_MSG'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O3DE Installation Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before using O3DE, you must set up the Python environment:

    /usr/o3de/python/get_python.sh

This will:
  • Download and configure Python 3.10.13
  • Install required Python dependencies
  • Set up the O3DE Python virtual environment

After running the script, you can launch O3DE:

    o3de

Or use the desktop entry from your application menu.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSTINSTALL_MSG

%postun
# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database -q %{_datadir}/applications || true
fi

%changelog
* Thu Nov 20 2025 Package Builder <builder@localhost> - 25100.0.1
- Initial RPM package for O3DE from main branch
- Built for Fedora 43
- Commit: ece239c0113d988907edea0022f7609387ae7baa
