#
# FindRapidXML.cmake -- system-package stub for o3de-rpm's Stage 1 migration.
#
# Replaces the upstream
#     ly_associate_package(PACKAGE_NAME RapidXML-1.13-rev1-multiplatform ...)
# entry that fetches RapidXML headers from packages.o3de.org, by locating
# the system-installed RapidXML headers (provided by Fedora's `rapidxml-devel`
# RPM) and creating the `3rdParty::RapidXML` INTERFACE target that O3DE
# consumers (AzCore + AzNetworking) expect.
#
# RapidXML is a header-only library; no .so to link. Build-time-only swap.
#
# Layout differences this stub bridges:
#
#   |              | O3DE bundle on packages.o3de.org           | Fedora rapidxml-devel              |
#   |--------------|---------------------------------------------|-------------------------------------|
#   | header paths | <bundle>/include/rapidxml/rapidxml.h        | /usr/include/rapidxml.h             |
#   |              | <bundle>/include/rapidxml/rapidxml_print.h  | /usr/include/rapidxml_print.h       |
#   |              | <bundle>/include/rapidxml/rapidxml_utils.h  | /usr/include/rapidxml_utils.h       |
#   |              | <bundle>/include/rapidxml/rapidxml_iterators.h | /usr/include/rapidxml_iterators.h |
#
# Engine code does `#include <rapidxml/rapidxml.h>` (and the three companion
# headers). We bridge the include-path mismatch by generating one-line
# wrapper headers at
#   ${CMAKE_BINARY_DIR}/_system_rapidxml/rapidxml/<name>.h
# that each `#include <<name>.h>` (the system flat-path form). The build dir
# is placed first on the consumer's include path so the wrappers win over
# any other rapidxml/ directory that might exist.
#
# Activation: copy this file into ${LY_ROOT_FOLDER}/cmake/3rdParty/ during
# %prep, and pass -DLY_USE_SYSTEM_RAPIDXML=ON to cmake so the gating in
# BuiltInPackages_linux_x86_64.cmake (Patch0006) skips the upstream fetcher.

set(TARGET_WITH_NAMESPACE "3rdParty::RapidXML")
if (TARGET ${TARGET_WITH_NAMESPACE})
    return()
endif()

find_path(RAPIDXML_SYSTEM_INCLUDE_DIR
    NAMES rapidxml.h
    PATHS /usr/include /usr/local/include
)

if (NOT RAPIDXML_SYSTEM_INCLUDE_DIR)
    message(FATAL_ERROR
        "FindRapidXML (system stub): could not locate rapidxml.h on a system "
        "include path. Install rapidxml-devel from Fedora, or set "
        "LY_USE_SYSTEM_RAPIDXML=OFF to fall back to the upstream fetcher.")
endif()

# Bridge the <rapidxml/<name>.h> include syntax to the system-installed
# flat-path <<name>.h> headers by emitting tiny wrapper headers in the
# build dir.
set(_o3de_rapidxml_wrapper_dir ${CMAKE_BINARY_DIR}/_system_rapidxml)
file(MAKE_DIRECTORY ${_o3de_rapidxml_wrapper_dir}/rapidxml)
foreach(_hdr rapidxml rapidxml_print rapidxml_utils rapidxml_iterators)
    file(WRITE ${_o3de_rapidxml_wrapper_dir}/rapidxml/${_hdr}.h
"// o3de-rpm Stage 1 system-rapidxml wrapper (FindRapidXML-system.cmake).\n\
// Bridges <rapidxml/${_hdr}.h> consumer syntax to the system-installed\n\
// flat-path <${_hdr}.h> header from Fedora's rapidxml-devel.\n\
#pragma once\n\
#include <${_hdr}.h>\n")
endforeach()

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE
        ${_o3de_rapidxml_wrapper_dir}
        ${RAPIDXML_SYSTEM_INCLUDE_DIR})

set(RapidXML_FOUND TRUE)
