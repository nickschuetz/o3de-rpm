#
# Findexpat.cmake — case-bridging system-expat shim for o3de-rpm Stage 1.
#
# Two roles:
#  1. Case bridge: bundled FindOpenColorIO.cmake calls find_package(expat)
#     lowercase, but cmake's stock module is uppercase FindEXPAT.cmake. On
#     Linux's case-sensitive filesystem those don't match. Naming this
#     shim Findexpat.cmake (lowercase) satisfies the lowercase consumer
#     call.
#  2. Target shape: produces 3rdParty::expat as a real INTERFACE IMPORTED
#     target (not an alias), linked through to the system library by file
#     path. Avoids the alias-of-alias error that engine-side code at
#     cmake/3rdParty/BuiltInPackages.cmake:35 triggers when 3rdParty::<X>
#     is itself an alias. Avoids the per-config IMPORTED_LOCATION_*
#     requirement that O3DE's runtime walker imposes on imported targets
#     when they're not INTERFACE.
#
# Same pattern as FindZLIB-system.cmake et al.

if (TARGET 3rdParty::expat)
    set(expat_FOUND TRUE)
    set(EXPAT_FOUND TRUE)
    return()
endif()

# Run cmake's stock FindEXPAT inline — uppercase filename, so include()
# rather than find_package() to avoid recursion concerns and to ensure
# we get exactly the stock module.
include(${CMAKE_ROOT}/Modules/FindEXPAT.cmake)
if (NOT EXPAT_FOUND)
    message(FATAL_ERROR "Findexpat-system shim: cmake stock FindEXPAT.cmake did not locate expat (system expat-devel installed?)")
endif()

add_library(3rdParty::expat INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET 3rdParty::expat INTERFACE ${EXPAT_INCLUDE_DIRS})
target_link_libraries(3rdParty::expat INTERFACE ${EXPAT_LIBRARIES})

# Bridge uppercase output variables to lowercase consumers (the bundled
# FindOpenColorIO.cmake reads `expat_FOUND` etc. for compat with the
# pre-existing dual-case convention the bundled Findexpat.cmake set up).
set(expat_FOUND ${EXPAT_FOUND})
set(expat_VERSION ${EXPAT_VERSION_STRING})
set(expat_INCLUDE_DIR ${EXPAT_INCLUDE_DIR})
set(expat_INCLUDE_DIRS ${EXPAT_INCLUDE_DIRS})
set(expat_LIBRARY ${EXPAT_LIBRARY})
set(expat_LIBRARIES ${EXPAT_LIBRARIES})
