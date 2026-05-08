#
# Findassimp.cmake — system-package shim for o3de-rpm's Stage 1 migration.
#
# Drops into cmake/3rdParty/ during %prep when --with system_assimp is on.
# `find_package(assimp REQUIRED)` resolves to this file because cmake/3rdParty/
# is on CMAKE_MODULE_PATH ahead of cmake's stock module path.
#
# Creates `3rdParty::assimp` directly (matching `ly_associate_package(...
# TARGETS assimp ...)`'s target name in the bundled-assimp case). Engine
# consumers in Code/Tools/SceneAPI/{SceneBuilder/Importers,SDKWrapper}/
# link `3rdParty::assimp`.
#
# Audit: 2026-05-07 (`/tmp/o3de-assimp-audit/INVESTIGATION_NOTES.md`).
# - Engine consumes assimp exclusively in Code/Tools/SceneAPI/ (asset-pipeline
#   tool); zero refs in Gems/ and zero in core Code/Framework/.
# - Engine include style: `<assimp/Importer.hpp>` / `<assimp/material.h>` /
#   `<assimp/matrix4x4.h>` / `<assimp/mesh.h>` / `<assimp/postprocess.h>` /
#   `<assimp/scene.h>`. All paths resolve in Fedora's `/usr/include/assimp/`
#   layout exactly — no path-bridging needed.
# - All 27 unique types + 7 processing flags engine consumes are public
#   `ai*` C-API and `Assimp::Importer` C++ class; 100% present in Fedora
#   6.0.4 headers (verified via `dnf download` + `rpm2cpio` extraction).
# - FBX importer compiled into Fedora's libassimp.so.6.0.4 (verified via
#   importer-descriptor strings).
#
# Why we don't `find_package(assimp CONFIG REQUIRED)` and alias:
# Fedora's `assimpConfig.cmake` creates `assimp::assimp` as a side-effect
# IMPORTED target. O3DE's runtime walker (cmake/Platform/Common/
# RuntimeDependencies_common.cmake) iterates every target in the project,
# hits side-effect targets that don't have a fully-populated
# IMPORTED_LOCATION, and bails. Doing the find_path / find_library lookup
# directly here means the only assimp-related target in the project is
# the one we want (`3rdParty::assimp`) — same pattern as the FindZLIB,
# FindSQLite, Findmikkelsen, etc. shims.
#
# Caveat (audit): 5.4.3 → 6.0.4 is a major version bump. Symbol-presence
# verified ✓; link-time API will validate at build; runtime FBX-import
# behavior on tricky inputs (subdivision surfaces, layered animations,
# embedded textures) is **unverified**. Mitigation: pair activation with
# a Tier 6 integration test that bakes a known FBX from AutomatedTesting
# Gem assets (FOLLOW_UPS.md item).
#
# Same shape as Findmikkelsen-system.cmake / FindZLIB-system.cmake /
# FindSQLite-system.cmake / etc.

set(TARGET_WITH_NAMESPACE "3rdParty::assimp")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(assimp_FOUND TRUE)
    return()
endif()

find_path(ASSIMP_SYSTEM_INCLUDE_DIR
    NAMES assimp/Importer.hpp
    PATHS /usr/include /usr/local/include
)

find_library(ASSIMP_SYSTEM_LIBRARY
    NAMES assimp
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT ASSIMP_SYSTEM_INCLUDE_DIR OR NOT ASSIMP_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findassimp (system stub): could not locate assimp/Importer.hpp "
        "(${ASSIMP_SYSTEM_INCLUDE_DIR}) and/or libassimp "
        "(${ASSIMP_SYSTEM_LIBRARY}). Install assimp-devel from Fedora, "
        "or set LY_USE_SYSTEM_ASSIMP=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${ASSIMP_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${ASSIMP_SYSTEM_LIBRARY})

set(assimp_FOUND TRUE)
