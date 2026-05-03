#
# FindFreetype.cmake — system-freetype shim for o3de-rpm Stage 1.
# See FindZLIB-system.cmake for the pattern + rationale.

if (TARGET 3rdParty::Freetype)
    set(Freetype_FOUND TRUE)
    set(FREETYPE_FOUND TRUE)
    return()
endif()

include(${CMAKE_ROOT}/Modules/FindFreetype.cmake)
if (NOT FREETYPE_FOUND)
    message(FATAL_ERROR "FindFreetype-system shim: cmake stock FindFreetype.cmake did not locate freetype (system freetype-devel installed?)")
endif()

add_library(3rdParty::Freetype INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::Freetype INTERFACE ${FREETYPE_INCLUDE_DIRS})
target_link_libraries(3rdParty::Freetype INTERFACE ${FREETYPE_LIBRARIES})

set(Freetype_FOUND TRUE)
set(FREETYPE_FOUND TRUE)
