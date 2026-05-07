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

**Status:** **7-pack validated end-to-end on `o3de-experimental` (2026-05-07)** — extends the 6-pack with the Stage 2a OpenEXR + Imath swap (first cross-stage step). Build 10430726 succeeded on F44 + rawhide; CI run 25475307693 passed Tiers 1+2+4+6 on both chroots (after a transient artifact-corruption flake in the prior run, fixed in commit `c57f5d8` by dropping the workflow's prepare-job artifact roundtrip). The 6-pack (`expat`, `freetype`, `lz4`, `mikkelsen`, `libpng`, `zlib`) was validated end-to-end 2026-05-05 (build 10426632 + CI 25402407670). The 7-pack adds `openexr` — `FindOpenEXR-system.cmake` is one half of the two-shim design (the other is `FindImath-system.cmake`); together they create `3rdParty::OpenEXR` (linking libOpenEXR + libOpenEXRCore + libIex + libIlmThread) and `3rdParty::Imath` (linking libImath), mirroring the bundle's `TARGETS OpenEXR Imath` declaration. Engine consumers (`Gems/Atom/Asset/ImageProcessingAtom/.../ExrLoader.cpp`) use `#include <OpenEXR/Imf*.h>` verbatim, matching Fedora's openexr-devel + imath-devel layout exactly. Per Nick_L (2026-05-05, [#5](https://github.com/nickschuetz/o3de-rpm/issues/5)), OpenEXR's version pin in O3DE is not hard; F44's openexr-3.2.4 + imath-3.1.12 are API-compatible with the bundle's 3.1.3. **Eligible for promotion to `o3de-stabilization`** whenever Mike's tester signal on the current stabilization build comes back positive (active-testers-window rule). The Stage 2b sibling sub-track (OpenImageIO + OpenColorIO) is NOT activated here — blocked on Stage 3 (Python migration) per Nick_L's circular-dependency + Python C Module ABI explanation. `libtiff` settled into Option C (Bundling Library Exception path) on 2026-05-05; `lua` remains deferred pending AzCore investigation.

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
| lz4 | `lz4-devel` | **validated in 6-pack 2026-05-05** — Findlz4-system.cmake mikkelsen-pattern; consumers use `<lz4.h>` directly (Fedora layout matches verbatim) |
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

### How upstream contributors can help (Stage 1)

These are the Stage 1 bundles where outside-the-packager visibility would unblock specific work. Each ask has a tracking issue — comment there or in #sig-build, both are watched. **Some asks are answered as of 2026-05-05 (Nick_L on sig-build); see issue comments for details.**

- **`system_lua` — AzCore's internal-header dependency.** [#1](https://github.com/nickschuetz/o3de-rpm/issues/1) — **needs investigation** (Nick_L 2026-05-05: "as for lua, no idea, I'd have ot just investigate it"). `Code/Framework/AzCore/.../ScriptContext.cpp` includes Lua's *internal* `<Lua/lobject.h>` header for low-level type definitions. Fedora's `lua-devel` only ships the public API (`lua.h`, `lauxlib.h`, `lualib.h`, `luaconf.h`). Question: is the internal-header use load-bearing, or could AzCore migrate to public-API-only (or vendor the needed type definitions inline)? This is currently the only blocker for `system_lua` activation. Two paths to resolution: upstream-side investigation (Nick_L or another contributor with engine context) or packaging-side investigation (we read the AzCore source ourselves and propose a migration as a draft PR). Both produce the same eventual outcome.
- **`system_tiff` — CryCommon `int64`/`uint64` typedef migration.** [#2](https://github.com/nickschuetz/o3de-rpm/issues/2) — **REFRAMED as actionable engine-maintenance work** (Nick_L 2026-05-05: "most of them are just legacy housework like, the uint64 stuff"). The migration is now characterized by upstream as legacy housework rather than out-of-scope. Anyone who picks up the engine-side PR (CryCommon's `int64`/`uint64` from `slonglong`/`ulonglong` to `int64_t`/`uint64_t`, with cross-platform format-specifier audit) unblocks `system_tiff` for free. Until someone does, libtiff stays bundled under Option C.
- **`mcpp` `_az` fork delta.** [#3](https://github.com/nickschuetz/o3de-rpm/issues/3) — **CLOSED, reframed as architectural choice** (Nick_L 2026-05-05: "we really just need any preprocessor that can run on c-like files"). mcpp's only role is `#ifdef` expansion in AZSL/AZSLI shader files; could be replaced with a Python plugin or system clang `-E`. Not a packaging concern; closing the question.
- **`AWSNativeSDK` + `AwsIotDeviceSdkCpp` libcurl bundling.** [#4](https://github.com/nickschuetz/o3de-rpm/issues/4) — **CLOSED, resolves via upstream direction** (Nick_L 2026-05-05: "AWS SDK should be excised from O3DE entirely tbh, so curl and such should be entirely a non issue"). When upstream excises AWS SDK from core O3DE, the libcurl transitive bundling problem disappears.

---

## Stage 2 — Big-media bundle migration

**Status:** **two sub-tracks** with different blocking conditions, per Nick_L's 2026-05-05 sig-build response (see [#5](https://github.com/nickschuetz/o3de-rpm/issues/5)).

### Stage 2a — OpenEXR + Imath (Stage-1.5; independent of Stage 3)

**Status:** **staged 2026-05-06; awaiting local + COPR validation.** Implementation lives in commit (TBD) — Patch0006 extended with `LY_USE_SYSTEM_OPENEXR` gate, new `FindOpenEXR-system.cmake` mikkelsen-pattern shim, spec wiring, Makefile + lockstep docs. Pre-validation: spec parses cleanly under all bcond modes, patch dry-run applies on a fresh tarball.

O3DE bundles `OpenEXR-3.1.3-rev4-linux`. F44 ships `openexr-devel-3.2.4` + `imath-devel-3.1.12`. The [O3DE build_config.json](https://github.com/o3de/3p-package-source/blob/main/package-system/OpenEXR/build_config.json) **does not patch OpenEXR**; per Nick_L 2026-05-05 ([#5](https://github.com/nickschuetz/o3de-rpm/issues/5)), version pins aren't hard. OpenEXR's only dependencies are Imath (sibling project, separate Fedora package) and zlib (already system-swapped in our 6-pack).

**No Python C Module** — pure C++. So Stage 2a ships independently of Stage 3 (Python migration). Effectively this is "Stage 1.5 — extends the 6-pack to 7-pack" rather than a hard Stage-2 boundary.

### Stage 2b — OpenImageIO + OpenColorIO (blocked on Stage 3)

**Status:** blocked on Stage 3 (Python migration to system Python).

O3DE bundles `openimageio-opencolorio-2.3.17-rev2-linux` (combined). The blocker isn't the C++ ABI — version pins aren't hard. The blocker is the **Python C Module ABI chain**:

- OpenImageIO and OpenColorIO are circularly dependent (one wraps the other)
- Both ship Python C Modules (Python bindings)
- Those Python C Modules must link against the same Python the editor's embedded Python uses
- Today: O3DE's editor links against bundled Python 3.10; F44 ships Python 3.13. System OIIO/OCIO Python C Modules link against 3.13 → ABI mismatch
- **Unblocks once Stage 3 lands** — when editor uses system Python, system OIIO/OCIO Python C Modules ABI-match

### How upstream contributors can help (Stage 2)

- **Version-pinning strictness.** [#5](https://github.com/nickschuetz/o3de-rpm/issues/5) — **ANSWERED** (Nick_L 2026-05-05). Pins are not hard for OpenEXR; for OIIO/OCIO the binding constraint is Python C Module ABI compat with the editor's embedded Python (which makes Stage 2b a Stage-3 dependency).

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

### How upstream contributors can help (Stage 3)

- **PySide2 → PySide6 migration timeline.** PySide2 is unmaintained upstream since 2024-12. Fedora ships pyside6 (PySide6 is actively maintained against PyQt 6 / Qt 6). Question: is there an upstream timeline or active work for the PySide2 → PySide6 migration? Linux-side, this is the gating dependency for system-Python; if upstream has a target window we can sequence Stage 3 work against it instead of doing carry-patches that conflict with the upstream migration.

---

## Stage 4 — Crypto migration (OpenSSL 1.1.1t → system 3.x)

**Status:** likely upstream-blocked, but the migration scope shrank 2026-05-05 with the AWS-SDK-excision news.

Today: O3DE bundles OpenSSL 1.1.1t (EOL since 2023-09-11 — 2.5+ years of CVE exposure if shipped today). Both COPR's policy and Fedora's are unsympathetic to vendored EOL crypto libraries.

Target: system OpenSSL 3.x.

**What just changed:** Per Nick_L's 2026-05-05 sig-build update (see [#4](https://github.com/nickschuetz/o3de-rpm/issues/4) / `project_aws_sdk_excision.md`), AWS SDK is being excised from core O3DE entirely; AWS-related Gems move to AWS-maintained O3DE repos. `AWSCore`'s OpenSSL usage leaves with it (out of our packaging scope). The remaining post-excision OpenSSL surface in core is **HttpRequestor and possibly others** (specifics still TBD — see [#8](https://github.com/nickschuetz/o3de-rpm/issues/8)).

**Why it's still hard:**
- 1.1 → 3.0 is a major API break (deprecated `EVP_*` functions, `BIO_*` changes, `SSL_*` ABI shifts).
- Each affected Gem still needs porting + testing.
- Likely needs upstream cooperation; we can patch in our spec but it's a maintenance burden.

**Path forward:**
- File the migration request upstream with O3DE (in flight via [#8](https://github.com/nickschuetz/o3de-rpm/issues/8)).
- Confirm post-AWS-excision OpenSSL surface — possibly just HttpRequestor (which itself may be libcurl-wrapped, in which case switching to a modern system libcurl bypasses the porting work entirely).
- Volunteer to do the porting work if upstream doesn't have bandwidth.
- Until done, the Fedora variant either ships affected Gems disabled or uses the runtime-fetcher pattern (see "Restricted bundles" below).

### How upstream contributors can help (Stage 4)

- **OpenSSL 3.x migration: timeline + remaining consumers.** [#8](https://github.com/nickschuetz/o3de-rpm/issues/8) — open. Three sub-questions: (1) any upstream signal on the migration; (2) post-AWS-excision, which Gems still consume OpenSSL in core; (3) are any of those consumers thin enough to replace via libcurl-wrapped-system-OpenSSL rather than direct porting? Stage 4 is currently the wild-card on the Fedora-roadmap timeline; even rough signal scopes whether it's trivial / moderate / hard.

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

**Why this is on the critical path:** DXC is the only one of the four restricted bundles that's **non-optional for engine use** — without DXC, the engine can't compile shaders. NvCloth/poly2tri/squish-ccr are all feature-gated (NvCloth appears Gem-isolated based on Cheddarspice's 2026-05-06 limited-scope cloth test — see "Restricted bundles" below).

**The opportunity:** The licensing problem is *only* the Windows DXIL signing tooling, not DXC itself. The HLSL → SPIR-V (Vulkan) code path is fully open-source under NCSA/Apache-2.0. Linux O3DE doesn't use the DXIL path at all. So we can ship a Linux-only DXC built from upstream Microsoft sources without the DXIL bits, and it's redistributable.

**The technical context** (massively simplified by Nick_L's 2026-05-05 sig-build response — see [#6](https://github.com/nickschuetz/o3de-rpm/issues/6)):

- **The engine doesn't link DXC at all.** No `libdxcompiler.so` linkage; DXC is a runtime/tool-time **binary** dependency only. The engine shells out to the `dxc` executable to compile shaders. **No library API surface to match in the rebuild.**
- DXC is a fork of Clang/LLVM (Microsoft forked Clang ~2017 to add an HLSL frontend). The bundled DXC carries `libclang-12.so.1` and `libtinfo.so.6` because the *bundled `dxc` binary* RPATH-resolves them — they're DXC's own internal LLVM 12 stack, not engine consumers. A clean rebuild against system clang/LLVM eliminates the `%__requires_exclude` workaround.
- The bundle pinning convention: `1.8.2505.1-o3de-rev3` decomposes as **source git tag** (`release-1.8.2505.1-o3de` in the [o3de/DirectXShaderCompiler](https://github.com/o3de/DirectXShaderCompiler/tree/release-1.8.2505.1-o3de) fork) plus the **package-system revision counter** (`-rev3`, just rebuilds of the same source). Build recipe lives in [`o3de/3p-package-source/tree/main/package-system/DirectXShaderCompiler`](https://github.com/o3de/3p-package-source/tree/main/package-system/DirectXShaderCompiler) — `build_config.json` has the canonical `package_url` + `git_tag`.
- The carry-patch is **4 commits**: [`microsoft:release-1.8.2505...o3de:DirectXShaderCompiler:release-1.8.2505.1-o3de`](https://github.com/microsoft/DirectXShaderCompiler/compare/release-1.8.2505...o3de:DirectXShaderCompiler:release-1.8.2505.1-o3de). One Linux compile fix, one adds a `dxsc` tool, others are general improvements that "should be contrib'd upstream tbh" per Nick_L. We can apply the diff as a custom patch on top of upstream Microsoft sources (`microsoft:release-1.8.2505`).

**The migration plan (when we reach Stage 5):**

1. Build upstream Microsoft DXC (`github.com/microsoft/DirectXShaderCompiler` at `release-1.8.2505`) from source against system clang/LLVM (Fedora 44 ships clang 22). Apply the 4-commit carry-patch from `o3de:release-1.8.2505.1-o3de` as a packaging-side patch (or vendor the diff into the build recipe).
2. Configure the build SPIR-V-only:
   ```
   -DENABLE_SPIRV_CODEGEN=ON
   -DSPIRV_BUILD_TESTS=OFF
   -DCLANG_INCLUDE_TESTS=OFF
   ```
   Do *not* enable any DXIL-target options.
3. Verify the resulting `dxc` binary works against the engine: feed it a sample shader, get back valid SPIR-V output. **No library-linking concerns** — the engine just shells out to `dxc`.
4. Package as a new `o3de-dxc-spirv` SRPM in `hellaenergy/o3de-dependencies` (the COPR repo with `enable_net=false`). License is NCSA + Apache-2.0 with LLVM exception, both Fedora-compatible. Ships `/usr/bin/dxc` and any DXC support files.
5. In `o3de.spec`, drop the upstream DXC fetch (remove the package from `BuiltInPackages_linux_x86_64.cmake` via patch), add `BuildRequires: o3de-dxc-spirv` (or `dxc` if upstream Fedora ever ships it), and either expose an `LY_DXC_PATH` cmake var or rely on `$PATH` to find `dxc`.
6. **Drop** the `%__requires_exclude ^libclang-12\.so.*|^libtinfo\.so\.6.*` line from the spec (it's only there because the bundled DXC's libclang/libtinfo aren't auto-Provided by rpm — once `dxc` comes from a system rebuild that links system libclang, the workaround isn't needed).

**Side benefits of completing this:**
- Eliminates the only mandatory restricted bundle, leaving poly2tri/squish-ccr as the only remaining optional feature-gated bits (NvCloth handles itself via PhysX-4 retirement). Handling option A becomes viable.
- Drops the `__requires_exclude` workaround (one fewer thing to justify in the Fedora package review).
- Reduces the runtime-fetcher surface area dramatically — most users won't need it at all.

**Risk:** O3DE may have applied custom patches on top of upstream DXC for the `1.8.2505.1-o3de-rev3` build (the `-o3de-rev3` suffix suggests it). If those patches are non-trivial, we'd need to track them and rebase onto whatever DXC version we ship. Worth investigating early — `git log` on O3DE's DXC fork (if there is one) or the patch set inside the bundled tarball.

### How upstream contributors can help (Stage 5)

In addition to the DXC asks in the "Restricted bundles" subsection above:

- **`LY_3RDPARTY_SYSTEM_OVERRIDE` generalization (long-term direction).** The proposed `LY_DXC_PATH` cmake var (see "Restricted bundles" subsection) could generalize: a uniform mechanism that lets distro packagers system-substitute *any* 3rdParty bundle without per-bundle gating. Question for the cmake side of the engine: would a generic `LY_USE_SYSTEM_<X>` convention (or a single `LY_SYSTEM_OVERRIDES` map) be in scope as a future engine feature? It would reduce the per-bundle gating Patch0006 currently applies to a single upstream-side change. Probably too ambitious for one PR; mention as a long-term direction we'd happily contribute toward if upstream is interested.

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

| Package | Why off-limits | What it enables | Upstream signal |
|---|---|---|---|
| **DirectXShaderCompilerDxc** | Microsoft tooling with redistribution restrictions on DXIL signing | shader compilation — **non-optional** for engine use | Linux-only SPIR-V rebuild is feasible (see Stage 5 sub-task below). |
| **NvCloth** | NVIDIA proprietary, not Fedora-acceptable | the NvCloth Gem (cloth simulation) — optional | **Functions independently of PhysX 4 (limited-scope test 2026-05-06).** Cheddarspice tested NvCloth with PhysX 4 removed + PhysX 5.6.1 active; AutomatedTesting cloth (chicken prefab) still works. Cheddarspice's qualifier: "in my limited testing, but it seems to be self-contained ... there *is* a shared foundation between PhysX but I'm guessing it was given a dedicated one." So full Gem-isolation across all cloth use cases is **inferred**, not exhaustively proven. The "auto-resolves via PhysX 4 retirement" framing (Nick_L 2026-05-05) is falsified. **Treat as a regular restricted bundle:** handle via option A (drop the Gem; appears Gem-isolated based on the test) or option B (runtime fetcher). PhysX 5's cloth replacement `PxDeformableSurface` is CUDA-only, so it's NOT a viable substitute for non-NVIDIA-GPU Linux users. Long-term upstream disposition (keep NvCloth in core vs. move to optional/restricted-Gem-repo) is still TBD. |
| **poly2tri** | Specific O3DE-vendored fork has license-attribution issues | navmesh generation — significant feature | No upstream-deprecation signal yet. |
| **squish-ccr** | Patent-encumbered texture compression algorithms | ImageProcessing Gem (asset bake) — significant | No upstream-deprecation signal yet. |

**Three handling options for the Fedora-shippable variant:**

| Option | Description | Pro | Con |
|---|---|---|---|
| A. Disable affected Gems | Drop NvCloth Gem, replace squish with a system substitute, skip navmesh features | clean license posture | feature loss; DXC is still required so this alone isn't sufficient |
| B. Runtime fetcher | `/opt/O3DE/<version>/python/fetch-restricted-deps.sh` — one-time post-install opt-in mirroring `get_python.sh`; downloads to `~/.o3de/3rdParty/` from `packages.o3de.org` | full feature set | requires user network action; some Fedora reviewers disapprove of this pattern |
| C. License-clean DXC rebuild | Build DXC from upstream NCSA/Apache-2.0 sources, configured Vulkan-only / SPIR-V-output (no Windows DXIL signing). Combined with A or B for the others. | best license posture | most engineering effort |

**Current preference:** **B** for short-term Fedora viability + **C as a follow-up** to reduce the runtime-fetch surface. With NvCloth confirmed standalone-but-not-disappearing as of 2026-05-06 (Cheddarspice's test under PhysX 5.6.1; see table above), the runtime-fetch surface in the long run is **NvCloth + poly2tri + squish-ccr** — all three remain optional/feature-gated. Distros can choose option A (drop those three Gems for a clean license posture, accept the feature loss) or option B (runtime-fetch them post-install). DXC is the load-bearing one regardless — making it license-clean is the hardest single win.

### How upstream contributors can help

This section exists for O3DE upstream contributors (3rdParty maintainers, sig-build folks, anyone with engine-internals visibility) reading this doc and wondering what concrete asks would unblock Fedora-track work. Each ask is something a packager can't determine from outside; an upstream contributor with the right context can answer in minutes.

**For DXC (critical-path; license-clean Linux rebuild — the highest-leverage win):** tracked at [#6](https://github.com/nickschuetz/o3de-rpm/issues/6). Sub-questions 1 and 3 ANSWERED by Nick_L 2026-05-05; sub-question 2 implicitly resolved.

1. **What's in the `-o3de-rev3` suffix?** — **ANSWERED.** `-rev3` is just the package-system revision counter; source git tag is `release-1.8.2505.1-o3de` in the [o3de fork](https://github.com/o3de/DirectXShaderCompiler/tree/release-1.8.2505.1-o3de). Diff against upstream Microsoft `release-1.8.2505` is **4 commits** — Linux compile fix, `dxsc` tool addition, and contributions that "should be contrib'd upstream tbh." Carry-patch is small + tractable.
2. **Could the engine accept an external DXC via cmake?** — Implicitly resolved. The engine just shells out to a `dxc` binary; `$PATH` discovery or an `LY_DXC_PATH` (or `LY_DXC_EXECUTABLE`) cmake var both work cleanly. No library-finding plumbing needed.
3. **What internal DXC API surface does the engine actually depend on?** — **ANSWERED (massive simplification).** Engine **doesn't link DXC** at all. DXC is invoked as a runtime/tool-time **executable** (the `dxc` binary), not linked as a library. So the license-clean rebuild only needs to produce a working `dxc` binary that produces SPIR-V output and accepts the same CLI. **No `libdxcompiler.so`, no internal LLVM symbol concerns, no `__requires_exclude` workaround needed in the post-rebuild spec.**

**For poly2tri + squish-ccr (Gem-boundary clarification):** [#7](https://github.com/nickschuetz/o3de-rpm/issues/7).

4. **Is each restricted bundle's dependency at the Gem boundary, or deeper?** If `poly2tri` is cleanly isolated to a single Gem (or a single navmesh subsystem), distros can drop just that Gem (handling option A) and ship the rest of the engine without losing other features. Same question for `squish-ccr` and the ImageProcessing Gem's BC7 baking. Knowing per-bundle whether the dependency is Gem-boundary vs. core-engine-path lets us scope option A precisely.

**For NvCloth:** Cheddarspice's 2026-05-06 test confirmed NvCloth still works with PhysX 4 removed + PhysX 5.6.1 active (the "essentially standalone" claim verified). For Fedora-track planning, NvCloth is a regular restricted bundle handled via option A (drop the Gem, confirmed Gem-isolated) or option B (runtime fetcher). The strategic question — does upstream keep NvCloth in core long-term, or move it to an optional/restricted-Gem repo? — is open. If anyone has visibility on the upstream PhysX 4 → 5 changeover plan and what it does to NvCloth's status in core, that scopes whether option A is sufficient or whether we should plan around NvCloth migrating out of core anyway.

**Where to send answers:** GitHub issues at https://github.com/nickschuetz/o3de-rpm/issues, or the #sig-build channel in the O3DE Discord (the conversation is already running there).

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
