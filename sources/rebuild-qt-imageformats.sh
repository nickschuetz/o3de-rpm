#!/bin/bash
# Rebuild Qt's jpeg and tiff image-format plugins against Fedora's
# libjpeg-turbo and libtiff, for the bundled Qt6 package.
#
# Why: the bundled qt-6.10.2 package from packages.o3de.org ships
# imageformats/libqjpeg.so linked to libjpeg.so.8 and libqtiff.so linked to
# libtiff.so.5 (the Ubuntu build host's libraries). Fedora has libjpeg.so.62
# and libtiff.so.6, so both plugins fail to load and Qt silently loses JPEG
# and TIFF: every .jpg texture fails in the Asset Processor ("No proper image
# loader") and the Project Manager background is missing
# (https://github.com/o3de/o3de/issues/20213). Upstream fix: build the Qt
# package with FEATURE_system_jpeg=OFF / FEATURE_system_tiff=OFF. Retire this
# script when that lands or when the RPM moves to system Qt6.
#
# The plugins are compiled from Qt's own sources at the SAME version as the
# bundled Qt (Qt refuses plugins built for another version), against the
# bundled Qt headers and libraries, and link only libjpeg/libtiff from Fedora.
#
# Usage: rebuild-qt-imageformats.sh <bundled qt dir> <qtbase src tarball>
#                                   <qtimageformats src tarball> <out dir>
# <bundled qt dir> is the package's qt/ directory (has include/, lib/, libexec/).
set -euo pipefail

QT="$1"; QTBASE_TAR="$2"; QTIF_TAR="$3"; OUT="$4"
CXX="${CXX:-clang++}"

# The bundled package's version must match the source tarballs exactly.
QTVER=$(sed -n 's/^set(PACKAGE_VERSION "\(.*\)")$/\1/p' "$QT/lib/cmake/Qt6/Qt6ConfigVersionImpl.cmake")
SRCVER=$(basename "$QTBASE_TAR" | sed -n 's/^qtbase-everywhere-src-\(.*\)\.tar\.xz$/\1/p')
if [ ! -f "$QTBASE_TAR" ] || [ ! -f "$QTIF_TAR" ]; then
    echo "rebuild-qt-imageformats: no plugin sources for bundled Qt '$QTVER' ($QTBASE_TAR);" >&2
    echo "add a qtbase/qtimageformats Source pair for it in o3de.spec and the Makefile." >&2
    exit 1
fi
if [ -z "$QTVER" ] || [ "$QTVER" != "$SRCVER" ]; then
    echo "rebuild-qt-imageformats: bundled Qt is '$QTVER' but the plugin sources are '$SRCVER';" >&2
    echo "update the qtbase/qtimageformats Source tarballs in o3de.spec to match." >&2
    exit 1
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -xf "$QTBASE_TAR" -C "$WORK" "qtbase-everywhere-src-$QTVER/src/plugins/imageformats/jpeg"
tar -xf "$QTIF_TAR" -C "$WORK" "qtimageformats-everywhere-src-$QTVER/src/plugins/imageformats/tiff"

INC=(-I"$QT/include" -I"$QT/include/QtCore" -I"$QT/include/QtGui"
     -I"$QT/include/QtCore/$QTVER" -I"$QT/include/QtCore/$QTVER/QtCore"
     -I"$QT/include/QtGui/$QTVER" -I"$QT/include/QtGui/$QTVER/QtGui"
     -I"$QT/mkspecs/linux-clang")
DEF=(-DQT_PLUGIN -DQT_SHARED -DQT_NO_DEBUG -DQT_CORE_LIB -DQT_GUI_LIB -DQT_NO_KEYWORDS)

build_plugin() {  # <name> <source dir> <system lib>
    local name=$1 dir=$2 lib=$3
    ( cd "$dir"
      "$QT/libexec/moc" "${DEF[@]}" "${INC[@]}" main.cpp -o main.moc
      # shellcheck disable=SC2016  # $ORIGIN is for the linker, not the shell
      "$CXX" -std=c++20 -O2 -g -fPIC -fvisibility=hidden -shared \
          ${CXXFLAGS:-} "${DEF[@]}" "${INC[@]}" -I. main.cpp q*handler.cpp \
          -o "$OUT/$name" -L"$QT/lib" -lQt6Gui -lQt6Core "$lib" \
          -Wl,-rpath,'$ORIGIN/..' -Wl,--as-needed ${LDFLAGS:-} )
}

mkdir -p "$OUT"
build_plugin libqjpeg.so "$WORK/qtbase-everywhere-src-$QTVER/src/plugins/imageformats/jpeg" -ljpeg
build_plugin libqtiff.so "$WORK/qtimageformats-everywhere-src-$QTVER/src/plugins/imageformats/tiff" -ltiff

# Refuse to hand back a plugin that still needs a non-Fedora soname.
for p in "$OUT/libqjpeg.so" "$OUT/libqtiff.so"; do
    if readelf -d "$p" | grep -qE 'NEEDED.*\[(libjpeg\.so\.8|libtiff\.so\.5)\]'; then
        echo "rebuild-qt-imageformats: $p still links a non-Fedora soname" >&2
        exit 1
    fi
done
echo "rebuild-qt-imageformats: built libqjpeg.so and libqtiff.so for Qt $QTVER in $OUT"
