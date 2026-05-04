#
# FindZLIB.cmake — system-zlib shim for o3de-rpm Stage 1.
#
# Drops into cmake/3rdParty/ during %prep when --with system_zlib is on.
# Shadows cmake's stock FindZLIB.cmake (because cmake/3rdParty/ is searched
# first via CMAKE_MODULE_PATH) and produces a 3rdParty::ZLIB target with the
# shape O3DE consumers expect: a real INTERFACE IMPORTED target (not an
# alias), linked through to the system library by file path.
#
# Refactored 2026-05-04 to follow Findmikkelsen-system.cmake's pattern
# (direct find_path + find_library, no `include(${CMAKE_ROOT}/Modules/...)`).
# An earlier version delegated to cmake's stock FindZLIB.cmake via include();
# that worked for header/library lookup but had a load-bearing side effect:
# the stock module creates `ZLIB::ZLIB` as `UNKNOWN IMPORTED` with
# `MAP_IMPORTED_CONFIG_DEBUG/RELEASE/PROFILE` set but only the unconfigured
# `IMPORTED_LOCATION` populated. O3DE's runtime walker
# (cmake/Platform/Common/RuntimeDependencies_common.cmake) iterates every
# target in the project, hits the side-effect target, and bails with:
#   "UNKNOWN_LIBRARY Library ZLIB::ZLIB specified MAP_IMPORTED_CONFIG_DEBUG
#    = DEBUG; but did not have any of IMPORTED_LOCATION_xxxx set"
# Doing the find_path/find_library lookup directly here means
# `ZLIB::ZLIB` never exists in the project — only `3rdParty::ZLIB`.
#
# Same bridging concerns as the original (re-entry guard,
# ly_target_include_system_directories, link by file path not by target
# alias) preserved. See Findmikkelsen-system.cmake for the original
# template.

set(TARGET_WITH_NAMESPACE "3rdParty::ZLIB")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(ZLIB_FOUND TRUE)
    return()
endif()

find_path(ZLIB_SYSTEM_INCLUDE_DIR
    NAMES zlib.h
    PATHS /usr/include /usr/local/include
)

find_library(ZLIB_SYSTEM_LIBRARY
    NAMES z
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT ZLIB_SYSTEM_INCLUDE_DIR OR NOT ZLIB_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindZLIB (system stub): could not locate zlib.h "
        "(${ZLIB_SYSTEM_INCLUDE_DIR}) and/or libz "
        "(${ZLIB_SYSTEM_LIBRARY}). Install zlib-devel from Fedora, or set "
        "LY_USE_SYSTEM_ZLIB=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${ZLIB_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${ZLIB_SYSTEM_LIBRARY})

# The bundled freetype's FindFreetype.cmake (and a few other 3rdParty
# Find modules) does `target_link_libraries(... INTERFACE ZLIB::ZLIB)`,
# which is the standard cmake namespace for the stock FindZLIB result.
# We don't `include(${CMAKE_ROOT}/Modules/FindZLIB.cmake)` here (that
# include creates a side-effect target with MAP_IMPORTED_CONFIG_* but
# no per-config IMPORTED_LOCATION_* — fails O3DE's runtime walker), so
# `ZLIB::ZLIB` doesn't exist by default. Provide it as an alias of
# `3rdParty::ZLIB` so the upstream consumers still resolve. Aliases
# don't carry MAP_IMPORTED_CONFIG_* themselves; the walker sees the
# aliased real target (`3rdParty::ZLIB`, INTERFACE IMPORTED with no
# config-mapping properties), so it stays clean.
if (NOT TARGET ZLIB::ZLIB)
    add_library(ZLIB::ZLIB ALIAS ${TARGET_WITH_NAMESPACE})
endif()

set(ZLIB_FOUND TRUE)
