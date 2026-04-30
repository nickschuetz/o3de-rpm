#!/bin/bash
# Tier 6 — UI smoke test for an installed o3de RPM.
#
# Launches Project Manager (and optionally Editor via O3DE's --exec
# Python automation) under Xvfb, verifies the process stays alive
# long enough to be considered "started", optionally captures a
# screenshot for the summary.
#
# Usage:
#   tests/ui-smoke-test.sh                  # Project Manager smoke only
#   tests/ui-smoke-test.sh --editor         # also try Editor --exec
#   tests/ui-smoke-test.sh --screenshot     # capture screenshots
#
# Prerequisites:
#   - o3de RPM installed
#   - Tier 3 setup done (per-user venv, engine registered)
#   - Xvfb installed (dnf install xorg-x11-server-Xvfb)
#   - Optional: scrot (for screenshots), mesa-vulkan-drivers (for
#     software Vulkan via lavapipe — set VK_ICD_FILENAMES manually
#     if running in a container)
#
# Exit code: 0 on pass, 1 on fail, 2 on prereqs missing.

set -uo pipefail

DO_EDITOR=0
DO_SCREENSHOT=0
ENGINE_PATH="${O3DE_ENGINE_PATH:-/opt/o3de}"
PASS='\033[1;32m✓\033[0m'
FAIL='\033[1;31m✗\033[0m'

while [ $# -gt 0 ]; do
    case "$1" in
        --editor)     DO_EDITOR=1; shift ;;
        --screenshot) DO_SCREENSHOT=1; shift ;;
        -h|--help)    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

require() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'prerequisite missing: %s — %s\n' "$1" "${2:-install it first}" >&2
        exit 2
    }
}
require Xvfb 'dnf install xorg-x11-server-Xvfb'
require xdpyinfo 'dnf install xorg-x11-utils'
[ "$DO_SCREENSHOT" -eq 1 ] && require scrot 'dnf install scrot'
require o3de 'install the o3de RPM first'

# ── Xvfb setup ───────────────────────────────────────────────────────────────
DISPLAY_NUM=99
while xdpyinfo -display ":$DISPLAY_NUM" >/dev/null 2>&1; do
    DISPLAY_NUM=$((DISPLAY_NUM + 1))
done

LOG=$(mktemp)
trap 'kill $XVFB_PID 2>/dev/null; rm -f "$LOG"' EXIT

Xvfb ":$DISPLAY_NUM" -screen 0 1920x1080x24 +extension RANDR \
    >"$LOG" 2>&1 &
XVFB_PID=$!
sleep 1
xdpyinfo -display ":$DISPLAY_NUM" >/dev/null 2>&1 || {
    echo "Xvfb failed to start. Log:"
    cat "$LOG"
    exit 1
}
export DISPLAY=":$DISPLAY_NUM"
echo "Xvfb up on $DISPLAY (pid $XVFB_PID)"

# ── Test: Project Manager launches and stays up ──────────────────────────────
echo
echo "▶▶▶ Project Manager smoke test"

PM_LOG=$(mktemp)
o3de >"$PM_LOG" 2>&1 &
PM_PID=$!

# Give it 15 seconds to either crash or settle
for i in 5 10 15; do
    sleep 5
    if ! kill -0 "$PM_PID" 2>/dev/null; then
        printf "$FAIL Project Manager exited within ${i}s\n"
        echo "Last 30 lines of output:"
        tail -30 "$PM_LOG"
        rm -f "$PM_LOG"
        exit 1
    fi
done

printf "$PASS Project Manager survived 15s without crashing\n"

# Verify a window actually appeared
if xdpyinfo -display "$DISPLAY" 2>/dev/null | grep -q 'root window id'; then
    if [ -n "$(xdotool search --name 'O3DE' 2>/dev/null)" ]; then
        printf "$PASS X window with title 'O3DE' is mapped\n"
    elif command -v wmctrl >/dev/null && wmctrl -lx | grep -qi o3de; then
        printf "$PASS Window manager sees an O3DE window\n"
    else
        printf "  (note: xdotool/wmctrl not finding the window — may be Wayland or window naming mismatch)\n"
    fi
fi

if [ "$DO_SCREENSHOT" -eq 1 ]; then
    SHOT="/tmp/o3de-pm-screenshot.png"
    scrot "$SHOT" 2>/dev/null && printf "$PASS Screenshot: $SHOT\n" || \
        printf "  (scrot failed; not blocking)\n"
fi

# Clean shutdown
kill -TERM "$PM_PID" 2>/dev/null
wait "$PM_PID" 2>/dev/null
rm -f "$PM_LOG"

# ── Test: Editor via --exec automation (opt-in) ──────────────────────────────
if [ "$DO_EDITOR" -eq 1 ]; then
    echo
    echo "▶▶▶ Editor scripted smoke test (--editor)"

    EDITOR="$ENGINE_PATH/bin/Linux/profile/Default/Editor"
    [ -x "$EDITOR" ] || EDITOR="$ENGINE_PATH/bin/Linux/debug/Default/Editor"
    if [ ! -x "$EDITOR" ]; then
        printf "$FAIL no Editor binary found\n"
        exit 1
    fi

    SCRIPT=$(mktemp --suffix=.py)
    cat >"$SCRIPT" <<'EOF'
# Minimal exit-cleanly automation script. Editor's Python automation
# API runs this in the editor process; sys.exit() shuts it down.
import sys
print("editor automation: ok")
sys.exit(0)
EOF

    timeout --preserve-status 60 "$EDITOR" --autotest_mode --runpythontest "$SCRIPT" \
        >/tmp/o3de-editor-smoke.log 2>&1
    RC=$?
    rm -f "$SCRIPT"

    if [ "$RC" -eq 0 ] || [ "$RC" -eq 124 ]; then
        # 124 = timeout-killed, which is fine if it printed our marker
        if grep -q 'editor automation: ok' /tmp/o3de-editor-smoke.log; then
            printf "$PASS Editor ran the automation script to completion\n"
        else
            printf "$FAIL Editor didn't print the automation marker; see /tmp/o3de-editor-smoke.log\n"
            exit 1
        fi
    else
        printf "$FAIL Editor --autotest_mode exited with code %s; see /tmp/o3de-editor-smoke.log\n" "$RC"
        exit 1
    fi
fi

echo
echo "All UI smoke tests passed."
exit 0
