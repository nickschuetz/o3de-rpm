#
# FindRapidJSON.cmake -- system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME RapidJSON-1.1.0-rev1-multiplatform ...)
# entry that fetches RapidJSON headers from packages.o3de.org, by locating
# the system-installed RapidJSON headers (provided by Fedora's `rapidjson-devel`
# RPM) and creating the `3rdParty::RapidJSON` INTERFACE target that O3DE
# consumers expect (AtomCore, AzCore, AzNetworking, AssetProcessor, Prefab,
# and others).
#
# RapidJSON is a header-only library; no .so to link. Build-time-only swap.
#
# No path translation needed: Fedora's rapidjson-devel ships headers at
# /usr/include/rapidjson/<name>.h with the same subdir layout the engine
# consumers expect (#include <rapidjson/document.h> etc.). The find shim
# just locates the rapidjson/ subdir and adds the parent /usr/include to
# the include path.
#
# Version note: engine pins 1.1.0; Fedora ships a post-1.1.0 main-branch
# snapshot from 2024-12-22. RapidJSON has not removed published API in
# that interval; engine consumers continue to work against the newer
# headers.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/ during
# %prep, and pass -DLY_USE_SYSTEM_RAPIDJSON=ON to cmake so the gating in
# BuiltInPackages_linux_x86_64.cmake (Patch0006) skips the upstream fetcher.

set(TARGET_WITH_NAMESPACE "3rdParty::RapidJSON")
if (TARGET ${TARGET_WITH_NAMESPACE})
    return()
endif()

find_path(RAPIDJSON_SYSTEM_INCLUDE_DIR
    NAMES rapidjson/rapidjson.h
    PATHS /usr/include /usr/local/include
)

if (NOT RAPIDJSON_SYSTEM_INCLUDE_DIR)
    message(FATAL_ERROR
        "FindRapidJSON (system stub): could not locate rapidjson/rapidjson.h "
        "on a system include path. Install rapidjson-devel from Fedora, or "
        "set LY_USE_SYSTEM_RAPIDJSON=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE
        ${RAPIDJSON_SYSTEM_INCLUDE_DIR})

set(RapidJSON_FOUND TRUE)
