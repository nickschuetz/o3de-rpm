#
# FindPNG.cmake — system-libpng shim for o3de-rpm Stage 1.
# See FindZLIB-system.cmake for the pattern + rationale.

if (TARGET 3rdParty::PNG)
    set(PNG_FOUND TRUE)
    return()
endif()

include(${CMAKE_ROOT}/Modules/FindPNG.cmake)
if (NOT PNG_FOUND)
    message(FATAL_ERROR "FindPNG-system shim: cmake stock FindPNG.cmake did not locate libpng (system libpng-devel installed?)")
endif()

add_library(3rdParty::PNG INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::PNG INTERFACE ${PNG_INCLUDE_DIRS})
target_link_libraries(3rdParty::PNG INTERFACE ${PNG_LIBRARIES})

set(PNG_FOUND TRUE)
