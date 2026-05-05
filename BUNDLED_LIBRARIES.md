# Bundled libraries inventory

Per-bundle status of every package O3DE pulls from `packages.o3de.org` at cmake configure time. This is the working source for the **Bundled Library Exception** filing required by Fedora package review.

For each entry: name, version O3DE bundles, license, what's in Fedora today, status against the Fedora-inclusion roadmap, and a one-line justification (when applicable).

Categories below match `FEDORA_ROADMAP.md` stages.

---

## Restricted (cannot be packaged for COPR or Fedora)

These four are omitted from `hellaenergy/o3de-dependencies` and remain fetched from `packages.o3de.org` at build time. **They will never go into Fedora.** See `FEDORA_ROADMAP.md` § "Restricted bundles" for the three handling options.

| Package | O3DE version | Upstream license | Why restricted |
|---|---|---|---|
| **DirectXShaderCompilerDxc** | 1.8.2505.1-o3de-rev3 | NCSA / Apache-2.0 (sources) + proprietary DXIL signing | The DXIL signing tooling is Microsoft-proprietary. **DXC is structurally a fork of Clang/LLVM** — that's why the bundle ships `libclang-12.so.1` + `libtinfo.so.6` under `Builders/DirectXShaderCompiler/lib/` (RPATH-resolved internal stack, hence the spec's `%__requires_exclude`). Linux O3DE only uses DXC's SPIR-V backend, not DXIL — so a license-clean rebuild from upstream Microsoft DXC sources against system clang is feasible. See `FEDORA_ROADMAP.md` § "License-clean DXC rebuild" for the concrete plan. |
| **NvCloth** | v1.1.6-4-gd243404-pr58-rev1 | NVIDIA Source Code License | NVIDIA-specific clauses incompatible with Fedora's free-software requirements. |
| **poly2tri** | 7f0487a-rev1 | BSD-3-Clause (upstream) | The specific O3DE-vendored fork has license-attribution complications. |
| **squish-ccr** | deb557d-rev1 | MIT-like + patents | Texture-compression algorithms encumbered by BPTC/BC7 patents. |

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
| SQLite | 3.37.2-rev1 | `sqlite-devel` | 3.46.x | trivial flip |
| Lua | 5.4.4-rev1 | `lua-devel` | 5.4.7+ | trivial flip |
| lz4 | 1.9.4-rev2 | `lz4-devel` | 1.9.x | trivial flip |
| libsamplerate | 0.2.1-rev2 | `libsamplerate-devel` | 0.2.2 | trivial flip |
| mcpp | 2.7.2_az.2-rev1 | `mcpp` | 2.7.x | O3DE uses an `_az` patched fork — verify base mcpp suffices. |
| **expat** | 2.4.2-rev2 | `expat-devel` | 2.6+ | **VALIDATED in 5-pack (2026-05-04)** — Patch0006 gate + Findexpat-system.cmake refactored to mikkelsen pattern (commit `0ca8e58`); preserves case-bridging role for bundled FindOpenColorIO. Engine binaries auto-Require `libexpat.so.1()(64bit)`. |
| **freetype** | 2.11.1-rev1 | `freetype-devel` | 2.14+ | **VALIDATED in 5-pack (2026-05-04)** — FindFreetype-system.cmake refactored (commit `6b14ffa`); single `/usr/include/freetype2` include dir covers both `<ft2build.h>` and `<freetype/...>` consumer forms. Engine binaries auto-Require `libfreetype.so.6()(64bit)`. |
| **Lua** | 5.4.4-rev1 | `lua-devel` | 5.4.8+ | **DEFERRED.** AzCore `ScriptContext.cpp:28` uses `<Lua/lobject.h>` — Lua's *internal* header — for low-level type definitions. Fedora's lua-devel only ships the public API (lua.h, lauxlib.h, lualib.h, luaconf.h). Activation needs a carry-patch replacing the lobject.h usage with public API, or a different way to expose Lua's internal types. Bcond + FindLua-system.cmake + Source declaration stay in place for future activation. Discovered on build 10420435 (compile-time after the cmake-config issues were fixed). |
| **mikkelsen** | 1.0.0.4 | `mikkelsen-devel` (from `hellaenergy/o3de-dependencies` COPR) | 1.0+git3e895b4 | **VALIDATED in 5-pack (re-validated 2026-05-04 against the rename)** — first validated 2026-05-03 (build 10419014). `--with system_mikkelsen` flips Patch0006 + Findmikkelsen-system.cmake on; engine binaries auto-Require `libmikktspace.so.0()(64bit)`. Live in `o3de-stabilization` since the o3de2605 promotion (2026-05-04). |
| **libpng** | 1.6.37-rev2 | `libpng-devel` | 1.6.56+ | **VALIDATED in 5-pack (2026-05-04)** — FindPNG-system.cmake refactored (commit `cba5059`); `find_library NAMES png16 png` covers Fedora's version-suffixed `libpng16.so.16`. Engine binaries auto-Require `libpng16.so.16()(64bit)` + `PNG16_0` versioned symbol. |
| **libtiff** | 4.2.0.15-rev3 | `libtiff-devel` | 4.6+ | **VALIDATED in 6-pack (2026-05-05)** — Patch0007 (deprecation, already in place) handles `uint8`/`uint16`/`uint32` migration in `TIFFLoader.cpp` + `ImageTIF.cpp`. Patch0008 (new) closes the second layer: `O3DE_SYSTEM_LIBTIFF_COMPAT` guard macro suppresses CryCommon's `int64`/`uint64` typedefs in the two TIFF TUs only, paired with `SKIP_UNITY_BUILD_INCLUSION` so the macro doesn't leak through unity merging. FindTIFF-system.cmake refactored to mikkelsen pattern (no stock include); provides `TIFF::TIFF` as ALIAS of `3rdParty::TIFF` for upstream consumers (bundled FindOpenImageIO.cmake). Engine binaries auto-Require `libtiff.so.6()(64bit)`. |
| **zlib** | 1.2.11-rev5 | `zlib-devel` (resolved via Provides chain to `zlib-ng-compat` on F44+) | 2.3+ | **VALIDATED in 5-pack (2026-05-04)** — FindZLIB-system.cmake refactored (commit `92bde6e`); `ZLIB::ZLIB` alias of `3rdParty::ZLIB` satisfies bundled FindFreetype's `target_link_libraries(... ZLIB::ZLIB)`. Engine binaries auto-Require `libz.so.1()(64bit)` + version-specific symbols. |
| assimp | 5.4.3-rev3 | `assimp-devel` | 5.4.x | trivial flip |
| SPIRVCross | 1.3.275.0-rev1 | `spirv-cross-devel` | 1.3.x | trivial flip |
| vulkan-validationlayers | 1.2.198-rev1 | `vulkan-validation-layers-devel` | 1.3.x | newer in Fedora; verify O3DE's loader interaction |
| googlebenchmark | 1.7.0-rev1 | `google-benchmark-devel` | 1.8.x | test-only; can drop entirely |

### mikkelsen migration status

**State:** **validated in experimental channel as of 2026-05-03.** End-to-end COPR build (10419014) + test-installed.yml CI run (25277223923) on F44 + rawhide both green. The Tier 2 swap-consistency check (added at the same time as this migration's activation) confirmed the binary RPM declares both `Requires: mikkelsen` AND `libmikktspace.so.0()(64bit)` in its auto-Requires — the latter being rpm's own ldd-walk evidence that some shipped engine binary actually links the system library. Default-off in `o3de.spec`'s base configuration (so `o3de-stabilization` testers continue to consume the upstream-fetched bundle); default-on for the `srpm-experimental` Makefile target via `--with system_mikkelsen` and the matching `--rpmbuild-with system_mikkelsen` chroot config on `hellaenergy/o3de-experimental`. **Awaiting Nick's testing-window-closes signal before promoting to o3de-stabilization.**

**Activation summary (commit follows this doc update):**
- `o3de.spec`: `%bcond_with system_mikkelsen` (default off), conditional `BuildRequires: mikkelsen-devel`, conditional `Requires: mikkelsen`, conditional `cp` of `Source30` (`Findmikkelsen-system.cmake`) into `cmake/3rdParty/Findmikkelsen.cmake` during `%prep`, and conditional `-DLY_USE_SYSTEM_MIKKELSEN=ON` in the `%build` cmake invocation. Patch0006 applies unconditionally (no-op without the cmake variable set).
- `Makefile`: `srpm-experimental` target wraps `srpm-snapshot`'s build with `--with system_mikkelsen`. `copr-experimental` and `copr-experimental-and-test` consume that SRPM.

**Validation status:** local `rpmbuild -bp` confirmed Patch0006 applies cleanly to commit `246b46f` and the find module gets dropped into the right place. End-to-end COPR build + CI-test run pending (this is the first build to exercise the experimental channel and the migration template).

**Promotion to o3de-stabilization:** once an `o3de-experimental` build with `--with system_mikkelsen` passes the test-installed.yml workflow (Tier 1+2+3+6 across F44 + rawhide), the same SRPM can be uploaded to `o3de-stabilization` (the community testers' channel) for community validation — but only when Nick signals the testing window is open for new pushes. See `MEMORY.md` → "Active community testers on COPR".

**Pattern this template establishes:** every Stage 1 package gets its own `LY_USE_SYSTEM_<PACKAGE>` gate via the same patch shape, plus a `Find<package>-system.cmake`-style find module. Future migrations (zlib, freetype, libpng, …) follow this template — the diff for each is ~5 lines in `BuiltInPackages_linux_x86_64.cmake` plus one find module file plus ~6 lines in `o3de.spec` (bcond + Source + Patch + BR/Requires + prep cp + cmake flag) plus one line in `Makefile`'s `SRPM_EXPERIMENTAL_FLAGS`.

---

## Big-media bundles (Stage 2 — version-pinning concerns)

These have Fedora equivalents but O3DE pins specific older API versions.

| Bundle | O3DE version | Fedora F44 | Concern |
|---|---|---|---|
| OpenEXR | 3.1.3-rev4 | 3.x | Same major; minor API differences. Verify. |
| OpenImageIO | 2.3.17-rev2 | 3.x | **Major API break.** OIIO 3.x dropped some C-API symbols OIIO 2.x exposed. Likely needs O3DE patches. |
| OpenColorIO | (bundled with OIIO) | 2.4.x | Should be compatible. |

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
