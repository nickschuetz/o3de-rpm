#
# Copyright (c) Contributors to the Open 3D Engine Project.
# For complete copyright and license terms please see the LICENSE at the root of this distribution.
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
#
# o3de-rpm system-swap shim for the in-tree 3rdParty providers on development.
#
# On development, rapidjson (o3de/o3de#20079), xxhash (#20068), cityhash
# (#20076) and mikktspace (#20078) are built from Code/3rdParty/<name>
# instead of the prebuilt packages, and since #20097 (2026-09-25) a 3rdParty::<Name> reference is
# resolved from that provider directory before any Find module is consulted.
# Our cmake/3rdParty/Find<Name>.cmake shims are therefore never reached there
# and the swap would silently build the bundled copy. When the matching
# system_<name> bcond is on, the spec copies this file over
# Code/3rdParty/<name>/CMakeLists.txt (only if that file exists:
# stabilization/26100 predates these changes). It defines the provider's
# targets from the Fedora package through the existing Find shim, which is
# installed with the engine's cmake/ directory, so project builds against the
# installed SDK resolve the same way.

get_filename_component(o3de_rpm_provider "${CMAKE_CURRENT_LIST_DIR}" NAME)

if (o3de_rpm_provider STREQUAL "rapidjson")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/FindRapidJSON.cmake")
    if (NOT TARGET 3rdParty::rapidjson)
        add_library(3rdParty::rapidjson ALIAS 3rdParty::RapidJSON)
    endif()
elseif (o3de_rpm_provider STREQUAL "xxhash")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findxxhash.cmake")
elseif (o3de_rpm_provider STREQUAL "cityhash")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findcityhash.cmake")
elseif (o3de_rpm_provider STREQUAL "mikktspace")
    # system_mikkelsen: same MikkTSpace commit (3e895b4) as the in-tree fetch.
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findmikkelsen.cmake")
    if (NOT TARGET 3rdParty::mikktspace)
        add_library(3rdParty::mikktspace ALIAS 3rdParty::mikkelsen)
    endif()
else()
    message(FATAL_ERROR "fetchcontent-provider-system.cmake: no system mapping for Code/3rdParty/${o3de_rpm_provider}")
endif()
