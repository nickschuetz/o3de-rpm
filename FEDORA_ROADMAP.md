# Fedora-inclusion roadmap

The goal: get the stable `o3de` package into the **Fedora repository proper**. Until that's reached, COPR (`hellaenergy/o3de` + `hellaenergy/o3de-snapshot`) is the interim distribution channel.

Fedora is one of **three** distribution targets named in the README (COPR today, o3debinaries.org as the eventual upstream channel, Fedora long-term). A future Flathub release tracked in `FLATPAK_NOTES.md` and surfaced in `ARCHITECTURE.md` is *not* in the README — it would confuse RPM-focused readers — but most of the work here is shared infrastructure regardless: the system-lib migration, OpenSSL port, and license-clean DXC rebuild all benefit the o3debinaries.org submission and the eventual Flatpak too. Fedora is the strictest target; if we satisfy Fedora, we satisfy everything.

This document is the staged plan, dependency map, and decision log. It lives in the repo so contributors can see the state of each blocker without spelunking through commit history.

---

## Stage 0 — COPR (interim, today)

**Status:** ✅ unblocked, in progress. Continues indefinitely as the user-facing distribution while later stages land.

**Deliverables:**
- `hellaenergy/o3de-dependencies` — Fedora-clean SRPMs for O3DE 3rdParty packages not in Fedora.
- `hellaenergy/o3de` (tagged stable releases), `hellaenergy/o3de-stabilization` (community-tester channel; pre-release validation builds from `stabilization/<release>`), `hellaenergy/o3de-snapshot` (one-off / ad-hoc development-branch builds), and `hellaenergy/o3de-experimental` (in-flight Stage 1 migrations) — all built with `enable_net=true` so O3DE's `LY_PACKAGE_SERVER_URLS` fetcher can pull the four restricted bundles from `packages.o3de.org` (see "Restricted bundles" below).
- Spec validated end-to-end on F44 / commit `246b46f` from `stabilization/26050`. First public COPR build (10416727) was installed by Nick on 2026-05-02 from the project that became `o3de-stabilization` (it was named `o3de-snapshot` until 2026-05-03 when the project was renamed and `o3de-snapshot` was repurposed for one-off dev builds); confirmed working via Project Manager + Editor launch; community testers were invited that day.
- Test infrastructure (test-installed.yml in clean F44 + rawhide containers) wired up: cron-polling of `o3de-snapshot` every 4 hours, repository_dispatch for explicit `make trigger-tests` runs, manual workflow_dispatch for ad-hoc URL-driven tests. The `o3de-experimental` channel is exercised explicitly by `make copr-experimental-and-test`.
- **Versioned multi-install architecture** (committed 2026-05-03): packages ship as `o3deNNNN` (`o3de2605` for 26.05.x; `o3de2610` will land alongside when 26.10 stabilization begins) installing to `/opt/O3DE/<DISPLAY_VERSION>/`, mirroring upstream's `.deb` and `.msi` install layouts. Different majors are co-installable; per-major desktop entries, AppStream IDs (`org.o3de.O3DE2605`), and SBOMs. `Provides: o3de = %{version}-%{release}` so any external `Requires: o3de` still resolves. This baseline reduces packaging-review friction for both the o3debinaries.org submission and Fedora-proper review by aligning Fedora packaging with the upstream cross-platform install convention.
- **`engine.json` `engine_name` stays unversioned** (corrected 2026-05-04): the cmake `-DO3DE_INSTALL_ENGINE_NAME=o3de` literal sets engine.json's identity to upstream's pristine default — that's what gem manifests' `compatible_engines` lists check against (e.g. WarehouseAssets ships `["o3de-sdk>=2.3.0", "o3de>=2.3.0"]`). Setting engine_name to a versioned form (`o3de2605`) breaks every existing third-party gem because no gem's compatible_engines enumerates the versioned name. Trade-off: the manifest's `engines_path` map keys by `engine_name`, so multiple installed o3deNNNN majors collide on the `o3de` key — only ONE major is "registered" at a time; switching uses `<install-prefix>/scripts/o3de.sh register --this-engine` from the desired install root. This matches upstream's `.deb` multi-install UX exactly. The other versioned identities (RPM name, install path, desktop entries, AppStream id, dock WM_CLASS, SBOM) stay versioned — they don't enter the gem-compat check.
- **Subpackage split** (2026-05-04): main `o3de2605` ships runtime + project-build materials (engine `.so`s, headers, gem sources, scripts, runtime cmake, Templates). `o3de2605-devel` carves out the static archives (`lib/Linux/profile/Default/*.a` + `lib64/`, ~178 .a files, ~4 GB) for native C++ gem developers who static-link against engine internals. `o3de2605-debug` (only with `--with debug`) adds debug-config binaries + their static archives. Project-build `*-devel` system packages (clang, mesa-libGL[U]-devel, libxcb-devel, fontconfig-devel, libcurl-devel, pcre2-devel, openssl-devel, libunwind-devel, libzstd-devel, vim-common, plus per-active-swap mikkelsen-devel etc.) are pulled in via main's `Recommends:` so default `dnf install o3de2605` gives a working build experience. cmake also moved from Requires to Recommends; launcher's engine-id calc has bundled-cmake-fallback path baked in for future use.

**Status of `hellaenergy/o3de-dependencies`:** all 9 SRPMs have **succeeded builds** in COPR (verified via `copr-cli list-builds hellaenergy/o3de-dependencies`). Some required iteration — `o3de-qt5` took ten attempts before landing — but the repo is consumable today via `dnf copr enable hellaenergy/o3de-dependencies`. The remaining work for *integrating* those packages with the o3de spec (so cmake consumes them via `BuildRequires:` instead of fetching from `packages.o3de.org`) is Stage 1 below.

---

## Stage 1 — System library migration (the long tail)

**Status:** **5-pack validated locally (2026-05-04).** Activated in `o3de-experimental`: `expat`, `freetype`, `mikkelsen`, `libpng`, `zlib` — combined build via `make rpm-experimental` succeeded (47 min) with all 5 system libraries appearing in auto-Requires (`libz.so.1`, `libpng16.so.16` + `PNG16_0`, `libfreetype.so.6`, `libexpat.so.1`, `libmikktspace.so.0`). `libtiff` is deferred for a deeper CryCommon migration; `lua` is deferred for an AzCore carry-patch. Each deferral has its own write-up below.

  - **`expat` / `freetype` / `libpng` / `zlib` validated (2026-05-04)** — earlier failure (build 10421133, 2026-05-03) traced to each of these four `Find<X>-system.cmake` shims `include()`ing cmake's stock find module (FindZLIB.cmake / FindPNG.cmake / FindFreetype.cmake / FindEXPAT.cmake). The stock include's side-effect upper-namespace target (`ZLIB::ZLIB` etc.) had `MAP_IMPORTED_CONFIG_*` properties set but only the unconfigured `IMPORTED_LOCATION` populated, which O3DE's runtime walker bailed on. Refactored each shim to the mikkelsen pattern (commits `92bde6e` / `cba5059` / `6b14ffa` / `0ca58e8`): direct `find_path` + `find_library` inline, no stock-module include, construct `3rdParty::<X>` as INTERFACE IMPORTED GLOBAL, alias the upper-namespace target (`ZLIB::ZLIB` etc.) to satisfy upstream consumers (notably the bundled freetype's `target_link_libraries(... INTERFACE ZLIB::ZLIB)`). Each shim validated individually via isolated `rpmbuild --with system_<X>` builds (47-52 min each); combined 5-pack also validated. Pending: COPR cross-distro confirmation, then promotion to `o3de-stabilization`.
  - **`libtiff` — Option C, Bundling Library Exception path (decided 2026-05-05)** — Patch0007 (deprecation migration of `TIFFLoader.cpp` + `ImageTIF.cpp` to C99 typedefs) stays in place; required for *any* build against modern libtiff. The deeper int64/uint64 typedef collision (libtiff's `<tiff.h>`: `int64_t`/`uint64_t` = `long` on LP64; CryCommon's `BaseTypes.h`: `slonglong`/`ulonglong` = `long long`) was attempted via Patch0008 (a narrow `O3DE_SYSTEM_LIBTIFF_COMPAT` guard around CryCommon's typedefs + SKIP_UNITY_BUILD_INCLUSION on the two TIFF .cpp files; commit `cda6b7b`) and reverted (`9f2f099`) after a local `rpmbuild -bb --with system_tiff` failed at compile time in `Cry_ValidNumber.h` — that header uses `uint64` directly in its own DoubleU64/DoubleU64ExpMask/DoubleU64FracMask macros, transitively included from `EditorDefs.h` via `Cry_Math.h`, *before* `<tiffio.h>` brings libtiff's typedef into scope. Reordering `<tiffio.h>` ahead of the engine headers compiles cleanly (libtiff's int64/uint64 become visible in time) but introduces a `long` vs `long long` mangling mismatch at link time — `CryGetTicks()` and other engine symbols compiled against the engine-wide `slonglong` typedef export `long long` mangling, and the TIFF TU's call sites would mangle as `long`. Option B (engine-wide CryCommon C99 migration) is out of scope; Option C (file Bundling Library Exception alongside Qt 5.15-rev9) is the path. The bcond, Source declaration, FindTIFF-system.cmake, and Patch0007 stay in place — if a future engine refactor touches CryCommon's foundational typedefs upstream, system_tiff becomes activatable without packaging-track changes. See `squeezing-typeface-tiffany.md` for the full closeout.
  - **`lua` deferred** — needs a carry-patch to replace AzCore `ScriptContext.cpp`'s `<Lua/lobject.h>` (Lua internal header) with public API; Fedora's lua-devel doesn't ship internal headers.

Remaining unmigrated bundles (mcpp, vulkan-validationlayers, googlebenchmark, assimp, SPIRVCross/lz4/libsamplerate, libcurl/pcre2/SQLite, OpenEXR/OIIO/OCIO, pyside2) are deferred — see notes by each in the table. The mikkelsen-only baseline is what currently ships from `o3de-experimental`; the four ZLIB-class swaps will batch-promote to `o3de-stabilization` after the find-shim refactor lands and validates, in one coherent push so testers see one migration moment.

O3DE bundles ~30 3rdParty packages from its CDN at cmake configure time. Most of them have direct Fedora equivalents we can pivot to.

| Bundled package | Fedora package | Status / effort |
|---|---|---|
| **mikkelsen** | `mikkelsen-devel` (in `hellaenergy/o3de-dependencies` until Fedora-accepted) | **ACTIVATED in `o3de-experimental` channel** via `--with system_mikkelsen` (Patch0006 + Findmikkelsen-system.cmake) |
| zlib | `zlib-devel` | **validated 2026-05-04** (commit `92bde6e`, refactored to mikkelsen pattern + ZLIB::ZLIB alias for upstream consumers) |
| freetype | `freetype-devel` | **validated 2026-05-04** (commit `6b14ffa`, refactored to mikkelsen pattern; single include dir at `/usr/include/freetype2` covers both `<ft2build.h>` and `<freetype/...>` consumer forms) |
| libcurl | `libcurl-devel` | follow-on (use mikkelsen template) |
| libpng | `libpng-devel` | **validated 2026-05-04** (commit `cba5059`, refactored to mikkelsen pattern) |
| libtiff | `libtiff-devel` | **Option C — Bundling Library Exception** (2026-05-05) — Patch0008 narrow-guard attempt failed because CryCommon's own internal headers use `uint64` directly. Engine-wide CryCommon C99 migration (Option B) ruled out. Stays bundled. |
| expat | `expat-devel` | **validated 2026-05-04** (commit `0ca58e8`, refactored to mikkelsen pattern; preserves case-bridging role for `find_package(expat)` lowercase from bundled FindOpenColorIO; extracts `EXPAT_VERSION_STRING` from `XML_*_VERSION` macros in expat.h) |
| SQLite | `sqlite-devel` | follow-on (use mikkelsen template) |
| pcre2 | `pcre2-devel` | follow-on (use mikkelsen template) |
| Lua 5.4 | `lua-devel` | follow-on (use mikkelsen template) |
| lz4 | `lz4-devel` | follow-on (use mikkelsen template) |
| libsamplerate | `libsamplerate-devel` | follow-on (use mikkelsen template) |
| mcpp | `mcpp` | follow-on; O3DE uses `_az`-patched fork — verify base mcpp suffices |
| OpenEXR | `openexr-devel` | Stage 2 (version-pinning concerns) |
| OpenImageIO | `OpenImageIO-devel` | Stage 2 (version-pinning concerns) |
| OpenColorIO | `OpenColorIO-devel` | Stage 2 (version-pinning concerns) |
| assimp | `assimp-devel` | follow-on (use mikkelsen template) |
| SPIRVCross | `spirv-cross-devel` | follow-on (use mikkelsen template) |
| vulkan-validationlayers | `vulkan-validation-layers-devel` | follow-on; F44 has 1.3.x vs O3DE's 1.2.198 — verify loader interaction |
| googlebenchmark | `google-benchmark-devel` | test-only; can drop entirely |
| pyside2 | `python3-pyside2` | needs Stage 3 (Python migration) first |

**The validated migration pattern, ~6 spec lines + 1 cmake stub + 1 patch + 1 Makefile line:**

1. Add `%bcond_with system_<lib>` to `o3de.spec` (default off).
2. Carry a Patch000N that wraps the upstream `ly_associate_package(PACKAGE_NAME <lib>-X.Y.Z-linux ...)` line in `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` with `if(NOT LY_USE_SYSTEM_<LIB>) ... endif()`. Apply unconditionally — it's a no-op when the gate variable isn't set.
3. Carry a `sources/Find<lib>-system.cmake` find-module stub that creates the `3rdParty::<lib>` INTERFACE target from the system library (using `find_path` / `find_library`, plus a wrapper header in `${CMAKE_BINARY_DIR}` if the consumer's `#include <X/Y.h>` syntax doesn't match the system layout). Reference `Findmikkelsen-system.cmake` as the template.
4. Add `Source3X: Find<lib>-system.cmake` to the spec; conditionally `cp %{SOURCE3X} cmake/3rdParty/Find<lib>.cmake` in `%prep` when the bcond is on.
5. Add conditional `BuildRequires: <lib>-devel` and (if not already auto-detected) `Requires: <lib>` blocks gated on `%if %{with system_<lib>}`.
6. Add the conditional `-DLY_USE_SYSTEM_<LIB>=ON` to the cmake invocation in `%build` (use `%{?with_system_<lib>:-DLY_USE_SYSTEM_<LIB>=ON}` so the line vanishes when the bcond is off).
7. In `Makefile`, append `--with system_<lib>` to `SRPM_EXPERIMENTAL_FLAGS`.
8. **Activate the bcond on the COPR experimental chroots** with `copr-cli edit-chroot hellaenergy/o3de-experimental/<chroot> --rpmbuild-with system_<lib>` for both `fedora-44-x86_64` and `fedora-rawhide-x86_64`. **This step is load-bearing** — `--with` flags passed to `rpmbuild -bs` (the local SRPM build) do *not* propagate into COPR's binary `rpmbuild -bb` invocation, so the bcond conditionals would silently default off in the binary RPM otherwise. (Discovered the hard way on build 10417928.) `make copr-init` prints the exact command sequence.
9. Update `BUNDLED_LIBRARIES.md` (status table row + activation note) and the diagram in `ARCHITECTURE.md` if the change affects the displayed flow.

**Why we don't use O3DE's built-in `LY_BUILD_USE_SYSTEM_*` options (where they exist):** O3DE has variable coverage — some bundles have a built-in opt-out, others don't. The patch-based pattern works uniformly across all of them and doesn't depend on each upstream package having pre-built migration support. Once the pattern is upstreamable as a single coherent change ("here's the LY_USE_SYSTEM_<X> convention for all migration-eligible bundles"), submit it as one PR rather than one per bundle.

**Promotion to `o3de-snapshot`:** each migration that passes test-installed.yml end-to-end on the experimental channel is eligible for promotion to the snapshot channel — but only when Nick signals the testing window is open for new pushes. Until then, `o3de-experimental` accumulates the validated activations and `o3de-snapshot` stays stable.

---

## Stage 2 — Big-media bundle migration

**Status:** dependent on Stage 1 + version-checking.

OpenEXR / OpenImageIO / OpenColorIO are split out from Stage 1 because they pin specific API versions:

- O3DE bundles `OpenEXR-3.1.3-rev4-linux`. Fedora 44 ships OpenEXR 3.x. Likely compatible; verify.
- O3DE bundles `openimageio-opencolorio-2.3.17-rev2-linux`. Fedora 44 ships OIIO 3.x. **Likely API-incompatible** — needs O3DE upstream patches.

If the API gap is too large, this stage may temporarily stay bundled until O3DE upstream catches up.

---

## Stage 3 — Python migration (3.10 → system)

**Status:** unblocked, moderate effort.

Today: O3DE bundles Python 3.10.13 from `packages.o3de.org` and creates a per-user venv at `~/.o3de/Python/venv/<engine-id>/lib/python3.10/`. The launcher's `O3DE_PYTHON_VERSION` env var (default `3.10`) is already parameterized for this migration.

Target: use system Python (currently 3.13 in F44, 3.12 in RHEL 10).

**Steps:**
1. Patch `python/get_python.sh` to skip the bundled-Python download path entirely when `LY_USE_SYSTEM_PYTHON=ON` is set.
2. Patch `python/python.sh` and `python/pip.sh` to invoke `/usr/bin/python3` instead of the bundled `runtime/python-3.10.x-rev2-linux/python/bin/python3`.
3. Patch `cmake/LYPython.cmake` to honor system Python.
4. Update `requirements.txt` for any deps that pin Python 3.10 (look at PySide2 specifically — system pyside2 is on 3.13).
5. Bump `%global o3de_bundled_python` semantics: it becomes "the system Python series" instead of "the bundled Python series".
6. Validate `o3de.sh register --this-engine`, the editor launch, and Project Manager end-to-end.

**Risk:** PySide2 has been unmaintained since 2024-12. Some O3DE Python tooling depends on it. F44's `python3-pyside2` is on 5.15.x but built against 3.13. The editor's Python bindings will need patching.

---

## Stage 4 — Crypto migration (OpenSSL 1.1.1t → system 3.x)

**Status:** likely upstream-blocked.

Today: O3DE bundles OpenSSL 1.1.1t (EOL since 2023-09-11). Both COPR's policy and Fedora's are unsympathetic to vendored EOL crypto libraries.

Target: system OpenSSL 3.x.

**Why it's hard:**
- O3DE C++ code that uses OpenSSL is scattered across multiple Gems (HttpRequestor, AWSCore, etc.).
- 1.1 → 3.0 is a major API break (deprecated `EVP_*` functions, `BIO_*` changes, `SSL_*` ABI shifts).
- Each affected Gem needs porting + testing.
- Likely needs upstream cooperation; we can patch in our spec but it's a maintenance burden.

**Path forward:**
- File the migration request upstream with O3DE.
- Volunteer to do the porting work if upstream doesn't have bandwidth.
- Until done, the Fedora variant either ships affected Gems disabled or uses the runtime-fetcher pattern (see "Restricted bundles" below).

---

## Stage 5 — Compliance polish

**Status:** dependent on Stages 1–4 reaching mostly-done; some items are independent.

| Item | Description | Independent? |
|---|---|---|
| **License-clean DXC rebuild** | See dedicated section below. Highest-leverage Stage 5 task. | yes (mostly) |
| Real `-debuginfo` subpackage | Distinct from the existing `o3deNNNN-debug` subpackage (which ships debug-config binaries alongside the profile build). Fedora's `-debuginfo` is the rpmbuild-extracted symbol files for stripped binaries — currently disabled via `%global debug_package %{nil}` because O3DE's binary layout trips rpmbuild's symbol extraction (likely a `BUILD_ID` ambiguity from the Ninja Multi-Config split). May need patches to O3DE's link rules. | yes |
| `-debugsource` subpackage | Source code corresponding to each debuginfo line. Should fall out automatically once `debuginfo` works. | yes |
| Bundled Library Exception filing | Required for the custom Qt 5.15-rev9 (load-bearing). Justification doc in `BUNDLED_LIBRARIES.md`. | yes |
| Mock-clean SRPM build | `mock --rebuild o3de.src.rpm` must succeed with `--isolation=simple --no-network` enabled. | needs Stage 1 / 2 / 3 |
| Reproducible build | byte-identical RPM from the same SRPM on different hosts | needs all earlier stages |
| AppStream `<screenshots>` | Required by Flathub; nice-to-have for Fedora. Need actual editor screenshots from a working install. | yes |
| `<content_rating>` review | Currently `oars-1.1` empty (which means "no objectionable content"). Verify with O3DE upstream that no mature-content engine features need flagging. | yes |

### License-clean DXC rebuild — the critical sub-task

**Why this is on the critical path:** DXC is the only one of the four restricted bundles that's **non-optional for engine use** (see § "Restricted bundles" below — without DXC, the engine can't compile shaders). NvCloth/poly2tri/squish-ccr are all feature-gated and can be runtime-fetched (handling option B). DXC alone needs a different solution.

**The opportunity:** The licensing problem is *only* the Windows DXIL signing tooling, not DXC itself. The HLSL → SPIR-V (Vulkan) code path is fully open-source under NCSA/Apache-2.0. Linux O3DE doesn't use the DXIL path at all. So we can ship a Linux-only DXC built from upstream Microsoft sources without the DXIL bits, and it's redistributable.

**The technical context, so the work is unambiguous when we get to it:**

DXC is a fork of Clang/LLVM, not a separate project. Microsoft forked Clang ~2017 to add an HLSL frontend. Internally, DXC is structurally a full Clang/LLVM build with:
- HLSL parser/AST (alongside Clang's existing C/C++ frontend)
- DXIL backend (Windows shader format — the licensed-encumbered piece)
- SPIR-V backend (cross-platform — what we want)

This is also why the bundled DXC carries `libclang-12.so.1` and `libtinfo.so.6` — those are DXC's own internal LLVM 12 stack, RPATH-resolved from `Builders/DirectXShaderCompiler/lib/`. It's also why we need `%__requires_exclude` in the spec today.

**The migration plan (when we reach Stage 5):**

1. Build upstream Microsoft DXC (`github.com/microsoft/DirectXShaderCompiler`) from source against system clang/LLVM (Fedora 44 ships clang 22). The version we need to match is whatever O3DE's `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` pins — currently DXC `1.8.2505.1-o3de-rev3`.
2. Configure the build SPIR-V-only:
   ```
   -DENABLE_SPIRV_CODEGEN=ON
   -DSPIRV_BUILD_TESTS=OFF
   -DCLANG_INCLUDE_TESTS=OFF
   ```
   Do *not* enable any DXIL-target options.
3. Verify the resulting `libdxcompiler.so` and `dxc` binary link against system `libclang`/`libLLVM`, not bundled copies — `ldd` should show `/usr/lib64/libclang.so.*` etc.
4. Package as a new `o3de-dxc-spirv` SRPM in `hellaenergy/o3de-dependencies` (the COPR repo with `enable_net=false`). License is NCSA + Apache-2.0 with LLVM exception, both Fedora-compatible.
5. In `o3de.spec`, drop the upstream DXC fetch (remove the package from `BuiltInPackages_linux_x86_64.cmake` via patch), add `BuildRequires: o3de-dxc-spirv-devel`, and patch O3DE's cmake to find DXC via pkg-config or a `LY_DXC_PATH` cmake var.
6. **Drop** the `%__requires_exclude ^libclang-12\.so.*|^libtinfo\.so\.6.*` line from the spec (it's only there because DXC's bundled libclang/libtinfo aren't auto-Provided by rpm — system libclang from a clean rebuild *is*).

**Side benefits of completing this:**
- Eliminates the only mandatory restricted bundle, leaving NvCloth/poly2tri/squish as purely optional feature-gated bits (handling option A becomes viable).
- Drops the `__requires_exclude` workaround (one fewer thing to justify in the Fedora package review).
- Reduces the runtime-fetcher surface area dramatically — most users won't need it at all.

**Risk:** O3DE may have applied custom patches on top of upstream DXC for the `1.8.2505.1-o3de-rev3` build (the `-o3de-rev3` suffix suggests it). If those patches are non-trivial, we'd need to track them and rebase onto whatever DXC version we ship. Worth investigating early — `git log` on O3DE's DXC fork (if there is one) or the patch set inside the bundled tarball.

---

## Stage 6 — Submit to Fedora

**Status:** target.

When stages 1–5 are done:

1. Create a Fedora packager account (FAS).
2. Find a sponsor for the new package review.
3. File a Fedora Package Review bug at `bugzilla.redhat.com/enter_bug.cgi?product=Fedora&component=Package%20Review`.
4. Iterate on review feedback.
5. Once approved: `fedpkg request-repo o3de`, push to dist-git, build via Koji.

Realistic timeline from today: **9–18 months**. The crypto migration (Stage 4) is the wild card.

---

## Restricted bundles — the off-limits four

These four upstream-bundled packages **cannot** be hosted in COPR or Fedora because of license/redistribution conflicts. This is documented in `BUNDLED_LIBRARIES.md` per package, but called out here because it shapes the entire Fedora-inclusion strategy:

| Package | Why off-limits | What it enables |
|---|---|---|
| **DirectXShaderCompilerDxc** | Microsoft tooling with redistribution restrictions on DXIL signing | shader compilation — **non-optional** for engine use |
| **NvCloth** | NVIDIA proprietary, not Fedora-acceptable | the NvCloth Gem (cloth simulation) — optional |
| **poly2tri** | Specific O3DE-vendored fork has license-attribution issues | navmesh generation — significant feature |
| **squish-ccr** | Patent-encumbered texture compression algorithms | ImageProcessing Gem (asset bake) — significant |

**Three handling options for the Fedora-shippable variant:**

| Option | Description | Pro | Con |
|---|---|---|---|
| A. Disable affected Gems | Drop NvCloth Gem, replace squish with a system substitute, skip navmesh features | clean license posture | feature loss; DXC is still required so this alone isn't sufficient |
| B. Runtime fetcher | `/opt/O3DE/<version>/python/fetch-restricted-deps.sh` — one-time post-install opt-in mirroring `get_python.sh`; downloads to `~/.o3de/3rdParty/` from `packages.o3de.org` | full feature set | requires user network action; some Fedora reviewers disapprove of this pattern |
| C. License-clean DXC rebuild | Build DXC from upstream NCSA/Apache-2.0 sources, configured Vulkan-only / SPIR-V-output (no Windows DXIL signing). Combined with A or B for the others. | best license posture | most engineering effort |

**Current preference:** **B** for short-term Fedora viability + **C as a follow-up** to reduce the runtime-fetch surface to just NvCloth/poly2tri/squish (all optional/feature-gated). DXC is the load-bearing one — making it license-clean is the hardest single win.

---

---

## Parallel goal — o3debinaries.org upstreaming

Independent track from Fedora-inclusion but **uses much of the same prep work**. The aim is to get the spec accepted into the upstream O3DE source tree so O3DE's own CI builds the RPM and hosts it at o3debinaries.org alongside the .deb / snap / Windows packages.

What's tractable today:
- The spec is already distribution-agnostic at the rpmbuild level. `hellaenergy/`-specific bits live in the Makefile (`copr-stable`/`copr-snapshot` targets), not in the spec or sources/. Upstream can adopt the spec verbatim.
- `make-snapshot-tarball.sh` and the patch files are similarly portable.
- The `--with snapshot` mode is what their CI would use for nightly builds; the default-mode is for tagged releases.

What's gated:
- O3DE's `cmake/Platform/Linux/Packaging/` directory may already have RPM packaging or .deb packaging conventions to align with. Need to study before submitting.
- The hellaenergy/o3de-dependencies COPR repo needs an upstream equivalent — those SRPMs (custom Qt 5.15-rev9, PhysX, AWSNativeSDK, …) need to either land at packages.o3de.org alongside the existing pre-built tarballs, or be packaged inline in the upstream spec via the `%bcond_with thirdparty_*` machinery.
- O3DE upstream's release engineering team needs to be in the loop. A pre-submission discussion in the O3DE community channel is the right starting point.

Stages 1–4 of the Fedora roadmap (system-lib migration, big-media bundles, Python migration, OpenSSL port) **all directly benefit upstreaming** — they reduce the bundled surface area, which makes the spec more maintainable upstream too. Stage 5's license-clean DXC rebuild also benefits upstream.

The submission process is much shorter than Fedora's: open a PR against the O3DE repo with the spec + sources/, get review from O3DE maintainers, iterate, merge. No FAS account, no sponsor, no Bugzilla bug — just a regular GitHub PR. Realistic timeline once Stages 1–3 are done: **2–4 months** for upstream PR review.

---

## Tracking

This document is the source of truth for stage status. Update this file (and link from PRs) whenever a stage moves forward.
