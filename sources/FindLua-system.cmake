#
# FindLua.cmake — system-lua shim for o3de-rpm Stage 1.
# See FindZLIB-system.cmake for the pattern + rationale.
#
# Note on Lua specifically: cmake's stock FindLua.cmake uses the
# *singular* `LUA_INCLUDE_DIR` (no S), unlike most other find modules
# that produce plural `*_INCLUDE_DIRS`. We pass it through as-is.
# Lua_FOUND (mixed case) is the pass signal cmake uses when the
# package name in find_package() is "Lua".

if (TARGET 3rdParty::Lua)
    set(Lua_FOUND TRUE)
    set(LUA_FOUND TRUE)
    return()
endif()

include(${CMAKE_ROOT}/Modules/FindLua.cmake)
if (NOT Lua_FOUND)
    message(FATAL_ERROR "FindLua-system shim: cmake stock FindLua.cmake did not locate Lua (system lua-devel installed?)")
endif()

add_library(3rdParty::Lua INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::Lua INTERFACE ${LUA_INCLUDE_DIR})
target_link_libraries(3rdParty::Lua INTERFACE ${LUA_LIBRARIES})

set(Lua_FOUND TRUE)
set(LUA_FOUND TRUE)
