#!/bin/bash
# O3DE launcher — sets up environment for the system-installed engine.
#
# Configuration via environment:
#   O3DE_BUILD_CONFIG  debug | profile
#                      Default: prefer profile, fall back to debug.
#                      The o3de RPM ships profile binaries; the optional
#                      o3de-debug subpackage adds debug binaries. With
#                      only one installed, auto-detect picks it.
#   O3DE_ENGINE_PATH   override engine root (default: /opt/o3de)
#   O3DE_PYTHON_VERSION  bundled-Python series (default: 3.10)
#                        Comes from O3DE's package CDN's python-X.Y.Z-revN-linux
#                        and matches the venv site-packages directory name.
set -euo pipefail

ENGINE_PATH="${O3DE_ENGINE_PATH:-/opt/o3de}"
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

# manifest.py uses O3DE_ENGINE_PATH to bypass the venv-relative __file__ logic.
# Engine-id calculation must match how get_python.sh computes it (via $DIR/..).
ENGINE_ID="$(/usr/bin/cmake -P "$ENGINE_PATH/cmake/CalculateEnginePathId.cmake" \
    "$ENGINE_PATH/python/.." 2>/dev/null | tail -1 || true)"

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

exec "$BIN_DIR/o3de" \
    -name O3DE \
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
# `-name O3DE` is the standard X11 toolkit argument (consumed by Qt
# before the engine's argparser sees it). Sets WM_CLASS to "O3DE" so
# GNOME/Plasma matches the running window to o3de-editor.desktop's
# StartupWMClass=O3DE and shows our installed icon in the dock,
# instead of the engine's internal Qt-set icon.
