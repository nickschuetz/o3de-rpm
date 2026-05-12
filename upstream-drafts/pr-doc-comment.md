# PR: ProcessWatcher: document prctl(PR_SET_PDEATHSIG) threading constraint

**Branch:** `nickschuetz/o3de:processwatcher-pdeathsig-doc`
**Target:** `o3de/o3de:development`
**File touched:** `Code/Framework/AzFramework/Platform/Linux/AzFramework/Process/ProcessWatcher_Linux.cpp` (+24 lines comment)
**Single commit:** DCO-signed, doc-only change

## Title (for the PR form)

`ProcessWatcher: document prctl(PR_SET_PDEATHSIG) threading constraint`

## Body (paste into PR description)

`processLaunchInfo.m_tetherLifetime = true` triggers `prctl(PR_SET_PDEATHSIG, SIGTERM)` in the child. Per `prctl(2)`, that signal fires when the THREAD that called `fork()` terminates, not when the parent PROCESS terminates -- a subtle distinction that's easy to miss when reading just the engine API surface.

Consumers that invoke `LaunchProcess` from a short-lived thread (task pool, QRunnable, `std::async`, etc.) will have their freshly-spawned child SIGTERM'd within milliseconds of `fork()`, as the launching thread retires immediately after the spawn returns.

This was missed when AssetProcessor's `BuilderManager` was tested with `m_tetherLifetime = true` enabled: BuilderManager forks builders from TaskWorker pool threads that retire immediately, and every spawned AssetBuilder got SIGTERM'd within ~21 ms of fork. (Tracked separately; see linked issue.)

This change adds a 20-line warning comment next to the `prctl` call documenting the precondition, the symptom pattern when it's violated, and pointing future callers at the child-side watchdog pattern as an alternative.

Doc-only change; no behavior change.

### Test plan

- Verify the file still compiles on Linux. (No code change; should be trivial.)
- Verify the existing m_tetherLifetime call sites (currently just the Multiplayer gem) are unaffected.

### Companion changes

This is the smallest, lowest-risk piece of a three-PR cluster addressing the AssetBuilder orphan bug:

- **(This PR)** Doc comment on the prctl threading constraint.
- **`assetbuilder-parent-death-watchdog`** Child-side parent-death watchdog in AssetBuilder's main() that prevents orphan accumulation, independent of the launching thread's lifetime.
- **(Issue, not PR yet)** BuilderManager refactor to fork from a dedicated long-lived spawn thread, which would also re-enable `m_tetherLifetime = true` correctly.

The three pieces compose. This doc comment is independently useful even if the other two never land.
