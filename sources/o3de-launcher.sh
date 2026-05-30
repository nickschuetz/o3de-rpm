#!/bin/bash
# O3DE launcher — sets up environment for the system-installed engine.
#
# Configuration via environment:
#   O3DE_BUILD_CONFIG  debug | profile
#                      Default: prefer profile, fall back to debug.
#                      The o3de RPM ships profile binaries; the optional
#                      o3de-debug subpackage adds debug binaries. With
#                      only one installed, auto-detect picks it.
#   O3DE_ENGINE_PATH   override engine root (default: @O3DE_INSTALL_PREFIX@,
#                      substituted to the versioned install path at %install
#                      time — e.g. /opt/O3DE/26.05.0)
#   O3DE_PYTHON_VERSION  bundled-Python series (default: 3.10)
#                        Comes from O3DE's package CDN's python-X.Y.Z-revN-linux
#                        and matches the venv site-packages directory name.
set -euo pipefail

# @O3DE_INSTALL_PREFIX@ is the placeholder the spec's %install step
# substitutes with the versioned install path (e.g. /opt/O3DE/26.05.0).
# Using a placeholder rather than a literal /opt/o3de prevents the
# substitution from also rewriting the legacy_prefixes list below
# (which intentionally keeps /opt/o3de as a HISTORICAL prefix to
# migrate user state from).
ENGINE_PATH="${O3DE_ENGINE_PATH:-@O3DE_INSTALL_PREFIX@}"
PYV="${O3DE_PYTHON_VERSION:-3.10}"

if [ -n "${O3DE_BUILD_CONFIG:-}" ]; then
    BUILD_CONFIG="$O3DE_BUILD_CONFIG"
    case "$BUILD_CONFIG" in
        debug|profile) ;;
        *)
            printf 'o3de: O3DE_BUILD_CONFIG must be debug or profile (got: %s)\n' \
                "$BUILD_CONFIG" >&2
            exit 64
            ;;
    esac
elif [ -x "$ENGINE_PATH/bin/Linux/profile/Default/o3de" ]; then
    BUILD_CONFIG=profile
elif [ -x "$ENGINE_PATH/bin/Linux/debug/Default/o3de" ]; then
    BUILD_CONFIG=debug
else
    printf 'o3de: no installed engine binary found under %s/bin/Linux/{profile,debug}/Default\n' \
        "$ENGINE_PATH" >&2
    exit 69
fi

BIN_DIR="$ENGINE_PATH/bin/Linux/$BUILD_CONFIG/Default"
if [ ! -x "$BIN_DIR/o3de" ]; then
    printf 'o3de: %s configuration is not installed at %s\n' \
        "$BUILD_CONFIG" "$BIN_DIR" >&2
    exit 69
fi

export O3DE_ENGINE_PATH="$ENGINE_PATH"

# Vulkan validation layers: when the RPM activates system_vulkan_validation_layers
# (Patch0013 + LY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS cmake gate), the bundled
# layer .so + manifest are NOT installed alongside the engine binary. Point the
# Vulkan loader at Fedora's standard layer-discovery directory if it isn't
# already set; the engine's Instance.cpp uses overwrite=0 on its own VK_LAYER_PATH
# SetEnv (Patch0013 second hunk), so this pre-set wins. Bundled-engine installs
# (system_vulkan_validation_layers OFF) ignore this -- the loader's default
# discovery still finds /usr/share/vulkan/explicit_layer.d/ entries in addition
# to whatever the engine SetEnv puts there. No-op when VK_LAYER_PATH is already
# user-set, which preserves developer overrides.
if [ -z "${VK_LAYER_PATH:-}" ] && [ -d /usr/share/vulkan/explicit_layer.d ]; then
    export VK_LAYER_PATH=/usr/share/vulkan/explicit_layer.d
fi

# manifest.py uses O3DE_ENGINE_PATH to bypass the venv-relative __file__ logic.
# Engine-id calculation must match how get_python.sh computes it (via $DIR/..).
#
# cmake-detection chain (matches get_python.sh's pattern):
#   1. system cmake on PATH (most common — installed via package mgr)
#   2. bundled cmake at <engineRoot>/cmake/runtime/bin/cmake (upstream's
#      .deb installer ships this; our RPM currently does not, but if a
#      future bundle lands the launcher picks it up automatically)
#   3. graceful degrade: empty ENGINE_ID, skip the per-engine venv on
#      PYTHONPATH. The engine still runs; user venv functionality
#      degrades silently.
# This chain is why cmake is `Recommends:` in the spec, not `Requires:`
# — minimal installs (--setopt=install_weak_deps=False) skip cmake
# and the launcher copes.
CMAKE_BIN=""
if command -v cmake >/dev/null 2>&1; then
    CMAKE_BIN="$(command -v cmake)"
elif [ -x "$ENGINE_PATH/cmake/runtime/bin/cmake" ]; then
    CMAKE_BIN="$ENGINE_PATH/cmake/runtime/bin/cmake"
fi

ENGINE_ID=""
if [ -n "$CMAKE_BIN" ]; then
    ENGINE_ID="$("$CMAKE_BIN" -P "$ENGINE_PATH/cmake/CalculateEnginePathId.cmake" \
        "$ENGINE_PATH/python/.." 2>/dev/null | tail -1 || true)"
fi

VENV_SITEPKGS=""
if [ -n "$ENGINE_ID" ] && [ -d "$HOME/.o3de/Python/venv/$ENGINE_ID/lib/python$PYV/site-packages" ]; then
    VENV_SITEPKGS="$HOME/.o3de/Python/venv/$ENGINE_ID/lib/python$PYV/site-packages"
fi

PYTHONPATH="$ENGINE_PATH/scripts${VENV_SITEPKGS:+:$VENV_SITEPKGS}${PYTHONPATH:+:$PYTHONPATH}"
LD_LIBRARY_PATH="$BIN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH LD_LIBRARY_PATH

# All writable state lives under ~/.o3de. Engine root stays read-only.
mkdir -p "$HOME/.o3de/user" "$HOME/.o3de/Logs"

# First-run migration: rewrite legacy engine_path overrides in
# <project>/user/project.json. Idempotent — gated by a per-prefix
# marker file. Only touches user/project.json (the override layer),
# never the project.json under VCS. JSON-aware (resilient to whitespace,
# trailing commas, sibling keys). Silently skips on any error so a
# malformed home dir can't block the editor from launching.
migration_marker="$HOME/.o3de/.engine-path-migrated-${ENGINE_PATH//\//_}"
if [ ! -f "$migration_marker" ] && [ -d "$HOME/O3DE/Projects" ]; then
    find "$HOME/O3DE/Projects" -maxdepth 3 -path '*/user/project.json' -print0 2>/dev/null \
        | xargs -0 -r /usr/bin/python3 -c '
import json, sys
target = sys.argv[1]
legacy_prefixes = ("/usr/o3de", "/opt/o3de")
for path in sys.argv[2:]:
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        continue
    ep = data.get("engine_path")
    if not isinstance(ep, str):
        continue
    # Only rewrite engine_path values that match a known legacy prefix
    # AND differ from the current install. Preserves user-customized paths.
    if ep == target or ep not in legacy_prefixes:
        continue
    data["engine_path"] = target
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
            f.write("\n")
    except OSError:
        pass
' "$ENGINE_PATH" 2>/dev/null || :
    touch "$migration_marker" 2>/dev/null || :
fi

# Qt 5.15-rev9 auto-DPI quirk on Wayland XWayland: the bundled Qt
# version mis-detects font scale, producing oversized or tiny fonts
# in Project Manager. Community report 2026-05-28 (adwaita on F44 +
# GNOME Wayland + 4K + amdgpu) confirms the same workaround used by
# the upstream Debian .deb package: set QT_FONT_DPI=100 to disable
# auto-scaling. Default only when the user hasn't set it AND we're
# on a Wayland session; X11 sessions behave correctly without this.
# Will become irrelevant when Qt 6 migration lands in 26.10.0
# (vanilla Qt 6 + system qt6-qtwayland resolves both this and the
# missing-wayland-platform-plugin gap).
if [ -z "${QT_FONT_DPI:-}" ] && [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    export QT_FONT_DPI=100
fi

# The editor's GUI helper dialogs (Open Export Settings, Open Android
# Project Generator, Open CMake GUI) drive the bundled Python's tkinter.
# Export Settings uses tkinter.tix, which does `package require Tix`.
# Fedora ships the Tix Tcl package under /usr/lib64/tcl/Tix<ver>/, but
# the bundled Tcl's auto_path only covers the version-specific
# /usr/lib64/tcl8.6 + /usr/share/tcl8.6 dirs, so it can't find Tix even
# when the tix package is installed. Add /usr/lib64/tcl to TCLLIBPATH
# (Tcl searches each entry plus its immediate subdirs for a pkgIndex) so
# Tix resolves. Harmless when tix isn't installed: just an unused search
# path. Guarded so a user-set TCLLIBPATH is preserved and not doubled.
# Community report 2026-05-29 (adwglds, F44); see the tk8/tcl8/tix
# Recommends in the spec.
case " ${TCLLIBPATH:-} " in
    *" /usr/lib64/tcl "*) : ;;
    *) export TCLLIBPATH="${TCLLIBPATH:+$TCLLIBPATH }/usr/lib64/tcl" ;;
esac

exec "$BIN_DIR/o3de" \
    -name "O3DE" \
    --engine-path="$ENGINE_PATH" \
    --project-user-path="$HOME/.o3de/user" \
    --project-log-path="$HOME/.o3de/Logs" \
    "$@"
# `--engine-path` is required: the engine's C++ scan-up engine-root logic
# resolves the shipped /opt/o3de/bin/Linux/profile/Default/engine.json
# symlink to a path whose SHA1 doesn't match the venv ID computed by
# get_python.sh (which hashes /opt/o3de/). Passing the engine root
# explicitly bypasses that scan-up and keeps both sides in sync.
#
# `-name "O3DE"` is the standard X11 toolkit argument (consumed by Qt
# before the engine's argparser sees it). Sets WM_CLASS to "O3DE" so
# GNOME/Plasma matches the running window to the desktop file's
# StartupWMClass and shows our installed icon in the dock, instead
# of the engine's internal Qt-set icon. The double-quotes around the
# literal value are LOAD-BEARING: o3de.spec's %install runs
#   sed -e 's|-name "O3DE"|-name "O3DE-%{o3de_major_tag}"|g' …
# at install time to versionize this string per major (so e.g.
# `o3de2605` passes `-name "O3DE-2605"` matching the desktop file's
# `StartupWMClass=O3DE-2605`). The sed pattern requires the quotes
# to match — without them, the substitution silently no-ops and the
# dock icon falls back to a generic Qt icon.
