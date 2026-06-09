# Fedora-inclusion roadmap

The goal: get the stable `o3de` package into the **Fedora repository proper**. Until that's reached, COPR (`hellaenergy/o3de` + `o3de-testing` + `o3de-stabilization` + `o3de-development` + `o3de-experimental`) is the interim distribution channel. Five engine projects with distinct roles plus the shared `o3de-dependencies` project for non-Fedora 3p deps.

Fedora is one of **three** distribution targets named in the README (COPR today, o3debinaries.org as the eventual upstream channel, Fedora long-term). A future Flathub release tracked in `FLATPAK_NOTES.md` and surfaced in `ARCHITECTURE.md` is *not* in the README — it would confuse RPM-focused readers — but most of the work here is shared infrastructure regardless: the system-lib migration, OpenSSL port, and license-clean DXC rebuild all benefit the o3debinaries.org submission and the eventual Flatpak too. Fedora is the strictest target; if we satisfy Fedora, we satisfy everything.

This document is the staged plan, dependency map, and decision log. It lives in the repo so contributors can see the state of each blocker without spelunking through commit history.

---

## Current state (2026-05-13 snapshot)

Quick TL;DR of where each stage stands as of this snapshot. Per-stage detail in sections below; this header gets refreshed as state advances.

| Stage | Status |
|---|---|
| 0 -- COPR distribution | Active. Five engine channels (o3de stable, o3de-testing pre-promotion soak introduced 2026-05-28, o3de-stabilization community/pre-release-window, o3de-development dev-branch, o3de-experimental in-flight migration work). Versioned multi-install architecture live (o3de2605 etc., /opt/O3DE/<v>/). o3de2605-devel subpackage split landed 2026-05-04. **CS10 chroot achieved first-ever successful engine build 2026-05-12** (build 10450340) via gcc-toolset-15-libatomic-devel BR; **CS10 with_opts gap fully closed 2026-05-14** -- experimental CS10 = 19 swaps (matches F44/rawhide); stabilization CS10 = 14 swaps (matches F44/rawhide). 17 of 19 experimental flags already validated end-to-end on builds 10456101 + 10457745; the 2 newly-added experimental flags + 6 newly-added stabilization flags will validate on their next triggered builds. |
| 1 -- System swap migration | **Stage 1 14-pack ACTIVE in `hellaenergy/o3de-stabilization` COPR** (promoted 2026-05-12/13 in build 10452477 for the 13-pack; 14th `system_vulkan_validation_layers` promoted 2026-05-14): zlib, freetype, libpng, expat, lz4, mikkelsen, openexr, poly2tri, lua, assimp, sqlite, libsamplerate, googlebenchmark, vulkan-validation-layers. Patch0013 v4 (three-hunk gate for vulkan-validation-layers) validated in experimental build 10457745 GREEN 2026-05-14 04:03 UTC before stabilization promotion. Patch0010 + Patch0011 cover Lua 5.5 forward-compat (rawhide); engine compiles green on Lua 5.5. Patch0012 v2 (AssetBuilder parent-death watchdog) also active in the o3de-stabilization COPR channel as of 10452477. **Three more Stage 1 swaps landed in `hellaenergy/o3de-testing` as of 2605.0-95** (validated on the 26.05.0 release engine, CI green on F44 + rawhide; pending promotion to stable): `system_rapidjson` (F44 + rawhide only; CS10's EPEL-10 rapidjson 1.1.0 release fails gcc-toolset-15 `-Werror=deprecated` on `std::iterator`, build 10526694), `system_xxhash`, and `system_cityhash` (all three chroots; cityhash now asserted in the Tier 2 + Tier 7 swap-health checks). |
| 2 -- Binary/library deps not in Fedora | **Stage 2 3-pack ACTIVE in `hellaenergy/o3de-stabilization` COPR (promoted 2026-05-14)**: o3de2605-spirv-cross (binary shellout), o3de2605-dxc-spirv (binary shellout), o3de2605-mcpp-az (library link, first of its kind). All three PoCs ✓ GREEN since 2026-05-08; promoted to stabilization after 6+ days of green experimental soak. Stabilization chroots now have `additional_repos: copr://hellaenergy/o3de-dependencies` set so Stage 2 build-time deps resolve. End-user `dnf copr enable hellaenergy/o3de-stabilization` triggers an `o3de-dependencies` enable via the test workflow's standard sequence. |
| 3 -- Python migration | Blocked. Bundled Python 3.10 hardcoded in cmake/3rdParty/Platform/Linux/Python_linux_x86_64.cmake. F44 ships 3.13. Unblocks Stage 2b (OpenImageIO + OpenColorIO blocked on Python C Module ABI). Engine-team owns. |
| 4 -- OpenSSL 3 migration | Blocked. Bundled OpenSSL 1.1.1t (EOL 2023-09-11) needs upstream migration to 3.x. Engine-team owns. |
| 5 -- Bundling Library Exception filings | In prep. Three documented exceptions: Qt 5.15 (custom-rev9 patches), squish-ccr (BC7 patent encumbrance), NvCloth (NVIDIA license). libtiff dropped out 2026-06-05: Patch0016 (TIFF_DISABLE_DEPRECATED) dissolved the CryCommon int64 collision and system_tiff validated end-to-end on experimental (builds 10568964/10570032 + CI 27017382939). The DXC entry that previously sat in this list dropped out 2026-05-28: `o3de2605-dxc-spirv` (in `hellaenergy/o3de-dependencies`) is the license-clean rebuild, fits Fedora's accepted vendored-compiler precedent (emscripten, halide, hipcc), and replaces the binary bundle entirely. |

### Notable changes since this doc was last comprehensively updated

- **O3DE 26.05.0 release date set: 2026-05-27** (sig-release chair Nick, decision 2026-05-12). 15-day pre-release window. Upstream `o3de/o3de:stabilization/26050` is in pre-release lockdown (only critical fixes merge) -- non-critical upstream merges to `development` won't reach our snapshot until we re-pin post-release. Triggers post-release packaging work: snapshot pin re-pin to 2605.0 release tag, Patch0007/Patch0008 retirement re-check (likely still needed since #19733/#19734 merged to development but not cherry-picked to stabilization/26050), COPR rebuild from release tag, tester announcement. Pre-release sweep agent scheduled for 2026-05-25 09:00 CDT. Memory: `project_2605_release_date.md`, `project_2605_stabilization_branch_locked.md`.
- **CS10 (CentOS Stream 10) first-ever successful engine build** 2026-05-12 (build 10450340) via `BuildRequires: gcc-toolset-15-libatomic-devel` gated on `%if 0%{?rhel}`. Caveat: CS10 chroot still has empty `with_opts` so it ships bundled-3p everywhere; full CS10 viability requires `o3de-dependencies` packages built for CS10 first, then with_opts propagation. Stabilization build 10452477 (early 2026-05-13) extended the success to the testers' channel. The "CS10 effort paused" framing from earlier is superseded.
- **Patch0012 v2 (AssetBuilder parent-death watchdog) ACTIVE in the `hellaenergy/o3de-stabilization` COPR channel since 2026-05-12.** Fixes the orphan AssetBuilder accumulation pattern across AP crashes (saw 18 + 3 orphans in one ROS2_Project session before the patch). v1 attempt used `m_tetherLifetime` / `prctl(PR_SET_PDEATHSIG)` and failed because PR_SET_PDEATHSIG signals on forking-thread death (not parent-process death) and AP forks from short-lived TaskWorker threads. v2 sidesteps with a child-side getppid() poll in AssetBuilder/main.cpp. Upstream as [o3de/o3de#19747](https://github.com/o3de/o3de/pull/19747) (maintainer informally accepting: "okay with accepting this for now"). Memory: `project_prctl_pdeathsig_thread_gotcha.md`, `project_assetbuilder_orphan_lifecycle_bug.md`.
- **Qt 5 -> Qt 6 strategic pivot.** O3DE engine team is migrating to vanilla Qt 6.10.2 for 26.10.0 (goal date, not guaranteed). [o3de/o3de#19567](https://github.com/o3de/o3de/pull/19567) ("Build against Qt6.10.2", base `development`) is the merge PR -- OPEN + APPROVED + CLEAN + MERGEABLE as of 2026-06-09, with sig-build planning to start the merge ~2026-06-10; Linux-Profile builds GREEN. Means: when this lands, our o3de-qt5 101MB bundled package retires in favor of a Stage 1 system_qt6 swap against Fedora's qt6-qtbase-devel etc. -- the entire Qt 5.15.2-rev9 line of work becomes obsolete. The merge is watched by tools/check-qt6-merge.py + the `qt6-merge-gate` pre-flight (chroot-flip runbook in FOLLOW_UPS.md "TRIGGER: qt6 merges into o3de/development"). See memory note project_o3de_bundles_custom_qt.md for the migration plan.
- **Upstream PR engagement**: three merged earlier this cycle -- [#19733](https://github.com/o3de/o3de/pull/19733) (AzCore Lua include cleanup), [#19734](https://github.com/o3de/o3de/pull/19734) (libtiff C99 typedefs), [#19737](https://github.com/o3de/o3de/pull/19737) (Microphone libsamplerate PAL gate). Each lets our corresponding local patch retire on next snapshot rebase. **Six more PRs + one design issue filed 2026-05-12**: [#19745](https://github.com/o3de/o3de/issues/19745) (BuilderManager threading constraint design issue), [#19746](https://github.com/o3de/o3de/pull/19746) (ProcessWatcher prctl doc comment, sig/core), [#19747](https://github.com/o3de/o3de/pull/19747) (AssetBuilder parent-death watchdog, sig/content + sig-core-reviewers), [#19748](https://github.com/o3de/o3de/pull/19748) (Clang21 -Wno-error= flags, sig/build; "we may need this one for this release"), [#19750](https://github.com/o3de/o3de/pull/19750) (WindowDecorationWrapper title propagation), [#19751](https://github.com/o3de/o3de/pull/19751) (manifest.py O3DE_ENGINE_PATH env-var), [#19752](https://github.com/o3de/o3de/pull/19752) (LYPython sdist install for INSTALLED_ENGINE). Maintainer engagement on #19747 (informal accept) + #19748 (release-candidate signal) + #19752 (architectural discussion of deeper venv-activation bug).
- **Comments on existing 2023-era community issues** ([#16375](https://github.com/o3de/o3de/issues/16375) umbrella system_X swap convention, [#16367](https://github.com/o3de/o3de/issues/16367) read-only engine install): added 2026-05-12 with concrete implementation evidence from the 13-active-swap stack, instead of filing duplicate fresh issues. Prior-art-check-before-drafting pattern memorized as `feedback_check_prior_art_before_drafting_upstream.md`.
- **Two upstream issues filed earlier**: [#19740](https://github.com/o3de/o3de/issues/19740) (libbenchmark.a missing from engine install set), [#19743](https://github.com/o3de/o3de/issues/19743) (AssetProcessorBatch lacks a "minimal scope" mode for single-asset testing).
- **Drift-detection workflow** (tools/check-deps-drift.py + .github/workflows/check-deps-drift.yml) live since 2026-05-08, weekly cron. Tracks engine pins vs COPR vs 3p-package-source vs spec bconds. Also tracks upstream migration branches (qt6, qt6_pyside) and PRs (#19567) under "Upstream migration tracking" section. Report cleaned 2026-05-11: 0 gap, 0 minor-drift, 5 in-sync, 5 bundled-exception, 2 out-of-date (1 intentional Qt drift + 1 ISPCTexComp commit fix landed).
- **Tier 7 test infrastructure rewrite** (2026-05-11). Original FBX asset-bake design discovered to be conceptually wrong (SceneAPI has a hidden hard dependency on Atom RPI gem chain). Rewritten as system-swap library-health check (per-swap SONAME + symbol + engine linkage smoke); all PASS in production (cityhash added 2026-05-31, so the per-swap matrix is 15 entries now; rapidjson + xxhash are header-only with no SONAME to assert). Filed upstream issue #19743 asking for `--minimal-scope` flag that would unlock proper SceneAPI-integration testing.
- **Engine forward-compatibility audit** completed 2026-05-11 (memory note project_engine_forward_compat_audit.md). Swept stabilization/26050 for OpenSSL 3 deprecations, glibc 2.39+ symbols, C++23 removals, Python C API, Vulkan version, Wayland. Zero concerning hits across all categories. Lua 5.5 was the exception, not a pattern.

---

## Stage 0 — COPR (interim, today)

**Status:** ✅ unblocked, in progress. Continues indefinitely as the user-facing distribution while later stages land.

**Deliverables:**
- `hellaenergy/o3de-dependencies` — Fedora-clean SRPMs for O3DE 3rdParty packages not in Fedora.
- `hellaenergy/o3de`, **tracks `o3de/o3de:main`** (upstream's release branch where each tagged release lives: `2510.2`, `2605.0`, etc.). Twice-yearly major cadence + occasional point releases + post-soak promotions from `o3de-testing`. Post-release runbook lives at [`POST_RELEASE.md`](POST_RELEASE.md); `make release-stable` target pre-flights spec state before pushing.
- `hellaenergy/o3de-testing`, pre-promotion soak channel for stable, introduced 2026-05-28. Mirrors Fedora's `updates-testing` semantics. Packaging-side bug fixes and minor enhancements land here from `main HEAD` (`make copr-testing-and-test`), soak ~48 hours, then promote to `hellaenergy/o3de` (`make copr-stable`). End-user-facing soak channel; testers opt in to catch packaging regressions before broader stable rollout.
- `hellaenergy/o3de-stabilization`, pre-release engine-validation builds from `stabilization/<release>`. Active during the upstream stabilization window (~4 weeks per release cycle); dormant between cycles. Community-tester channel when active.
- `hellaenergy/o3de-development` — Sunday-cron builds from `o3de/development` (renamed from `o3de-snapshot` 2026-05-23 to make the branch-tracking intent explicit; auto-refreshed via `.github/workflows/snapshot-development.yml`, which pins its checkout to the o3de-rpm `development` spec branch). For an in-progress migration ref (e.g. qt6), a dedicated COPR project per branch (e.g. `o3de-development-qt6`).
- `hellaenergy/o3de-experimental` — in-flight Stage 1 / Stage 2 migrations.

All five engine projects built with `enable_net=true` so O3DE's `LY_PACKAGE_SERVER_URLS` fetcher can pull the remaining restricted bundles (NvCloth + squish-ccr; DXC retired 2026-05-08 via o3de2605-dxc-spirv rebuild; poly2tri became Stage-1-swappable as of 2026-05-07) from `packages.o3de.org` (see "Restricted bundles" below).
- Spec validated end-to-end on F44 / commit `246b46f` from `stabilization/26050`. First public COPR build (10416727) was installed by Nick on 2026-05-02 from the project that became `o3de-stabilization` (it was named `o3de-snapshot` until 2026-05-03 when the project was renamed and `o3de-snapshot` was repurposed for one-off dev builds); confirmed working via Project Manager + Editor launch; community testers were invited that day.
- Test infrastructure (test-installed.yml in clean F44 + rawhide containers) wired up: cron-polling of `o3de-stabilization` every 4 hours, repository_dispatch for explicit `make trigger-tests` runs, manual workflow_dispatch for ad-hoc URL-driven tests. The `o3de-experimental` and `o3de-development` channels are exercised explicitly by `make copr-experimental-and-test` / `copr-development-and-test`.
- **Versioned multi-install architecture** (committed 2026-05-03): packages ship as `o3deNNNN` (`o3de2605` for 26.05.x; `o3de2610` will land alongside when 26.10 stabilization begins) installing to `/opt/O3DE/<DISPLAY_VERSION>/`, mirroring upstream's `.deb` and `.msi` install layouts. Different majors are co-installable; per-major desktop entries, AppStream IDs (`org.o3de.O3DE2605`), and SBOMs. `Provides: o3de = %{version}-%{release}` so any external `Requires: o3de` still resolves. This baseline reduces packaging-review friction for both the o3debinaries.org submission and Fedora-proper review by aligning Fedora packaging with the upstream cross-platform install convention.
- **`engine.json` `engine_name` stays unversioned** (corrected 2026-05-04): the cmake `-DO3DE_INSTALL_ENGINE_NAME=o3de` literal sets engine.json's identity to upstream's pristine default — that's what gem manifests' `compatible_engines` lists check against (e.g. WarehouseAssets ships `["o3de-sdk>=2.3.0", "o3de>=2.3.0"]`). Setting engine_name to a versioned form (`o3de2605`) breaks every existing third-party gem because no gem's compatible_engines enumerates the versioned name. Trade-off: the manifest's `engines_path` map keys by `engine_name`, so multiple installed o3deNNNN majors collide on the `o3de` key — only ONE major is "registered" at a time; switching uses `<install-prefix>/scripts/o3de.sh register --this-engine` from the desired install root. This matches upstream's `.deb` multi-install UX exactly. The other versioned identities (RPM name, install path, desktop entries, AppStream id, dock WM_CLASS, SBOM) stay versioned — they don't enter the gem-compat check.
- **Subpackage split** (2026-05-04): main `o3de2605` ships runtime + project-build materials (engine `.so`s, headers, gem sources, scripts, runtime cmake, Templates). `o3de2605-devel` carves out the static archives (`lib/Linux/profile/Default/*.a` + `lib64/`, ~178 .a files, ~4 GB) for native C++ gem developers who static-link against engine internals. `o3de2605-debug` (only with `--with debug`) adds debug-config binaries + their static archives. Project-build `*-devel` system packages (clang, mesa-libGL[U]-devel, libxcb-devel, fontconfig-devel, libcurl-devel, pcre2-devel, openssl-devel, libunwind-devel, libzstd-devel, vim-common, plus per-active-swap mikkelsen-devel etc.) are pulled in via main's `Recommends:` so default `dnf install o3de2605` gives a working build experience. cmake also moved from Requires to Recommends; launcher's engine-id calc has bundled-cmake-fallback path baked in for future use.

**Status of `hellaenergy/o3de-dependencies`:** all 9 SRPMs have **succeeded builds** in COPR (verified via `copr-cli list-builds hellaenergy/o3de-dependencies`). Some required iteration — `o3de-qt5` took ten attempts before landing — but the repo is consumable today via `dnf copr enable hellaenergy/o3de-dependencies`. The remaining work for *integrating* those packages with the o3de spec (so cmake consumes them via `BuildRequires:` instead of fetching from `packages.o3de.org`) is Stage 1 below.

---

## Stage 1 — System library migration (the long tail)

**Status:** **9-pack VALIDATED end-to-end on `o3de-experimental` (2026-05-07)** — build **10433646 succeeded** on F44 + rawhide; `test-installed.yml` CI auto-triggered against the new RPM URL (run pending; 30-60 min for results). Extends the 8-pack with `system_lua`, activated by Patch0008 (commit `d69bb9c`). Patch0008 drops AzCore `ScriptContext.cpp`'s `#include <Lua/lobject.h>` — audit identified the only consumed symbol (`LUAI_MAXALIGN`) is already public Lua API via `luaconf.h`'s transitive include from `lauxlib.h`. Same patch was submitted upstream as o3de/o3de [PR #19733](https://github.com/o3de/o3de/pull/19733) (approved by nick-l-o3de 2026-05-07, awaiting merge); when that lands, our Patch0008 becomes redundant. The 8-pack added `system_poly2tri` (Stage 1 swap reframed from "off-limits restricted bundle" via the audit at [#7](https://github.com/nickschuetz/o3de-rpm/issues/7), 2026-05-07; see "Restricted bundles" below). The 7-pack was validated end-to-end on `o3de-experimental` 2026-05-07 (build 10430726, CI run 25475307693 passed Tiers 1+2+4+6 on F44 + rawhide). Build 10430726 succeeded on F44 + rawhide; CI run 25475307693 passed Tiers 1+2+4+6 on both chroots (after a transient artifact-corruption flake in the prior run, fixed in commit `c57f5d8` by dropping the workflow's prepare-job artifact roundtrip). The 6-pack (`expat`, `freetype`, `lz4`, `mikkelsen`, `libpng`, `zlib`) was validated end-to-end 2026-05-05 (build 10426632 + CI 25402407670). The 7-pack adds `openexr` — `FindOpenEXR-system.cmake` is one half of the two-shim design (the other is `FindImath-system.cmake`); together they create `3rdParty::OpenEXR` (linking libOpenEXR + libOpenEXRCore + libIex + libIlmThread) and `3rdParty::Imath` (linking libImath), mirroring the bundle's `TARGETS OpenEXR Imath` declaration. Engine consumers (`Gems/Atom/Asset/ImageProcessingAtom/.../ExrLoader.cpp`) use `#include <OpenEXR/Imf*.h>` verbatim, matching Fedora's openexr-devel + imath-devel layout exactly. Per Nick_L (2026-05-05, [#5](https://github.com/nickschuetz/o3de-rpm/issues/5)), OpenEXR's version pin in O3DE is not hard; F44's openexr-3.2.4 + imath-3.1.12 are API-compatible with the bundle's 3.1.3. **Eligible for promotion to `o3de-stabilization`** whenever Mike's tester signal on the current stabilization build comes back positive (active-testers-window rule). The Stage 2b sibling sub-track (OpenImageIO + OpenColorIO) is NOT activated here — blocked on Stage 3 (Python migration) per Nick_L's circular-dependency + Python C Module ABI explanation. `libtiff` settled into Option C (Bundling Library Exception path) on 2026-05-05; `lua` remains deferred pending AzCore investigation.

  - **`expat` / `freetype` / `libpng` / `zlib` validated (2026-05-04)** — earlier failure (build 10421133, 2026-05-03) traced to each of these four `Find<X>-system.cmake` shims `include()`ing cmake's stock find module (FindZLIB.cmake / FindPNG.cmake / FindFreetype.cmake / FindEXPAT.cmake). The stock include's side-effect upper-namespace target (`ZLIB::ZLIB` etc.) had `MAP_IMPORTED_CONFIG_*` properties set but only the unconfigured `IMPORTED_LOCATION` populated, which O3DE's runtime walker bailed on. Refactored each shim to the mikkelsen pattern (commits `92bde6e` / `cba5059` / `6b14ffa` / `0ca58e8`): direct `find_path` + `find_library` inline, no stock-module include, construct `3rdParty::<X>` as INTERFACE IMPORTED GLOBAL, alias the upper-namespace target (`ZLIB::ZLIB` etc.) to satisfy upstream consumers (notably the bundled freetype's `target_link_libraries(... INTERFACE ZLIB::ZLIB)`). Each shim validated individually via isolated `rpmbuild --with system_<X>` builds (47-52 min each); combined 5-pack also validated. Pending: COPR cross-distro confirmation, then promotion to `o3de-stabilization`.
  - **`libtiff` — Option C, Bundling Library Exception path (decided 2026-05-05)** — Patch0007 (deprecation migration of `TIFFLoader.cpp` + `ImageTIF.cpp` to C99 typedefs) stays in place; required for *any* build against modern libtiff. The deeper int64/uint64 typedef collision (libtiff's `<tiff.h>`: `int64_t`/`uint64_t` = `long` on LP64; CryCommon's `BaseTypes.h`: `slonglong`/`ulonglong` = `long long`) was attempted via Patch0008 (a narrow `O3DE_SYSTEM_LIBTIFF_COMPAT` guard around CryCommon's typedefs + SKIP_UNITY_BUILD_INCLUSION on the two TIFF .cpp files; commit `cda6b7b`) and reverted (`9f2f099`) after a local `rpmbuild -bb --with system_tiff` failed at compile time in `Cry_ValidNumber.h` — that header uses `uint64` directly in its own DoubleU64/DoubleU64ExpMask/DoubleU64FracMask macros, transitively included from `EditorDefs.h` via `Cry_Math.h`, *before* `<tiffio.h>` brings libtiff's typedef into scope. Reordering `<tiffio.h>` ahead of the engine headers compiles cleanly (libtiff's int64/uint64 become visible in time) but introduces a `long` vs `long long` mangling mismatch at link time — `CryGetTicks()` and other engine symbols compiled against the engine-wide `slonglong` typedef export `long long` mangling, and the TIFF TU's call sites would mangle as `long`. Option B (engine-wide CryCommon C99 migration) is out of scope; Option C (file Bundling Library Exception alongside Qt 5.15-rev9) is the path. The bcond, Source declaration, FindTIFF-system.cmake, and Patch0007 stay in place — if a future engine refactor touches CryCommon's foundational typedefs upstream, system_tiff becomes activatable without packaging-track changes. See `squeezing-typeface-tiffany.md` for the full closeout. **RESOLVED 2026-06-05 by Option D, nobody's typedefs move:** libtiff 4.5+ guards its legacy non-prefixed typedefs behind `TIFF_DISABLE_DEPRECATED`; with every tiffio.h consumer already on C99 names (Patch0007 / upstream #19734) the guard removes the tiff side of the collision entirely. Patch0016 defines it in the three consumer TUs; CryCommon untouched, the Cry_ValidNumber.h ordering trap never engages. Validated: builds 10568964 + 10570032 (F44/rawhide/CS10) + CI 27017382939 Tier 2 swap-health (system libtiff.so.6 in auto-Requires, zero bundled tiff in payload, rawhide = libtiff 4.7.1). Active on o3de-experimental; upstream issue + PR pitch pending.
  - **`lua` activated 2026-05-07** — Patch0008 (carry-patch + upstream PR #19733) drops AzCore `ScriptContext.cpp`'s `<Lua/lobject.h>` include. Audit identified only `LUAI_MAXALIGN` was needed and it's already public Lua API; Fedora's lua-devel suffices. 9-pack queues with this commit.

Remaining unmigrated bundles (mcpp, vulkan-validationlayers, googlebenchmark, assimp, SPIRVCross/lz4/libsamplerate, libcurl/pcre2/SQLite, OpenEXR/OIIO/OCIO, pyside2) are deferred — see notes by each in the table. The mikkelsen-only baseline is what currently ships from `o3de-experimental`; the four ZLIB-class swaps will batch-promote to `o3de-stabilization` after the find-shim refactor lands and validates, in one coherent push so testers see one migration moment.

O3DE bundles ~30 3rdParty packages from its CDN at cmake configure time. Most of them have direct Fedora equivalents we can pivot to.

| Bundled package | Fedora package | Status / effort |
|---|---|---|
| **mikkelsen** | `mikkelsen-devel` (in `hellaenergy/o3de-dependencies` until Fedora-accepted) | **ACTIVATED in `o3de-experimental` channel** via `--with system_mikkelsen` (Patch0006 + Findmikkelsen-system.cmake) |
| zlib | `zlib-devel` | **validated 2026-05-04** (commit `92bde6e`, refactored to mikkelsen pattern + ZLIB::ZLIB alias for upstream consumers) |
| freetype | `freetype-devel` | **validated 2026-05-04** (commit `6b14ffa`, refactored to mikkelsen pattern; single include dir at `/usr/include/freetype2` covers both `<ft2build.h>` and `<freetype/...>` consumer forms) |
| libcurl | `libcurl-devel` | follow-on (use mikkelsen template) |
| libpng | `libpng-devel` | **validated 2026-05-04** (commit `cba5059`, refactored to mikkelsen pattern) |
| libtiff | `libtiff-devel` | **ACTIVE on experimental (2026-06-05)** — Patch0016 defines `TIFF_DISABLE_DEPRECATED` in the three tiffio.h consumer TUs, removing libtiff's legacy int64/uint64 typedefs (the CryCommon collision) at the source. Upstream pitch pending; promotion to stabilization on the usual soak rules. |
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
| vulkan-validationlayers | `vulkan-validation-layers` (runtime; no -devel) | **ACTIVE in experimental** 2026-05-13/14 via Patch0013 v4 + build 10457745. Runtime-discovery via VK_LAYER_PATH (Vulkan loader's standard path) -- no link-time cmake dep at all, so the pattern is "three-hunk gate" rather than the usual Find shim. F44 ships 1.4.x vs O3DE's bundled 1.2.198; loader interaction validated by build success across fc44 + rawhide + CS10. Not promoted to stabilization (mid-window rule). |
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

**Promotion to `o3de-stabilization`:** each migration that passes test-installed.yml end-to-end on the experimental channel is eligible for promotion to the stabilization channel — but only when Nick signals the testing window is open for new pushes. Until then, `o3de-experimental` accumulates the validated activations and `o3de-stabilization` stays stable.

### How upstream contributors can help (Stage 1)

These are the Stage 1 bundles where outside-the-packager visibility would unblock specific work. Each ask has a tracking issue — comment there or in #sig-build, both are watched. **Some asks are answered as of 2026-05-05 (Nick_L on sig-build); see issue comments for details.**

- **`system_lua` — RESOLVED 2026-05-07.** [#1](https://github.com/nickschuetz/o3de-rpm/issues/1). Audit-pattern playbook on AzCore's `ScriptContext.cpp` identified the only symbol consumed from `<Lua/lobject.h>` was `LUAI_MAXALIGN`, which is already public Lua API — defined in `luaconf.h` and used in `lauxlib.h`'s `luaL_Buffer`. Empirical compile test confirmed dropping the include is behavior-preserving. Resulted in [o3de/o3de PR #19733](https://github.com/o3de/o3de/pull/19733) (approved by nick-l-o3de 2026-05-07, awaiting merge) and our local Patch0008 (commit `d69bb9c`). `system_lua` activated in the 9-pack 2026-05-07.
- **`system_tiff` — CryCommon `int64`/`uint64` typedef migration.** [#2](https://github.com/nickschuetz/o3de-rpm/issues/2) — **REFRAMED as actionable engine-maintenance work** (Nick_L 2026-05-05: "most of them are just legacy housework like, the uint64 stuff"). The migration is now characterized by upstream as legacy housework rather than out-of-scope. Anyone who picks up the engine-side PR (CryCommon's `int64`/`uint64` from `slonglong`/`ulonglong` to `int64_t`/`uint64_t`, with cross-platform format-specifier audit) still improves engine hygiene, but as of 2026-06-05 it is NO LONGER the system_tiff blocker: Patch0016's `TIFF_DISABLE_DEPRECATED` dissolved the collision from the libtiff side and the swap is active on experimental.
- **`mcpp` `_az` fork delta.** [#3](https://github.com/nickschuetz/o3de-rpm/issues/3) — **CLOSED, reframed as architectural choice** (Nick_L 2026-05-05: "we really just need any preprocessor that can run on c-like files"). mcpp's only role is `#ifdef` expansion in AZSL/AZSLI shader files; could be replaced with a Python plugin or system clang `-E`. Not a packaging concern; closing the question.
- **`AWSNativeSDK` + `AwsIotDeviceSdkCpp` libcurl bundling.** [#4](https://github.com/nickschuetz/o3de-rpm/issues/4) — **CLOSED, resolves via upstream direction** (Nick_L 2026-05-05: "AWS SDK should be excised from O3DE entirely tbh, so curl and such should be entirely a non issue"). When upstream excises AWS SDK from core O3DE, the libcurl transitive bundling problem disappears.

---

## Stage 2 — Big-media bundle migration

**Status:** **two sub-tracks** with different blocking conditions, per Nick_L's 2026-05-05 sig-build response (see [#5](https://github.com/nickschuetz/o3de-rpm/issues/5)).

### Stage 2a — OpenEXR + Imath -- ABSORBED INTO STAGE 1 (2026-05-07)

**Status:** **DONE.** Absorbed into the Stage 1 system-swap track as `system_openexr` (two-shim variant -- `FindOpenEXR-system.cmake` + `FindImath-system.cmake`). Active in the 14-pack live in the `hellaenergy/o3de-stabilization` COPR channel as of the 2026-05-14 promotion (build 10460860).

O3DE bundles `OpenEXR-3.1.3-rev4-linux`. F44 ships `openexr-devel-3.2.4` + `imath-devel-3.1.12`. Per Nick_L 2026-05-05 ([#5](https://github.com/nickschuetz/o3de-rpm/issues/5)), version pins aren't hard; OpenEXR has no Python C Module so it never had the Stage 2b ABI constraint. The original "Stage 2a / Stage 1.5" framing was a sub-track classification that ended up being unnecessary -- once the find-shim pattern was generalized, OpenEXR slotted in as another Stage 1 swap alongside the other 12.

Section retained here for the historical breadcrumb to issue [#5](https://github.com/nickschuetz/o3de-rpm/issues/5) and Nick_L's pin-strictness response. Current swap details live in the Stage 1 per-package table above.

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

Target: use system Python (currently 3.13 in F44, 3.12 in CentOS Stream 10).

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
| **License-clean DXC rebuild** | **DONE 2026-05-14** -- shipped as `o3de2605-dxc-spirv` in `hellaenergy/o3de-dependencies`, active in stabilization. Recap section below. | done |
| Real `-debuginfo` subpackage | Distinct from the existing `o3deNNNN-debug` subpackage (which ships debug-config binaries alongside the profile build). Fedora's `-debuginfo` is the rpmbuild-extracted symbol files for stripped binaries — currently disabled via `%global debug_package %{nil}` because O3DE's binary layout trips rpmbuild's symbol extraction (likely a `BUILD_ID` ambiguity from the Ninja Multi-Config split). May need patches to O3DE's link rules. | yes |
| `-debugsource` subpackage | Source code corresponding to each debuginfo line. Should fall out automatically once `debuginfo` works. | yes |
| Bundled Library Exception filing | Required for the custom Qt 5.15-rev9 (load-bearing). Justification doc in `BUNDLED_LIBRARIES.md`. | yes |
| Mock-clean SRPM build | `mock --rebuild o3de.src.rpm` must succeed with `--isolation=simple --no-network` enabled. | needs Stage 1 / 2 / 3 |
| Reproducible build | byte-identical RPM from the same SRPM on different hosts | needs all earlier stages |
| AppStream `<screenshots>` | Required by Flathub; nice-to-have for Fedora. Need actual editor screenshots from a working install. | yes |
| `<content_rating>` review | Currently `oars-1.1` empty (which means "no objectionable content"). Verify with O3DE upstream that no mature-content engine features need flagging. | yes |

### License-clean DXC rebuild (recap)

**Status:** DONE. Shipped as `o3de2605-dxc-spirv` in `hellaenergy/o3de-dependencies` 2026-05-08; promoted to `hellaenergy/o3de-stabilization` 2026-05-14 (build 10460860 GREEN). Engine consumes the rebuilt binary via `system_dxc` bcond + Patch0008. Re-audit 2026-05-28 confirmed both the original bundle and the rebuild are clean of the previously-feared `libclang-12.so` runtime dep (it was never there; LLVM 12 is statically linked into `libdxcompiler.so` in both).

**Why this mattered for Stage 5:** DXC is the only one of the four originally-listed restricted bundles that is non-optional for engine use; without DXC, the engine cannot compile shaders. NvCloth + squish-ccr are feature-gated; poly2tri is a Stage 1 system swap as of 2026-05-07. Solving DXC was the gating Stage 5 task.

**The licensing problem was narrow.** Only the Windows DXIL signing tooling is Microsoft-proprietary. The HLSL to SPIR-V (Vulkan) code path is fully open-source under NCSA / Apache-2.0 with LLVM exception. Linux O3DE never exercises the DXIL path. A Linux-only DXC built from upstream Microsoft sources without DXIL is redistributable, and lands the bundle squarely in Fedora's accepted vendored-compiler precedent (emscripten, halide, hipcc).

**Engine architecture (per Nick_L 2026-05-05 sig-build response, [#6](https://github.com/nickschuetz/o3de-rpm/issues/6)):** the engine never links DXC. It shells out to the `dxc` executable at shader-compile time. There is no library API surface to match in the rebuild; only the CLI contract matters.

**Source layout:** the bundle pin `1.8.2505.1-o3de-rev3` decomposes as source git tag (`release-1.8.2505.1-o3de` in the [o3de/DirectXShaderCompiler](https://github.com/o3de/DirectXShaderCompiler/tree/release-1.8.2505.1-o3de) fork) plus the package-system revision counter (`-rev3`, just rebuilds of the same source). The o3de fork's carry-patch is 4 commits on top of upstream Microsoft `release-1.8.2505`: one Linux compile fix, one adds a `dxsc` tool, the others are general improvements. Build recipe in [`o3de/3p-package-source/tree/main/package-system/DirectXShaderCompiler`](https://github.com/o3de/3p-package-source/tree/main/package-system/DirectXShaderCompiler).

**Bundle contents reality check (2026-05-28 re-audit).** The original `DirectXShaderCompilerDxc-1.8.2505.1-o3de-rev3-linux` bundle's `lib/` directory ships exactly two files: `libdxcompiler.so` and `libdxil.so`. It does NOT ship `libclang-12.so.1` or `libtinfo.so.6` as separate shared libraries; LLVM 12 + Clang 12 are statically linked into `libdxcompiler.so` and into the `dxc-3.7` / `dxa-3.7` / `dxopt-3.7` / `llvm-*` binaries. The original bundled `dxc-3.7` dynamically links only `libtinfo.so.6` from /lib64 plus standard libstdc++/glibc (verified via `ldd`). The spec's `%__requires_exclude libclang-12` clause is a no-op today (auto-Requires never generates that symbol against anything we ship) and can drop in a future cleanup pass. The earlier framing about "bundled libclang-12.so.1 + libtinfo.so.6 under Builders/DirectXShaderCompiler/lib/" was inaccurate.

**What the rebuild shipped:**

1. SRPM `o3de2605-dxc-spirv` built upstream Microsoft DXC `release-1.8.2505` against system clang/LLVM, applying the 4-commit o3de carry-patch as a packaging-side patch. SPIRV-only configuration (`ENABLE_SPIRV_CODEGEN=ON`, `SPIRV_BUILD_TESTS=OFF`, `CLANG_INCLUDE_TESTS=OFF`); no DXIL-target options. Twelve build iterations resolved Fedora-toolchain integration issues (cyclic clang static-deps with Fedora's `%cmake` BUILD_SHARED_LIBS=ON default, Fedora vs DXC `basetsd.h` LONG-type collision, SPIRV-Tools-opt INTERFACE_LINK_LIBRARIES propagation gap). See `BUNDLED_LIBRARIES.md` § "Binary-only / DXC-class dependencies" for the full iteration history.
2. Built RPM (8.4 MB compressed, 22.8 MB installed) ships only `/usr/bin/dxc`, `/usr/bin/dxsc`, `/usr/lib64/libdxcompiler.so`. Drops the unused `dxa` / `dxl` / `dxopt` / `dxr` / `dxv` / `llvm-*` / `opt` binaries the original bundle carried, and drops the entire DXIL signing tooling.
3. Functional verification: `dxc -spirv -T ps_6_0 -E main shader.hlsl` produces valid SPIR-V output (`OpCapability Shader / OpMemoryModel Logical GLSL450 / OpEntryPoint Fragment %main`); links cleanly to system `libSPIRV-Tools.so` + bundled DirectX-Headers (DXC has its own Win-types compat layer that conflicts with Fedora's DirectX-Headers, so DirectX-Headers stays bundled as Source2 at DXC's exact submodule SHA `980971e`).
4. Engine-side glue: `system_dxc` bcond + Patch0008 + install-time symlink overlay route engine consumption to the system binary. Engine code unchanged.

**Residual housekeeping:**

- Drop `%__requires_exclude ^libclang-12\.so.*|^libtinfo\.so\.6.*` from the spec once the bundled DXC stops shipping in any active channel (the `libtinfo.so.6` half becomes a proper auto-Requires against system libtinfo once the rebuild fully replaces the bundle).
- File a small Bundling Library Exception for the bundled DirectX-Headers sub-source in `o3de2605-dxc-spirv` (DXC's compat-layer conflict with Fedora's DirectX-Headers is the reason); narrow scope.

**Side benefits realized:**
- Eliminated the only mandatory restricted bundle. Remaining restricted bundles (NvCloth + squish-ccr) are both feature-gated.
- Engine binary size and runtime-fetcher surface area reduced.

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
| **NvCloth** | NVIDIA proprietary, not Fedora-acceptable | the NvCloth Gem (cloth simulation) — optional | **Confirmed standalone via three independent evidence types (2026-05-06 / 2026-05-07).** (1) Cheddarspice runtime test 2026-05-06: NvCloth Gem still works with PhysX 4 removed + PhysX 5.6.1 active (chicken prefab cloth test). (2) Steve P [Amazon] code review 2026-05-07: "I didn't see any direct references to the actual physx4 library in any of the nvcloth code" (independent static analysis). (3) Cheddarspice structural explanation 2026-05-07: "NvCloth has its own standalone PxShared library and Foundation which PhysX5 has it's own as well" — explains *why* the code review found no PhysX 4 refs and *why* the cloth test passed. The earlier "auto-resolves via PhysX 4 retirement" framing (Nick_L 2026-05-05) is falsified. **Treat as a regular restricted bundle:** option A (drop the Gem) is now well-supported, not tentative — three corroborating evidence types make cascading-dependency surprises unlikely. Option B (runtime fetcher) remains the alternative. PhysX 5's `PxDeformableSurface` is CUDA-only so it's NOT a viable substitute for non-NVIDIA-GPU Linux users. PR #19726 (PhysX 4 retirement) is approved by both Steve P [Amazon] and Nick_L (tested against physx4 default + NewspaperDelivery samples; PhysX→PhysX5 alias removes need for conversion script). Merge timing has a hedge though — alex7900 surfaced an upgrade-tool edge case in #sig-build 2026-05-07 PM (`'PHYSX_SETREG_GEM_NAME' macro redefined` error after running the upgrade-physx-gem script on a Multiplayer-Gem project), which gives Nick_L's proposed registry-fallback enhancement (lookup PhysX5 first, fall back to PhysX) more relevance. The enhancement isn't strictly required for merge; could go in same week or could slip if maintainers want it bundled. When the PR does merge, Patch0009's PhysX4 hunk becomes dead code (mechanical rebase: drop the PhysX4 hunk, regenerate the patch). Long-term upstream disposition (keep NvCloth in core vs move to optional/restricted-Gem-repo) is still open. |
| **poly2tri** | Specific O3DE-vendored fork has license-attribution issues | polygon-prism shape colliders (PhysX Gem editor utility) — narrow feature | **Reframed 2026-05-07 — Stage 1 swap candidate, not restricted.** Audit ([#7](https://github.com/nickschuetz/o3de-rpm/issues/7)) found poly2tri consumers exclusively in `Gems/PhysX/` (zero references in core `Code/`); engine uses public `p2t::` namespace API only (no internal-symbol coupling). Fedora's `poly2tri-devel` ships from Mason Green's BSD-3-Clause original (commit `26242d0a`, May 2013) — license-clean and independent of the bundled fork's attribution issue. Implemented as the 8-pack's incremental Stage 1 swap (Patch0009 gating PhysX{4,5} PAL_linux.cmake on `LY_USE_SYSTEM_POLY2TRI`; `Findpoly2tri-system.cmake` bridging engine's `<poly2tri.h>` syntax to `/usr/include/poly2tri/poly2tri.h`). Same audit-track playbook that delivered the AzCore Lua PR (#19733) and the OpenEXR shim split. **Strategic implication:** the original "must drop the feature OR runtime-fetch" framing was wrong — the Fedora-track answer is a clean Stage 1 swap. |
| **squish-ccr** | Patent-encumbered texture compression algorithms | ImageProcessing Gem (BC7 asset bake) — narrow feature | **Audit 2026-05-07 — stays restricted.** Same audit pass that flipped poly2tri also confirmed squish-ccr genuinely belongs in this table: (1) Fedora's `squish` package is the upstream libsquish library (DXT compression only — BC1/BC3/BC5), which lacks BC7 entirely; (2) the squish-ccr fork's BC7 codec is the patent-encumbered piece that Fedora couldn't ship even if it were a separate package; (3) the engine consumes squish-ccr-specific extension API beyond upstream libsquish's surface, so an ABI-compatible drop-in isn't possible. Disposition: handle via option A (drop the BC7 path in the ImageProcessing Gem's bake step — engine still produces other texture formats) or option B (runtime fetcher). Option C (rebuild as a license-clean fork without BC7) loses the feature anyway, so option A is simpler. |

**Three handling options for the Fedora-shippable variant:**

| Option | Description | Pro | Con |
|---|---|---|---|
| A. Disable affected Gems | Drop NvCloth Gem, replace squish with a system substitute, skip navmesh features | clean license posture | feature loss; DXC is still required so this alone isn't sufficient |
| B. Runtime fetcher | `/opt/O3DE/<version>/python/fetch-restricted-deps.sh` — one-time post-install opt-in mirroring `get_python.sh`; downloads to `~/.o3de/3rdParty/` from `packages.o3de.org` | full feature set | requires user network action; some Fedora reviewers disapprove of this pattern |
| C. License-clean DXC rebuild | Build DXC from upstream NCSA/Apache-2.0 sources, configured Vulkan-only / SPIR-V-output (no Windows DXIL signing). Combined with A or B for the others. | best license posture | most engineering effort |

**Current preference:** **B** for short-term Fedora viability + **C as a follow-up** to reduce the runtime-fetch surface. After the 2026-05-07 audit pass, the long-run runtime-fetch / drop-feature surface is **DXC + NvCloth + squish-ccr** — `poly2tri` flipped out of this set into Stage 1 (Fedora's `poly2tri-devel` is license-clean, see the table above). DXC is the load-bearing one regardless — making it license-clean is the hardest single win.

### How upstream contributors can help

This section exists for O3DE upstream contributors (3rdParty maintainers, sig-build folks, anyone with engine-internals visibility) reading this doc and wondering what concrete asks would unblock Fedora-track work. Each ask is something a packager can't determine from outside; an upstream contributor with the right context can answer in minutes.

**For DXC (critical-path; license-clean Linux rebuild — the highest-leverage win):** tracked at [#6](https://github.com/nickschuetz/o3de-rpm/issues/6). Sub-questions 1 and 3 ANSWERED by Nick_L 2026-05-05; sub-question 2 implicitly resolved.

1. **What's in the `-o3de-rev3` suffix?** — **ANSWERED.** `-rev3` is just the package-system revision counter; source git tag is `release-1.8.2505.1-o3de` in the [o3de fork](https://github.com/o3de/DirectXShaderCompiler/tree/release-1.8.2505.1-o3de). Diff against upstream Microsoft `release-1.8.2505` is **4 commits** — Linux compile fix, `dxsc` tool addition, and contributions that "should be contrib'd upstream tbh." Carry-patch is small + tractable.
2. **Could the engine accept an external DXC via cmake?** — Implicitly resolved. The engine just shells out to a `dxc` binary; `$PATH` discovery or an `LY_DXC_PATH` (or `LY_DXC_EXECUTABLE`) cmake var both work cleanly. No library-finding plumbing needed.
3. **What internal DXC API surface does the engine actually depend on?** — **ANSWERED (massive simplification).** Engine **doesn't link DXC** at all. DXC is invoked as a runtime/tool-time **executable** (the `dxc` binary), not linked as a library. So the license-clean rebuild only needs to produce a working `dxc` binary that produces SPIR-V output and accepts the same CLI. **No `libdxcompiler.so`, no internal LLVM symbol concerns, no `__requires_exclude` workaround needed in the post-rebuild spec.**

**For poly2tri + squish-ccr (Gem-boundary clarification):** [#7](https://github.com/nickschuetz/o3de-rpm/issues/7) — **partially answered by audit 2026-05-07.**

4. **Is each restricted bundle's dependency at the Gem boundary, or deeper?** **Audit answered.** poly2tri: Gems/PhysX/ only (Editor's PolygonPrismMeshUtils for polygon-prism shape colliders; zero references in core Code/); plus Fedora's poly2tri-devel turned out to be license-clean, so it's now a Stage 1 swap, not a restricted bundle (see table). squish-ccr: ImageProcessing Gem only, but the Fedora-side alternative (libsquish) lacks BC7 entirely and the squish-ccr fork's API surface diverges from upstream — stays in this table. Engine impact: if a distro drops squish-ccr, the BC7 path in the ImageProcessing Gem's bake step disappears; non-BC7 texture formats (BC1/BC3/BC5/uncompressed) still bake fine.

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
