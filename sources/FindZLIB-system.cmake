#
# FindZLIB.cmake — system-zlib shim for o3de-rpm Stage 1.
#
# Drops into cmake/3rdParty/ during %prep when --with system_zlib is on.
# Shadows cmake's stock FindZLIB.cmake (because cmake/3rdParty/ is searched
# first via CMAKE_MODULE_PATH) and produces a 3rdParty::ZLIB target with the
# shape O3DE consumers expect: a real INTERFACE IMPORTED target (not an alias),
# linked through to the system library by file path (not by aliasing
# ZLIB::ZLIB). This avoids two failure modes hit by an earlier alias-based
# attempt:
#   - cmake/3rdParty/BuiltInPackages.cmake creates `3rdParty::zlib` as an
#     ALIAS of `3rdParty::ZLIB`. Aliasing an alias is a hard cmake error.
#   - O3DE's runtime-dependency walker requires per-config IMPORTED_LOCATION_*
#     properties; cmake's stock UNKNOWN IMPORTED `ZLIB::ZLIB` only sets the
#     unconfigured IMPORTED_LOCATION, which trips the walker.
#
# Same pattern as Findmikkelsen-system.cmake. Future Stage 1 swap shims
# follow this template.

if (TARGET 3rdParty::ZLIB)
    set(ZLIB_FOUND TRUE)
    return()
endif()

# Run cmake's stock FindZLIB inline to do the actual library/header lookup.
# `include()` instead of `find_package()` so we don't recurse into ourselves
# (we ARE FindZLIB.cmake on the search path).
include(${CMAKE_ROOT}/Modules/FindZLIB.cmake)
if (NOT ZLIB_FOUND)
    message(FATAL_ERROR "FindZLIB-system shim: cmake stock FindZLIB.cmake did not locate zlib (system zlib-devel installed?)")
endif()

add_library(3rdParty::ZLIB INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::ZLIB INTERFACE ${ZLIB_INCLUDE_DIRS})
# Use the library path (string) — not the cmake-stock target ZLIB::ZLIB —
# so the runtime walker treats it as a file dependency rather than walking
# into ZLIB::ZLIB and complaining about its missing IMPORTED_LOCATION_*.
target_link_libraries(3rdParty::ZLIB INTERFACE ${ZLIB_LIBRARIES})

set(ZLIB_FOUND TRUE)
