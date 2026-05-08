#
# Findmcpp.cmake -- system-package shim for o3de-rpm's Stage 2 migration.
#
# Drops into cmake/3rdParty/ during %prep when --with system_mcpp is on.
# `find_package(mcpp REQUIRED)` resolves to this file because cmake/3rdParty/
# is on CMAKE_MODULE_PATH ahead of cmake's stock module path.
#
# Creates `3rdParty::mcpp` directly (matching `ly_associate_package(...
# TARGETS mcpp ...)`'s target name in the bundled mcpp-2.7.2_az.2-rev1-linux
# case). Engine consumers in
# Gems/Atom/Asset/Shader/Code/Source/Editor/CommonFiles/Preprocessor.cpp
# call `mcpp_lib_main()`, `mcpp_set_out_func()`,
# `mcpp_set_report_include_callback()` against the linked-in library.
#
# Source: hellaenergy/o3de-dependencies COPR `o3de-mcpp-az-devel`
# (license-clean rebuild of upstream mcpp 2.7.2 + o3de/3p-package-source's
# `_az.2` 566-line patch series; ✓ green PoC build 10436752 since
# 2026-05-08, both F44 + rawhide). Ships:
#   /usr/lib64/libmcpp.so      (devel symlink to libmcpp.so.0.3.0)
#   /usr/lib64/libmcpp.a       (static archive, also available)
#   /usr/include/mcpp_lib.h    (public header)
#   /usr/include/mcpp_out.h    (public header)
#
# Why we don't use cmake's stock find module: there is no stock `Findmcpp`
# (mcpp is abandonware-class with no upstream cmake support). Same shape
# as Findmikkelsen-system.cmake / Findlz4-system.cmake -- direct
# find_path / find_library lookup.
#
# Library-link variant of the DXC-class Stage 2 swap pattern. Unlike
# system_spirvcross / system_dxc which use install-time symlink overlays
# (the engine shells out to those binaries at runtime), mcpp is linked
# into the engine binary at build time -- so the install-overlay
# approach does not apply. We need a real Find shim + Patch0006 gate
# to skip the bundled fetch and link against the system library at
# configure time.

set(TARGET_WITH_NAMESPACE "3rdParty::mcpp")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(mcpp_FOUND TRUE)
    return()
endif()

find_path(MCPP_SYSTEM_INCLUDE_DIR
    NAMES mcpp_lib.h
    PATHS /usr/include /usr/local/include
)

find_library(MCPP_SYSTEM_LIBRARY
    NAMES mcpp
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT MCPP_SYSTEM_INCLUDE_DIR OR NOT MCPP_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findmcpp (system stub): could not locate mcpp_lib.h "
        "(${MCPP_SYSTEM_INCLUDE_DIR}) and/or libmcpp "
        "(${MCPP_SYSTEM_LIBRARY}). Install o3de-mcpp-az-devel from the "
        "hellaenergy/o3de-dependencies COPR project, or set "
        "LY_USE_SYSTEM_MCPP=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${MCPP_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${MCPP_SYSTEM_LIBRARY})

set(mcpp_FOUND TRUE)
