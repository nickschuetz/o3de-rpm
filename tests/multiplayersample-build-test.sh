#!/bin/bash
# Tier 9 -- O3DE MultiplayerSample build+bake smoke test against the
# installed o3de2605 RPM. Exercises the full "user-facing project
# author" flow: clone a real community project, register it against
# the installed engine, configure+build with cmake, run AssetProcessorBatch
# over the project's asset tree, smoke the GameLauncher binary.
#
# Purpose: catch regressions the cube.fbx asset-bake test (Tier 7) can't.
# Tier 7 only probes per-library health on a tiny scene; Tier 9 exercises
# the project-build pipeline (cmake configure against installed engine,
# gem resolution, AzslcCompile, ShaderAssetBuilder, the lot) plus a
# real multi-level asset tree on a project that ships networking,
# replication, gameplay scripting -- a much bigger surface.
#
# Branch alignment: o3de-multiplayersample tracks O3DE's `development`.
# No `stabilization/26050` branch exists in multiplayersample (the last
# was `stabilization/25100`). For our 26.05.x engine snapshot pinned at
# `stabilization/26050 @ 246b46f5`, the closest matching multiplayersample
# branch is `development`. This is a known directional mismatch -- the
# engine is on the locked release branch, the sample is on dev -- but
# it's the best signal we have until multiplayersample cuts a 26.05
# release branch.
#
# Cost: ~10-30 min on a workstation (cold), ~5-15 min warm. Project
# build is incremental thanks to ninja + ccache (if installed); the
# expensive part is the project asset bake. Disk: ~10 GB build tree.
#
# Usage:
#   tests/multiplayersample-build-test.sh                     # auto-detect installed engine
#   O3DE_PKGNAME=o3de2605 tests/multiplayersample-build-test.sh
#   MPSAMPLE_REPO_URL=...  tests/multiplayersample-build-test.sh  # override sample repo
#   MPSAMPLE_ASSETS_REPO_URL=... tests/multiplayersample-build-test.sh # override assets repo
#   MPSAMPLE_DIR=/path tests/multiplayersample-build-test.sh  # custom clone target
#   MPSAMPLE_BRANCH=other-branch tests/multiplayersample-build-test.sh
#   MPSAMPLE_SKIP_CLONE=1 tests/multiplayersample-build-test.sh   # reuse existing checkout
#   MPSAMPLE_SKIP_BAKE=1  tests/multiplayersample-build-test.sh   # skip the slow asset bake
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

# Defaults point at upstream. The o3de-multiplayersample-assets#177
# fix (Linux case-sensitive standardpbr.materialtype reference) merged
# upstream 2026-05-22; the sample repo itself stays in lock-step with
# upstream's development. Set these env vars to a fork URL when you
# need to test a fork-side fix before its upstream PR merges.
: "${MPSAMPLE_REPO_URL:=https://github.com/o3de/o3de-multiplayersample.git}"
: "${MPSAMPLE_ASSETS_REPO_URL:=https://github.com/o3de/o3de-multiplayersample-assets.git}"
: "${MPSAMPLE_DIR:=$HOME/PROJECTS/o3de-multiplayersample}"
: "${MPSAMPLE_ASSETS_DIR:=$HOME/PROJECTS/o3de-multiplayersample-assets}"
: "${MPSAMPLE_BRANCH:=development}"
: "${MPSAMPLE_SKIP_CLONE:=0}"
: "${MPSAMPLE_SKIP_BAKE:=0}"

# Ninja parallelism. O3DE's link step is RAM-hungry (each concurrent
# C++ link of a big gem/engine .so consumes 6-10 GB). On a 32 GB system
# with default `--parallel $(nproc)`, the link phase OOMs and the host
# can crash (seen 2026-05-14 on a 32 GB workstation building
# MultiplayerSample.GameLauncher). Auto-throttle: if MemTotal < 48 GiB,
# cap parallelism at max(2, MemTotal_GiB / 8) -- gives each concurrent
# link ~8 GB of headroom. Honors explicit MPSAMPLE_PARALLEL override.
if [ -z "${MPSAMPLE_PARALLEL:-}" ]; then
    mem_total_kb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
    mem_total_gib=$((mem_total_kb / 1024 / 1024))
    if [ "$mem_total_gib" -lt 48 ] && [ "$mem_total_gib" -gt 0 ]; then
        MPSAMPLE_PARALLEL=$(( mem_total_gib / 8 ))
        [ "$MPSAMPLE_PARALLEL" -lt 2 ] && MPSAMPLE_PARALLEL=2
    fi
fi

printf "${BOLD}=== Tier 9 -- MultiplayerSample project build smoke ===${RST}\n"
printf "engine package: %s\n" "$O3DE_PKGNAME"
printf "engine path:    %s\n" "$ENGINE_PATH"
printf "sample dir:     %s\n" "$MPSAMPLE_DIR"
printf "assets dir:     %s\n" "$MPSAMPLE_ASSETS_DIR"
printf "sample branch:  %s\n\n" "$MPSAMPLE_BRANCH"

# Helper for the two clone steps -- same shape, different repo + dir.
# Args: $1 = repo URL, $2 = local clone target dir
clone_or_refresh() {
    local url="$1" dir="$2"
    if [ "$MPSAMPLE_SKIP_CLONE" = "1" ]; then
        info "skip clone (MPSAMPLE_SKIP_CLONE=1): $dir"
        [ -d "$dir/.git" ] || { nope "skip clone" "no checkout at $dir"; return 1; }
        return 0
    fi
    if [ -d "$dir/.git" ]; then
        info "existing checkout at $dir -- refreshing"
        ( cd "$dir" && git fetch --quiet origin "$MPSAMPLE_BRANCH" && git checkout --quiet "$MPSAMPLE_BRANCH" && git reset --hard --quiet "origin/$MPSAMPLE_BRANCH" ) \
            || { nope "git refresh" "$dir -- see git output above"; return 1; }
        ok "refreshed $dir to origin/$MPSAMPLE_BRANCH"
    else
        mkdir -p "$(dirname "$dir")"
        info "cloning $url (--branch $MPSAMPLE_BRANCH) -- this may take a few minutes"
        git clone --quiet --depth 50 --branch "$MPSAMPLE_BRANCH" "$url" "$dir" \
            || { nope "git clone" "$url -- see git output above"; return 1; }
        ok "cloned to $dir (branch $MPSAMPLE_BRANCH)"
    fi
    return 0
}

# ─── Step 1: Clone (or refresh) the MultiplayerSample project + assets ──────
# Both repos are needed: o3de-multiplayersample is the project itself;
# o3de-multiplayersample-assets ships the project's gem dependencies
# (character_mps, props_mps, landscape_mps, kb3d_mps, level_art_mps,
# pbr_material_pack_mps) referenced from project.json's gem_names list.
# Per upstream README, both must be on the same branch as the engine.
printf "${BOLD}-- Step 1a: clone / refresh o3de-multiplayersample --${RST}\n"
clone_or_refresh "$MPSAMPLE_REPO_URL" "$MPSAMPLE_DIR" || exit 1
printf "\n${BOLD}-- Step 1b: clone / refresh o3de-multiplayersample-assets --${RST}\n"
clone_or_refresh "$MPSAMPLE_ASSETS_REPO_URL" "$MPSAMPLE_ASSETS_DIR" || exit 1

# LFS auto-recovery (mirrors Tier 10's logic, see [[project_o3de_sample_maintenance_gap]]):
# If the working tree has LFS pointer files (131 bytes) instead of real
# binary content, FBX scene-compilation fails downstream with cryptic
# parser errors. Three failure modes guarded against:
#   1. Initial clone done with GIT_LFS_SKIP_SMUDGE=1 / LFS server outage
#      leaves the tree as pointer files.
#   2. The git fetch + git reset --hard refresh path doesn't re-trigger
#      smudge on files that already have pointer content.
#   3. The .lfsconfig in the upstream repo points at the BASE endpoint
#      `/api/v1` (auth=none); a fork-served clone needs the per-fork
#      sub-path with credentials, plus a small batch size (10) to avoid
#      the AWS-Lambda batch-size limit that returns HTTP 502.
for repo_dir in "$MPSAMPLE_DIR" "$MPSAMPLE_ASSETS_DIR"; do
    # Pick a known LFS-tracked file in each repo as the size canary.
    # Both repos use FBX heavily; use any *.fbx if present.
    canary=$(find "$repo_dir" -name "*.fbx" -type f 2>/dev/null | head -1)
    [ -z "$canary" ] && continue
    canary_size=$(stat -c '%s' "$canary" 2>/dev/null || echo 0)
    if [ "$canary_size" -lt 1024 ]; then
        info "LFS pointer detected in $repo_dir ($canary is $canary_size bytes) -- configuring + pulling"
        # Derive the fork owner from the URL configured for this repo.
        repo_url=$(cd "$repo_dir" && git remote get-url origin 2>/dev/null)
        mps_owner=$(basename "$(dirname "$repo_url")")
        ( cd "$repo_dir" && \
            git config lfs.url "https://d1yks6rjd5juc8.cloudfront.net/api/v1/fork/$mps_owner" && \
            git config lfs.transfer.batchSize 10 && \
            git lfs pull )
        if [ $? -eq 0 ]; then
            ok "git lfs pull completed in $repo_dir (batchSize=10, fork=$mps_owner)"
        else
            nope "git lfs pull" "$repo_dir -- see $repo_dir/.git/lfs/logs/"
            exit 1
        fi
    else
        ok "LFS working tree already populated in $repo_dir ($canary is $canary_size bytes)"
    fi
done

cd "$MPSAMPLE_DIR" || { nope "cd" "could not cd to $MPSAMPLE_DIR"; exit 1; }
head_sha=$(git rev-parse --short HEAD 2>/dev/null)
assets_head_sha=$(git -C "$MPSAMPLE_ASSETS_DIR" rev-parse --short HEAD 2>/dev/null)
info "project HEAD: $head_sha   assets HEAD: $assets_head_sha"

# ─── Step 2: Register gems + project against installed engine ───────────────
# Order is load-bearing: gems first (so the gem names referenced in
# project.json resolve), then the project itself. Otherwise project
# registration fails with "The project requires <gem-name>".
printf "\n${BOLD}-- Step 2: register gems + project against installed engine --${RST}\n"
if "$ENGINE_PATH/scripts/o3de.sh" register --all-gems-path "$MPSAMPLE_ASSETS_DIR/Gems" >/tmp/tier9-register-gems.log 2>&1; then
    ok "asset-side gems registered ($MPSAMPLE_ASSETS_DIR/Gems)"
else
    nope "o3de.sh register --all-gems-path" "see /tmp/tier9-register-gems.log"
    exit 1
fi
if "$ENGINE_PATH/scripts/o3de.sh" register -p "$MPSAMPLE_DIR" >/tmp/tier9-register-project.log 2>&1; then
    ok "project registered against engine"
else
    nope "o3de.sh register -p" "see /tmp/tier9-register-project.log"
    exit 1
fi

# ─── Step 3: cmake configure ────────────────────────────────────────────────
printf "\n${BOLD}-- Step 3: cmake configure --${RST}\n"
BUILD_DIR="$MPSAMPLE_DIR/build/linux"
mkdir -p "$BUILD_DIR"
# CC/CXX: O3DE requires clang on Linux. Engine cmake refuses gcc.
# CMAKE_BUILD_TYPE: profile is the default; matches our installed engine layout.
# LY_PROJECTS: tell cmake which project to configure.
# LY_DISABLE_TEST_MODULES=ON: skip test targets (engine ships AzTest but
#   the project's own test bits would just add build time here).
# LY_3RDPARTY_PATH: needed even for installed-engine builds; point at a
#   user-writable dir for any project-side 3p fetches.
mkdir -p "$HOME/.o3de/3rdParty"
configure_log=/tmp/tier9-cmake-configure.log
info "running cmake configure (clang, ninja, profile)"
if env CC=clang CXX=clang++ cmake \
    -B "$BUILD_DIR" -S "$MPSAMPLE_DIR" \
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

# ─── Step 4: ninja build (game launcher + bare project gem) ─────────────────
# Build TWO targets:
#   1. MultiplayerSample.GameLauncher -- the client-side runnable game (used
#      by the smoke step below). Pulls in libMultiplayerSample.Client.so as
#      a side effect.
#   2. MultiplayerSample (bare phony target) -- produces libMultiplayerSample.so
#      with no variant suffix. This is the .so AssetProcessorBatch tries to
#      load to populate BehaviorContext for ScriptCanvas processing. Without
#      it, AP fails on .scriptcanvas files that reference the project's own
#      multiplayer components (e.g., NetworkHealthComponent), producing
#      "Failed to load dynamic library at path 'libMultiplayerSample.so'"
#      errors followed by CreateJobs failures on the affected scriptcanvas
#      files. Caught 2026-05-14 while diagnosing 8 .scriptcanvas job failures
#      that disappeared once the bare target was built.
printf "\n${BOLD}-- Step 4: ninja build (MultiplayerSample.GameLauncher + MultiplayerSample) --${RST}\n"
build_log=/tmp/tier9-ninja-build.log
parallel_arg=""
if [ -n "${MPSAMPLE_PARALLEL:-}" ]; then
    parallel_arg="--parallel $MPSAMPLE_PARALLEL"
    info "building MultiplayerSample.GameLauncher + bare MultiplayerSample (throttled to $MPSAMPLE_PARALLEL parallel workers for RAM)"
else
    parallel_arg="--parallel"
    info "building MultiplayerSample.GameLauncher + bare MultiplayerSample (full parallelism)"
fi
if env CC=clang CXX=clang++ cmake --build "$BUILD_DIR" \
        --target MultiplayerSample.GameLauncher \
        --target MultiplayerSample \
        $parallel_arg \
    >"$build_log" 2>&1
then
    ok "MultiplayerSample.GameLauncher + libMultiplayerSample.so built"
else
    nope "ninja build" "see $build_log (tail printed below)"
    tail -50 "$build_log"
    exit 1
fi

launcher_bin="$BUILD_DIR/bin/profile/MultiplayerSample.GameLauncher"
if [ -x "$launcher_bin" ]; then
    ok "GameLauncher binary present at $launcher_bin"
else
    nope "binary" "GameLauncher not at expected path"
fi

# ─── Step 5: AssetProcessorBatch (full project bake) ────────────────────────
# Two-pass strategy to absorb AP's cold-cache job-dependency quirk:
# Some O3DE asset builders don't declare full JobDependency on their
# upstream-dep assets (e.g. ParticleBuilder's preWarm.particle references
# ParticleSpriteEmit.material but doesn't declare a JobDependency on it).
# On a cold cache, AP picks up the dependent first (alphabetic) and fails;
# the second pass succeeds because the dep is now baked. Documented
# instances: cube.fbx (project_tier7_cold_cache_quirk.md) and
# preWarm.particle (2026-05-14). Tier 9 absorbs the quirk by re-running
# once and grading on the union result -- if the second pass leaves 0
# failures, count it as PASS.
if [ "$MPSAMPLE_SKIP_BAKE" = "1" ]; then
    printf "\n${BOLD}-- Step 5: AssetProcessorBatch (SKIPPED, MPSAMPLE_SKIP_BAKE=1) --${RST}\n"
else
    printf "\n${BOLD}-- Step 5: AssetProcessorBatch (full project asset bake) --${RST}\n"
    ap_log=/tmp/tier9-ap-batch.log
    ap_log_pass2=/tmp/tier9-ap-batch-pass2.log
    info "running AssetProcessorBatch on MultiplayerSample (logs to $ap_log)"
    apbatch="$BUILD_DIR/bin/profile/AssetProcessorBatch"
    if [ ! -x "$apbatch" ]; then
        apbatch="$ENGINE_PATH/bin/Linux/profile/Default/AssetProcessorBatch"
    fi
    if [ ! -x "$apbatch" ]; then
        nope "AssetProcessorBatch" "binary not found in either build/ or engine"
        exit 1
    fi
    pass1_ok=0
    if env "$apbatch" --project-path="$MPSAMPLE_DIR" --platforms=linux \
            >"$ap_log" 2>&1
    then
        ok "AssetProcessorBatch pass 1 completed cleanly"
        pass1_ok=1
    else
        pass1_failed=$(grep -oE 'Number of Assets Failed to Process: [0-9]+' "$ap_log" | tail -1 | awk '{print $NF}')
        : "${pass1_failed:=?}"
        info "AssetProcessorBatch pass 1: $pass1_failed asset(s) failed; running pass 2 (cold-cache quirk absorber)"
        if env "$apbatch" --project-path="$MPSAMPLE_DIR" --platforms=linux \
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
    if [ "$pass1_ok" -ne 1 ]; then
        ap_exit=$?
        err_count=$(grep -cE "^\[Error\]|FAIL|fatal:" "$ap_log" 2>/dev/null || echo 0)
        nope "AssetProcessorBatch" "exit=$ap_exit, $err_count error-tagged lines (see $ap_log tail)"
        tail -40 "$ap_log"
    fi
fi

# ─── Step 6: GameLauncher smoke (skipped on no-display environments) ────────
printf "\n${BOLD}-- Step 6: GameLauncher smoke --${RST}\n"
if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    info "no DISPLAY / WAYLAND_DISPLAY in env; skipping interactive launcher smoke"
    info "(rerun with DISPLAY=:0 to exercise this step; CI runs use Xvfb)"
else
    # Smoke step modernized 2026-05-21 to mirror Tier 10's logic:
    #   - Pass bg_ConnectToAssetProcessor=0 to skip the auto-AP-spawn wait
    #     (Step 5 already populated the cache).
    #   - 30s timeout (15s was too tight; launcher's startup overhead is
    #     ~10s of module/RHI init before level load even starts).
    #   - Read the per-project Game.log (unbuffered, written directly by
    #     the engine) instead of the captured stdout, which can be
    #     truncated when timeout(1) kills the launcher.
    #   - Success means at least one "Game Level Load Time:" line in the
    #     log -- positive proof a level loaded. Process-didn't-crash
    #     alone is not sufficient (the launcher parks in a hung-but-
    #     running state when level load fails).
    #   - Crash patterns exclude "CriticalAssetsCompiled" (which is
    #     actually a SUCCESS log line). Match word-boundary contexts only.
    #   - The project's autoexec may attempt multiple LoadLevel calls and
    #     log "Requested level not found" for the failed ones; treat
    #     "level loaded" as authoritative even when some attempts failed.
    smoke_log=/tmp/tier9-launcher-smoke.log
    info "smoke: starting GameLauncher with 30s timeout"
    timeout 30s "$launcher_bin" \
        --project-path="$MPSAMPLE_DIR" \
        --regset="/Amazon/AzCore/Bootstrap/sys_PakPriority=1" \
        --regset="/O3DE/Autoexec/ConsoleCommands/bg_ConnectToAssetProcessor=0" \
        >"$smoke_log" 2>&1
    smoke_exit=$?
    game_log="$MPSAMPLE_DIR/user/log/Game.log"
    if [ -f "$game_log" ]; then
        log_to_check="$game_log"
    else
        log_to_check="$smoke_log"
    fi
    if grep -qE "Critical Error|Critical:|Assertion failed|Segmentation fault|core dumped|panic\(\)" "$log_to_check"; then
        nope "GameLauncher smoke" "crash/assertion markers in log (see $log_to_check)"
    elif grep -qE "Game Level Load Time:" "$log_to_check"; then
        level=$(grep "Game Level Load Time:" "$log_to_check" | grep -oE 'Levels/[^ ]+\.spawnable' | head -1)
        ok "GameLauncher loaded $level"
    elif grep -qE "Requested level not found" "$log_to_check"; then
        nope "GameLauncher smoke" "no level loaded; explicit not-found error in log (see $log_to_check)"
    elif [ "$smoke_exit" -eq 124 ] || [ "$smoke_exit" -eq 0 ]; then
        nope "GameLauncher smoke" "no level-load marker within 30s (see $log_to_check)"
    else
        nope "GameLauncher smoke" "exit=$smoke_exit (likely init failure, see $log_to_check)"
        tail -30 "$log_to_check"
    fi
fi

# ─── Summary ────────────────────────────────────────────────────────────────
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
