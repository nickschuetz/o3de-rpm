#
# FindOpenEXR.cmake — system-package stub for o3de-rpm's Stage 2a migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME OpenEXR-3.1.3-rev4-linux ...
#                          TARGETS OpenEXR Imath ...)
# entry that fetches OpenEXR (and the Imath sibling library) from
# packages.o3de.org. Despite the bundle's name, it ships TWO separate
# logical libraries upstream — OpenEXR proper plus its required Imath
# dependency — and the cmake target list reflects that.
#
# Mirrors the bundle's two-target shape across two Find modules:
#   - FindImath-system.cmake → cmake/3rdParty/FindImath.cmake (separate
#     because the bundled FindOpenColorIO.cmake calls find_package(Imath)
#     independently, and OCIO/OIIO bundles run before any OpenEXR consumer).
#   - This file → cmake/3rdParty/FindOpenEXR.cmake (creates 3rdParty::OpenEXR
#     by linking the OpenEXR library family + delegating Imath via
#     find_package(Imath)).
#
# Layout:
#
#   |             | O3DE bundle (3.1.3-rev4)             | Fedora F44 (3.2.4) |
#   |-------------|--------------------------------------|----------------------|
#   | OpenEXR hdr | <bundle>/include/OpenEXR/Imf*.h      | /usr/include/OpenEXR/Imf*.h |
#   | OpenEXR lib | libOpenEXR.so + libIex/libIlmThread… | libOpenEXR-3_2.so.31 + libOpenEXRCore-3_2 + libIex-3_2 + libIlmThread-3_2 |
#
# Engine consumers (Gems/Atom/Asset/ImageProcessingAtom) use
# `#include <OpenEXR/ImfArray.h>` etc. — matches Fedora's layout exactly,
# no wrapper-header bridging needed.
#
# Version note: O3DE's bundle is OpenEXR 3.1.3 / Imath 3.1.x; F44 ships
# OpenEXR 3.2.4 / Imath 3.1.12. Per Nick_L (sig-build, 2026-05-05), the
# OpenEXR version pin in the engine is not hard — system version works
# as long as API-compatible. 3.1 → 3.2 is back-compatible per OpenEXR's
# semver.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/
# alongside FindImath.cmake during %prep, and pass
# -DLY_USE_SYSTEM_OPENEXR=ON to cmake.

# NOTE: don't use a TARGET_WITH_NAMESPACE local variable here — this shim
# calls find_package(Imath) which includes FindImath.cmake at parent scope,
# and that file would overwrite our local TARGET_WITH_NAMESPACE with
# "3rdParty::Imath", causing the subsequent add_library() to try to create
# 3rdParty::Imath instead of 3rdParty::OpenEXR. Use the literal target
# name throughout this shim.

if (TARGET 3rdParty::OpenEXR)
    set(OpenEXR_FOUND TRUE)
    return()
endif()

# Imath comes via its own Find module (creates 3rdParty::Imath +
# Imath::Imath alias). REQUIRED because OpenEXR can't link without it.
find_package(Imath REQUIRED)

find_path(OPENEXR_SYSTEM_INCLUDE_DIR
    NAMES OpenEXR/ImfHeader.h
    PATHS /usr/include /usr/local/include
)

find_library(OPENEXR_SYSTEM_LIBRARY
    NAMES OpenEXR-3_2 OpenEXR
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

find_library(OPENEXR_CORE_SYSTEM_LIBRARY
    NAMES OpenEXRCore-3_2 OpenEXRCore
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

find_library(IEX_SYSTEM_LIBRARY
    NAMES Iex-3_2 Iex
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

find_library(ILMTHREAD_SYSTEM_LIBRARY
    NAMES IlmThread-3_2 IlmThread
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT OPENEXR_SYSTEM_INCLUDE_DIR OR NOT OPENEXR_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindOpenEXR (system stub): could not locate OpenEXR/ImfHeader.h "
        "(${OPENEXR_SYSTEM_INCLUDE_DIR}) and/or libOpenEXR "
        "(${OPENEXR_SYSTEM_LIBRARY}). Install openexr-devel from Fedora, "
        "or set LY_USE_SYSTEM_OPENEXR=OFF to fall back to the upstream fetcher.")
endif()

add_library(3rdParty::OpenEXR INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::OpenEXR
    INTERFACE ${OPENEXR_SYSTEM_INCLUDE_DIR})
target_link_libraries(3rdParty::OpenEXR
    INTERFACE
        ${OPENEXR_SYSTEM_LIBRARY}
        ${OPENEXR_CORE_SYSTEM_LIBRARY}
        ${IEX_SYSTEM_LIBRARY}
        ${ILMTHREAD_SYSTEM_LIBRARY}
        3rdParty::Imath)

# Upper-namespace alias for any upstream consumer that does
# `find_package(OpenEXR)` and then references `OpenEXR::OpenEXR`.
if (NOT TARGET OpenEXR::OpenEXR)
    add_library(OpenEXR::OpenEXR ALIAS 3rdParty::OpenEXR)
endif()

set(OpenEXR_FOUND TRUE)
