# BuilderManager forks AssetBuilders from short-lived TaskWorker threads, silently breaking m_tetherLifetime

## Summary

`AssetProcessor::Builder::LaunchProcess` (Code/Tools/AssetProcessor/native/utilities/Builder.cpp) is invoked from short-lived BuilderManager worker threads. This silently breaks any caller-side use of `processLaunchInfo.m_tetherLifetime = true`, because the underlying Linux mechanism (`prctl(PR_SET_PDEATHSIG)`) binds the death signal to the **forking thread's TID**, not the parent process. The launching worker thread retires immediately after returning from `LaunchProcess`, and the kernel SIGTERMs the freshly-spawned AssetBuilder within milliseconds.

This is a latent architectural issue that surfaces as soon as anyone tries to use the engine's existing `m_tetherLifetime` API from AssetProcessor's spawn path. Today no AssetProcessor code sets `m_tetherLifetime = true`, so the issue is invisible -- but as a result, AssetBuilders that survive an AssetProcessor crash get reparented to PID 1 (or systemd-user) and run forever, accumulating across AP restarts.

## Reproduction (orphan symptom, current trunk)

1. Open Editor against any project; let AP spawn its resident builder pool (8+ live AssetBuilders parented to the AP PID).
2. `kill -9 <AssetProcessor-pid>` (simulates a crash, bypasses clean-shutdown IPC).
3. `ps -o pid,ppid,comm -C AssetBuilder` -- the residents persist with PPID 1 (or the user systemd PID on user-systemd setups) and continue running indefinitely.

Each orphan consumes ~300 MB RSS, plus held file descriptors and shared-memory segments. Across a typical workflow (Editor crash recoveries, AP-restart cycles), 15+ orphans can accumulate in a single hour-long session.

## Reproduction (`m_tetherLifetime` failure, with one-line tether enabled)

Set `processLaunchInfo.m_tetherLifetime = true;` in `Builder::LaunchProcess`. Rebuild. On first run, every AssetBuilder receives SIGTERM within ~21 ms of spawn:

```
ProcessWatcher: Child process id <PID> terminated prematurely (signal 15)
BuilderManager: Lost connection to builder <UUID>
```

AP can never establish its resident pool; Editor hangs indefinitely at "Asset Processor working..."

## Root cause

From `prctl(2)`:

> PR_SET_PDEATHSIG (since Linux 2.1.57)
>     Warning: the "parent" in this case is considered to be the thread that created this process using fork(2). In other words, the signal is sent when the thread terminates, not when the entire parent process terminates.

So `PR_SET_PDEATHSIG` is fundamentally about the **forking thread's lifetime**, not the parent process's lifetime. The kernel sends the death signal as soon as that specific TID exits.

Today's `m_tetherLifetime = true` callers (e.g., the Multiplayer gem at `Gems/Multiplayer/Code/Source/Editor/MultiplayerEditorSystemComponent.cpp`) happen to invoke `LaunchProcess` from a long-lived thread (Editor's main UI thread), so the precondition is met by accident. AssetProcessor's `Builder::LaunchProcess` is called from `BuilderManager` worker threads (TaskWorker pool, QRunnable, etc.) that retire within microseconds of returning the ProcessWatcher to the Builder object -- the precondition is violated, and the freshly-spawned child gets signaled.

This is a footgun in the engine's process-launching API surface: same call, different observable behavior depending on caller threading. It is not documented at the API surface.

## Proposed fix directions

Three escalating levels of change. Each is independently useful; they can land in sequence.

### (a) Documentation -- inline comment at the prctl call site

A 5-line warning block at `Code/Framework/AzFramework/Platform/Linux/AzFramework/Process/ProcessWatcher_Linux.cpp:336` explaining the threading constraint and pointing future callers at a safer alternative. Doesn't fix any current code; prevents future repeats. Near-zero risk, near-zero review cost.

Status: draft PR ready (`processwatcher-pdeathsig-doc` branch).

### (b) Child-side parent-death watchdog in AssetBuilder

Add a small detached thread in `Code/Tools/AssetProcessor/AssetBuilder/main.cpp` that polls `getppid()` every 2 seconds. When the parent PID changes, the builder `_exit(0)`'s cleanly. Independent of the launching thread's lifetime; ~12 LOC; negligible CPU; 2-second max orphan lifetime.

This fixes the user-visible orphan symptom for AssetBuilder specifically, without addressing the structural cause in BuilderManager. POSIX implementation (Linux + Mac); Windows port is similar shape (`OpenProcess(PROCESS_SYNCHRONIZE) + WaitForSingleObject` on a parent handle in the watchdog thread).

Status: draft PR ready (`assetbuilder-parent-death-watchdog` branch).

### (c) BuilderManager refactor -- centralize spawn through a long-lived thread

Refactor BuilderManager to dispatch all `LaunchProcess` calls through a single dedicated launcher thread that exists for the lifetime of BuilderManager. Worker threads enqueue spawn requests onto the launcher thread instead of calling LaunchProcess directly. The launcher thread does the fork and exec, so `prctl(PR_SET_PDEATHSIG)` would track a stable TID and `m_tetherLifetime = true` would work as advertised.

Secondary benefits: centralized spawn logic is easier to debug, monitor, and rate-limit. Better lifecycle tracking and observability. Removes a class of race conditions where parallel workers spawn builders simultaneously.

Estimated scope: 50-100 LOC of refactor in BuilderManager + Builder + adjacent code paths. Touches a hot path during asset processing; would benefit from careful review.

### (d) ProcessLauncher refactor -- replace prctl with a robust mechanism

Even after (c), the underlying API in `ProcessWatcher_Linux.cpp` still has the footgun documented in (a). A future direction: replace `PR_SET_PDEATHSIG` with a mechanism that genuinely tracks the parent process. Two candidates:
- **pidfd** (Linux >= 5.3): `pidfd_open(parent_pid)` returns an FD that becomes readable when the parent dies. The FD survives exec; the child binary can poll it on a watchdog thread. Modern and elegant; requires kernel >= 5.3 (fine for current Fedora / Mac equivalent / supported Windows targets).
- **Internal launcher thread inside ProcessLauncher**: similar idea to (c) but at a lower layer. ProcessLauncher itself spawns a singleton thread that all forks route through. Higher blast radius (affects every `m_tetherLifetime` user).

Significant scope; would want a separate design discussion before implementation.

## Recommended sequence

1. (a) Documentation comment -- can land immediately. Useful for future callers regardless of what we do about (b)/(c)/(d).
2. (b) Watchdog in AssetBuilder -- focused fix for the immediate orphan symptom. Lands quickly; defense-in-depth for any future regressions.
3. (c) BuilderManager refactor -- structural fix once the community converges on direction. (a) + (b) compose well with (c) -- they become belt-and-suspenders rather than redundant.
4. (d) ProcessLauncher refactor -- aspirational; revisit if a second non-AP consumer is observed misusing `m_tetherLifetime`.

## Observability summary (from the original 2026-05-12 investigation)

Without fix: orphan AssetBuilders accumulate across AP restarts. Saw 18 + 3 orphans in two cycles during a single 3-hour ROS2_Project session. Each ~300 MB RSS, holding FDs and shared memory.

With (b) child-side watchdog: orphans get reaped within 2 seconds of AP death. Verified with `kill -9 <AP-pid>; ps -o pid,ppid,comm -C AssetBuilder` showing zero non-AP-parented builders after the polling interval.

(Caveat: (c) was not exercised in the 2026-05-12 investigation; the watchdog is sufficient to verify the symptom is gone.)
