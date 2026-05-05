#
# Findlz4.cmake — system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME lz4-1.9.4-rev2-linux ...)
# entry that fetches lz4 from packages.o3de.org. The system Fedora
# layout matches what the engine's consumers expect verbatim:
#
#   |              | O3DE bundle on packages.o3de.org   | Fedora lz4-devel    |
#   |--------------|------------------------------------|---------------------|
#   | header path  | <bundle>/include/lz4.h             | /usr/include/lz4.h  |
#   |              | <bundle>/include/lz4hc.h           | /usr/include/lz4hc.h |
#   |              | <bundle>/include/lz4frame.h        | /usr/include/lz4frame.h |
#   | library      | <bundle>/lib/{debug,release}/lz4   | /usr/lib64/liblz4.so |
#
# Engine consumers use `#include <lz4.h>` / `<lz4hc.h>` / `<lz4frame.h>`
# verbatim (Gems/MultiplayerCompression and Code/Framework/AzFramework
# Archive code), so no wrapper header is needed.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/ during
# %prep, and pass -DLY_USE_SYSTEM_LZ4=ON to cmake so the gating in
# BuiltInPackages_linux_x86_64.cmake (Patch0006) skips the upstream fetcher.
#
# Pattern: same direct-find-no-stock-include shape as the four ZLIB-class
# refactors (commits 92bde6e / cba5059 / 6b14ffa / 0ca58e8). cmake doesn't
# ship a stock FindLZ4.cmake module so there's no side-effect target to
# avoid creating; the find_path/find_library are direct lookups.

set(TARGET_WITH_NAMESPACE "3rdParty::lz4")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(lz4_FOUND TRUE)
    return()
endif()

find_path(LZ4_SYSTEM_INCLUDE_DIR
    NAMES lz4.h
    PATHS /usr/include /usr/local/include
)

find_library(LZ4_SYSTEM_LIBRARY
    NAMES lz4
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT LZ4_SYSTEM_INCLUDE_DIR OR NOT LZ4_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findlz4 (system stub): could not locate lz4.h "
        "(${LZ4_SYSTEM_INCLUDE_DIR}) and/or liblz4 "
        "(${LZ4_SYSTEM_LIBRARY}). Install lz4-devel from Fedora, or set "
        "LY_USE_SYSTEM_LZ4=OFF to fall back to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${LZ4_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${LZ4_SYSTEM_LIBRARY})

set(lz4_FOUND TRUE)
