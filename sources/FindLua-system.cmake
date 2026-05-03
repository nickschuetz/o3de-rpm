#
# FindLua.cmake — system-lua shim for o3de-rpm Stage 1.
# See FindZLIB-system.cmake for the base pattern + rationale.
#
# Lua needs additional include-path bridging on top of the standard
# shim shape. O3DE consumers `#include <Lua/lauxlib.h>` (Lua/ prefix,
# matching the bundled Lua-5.4.4-rev1-linux package's `Lua/include/Lua/`
# layout). Fedora's lua-devel ships headers flat at /usr/include/lua.h,
# /usr/include/lauxlib.h, etc. — no Lua/ subdir.
#
# Same trick as Findmikkelsen-system.cmake: generate a tiny wrapper-
# header tree at ${CMAKE_BINARY_DIR}/_system_lua/Lua/<header>.h that
# `#include <header.h>` to pick up the system version. Add the wrapper
# directory to the target's include path so `#include <Lua/lauxlib.h>`
# resolves to the wrapper, which then resolves to the system header.

if (TARGET 3rdParty::Lua)
    set(Lua_FOUND TRUE)
    set(LUA_FOUND TRUE)
    return()
endif()

include(${CMAKE_ROOT}/Modules/FindLua.cmake)
if (NOT Lua_FOUND)
    message(FATAL_ERROR "FindLua-system shim: cmake stock FindLua.cmake did not locate Lua (system lua-devel installed?)")
endif()

# Bridge the <Lua/foo.h> consumer-include path to Fedora's flat
# /usr/include/foo.h layout via a generated wrapper-header tree.
set(_o3de_lua_wrapper_dir ${CMAKE_BINARY_DIR}/_system_lua)
file(MAKE_DIRECTORY ${_o3de_lua_wrapper_dir}/Lua)
foreach(_h lua.h lauxlib.h lualib.h luaconf.h)
    file(WRITE ${_o3de_lua_wrapper_dir}/Lua/${_h}
"// o3de-rpm Stage 1 system-lua wrapper (FindLua-system.cmake).\n\
// Bridges <Lua/${_h}> consumer syntax to the system-installed\n\
// <${_h}> header.\n\
#pragma once\n\
#include <${_h}>\n")
endforeach()

add_library(3rdParty::Lua INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::Lua
    INTERFACE
        ${_o3de_lua_wrapper_dir}
        ${LUA_INCLUDE_DIR})
target_link_libraries(3rdParty::Lua INTERFACE ${LUA_LIBRARIES})

set(Lua_FOUND TRUE)
set(LUA_FOUND TRUE)
