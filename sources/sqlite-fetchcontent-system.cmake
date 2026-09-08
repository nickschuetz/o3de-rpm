#
# Copyright (c) Contributors to the Open 3D Engine Project.
# For complete copyright and license terms please see the LICENSE at the root of this distribution.
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
#
# o3de-rpm system-sqlite shim for Code/3rdParty/sqlite/CMakeLists.txt.
#
# Upstream o3de/o3de#20072 (development, 2026-09-05) stopped consuming the
# prebuilt SQLite-3.37.2 3rdParty package and instead builds sqlite 3.53.4
# from the sqlite.org amalgamation via o3de_fetch_content(URL ...), exposing it
# as 3rdParty::sqlite (with a 3rdParty::SQLite alias). That fetch is URL-only
# with no git fallback, so under -DO3DE_FETCHCONTENT_FORCE_GIT=ON (our CentOS
# Stream 10 / CMake 3.31 workaround) configure dies with "All URL downloads
# failed and no GIT was provided as fallback"; and with the system_sqlite swap
# we must not download or build a bundled sqlite at all. The spec copies this
# file over the upstream CMakeLists.txt in %prep when LY_USE_SYSTEM_SQLITE is
# on and the upstream file exists (stabilization/26100 predates #20072).
#
# Defines the same targets upstream does, backed by Fedora's sqlite-devel.

set(TARGET_WITH_NAMESPACE "3rdParty::sqlite")
if (TARGET ${TARGET_WITH_NAMESPACE})
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
        "sqlite (system shim): could not locate sqlite3.h "
        "(${SQLITE_SYSTEM_INCLUDE_DIR}) and/or libsqlite3 "
        "(${SQLITE_SYSTEM_LIBRARY}). Install sqlite-devel from Fedora, "
        "or set LY_USE_SYSTEM_SQLITE=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${SQLITE_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${SQLITE_SYSTEM_LIBRARY})

# Upstream keeps a 3rdParty::SQLite alias for pre-#20072 consumers (external
# gems, projects). Mirror it, unless the prebuilt-path shim
# (cmake/3rdParty/FindSQLite.cmake) already created that name.
if (NOT TARGET 3rdParty::SQLite)
    add_library(3rdParty::SQLite ALIAS ${TARGET_WITH_NAMESPACE})
endif()
