#
# FindTIFF.cmake — system-libtiff shim for o3de-rpm Stage 1.
#
# Drops into cmake/3rdParty/ during %prep when --with system_tiff is on.
# Shadows cmake's stock FindTIFF.cmake (because cmake/3rdParty/ is searched
# first via CMAKE_MODULE_PATH) and produces a 3rdParty::TIFF target with the
# shape O3DE consumers expect: a real INTERFACE IMPORTED target (not an
# alias), linked through to the system library by file path.
#
# Refactored 2026-05-05 to follow Findmikkelsen-system.cmake's pattern
# (direct find_path + find_library, no `include(${CMAKE_ROOT}/Modules/...)`).
# Same load-bearing reason as the four ZLIB-class shim refactors
# (commits 92bde6e / cba5059 / 6b14ffa / 0ca58e8): cmake's stock
# FindTIFF.cmake creates `TIFF::TIFF` as `UNKNOWN IMPORTED` with
# `MAP_IMPORTED_CONFIG_*` set but only an unconfigured `IMPORTED_LOCATION`,
# which O3DE's runtime walker
# (cmake/Platform/Common/RuntimeDependencies_common.cmake) bails on:
#   "UNKNOWN_LIBRARY Library TIFF::TIFF specified MAP_IMPORTED_CONFIG_DEBUG
#    = DEBUG; but did not have any of IMPORTED_LOCATION_xxxx set"
# Doing the find_path/find_library lookup directly here means
# `TIFF::TIFF` never exists in the project as a side-effect target —
# only `3rdParty::TIFF`.
#
# Pairs with Patch0008 (sources/0008-system-libtiff-compat.patch) which
# gates CryCommon's int64/uint64 typedefs behind O3DE_SYSTEM_LIBTIFF_COMPAT
# so libtiff's <tiff.h> typedefs can win in the two TIFF-using TUs.

set(TARGET_WITH_NAMESPACE "3rdParty::TIFF")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(TIFF_FOUND TRUE)
    return()
endif()

find_path(TIFF_SYSTEM_INCLUDE_DIR
    NAMES tiffio.h
    PATHS /usr/include /usr/local/include
)

find_library(TIFF_SYSTEM_LIBRARY
    NAMES tiff
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT TIFF_SYSTEM_INCLUDE_DIR OR NOT TIFF_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindTIFF (system stub): could not locate tiffio.h "
        "(${TIFF_SYSTEM_INCLUDE_DIR}) and/or libtiff "
        "(${TIFF_SYSTEM_LIBRARY}). Install libtiff-devel from Fedora, or set "
        "LY_USE_SYSTEM_TIFF=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${TIFF_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${TIFF_SYSTEM_LIBRARY})

# The bundled FindOpenImageIO.cmake and a handful of upstream consumers
# reference `TIFF::TIFF` — the standard cmake namespace for the stock
# FindTIFF result. We don't `include(${CMAKE_ROOT}/Modules/FindTIFF.cmake)`
# here (that would re-introduce the runtime-walker bailout), so
# `TIFF::TIFF` doesn't exist by default. Provide it as an alias of
# `3rdParty::TIFF` so upstream consumers still resolve. Aliases don't
# carry MAP_IMPORTED_CONFIG_* themselves; the walker sees the aliased
# real target (`3rdParty::TIFF`, INTERFACE IMPORTED with no
# config-mapping properties), so it stays clean.
if (NOT TARGET TIFF::TIFF)
    add_library(TIFF::TIFF ALIAS ${TARGET_WITH_NAMESPACE})
endif()

set(TIFF_FOUND TRUE)
