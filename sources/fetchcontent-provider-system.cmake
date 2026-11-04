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
# On 2026-10-29/30 zlib (#20167), lua (#20162), png (#20168), freetype
# (#20169), lz4 (#20163), mcpp (#20160) and libsamplerate (#20166) moved
# there as well, and on 2026-11-02 expat (#20170).
# Our cmake/3rdParty/Find<Name>.cmake shims are therefore never reached there
# and the swap would silently build the bundled copy. When the matching
# system_<name> bcond is on, the spec copies this file over
# Code/3rdParty/<name>/CMakeLists.txt (only if that file exists:
# stabilization/26100 predates these changes). It defines the provider's
# targets from the Fedora package through the existing Find shim, which is
# installed with the engine's cmake/ directory, so project builds against the
# installed SDK resolve the same way. The resolver loads a provider directory
# once and then requires every requested name to exist, so each branch defines
# all the namespaced names the upstream recipe does.

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
elseif (o3de_rpm_provider STREQUAL "zlib")
    # Defines 3rdParty::ZLIB and ZLIB::ZLIB.
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/FindZLIB.cmake")
    if (NOT TARGET 3rdParty::zlib)
        add_library(3rdParty::zlib ALIAS 3rdParty::ZLIB)
    endif()
elseif (o3de_rpm_provider STREQUAL "lua")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/FindLua.cmake")
    if (NOT TARGET 3rdParty::lua)
        add_library(3rdParty::lua ALIAS 3rdParty::Lua)
    endif()
elseif (o3de_rpm_provider STREQUAL "png")
    # Defines 3rdParty::PNG and PNG::PNG.
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/FindPNG.cmake")
    if (NOT TARGET 3rdParty::png)
        add_library(3rdParty::png ALIAS 3rdParty::PNG)
    endif()
elseif (o3de_rpm_provider STREQUAL "freetype")
    # Defines 3rdParty::Freetype and Freetype::Freetype.
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/FindFreetype.cmake")
elseif (o3de_rpm_provider STREQUAL "lz4")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findlz4.cmake")
elseif (o3de_rpm_provider STREQUAL "mcpp")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findmcpp.cmake")
elseif (o3de_rpm_provider STREQUAL "libsamplerate")
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findlibsamplerate.cmake")
elseif (o3de_rpm_provider STREQUAL "expat")
    # Defines 3rdParty::expat and EXPAT::EXPAT; the upstream recipe also
    # defines expat::expat.
    include("${LY_ROOT_FOLDER}/cmake/3rdParty/Findexpat.cmake")
    if (NOT TARGET expat::expat)
        add_library(expat::expat ALIAS 3rdParty::expat)
    endif()
else()
    message(FATAL_ERROR "fetchcontent-provider-system.cmake: no system mapping for Code/3rdParty/${o3de_rpm_provider}")
endif()
