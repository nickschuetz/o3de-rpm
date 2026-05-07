#
# Findpoly2tri.cmake — system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME poly2tri-7f0487a-rev1-linux ...)
# entry that fetches a vendored poly2tri fork from packages.o3de.org. The
# fork carries license-attribution issues that block redistribution; the
# Fedora system poly2tri (from Mason Green's original BSD-3-Clause tree)
# is independent of those issues.
#
# Layout:
#
#   |              | O3DE bundle (poly2tri-7f0487a-rev1)         | Fedora F44 (poly2tri-0.0^20130501) |
#   |--------------|----------------------------------------------|------------------------------------|
#   | header path  | <bundle>/include/poly2tri.h                 | /usr/include/poly2tri/poly2tri.h   |
#   | extra hdrs   | <bundle>/include/{common,sweep}/*.h         | /usr/include/poly2tri/{common,sweep}/*.h |
#   | library      | <bundle>/lib/libpoly2tri.a                  | /usr/lib64/libpoly2tri.so.1        |
#
# Engine consumers (Gems/PhysX/Core/Code/Editor/PolygonPrismMeshUtils.h)
# do `#include <poly2tri.h>` — no `poly2tri/` prefix. Fedora's headers
# live under `/usr/include/poly2tri/`. We bridge by adding
# `/usr/include/poly2tri` directly to the include path so `<poly2tri.h>`
# resolves cleanly.
#
# Engine uses public p2t:: namespace API only (p2t::Point, p2t::Triangle,
# p2t::CDT) — no internal-namespace symbols. Verified via audit
# 2026-05-07 (issue #7); see /tmp/o3de-poly2tri-audit/INVESTIGATION_NOTES.md.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/
# during %prep, and pass -DLY_USE_SYSTEM_POLY2TRI=ON so the gating in
# PhysX4 + PhysX5 PAL_linux.cmake (Patch0009) skips the upstream fetcher.
#
# Pattern: same direct-find-no-stock-include shape as the other Stage 1
# refactored shims. cmake doesn't ship a stock FindPoly2tri.cmake; this
# is the only resolution path.

set(TARGET_WITH_NAMESPACE "3rdParty::poly2tri")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(poly2tri_FOUND TRUE)
    return()
endif()

# Find the directory containing poly2tri.h. Fedora ships at
# /usr/include/poly2tri/ (with poly2tri.h directly inside that dir);
# we add THAT directory to the include path so `#include <poly2tri.h>`
# resolves to /usr/include/poly2tri/poly2tri.h.
find_path(POLY2TRI_SYSTEM_INCLUDE_DIR
    NAMES poly2tri.h
    PATHS /usr/include/poly2tri /usr/local/include/poly2tri
)

find_library(POLY2TRI_SYSTEM_LIBRARY
    NAMES poly2tri
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT POLY2TRI_SYSTEM_INCLUDE_DIR OR NOT POLY2TRI_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findpoly2tri (system stub): could not locate poly2tri.h "
        "(${POLY2TRI_SYSTEM_INCLUDE_DIR}) and/or libpoly2tri "
        "(${POLY2TRI_SYSTEM_LIBRARY}). Install poly2tri-devel from Fedora, "
        "or set LY_USE_SYSTEM_POLY2TRI=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${POLY2TRI_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${POLY2TRI_SYSTEM_LIBRARY})

set(poly2tri_FOUND TRUE)
