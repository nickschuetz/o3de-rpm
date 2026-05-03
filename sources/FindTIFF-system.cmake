#
# FindTIFF.cmake — system-libtiff shim for o3de-rpm Stage 1.
# See FindZLIB-system.cmake for the pattern + rationale.

if (TARGET 3rdParty::TIFF)
    set(TIFF_FOUND TRUE)
    return()
endif()

include(${CMAKE_ROOT}/Modules/FindTIFF.cmake)
if (NOT TIFF_FOUND)
    message(FATAL_ERROR "FindTIFF-system shim: cmake stock FindTIFF.cmake did not locate libtiff (system libtiff-devel installed?)")
endif()

add_library(3rdParty::TIFF INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::TIFF INTERFACE ${TIFF_INCLUDE_DIRS})
target_link_libraries(3rdParty::TIFF INTERFACE ${TIFF_LIBRARIES})

set(TIFF_FOUND TRUE)
