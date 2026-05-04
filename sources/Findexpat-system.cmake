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
#     path.
#
# Refactored 2026-05-04 to the mikkelsen pattern (direct find_path +
# find_library, no `include(${CMAKE_ROOT}/Modules/FindEXPAT.cmake)`).
# Same root cause and same fix as FindZLIB-system.cmake — see that
# file's comment block for the full diagnosis. Note that this shim
# also provides EXPAT::EXPAT as an alias of 3rdParty::expat — that's
# the standard cmake namespace some upstream consumers reference.

set(TARGET_WITH_NAMESPACE "3rdParty::expat")
if (TARGET ${TARGET_WITH_NAMESPACE})
    set(expat_FOUND TRUE)
    set(EXPAT_FOUND TRUE)
    return()
endif()

find_path(EXPAT_SYSTEM_INCLUDE_DIR
    NAMES expat.h
    PATHS /usr/include /usr/local/include
)

find_library(EXPAT_SYSTEM_LIBRARY
    NAMES expat
    PATHS /usr/lib64 /usr/lib /usr/local/lib64 /usr/local/lib
)

if (NOT EXPAT_SYSTEM_INCLUDE_DIR OR NOT EXPAT_SYSTEM_LIBRARY)
    message(FATAL_ERROR
        "Findexpat (system stub): could not locate expat.h "
        "(${EXPAT_SYSTEM_INCLUDE_DIR}) and/or libexpat "
        "(${EXPAT_SYSTEM_LIBRARY}). Install expat-devel from Fedora, or "
        "set LY_USE_SYSTEM_EXPAT=OFF to fall back to the upstream fetcher.")
endif()

# Extract the version from expat.h's XML_MAJOR/MINOR/MICRO_VERSION macros
# so consumers like the bundled FindOpenColorIO.cmake that read
# `expat_VERSION` get a real value (rather than an empty string that
# might trip a >= compare).
file(READ "${EXPAT_SYSTEM_INCLUDE_DIR}/expat.h" _expat_h_contents)
string(REGEX MATCH "#[ ]*define[ ]+XML_MAJOR_VERSION[ ]+([0-9]+)" _ "${_expat_h_contents}")
set(_expat_major "${CMAKE_MATCH_1}")
string(REGEX MATCH "#[ ]*define[ ]+XML_MINOR_VERSION[ ]+([0-9]+)" _ "${_expat_h_contents}")
set(_expat_minor "${CMAKE_MATCH_1}")
string(REGEX MATCH "#[ ]*define[ ]+XML_MICRO_VERSION[ ]+([0-9]+)" _ "${_expat_h_contents}")
set(_expat_micro "${CMAKE_MATCH_1}")
set(EXPAT_VERSION_STRING "${_expat_major}.${_expat_minor}.${_expat_micro}")
unset(_expat_h_contents)
unset(_expat_major)
unset(_expat_minor)
unset(_expat_micro)

add_library(${TARGET_WITH_NAMESPACE} INTERFACE IMPORTED GLOBAL)
ly_target_include_system_directories(TARGET ${TARGET_WITH_NAMESPACE}
    INTERFACE ${EXPAT_SYSTEM_INCLUDE_DIR})
target_link_libraries(${TARGET_WITH_NAMESPACE} INTERFACE ${EXPAT_SYSTEM_LIBRARY})

# Provide EXPAT::EXPAT as the standard uppercase cmake namespace alias.
# See FindZLIB-system.cmake's alias block for the rationale.
if (NOT TARGET EXPAT::EXPAT)
    add_library(EXPAT::EXPAT ALIAS ${TARGET_WITH_NAMESPACE})
endif()

# Bridge uppercase output variables to lowercase consumers (the bundled
# FindOpenColorIO.cmake reads `expat_FOUND` etc. for compat with the
# pre-existing dual-case convention the bundled Findexpat.cmake set up).
set(EXPAT_FOUND TRUE)
set(EXPAT_INCLUDE_DIR "${EXPAT_SYSTEM_INCLUDE_DIR}")
set(EXPAT_INCLUDE_DIRS "${EXPAT_SYSTEM_INCLUDE_DIR}")
set(EXPAT_LIBRARY "${EXPAT_SYSTEM_LIBRARY}")
set(EXPAT_LIBRARIES "${EXPAT_SYSTEM_LIBRARY}")
set(expat_FOUND TRUE)
set(expat_VERSION ${EXPAT_VERSION_STRING})
set(expat_INCLUDE_DIR ${EXPAT_INCLUDE_DIR})
set(expat_INCLUDE_DIRS ${EXPAT_INCLUDE_DIRS})
set(expat_LIBRARY ${EXPAT_LIBRARY})
set(expat_LIBRARIES ${EXPAT_LIBRARIES})
