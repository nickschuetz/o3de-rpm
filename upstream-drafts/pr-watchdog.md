# PR: AssetBuilder: add child-side parent-death watchdog

**Branch:** `nickschuetz/o3de:assetbuilder-parent-death-watchdog`
**Target:** `o3de/o3de:development`
**File touched:** `Code/Tools/AssetProcessor/AssetBuilder/main.cpp` (+49 lines)
**Single commit:** DCO-signed

## Title (for the PR form)

`AssetBuilder: add child-side parent-death watchdog`

## Body (paste into PR description)

When AssetProcessor dies (crash, SIGKILL, ungraceful shutdown), the resident AssetBuilders it previously spawned get reparented to PID 1 (or the user's systemd instance) and keep running indefinitely. Each AP restart spawns a fresh resident pool without adopting the orphans, so they accumulate across restarts -- roughly 300 MB RSS each, plus held file descriptors and shared-memory segments.

This patch addresses the symptom by adding a small detached watchdog thread to AssetBuilder's `main()`. The thread polls `getppid()` every 2 seconds; when the parent PID changes (we've been reparented), the builder calls `_exit(0)`. Independent of any threading-model assumptions on the AP side; ~12 LOC; negligible runtime cost.

POSIX (Linux + Mac) implementation only. The same orphan-lifetime bug exists on Windows but the appropriate mechanism differs (`OpenProcess(PROCESS_SYNCHRONIZE) + WaitForSingleObject` on a parent process handle in the watchdog thread). A Windows port can follow as a separate change.

### Why not `m_tetherLifetime = true`

The engine's existing `m_tetherLifetime` mechanism on Linux uses `prctl(PR_SET_PDEATHSIG, SIGTERM)`. Per `prctl(2)`, that signal fires when the **THREAD that called `fork()`** terminates, not when the parent process terminates. AssetProcessor's `BuilderManager::LaunchProcess` is called from short-lived TaskWorker threads that retire immediately after the spawn returns -- so setting `m_tetherLifetime = true` causes the kernel to SIGTERM every freshly-spawned builder within milliseconds of `fork()`. We verified this empirically.

The structural fix (refactor BuilderManager to spawn from a long-lived thread) is tracked in a separate design issue (link TBD). The watchdog here is the focused, low-risk fix for the user-visible orphan symptom; it composes cleanly with any future BuilderManager refactor.

### Reproduction (without this patch)

1. Open Editor in a project; let AP spawn its resident builder pool.
2. `kill -9 <AssetProcessor-pid>`
3. `ps -o pid,ppid,comm -C AssetBuilder`

Before this patch: resident AssetBuilders persist with PPID 1 (or the user systemd PID) and keep running until manually killed.

After this patch: resident AssetBuilders detect the reparenting within 2 seconds and exit cleanly. `ps` shows zero AssetBuilder processes with non-AP parents.

### Risk assessment

- One detached thread per AssetBuilder process. Sleeps 2 seconds between checks; CPU cost is rounding error.
- 2-second max orphan lifetime is acceptable for the orphan-cleanup use case.
- Behavior on standalone launch (parent is shell or systemd-user): watchdog detects shell exit and exits with it -- intuitive.
- Behavior on AP launch (parent is AP): watchdog stays idle until AP dies.
- Behavior on launch with `parentAtStartup <= 1` (e.g., launched by init directly, unusual): watchdog skips entirely, so we don't self-exit immediately.
- `_exit(0)` is used (not `exit()`) to skip C++ destructors -- the builder's parent has already died, no point in graceful teardown.

### Test plan

1. Build green on Linux + Mac.
2. Open Editor in a project (PM -> Open Editor). Confirm resident builder pool spawns normally.
3. `kill -9 <AssetProcessor-pid>`. Confirm builder pool exits within 2-3 seconds (`ps -C AssetBuilder` returns no rows).
4. Clean-shutdown regression: close Editor normally. Confirm builders shut down via the existing IPC shutdown path with no errors, no premature watchdog firing.
