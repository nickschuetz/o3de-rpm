#
# Findlibsamplerate.cmake — system-package shim for o3de-rpm's Stage 1 migration.
#
# Drops into cmake/3rdParty/ during %prep when --with system_libsamplerate is on.
# `find_package(libsamplerate REQUIRED)` resolves to this file because
# cmake/3rdParty/ is on CMAKE_MODULE_PATH ahead of cmake's stock module path.
#
# Creates `3rdParty::libsamplerate` directly (matching `ly_associate_package(...
# TARGETS libsamplerate ...)`'s target name in the bundled-libsamplerate case).
#
# Audit: 2026-05-07 (`/tmp/o3de-assimp-audit/LIBSAMPLERATE_INVESTIGATION_NOTES.md`).
# - Engine consumes libsamplerate exclusively in `Gems/Microphone/`.
# - The Microphone Gem's Linux PAL points to `MicrophoneSystemComponent_None.cpp`
#   (a do-nothing stub) — zero `src_*` function calls in the Linux runtime path.
# - The Gem's CMakeLists.txt:25 unconditionally LINKS 3rdParty::libsamplerate,
#   so this shim still needs to satisfy the cmake link.
# - Engine include is `<samplerate.h>` (top-level, no subdir) — matches Fedora's
#   `/usr/include/samplerate.h` layout exactly. No path-bridging needed.
# - 0.2.1 → 0.2.2 is patch-version increment within libsamplerate's 23-year
#   ABI-stable major (since 0.1.0, 2002).
#
# License: BSD-2-Clause (Erik de Castro Lopo, libsndfile author). Fedora-acceptable.
#
# Same shape as Findmikkelsen-system.cmake / FindZLIB-system.cmake / etc.
# (libsamplerate doesn't ship a stock cmake module — use direct find_path /
# find_library; pkg-config available at /usr/lib64/pkgconfig/samplerate.pc as
# a fallback if needed.)

set(TARGET_WITH_NAMESPACE "3rdParty::libsamplerate")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(libsamplerate_FOUND TRUE)
    return()
endif()

find_path(LIBSAMPLERATE_SYSTEM_INCLUDE_DIR
    NAMES samplerate.h
    PATHS /usr/include /usr/local/include
)

find_library(LIBSAMPLERATE_SYSTEM_LIBRARY
    NAMES samplerate
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT LIBSAMPLERATE_SYSTEM_INCLUDE_DIR OR NOT LIBSAMPLERATE_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findlibsamplerate (system stub): could not locate samplerate.h "
        "(${LIBSAMPLERATE_SYSTEM_INCLUDE_DIR}) and/or libsamplerate "
        "(${LIBSAMPLERATE_SYSTEM_LIBRARY}). Install libsamplerate-devel from "
        "Fedora, or set LY_USE_SYSTEM_LIBSAMPLERATE=OFF to fall back to the "
        "upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${LIBSAMPLERATE_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${LIBSAMPLERATE_SYSTEM_LIBRARY})

set(libsamplerate_FOUND TRUE)
