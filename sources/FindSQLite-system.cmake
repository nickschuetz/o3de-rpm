#
# FindSQLite.cmake — system-package shim for o3de-rpm's Stage 1 migration.
#
# Drops into cmake/3rdParty/ during %prep when --with system_sqlite is on.
# `find_package(SQLite REQUIRED)` resolves to this file because cmake/3rdParty/
# is added to CMAKE_MODULE_PATH ahead of cmake's stock FindSQLite3.cmake.
#
# Creates `3rdParty::SQLite` directly (matching `ly_associate_package(...
# TARGETS SQLite ...)`'s target name in the bundled-SQLite case). Engine
# consumers in Code/Framework/AzToolsFramework/SQLite/ +
# Code/Tools/AssetProcessor/AssetDatabase/ link `3rdParty::SQLite`.
#
# Why we don't `include(${CMAKE_ROOT}/Modules/FindSQLite3.cmake)` and alias:
# the stock module creates `SQLite::SQLite3` as a side-effect IMPORTED target.
# O3DE's runtime walker (cmake/Platform/Common/RuntimeDependencies_common.cmake)
# iterates every target in the project, hits side-effect targets that don't
# have a fully-populated IMPORTED_LOCATION, and bails. Doing the find_path /
# find_library lookup directly here means the only SQLite-related target in
# the project is the one we want (`3rdParty::SQLite`).
#
# Audit: 2026-05-07 (`/tmp/o3de-assimp-audit/SQLITE_INVESTIGATION_NOTES.md`).
# 100% of the 29 unique sqlite3_* symbols engine consumes are present in
# Fedora 3.51.2 headers; 3.37 → 3.51 is point-version increment within
# SQLite's 21-year ABI-stable major (since 3.0.0, 2004); zero extension-only
# API used (no FTS5/RTREE/JSON1/SEE) so Fedora's standard sqlite-libs is
# sufficient.
#
# Same shape as Findmikkelsen-system.cmake / FindZLIB-system.cmake / etc.

set(TARGET_WITH_NAMESPACE "3rdParty::SQLite")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(SQLite_FOUND TRUE)
    return()
endif()

find_path(SQLITE_SYSTEM_INCLUDE_DIR
    NAMES sqlite3.h
    PATHS /usr/include /usr/local/include
)

find_library(SQLITE_SYSTEM_LIBRARY
    NAMES sqlite3
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT SQLITE_SYSTEM_INCLUDE_DIR OR NOT SQLITE_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindSQLite (system stub): could not locate sqlite3.h "
        "(${SQLITE_SYSTEM_INCLUDE_DIR}) and/or libsqlite3 "
        "(${SQLITE_SYSTEM_LIBRARY}). Install sqlite-devel from Fedora, "
        "or set LY_USE_SYSTEM_SQLITE=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${SQLITE_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${SQLITE_SYSTEM_LIBRARY})

set(SQLite_FOUND TRUE)
