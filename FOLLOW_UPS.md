# Follow-ups & state-of-play

End-of-day capture: what landed, what's pending, what's loaded for next session.

This file is intentionally a living scratchpad. Entries get added or removed as work progresses. Promote anything tracker-worthy to `FEDORA_ROADMAP.md`, a GitHub issue, or a memory note. Anything below that's gone stale by the time you read it can be deleted.

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
