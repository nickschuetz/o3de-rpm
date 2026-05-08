#
# FindGoogleBenchmark.cmake -- system-package shim for o3de-rpm's Stage 1 migration.
#
# Drops into cmake/3rdParty/ during %prep when --with system_googlebenchmark
# is on. `find_package(GoogleBenchmark REQUIRED)` resolves to this file
# because cmake/3rdParty/ is on CMAKE_MODULE_PATH ahead of cmake's stock
# module path.
#
# Creates `3rdParty::GoogleBenchmark` directly (matching `ly_associate_package(...
# TARGETS GoogleBenchmark ...)`'s target name in the bundled-googlebenchmark
# case). Engine consumer is `Code/Framework/AzTest/CMakeLists.txt:32-34`
# which links AzTest's static archive against the GoogleBenchmark target;
# AzTestRunner statically links AzTest in turn (verified empirically via nm
# symbol inspection 2026-05-08; see project_az_test_runner_architecture.md
# memory note for the architecture detail).
#
# Architectural context:
#
# Per @nick-l-o3de's 2026-05-08 sig-build / PR #19738 thread, the engine's
# `LY_DISABLE_TEST_MODULES=ON` switch (which our spec sets in %build) is
# meant to skip the engine's OWN test modules but NOT to suppress the test
# infrastructure that ships for external gem developers. AzTestRunner +
# AzTest + googletest + googlemock + googlebenchmark all ship unconditionally
# so a `.deb` / `.msi` / `sdk` user can write their own benchmarks against
# the runner. So googlebenchmark is a build+ship dep of the engine no matter
# what -- this swap just shifts the source from the bundled prebuilt tarball
# (packages.o3de.org CDN) to Fedora's google-benchmark-devel.
#
# Why we don't `find_package(benchmark CONFIG REQUIRED)` and alias:
# Fedora's benchmarkConfig.cmake creates `benchmark::benchmark` as a
# side-effect IMPORTED target. O3DE's runtime walker (cmake/Platform/Common/
# RuntimeDependencies_common.cmake) iterates every target in the project,
# hits side-effect targets that don't have a fully-populated IMPORTED_LOCATION,
# and bails. Doing the find_path / find_library lookup directly here means
# the only googlebenchmark-related target in the project is the one we want
# (`3rdParty::GoogleBenchmark`) -- same pattern as the FindZLIB, FindSQLite,
# Findassimp, etc. shims.
#
# Linkage variance: the bundled tarball ships static archives (libbenchmark.a)
# and the engine's bundled FindGoogleBenchmark.cmake.template links to those.
# Fedora ships ONLY the shared library (`libbenchmark.so` -- no `-static`
# subpackage). With this swap on, AzTestRunner ends up dynamically linked
# to libbenchmark.so.1 at runtime instead of having gbench compiled in
# statically. gbench's public API is stable across 1.7.0 (engine pin) -> 1.9.5
# (Fedora ship); same shape as how the rest of our Stage 1 swaps move from
# bundled-static to system-shared.
#
# Engine pin: googlebenchmark-1.7.0-rev1-linux. Fedora's google-benchmark-devel
# in F44 is 1.9.5-5.fc44. ABI-compatible for our consumers (AzTest's API
# surface uses standard BENCHMARK macros + benchmark::internal::InitializeStreams).

set(TARGET_WITH_NAMESPACE "3rdParty::GoogleBenchmark")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(GoogleBenchmark_FOUND TRUE)
    return()
endif()

find_path(GOOGLEBENCHMARK_SYSTEM_INCLUDE_DIR
    NAMES benchmark/benchmark.h
    PATHS /usr/include /usr/local/include
)

find_library(GOOGLEBENCHMARK_SYSTEM_LIBRARY
    NAMES benchmark
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT GOOGLEBENCHMARK_SYSTEM_INCLUDE_DIR OR NOT GOOGLEBENCHMARK_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "FindGoogleBenchmark (system stub): could not locate benchmark/benchmark.h "
        "(${GOOGLEBENCHMARK_SYSTEM_INCLUDE_DIR}) and/or libbenchmark "
        "(${GOOGLEBENCHMARK_SYSTEM_LIBRARY}). Install google-benchmark-devel "
        "from Fedora, or set LY_USE_SYSTEM_GOOGLEBENCHMARK=OFF to fall back "
        "to the upstream fetcher.")
endif()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${GOOGLEBENCHMARK_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${GOOGLEBENCHMARK_SYSTEM_LIBRARY})

set(GoogleBenchmark_FOUND TRUE)
