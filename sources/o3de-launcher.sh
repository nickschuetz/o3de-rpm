#!/bin/bash
# O3DE launcher — sets up environment for the system-installed engine.
#
# Configuration via environment:
#   O3DE_BUILD_CONFIG  debug | profile
#                      Default: prefer profile, fall back to debug. Builds
#                      packaged with rpmbuild --with debug_only ship only
#                      debug, so the fallback is what matters there.
#   O3DE_ENGINE_PATH   override engine root (default: /opt/o3de)
set -euo pipefail

ENGINE_PATH="${O3DE_ENGINE_PATH:-/opt/o3de}"

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
if [ -n "$ENGINE_ID" ] && [ -d "$HOME/.o3de/Python/venv/$ENGINE_ID/lib/python3.10/site-packages" ]; then
    VENV_SITEPKGS="$HOME/.o3de/Python/venv/$ENGINE_ID/lib/python3.10/site-packages"
fi

PYTHONPATH="$ENGINE_PATH/scripts${VENV_SITEPKGS:+:$VENV_SITEPKGS}${PYTHONPATH:+:$PYTHONPATH}"
LD_LIBRARY_PATH="$BIN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH LD_LIBRARY_PATH

# All writable state lives under ~/.o3de. Engine root stays read-only.
mkdir -p "$HOME/.o3de/user" "$HOME/.o3de/Logs"

exec "$BIN_DIR/o3de" \
    --project-user-path="$HOME/.o3de/user" \
    --project-log-path="$HOME/.o3de/Logs" \
    "$@"
