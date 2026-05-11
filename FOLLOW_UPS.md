# Follow-ups & state-of-play

End-of-day capture: what landed, what's pending, what's loaded for next session.

This file is intentionally a living scratchpad. Entries get added or removed as work progresses. Promote anything tracker-worthy to `FEDORA_ROADMAP.md`, a GitHub issue, or a memory note. Anything below that's gone stale by the time you read it can be deleted.

---

## 2026-05-11 late afternoon -- Mike-C feedback + Tier 7 deeper reframe + Qt 6 PR tracking

### Mike-C feedback from 2026-05-07 (caught up 2026-05-11)

Mike posted to Discord on 5/7 with three observations testing the then-current stabilization build. Surfaced late; addressed:

1. **`libAzGameFramework.a` missing during native project build.** Downstream of #3 below. The static archive lives in `o3de2605-devel` subpackage (carved out 2026-05-04 via commit `285d924`). When the COPR Pulp CDN bug bailed his `o3de2605-devel` install mid-stream, the .so's and runtime tooling landed but the .a's never did. Resolution path: in-flight build **10444167** (12-pack stabilization promotion, due ~5h from 2026-05-11 mid-afternoon) will publish a fresh artifact to Pulp, regenerating the metadata and resolving the Content-Length inconsistency naturally. Mike doesn't need to do anything except retry `sudo dnf install o3de2605-devel` after the new build lands.

2. **CMake bundling question** (he noted Project Manager downloaded bundled CMake 4.2.3 but our path `/opt/O3DE/26.05.0/cmake/runtime/` is empty; asked if removed for licensing). Answer: no, BSD-3-Clause -- not licensing. Per Fedora packaging guideline 12 ("don't bundle libraries Fedora ships"), we depend on system CMake via `Recommends: cmake`. The empty `cmake/runtime/` tree stays declared as a placeholder for future in case the engine ever pins a patched CMake; today engine just uses whichever cmake is on PATH. Spec comment is accurate.

3. **COPR Pulp CDN Content-Length inconsistency** (501,315,746 advertised vs 501,182,865 in repodata for o3de2605-devel). Pulp/S3 storage-layer bug on COPR's side; not our packaging. Retry sometimes clears it; the in-flight build above will give Pulp a fresh artifact to regenerate metadata against.

Side note from the same investigation: o3de2605-devel is ~500MB compressed (~4GB expanded; 178 static archives). Only relevant for native C++ Gem development against engine internals -- end users running games or Lua/ScriptCanvas project authors don't need it. Worth noting in user docs at some point.

### Tier 7 deeper reframe (post `--scanfolders` experiment)

Earlier today's `--scanfolders=$ENGINE_PATH/Gems` fix (commit `832689e`) was validated against the failing run and didn't actually fix it. Cold log analysis revealed the deeper truth: even a single-file cube.fbx bake through SceneAPI declares a `JobDependency` on `DefaultVertexBufferPool.resourcepool`, which transitively requires shaders + SRG merge + Atom RPI gem. The empty scratch project can't satisfy that dep chain. Adding engine Gems to scan folders made it worse (600 engine-asset bakes failed for the same chain reasons, drowning out the cube.fbx signal).

**Implication**: the original Tier 7 test premise ("single-file scratch project that just exercises assimp's import path") was conceptually wrong. FBX -> azmodel through SceneAPI is NOT standalone from the Atom rendering pipeline.

`--scanfolders` change reverted. Test script stays in tree as a known-broken record of the dep-chain finding. Real fix options documented in updated `project_tier7_cold_cache_quirk.md`:
- **(a)** Skip AP entirely; test assimp at C++ API level (compile small binary against system_assimp, assert mesh count etc.). Recommended.
- **(b)** Use AutomatedTesting project structure (heavy; touches whole engine asset library).
- **(c)** Drop Tier 7 entirely.

Tier 7 cron stays OFF; rebuild won't happen until (a)-style direct-assimp test is implemented. This is a fundamental redesign, NOT a quick fix; defer until next sprint.

### Qt 6 tracking now includes PR #19567

User pointed at PR [o3de/o3de#19567](https://github.com/o3de/o3de/pull/19567) -- this is the actual merge candidate (qt6 -> development). Updated `tools/check-deps-drift.py` to also track PR state in the drift report's "Upstream migration tracking" section. Drift report now shows:

```
| #19567 | OPEN | 57d | 1662 | +2547/-5075 | development | qt6 | Linux-Profile=SUCCESS / Linux-Asset=FAILURE |
```

**Key insight from PR scope review**: Linux-Profile builds GREEN on Qt 6.10.2. Engine compiles cleanly on Linux against vanilla Qt 6 -- empirical proof that `system_qt6` Stage 1 swap is feasible the day this PR merges. Mac-Profile + Windows-Profile + Windows-Release all FAIL (Mac toolchain + Windows VS2019 -> 2022 toolset bump issues). PySide2 not yet migrated (major author-flagged blocker). AP/APB hangs on exit (caught by nick-l-o3de 2026-02-18).

Stalled since 2026-03-14; nick-l-o3de's earlier "hold merging until stabilization/26050 is cut" gate is long since released (26050 cut weeks ago). PR is now just waiting on review + work bandwidth.

### Other items wrapped this session

- **Tier 7 actual fix attempt** -- reverted (didn't work; see above).
- **`make srpm-snapshot-qt6` smoke test** -- caught 2 infra bugs (cd-scoping in Makefile + %global override in spec); both fixed. SRPM now generates end-to-end against the qt6 branch tip.
- **Cruft cleanup** -- deleted PhysX + aws-gamelift-server-sdk from o3de-dependencies (engine no longer references either).
- **ISPCTexComp drift fix** -- rebuilt from commit 36b80aa (the engine-pinned source) instead of 691513b. Build 10444466 GREEN on F44+rawhide.
- **Drift report `bundled-exception` classification** -- 5 documented bundles (OpenSSL/openimageio-opencolorio/pyside2/squish-ccr/vulkan-validationlayers) moved out of "gap" bucket. Drift report now: 0 gap, 0 minor-drift, 2 out-of-date (ISPCTexComp resolving + Qt intentional).

---

## 2026-05-11 afternoon -- F44 consolidation session + Qt 6 strategic clarification

After pausing CS10, ran four-track F44 hardening:

1. **Tier 7 root-cause investigation: ✓ DONE.** Reframed the failure -- not a parallel-jobs SRG-merge race, but a **scan-folder configuration** problem. Test scratch project doesn't include `/opt/O3DE/26.05.0/Gems/` in its scan folders, so `MergeShaderResourceGroupAsset`'s outputs (viewsrg.srgi, scenesrg.srgi) are invisible to `ShaderAssetBuilder`. The `--regset maxJobs=1` validation experiment failed and was reverted (commit `705ea99`). Memory notes `project_tier7_cold_cache_quirk.md` + `project_tier7_serial_pass_option.md` reframed with the corrected understanding. Workflow updated to upload BOTH cold + warm AP logs (`f0ac388`). Actual fix scope (next item in queue, not yet started): pass `--scanfolders=$ENGINE_PATH/Gems` to AP in `tests/asset-bake-test.sh:run_ap_pass()`. Bonus finding from same investigation: SQLite header/library version mismatch produces three `Trace::Assert` blocks at AP startup (system_sqlite swap firing SQLite's built-in version-sanity check). Non-fatal; low priority noise.

2. **Stabilization 7-pack -> 12-pack promotion: ✓ APPLIED + VALIDATING.** o3de-stabilization F44 + rawhide chroots extended from 8 with_opts to 13 (added system_assimp + system_libsamplerate + system_lua + system_poly2tri + system_sqlite). New SRPM_STABILIZATION_FLAGS list in Makefile mirrors the chroot config. Build **10444167** queued (F44+rawhide; CS10 untouched per pause). ETA ~5h each chroot. Will land the 12-pack for community testers if green; rollback is just reverting the chroot edit.

3. **Qt 5.15.1 -> 5.15.2-rev9 rebuild: RETIRED-as-DEAD-WORK.** Investigation revealed the rev9 source isn't published anywhere (only as a binary on packages.o3de.org), so "rebuild" isn't mechanical. Bigger picture: engine team's strategic direction is Qt 6 for 26.10.0, NOT improving Qt 5. Don't invest in o3de-qt5 anymore. See "Qt 6 migration tracking" entry below for the forward plan.

4. **system_googlebenchmark activation: ✓ APPLIED + VALIDATING.** Plumbing landed 2026-05-08 (bcond+Source+Find shim) but was OFF; today's activation adds `--with system_googlebenchmark` to SRPM_EXPERIMENTAL_FLAGS + experimental chroot. Engine still ships AzTest+AzTestRunner+gbench unconditionally (architecturally correct shape per closed PR #19738 redirect); linkage now pulls Fedora's `google-benchmark-devel`. Build **10444166** queued (F44+rawhide). ETA ~5h each. Validates the 18-pack stack in one go.

Reference state at end of session: HEAD `f0ac388` ("test(tier7): upload both cold + warm AP logs..."). Spec changelog `2605.0-47`.

### Builds in flight (overnight)
- 10444166 (experimental F44+rawhide, 18-pack incl. googlebenchmark)
- 10444167 (stabilization F44+rawhide, 12-pack promotion)

---

## Upstream PR status (2026-05-11 refresh)

- **#19733 (AzCore Lua include cleanup)** -- MERGED 2026-05-08 by nick-l-o3de. Our Patch0008 becomes redundant on next snapshot rebase.
- **#19734 (libtiff C99 typedefs)** -- MERGED 2026-05-08 by nick-l-o3de. Our Patch0007 becomes redundant on next snapshot rebase.
- **#19737 (Microphone libsamplerate PAL-trait gate)** -- **MERGED 2026-05-10 by nick-l-o3de.** When we pull a fresh snapshot from development (or once stabilization/26050 cherry-picks it forward), our local Microphone-related patch hunks become redundant. Action: audit local patches against the merged PR on next snapshot rebase. Three of three upstream PRs this cycle now merged.
- **#19738 (googlebenchmark gate on LY_DISABLE_TEST_MODULES)** -- CLOSED 2026-05-08 (architecturally wrong premise per nick-l-o3de). Replaced by today's system_googlebenchmark Stage 1 swap activation (build 10444166).
- **#19740 (libbenchmark.a missing from engine install set)** -- filed as upstream issue 2026-05-08; awaiting volunteer pickup. Memory note `project_az_test_runner_architecture.md`. Not blocking on us.
- **#19743 (AP minimal-scope flag request)** -- filed as upstream discussion-quality issue 2026-05-11. Documents the empty-scratch-project workflow gap surfaced by today's Tier 7 investigation (cube.fbx declares JobDependency on `DefaultVertexBufferPool.resourcepool` -> transitively needs full Atom RPI gem registration; AP has no `--single-asset` / `--minimal-scope` flag to break the chain). Awaiting engine-team feedback on API shape; happy to contribute implementation once design settled. Resolution unlocks proper Tier 7 SceneAPI-integration coverage (current Tier 7 is library-health only).

---

## Qt 6 migration tracking (planned for 26.10.0; NOT guaranteed)

Replaces the retired "Qt 5.15.1 -> 5.15.2-rev9 rebuild" item with the actual strategic shape.

**Upstream tracking links**:
- **Feature request**: [o3de/o3de#19081](https://github.com/o3de/o3de/issues/19081) -- "Upgrate O3DE tools to QT6", OPEN, priority/major (sig/content + feature/editor + feature-need/important-soon).
- **Engine PR**: [o3de/o3de#19567](https://github.com/o3de/o3de/pull/19567) -- "Build against Qt 6.10.2", OPEN, base=development head=qt6, last activity 2026-03-14. The actual merge candidate for the qt6 branch.
- **3p side**: [o3de/3p-package-source#293](https://github.com/o3de/3p-package-source/pull/293) -- "Update from QT5.15 to QT6.10.2" -- **MERGED 2026-02-13 by sptramer.** Recipe for Qt 6.10.2 builds is now upstream.
- **Engine branches** (TWO of them now):
  - `o3de/o3de:qt6` at HEAD `b74cbc8` (2026-03-10). 19 commits ahead of development, 36 commits behind, ~300 files changed. Main Qt 6 work.
  - `o3de/o3de:qt6_pyside` at HEAD `719eb73` (2026-03-14). 5 commits ahead of `qt6`, 0 behind. PySide6 migration sub-branch off qt6 -- the work that addresses PR #19567's "PySide2 not yet migrated" blocker. Author-flagged WIP (`(WIP) cmake package change` is the last commit message); no PR open yet.
- **Discord thread**: https://discord.com/channels/805939474655346758/1420144310908616725 -- "QT6 Support" thread in O3DE Foundation Discord's `gems-and-features` channel. Opened by Guillaume [Cloud Imperium] 2025-09-23 with initial status: Windows+Linux "builds and launches, needs deep testing"; Mac "will build soon". Tracked manually (Claude can't access Discord); valuable for status updates between commit/PR activity windows.
- **Linked discussion**: [o3de/o3de#14940](https://github.com/o3de/o3de/discussions/14940) -- closed; 2025-era community offer of Qt 6.3.2 work from a 22.05 branch fork.

**Activity timeline**: substantive work happened in two waves (Sept 2025 = initial Linux/Windows runtime; Feb-Mar 2026 = PR opened + 3p recipe merged + PySide branch started). Idle since 2026-03-14 (~2 months as of 2026-05-11). The "hold merging until stabilization/26050 cut" gate from nick-l-o3de 2026-02-17 is long since released.

**Critical for packaging**: Qt 6 will be **VANILLA** (no custom O3DE patches). PR #293's description states *"Nothing, we are using vanilla QT. In the process, we are nuking the custom changes"*. The Qt 5.15 fork's load-bearing patches (PropagateStyleToChildren / ManualStyleSheet / tooltip layouting / TIFF support / tree-view expand) are being dropped, not forward-ported. Means: when Qt 6 migration lands, **Fedora's system qt6 packages CAN substitute** -- the entire `o3de-qt5` bundle (101MB tarball, multi-hour build) can be retired in favor of `BuildRequires: qt6-qtbase-devel qt6-qttools-devel qt6-qtsvg-devel ...` + `system_qt6` Stage 1 swap.

**Volunteer-project caveat**: 26.10.0 (fall 2026 stable release) is the goal date, but O3DE is open-source volunteer work. The qt6 branch hasn't received commits since 2026-03-10 -- two months of inactivity. There's a real-but-low chance Qt 6 slips past 26.10.0. **Don't preemptively retire o3de-qt5 packaging.** Wait for empirical merge to development + stabilization/26100 cutover before drafting `system_qt6`.

**Action items (in order)**:
1. **Nothing right now.** Engine team owns the qt6 branch merge cadence; packaging-side work is contingent on that.
2. **When stabilization/26100 branch is cut** (typical cadence: ~3-4 months before stable release, so likely mid-July 2026): inspect `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` on the stabilization branch. If `qt-6.10.2-*-linux`: draft system_qt6 swap. If still `qt-5.15.2-rev9-linux`: Qt 6 slipped; keep o3de-qt5 for one more cycle and revisit for 27.05.x.
3. **Adjacent: PySide6** migration. PR #19361 (Component Creation Class Wizard Expansion) introduces PySide6 dependency. Same shape as Qt 6 -- F44 ships `python3-pyside6`; retire bundled `pyside2-5.15.2.1-py3.10-rev7` when engine migrates.

**Why Qt 6 didn't make 26.05.0** (referenced from the curious question 2026-05-11): timing + scope. The qt6 branch had its substantive activity Jan-Mar 2026; stabilization/26050 was cut ~Feb 2026 (typical 3-month-before-release cadence) and the qt6 work missed that cutoff. The 300-file / 19-commit scope plus 35-commit-behind rebase backlog plus the cross-platform validation cycles (Mac still pins 5.15.2-rev8 in 3p build_config; Mac path lags Linux/Windows) compound. Volunteer cadence means PR #293 merged in February and then nothing has driven the qt6 engine-branch forward since March. Memory note `project_o3de_bundles_custom_qt.md` documents the migration plan + cautions.

---

## CS10 (CentOS Stream 10) -- PAUSED 2026-05-11

CS10 chroot pivot effort started 2026-05-08, paused 2026-05-11 to consolidate on F44 + rawhide first.

**Why paused:** The remaining CS10 work isn't bounded. `ispc` (Intel SPMD compiler) has no `epel10` branch in Fedora -- ISPCTexComp can't be built on CS10 without either us packaging ispc ourselves (significant scope creep) or adding an engine-side cmake gate. The heavier deps (Qt5, PhysX, AWSNativeSDK) haven't been CS10-tested and likely surface their own per-spec quirks. F44 + rawhide just went green end-to-end yesterday on the full 14-pack + Patch0010 + Patch0011 stack (build 10442708); that foundation should harden before splitting attention. Tier 7 still fails on F44 + rawhide (the `--regset maxJobs=1` hypothesis was wrong -- see `project_tier7_serial_pass_option.md`); that's a higher-leverage F44 win than CS10 grinding.

**Stance**: leave the CS10 chroots configured but stop submitting to them. Nothing gets torn down; nothing gets added. The work that landed is correct and harmless; it just sits idle.

**What landed that's keeper-state (do NOT revert)**:
- All 4 engine COPR projects + o3de-dependencies have `centos-stream-10-x86_64` chroot enabled. Empty + idle is fine.
- `o3de-experimental` CS10 chroot has the full 17 with_opts + EPEL-10 + o3de-dependencies repo wired. Will be picked up unchanged when CS10 work resumes.
- Spec-side: o3de.spec round-1 + round-2 escape fixes (2605.0-45 + 2605.0-46), Makefile timeout bump to 8h (28800s). All behavior-preserving on F44/rawhide.
- mcpp PoC rev10 (debug_package + bulk escape), dxc-spirv PoC rev14 (prophylactic escape). Both have CS10-green RPMs in o3de-dependencies.
- 5 CS10-green dep RPMs in o3de-dependencies: mikkelsen, azslc, astc-encoder, aws-iot-device-sdk-cpp-v2, aws-gamelift-server-sdk (built 2026-05-11 from F44 SRPMs).

**What's known-blocked when we resume**:
- ISPCTexComp CS10 build needs `ispc` for EL10. No upstream solution. Resume options:
  - (a) Package ispc ourselves in `hellaenergy/o3de-dependencies` as a CS10-targeted SRPM.
  - (b) Engine-side cmake gate to skip ISPCTexComp on CS10 builds.
  - (c) Drop CS10 support indefinitely if neither (a) nor (b) lands.
- Qt5 + PhysX + AWSNativeSDK haven't been CS10-built yet. Multi-hour each.
- Engine compile on CS10 has never reached the build phase (always blocked at BR resolution so far). Once deps are sorted, expect to surface clang 19 vs F44's clang 21 diagnostic differences and libstdc++ 14.3 vs 15.x deprecation deltas.

**Resume-from-here ledger**: memory notes `project_cs10_engine_build_blockers.md` (incremental discovery list), `project_cs10_with_opts_gap.md` (chroot config fix recipe -- already applied; documents the gotcha for future chroot additions), `project_cs10_debuginfo_quirk.md` (the two known RPM 4.19 quirks + escape pattern).

**Resume conditions** (any one is enough to revisit):
- An external user requests CS10 / RHEL 10 support (would shift priority from speculative to real-demand).
- F44 + rawhide are at a stable "no critical pending work" state (Tier 7 fixed, stabilization channel at 12-pack or 14-pack, drift items at zero, upstream PR backlog cleared).
- ispc lands an `epel10` branch in Fedora (eliminates the biggest unbounded chunk).

---

## End-of-day 2026-05-10 -- what landed

Short evening session focused on diagnosing build 10439258 (the post-Patch0011 validation rebuild) and clearing the next round of blockers.

### Build 10439258 outcome (the post-Patch0011 validation rebuild)

Mixed result with one new gotcha:

- **F44 chroot**: ran 5h02m, **engine compiled fully**, packaging emitted Provides/Requires for both `o3de2605` and `o3de2605-devel` subpackages, killed at the final `Checking for unpackaged file(s)` step by the COPR default 5h wall-clock timeout (`!! Copr timeout => sending INT`). Build essentially "done" -- binaries were generated, just couldn't finish RPM finalization. Underlying cause: Makefile passes `--timeout 25200` (7h) but the rebuild was submitted via raw copr-cli without the flag, defaulting to 5h (18000s) and being killed at 18141s.
- **rawhide chroot**: same 5h timeout pattern; same compiled-fully + packaging-emitted state. Crucially, the Requires list shows `liblua-5.5.so` -- meaning **Patch0010 + Patch0011 cleared all Lua 5.5 sites and the engine compiled clean on Lua 5.5**. No third break site emerged.
- **CS10 chroot**: failed at SRPM-prep in 134s with a NEW RPM 4.19 quirk -- `error: line 1087: second %install`. Different from the mcpp debuginfo quirk caught on 2026-05-08. Root cause: the o3de.spec had a comment inside the `%install` block reading `# Per-version mutation lands here at %install time:` -- RPM 4.19 (CS10) parses the unescaped literal `%install` token inside that comment as a section-start marker; RPM 6.x (F44 + rawhide) ignores it.

### Fixes landed today

- **CS10 spec quirk fix** (commit `d889edb`) -- rephrased the line-1087 comment to drop the percent sign + added an inline note documenting the RPM 4.19 quirk so future edits don't reintroduce it. Swept the rest of the active `%install` block: no other comments in that block contain the token, so the fix is local. Other `%install` references elsewhere in o3de.spec (lines 455, 524, the changelog) sit outside the active `%install` block and are unaffected by the parser bug.
- **Makefile COPR timeout bump 25200 -> 28800** (same commit) -- 8h ceiling for all four `copr-cli build` invocations (stable / snapshot / stabilization / experimental) + the internal `_copr-and-test` helper. F44's empirical 5h02m baseline + rawhide's typical 10-30% slowdown could overflow even 7h on a worst-case run; 8h gives usable headroom for rawhide AND CS10 (CS10 build time unknown until first end-to-end run completes). Updated the inline comment block explaining the choice.
- **Validation rebuild submitted as build 10442708** (o3de-experimental, all 3 chroots, 8h timeout). https://copr.fedorainfracloud.org/coprs/build/10442708 -- expected to land sometime overnight depending on rawhide + CS10 compile times.

### Lua 5.5 break-site pre-flight audit (concluded: Patch0010 + Patch0011 are sufficient)

Per the existing `project_lua_5_5_newstate_break.md` memory note's hedge ("there may be MORE Lua 5.5 break sites we haven't tripped on yet"), ran the recommended comprehensive grep against `o3de/development @ 706cd0f3` (head of upstream development) to enumerate ALL potential Lua 5.5 break sites prophylactically:

- `LUA_NUMTAGS`: exactly 2 sites, both in `Code/Tools/LuaIDE/Source/LUA/WatchesPanel.cpp:834,838`. **Both covered by Patch0011.**
- `lua_newstate`: exactly 1 site in `Code/Framework/AzCore/AzCore/Script/ScriptContext.cpp:4360`. **Covered by Patch0010.**
- Other Lua 5.5-vulnerable symbols swept (`luaL_register`, `lua_open`, `lua_resume`, `LUAI_FUNC`): zero hits across `Code/` + `Gems/`.

Conclusion matches the empirical evidence (rawhide compiled the full engine in 10439258 with `liblua-5.5.so` linkage). **No Patch0012 needed.** The "may be MORE sites" hedge in the memory note can retire when next updated. If a future engine snapshot adds new Lua surface area, re-run the same grep before assuming the patches are still complete.

### Stage 2 dep spec sweep (CS10 quirks)

Swept the three Stage 2 dep specs (`o3de2605-mcpp-az`, `o3de2605-dxc-spirv`, `o3de2605-spirv-cross`) for the `%install`-in-comment pattern that broke o3de.spec on CS10: **all three clean** (none contain `%install` text inside their `%install` blocks). The o3de engine spec was unique in having that comment.

Separately applied the known mcpp `%global debug_package %{nil}` fix per memory note `project_cs10_debuginfo_quirk.md`:

- **mcpp rev9 spec change**: added `%global debug_package %{nil}` near the top with an inline comment explaining the RPM 4.19 vs RPM 6.x asymmetry. Bumped `mcpp_pkgrev` to rev9 + added a changelog entry.
- **mcpp rev9 SRPM built** at `/home/nschuetz/o3de2605-mcpp-az-poc/o3de2605-mcpp-az-2.7.2-1.rev9.fc44.src.rpm`.
- **CS10-only mcpp validation build submitted as build 10442715** (`o3de-dependencies`, CS10 chroot only via `-r centos-stream-10-x86_64`). Should complete in ~2-3 min and either confirm the debug_package fix works, or surface the next CS10 quirk. Independent of the engine build so doesn't compete for builder slots. https://copr.fedorainfracloud.org/coprs/build/10442715

If mcpp rev9 builds clean on CS10, the same `%global debug_package %{nil}` macro can be propagated prophylactically to `o3de2605-spirv-cross` and `o3de2605-dxc-spirv` specs as belt-and-suspenders before their first CS10 build attempts (currently only mcpp has had a CS10 attempt; spirv-cross's CS10 result on 2026-05-08 was a different non-debuginfo SRPM, so debuginfo quirk wasn't tested there yet).

### Other notes

- The `o3de2605-devel` subpackage split appears to have landed at some point during 2026-05-08's work; confirmed by 10439258's packaging output showing both `o3de2605` and `o3de2605-devel` Provides lists. Not in scope for this session's investigation; flagged here for visibility.
- The mcpp PoC working tree's git history doesn't include the rev6-rev8 commits (those were spec edits without local commits). Today's rev9 edit also not committed to the PoC's local git -- pure SRPM build + COPR submit. If the PoC eventually graduates to a real repo, the changelog entries in the spec ARE the canonical history.

### Reference state at end-of-day 2026-05-10

- **HEAD on main**: `7a31d01` ("fix(cs10): bulk-escape ALL section-keyword tokens in o3de.spec comments/changelog (round 2)")
- **Spec changelog**: `2605.0-46`
- **Active in `o3de-experimental` chroot config**: still 17 with_opts entries (snapshot + stabilization + 12 Stage 1 + 3 Stage 2)
- **Builds in flight overnight**:
  - 10442708 (engine validation, all 3 chroots, ORIGINAL post-2605.0-45 spec): F44 + rawhide should succeed in ~5-8h; CS10 chroot of THIS build is now known-doomed (will trip at next unescaped section token past line 1087) but not cancelled because F44 + rawhide still produce useful artifacts.
  - 10442734 (engine CS10-only, ROUND-2 escaped spec at 2605.0-46): queued behind 10442708's CS10 slot; will start when capacity opens. First true CS10 engine compile attempt; expected 5-8h.
- **Builds that completed during the session**:
  - 10442715 (mcpp rev9 CS10): FAILED with the second CS10 quirk that drove the round-2 escape work.
  - 10442733 (mcpp rev10 CS10, post-bulk-escape): SUCCEEDED -- empirical proof the bulk-escape fix works.
- **Stage 2 PoC working trees**: paths unchanged. mcpp PoC now at rev10 (debug_package + bulk escape), local git up-to-date with HEAD `8167b9f`. dxc-spirv PoC has the prophylactic escape fix applied (no rev bump yet; HEAD `c62581c`). spirv-cross PoC unchanged (no unescaped section tokens; nothing to fix).

### Memory notes refreshed this session

- `project_lua_5_5_newstate_break.md`: hedge "may be MORE Lua 5.5 sites" retired; comprehensive grep audit at `o3de/development @ 706cd0f3` confirmed Patch0010 + Patch0011 are the complete set. Future engine snapshots should re-run the grep.
- `project_cs10_debuginfo_quirk.md`: renamed + expanded to cover BOTH known CS10/RPM 4.19 quirks (debuginfo double-emission + literal `%install` in comments anywhere). Scope correction: in-comment section tokens trip the parser ANYWHERE in the spec, not just inside the active section block (corrected mid-session after empirical evidence from build 10442715).
- `MEMORY.md` index entries updated for both.

### Autonomous overnight continuation (added 2026-05-10 22:35 CST)

Five more tracks completed after the initial "ALL" go-ahead:

1. **Drift workflow re-triggered** (run 25648396886) -- conclusion: failure (intentional design; red dot surfaces drift items). Issue #9 still surfacing the 5 drift items from 2026-05-08: ISPCTexComp commit drift, qt5 5.15.1 vs .2, AWSNativeSDK .288 vs .361, astc-encoder 3.2 vs 5.3, mikkelsen label-form. Plus 2 cruft (aws-gamelift, PhysX). No new actionable items beyond what we already had.

2. **Stage 2 dep CS10 audit + prophylactic escape**:
   - mcpp PoC: rev10 ✓ GREEN on CS10 (build 10442733). Validated the bulk-escape pattern.
   - dxc-spirv PoC: rev14 in flight as CS10-only (build 10442739, started 22:18 CST, running). Prophylactic escape applied at 4 lines; no debuginfo suppression added yet (large library binaries may warrant debug symbols).
   - spirv-cross PoC: no unescaped tokens; already empirically green on CS10 (build 10438108 from 2026-05-08). No action needed.

3. **CS10 engine source compat pre-flight** (`grep -rn` against `o3de/development @ 706cd0f3`):
   - Zero hits for: C23 reserved-word collisions, OpenSSL 3 deprecated APIs, glibc symbol-version assumptions, boost deps, `<experimental/...>` includes.
   - Engine sets `CMAKE_CXX_STANDARD 20`. Requires clang >= 19 (CS10 boundary).
   - One special handling: clang >= 21 branch for googletest workaround (CS10 won't trigger; harmless).
   - **CS10 toolchain confirmed from build 10442734 dnf logs**: clang version not visible but expected 19+; gcc/libstdc++ 14.3.1 (F44 ships 15.x); glibc 2.39 (F44 ships 2.42); **lua 5.4.8** (Patch0010+0011 are NO-OPS on CS10 -- gated on `LUA_VERSION_NUM >= 505`); openssl 3.5.5.
   - All findings + predictive next-blockers documented in new memory note `project_cs10_engine_build_blockers.md`.

4. **Doc drift identification (NOT updated, only enumerated)**:
   - **Patch0010 + Patch0011 (Lua 5.5 compat) -- ZERO mention in user-facing docs (README, ARCHITECTURE, BUNDLED_LIBRARIES, FEDORA_ROADMAP, CONTRIBUTING).** Major gap. These are the most significant engine-side patches added in the last week.
   - **CS10 chroot -- mentioned in README, CONTRIBUTING, FEDORA_ROADMAP; NOT mentioned in ARCHITECTURE.md or BUNDLED_LIBRARIES.md.** Minor gap.
   - **-devel subpackage + system_googlebenchmark + versioned-major naming**: all well-covered across docs.

5. **Tier 7 design research**:
   - **MAJOR FIND: AssetProcessor supports `--regset` CLI flag** (Code/Tools/AssetProcessor/native/utilities/ApplicationManagerBase.cpp:303).
   - Hypothesis: `AssetProcessorBatch --regset "/Amazon/AssetProcessor/Settings/Jobs/maxJobs=1"` forces serial processing, which should sidestep the cold-cache parallel SRG-merge ordering quirk without ANY engine code change.
   - If validated, Tier 7 can switch from the current two-pass design to a simple single-pass-serialized-on-cold design.
   - Documented as new memory note `project_tier7_serial_pass_option.md` with the predicted validation plan.

### BIG SECONDARY FINDING (caught while investigating 10442734)

**CS10 chroot has empty `with_opts` across all engine COPR projects.** When CS10 chroot was added 2026-05-08, the `--rpmbuild-with` flags didn't propagate; CS10 currently runs builds with all bconds at default (bundled libs, NOT system swaps). This is the inverse-side of the REPLACE-not-append memory rule -- `add-chroot` defaults `with_opts` to empty.

Empirical state (verified 22:30 CST):
- `o3de`: F44=0, CS10=0 (both intentionally clean stable channels; no gap).
- `o3de-snapshot`: F44=0, CS10=0 (same).
- `o3de-stabilization`: F44=8, **CS10=0 (GAP -- 8 flags missing)**.
- `o3de-experimental`: F44=17, **CS10=0 (GAP -- 17 flags missing)**.

This means: **all CS10 build attempts so far have NOT exercised any Stage 1/2 swap.** When CS10 engine compile eventually succeeds, it'll be a bundled-libs validation, not Stage 1/2 validation. Documented in new memory note `project_cs10_with_opts_gap.md` with the fix recipe (copr-cli edit-chroot with the FULL list per chroot, per the REPLACE-not-append rule). NOT auto-fixed -- chroot config edits need your judgment.

### 10442734 progress (the CS10 engine attempt with round-2 spec)

Failed at BR resolution after 147s: `No matching package to install: 'pkgconfig(libunwind)'`. Crucially: **cleared the spec-parse hurdle** -- the round-2 bulk-escape fix works for the engine spec at scale.

`libunwind-devel` exists in EPEL-10 (verified at https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/Packages/l/) but NOT in base CS10 repos. Fix recipe: enable EPEL-10 as an additional_repo on the CS10 chroot config. Per `project_cs10_engine_build_blockers.md`, deferred until your morning review since chroot config is yours to decide.

### Reference state at end-of-autonomous-session 2026-05-10 22:35 CST

- **HEAD on main**: `99fcc38` ("docs(follow-ups): capture round-2 CS10 escape work + mcpp rev10 validation")
- **Spec changelog**: `2605.0-46`
- **Builds in flight (still running overnight)**:
  - 10442708 (engine all 3 chroots, 2605.0-45 spec): F44 + rawhide expected to succeed by morning; CS10 known-doomed at next unescaped token (~3-4 hours wasted CS10 runtime, accepted).
  - 10442739 (dxc-spirv rev14 CS10-only): running ~15+ min so far; first CS10 attempt for this spec, may surface more CS10 quirks.
- **Builds completed during autonomous session**:
  - 10442715 (mcpp rev9 CS10): FAILED -> drove round-2 fix.
  - 10442733 (mcpp rev10 CS10, post-bulk-escape): SUCCEEDED ✓.
  - 10442734 (engine CS10-only, round-2 spec): FAILED at BR-resolution on libunwind-devel; cleared spec-parse ✓.
- **New memory notes (3)**: `project_cs10_with_opts_gap.md`, `project_cs10_engine_build_blockers.md`, `project_tier7_serial_pass_option.md`. All indexed in MEMORY.md.
- **PoC working tree commits (2, local-only, not pushed)**: mcpp `8167b9f` (rev9 + rev10), dxc-spirv `c62581c` (prophylactic escape).

### Morning priority queue

1. **Check 10442708 F44 + rawhide** -- if both succeed, full Stage 1+2 stack is validated on those chroots.
2. **Check 10442739 (dxc-spirv CS10)** -- likely success unless a new CS10-specific issue surfaces for this spec shape.
3. **Decide CS10 chroot config fixes**: enable EPEL-10 + propagate with_opts. Both per-project per-chroot, both require explicit copr-cli invocations with full lists.
4. **Doc drift fixes** if time permits: add Patch0010/0011 mention to BUNDLED_LIBRARIES.md (the natural home); CS10 mention to ARCHITECTURE.md's Mermaid diagram + paragraph.
5. **Tier 7 `--regset` validation**: low-effort experiment; one workflow_dispatch run with `run_asset_bake=true` after manually modifying the test to add `--regset maxJobs=1`. If it works, the cold-cache quirk gets a clean fix.
6. **Stabilization channel still on 7-pack**; community testers untouched. No promotions needed until F44 + rawhide validate clean on 10442708.

---

## End-of-day 2026-05-08 -- what landed

Bigger day than yesterday. Fifteen commits on `main` plus three PoC dirs plus two upstream PRs.

### Stage 1 system swaps (5 added today; engine now consumes 12 system libs)

- **`system_sqlite` activated (10-pack)** -- audit-confirmed cleanest Stage 1 candidate. 29 sqlite3_* symbols all in Fedora 3.51.2; no extension API used. `Findsqlite-system.cmake` mikkelsen-pattern shim sidesteps the runtime-walker side-effect target issue.
- **`system_libsamplerate` activated (11-pack)** -- lowest-risk swap; Linux PAL is a do-nothing None stub so the engine never calls `src_*` at runtime, but the static lib still needs to satisfy the link.
- **`system_assimp` activated (12-pack)** -- 5.4 to 6.0 major bump caveat noted; symbols verified, runtime FBX behavior covered by new Tier 7 `tests/asset-bake-test.sh` (added end-of-day; not yet validated against a live install).
- **`system_spirvcross` activated (Stage 2 first binary-only swap)** -- engine-side glue via `%install`-time symlink to `/usr/bin/spirv-cross` from the o3de-spirv-cross COPR package. No engine code change.
- **`system_dxc` activated (Stage 2 second binary-only swap)** -- same install-overlay shape but three symlinks (dxc, dxsc, libdxcompiler.so).

### Stage 2 PoCs (third one landed today; full set now ✓ green)

- **DXC PoC ✓ GREEN** -- `o3de-dxc-spirv-1.8.2505.1-1.rev12` (build 10435628). 12 iterations rev4 -> rev12. Final fix: Patch0002 added `SPIRV-Tools` to clangSPIRV's LINK_LIBS at the consumer side (rev11's transitive `target_link_libraries(IMPORTED INTERFACE)` form didn't propagate). Functional verification: `dxc -spirv -T ps_6_0 -E main shader.hlsl` produces valid SPIR-V output.
- **mcpp PoC ✓ GREEN + engine-side glue activated** -- `o3de-mcpp-az-2.7.2-1.rev7` (build 10436752, F44 + rawhide). 7 iterations rev1 -> rev7. Library-link variant of the DXC-class pattern (different shape from spirvcross/dxc which are binary shellouts -- mcpp is `#include <mcpp_lib.h>` + linked into the engine binary at build time). Source: upstream mcpp 2.7.2 (BSD-2-Clause, abandonware-class, 2008) + o3de/3p-package-source's 566-line `_az.2` patch. Configure: `--with-pic --enable-mcpplib`. Outputs the four expected RPMs: o3de-mcpp-az (libmcpp.so.0, /usr/bin/mcpp, man page), o3de-mcpp-az-devel (libmcpp.so + libmcpp.a + mcpp_lib.h + mcpp_out.h), debuginfo, debugsource. Iteration history: rev1 missing libtool BR, rev2 GCC 14 strictness on pointer types, rev3 LL_FORM undefined (configure AC_RUN_IFELSE silent fail), rev4 `true`/`false` keyword conflict in C23, rev5 trim AUTHORS + info docs from %files, rev6 unpackaged docs from autotools install, rev7 fix.
- **system_mcpp engine-side glue activated** (commit `1cf44dc`) -- third Stage 2 swap, first library-link variant. `Findmcpp-system.cmake` shim + Patch0006 `LY_USE_SYSTEM_MCPP` gate + spec wiring (`%bcond_with system_mcpp`, Source44 declaration, BR `o3de-mcpp-az-devel`, Requires `o3de-mcpp-az`, cmake `-DLY_USE_SYSTEM_MCPP=ON`). Engine code unchanged. SBOM bumped 2605.0-39 -> 2605.0-40. The two Stage 2 architectural variants (binary shellout for spirvcross/dxc, library link for mcpp) are now both proven in production engine builds.

### Upstream PRs (2 new + 1 fix on existing)

- **PR #19737** (Microphone libsamplerate PAL-trait gate) -- submitted 2026-05-08. Adds `PAL_TRAIT_MICROPHONE_USES_LIBSAMPLERATE` (FALSE on Linux/None, TRUE elsewhere) so Linux builds drop the libsamplerate dep entirely. Initial submission failed o3de's `UnicodeValidator` (em-dashes in comments); force-pushed em-dash-free version. CI re-running.
- **PR #19738** (BuiltInPackages googlebenchmark gate on LY_DISABLE_TEST_MODULES) -- submitted 2026-05-08, **NEEDS TO BE CLOSED 2026-05-08 (architectural premise wrong)**. Nick_L on the PR + sig-build Discord clarified: `LY_DISABLE_TEST_MODULES` means "skip our internal test modules" NOT "disable test infrastructure". AzTestRunner + AzTest + googletest + googlebenchmark + googlemock all ship unconditionally so gem developers can run their own tests. Verified at `Code/Framework/AzTest/CMakeLists.txt:34` (AzTest links `3rdParty::GoogleBenchmark` directly) + the explicit comment in `Code/Tools/AzTestRunner/CMakeLists.txt` ("note that LY_DISABLE_TEST_MODULES is a CMake variable that controls whether test modules are built or not and it should be interpreted as 'build our own tests'..."). Memory captured at `project_az_test_runner_architecture.md`. Replacement direction: close #19738 + write a `system_googlebenchmark` Stage 1 swap against Fedora's `google-benchmark-devel`, same shape as system_lua / system_assimp / etc.
- **PR #19733** (AzCore Lua) -- still open, awaiting maintainer merge.
- **PR #19734** (libtiff C99) -- 15 of 16 CI checks passed after re-run; Mac-Asset still in `macos-15-intel` runner queue.

### Audits (1 new today; 9 cumulative)

- **mcpp audit** -- reframed the existing `project_mcpp_architectural_choice.md` memory note: half-true ("any preprocessor would work" philosophically yes; in practice the engine binds to mcpp's specific library API, and Fedora ships zero mcpp packages). Right answer is the DXC-class library-rebuild we just shipped as the PoC.

### Infrastructure / hygiene

- **F43 chroot dropped** from `hellaenergy/o3de-dependencies` (was failing on EOL distro per `project_target_distros.md` rule).
- **`o3de-dependencies` COPR project added to `scripts/copr-metadata.sh`** managed-projects list (4 -> 5). Description + instructions populated and live-pushed.
- **Tier 7 cron default flipped OFF** (commit `a7c6e18`) -- first live run (CI run 25553050229) confirmed test infrastructure works end-to-end (Tiers 1+2+3 green, AP launched, log + artifact upload clean) but revealed a cold-cache parallel-jobs SRG-merge ordering quirk that fails 76+ FBX bakes + 210 shader builds spuriously on first AP pass. NOT a packaging regression -- same on upstream from-source build. Cron-driven cycle would keep red-flagging a non-bug; flipped to opt-in via workflow_dispatch only until design fix. Memory captured at `project_tier7_cold_cache_quirk.md`.
- **COPR edit-chroot REPLACE-not-append gotcha caught** -- single-flag `copr-cli edit-chroot --rpmbuild-with system_mcpp` reduced o3de-experimental's 16-entry with_opts list to 1 entry. Detected via post-edit `get-chroot` verification within ~5 min, restored full list before any builds were submitted in the corrupt window. Two in-flight builds (10435647 + 10436540) had already resolved their chroot config at task pickup over an hour earlier so they're unaffected. Memory rule + Makefile copr-init hint updated (commits `ddb299f` and the new `feedback_copr_edit_chroot_replaces.md`) to make the REPLACE semantic explicit.
- **Lua 5.5 LUA_NUMTAGS macro removed -- Patch0011 covers it** (this commit) -- second-of-N Lua 5.5 compat patches sibling to Patch0010. `Code/Tools/LuaIDE/Source/LUA/WatchesPanel.cpp` references `LUA_NUMTAGS` at two sites (a bounds check + a static_assert); 5.5 dropped that public macro. Patch0011 adds a one-line `#define LUA_NUMTAGS LUA_NUMTYPES` shim guarded on `#if LUA_VERSION_NUM >= 505 && !defined(LUA_NUMTAGS)`. Caught on rawhide chroot of build 10437498 (the chain-built rename + Patch0010 + system_mcpp validation run); the build progressed past Patch0010's covered site in ScriptContext.cpp only to trip on this LuaIDE site later. F44 chroot of the same build separately failed with "Build root is locked by another process" (transient COPR/mock infrastructure flake; not our code) -- the next experimental rebuild should clear F44 cleanly. SBOM bumped 2605.0-43 -> 2605.0-44. Memory note `project_lua_5_5_newstate_break.md` updated to reflect there are MORE Lua 5.5 sites we haven't tripped on yet (right way to find them all is `grep -rn LUA_NUMTAGS\|lua_newstate Code/ Gems/` against a Lua-5.5 sysroot; surfaces naturally during CS10 Phase 2).
- **Lua 5.5 lua_newstate signature break -- Patch0010 covers it** (commit `7f0c403`) -- Fedora rawhide has shipped Lua 5.5 ahead of F45, adding a required third `unsigned seed` parameter to `lua_newstate`. Engine's `Code/Framework/AzCore/AzCore/Script/ScriptContext.cpp:4359` calls the 5.4 two-arg form. Caught on builds 10436540 (14-pack rawhide chroot, 2026-05-08, FAILED) + 10435647 (10-pack rawhide chroot, same failure -- F44 still building so overall state still "running"). Patch0010 wraps the call in `#if LUA_VERSION_NUM >= 505` guard, passing seed=0 on 5.5+. Behavior-preserving on Lua 5.4. SBOM bumped 2605.0-40 -> 2605.0-41. Memory note: `project_lua_5_5_newstate_break.md`. Worth pitching upstream once the patch shape settles -- benefits every distro on rawhide's Lua 5.5 trajectory.
- **Versioned-major rename of Stage 2 COPR deps** (commit `0e5f751` engine-side; three rename builds 10437362/10437377/10437378 in flight) -- `o3de-spirv-cross` / `o3de-dxc-spirv` / `o3de-mcpp-az` renamed to `o3de2605-spirv-cross` / `o3de2605-dxc-spirv` / `o3de2605-mcpp-az` to mirror the engine package's o3deNNNN convention. Future `o3de2610-<dep>` packages co-exist in the same `hellaenergy/o3de-dependencies` COPR for the 26.10.x line. Rejected per-major COPR projects in favor of versioned-package-names-in-single-project (mirrors postgresql10/postgresql10-server in Fedora's main repo + matches upstream's CDN keying model). Empirical research showed cross-engine-branch divergence is small (1-3 lines between main/stabilization/development BuiltInPackages files), upstream's CDN co-hosts versions across major lines, and 3p-package-source has no engine-aligned branching -- so versioned-package-names is the architecturally-correct mirror of upstream's mental model. Rationale captured as a new "Eighth separation" in ARCHITECTURE.md + memory note `project_o3de_3p_versioning_research.md`. SBOM bumped 2605.0-41 -> 2605.0-42. Live COPR metadata for both `o3de-experimental` and `o3de-dependencies` refreshed and pushed.

- **system_googlebenchmark Stage 1 swap PLUMBING** (replaces closed PR #19738's intent in the architecturally-correct shape). Bcond + Find shim + Patch0006 hunk + spec wiring + Makefile spec-parse-experimental include + dep-map.yaml entry. Bcond is OFF by default; not yet in SRPM_EXPERIMENTAL_FLAGS or any chroot config so today's chain-built 15-pack experimental (10437498) is unaffected. Activation deferred to a separate commit after the chain-build + smoke-testing cycle. Linkage variance noted: Fedora ships only libbenchmark.so (no -static), so AzTestRunner ends up dynamically linked rather than having gbench compiled in statically; gbench's API is stable across 1.7.0 (engine pin) -> 1.9.5 (Fedora ship). Sibling-fix-not-replacement: o3de/o3de#19740 (libbenchmark.a missing from the engine's install set) is still the right fix on the engine side; the system swap is partial mitigation for external gem developers because they can satisfy benchmark links via Fedora's google-benchmark-devel directly. SBOM bumped 2605.0-42 -> 2605.0-43.

- **CentOS Stream 10 chroot pivot (Phase 1 ✓ verified)** -- corrected an earlier misalignment where the project's stated target was "F44+ / RHEL 10+" but only `hellaenergy/o3de` had a RHEL 10-targeted chroot enabled (`epel-10-x86_64`), and the actual intent per Nick was the CentOS Stream 10 line (which is upstream of RHEL 10). Phase 1 chroot pivot applied to all 5 COPR projects: dropped `epel-10-x86_64` from `hellaenergy/o3de`, added `centos-stream-10-x86_64` to all of `o3de`, `o3de-stabilization`, `o3de-snapshot`, `o3de-experimental`, `o3de-dependencies`. Each project now has F44 + rawhide + CS10. Two smoke builds run on CS10 chroot only: build 10438101 (`o3de2605-mcpp-az`) FAILED with `error: line 235: %package debuginfo: package o3de2605-mcpp-az-debuginfo already exists` -- a CS10/RPM 4.19-specific macro double-definition that doesn't fire on F44's RPM 6.x; per-spec fix is `%global debug_package %{nil}`. Build 10438108 (`o3de2605-spirv-cross`) SUCCEEDED in 2 min, confirming the COPR + mock + RPM-build chain works on CS10 for our shape. So the CS10 viability is proven for cmake-based simple builds; the mcpp result is a per-spec quirk to fix in Phase 2 (memory note `project_cs10_debuginfo_quirk.md`). Phase 2 (engine-side iteration on CS10 + per-spec fixes for mcpp + heavier deps) is the natural next session. Memory note `project_target_distros.md` updated to reflect F44+ / CS10+ instead of F44+ / RHEL 10+; doc sweep across CONTRIBUTING.md, FEDORA_ROADMAP.md, Makefile copr-init hint, tests/test-branch.sh.
- **New memory rules** -- `feedback_no_em_dashes.md` (user preference, ASCII punctuation everywhere); `project_o3de_unicode_validator.md` (upstream gate that caught PR #19737); `project_tier7_cold_cache_quirk.md`; `feedback_copr_edit_chroot_replaces.md`.

### In flight (background agents)

- **Drift-detection workflow** -- `tools/check-deps-drift.py` + `.github/workflows/check-deps-drift.yml` + `tools/dep-map.yaml` (compares engine BuiltInPackages vs COPR builds vs 3p-package-source; sticky issue updates weekly).
- **Tier 7 FBX-bake integration test** for assimp -- script committed (`tests/asset-bake-test.sh`); pending live-install validation to confirm the assumptions in its "Manual verification status" header (cache layout, .azmodel magic prefix, AssetProcessorBatch arg surface).

### COPR builds in flight

- **10-pack experimental** (10435647) -- running ~4h; queued before today's chroot config bump. May effectively run as a 14-pack-equivalent if its binary phase saw the new chroot config; otherwise validates the 10-pack as planned.
- **14-pack experimental** -- just queued (background task `bbjeb3mnt`), incoming build_id.
- **mcpp PoC rev1** (10436552) -- running.

---

## Pending -- what's loaded for next session

### Hot

- **9-pack stabilization promotion** -- the 9-pack validated end-to-end yesterday (build 10433646, CI run 25522053232 green). Currently only the 7-pack is in `o3de-stabilization`. Per `project_active_community_testers.md` we should give the 7-pack a ~1-week soak before pushing the 9-pack to testers. Earliest reasonable promotion: 2026-05-14ish. Mechanical: extend stabilization chroot config with `system_lua` + `system_poly2tri` + queue build.
- **14-pack stabilization promotion** -- same shape but adds 4 more flags (system_assimp + system_libsamplerate + system_spirvcross + system_dxc). Consider whether to do incrementally (12-pack first, then 14-pack) or all at once. Probably incrementally, with 7-pack -> 12-pack -> 14-pack staircase, gating each on tester soak.
- **mcpp PoC engine-side glue** -- mcpp PoC ✓ green as of 2026-05-08 (rev7). Next: write `LY_USE_SYSTEM_MCPP` bcond + Patch0006 gate + `Findmcpp-system.cmake` shim creating `3rdParty::mcpp` IMPORTED target against `/usr/lib64/libmcpp.so` + `/usr/include/mcpp_lib.h`. This is the third Stage 2 swap (library-link variant; spirv-cross + dxc were binary shellouts). Probably ~1-2 iterations to nail the cmake target shape.

- **Tier 7 redesign** -- run 25553050229 (2026-05-08) confirmed Tier 7 infrastructure works end-to-end, but the test design is too tight: AssetProcessorBatch's parallel-jobs scheduler hits a cold-cache SRG-merge dependency-ordering quirk on first pass (viewsrg.srgi / scenesrg.srgi auto-generated AFTER ShaderAssetBuilder runs), spuriously failing 76+ FBX bakes + 210 shaders. Workflow flipped to opt-in (run_asset_bake default false) for cron until design fix. Next iteration options: (a) AP `--scanFolders` to scope to project Assets/ only, (b) two-pass AP run + check second-pass results, (c) upstream bug report on the cold-cache parallel SRG ordering. Memory captured at `project_tier7_cold_cache_quirk.md`.

### Warm

- **Patch0009 PhysX4-hunk timebomb** -- when PR #19726 (PhysX 4 retirement) merges upstream, our `Gems/PhysX/Core/PhysX4/.../PAL_linux.cmake` patch hunk will fail to apply. Mechanical rebase: drop the PhysX4 hunk; regenerate Patch0009 with only the PhysX5 hunk. Not blocked on us. Annotated in three places (spec Patch0009 declaration, patch file header, NvCloth memory).
- ~~**Drift-detection workflow rollout**~~ -- DONE 2026-05-08. Workflow committed (`.github/workflows/check-deps-drift.yml`), first manual trigger uncovered a "dubious ownership" git-config issue (Fedora container + actions/checkout uid mismatch), fixed in commit 360b088 (`safe.directory` step), re-trigger created sticky [issue #9 "Dependency drift report"](https://github.com/nickschuetz/o3de-rpm/issues/9). The 'drift' label was created proactively + applied. Weekly cron at Mondays 06:00 UTC active. The workflow's exit-non-zero-on-drift behavior is intentional (red GHA dot surfaces real action items).
- ~~**Tier 7 FBX-bake test rollout**~~ -- DONE 2026-05-08 in the sense of "first live run executed". Run 25553050229 confirmed the AssetProcessorBatch invocation works against the RPM-installed engine; the test fired end-to-end and uploaded artifact logs cleanly. Remaining design issue (cold-cache AP ordering quirk; not packaging) tracked as the new "Tier 7 redesign" item above.

### Cool (someday/maybe)

- **Drift-detection findings act-on** -- the audit research agent today identified 5 drift items in `o3de-dependencies` (qt5 5.15.1 vs .2; AWSNativeSDK .361 vs .288; astc-encoder 5.3.0 vs 3.2; ISPCTexComp commit 691513b vs 36b80aa; mikkelsen label form). Plus 2 cruft (aws-gamelift, PhysX no longer referenced on Linux). When the drift-detection workflow lands and the sticky issue surfaces these, decide which to fix.
- ~~**F43 cleanup verification**~~ -- DONE 2026-05-08. Audited all 4 engine projects (`o3de`, `o3de-stabilization`, `o3de-snapshot`, `o3de-experimental`); all already F44 + rawhide only (plus `o3de` had `epel-10-x86_64` per Nick's intent at the time, which was shorthand for the CS10 line; that chroot was replaced with `centos-stream-10-x86_64` later in the same day during the CS10 pivot, see entry below). No action needed.
- **CryCommon int64/uint64 C99 migration** -- Nick_L 2026-05-05 said upstream is "open" to this; if an engine PR lands, `system_tiff` activates automatically. Not blocking; pure optionality for someone else to pick up.
- **Engine-side cmake-gate cleanup for Stage 2 swaps** -- both system_spirvcross and system_dxc currently use install-time symlink overlays (the bundled fetches still happen at cmake-config time, then we overlay). Cleaner long-term: write Find shims that create IMPORTED EXECUTABLE / IMPORTED SHARED targets pointing at /usr/bin/, then gate Patch0006 to skip the upstream fetch entirely. Saves the cmake-time fetch.

---

## Reference state at end-of-day 2026-05-08

- **HEAD on main**: `0e5f751` ("feat(stage2-rename): o3de-<dep> -> o3de2605-<dep> for versioned-major coexistence")
- **Spec changelog**: `2605.0-42`
- **Active in `o3de-stabilization`**: 7-pack
- **Active in `o3de-experimental` chroot config**: 16 system_* flags (snapshot + stabilization + 12 Stage 1 + 3 Stage 2 = 17 with_opts entries)
- **In `o3de-dependencies`** (after F43 chroot drop, F44 + rawhide only): 9 existing deps + 3 Stage 2 PoCs all ✓ green AND renamed to `o3deNNNN-<dep>` form: `o3de2605-spirv-cross-1.3.275.0-1.rev3`, `o3de2605-dxc-spirv-1.8.2505.1-1.rev13`, `o3de2605-mcpp-az-2.7.2-1.rev8` (rename builds 10437362/10437377/10437378 in flight as of end-of-day; the unversioned predecessor packages stay live as Obsoletes-from-the-new ones until they land green).
- **Upstream PRs**: **#19733 (Lua) MERGED 2026-05-08** by Nicholas Lawson into development. **#19734 (libtiff C99) MERGED 2026-05-08** same day, same reviewer. Both happened within ~1h of each other (~11:18 AM). #19737 (Microphone libsamplerate PAL gate) still REVIEW_REQUIRED + 1 unrelated Android-Asset CI failure. #19738 (googlebenchmark gate) **CLOSED 2026-05-08** -- Nick_L clarified architectural premise was wrong (LY_DISABLE_TEST_MODULES means "skip our internal test modules" not "disable test infrastructure"; AzTest + AzTestRunner + gbench all ship unconditionally for gem developers). Replacement direction: `system_googlebenchmark` Stage 1 swap against Fedora's `google-benchmark-devel`. **Side bug surfaced from the same investigation:** `libbenchmark.a` standalone archive is NOT installed alongside `libgtest.a` + `libgmock.a` even though gbench source IS compiled into AzTestRunner -- exactly the missing-benchmark-libs case Nick_L predicted on the PR thread. NOT a packaging-side issue (we just ship what cmake installs); it's an upstream cmake-install rule mismatch worth a separate o3de/o3de PR. Memory note: `project_az_test_runner_architecture.md` updated with the empirical finding.

- **Patch dropoff implication of #19733 + #19734 merging**: when we pull a fresh snapshot from `development` (or once `stabilization/26050` cherry-picks these forward), our `sources/0008-azcore-drop-lua-lobject-include.patch` and `sources/0007-libtiff-c99-typedefs.patch` become redundant. Either they'll fail with "patch already applied" at `%autosetup -p1` time (forcing the drop) or they'll apply cleanly because the upstream merges haven't reached the snapshot yet. Action: when next snapshot rebase happens, audit these two patches; drop them from spec + sources/ if upstream has the fix, or keep them if the snapshot pre-dates the merge. No urgency since stabilization/26050 doesn't auto-pick from development.
- **Audits done**: 9 (Lua, poly2tri, squish-ccr, assimp, SQLite, libsamplerate, SPIRVCross, googlebenchmark, mcpp); plus the empirical 3p-versioning research that drove the rename decision.
- **Memory notes added today**: `feedback_no_em_dashes.md`, `project_o3de_unicode_validator.md`, `project_tier7_cold_cache_quirk.md`, `feedback_copr_edit_chroot_replaces.md`, `project_lua_5_5_newstate_break.md`, `project_az_test_runner_architecture.md`, `project_o3de_3p_versioning_research.md`, plus update to `project_mcpp_architectural_choice.md` (Update 2026-05-08 audit reframing section).
- **PoC working trees** (local-only git, not pushed upstream): `/home/nschuetz/o3de2605-dxc-spirv-poc/`, `/home/nschuetz/o3de2605-spirv-cross-poc/`, `/home/nschuetz/o3de2605-mcpp-az-poc/` (renamed from unversioned form 2026-05-08 to align dir names with the spec-internal versioned package names).
- **Audit notes** (gitignored, ephemeral): `/tmp/o3de-assimp-audit/{INVESTIGATION_NOTES,SQLITE_INVESTIGATION_NOTES,LIBSAMPLERATE_INVESTIGATION_NOTES,SPIRVCROSS_INVESTIGATION_NOTES,GOOGLEBENCHMARK_INVESTIGATION_NOTES,MCPP_INVESTIGATION_NOTES}.md`, `/tmp/o3de-poly2tri-audit/INVESTIGATION_NOTES.md`

---

## End-of-day 2026-05-07 (history) -- what landed

Big day. Five concrete milestones across the Stage 1 / Stage 2 / upstream-PR tracks.

- **9-pack VALIDATED end-to-end on `o3de-experimental`** (build 10433646; CI run 25522053232). Adds system_lua + system_poly2tri to the 7-pack.
- **7-pack PROMOTED to `o3de-stabilization`** (build 10433491; CI run 25520049089). Real users can install via `dnf copr enable hellaenergy/o3de-stabilization && dnf install o3de2605`.
- **SPIRV-Cross PoC ✓ GREEN** (`o3de-spirv-cross-1.3.275.0-1.rev2`, build 10434617). First binary-only PoC to land.
- **DXC PoC at 99.5%** -- rev10 reached step 1106/1111; rev11 transitive-link attempt didn't propagate. Today's rev12 fix (Patch0002 at clangSPIRV's LINK_LIBS) made it green.
- **8 audits in one day** (Lua/poly2tri/squish-ccr/assimp/SQLite/libsamplerate/SPIRVCross/googlebenchmark) -- all 5 "trivial flip" annotations from the original BUNDLED_LIBRARIES.md verified or reframed.
- **2 upstream PRs submitted** (#19733 AzCore Lua, #19734 libtiff C99); both approved by nick-l-o3de.

Reference state at end-of-day 2026-05-07:
- HEAD: `09baf37` ("copr-metadata: sync 9-pack experimental + 7-pack stabilization status")
- Spec: `2605.0-34`
- Memory notes added: `feedback_audit_pattern_yields_findings.md`; updates to `project_nvcloth_status.md` + `project_o3de_restricted_bundles.md`
