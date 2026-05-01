#
# Findmikkelsen.cmake — system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME mikkelsen-1.0.0.4-linux ...)
# entry that fetches mikkelsen from packages.o3de.org, by locating the
# system-installed MikkTSpace headers and library (provided by the
# `mikkelsen` and `mikkelsen-devel` RPMs from hellaenergy/o3de-dependencies)
# and creating the `3rdParty::mikkelsen` INTERFACE target O3DE consumers
# (currently only Gems/SceneProcessing) expect.
#
# Layout differences this stub bridges:
#
#   |              | O3DE bundle on packages.o3de.org           | hellaenergy/o3de-dependencies + Fedora |
#   |--------------|---------------------------------------------|-----------------------------------------|
#   | header path  | <bundle>/include/mikkelsen/mikktspace.h     | /usr/include/mikktspace.h               |
#   | library      | <bundle>/lib/{debug,release}/libmikkelsen.a | /usr/lib64/libmikktspace.{so,so.0,a}    |
#
# Consumer code does `#include <mikkelsen/mikktspace.h>` and links the
# `3rdParty::mikkelsen` target. We bridge the include-path mismatch by
# generating a one-line wrapper header at
#   ${CMAKE_BINARY_DIR}/_system_mikkelsen/mikkelsen/mikktspace.h
# that just `#include <mikktspace.h>`. The library mismatch is bridged by
# linking whichever name is found by find_library() (mikkelsen first, then
# mikktspace as the COPR/Fedora form).
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/ during
# %prep, and pass -DLY_USE_SYSTEM_MIKKELSEN=ON to cmake so the gating in
# BuiltInPackages_linux_x86_64.cmake (Patch0006) skips the upstream fetcher.

set(TARGET_WITH_NAMESPACE "3rdParty::mikkelsen")
if (TARGET ${TARGET_WITH_NAMESPACE})
    return()
endif()

find_path(MIKKELSEN_SYSTEM_INCLUDE_DIR
    NAMES mikktspace.h
    PATHS /usr/include /usr/local/include
)

find_library(MIKKELSEN_SYSTEM_LIBRARY
    NAMES mikkelsen mikktspace
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT MIKKELSEN_SYSTEM_INCLUDE_DIR OR NOT MIKKELSEN_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findmikkelsen (system stub): could not locate mikktspace.h "
        "(${MIKKELSEN_SYSTEM_INCLUDE_DIR}) and/or libmikkelsen/libmikktspace "
        "(${MIKKELSEN_SYSTEM_LIBRARY}). Install mikkelsen-devel from "
        "hellaenergy/o3de-dependencies on COPR, or set "
        "LY_USE_SYSTEM_MIKKELSEN=OFF to fall back to the upstream fetcher.")
endif()

# Bridge the <mikkelsen/mikktspace.h> include syntax to the system-installed
# <mikktspace.h> by emitting a tiny wrapper header in the build dir.
set(_o3de_mikkelsen_wrapper_dir ${CMAKE_BINARY_DIR}/_system_mikkelsen)
file(MAKE_DIRECTORY ${_o3de_mikkelsen_wrapper_dir}/mikkelsen)
file(WRITE ${_o3de_mikkelsen_wrapper_dir}/mikkelsen/mikktspace.h
"// o3de-rpm Stage 1 system-mikkelsen wrapper (Findmikkelsen-system.cmake).\n\
// Bridges <mikkelsen/mikktspace.h> consumer syntax to the system-installed\n\
// <mikktspace.h> header.\n\
#pragma once\n\
#include <mikktspace.h>\n")

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE
        ${_o3de_mikkelsen_wrapper_dir}
        ${MIKKELSEN_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${MIKKELSEN_SYSTEM_LIBRARY})

set(mikkelsen_FOUND TRUE)
