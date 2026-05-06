#
# FindImath.cmake — system-package stub for o3de-rpm's Stage 2a migration.
#
# Companion to FindOpenEXR-system.cmake. Both ship under
# system_openexr (they're a single ly_associate_package bundle upstream
# with TARGETS OpenEXR Imath, but the bundled FindOpenColorIO.cmake
# does an independent `find_package(Imath REQUIRED MODULE)`, so we need
# a separate Find module that resolves on CMAKE_MODULE_PATH.
#
# Creates `3rdParty::Imath` (INTERFACE IMPORTED) plus the upper-namespace
# `Imath::Imath` alias that bundled OCIO/OIIO consumers expect.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/
# during %prep alongside FindOpenEXR.cmake when --with system_openexr.

# NOTE: literal target name (not via TARGET_WITH_NAMESPACE) — see comment
# in FindOpenEXR-system.cmake about variable scope pollution when one shim
# include()s another via find_package.

if (TARGET 3rdParty::Imath)
    set(Imath_FOUND TRUE)
    return()
endif()

# Find /usr/include/Imath directly (not /usr/include) — Fedora's
# /usr/include/OpenEXR/ImfFrameBuffer.h includes <ImathBox.h> without the
# Imath/ prefix (matches pkg-config OpenEXR --cflags `-I/usr/include/Imath`).
# Exposing /usr/include/Imath as the include dir resolves both:
#   - `#include <ImathBox.h>` (used by Fedora's OpenEXR system headers)
#   - `#include <ImathConfig.h>` etc. (direct Imath consumers)
find_path(IMATH_SYSTEM_INCLUDE_DIR
    NAMES ImathConfig.h
    PATHS /usr/include/Imath /usr/local/include/Imath
)

find_library(IMATH_SYSTEM_LIBRARY
    NAMES Imath-3_1 Imath
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT IMATH_SYSTEM_INCLUDE_DIR OR NOT IMATH_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindImath (system stub): could not locate Imath/ImathConfig.h "
        "(${IMATH_SYSTEM_INCLUDE_DIR}) and/or libImath "
        "(${IMATH_SYSTEM_LIBRARY}). Install imath-devel from Fedora, or set "
        "LY_USE_SYSTEM_OPENEXR=OFF to fall back to the upstream fetcher.")
endif()

add_library(3rdParty::Imath INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::Imath
    INTERFACE ${IMATH_SYSTEM_INCLUDE_DIR})
target_link_libraries(3rdParty::Imath INTERFACE ${IMATH_SYSTEM_LIBRARY})

# Upper-namespace alias for upstream consumers — bundled FindOpenColorIO.cmake
# checks `if (NOT TARGET Imath::Imath)` to decide whether to fetch Imath
# itself; providing the alias here lets that check pass without round-trip.
if (NOT TARGET Imath::Imath)
    add_library(Imath::Imath ALIAS 3rdParty::Imath)
endif()

set(Imath_FOUND TRUE)
