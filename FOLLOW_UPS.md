# Follow-ups & state-of-play

End-of-day capture: what landed, what's pending, what's loaded for next session.

This file is intentionally a living scratchpad — entries get added or removed as work progresses. Promote anything tracker-worthy to `FEDORA_ROADMAP.md`, a GitHub issue, or a memory note. Anything below that's gone stale by the time you read it can be deleted.

---

## End-of-day 2026-05-07 — what landed

Big day. Five concrete milestones across the Stage 1 / Stage 2 / upstream-PR tracks.

### Stage 1 — system-library swaps

- **9-pack VALIDATED end-to-end on `o3de-experimental`** — build 10433646 succeeded on F44 + rawhide; CI run 25522053232 passed Tiers 1+2+4+6 on both chroots. Adds `system_lua` + `system_poly2tri` to the 7-pack baseline.
  - **`system_poly2tri`** activated via Patch0009 + `Findpoly2tri-system.cmake` (Source40). Audit ([#7](https://github.com/nickschuetz/o3de-rpm/issues/7)) reframed it from "off-limits restricted bundle" to "Stage 1 swap candidate" — Fedora's `poly2tri-devel` ships from Mason Green's BSD-3-Clause original tree (license-clean, independent of the bundled fork's attribution issue).
  - **`system_lua`** activated via Patch0008 (carry-patch). Audit found AzCore `ScriptContext.cpp:28`'s `<Lua/lobject.h>` include was redundant — the only consumed symbol (`LUAI_MAXALIGN`) is already public Lua API via `luaconf.h`'s transitive include from `lauxlib.h`. Same patch submitted upstream as **PR #19733** (approved by nick-l-o3de 2026-05-07, awaiting maintainer merge).

- **7-pack PROMOTED to `o3de-stabilization`** — build 10433491 succeeded on F44 + rawhide; CI run 25520049089 passed in 3m48s. Real users can now `dnf copr enable hellaenergy/o3de-stabilization && dnf install o3de2605` to get the 7-pack RPM. The 9-pack stays in `o3de-experimental` until community feedback on the 7-pack lands.

- **COPR project metadata synced** — both `o3de-experimental` and `o3de-stabilization` description/instructions updated to reflect today's state. `make copr-metadata-push` verified clean.

### Stage 2 — binary-only / DXC-class PoCs

- **SPIRV-Cross PoC ✓ GREEN** — `o3de-spirv-cross-1.3.275.0-1.rev2` built and signed in `hellaenergy/o3de-dependencies` (build 10434617, 3m31s on F44 + rawhide). Functional verification: 976KB compressed RPM ships `/usr/bin/spirv-cross`; `--help` prints correct usage. License: Apache-2.0 OR MIT. Source: `KhronosGroup/SPIRV-Cross` at tag `vulkan-sdk-1.3.275.0` (SHA `117161dd5460`).
  - Iteration count: 2 (rev1 cmake-policy issue, rev2 success). Working tree at `/home/nschuetz/o3de-spirv-cross-poc/` (local-only git repo).

- **DXC PoC at 99.5%** — `o3de-dxc-spirv` rev10 reached step 1106/1111 in the build pipeline before failing at the FINAL link of `libdxcompiler.so` with undefined `spv*` references. rev11 (transitive `target_link_libraries(SPIRV-Tools-opt INTERFACE SPIRV-Tools)`) didn't propagate as hoped — the link line still shows only `-lSPIRV-Tools-opt`. Probably needs `set_target_properties(SPIRV-Tools-opt PROPERTIES INTERFACE_LINK_LIBRARIES SPIRV-Tools)` form OR a Patch0002 against `tools/clang/lib/SPIRV/CMakeLists.txt:43` adding `SPIRV-Tools` next to `SPIRV-Tools-opt` directly. Iteration count: 8 (rev4 → rev11). Working tree at `/home/nschuetz/o3de-dxc-spirv-poc/`.

### Audits — eight new in one day

| Bundle | Outcome | Action |
|---|---|---|
| Lua | Single-line carry-patch + upstream PR | Activated 9-pack |
| poly2tri | Gem-isolated, license-clean | Activated 8-pack |
| squish-ccr | Genuinely restricted (BC7 patent) | Stays restricted (sharpened) |
| assimp | Stage 1 candidate, 5→6 caveat | Pending impl + Tier 6 test |
| SQLite | Cleanest Stage 1 to date | Pending impl |
| libsamplerate | Stage 1 + upstream-PR opportunity | Pending impl + PR draft |
| SPIRVCross | DXC-class — needs COPR rebuild | PoC ✓ green |
| googlebenchmark | Test-only (LY_DISABLE_TEST_MODULES neutralizes) | Status quo + upstream PR opportunity |

Eight audits, all five "trivial flip" annotations from the original `BUNDLED_LIBRARIES.md` table verified or reframed. Audit-pattern playbook reliability tracker → 8/8 actionable findings.

### Upstream PRs

- **PR #19733** (AzCore Lua `<lobject.h>` drop) — approved by nick-l-o3de 2026-05-07, awaiting maintainer merge. CI green.
- **PR #19734** (libtiff C99 typedef migration) — approved by nick-l-o3de; CI hit infrastructure flakes (network failures + 5h41m timeouts on Mac/Windows/Android/iOS Asset builds, all showing `Compilation failed: 0`). Re-run triggered late afternoon; pending outcome.

### Documentation lockstep

Per `feedback_keep_docs_current.md`: every spec/sources change → updates README, ARCHITECTURE diagram + prose, BUNDLED_LIBRARIES, FEDORA_ROADMAP, FLATPAK_NOTES, SBOM, tests assertions. Today:

- `BUNDLED_LIBRARIES.md` — DXC iteration history rev4→rev11; SPIRV-Cross PoC ✓ row; SQLite + libsamplerate + assimp Stage 1 audit findings; binary-only/DXC-class section + intro paragraph.
- `FEDORA_ROADMAP.md` — 9-pack staged → VALIDATED; PhysX 4 retirement timing hedge (alex7900's `PHYSX_SETREG_GEM_NAME` macro-redefined edge case).
- `ARCHITECTURE.md` — Mermaid diagram extended with new "Build-time dependencies" subgraph (Fedora repos / `o3de-dependencies` / `packages.o3de.org` CDN); new 7th "separation to notice" prose explaining the three-source dependency graph.
- `FLATPAK_NOTES.md` (gitignored) — submodule + `BUILD_SHARED_LIBS` lessons from DXC iteration.
- SBOM bumped from 2605.0-30 → 2605.0-34.

---

## Pending — what's loaded for next session

### Hot (could land in 1-2 hours)

- **DXC PoC rev12** — pick one of two fixes for the SPIRV-Tools transitive link:
  - **Option A**: `set_target_properties(SPIRV-Tools-opt PROPERTIES INTERFACE_LINK_LIBRARIES SPIRV-Tools)` instead of `target_link_libraries(... INTERFACE)`. Smaller diff to existing Patch0001.
  - **Option B**: Patch0002 against `tools/clang/lib/SPIRV/CMakeLists.txt:43` adding `SPIRV-Tools` directly to clangSPIRV's link list. More targeted — hits the specific cmake target that needs the symbol.
  - Recommend B; the failure mode showed cmake's IMPORTED-target `INTERFACE_LINK_LIBRARIES` propagation was unreliable.

- **Patch0009 PhysX4-hunk timebomb** — when PR #19726 (PhysX 4 retirement) merges, our `Gems/PhysX/Core/PhysX4/.../PAL_linux.cmake` patch hunk will fail to apply. Mechanical rebase: drop the PhysX4 hunk; regenerate Patch0009 with only the PhysX5 hunk. **Not blocked on us** — fires when upstream merges (could be days, could be weeks; alex7900's `upgrade-physx-gem` migration-tool edge case may push out the merge). Annotated in three places (spec Patch0009 declaration, patch file header, NvCloth memory) so future-me can't miss it.

### Warm (next week or two)

- **Stage 1 implementations** — assimp / SQLite / libsamplerate (the audit-confirmed Stage 1 candidates). Order: SQLite first (cleanest swap, no major-version risk, no Find shim needed). Then libsamplerate (essentially zero risk on Linux because the runtime path is a None stub). Then assimp (paired with a Tier 6 FBX-bake integration test to catch 5→6 behavior deltas).

- **Engine-side glue for SPIRV-Cross + DXC PoCs** — once both PoCs are green, the engine spec needs `LY_USE_SYSTEM_DXC` + `LY_USE_SYSTEM_SPIRVCROSS` bconds + Find shims that point `3rdParty::DirectXShaderCompilerDxc` and `3rdParty::SPIRVCross` at the system-installed binaries (`/usr/bin/dxc` + `/usr/bin/spirv-cross` from the COPR-built packages) instead of fetching from `packages.o3de.org`. SPIRV-Cross is ready now; DXC waits on PoC completion.

- **9-pack stabilization promotion** — once the 7-pack has had ~1 week of community-tester soak time, promote the 9-pack into stabilization too. Add `system_lua` + `system_poly2tri` to `hellaenergy/o3de-stabilization`'s chroot config + queue a build. Don't push during an active testing window per `project_active_community_testers.md`.

- **Upstream PR drafts**:
  - **libsamplerate PAL trait** — gate `Gems/Microphone/Code/CMakeLists.txt`'s `3rdParty::libsamplerate` dependency on a `PAL_TRAIT_MICROPHONE_USES_LIBSAMPLERATE` flag (FALSE on Linux/None, TRUE elsewhere). Drops the dependency entirely on Linux. Same shape as PR #19733.
  - **googlebenchmark gate** — wrap the unconditional `ly_associate_package(googlebenchmark...)` in `BuiltInPackages_*.cmake` with `if (PAL_TRAIT_BUILD_TESTS_SUPPORTED AND NOT LY_DISABLE_TEST_MODULES)`. Could bundle with the libsamplerate PR as a "drop unused/test-only deps" patch.

### Cool (someday/maybe)

- **`o3de-mcpp-az` PoC** — sibling to DXC + SPIRV-Cross PoCs, but library-link instead of binary-shellout. License-clean COPR rebuild from upstream mcpp 2.7.2 (BSD-2-Clause, abandonware-class) + apply the `_az.2` patches. Output: `libmcpp-az.so` + `mcpp_lib.h` (engine `#include`s the lib header and calls `mcpp_lib_main()` etc.). Defer until DXC PoC lands; pattern proven, just bandwidth-bound. Audit added 2026-05-08, see `project_mcpp_architectural_choice.md` (Update 2026-05-08 section).

- **Tier 6 integration test for assimp** — bake a known FBX from AutomatedTesting Gem and smoke-test the resulting `.azmodel` + `.azmaterial` for non-emptiness. Pairs with assimp activation to catch 5→6 behavior deltas.
- **F43 chroot cleanup in hellaenergy/o3de-dependencies** — F43 hit EOL April 2025; per `project_target_distros.md` we're F44+ / RHEL 10+ only. The DXC PoC F43 chroot keeps failing at SRPM-build because of EOL package availability issues. Drop the F43 chroot from the project.
- **`o3de-dependencies` COPR metadata sync** — we don't currently manage that project's description/instructions from this repo. Could add `copr-metadata/o3de-dependencies/` if it would help users discover what's in there (Qt5-rev9, PhysX, AWS SDK, mikkelsen, in-flight DXC + SPIRV-Cross PoCs, etc.).
- **CryCommon int64/uint64 C99 migration** — Nick_L 2026-05-05 said upstream is "open" to this; if an engine PR lands, `system_tiff` activates automatically. Not blocking; pure optionality for someone else to pick up.

---

## Reference state at end-of-day 2026-05-07

- **HEAD on main**: `09baf37` ("copr-metadata: sync 9-pack experimental + 7-pack stabilization status")
- **Spec changelog**: `2605.0-34`
- **Active in `o3de-stabilization`**: 7-pack
- **Active in `o3de-experimental`**: 9-pack
- **In `o3de-dependencies`**: 9 existing deps + `o3de-spirv-cross-1.3.275.0-1.rev2` (✓ green); `o3de-dxc-spirv-1.8.2505.1-1.rev11` (failed at link step 1106/1111)
- **Upstream PRs in flight**: #19733 (Lua, approved-awaiting-merge), #19734 (libtiff, approved-CI-rerun-pending)
- **Audits done**: 8 (Lua, poly2tri, squish-ccr, assimp, SQLite, libsamplerate, SPIRVCross, googlebenchmark)
- **Memory notes added today**: `feedback_audit_pattern_yields_findings.md`; updates to `project_nvcloth_status.md` (2 new sections — code-review confirmation + alex7900 timing hedge), `project_o3de_restricted_bundles.md` (poly2tri removed)
- **PoC working trees** (local-only git, not pushed upstream): `/home/nschuetz/o3de-dxc-spirv-poc/`, `/home/nschuetz/o3de-spirv-cross-poc/`
- **Audit notes** (gitignored, ephemeral): `/tmp/o3de-assimp-audit/{INVESTIGATION_NOTES,SQLITE_INVESTIGATION_NOTES,LIBSAMPLERATE_INVESTIGATION_NOTES,SPIRVCROSS_INVESTIGATION_NOTES,GOOGLEBENCHMARK_INVESTIGATION_NOTES}.md`, `/tmp/o3de-poly2tri-audit/INVESTIGATION_NOTES.md`
