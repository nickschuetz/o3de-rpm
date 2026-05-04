#
# FindPNG.cmake — system-libpng shim for o3de-rpm Stage 1.
#
# Refactored 2026-05-04 to the mikkelsen pattern (direct find_path +
# find_library, no `include(${CMAKE_ROOT}/Modules/FindPNG.cmake)`). The
# stock include's side-effect creation of `PNG::PNG` with MAP_IMPORTED_
# CONFIG_* but no per-config IMPORTED_LOCATION fails O3DE's runtime
# walker. Same problem and same fix as FindZLIB-system.cmake — see
# that file's comment block for the full diagnosis.
#
# Library name on Fedora: `libpng16.so.16` (version-suffixed).
# `find_library NAMES png16 png` searches both for compatibility with
# distros that symlink libpng.so generically.

set(TARGET_WITH_NAMESPACE "3rdParty::PNG")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(PNG_FOUND TRUE)
    return()
endif()

find_path(PNG_SYSTEM_INCLUDE_DIR
    NAMES png.h
    PATHS /usr/include /usr/local/include
)

find_library(PNG_SYSTEM_LIBRARY
    NAMES png16 png
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT PNG_SYSTEM_INCLUDE_DIR OR NOT PNG_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindPNG (system stub): could not locate png.h "
        "(${PNG_SYSTEM_INCLUDE_DIR}) and/or libpng "
        "(${PNG_SYSTEM_LIBRARY}). Install libpng-devel from Fedora, or "
        "set LY_USE_SYSTEM_PNG=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${PNG_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${PNG_SYSTEM_LIBRARY})

# Provide PNG::PNG as the standard cmake namespace alias for upstream
# consumers that reference it directly. See FindZLIB-system.cmake's
# alias block for the rationale.
if (NOT TARGET PNG::PNG)
    add_library(PNG::PNG ALIAS ${TARGET_WITH_NAMESPACE})
endif()

set(PNG_FOUND TRUE)
