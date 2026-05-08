# Follow-ups & state-of-play

End-of-day capture: what landed, what's pending, what's loaded for next session.

This file is intentionally a living scratchpad. Entries get added or removed as work progresses. Promote anything tracker-worthy to `FEDORA_ROADMAP.md`, a GitHub issue, or a memory note. Anything below that's gone stale by the time you read it can be deleted.

---

## End-of-day 2026-05-08 -- what landed

Bigger day than yesterday. Eleven commits on `main` plus three PoC dirs plus two upstream PRs.

### Stage 1 system swaps (5 added today; engine now consumes 12 system libs)

- **`system_sqlite` activated (10-pack)** -- audit-confirmed cleanest Stage 1 candidate. 29 sqlite3_* symbols all in Fedora 3.51.2; no extension API used. `Findsqlite-system.cmake` mikkelsen-pattern shim sidesteps the runtime-walker side-effect target issue.
- **`system_libsamplerate` activated (11-pack)** -- lowest-risk swap; Linux PAL is a do-nothing None stub so the engine never calls `src_*` at runtime, but the static lib still needs to satisfy the link.
- **`system_assimp` activated (12-pack)** -- 5.4 to 6.0 major bump caveat noted; symbols verified, runtime FBX behavior covered by new Tier 7 `tests/asset-bake-test.sh` (added end-of-day; not yet validated against a live install).
- **`system_spirvcross` activated (Stage 2 first binary-only swap)** -- engine-side glue via `%install`-time symlink to `/usr/bin/spirv-cross` from the o3de-spirv-cross COPR package. No engine code change.
- **`system_dxc` activated (Stage 2 second binary-only swap)** -- same install-overlay shape but three symlinks (dxc, dxsc, libdxcompiler.so).

### Stage 2 binary-only PoCs

- **DXC PoC ✓ GREEN** -- `o3de-dxc-spirv-1.8.2505.1-1.rev12` (build 10435628). 12 iterations rev4 -> rev12. Final fix: Patch0002 added `SPIRV-Tools` to clangSPIRV's LINK_LIBS at the consumer side (rev11's transitive `target_link_libraries(IMPORTED INTERFACE)` form didn't propagate). Functional verification: `dxc -spirv -T ps_6_0 -E main shader.hlsl` produces valid SPIR-V output.
- **mcpp PoC submitted (rev1 in flight)** -- `o3de-mcpp-az-2.7.2-1.rev1` (build 10436552, running). Library-link variant of the DXC-class pattern. Source: upstream mcpp 2.7.2 (BSD-2-Clause, abandonware-class, 2008) + o3de/3p-package-source's 566-line `_az.2` patch. Configure: `--with-pic --enable-mcpplib`. Outputs libmcpp.so + libmcpp.a + mcpp_lib.h headers (as o3de-mcpp-az + o3de-mcpp-az-devel subpackages).

### Upstream PRs (2 new + 1 fix on existing)

- **PR #19737** (Microphone libsamplerate PAL-trait gate) -- submitted 2026-05-08. Adds `PAL_TRAIT_MICROPHONE_USES_LIBSAMPLERATE` (FALSE on Linux/None, TRUE elsewhere) so Linux builds drop the libsamplerate dep entirely. Initial submission failed o3de's `UnicodeValidator` (em-dashes in comments); force-pushed em-dash-free version. CI re-running.
- **PR #19738** (BuiltInPackages googlebenchmark gate on LY_DISABLE_TEST_MODULES) -- submitted 2026-05-08. Wraps the unconditional `ly_associate_package(googlebenchmark...)` in 7 platform files. Behavior-preserving when tests enabled (default); skips fetch when tests disabled.
- **PR #19733** (AzCore Lua) -- still open, awaiting maintainer merge.
- **PR #19734** (libtiff C99) -- 15 of 16 CI checks passed after re-run; Mac-Asset still in `macos-15-intel` runner queue.

### Audits (1 new today; 9 cumulative)

- **mcpp audit** -- reframed the existing `project_mcpp_architectural_choice.md` memory note: half-true ("any preprocessor would work" philosophically yes; in practice the engine binds to mcpp's specific library API, and Fedora ships zero mcpp packages). Right answer is the DXC-class library-rebuild we just shipped as the PoC.

### Infrastructure / hygiene

- **F43 chroot dropped** from `hellaenergy/o3de-dependencies` (was failing on EOL distro per `project_target_distros.md` rule).
- **`o3de-dependencies` COPR project added to `scripts/copr-metadata.sh`** managed-projects list (4 -> 5). Description + instructions populated and live-pushed.
- **New memory rules** -- `feedback_no_em_dashes.md` (user preference, ASCII punctuation everywhere); `project_o3de_unicode_validator.md` (upstream gate that caught PR #19737).

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
- **mcpp PoC engine-side glue** -- once the mcpp PoC RPM lands green, write a `Findmcpp-system.cmake` shim or use the install-overlay approach (third Stage 2 binary-only swap, library-link variant). Probably ~1-2 iterations to nail the cmake target shape.

### Warm

- **Patch0009 PhysX4-hunk timebomb** -- when PR #19726 (PhysX 4 retirement) merges upstream, our `Gems/PhysX/Core/PhysX4/.../PAL_linux.cmake` patch hunk will fail to apply. Mechanical rebase: drop the PhysX4 hunk; regenerate Patch0009 with only the PhysX5 hunk. Not blocked on us. Annotated in three places (spec Patch0009 declaration, patch file header, NvCloth memory).
- **Drift-detection workflow rollout** -- when the background agent finishes building it, review + commit + manually trigger the first run + verify the sticky-issue mechanism works. Then let the weekly cron fire on its own schedule.
- **Tier 7 FBX-bake test rollout** -- script in tree as of 2026-05-08; needs first live run against an installed o3de2605 with the 12-pack swaps active to (a) confirm the AssetProcessorBatch invocation pattern works against an RPM-installed engine, (b) shake out the assumptions list in the script header, and (c) reveal any actual assimp 5 to 6 behavior deltas requiring follow-up patch work.

### Cool (someday/maybe)

- **Drift-detection findings act-on** -- the audit research agent today identified 5 drift items in `o3de-dependencies` (qt5 5.15.1 vs .2; AWSNativeSDK .361 vs .288; astc-encoder 5.3.0 vs 3.2; ISPCTexComp commit 691513b vs 36b80aa; mikkelsen label form). Plus 2 cruft (aws-gamelift, PhysX no longer referenced on Linux). When the drift-detection workflow lands and the sticky issue surfaces these, decide which to fix.
- **F43 cleanup verification** -- F43 dropped today from `o3de-dependencies`. The `o3de-experimental` and other engine projects also have F43? (Check + drop if yes.)
- **CryCommon int64/uint64 C99 migration** -- Nick_L 2026-05-05 said upstream is "open" to this; if an engine PR lands, `system_tiff` activates automatically. Not blocking; pure optionality for someone else to pick up.
- **Engine-side cmake-gate cleanup for Stage 2 swaps** -- both system_spirvcross and system_dxc currently use install-time symlink overlays (the bundled fetches still happen at cmake-config time, then we overlay). Cleaner long-term: write Find shims that create IMPORTED EXECUTABLE / IMPORTED SHARED targets pointing at /usr/bin/, then gate Patch0006 to skip the upstream fetch entirely. Saves the cmake-time fetch.

---

## Reference state at end-of-day 2026-05-08

- **HEAD on main**: `d801339` ("Stage 2 second activation: system_dxc via install-time symlink overlay")
- **Spec changelog**: `2605.0-39`
- **Active in `o3de-stabilization`**: 7-pack
- **Active in `o3de-experimental` chroot config**: 14 system_* flags (10-pack build queued before bump may run as effectively 10-pack OR 14-pack depending on when its binary phase started; new builds will be 14-pack)
- **In `o3de-dependencies`** (after F43 chroot drop, F44 + rawhide only): 9 existing deps + `o3de-spirv-cross-1.3.275.0-1.rev2` (green) + `o3de-dxc-spirv-1.8.2505.1-1.rev12` (green) + `o3de-mcpp-az-2.7.2-1.rev1` (in flight)
- **Upstream PRs in flight**: #19733 (Lua, approved-awaiting-merge), #19734 (libtiff, approved-15-of-16-CI-passed-Mac-Asset-queued), #19737 (Microphone libsamplerate PAL gate, em-dash fix CI re-running), #19738 (googlebenchmark gate, platform builds in progress)
- **Audits done**: 9 (Lua, poly2tri, squish-ccr, assimp, SQLite, libsamplerate, SPIRVCross, googlebenchmark, mcpp)
- **Memory notes added today**: `feedback_no_em_dashes.md`, `project_o3de_unicode_validator.md`, plus update to `project_mcpp_architectural_choice.md` (Update 2026-05-08 audit reframing section)
- **PoC working trees** (local-only git, not pushed upstream): `/home/nschuetz/o3de-dxc-spirv-poc/`, `/home/nschuetz/o3de-spirv-cross-poc/`, `/home/nschuetz/o3de-mcpp-az-poc/`
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
