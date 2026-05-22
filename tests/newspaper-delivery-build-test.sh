#!/bin/bash
# Tier 10 -- O3DE NewspaperDeliveryGame (Paper_Kid) build+bake smoke test
# against the installed o3de2605 RPM. Exercises a different project
# shape than Tier 9 (MultiplayerSample): script-only project (no native
# C++ gem code) with heavy LyShine + LandscapeCanvas + WhiteBox +
# EMotionFX usage. Single-player (no Multiplayer gem), no
# OpenParticleSystem, no NvCloth.
#
# Purpose: catch regressions Tier 7 (cube.fbx) and Tier 9
# (MultiplayerSample) can't surface -- specifically:
#   - script_only=true project asset pipeline (no native build artifacts)
#   - LyShine (legacy UI) asset processing
#   - LandscapeCanvas (terrain editor) asset processing
#   - WhiteBox (level prototyping) asset processing
#   - Lua / ScriptCanvas runtime path more heavily than Tier 9
#
# Pinning: clones from Nick's fork (nickschuetz/NewspaperDeliveryGame),
# pinned to a specific commit SHA. Using the fork rather than upstream
# directly gives us control over what we validate against -- if upstream
# breaks the project on Linux, the `test` branch on the fork can carry
# Linux-specific fixes without diverging the public-facing `main`. To
# sync from upstream, fast-forward the fork's `main` and bump the SHA
# in this script (same pattern as the engine snapshot pin in o3de.spec).
#
# Cost: ~10-20 min on a workstation (cold), ~3-10 min warm. No native
# C++ link phase (script_only=true) -- the heavy step is the
# AssetProcessorBatch full project bake. Disk: ~2-3 GB build tree.
#
# Usage:
#   tests/newspaper-delivery-build-test.sh             # auto-detect installed engine, default pin
#   NPD_DIR=/path tests/newspaper-delivery-build-test.sh
#   NPD_BRANCH=test tests/newspaper-delivery-build-test.sh    # follow `test` branch instead of pinned SHA
#   NPD_PIN_SHA=<sha> tests/newspaper-delivery-build-test.sh  # override pinned SHA
#   NPD_SKIP_CLONE=1 ...                                # reuse existing checkout
#   NPD_SKIP_BAKE=1  ...                                # skip asset bake (faster smoke)
#
# Exit codes:
#   0 -- all checks pass
#   1 -- one or more checks failed (consult the log)
#   2 -- prerequisite missing (engine not installed, git unavailable, etc.)

set -uo pipefail

RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RST='\033[0m'

pass=0; fail=0
ok()   { printf "  ${GREEN}PASS${RST} %s\n" "$*"; pass=$((pass+1)); }
nope() { printf "  ${RED}FAIL${RST} %s -- %s\n" "$1" "$2"; fail=$((fail+1)); }
warn() { printf "  ${YELLOW}WARN${RST} %s\n" "$*"; }
info() { printf "  %s\n" "$*"; }

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

command -v git >/dev/null 2>&1 || { printf "prerequisite missing: git\n" >&2; exit 2; }
command -v cmake >/dev/null 2>&1 || { printf "prerequisite missing: cmake\n" >&2; exit 2; }
command -v ninja >/dev/null 2>&1 || { printf "prerequisite missing: ninja-build\n" >&2; exit 2; }
command -v clang >/dev/null 2>&1 || { printf "prerequisite missing: clang\n" >&2; exit 2; }

# Default pin: latest commit on Nick's fork as of 2026-05-19. The
# "Make project script-only (#18)" commit; this is the version we
# validated against when we wired up Tier 10. Bump after refreshing
# the fork from upstream.
: "${NPD_REPO_URL:=https://github.com/nickschuetz/NewspaperDeliveryGame.git}"
: "${NPD_DIR:=$HOME/PROJECTS/NewspaperDeliveryGame}"
: "${NPD_BRANCH:=main}"
: "${NPD_PIN_SHA:=80d94e7}"
: "${NPD_SKIP_CLONE:=0}"
: "${NPD_SKIP_BAKE:=0}"

printf "${BOLD}=== Tier 10 -- NewspaperDeliveryGame (Paper_Kid) project build smoke ===${RST}\n"
printf "engine package: %s\n" "$O3DE_PKGNAME"
printf "engine path:    %s\n" "$ENGINE_PATH"
printf "project dir:    %s\n" "$NPD_DIR"
printf "project repo:   %s\n" "$NPD_REPO_URL"
printf "project branch: %s\n" "$NPD_BRANCH"
printf "pin SHA:        %s\n\n" "$NPD_PIN_SHA"

# Step 1: Clone (or refresh) the NewspaperDeliveryGame project.
printf "${BOLD}-- Step 1: clone / refresh NewspaperDeliveryGame --${RST}\n"
if [ "$NPD_SKIP_CLONE" = "1" ]; then
    info "skip clone (NPD_SKIP_CLONE=1): $NPD_DIR"
    if [ ! -d "$NPD_DIR/.git" ]; then
        nope "skip clone" "no checkout at $NPD_DIR"
        exit 1
    fi
elif [ -d "$NPD_DIR/.git" ]; then
    info "existing checkout at $NPD_DIR -- refreshing"
    if ( cd "$NPD_DIR" && git fetch --quiet origin "$NPD_BRANCH" \
            && git checkout --quiet "$NPD_BRANCH" \
            && git reset --hard --quiet "origin/$NPD_BRANCH" ); then
        ok "refreshed $NPD_DIR to origin/$NPD_BRANCH"
    else
        nope "git refresh" "$NPD_DIR -- see git output above"
        exit 1
    fi
else
    mkdir -p "$(dirname "$NPD_DIR")"
    info "cloning $NPD_REPO_URL (--branch $NPD_BRANCH) -- this may take a minute"
    if git clone --quiet --branch "$NPD_BRANCH" "$NPD_REPO_URL" "$NPD_DIR"; then
        ok "cloned to $NPD_DIR (branch $NPD_BRANCH)"
    else
        nope "git clone" "$NPD_REPO_URL -- see git output above"
        exit 1
    fi
fi

# Pin to the SHA so we have reproducibility across runs even if branch tip moves.
# Skip pinning if branch was explicitly overridden (NPD_BRANCH != main) -- the
# user wants to follow the branch tip in that case.
if [ "$NPD_BRANCH" = "main" ] && [ -n "$NPD_PIN_SHA" ]; then
    if ( cd "$NPD_DIR" && git checkout --quiet "$NPD_PIN_SHA" 2>/dev/null ); then
        ok "checked out pinned SHA $NPD_PIN_SHA"
    else
        warn "pinned SHA $NPD_PIN_SHA not resolvable -- continuing at branch tip"
    fi
fi

cd "$NPD_DIR" || { nope "cd" "could not cd to $NPD_DIR"; exit 1; }
head_sha=$(git rev-parse --short HEAD 2>/dev/null)
info "project HEAD: $head_sha"

# Step 2: Register the project against the installed engine.
# NewspaperDeliveryGame's project.json references only engine-shipped gems
# (Atom, AudioSystem, LyShine, EMotionFX, etc.) -- no external gem repo
# like Tier 9's o3de-multiplayersample-assets. So just register the project.
printf "\n${BOLD}-- Step 2: register project against installed engine --${RST}\n"
if "$ENGINE_PATH/scripts/o3de.sh" register -p "$NPD_DIR" >/tmp/tier10-register-project.log 2>&1; then
    ok "project registered against engine"
else
    nope "o3de.sh register -p" "see /tmp/tier10-register-project.log"
    exit 1
fi

# Step 3: cmake configure.
# script_only=true projects don't produce native artifacts, but cmake
# configure is still needed for AssetProcessor scan-folder discovery and
# project-script export. The configure cost is much lower than for
# native projects (no per-gem compile graph to construct).
printf "\n${BOLD}-- Step 3: cmake configure --${RST}\n"
BUILD_DIR="$NPD_DIR/build/linux"
mkdir -p "$BUILD_DIR" "$HOME/.o3de/3rdParty"
configure_log=/tmp/tier10-cmake-configure.log
info "running cmake configure (clang, ninja, profile)"
if env CC=clang CXX=clang++ cmake \
        -B "$BUILD_DIR" -S "$NPD_DIR" \
        -G Ninja \
        -DCMAKE_BUILD_TYPE=profile \
        -DLY_3RDPARTY_PATH="$HOME/.o3de/3rdParty" \
        -DLY_DISABLE_TEST_MODULES=ON \
        -DLY_STRIP_DEBUG_SYMBOLS=ON \
        >"$configure_log" 2>&1
then
    ok "cmake configure succeeded"
else
    nope "cmake configure" "see $configure_log (tail printed below)"
    tail -30 "$configure_log"
    exit 1
fi

# Step 4: AssetProcessorBatch (full project bake) with 2-pass absorber.
# Same cold-cache JobDep-gap absorber pattern as Tier 9. Even on a
# script-only project, AssetProcessor still has to bake every asset
# referenced by the project's Levels / Prefabs / Media / etc. directories,
# and the same cold-cache ordering quirks can surface.
if [ "$NPD_SKIP_BAKE" = "1" ]; then
    printf "\n${BOLD}-- Step 4: AssetProcessorBatch (SKIPPED, NPD_SKIP_BAKE=1) --${RST}\n"
else
    printf "\n${BOLD}-- Step 4: AssetProcessorBatch (full project asset bake) --${RST}\n"
    ap_log=/tmp/tier10-ap-batch.log
    ap_log_pass2=/tmp/tier10-ap-batch-pass2.log
    apbatch="$ENGINE_PATH/bin/Linux/profile/Default/AssetProcessorBatch"
    if [ ! -x "$apbatch" ]; then
        nope "AssetProcessorBatch" "binary not found at $apbatch"
        exit 1
    fi
    info "running AssetProcessorBatch on NewspaperDeliveryGame (logs to $ap_log)"
    pass1_ok=0
    if env "$apbatch" --project-path="$NPD_DIR" --platforms=linux \
            >"$ap_log" 2>&1
    then
        ok "AssetProcessorBatch pass 1 completed cleanly"
        pass1_ok=1
    else
        pass1_failed=$(grep -oE 'Number of Assets Failed to Process: [0-9]+' "$ap_log" | tail -1 | awk '{print $NF}')
        : "${pass1_failed:=?}"
        info "AssetProcessorBatch pass 1: $pass1_failed asset(s) failed; running pass 2 (cold-cache quirk absorber)"
        if env "$apbatch" --project-path="$NPD_DIR" --platforms=linux \
                >"$ap_log_pass2" 2>&1
        then
            ok "AssetProcessorBatch pass 2 succeeded -- cold-cache quirk absorbed (pass 1 had $pass1_failed failure(s))"
            pass1_ok=1
        else
            pass2_failed=$(grep -oE 'Number of Assets Failed to Process: [0-9]+' "$ap_log_pass2" | tail -1 | awk '{print $NF}')
            : "${pass2_failed:=?}"
            nope "AssetProcessorBatch" "pass 1 had $pass1_failed failures, pass 2 had $pass2_failed failures (see $ap_log_pass2 tail)"
            tail -40 "$ap_log_pass2"
        fi
    fi
fi

# Step 5: GameLauncher smoke (skipped on no-display environments).
# script_only projects run via the engine-installed O3DE.GameLauncher
# binary with --project-path, not a project-built launcher. Sanity-check
# that the launcher starts, runs for a few seconds, and exits without
# crash markers in its log.
printf "\n${BOLD}-- Step 5: GameLauncher smoke --${RST}\n"
launcher_bin="$ENGINE_PATH/bin/Linux/profile/Default/O3DE.GameLauncher"
if [ ! -x "$launcher_bin" ]; then
    nope "launcher" "O3DE.GameLauncher not at expected path $launcher_bin"
elif [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    info "no DISPLAY / WAYLAND_DISPLAY in env; skipping interactive launcher smoke"
    info "(rerun with DISPLAY=:0 to exercise this step; CI runs use Xvfb)"
else
    smoke_log=/tmp/tier10-launcher-smoke.log
    info "smoke: starting O3DE.GameLauncher --project-path with 15s timeout"
    # bg_ConnectToAssetProcessor=0 -- cache is fully baked from Step 4;
    # skip the launcher's auto-AP-spawn-and-wait path (~minutes of init
    # before level load even starts), which causes the launcher to hang
    # past Fedora's app-not-responding timeout.
    # Also: load the CharacterSample level explicitly since the project's
    # autoexec.cfg points at "start" which doesn't exist in this fork.
    timeout 15s "$launcher_bin" --project-path="$NPD_DIR" \
        --regset="/Amazon/AzCore/Bootstrap/sys_PakPriority=1" \
        --regset="/O3DE/Autoexec/ConsoleCommands/LoadLevel=CharacterSample" \
        --regset="/O3DE/Autoexec/ConsoleCommands/bg_ConnectToAssetProcessor=0" \
        >"$smoke_log" 2>&1
    smoke_exit=$?
    # 124 = timeout had to kill (= launcher ran for 15s without dying).
    # That alone is NOT enough -- the launcher can stay up for 15s while
    # never actually loading the level (black screen, hung main loop).
    # Real success requires a positive level-load marker in the log:
    #   "Game Level Load Time: [...] Level Levels/<NAME>/<NAME>.spawnable"
    # which O3DE prints after LEVEL_LOAD_END.
    # Crash markers exclude "CriticalAssetsCompiled" -- that's a SUCCESS log
    # line ("Launcher: CriticalAssetsCompiled") meaning critical assets are
    # ready, NOT a crash. Use word-boundary patterns that match real crashes.
    if grep -qE "Critical Error|Critical:|Assertion failed|Segmentation fault|core dumped|panic\(\)" "$smoke_log"; then
        nope "GameLauncher smoke" "crash/assertion markers in log (see $smoke_log)"
    elif grep -qE "Requested level not found" "$smoke_log"; then
        nope "GameLauncher smoke" "level not found in cache (see $smoke_log)"
    elif ! grep -qE "Game Level Load Time:" "$smoke_log"; then
        nope "GameLauncher smoke" "level never reached LEVEL_LOAD_END within 15s (see $smoke_log)"
    elif [ "$smoke_exit" -eq 124 ] || [ "$smoke_exit" -eq 0 ]; then
        level=$(grep "Game Level Load Time:" "$smoke_log" | grep -oE 'Level [^ ]+' | head -1)
        ok "GameLauncher loaded $level"
    else
        nope "GameLauncher smoke" "exit=$smoke_exit (likely init failure, see $smoke_log)"
        tail -30 "$smoke_log"
    fi
fi

# Summary.
printf "\n${BOLD}-- Summary --${RST}\n"
printf "  passed: %s\n" "$pass"
printf "  failed: %s\n" "$fail"
if [ "$fail" -eq 0 ]; then
    printf "  ${GREEN}OVERALL: PASS${RST}\n"
    exit 0
else
    printf "  ${RED}OVERALL: FAIL${RST}\n"
    exit 1
fi
