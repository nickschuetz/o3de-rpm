#
# FindFreetype.cmake — system-freetype shim for o3de-rpm Stage 1.
#
# Refactored 2026-05-04 to the mikkelsen pattern (direct find_path +
# find_library, no `include(${CMAKE_ROOT}/Modules/FindFreetype.cmake)`).
# Same root cause and same fix as FindZLIB-system.cmake — see that
# file's comment block for the full diagnosis.
#
# FreeType layout on Fedora (and most modern distros):
#
#   /usr/include/freetype2/ft2build.h           (top-level entry header)
#   /usr/include/freetype2/freetype/freetype.h  (and the rest under freetype/)
#
# Both header forms (`#include <ft2build.h>` AND `#include <freetype/...>`)
# resolve via a SINGLE `-I/usr/include/freetype2` on the include path:
#   - `<ft2build.h>` → /usr/include/freetype2/ft2build.h
#   - `<freetype/freetype.h>` → /usr/include/freetype2/freetype/freetype.h
# So we only need one find_path call rooted at the freetype2/ dir.

set(TARGET_WITH_NAMESPACE "3rdParty::Freetype")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(Freetype_FOUND TRUE)
    set(FREETYPE_FOUND TRUE)
    return()
endif()

find_path(FREETYPE_SYSTEM_INCLUDE_DIR
    NAMES ft2build.h
    PATHS /usr/include/freetype2 /usr/local/include/freetype2
)

find_library(FREETYPE_SYSTEM_LIBRARY
    NAMES freetype
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT FREETYPE_SYSTEM_INCLUDE_DIR OR NOT FREETYPE_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindFreetype (system stub): could not locate ft2build.h under "
        "/usr/include/freetype2 (${FREETYPE_SYSTEM_INCLUDE_DIR}) and/or "
        "libfreetype (${FREETYPE_SYSTEM_LIBRARY}). Install freetype-devel "
        "from Fedora, or set LY_USE_SYSTEM_FREETYPE=OFF to fall back to "
        "the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${FREETYPE_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${FREETYPE_SYSTEM_LIBRARY})

# Provide Freetype::Freetype as the standard cmake namespace alias for
# upstream consumers that reference it directly. See
# FindZLIB-system.cmake's alias block for the rationale.
if (NOT TARGET Freetype::Freetype)
    add_library(Freetype::Freetype ALIAS ${TARGET_WITH_NAMESPACE})
endif()

set(Freetype_FOUND TRUE)
set(FREETYPE_FOUND TRUE)
