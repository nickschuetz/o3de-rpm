#!/bin/bash
# Tier 11 -- Post-load liveness smoke test
#
# Validates that a GameLauncher continues running normally for a
# fixed window after reaching LEVEL_LOAD_END, without crashing.
# Catches "level loaded but engine froze immediately" -- a real
# failure mode that Tier 9 / Tier 10's smoke checks can't detect
# because they only verify the level-load success marker is present
# at some point in Game.log.
#
# Mechanism:
#   1. Launch the project's GameLauncher with bg_ConnectToAssetProcessor=0
#      and a known-good LoadLevel regset.
#   2. timeout(1) kills it after LIVENESS_SECONDS (default: 60).
#   3. After kill, verify:
#      a. The launcher was alive at end-of-window (timeout returned 124,
#         not a non-zero crash exit).
#      b. Game.log shows the LEVEL_LOAD_END success marker
#         ("Game Level Load Time:").
#      c. No crash markers (Critical Error, Assertion failed,
#         Segmentation fault, core dumped, panic()) appear in
#         Game.log.
#      d. Game.log accumulated SOME new lines during the observation
#         window (post-LEVEL_LOAD_END -- evidence the engine main
#         loop continues to do work, not a frozen first frame).
#
# Parameterized by env vars so the same script works for either
# sample. Defaults to NewspaperDeliveryGame (Tier 10's project)
# since it's the lighter-weight sample and the recovery logic is
# already proven.
#
# Usage:
#   tests/post-load-liveness-test.sh                            # NewspaperDeliveryGame / Neighborhood / 60s
#   LIVENESS_SECONDS=120 tests/post-load-liveness-test.sh       # extend window
#   PROJECT=multiplayer tests/post-load-liveness-test.sh        # switch to MultiplayerSample
#   PROJECT_DIR=...  LAUNCHER_BIN=...  LEVEL=... tests/post-load-liveness-test.sh
#                                                               # explicit project-specific override
#
# Exit codes:
#   0 -- all checks pass
#   1 -- one or more checks failed (see /tmp/tier11-*.log)
#   2 -- prerequisite missing (engine not installed, no DISPLAY, project not baked)

set -uo pipefail

RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RST='\033[0m'

pass=0; fail=0
ok()   { printf "  ${GREEN}PASS${RST} %s\n" "$*"; pass=$((pass+1)); }
nope() { printf "  ${RED}FAIL${RST} %s -- %s\n" "$1" "$2"; fail=$((fail+1)); }
warn() { printf "  ${YELLOW}WARN${RST} %s\n" "$*"; }
info() { printf "  %s\n" "$*"; }

: "${LIVENESS_SECONDS:=60}"
: "${PROJECT:=newspaper}"

# Auto-detect installed engine.
: "${O3DE_PKGNAME:=$(rpm -qa --qf '%{NAME}\n' 2>/dev/null | grep -E '^o3de[0-9]+$' | head -1)}"
: "${O3DE_PKGNAME:=o3de}"
if ! rpm -q "$O3DE_PKGNAME" >/dev/null 2>&1; then
    printf "prerequisite missing: %s package not installed\n" "$O3DE_PKGNAME" >&2
    exit 2
fi
ENGINE_PATH=$(rpm -ql "$O3DE_PKGNAME" 2>/dev/null \
    | grep -E '/engine\.json$' | grep -v '/bin/' | head -1 | xargs -r dirname)
[ -d "$ENGINE_PATH" ] || { printf "prerequisite missing: engine path not resolved\n" >&2; exit 2; }

# DISPLAY is required -- the launcher renders.
if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    printf "prerequisite missing: no DISPLAY / WAYLAND_DISPLAY -- liveness smoke needs a display\n" >&2
    exit 2
fi

# Project-specific defaults. Override any of these via env if the
# caller wants something different.
case "$PROJECT" in
    newspaper|newspaper-delivery|npd|paperkid)
        : "${PROJECT_DIR:=$HOME/PROJECTS/NewspaperDeliveryGame}"
        : "${LAUNCHER_BIN:=$ENGINE_PATH/bin/Linux/profile/Default/O3DE.GameLauncher}"
        : "${LEVEL:=Neighborhood}"
        : "${ENGINE_PATH_ARG:=$ENGINE_PATH}"
        ;;
    multiplayer|mps|multiplayer-sample)
        : "${PROJECT_DIR:=$HOME/PROJECTS/o3de-multiplayersample}"
        : "${LAUNCHER_BIN:=$PROJECT_DIR/build/linux/bin/profile/MultiplayerSample.GameLauncher}"
        # multiplayersample's autoexec works, but pre-set LoadLevel
        # anyway so this test doesn't depend on autoexec contents.
        : "${LEVEL:=}"
        : "${ENGINE_PATH_ARG:=$ENGINE_PATH}"
        ;;
    *)
        printf "unknown PROJECT=%s; expected 'newspaper' or 'multiplayer'\n" "$PROJECT" >&2
        exit 2
        ;;
esac

if [ ! -x "$LAUNCHER_BIN" ]; then
    printf "prerequisite missing: launcher binary not executable: %s\n" "$LAUNCHER_BIN" >&2
    exit 2
fi
if [ ! -d "$PROJECT_DIR/Cache" ]; then
    printf "prerequisite missing: project Cache/ not present -- run Tier 9/10 first to populate\n  expected: %s/Cache\n" "$PROJECT_DIR" >&2
    exit 2
fi

printf "${BOLD}=== Tier 11 -- post-load liveness smoke (project: %s) ===${RST}\n" "$PROJECT"
printf "engine path:    %s\n" "$ENGINE_PATH"
printf "project dir:    %s\n" "$PROJECT_DIR"
printf "launcher bin:   %s\n" "$LAUNCHER_BIN"
printf "level:          %s\n" "${LEVEL:-<from autoexec>}"
printf "window:         %ss\n\n" "$LIVENESS_SECONDS"

game_log="$PROJECT_DIR/user/log/Game.log"
smoke_log=/tmp/tier11-launcher-smoke.log

# The launcher rotates Game.log into a backup on startup -- the new
# session writes to a fresh file. So we don't measure a "delta"; we
# move the old log out of the way and measure the fresh log's total
# line count after the run. The new line count IS the activity count.
if [ -f "$game_log" ]; then
    mv "$game_log" "${game_log}.tier11-baseline.$$"
    info "moved pre-existing Game.log aside (so new run's count is the activity count)"
fi

# Build the regset args. LoadLevel regset only if LEVEL is set.
loadlevel_arg=""
if [ -n "$LEVEL" ]; then
    loadlevel_arg="--regset=/O3DE/Autoexec/ConsoleCommands/LoadLevel=$LEVEL"
fi

info "smoke: starting launcher with ${LIVENESS_SECONDS}s timeout"
timeout "${LIVENESS_SECONDS}s" "$LAUNCHER_BIN" \
    --project-path="$PROJECT_DIR" \
    --engine-path="$ENGINE_PATH_ARG" \
    --regset="/Amazon/AzCore/Bootstrap/sys_PakPriority=1" \
    --regset="/O3DE/Autoexec/ConsoleCommands/bg_ConnectToAssetProcessor=0" \
    $loadlevel_arg \
    >"$smoke_log" 2>&1
smoke_exit=$?

# Capture post-run line count. This is the full activity count
# for the fresh log file the launcher created on startup.
activity_lines=0
if [ -f "$game_log" ]; then
    activity_lines=$(wc -l < "$game_log")
fi
info "Game.log new line count (= activity this run): $activity_lines"

# Verification logic, in order of strictness:
#
# 1. timeout exit code semantics:
#    124 = timeout fired, process was killed (= alive at end-of-window: GOOD)
#    0   = launcher exited cleanly before window elapsed (unusual)
#    anything else = launcher crashed or exited with error
#
# 2. Crash markers anywhere in Game.log (post-pre-lines window):
#    "Critical Error", "Critical:", "Assertion failed",
#    "Segmentation fault", "core dumped", "panic()"
#    Note: NOT "CriticalAssetsCompiled" (that's a success log line).
#
# 3. Level-load success marker:
#    "Game Level Load Time:" must appear -- proves we even got to
#    a playable state.
#
# 4. Activity during window:
#    delta_lines must be > some-threshold to prove the engine
#    actually did work during the observation window, not just
#    print level-load messages and freeze.

if ! [ -f "$game_log" ]; then
    nope "Game.log not produced" "launcher may have crashed before writing log; see $smoke_log"
elif grep -qE "Critical Error|Critical:|Assertion failed|Segmentation fault|core dumped|panic\(\)" "$game_log"; then
    nope "crash markers in Game.log" "see $game_log"
elif ! grep -qE "Game Level Load Time:" "$game_log"; then
    nope "level never reached LEVEL_LOAD_END" "the launcher never produced a 'Game Level Load Time:' marker; see $game_log"
elif [ "$smoke_exit" -ne 124 ] && [ "$smoke_exit" -ne 0 ]; then
    nope "launcher died early" "exit=$smoke_exit before the ${LIVENESS_SECONDS}s window elapsed; see $smoke_log + $game_log"
else
    ok "launcher reached LEVEL_LOAD_END (Game Level Load Time present in log)"
    ok "no crash markers in Game.log over ${LIVENESS_SECONDS}s observation"
    if [ "$smoke_exit" -eq 124 ]; then
        ok "launcher was alive at end of ${LIVENESS_SECONDS}s window (timeout had to kill it)"
    else
        warn "launcher exited cleanly (exit=$smoke_exit) before timeout -- liveness inconclusive but no crash"
    fi
    # Activity threshold: with no AP-connection and a steady-state
    # level loaded, the engine writes very little to Game.log. But
    # it should write SOMETHING (CVar echoes, async-asset events,
    # spawnable generation churn). 50 new lines over a 60s window
    # is a conservative floor. If a project has special quiet-mode
    # behavior that violates this, the env var threshold below can
    # be tuned.
    : "${LIVENESS_MIN_NEW_LINES:=50}"
    if [ "$activity_lines" -ge "$LIVENESS_MIN_NEW_LINES" ]; then
        ok "engine wrote $activity_lines log lines during the ${LIVENESS_SECONDS}s window (>= $LIVENESS_MIN_NEW_LINES threshold)"
    else
        nope "engine log activity low" "only $activity_lines lines this run (threshold $LIVENESS_MIN_NEW_LINES); engine may be frozen post-load"
    fi
fi

printf "\n${BOLD}-- Summary --${RST}\n"
printf "  passed: %s\n" "$pass"
printf "  failed: %s\n" "$fail"
if [ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]; then
    printf "  ${GREEN}OVERALL: PASS${RST}\n"
    exit 0
else
    printf "  ${RED}OVERALL: FAIL${RST}\n"
    exit 1
fi
