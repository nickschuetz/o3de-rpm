#
# Findxxhash.cmake -- system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME xxhash-0.7.4-rev1-multiplatform ...)
# entry that fetches xxhash headers from packages.o3de.org, by locating
# the system-installed xxhash header (provided by Fedora's `xxhash-devel`
# RPM) and creating the `3rdParty::xxhash` INTERFACE target that O3DE
# consumers expect (AssetProcessor + AssetBuilderSDK).
#
# Build-time-only swap. The bundled xxhash package on packages.o3de.org
# is also header-only (its Findxxhash.cmake creates an INTERFACE IMPORTED
# target with just an include dir, no library link), so the engine uses
# xxhash via its static-inline functions and does not link libxxhash.so.
# We mirror that: include path only, no library link.
#
# Layout differences this stub bridges:
#
#   |              | O3DE bundle on packages.o3de.org           | Fedora xxhash-devel               |
#   |--------------|---------------------------------------------|------------------------------------|
#   | header path  | <bundle>/xxhash/include/xxhash/xxhash.h     | /usr/include/xxhash.h              |
#
# Engine code does `#include <xxhash/xxhash.h>`. We bridge the include-path
# mismatch by generating a one-line wrapper header at
#   ${CMAKE_BINARY_DIR}/_system_xxhash/xxhash/xxhash.h
# that just `#include <xxhash.h>` (the system flat-path form).
#
# Version note: engine pins 0.7.4; Fedora ships 0.8.3. The xxhash 64-bit
# and 128-bit hash functions used by AssetProcessor / AssetBuilderSDK
# (XXH64, XXH3_64bits, XXH3_128bits) have stable C ABI from 0.7 forward.
# The 0.7 to 0.8 transition added new functions and improved performance
# without breaking the existing API.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/ during
# %prep, and pass -DLY_USE_SYSTEM_XXHASH=ON to cmake so the gating in
# BuiltInPackages_linux_x86_64.cmake (Patch0006) skips the upstream fetcher.

set(TARGET_WITH_NAMESPACE "3rdParty::xxhash")
if (TARGET ${TARGET_WITH_NAMESPACE})
    return()
endif()

find_path(XXHASH_SYSTEM_INCLUDE_DIR
    NAMES xxhash.h
    PATHS /usr/include /usr/local/include
)

if (NOT XXHASH_SYSTEM_INCLUDE_DIR)
    message(FATAL_ERROR
        "Findxxhash (system stub): could not locate xxhash.h on a system "
        "include path. Install xxhash-devel from Fedora, or set "
        "LY_USE_SYSTEM_XXHASH=OFF to fall back to the upstream fetcher.")
endif()

# Bridge the <xxhash/xxhash.h> include syntax to the system-installed
# flat-path <xxhash.h> header by emitting a tiny wrapper header in the
# build dir.
set(_o3de_xxhash_wrapper_dir ${CMAKE_BINARY_DIR}/_system_xxhash)
file(MAKE_DIRECTORY ${_o3de_xxhash_wrapper_dir}/xxhash)
file(WRITE ${_o3de_xxhash_wrapper_dir}/xxhash/xxhash.h
"// o3de-rpm Stage 1 system-xxhash wrapper (Findxxhash-system.cmake).\n\
// Bridges <xxhash/xxhash.h> consumer syntax to the system-installed\n\
// flat-path <xxhash.h> header from Fedora's xxhash-devel.\n\
#pragma once\n\
#include <xxhash.h>\n")

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE
        ${_o3de_xxhash_wrapper_dir}
        ${XXHASH_SYSTEM_INCLUDE_DIR})

set(xxhash_FOUND TRUE)
