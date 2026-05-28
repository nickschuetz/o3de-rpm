#
# Findcityhash.cmake -- system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME cityhash-1.1-multiplatform ...)
# entry that fetches a pre-compiled cityhash bundle from packages.o3de.org,
# by locating the system-installed cityhash library (provided by the
# `o3de2605-cityhash` package from `hellaenergy/o3de-dependencies` COPR)
# and creating the `3rdParty::cityhash` INTERFACE target that O3DE
# consumers expect (only AzCore at present, via
# Code/Framework/AzCore/AzCore/Utils/TypeHash.cpp).
#
# cityhash is not in Fedora's main repository, so this swap routes
# through our license-clean COPR rebuild rather than a Fedora package.
# The rebuild ships `/usr/include/city.h` + `/usr/lib64/libcityhash.so`
# (main package) and `/usr/lib64/libcityhash.a` (devel subpackage).
#
# Layout differences this stub bridges:
#
#   |              | O3DE bundle on packages.o3de.org             | o3de2605-cityhash on COPR |
#   |--------------|-----------------------------------------------|---------------------------|
#   | header path  | <bundle>/cityhash/src/city.h                  | /usr/include/city.h       |
#   | linkage      | <bundle>/cityhash/build/linux/.../libcityhash.a (static) | /usr/lib64/libcityhash.so (shared) |
#
# Engine code does `#include <city.h>` -- no subdir bridge needed since
# /usr/include is naturally on the include path. The bundled package
# linked a static archive; we link the shared library instead (same C++
# ABI for the CityHash64 family used by AzCore).
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/ during
# %prep, and pass -DLY_USE_SYSTEM_CITYHASH=ON to cmake so the gating in
# BuiltInPackages_linux_x86_64.cmake (Patch0006) skips the upstream fetcher.

set(TARGET_WITH_NAMESPACE "3rdParty::cityhash")
if (TARGET ${TARGET_WITH_NAMESPACE})
    return()
endif()

find_path(CITYHASH_SYSTEM_INCLUDE_DIR
    NAMES city.h
    PATHS /usr/include /usr/local/include
)

find_library(CITYHASH_SYSTEM_LIBRARY
    NAMES cityhash
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT CITYHASH_SYSTEM_INCLUDE_DIR OR NOT CITYHASH_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findcityhash (system stub): could not locate city.h "
        "(${CITYHASH_SYSTEM_INCLUDE_DIR}) and/or libcityhash "
        "(${CITYHASH_SYSTEM_LIBRARY}). Install o3de2605-cityhash-devel "
        "from hellaenergy/o3de-dependencies on COPR, or set "
        "LY_USE_SYSTEM_CITYHASH=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE
        ${CITYHASH_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${CITYHASH_SYSTEM_LIBRARY})

set(cityhash_FOUND TRUE)
