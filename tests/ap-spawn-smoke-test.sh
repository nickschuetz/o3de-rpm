#!/bin/bash
# Tier 8 -- AssetProcessor runtime process-lifecycle smoke
#
# Launches AssetProcessor against a registered project and verifies
# that at least one AssetBuilder child reaches and sustains "alive"
# state. Catches the class of bug where AP can spawn-but-not-keep
# builders alive.
#
# Motivating example: 2026-05-12 Patch0012 v1 attempt set
# processLaunchInfo.m_tetherLifetime = true in Builder::LaunchProcess.
# Built clean on F44 + rawhide (COPR 10447331), passed every static
# check we had. On first runtime: every AssetBuilder received SIGTERM
# within ~21 ms of fork because prctl(PR_SET_PDEATHSIG) tracks the
# forking thread (a short-lived TaskWorker), not the parent process.
# AP could never establish its resident pool; Editor hung at
# "Asset Processor working..." indefinitely. Build-validation passed,
# runtime-validation failed.
#
# This tier was the missing check.
#
# Test design:
#   1. Spawn AssetProcessor with --project-path against a registered project.
#   2. Poll every 2s for builders that are alive (parented to our AP, not
#      in Z/zombie state). Up to O3DE_TEST_AP_TIMEOUT seconds.
#   3. Once >= 1 alive builder found, take a second sample
#      O3DE_TEST_AP_PERSIST_S seconds later. Require at least one PID
#      from sample 1 to still be alive in sample 2 (catches the
#      "flashing builders" v1 pattern -- builders spawn but die fast
#      enough that any single sample might miss them, but the dual
#      sample with PID overlap catches sustained absence).
#   4. Cleanup: SIGTERM the AP we spawned; reap any straggling builders.
#
# Skip conditions (exit 2):
#   - No registered projects in ~/.o3de/o3de_manifest.json
#   - AssetProcessor binary missing
#
# Failure conditions (exit 1):
#   - No alive builders within O3DE_TEST_AP_TIMEOUT seconds
#   - Builders flashed in/out but none persisted O3DE_TEST_AP_PERSIST_S
#     between samples (the v1 Patch0012 failure signature)
#
# Pass condition (exit 0):
#   - At least one builder alive, sustained between two samples.
#
# Environment overrides:
#   O3DE_PKGNAME            pin a specific versioned package (default: auto-detect)
#   O3DE_TEST_PROJECT_PATH  use this project (default: first manifest entry)
#   O3DE_TEST_AP_TIMEOUT    max wait seconds for first builder (default 60)
#   O3DE_TEST_AP_PERSIST_S  delay between dual samples (default 5)

set -uo pipefail

RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RST='\033[0m'

pass=0; fail=0
ok()   { printf "  ${GREEN}PASS${RST} %s\n" "$*"; pass=$((pass+1)); }
nope() { printf "  ${RED}FAIL${RST} %s -- %s\n" "$1" "$2"; fail=$((fail+1)); }
info() { printf "  %s\n" "$*"; }

: "${O3DE_PKGNAME:=$(rpm -qa --qf '%{NAME}\n' 2>/dev/null | grep -E '^o3de[0-9]+$' | head -1)}"
: "${O3DE_PKGNAME:=o3de}"
: "${O3DE_TEST_AP_TIMEOUT:=60}"
: "${O3DE_TEST_AP_PERSIST_S:=5}"

if ! rpm -q "$O3DE_PKGNAME" >/dev/null 2>&1; then
    printf "prerequisite missing: %s package not installed\n" "$O3DE_PKGNAME" >&2
    exit 2
fi

ENGINE_PATH=$(rpm -ql "$O3DE_PKGNAME" 2>/dev/null \
    | grep -E '/engine\.json$' | grep -v '/bin/' | head -1 | xargs -r dirname)
[ -d "$ENGINE_PATH" ] || { printf "prerequisite missing: engine path not resolved\n" >&2; exit 2; }

AP_BIN="$ENGINE_PATH/bin/Linux/profile/Default/AssetProcessor"
[ -x "$AP_BIN" ] || { printf "prerequisite missing: AssetProcessor binary not at %s\n" "$AP_BIN" >&2; exit 2; }

# Pick a registered project for AP to load. If the caller didn't pass
# one explicitly, use the first one from the user's manifest.
if [ -z "${O3DE_TEST_PROJECT_PATH:-}" ]; then
    MANIFEST="$HOME/.o3de/o3de_manifest.json"
    if [ ! -r "$MANIFEST" ]; then
        printf "prerequisite missing: no manifest at %s; run o3de2605-cli register --this-engine first\n" "$MANIFEST" >&2
        exit 2
    fi
    O3DE_TEST_PROJECT_PATH=$(python3 -c "
import json, sys
m = json.load(open('$MANIFEST'))
projs = m.get('projects', [])
print(projs[0] if projs else '', end='')
" 2>/dev/null)
    if [ -z "$O3DE_TEST_PROJECT_PATH" ]; then
        printf "prerequisite missing: no registered projects in %s\n" "$MANIFEST" >&2
        exit 2
    fi
fi

[ -d "$O3DE_TEST_PROJECT_PATH" ] || { printf "prerequisite missing: project path not a directory: %s\n" "$O3DE_TEST_PROJECT_PATH" >&2; exit 2; }

printf "${BOLD}=== Tier 8 -- AssetProcessor runtime smoke ===${RST}\n"
printf "package:       %s\n" "$O3DE_PKGNAME"
printf "engine:        %s\n" "$ENGINE_PATH"
printf "AP binary:     %s\n" "$AP_BIN"
printf "project path:  %s\n" "$O3DE_TEST_PROJECT_PATH"
printf "timeout:       %ds first-builder + %ds persistence\n\n" "$O3DE_TEST_AP_TIMEOUT" "$O3DE_TEST_AP_PERSIST_S"

# Spawn AP detached so its stdout/stderr don't tangle our output.
AP_LOG=$(mktemp -t ap-spawn-smoke.XXXXXX.log)
trap 'rm -f "$AP_LOG"' EXIT

"$AP_BIN" --project-path="$O3DE_TEST_PROJECT_PATH" --start-hidden >"$AP_LOG" 2>&1 &
AP_PID=$!

cleanup() {
    if kill -0 "$AP_PID" 2>/dev/null; then
        info "cleanup: SIGTERM AP pid $AP_PID"
        kill -TERM "$AP_PID" 2>/dev/null
        sleep 2
        if kill -0 "$AP_PID" 2>/dev/null; then
            info "cleanup: SIGKILL AP pid $AP_PID (TERM didn't take)"
            kill -9 "$AP_PID" 2>/dev/null
        fi
    fi
    # Reap any straggling builders parented to systemd-user (orphans
    # from earlier AP-death scenarios; not our concern but worth a
    # final sweep to leave the system clean).
    sleep 1
    stragglers=$(pgrep -x AssetBuilder 2>/dev/null | wc -l)
    if [ "$stragglers" -gt 0 ]; then
        info "cleanup: $stragglers straggling AssetBuilder processes; leaving (test scope is AP-spawn smoke, not orphan cleanup)"
    fi
}
trap 'cleanup; rm -f "$AP_LOG"' EXIT

# Helper: count builders parented to our AP that are alive (not zombie).
count_alive_builders() {
    pgrep -P "$AP_PID" -x AssetBuilder 2>/dev/null | while read -r pid; do
        state=$(awk '{print $3}' "/proc/$pid/stat" 2>/dev/null)
        [ "$state" != "Z" ] && [ -n "$state" ] && echo "$pid"
    done | wc -l
}

list_alive_builders() {
    pgrep -P "$AP_PID" -x AssetBuilder 2>/dev/null | while read -r pid; do
        state=$(awk '{print $3}' "/proc/$pid/stat" 2>/dev/null)
        [ "$state" != "Z" ] && [ -n "$state" ] && echo "$pid"
    done
}

# Phase 1: wait up to O3DE_TEST_AP_TIMEOUT seconds for >= 1 alive builder.
printf "Phase 1: wait for first alive builder (up to %ds)...\n" "$O3DE_TEST_AP_TIMEOUT"
first_seen_at=""
for i in $(seq 1 $((O3DE_TEST_AP_TIMEOUT / 2))); do
    sleep 2
    if ! kill -0 "$AP_PID" 2>/dev/null; then
        nope "ap-alive" "AssetProcessor died unexpectedly at $((i*2))s"
        info "AP log tail (last 20 lines):"
        tail -20 "$AP_LOG" 2>/dev/null | sed 's/^/    /'
        exit 1
    fi
    n=$(count_alive_builders)
    if [ "$n" -ge 1 ]; then
        first_seen_at=$((i*2))
        ok "phase-1 first builder alive after ${first_seen_at}s (count=$n)"
        sample1_pids=$(list_alive_builders | tr '\n' ' ')
        info "sample 1 PIDs: $sample1_pids"
        break
    fi
done

if [ -z "$first_seen_at" ]; then
    nope "phase-1" "no alive builders parented to AP within ${O3DE_TEST_AP_TIMEOUT}s"
    info "AP processes: $(pgrep -af AssetProcessor 2>/dev/null | wc -l) ; child builders: $(pgrep -P "$AP_PID" -x AssetBuilder | wc -l)"
    info "AP log tail (last 30 lines):"
    tail -30 "$AP_LOG" 2>/dev/null | sed 's/^/    /'
    exit 1
fi

# Phase 2: take a second sample after the persistence window. Require
# at least one PID from sample 1 to still be alive. Catches the v1
# Patch0012 "flashing builders" pattern -- if builders spawn but die
# within ~21ms of fork, the dual-sample requirement isn't satisfied.
printf "Phase 2: wait %ds and re-sample (persistence check)...\n" "$O3DE_TEST_AP_PERSIST_S"
sleep "$O3DE_TEST_AP_PERSIST_S"
sample2_pids=$(list_alive_builders | tr '\n' ' ')
info "sample 2 PIDs: $sample2_pids"

overlap=0
for pid1 in $sample1_pids; do
    for pid2 in $sample2_pids; do
        if [ "$pid1" = "$pid2" ]; then
            overlap=$((overlap+1))
            break
        fi
    done
done

if [ "$overlap" -ge 1 ]; then
    ok "phase-2 $overlap builder(s) persisted across the ${O3DE_TEST_AP_PERSIST_S}s window"
else
    nope "phase-2" "no builder from sample 1 survived the ${O3DE_TEST_AP_PERSIST_S}s persistence window"
    info "this is the v1 Patch0012 failure signature (builders spawn but die within ms)"
    info "AP log tail (last 30 lines):"
    tail -30 "$AP_LOG" 2>/dev/null | sed 's/^/    /'
    exit 1
fi

printf "\n${BOLD}-- Summary --${RST}\n"
total=$((pass+fail))
if [ "$fail" -eq 0 ]; then
    printf "  ${GREEN}${pass}/${total} checks passed${RST}\n"
    exit 0
else
    printf "  ${YELLOW}${pass}/${total} passed${RST}, ${RED}${fail} failed${RST}\n"
    exit 1
fi
