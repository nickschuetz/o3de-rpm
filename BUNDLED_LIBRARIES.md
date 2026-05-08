# Bundled libraries inventory

Per-bundle status of every package O3DE pulls from `packages.o3de.org` at cmake configure time. This is the working source for the **Bundled Library Exception** filing required by Fedora package review.

For each entry: name, version O3DE bundles, license, what's in Fedora today, status against the Fedora-inclusion roadmap, and a one-line justification (when applicable).

Categories below match `FEDORA_ROADMAP.md` stages.

---

## Restricted (cannot be packaged for COPR or Fedora)

These three are omitted from `hellaenergy/o3de-dependencies` and remain fetched from `packages.o3de.org` at build time. **They will never go into Fedora.** See `FEDORA_ROADMAP.md` § "Restricted bundles" for the three handling options.

`poly2tri` was originally a fourth entry here; the audit on 2026-05-07 ([#7](https://github.com/nickschuetz/o3de-rpm/issues/7)) reframed it as a Stage 1 swap candidate (Fedora's `poly2tri-devel` ships from Mason Green's BSD-3-Clause original tree, license-clean and independent of the bundled fork's attribution issue). It now lives under "In Fedora proper" below.

| Package | O3DE version | Upstream license | Why restricted |
|---|---|---|---|
| **DirectXShaderCompilerDxc** | 1.8.2505.1-o3de-rev3 | NCSA / Apache-2.0 (sources) + proprietary DXIL signing | The DXIL signing tooling is Microsoft-proprietary. **DXC is structurally a fork of Clang/LLVM** — that's why the bundle ships `libclang-12.so.1` + `libtinfo.so.6` under `Builders/DirectXShaderCompiler/lib/` (RPATH-resolved internal stack, hence the spec's `%__requires_exclude`). Linux O3DE only uses DXC's SPIR-V backend, not DXIL — so a license-clean rebuild from upstream Microsoft DXC sources against system clang is feasible. See `FEDORA_ROADMAP.md` § "License-clean DXC rebuild" for the concrete plan. |
| **NvCloth** | v1.1.6-4-gd243404-pr58-rev1 | NVIDIA Source Code License | NVIDIA-specific clauses incompatible with Fedora's free-software requirements. **Confirmed standalone via three independent evidence types (2026-05-06 / 2026-05-07):** (1) Cheddarspice runtime test 2026-05-06 — NvCloth Gem still works with PhysX 4 removed + PhysX 5.6.1 active (chicken prefab); (2) Steve P [Amazon] code review 2026-05-07 — no direct PhysX 4 references in NvCloth source; (3) Cheddarspice structural fact 2026-05-07 — NvCloth ships its own standalone PxShared + Foundation (PhysX 5 ships its own pair). The earlier "auto-resolves via PhysX 4 retirement" framing is falsified. **Option A (drop the Gem) is now well-supported for Fedora-track**, not tentative. PhysX 5's `PxDeformableSurface` is CUDA-only — NOT a substitute for non-NVIDIA-GPU users. PR #19726 (PhysX 4 retirement) is approved by Steve P [Amazon] + Nick_L (tested against physx4 default + NewspaperDelivery samples; PhysX→PhysX5 alias). Merge timing has a hedge — alex7900 surfaced an `upgrade-physx-gem` script edge case 2026-05-07 PM (`PHYSX_SETREG_GEM_NAME` macro redefined error) which gives Nick_L's proposed registry-fallback enhancement (try PhysX5 first, fall back to PhysX) more relevance. Could go in same-week or slip if maintainers want it bundled. When the PR does merge, Patch0009's PhysX4 hunk becomes dead code; mechanical rebase. |
| **squish-ccr** | deb557d-rev1 | MIT-like + patents | Texture-compression algorithms encumbered by BPTC/BC7 patents. **Audit 2026-05-07 (issue #7) confirmed this stays restricted:** Fedora's `squish` package is upstream libsquish (DXT compression only — BC1/BC3/BC5; lacks BC7 entirely); the squish-ccr fork's BC7 codec is the patent-encumbered piece Fedora wouldn't ship even if separately packaged; engine consumes squish-ccr-specific extension API beyond upstream libsquish's surface, so an ABI-compatible drop-in isn't possible. Engine impact of dropping: BC7 path in the ImageProcessing Gem's bake step disappears; BC1/BC3/BC5/uncompressed texture formats still bake fine. |

---

## In the dependencies COPR (`hellaenergy/o3de-dependencies`)

SRPM'd, uploaded, and **all 9 have at least one succeeded build** (per the COPR build history at `copr-cli list-builds hellaenergy/o3de-dependencies`). Some packages required several iterations before succeeding — `o3de-qt5` took ten attempts, `aws-gamelift-server-sdk` and `PhysX` each took several. Build artifacts live at `https://download.copr.fedorainfracloud.org/results/hellaenergy/o3de-dependencies/fedora-44-x86_64/` and are consumable by enabling the COPR repo on a target system. These exist because they're not in Fedora proper but their licenses are clean.

| Package | O3DE version | hellaenergy SRPM | License | Status |
|---|---|---|---|---|
| **Qt 5.15** (custom-rev9) | 5.15.2-rev9 | `o3de-qt5-5.15.1` | LGPL-3.0-only OR GPL-3.0-only (Qt) + O3DE-rev9 patches (Apache-2.0) | **Bundling Library Exception** required for Fedora — system Qt5 cannot substitute (rev9 patches are load-bearing). |
| **PhysX** | 5.1.1-rev4 | `PhysX-5.1.2` | BSD-3-Clause | PhysX 5.x is open-source (NVIDIA released 2022); not in Fedora. |
| AWSNativeSDK | 1.11.361 | `o3de-AWSNativeSDK-1.11.361` | Apache-2.0 | Specific version O3DE pins; AWS SDK isn't in Fedora. |
| aws-iot-device-sdk-cpp-v2 | 1.15.2 | `aws-iot-device-sdk-cpp-v2-1.15.2` | Apache-2.0 | dep of AWSNativeSDK. |
| aws-gamelift-server-sdk | 5.1.2 | `aws-gamelift-server-sdk-5.1.2` | Apache-2.0 | Used by GameLift Gem (optional). |
| azslc | 1.8.22-rev1 | `azslc-1.8.22` | Apache-2.0 | O3DE shader language compiler. |
| ISPCTexComp | 36b80aa-rev1 | `ISPCTexComp-0-0.1.20230807git691513b` | MIT | Intel ISPC texture compressor. |
| astc-encoder | 3.2-rev2 | `astc-encoder-5.3.0` | Apache-2.0 | ARM ASTC reference encoder. |
| mikkelsen | 1.0.0.4 | `mikkelsen-1.0` | Public domain | Tangent-space generator (Morten Mikkelsen). |

---

## Version cross-reference: COPR vs upstream-expected

The COPR `o3de-dependencies` repo packages have specific versions; O3DE's `stabilization/26050` source expects specific versions. They don't all line up. Documented here so Stage 1 PRs know what to bump.

| Package | O3DE expects (stabilization/26050) | COPR has | Δ |
|---|---|---|---|
| AWSNativeSDK | 1.11.288-rev1 | 1.11.361 | patch-level mismatch (~70 patches) |
| qt | 5.15.2-rev9 | 5.15.1 | patch-level + verify rev9 patches present |
| astc-encoder | 3.2-rev2 | 5.3.0 | **major version mismatch (API change)** |
| PhysX 5 | 5.1.1-rev4 | 5.1.2 | patch-level mismatch |
| PhysX 4 | 4.1.2.29882248-rev8 | not packaged | **missing** — PhysX gem expects both 4 and 5 |
| AwsIotDeviceSdkCpp | 1.15.2-rev1 | 1.15.2 | matches |
| mikkelsen | 1.0.0.4 | 1.0 | matches |
| azslc | 1.8.22-rev1 | 1.8.22 | matches |
| ISPCTexComp | 36b80aa-rev1 | 0-0.4.20230807git691513b | same git ref |

Current state: irrelevant — we use `enable_net=true` and `LY_PACKAGE_SERVER_URLS` fetches the upstream-expected versions from `packages.o3de.org` regardless. Stage 1 is when each PR will need to (a) rebuild the COPR SRPM to the matching version OR (b) patch O3DE to accept the COPR version OR (c) configure O3DE to drop the legacy path entirely (PhysX 4 likely option). Each is a per-package decision.

## Migrate to system Fedora libs (Stage 1 — the long tail)

These have direct Fedora equivalents. Migration is per-package, low risk per migration, but ~20 PRs total.

| O3DE bundle | Bundled version | Fedora package | Fedora version (F44) | Notes |
|---|---|---|---|---|
| zlib | 1.2.11-rev5 | `zlib-devel` | 1.3.x | trivial flip |
| freetype | 2.11.1-rev1 | `freetype-devel` | 2.13.x | trivial flip |
| libcurl | (transitively) | `libcurl-devel` | 8.x | trivial flip |
| libpng | 1.6.37-rev2 | `libpng-devel` | 1.6.43+ | trivial flip |
| libtiff | 4.2.0.15-rev3 | `libtiff-devel` | 4.6.x | trivial flip |
| expat | 2.4.2-rev2 | `expat-devel` | 2.6.x | trivial flip |
| **SQLite** | 3.37.2-rev1 | `sqlite-devel` | 3.51.2 | **ACTIVATED in 10-pack (2026-05-08).** Audit (2026-05-07) found SQLite the cleanest Stage 1 candidate: consumers exclusively in `Code/Framework/AzToolsFramework/SQLite/` + `Code/Tools/AssetProcessor/AssetDatabase/` (editor/tool framework, not runtime). All 29 unique `sqlite3_*` symbols are core public C-API, 100% present in Fedora 3.51.2 headers. Zero extension-only API used (no FTS5/RTREE/JSON1/SEE). 3.37 → 3.51 is point-version increment within SQLite's 21-year ABI-stable major. Single-header include `<sqlite3.h>` matches Fedora layout exactly. Implementation note: the audit's "no Find shim needed" claim was slightly off — cmake's stock `FindSQLite3.cmake` creates `SQLite::SQLite3` as a side-effect IMPORTED target which trips O3DE's runtime walker (same issue as the original ZLIB shim). Implemented via `FindSQLite-system.cmake` (Source41, mikkelsen pattern: direct find_path/find_library, creates `3rdParty::SQLite` directly). Patch0006 extended with the `LY_USE_SYSTEM_SQLITE` gate hunk. Engine has an exact-match `sqlite3_libversion_number() == SQLITE_VERSION_NUMBER` runtime assertion — automatically satisfied by paired system header+library; not a blocker. Audit notes: `/tmp/o3de-assimp-audit/SQLITE_INVESTIGATION_NOTES.md`. |
| Lua | 5.4.4-rev1 | `lua-devel` | 5.4.7+ | trivial flip |
| lz4 | 1.9.4-rev2 | `lz4-devel` | 1.10.0 | **VALIDATED in 6-pack (2026-05-05)** — Findlz4-system.cmake mikkelsen-pattern (no stock include needed; cmake doesn't ship FindLZ4). Engine consumers use `#include <lz4.h>` / `<lz4hc.h>` / `<lz4frame.h>` verbatim, matching Fedora layout exactly — no wrapper bridging. Engine binaries auto-Require `liblz4.so.1()(64bit)`. lz4 1.10 has stable API back-compat with 1.9 (the engine's bundled major). |
| **libsamplerate** | 0.2.1-rev2 | `libsamplerate-devel` | 0.2.2 (BSD-2-Clause) | **Audited 2026-05-07 — Stage 1 viable + upstream-PR opportunity.** Single Gem (`Gems/Microphone/`); engine actually calls `src_*` functions only on Windows (`MicrophoneSystemComponent_Windows.cpp`). Linux PAL points to a `None` stub (do-nothing implementation) — **zero libsamplerate function calls in the Linux runtime path**, but the Gem unconditionally links `3rdParty::libsamplerate` per `Gems/Microphone/Code/CMakeLists.txt:25`. Bundle anchor on standard Patch0006 surface. 0.2.1 → 0.2.2 is patch-version increment within the 23-year ABI-stable major (since 0.1.0, 2002). No stock cmake module; pkg-config available (`samplerate.pc`) — Find shim via `pkg_check_modules(SAMPLERATE samplerate)`. **Stage 1 swap risk = essentially zero** (Linux runtime never exercises libsamplerate). **Upstream PR follow-on**: gate the `3rdParty::libsamplerate` dependency in Microphone's CMakeLists.txt on a `PAL_TRAIT_MICROPHONE_USES_LIBSAMPLERATE` flag (FALSE on Linux/None, TRUE elsewhere) — same shape as the AzCore Lua PR (#19733); drops the dependency entirely on Linux, cleaner long-term. Audit notes: `/tmp/o3de-assimp-audit/LIBSAMPLERATE_INVESTIGATION_NOTES.md`. |
| mcpp | 2.7.2_az.2-rev1 | `mcpp` | 2.7.x | O3DE uses an `_az` patched fork — verify base mcpp suffices. |
| **expat** | 2.4.2-rev2 | `expat-devel` | 2.6+ | **VALIDATED in 5-pack (2026-05-04)** — Patch0006 gate + Findexpat-system.cmake refactored to mikkelsen pattern (commit `0ca8e58`); preserves case-bridging role for bundled FindOpenColorIO. Engine binaries auto-Require `libexpat.so.1()(64bit)`. |
| **freetype** | 2.11.1-rev1 | `freetype-devel` | 2.14+ | **VALIDATED in 5-pack (2026-05-04)** — FindFreetype-system.cmake refactored (commit `6b14ffa`); single `/usr/include/freetype2` include dir covers both `<ft2build.h>` and `<freetype/...>` consumer forms. Engine binaries auto-Require `libfreetype.so.6()(64bit)`. |
| **Lua** | 5.4.4-rev1 | `lua-devel` | 5.4.8+ | **ACTIVATED in 9-pack (2026-05-07).** Patch0008 (commit `d69bb9c`) drops AzCore `ScriptContext.cpp`'s `#include <Lua/lobject.h>` — audit identified the only symbol consumed (`LUAI_MAXALIGN`) is already public Lua API via `luaconf.h`'s transitive include from `lauxlib.h`. Behavior-preserving; bundled-Lua builds also benefit (one fewer brittle internal-header dependency). Same patch was submitted upstream as o3de/o3de PR #19733 (approved by nick-l-o3de 2026-05-07, awaiting merge); when that merges, our Patch0008 becomes redundant. Originally framed as DEFERRED on build 10420435; the audit-pattern playbook ([feedback memory](#)) reframed it as a single-line carry-patch on 2026-05-07. |
| **mikkelsen** | 1.0.0.4 | `mikkelsen-devel` (from `hellaenergy/o3de-dependencies` COPR) | 1.0+git3e895b4 | **VALIDATED in 5-pack (re-validated 2026-05-04 against the rename)** — first validated 2026-05-03 (build 10419014). `--with system_mikkelsen` flips Patch0006 + Findmikkelsen-system.cmake on; engine binaries auto-Require `libmikktspace.so.0()(64bit)`. Live in `o3de-stabilization` since the o3de2605 promotion (2026-05-04). |
| **libpng** | 1.6.37-rev2 | `libpng-devel` | 1.6.56+ | **VALIDATED in 5-pack (2026-05-04)** — FindPNG-system.cmake refactored (commit `cba5059`); `find_library NAMES png16 png` covers Fedora's version-suffixed `libpng16.so.16`. Engine binaries auto-Require `libpng16.so.16()(64bit)` + `PNG16_0` versioned symbol. |
| **libtiff** | 4.2.0.15-rev3 | `libtiff-devel` | 4.6+ | **OPTION C — Bundling Library Exception path (decided 2026-05-05).** Patch0007 (deprecation migration in `TIFFLoader.cpp` + `ImageTIF.cpp`) stays in place; required regardless of system_tiff. Patch0008 (Option A: narrow `O3DE_SYSTEM_LIBTIFF_COMPAT` guard around CryCommon's int64/uint64 + SKIP_UNITY_BUILD_INCLUSION) was attempted (commit `cda6b7b`) and reverted (`9f2f099`) after a local `rpmbuild -bb --with system_tiff` failed at compile time: `Code/Legacy/CryCommon/Cry_ValidNumber.h` uses `uint64` directly in its own DoubleU64/DoubleU64ExpMask macros, transitively included via `EditorDefs.h` → `Cry_Math.h`, *before* `<tiffio.h>` brings libtiff's typedef into scope. Reordering tiffio.h ahead of engine headers compiles but ABI-mismatches at link (libtiff's `int64 = int64_t = long` LP64 vs CryCommon's exported `long long` mangling for `CryGetTicks()` and others). Option B (engine-wide CryCommon C99 migration) ruled out as too invasive. Decision: ship bundled libtiff-4.2.0.15-rev3 from packages.o3de.org indefinitely; file Bundling Library Exception with the rest of Stage 5. Bcond + FindTIFF-system.cmake + Source declaration stay declared but defaulted off in case future engine refactors make Option A viable. See spec changelog 2605.0-27 + `squeezing-typeface-tiffany.md` for the full diagnosis. |
| **zlib** | 1.2.11-rev5 | `zlib-devel` (resolved via Provides chain to `zlib-ng-compat` on F44+) | 2.3+ | **VALIDATED in 5-pack (2026-05-04)** — FindZLIB-system.cmake refactored (commit `92bde6e`); `ZLIB::ZLIB` alias of `3rdParty::ZLIB` satisfies bundled FindFreetype's `target_link_libraries(... ZLIB::ZLIB)`. Engine binaries auto-Require `libz.so.1()(64bit)` + version-specific symbols. |
| assimp | 5.4.3-rev3 | `assimp-devel` | 6.0.4 | **Audited 2026-05-07 — Stage 1 candidate with one caveat.** Consumers exclusively in `Code/Tools/SceneAPI/` (asset-pipeline tool); zero in `Gems/`, zero in core `Code/Framework/`. All 27 types + 7 processing flags engine consumes are public C-API (`ai*` prefix + `Assimp::Importer`); 100% present in Fedora 6.0.4 headers (verified via `dnf download` + `rpm2cpio` extraction). Engine include style `<assimp/header.h>` matches Fedora layout exactly — no path-bridging needed. Bundle anchor on standard Patch0006 surface. Fedora ships `assimpConfig.cmake` config-mode export — **no Find shim needed**, just `find_package(assimp CONFIG REQUIRED)`. FBX importer compiled into Fedora's libassimp.so.6.0.4 (verified via importer-descriptor strings). **Caveat:** 5.4 → 6.0 major version delta — symbols ✓ + link-time API will validate at build, but runtime FBX-import behavior on tricky inputs (subdivision surfaces, layered animations, embedded textures) is **unverified**. Mitigation: pair activation with a Tier 6 integration-test that bakes a known FBX (e.g. one from AutomatedTesting Gem) and smoke-tests output non-emptiness. **Simplest Stage 1 swap to date** — no shim, no `%prep cp`, no path-bridging. Audit notes: `/tmp/o3de-assimp-audit/INVESTIGATION_NOTES.md`. |
| ~~SPIRVCross~~ | — | — | — | **NOT a Stage 1 candidate (audit 2026-05-07).** Reclassified — see "Binary-only / DXC-class dependencies" section below. The "Fedora 1.3.x — trivial flip" annotation was wrong; Fedora doesn't ship SPIRV-Cross at all, and the engine treats it as an executable (not a library link) like DXC. |
| vulkan-validationlayers | 1.2.198-rev1 | `vulkan-validation-layers-devel` | 1.3.x | newer in Fedora; verify O3DE's loader interaction |
| googlebenchmark | 1.7.0-rev1 | `google-benchmark-devel` | 1.8.x | test-only; can drop entirely |
| **poly2tri** | 7f0487a-rev1 | `poly2tri-devel` | 0.0^20130501 (commit `26242d0a`, Mason Green BSD-3-Clause) | **NEW Stage 1 candidate (audit 2026-05-07, [#7](https://github.com/nickschuetz/o3de-rpm/issues/7))** — reframed from "off-limits restricted" after the audit found: (a) consumers exclusively in `Gems/PhysX/` (Editor's `PolygonPrismMeshUtils` for polygon-prism shape colliders; zero references in core `Code/`); (b) engine uses public `p2t::` namespace API only — no internal-symbol coupling; (c) Fedora's `poly2tri-devel` ships from Mason Green's BSD-3-Clause original tree, license-clean and independent of the bundled fork's attribution issue. Implemented as Patch0009 gating PhysX{4,5} `PAL_linux.cmake` on `LY_USE_SYSTEM_POLY2TRI`; `Findpoly2tri-system.cmake` bridges engine's `<poly2tri.h>` syntax to `/usr/include/poly2tri/poly2tri.h` via include-path adjustment. Spec: bcond + Source40 + conditional BR/Recommends/Requires/cmake -D + %prep cp. ABI compatibility (Fedora `0.0^20130501hg26242d0aa7b8` vs bundled `7f0487a-rev1`) inferred-with-high-confidence from public-API stability since 2013; **needs experimental-build verification**. |

### mikkelsen migration status

**State:** **validated in experimental channel as of 2026-05-03.** End-to-end COPR build (10419014) + test-installed.yml CI run (25277223923) on F44 + rawhide both green. The Tier 2 swap-consistency check (added at the same time as this migration's activation) confirmed the binary RPM declares both `Requires: mikkelsen` AND `libmikktspace.so.0()(64bit)` in its auto-Requires — the latter being rpm's own ldd-walk evidence that some shipped engine binary actually links the system library. Default-off in `o3de.spec`'s base configuration (so `o3de-stabilization` testers continue to consume the upstream-fetched bundle); default-on for the `srpm-experimental` Makefile target via `--with system_mikkelsen` and the matching `--rpmbuild-with system_mikkelsen` chroot config on `hellaenergy/o3de-experimental`. **Awaiting Nick's testing-window-closes signal before promoting to o3de-stabilization.**

**Activation summary (commit follows this doc update):**
- `o3de.spec`: `%bcond_with system_mikkelsen` (default off), conditional `BuildRequires: mikkelsen-devel`, conditional `Requires: mikkelsen`, conditional `cp` of `Source30` (`Findmikkelsen-system.cmake`) into `cmake/3rdParty/Findmikkelsen.cmake` during `%prep`, and conditional `-DLY_USE_SYSTEM_MIKKELSEN=ON` in the `%build` cmake invocation. Patch0006 applies unconditionally (no-op without the cmake variable set).
- `Makefile`: `srpm-experimental` target wraps `srpm-snapshot`'s build with `--with system_mikkelsen`. `copr-experimental` and `copr-experimental-and-test` consume that SRPM.

**Validation status:** local `rpmbuild -bp` confirmed Patch0006 applies cleanly to commit `246b46f` and the find module gets dropped into the right place. End-to-end COPR build + CI-test run pending (this is the first build to exercise the experimental channel and the migration template).

**Promotion to o3de-stabilization:** once an `o3de-experimental` build with `--with system_mikkelsen` passes the test-installed.yml workflow (Tier 1+2+3+6 across F44 + rawhide), the same SRPM can be uploaded to `o3de-stabilization` (the community testers' channel) for community validation — but only when Nick signals the testing window is open for new pushes. See `MEMORY.md` → "Active community testers on COPR".

**Pattern this template establishes:** every Stage 1 package gets its own `LY_USE_SYSTEM_<PACKAGE>` gate via the same patch shape, plus a `Find<package>-system.cmake`-style find module. Future migrations (zlib, freetype, libpng, …) follow this template — the diff for each is ~5 lines in `BuiltInPackages_linux_x86_64.cmake` plus one find module file plus ~6 lines in `o3de.spec` (bcond + Source + Patch + BR/Requires + prep cp + cmake flag) plus one line in `Makefile`'s `SRPM_EXPERIMENTAL_FLAGS`.

---

## Binary-only / DXC-class dependencies (Stage 2 sibling track)

Bundles where the engine **invokes an executable** (not a library link) — same architectural pattern: engine spawns the tool as a subprocess, doesn't `dlopen` anything. These can't be Stage-1-swapped because there's no library API to gate; the answer is to **build the upstream sources as a license-clean COPR package** and have the engine's runtime path point at the system-installed binary.

**Status as of 2026-05-07**: SPIRV-Cross PoC is ✓ green (rev2 succeeded, build 10434617, working `spirv-cross` binary verified). DXC PoC iterating (rev10 reached 99.5% of the build pipeline; rev11 in flight with the final transitive-link fix).

| Bundle | O3DE version | License | Fedora available? | Path |
|---|---|---|---|---|
| **DirectXShaderCompilerDxc** | 1.8.2505.1-o3de-rev3 | NCSA + Apache-2.0 (LLVM exception) | No | License-clean rebuild from upstream `o3de/DirectXShaderCompiler` at tag `release-1.8.2505.1-o3de`. PoC SRPM `o3de-dxc-spirv` iterating in `hellaenergy/o3de-dependencies` COPR (2026-05-07): rev4 → fail (52s, empty submodule placeholder dirs); rev5 → fail (1m08s, Patch0001 IS_DIRECTORY edge case); rev6 → fail (18s, Fedora `%%cmake` sets BUILD_SHARED_LIBS=ON which conflicts with DXC's clang-as-static expectation, cyclic-deps among `clangAST`/`clangCodeGen`/etc.); rev7 → fail (2m02s, step 188/1111, missing `git` BR); rev8 → fail (7m, `d3d12shader.h` not found — wrong DIRECTX_HEADER_INCLUDE_DIR path); rev9 → fail (7m, step 484/1111 = 44%, typedef conflict between Fedora's `/usr/include/wsl/stubs/basetsd.h` (`LONG = int32_t`) and DXC's own `include/dxc/WinAdapter.h` (`LONG = long` LP64) — structurally incompatible); rev10 → in flight, switches to bundled DirectX-Headers via Source2 pinned at DXC's submodule SHA `980971e` (verified via `gh api /repos/o3de/DirectXShaderCompiler/git/trees/release-1.8.2505.1-o3de:external`). Each iteration has revealed a deeper architectural assumption. Patch0001 redirects DXC's `external/CMakeLists.txt` to use Fedora's `spirv-headers-devel` + `spirv-tools-devel`. **Architectural lesson**: Fedora's DirectX-Headers is fine for projects that DON'T have their own Win-types compat layer; DXC has its own (`WinAdapter.h`), and the two layers can't coexist. Stage-1-style "use system Foo" doesn't work universally — some 3rdParty deps need to be bundled-as-source because of internal architectural assumptions. Engine shells out to `dxc` binary at shader-compile time per Nick_L (sig-build, 2026-05-05); does NOT link the DXC C++ library — same architectural pattern as SPIRV-Cross below. See `FEDORA_ROADMAP.md` § "License-clean DXC rebuild" + `project_dxc_binary_only_dependency.md` memory. |
| **SPIRVCross** | 1.3.275.0-rev1 | Apache-2.0 OR MIT (KhronosGroup) | **No** (audit 2026-05-07 confirmed Fedora F44 ships no SPIRV-Cross packages — neither `spirv-cross-devel` nor `spirv-cross-libs` nor `spirv-cross` binary) | **PoC ✓ GREEN as of 2026-05-07.** License-clean rebuild from upstream `KhronosGroup/SPIRV-Cross` at tag `vulkan-sdk-1.3.275.0` (SHA `117161dd5460`, verified via `o3de/3p-package-source/.../SPIRVCross/build_config.json`). PoC SRPM `o3de-spirv-cross` iterating in `hellaenergy/o3de-dependencies` COPR (2026-05-07): rev1 → fail (7s, `cmake_minimum_required` policy too low for Fedora 44's modern cmake); rev2 → **succeeded** (3m31s on F44 + rawhide; build 10434617). Built RPM (976KB compressed, 2.7MB installed) ships `/usr/bin/spirv-cross` + license files + README; functional verification confirmed `spirv-cross --help` works correctly. Engine shells out to `spirv-cross` binary at asset-build time (`Gems/Atom/RHI/Metal/Code/Source/RHI.Builders/ShaderPlatformInterface.cpp:331`); zero `#include` lines for SPIRV-Cross C++ headers anywhere in `Code/` or `Gems/`. Sibling track to DXC PoC. Working tree at `/home/nschuetz/o3de-spirv-cross-poc/` (local-only git repo; pre-no-upstream-until-baked stage). Audit notes: `/tmp/o3de-assimp-audit/SPIRVCROSS_INVESTIGATION_NOTES.md`. |

The "Fedora F44 1.3.x — trivial flip" annotation that previously appeared in the Stage 1 table for SPIRVCross was unverified guesswork; the audit produced the correct classification.

This section will grow as future audits identify other binary-only dependencies. Common shape: a path string of the form `"Builders/<X>/<x-binary>"` in `Gems/Atom/.../ShaderPlatformInterface*.cpp`, zero header `#include` lines, a cmake `3rdParty::<X>` target that's a runtime dependency on the executable. Same handling: COPR-build the upstream sources, point the engine's runtime invocation at the system binary.

---

## Big-media bundles (Stage 2 — version-pinning concerns)

These have Fedora equivalents but O3DE pins specific older API versions.

| Bundle | O3DE version | Fedora F44 | Concern |
|---|---|---|---|
| **OpenEXR + Imath** | 3.1.3-rev4 (bundle declares both targets) | openexr-3.2.4 + imath-3.1.12 | **VALIDATED in 7-pack (2026-05-07)** — two-shim design (`FindOpenEXR-system.cmake` + `FindImath-system.cmake`) creates both `3rdParty::OpenEXR` (links libOpenEXR + libOpenEXRCore + libIex + libIlmThread) and `3rdParty::Imath` (links libImath). Two shims rather than one: bundled FindOpenColorIO calls `find_package(Imath)` independently of OpenEXR, so `FindImath.cmake` must resolve on CMAKE_MODULE_PATH regardless of evaluation order. Engine consumers use `#include <OpenEXR/Imf*.h>` verbatim, matching Fedora layout. Per Nick_L 2026-05-05, version pins aren't hard; 3.1 → 3.2 is OpenEXR back-compat. Engine binaries auto-Require `libOpenEXR-3_2.so.31()(64bit)` + `libImath-3_1.so.29()(64bit)` + ancillary OpenEXR-family libs. |
| OpenImageIO | 2.3.17-rev2 | 3.x | **Stage 2b — blocked on Stage 3 (Python migration)** per Nick_L 2026-05-05. OIIO + OCIO are circularly dependent; both ship Python C Modules that must ABI-match the editor's embedded Python. Today's editor uses bundled Python 3.10; F44 has Python 3.13. System OIIO/OCIO Python C Modules link against 3.13 → ABI mismatch. Unblocks once editor uses system Python. |
| OpenColorIO | (bundled with OIIO) | 2.4.x | Same Stage 2b sub-track as OpenImageIO above. Circularly dependent + Python C Module ABI chain. |

---

## Bundles that have no clean migration target

| Bundle | Notes |
|---|---|
| Python 3.10.13-rev2 | Migrate to system Python 3.13 in Stage 3. F44 has 3.13; bundled is 3.10. PySide2 binding compatibility is the gating concern. |
| pyside2 5.15.2.1-py3.10-rev7 | Bundled because tied to bundled Python. F44 has `python3-pyside2` 5.15.x but built against 3.13 — should work after Stage 3. |
| OpenSSL 1.1.1t | **Stage 4. Major engineering effort.** EOL since 2023-09-11. Migration to system OpenSSL 3.x likely needs upstream O3DE patches across multiple Gems. |
| O3DE-clang-toolchain | Embedded clang/libclang. Build-time only; not in the runtime RPM. Probably remove the `__requires_exclude` workaround once Stage 5 cleans up build artifacts. |

---

## Justification template (for Fedora package review)

When the time comes to file the Bundled Library Exception, this is the bullet structure each entry needs:

> **Library:** `<name>` version `<version>`
> **Why bundled:** Custom patches that diverge from upstream and are required for O3DE to function correctly. *(For Qt-rev9 specifically: the engine's editor depends on the rev9-specific changes; same upstream version of Qt5 is not a substitute.)*
> **Why not packaging the patched version separately:** Patches are not generally useful outside O3DE; packaging would mean two parallel Qt5 packages in the system, conflicting on file paths.
> **Maintenance commitment:** We track upstream O3DE's rev bumps and rebuild the Fedora package within X days of an O3DE point release.
> **Security tracking:** When upstream Qt5 issues CVEs, we apply the fix on top of rev9 within Y days.

---

## Tracking

Update this file when a bundle migrates. Strike-through completed migrations rather than deleting them, so the history is visible to reviewers.
