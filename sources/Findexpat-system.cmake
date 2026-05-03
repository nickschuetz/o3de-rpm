#
# Findexpat.cmake — case-bridging system-expat shim for o3de-rpm Stage 1.
#
# Why this file exists: the bundled openimageio-opencolorio package's
# FindOpenColorIO.cmake calls `find_package(expat)` (lowercase), which
# on Linux's case-sensitive filesystem looks for Findexpat.cmake — not
# cmake's stock FindEXPAT.cmake (uppercase). When --with system_expat
# is on and we gate out the upstream ly_associate_package(expat-2.4.2...)
# call, the bundled Findexpat.cmake (lowercase, from packages.o3de.org)
# is not on disk anymore, and find_package(expat) silently fails.
#
# This shim is named Findexpat.cmake and copied into cmake/3rdParty/
# during %prep. cmake's MODULE_PATH discovery picks it up, it delegates
# to the stock FindEXPAT.cmake (uppercase) — which does the actual
# system-package lookup — and re-exposes the results under both the
# uppercase and lowercase variable conventions for compatibility.
#
# The bundled Findexpat.cmake establishes the dual-case convention
# (see comments in expat-2.4.2-rev2-linux/Findexpat.cmake): both
# EXPAT_* and expat_* output variables, plus the 3rdParty::expat
# namespaced target. We mirror that contract.

if (TARGET 3rdParty::expat)
    set(expat_FOUND TRUE)
    return()
endif()

# MODULE forces cmake to use the stock FindEXPAT.cmake rather than
# any cmake config file expat might ship as XConfig.cmake (which on
# Fedora it doesn't, but be explicit).
find_package(EXPAT REQUIRED MODULE)

# Bridge uppercase output variables to lowercase consumers (notably
# the bundled FindOpenColorIO.cmake) expect.
set(expat_FOUND ${EXPAT_FOUND})
set(expat_VERSION ${EXPAT_VERSION_STRING})
set(expat_INCLUDE_DIR ${EXPAT_INCLUDE_DIR})
set(expat_INCLUDE_DIRS ${EXPAT_INCLUDE_DIRS})
set(expat_LIBRARY ${EXPAT_LIBRARY})
set(expat_LIBRARIES ${EXPAT_LIBRARIES})

# Most O3DE consumers reference 3rdParty::expat (via O3DE's namespacing
# convention). Patch0006's else-branch creates the same alias when
# --with system_expat is active; we re-create here defensively in case
# this shim is loaded before that branch ran.
if (NOT TARGET 3rdParty::expat)
    add_library(3rdParty::expat ALIAS EXPAT::EXPAT)
endif()
