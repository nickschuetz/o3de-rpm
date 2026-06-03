# Contributing to o3de-rpm

This document is for **packaging contributors** — anyone who wants to change the spec, the test suite, the build flow, or the documentation. End users and engine contributors who want to test their O3DE branch as a Fedora RPM should start with [`README.md`](README.md) and [`tests/README.md`](tests/README.md) instead.

---

## What this repo is

A single RPM spec (`o3de.spec`) plus its sources/, patches/, tests/, and CI infrastructure for building and shipping the [Open 3D Engine](https://o3de.org) as an installable Fedora package. The same spec produces:

- **Stable release builds** from upstream's tagged release tarball
- **Development snapshot builds** from any git ref (branch, tag, commit) of `o3de/o3de`

via a single `--with snapshot` toggle.

The longer-term goal is inclusion in Fedora proper. The roadmap to that lives in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md). The per-bundle Fedora-readiness assessment lives in [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md).

---

## Repo layout, briefly

| Path | Purpose |
|---|---|
| `o3de.spec` | the spec itself (single source of truth for the RPM) |
| `README.md` | end-user / community-tester facing |
| `ARCHITECTURE.md` | source-to-RPM flowchart + load-bearing design separations |
| `CONTRIBUTING.md` | this file |
| `Makefile` | `make help` lists the targets — lint, srpm, rpm, copr, test |
| `FEDORA_ROADMAP.md` | staged plan for Fedora inclusion |
| `BUNDLED_LIBRARIES.md` | per-bundle license / version / migration status |
| `sources/` | rpm SOURCES dir (sources + patches; rpm flattens these) |
| `tests/` | post-install integration test suite (Tiers 1–10) |
| `.github/workflows/` | CI: spec lint, RPM-install tests |

Two files **deliberately excluded from git** as working notes (see `.git/info/exclude`):

| Path | Purpose |
|---|---|
| `BUILD_NOTES.md` | scratchpad of build-test findings; rolled forward across sessions, deleted when each finding becomes a permanent doc or a fix |
| `FLATPAK_NOTES.md` | carry-over notes for a future Flatpak repo — what transfers, what differs, gotchas |

---

## How the spec is structured

Read `o3de.spec` top-to-bottom. The shape is:

1. **Build-mode toggles** (`%bcond_with`) — `snapshot`, `stabilization`, `debug`, `thirdparty_*`, plus `development_snapshot` (added 2026-05-18; gates the 6 carry-patches whose upstream equivalents have merged into `o3de/development` so they don't fail-to-apply when building against dev-branch tip; default OFF so stabilization channel builds are unchanged; requires a matching `--rpmbuild-with development_snapshot` on the COPR project's chroots because `--with` flags don't propagate through SRPM rebuild — see [[feedback_copr_with_propagation]])
2. **Version pinning** — `stable_tag`, `engine_cmake_version` (derived 3-component for cmake), snapshot pins
3. **Versioned-naming macros** (derived from `stable_tag`) — `o3de_major_tag` (e.g. `2605`), `o3de_pkgname` (e.g. `o3de2605`), `o3de_install_prefix` (e.g. `/opt/O3DE/26.05.0`). Bump `stable_tag` to `2610.0` and the spec automatically produces an `o3de2610` package at `/opt/O3DE/26.10.0/` — no other edits needed. Subpackages (`%{name}-debug`, `%{name}-devel`) inherit the versioning automatically. **NOT versioned: `engine.json`'s `engine_name` field.** The cmake `-DO3DE_INSTALL_ENGINE_NAME=o3de` literal sets engine.json's identity to upstream's default — that's what gem manifests' `compatible_engines` lists check against (e.g. `["o3de-sdk>=2.3.0", "o3de>=2.3.0"]`). Setting engine_name to a versioned form would reject every existing third-party gem. See the comment block above the `cmake \\` invocation in the spec for the trade-off detail.
4. **rpm build behavior**: `debug_package`, payload compression, `__requires_exclude` (historical clause for DXC's bundled libclang-12 / libtinfo.so.6; verified 2026-05-28 as a no-op today, tracked as Stage 5 housekeeping for removal)
5. **Name / Version / Release** with conditional logic for snapshot mode (`Name: %{o3de_pkgname}`)
6. **Source0** (the upstream tarball — release URL or local snapshot)
7. **Source10–25** (auxiliary files: launcher, desktops, metainfo, icons, SBOM, snapshot helper)
8. **Patch0001-0013 all active** via `%autosetup -p1`. Six carry-patches now have TIMEBOMB notes (upstream-equivalent merged into `development` but not into `stabilization/26050`; they retire when stabilization absorbs the changes): Patch0001 + Patch0002 + Patch0005 (merged 2026-05-14), Patch0007 + Patch0008 (merged 2026-05-08), Patch0012 v2 (merged 2026-05-15). Patch0012 is the v2 child-side watchdog after the v1 prctl approach was withdrawn 2026-05-12; v1 patch file retained in `sources/` as reference. Patch0013 v4 gates the vulkan-validationlayers Stage 1 swap in three places (BuiltInPackages, PAL_linux, Instance.cpp). Lua 5.5 compat hits Patch0008/0010/0011 conditionally on the rawhide chroot.
9. **BuildRequires / Requires** — minimal, validated against auto-Requires
10. **`%prep`, `%build`, `%install`, `%check`, `%files`** — standard rpm sections
11. **Scriptlets** (`%post`, `%postun`)
12. **Changelog**

If you change *anything* in the spec or sources/, **update the README's layout block, the `ARCHITECTURE.md` Mermaid diagram and prose, and any other doc section that references the changed file** — in the same commit. This is a hard rule; doc drift is treated as a regression.

---

## Patches

Thirteen active patches in `sources/`. **Six TIMEBOMBs** -- upstream-equivalents merged to `development` but not to `stabilization/26050` (our snapshot source branch); they retire when stabilization absorbs the changes. The new `--with development_snapshot` bcond (2026-05-18) gates all six off so `make copr-development` can build against dev-branch tip without `%prep` failing to apply them — local SRPM-build only; for COPR you also need `--rpmbuild-with development_snapshot` on the chroot:

- Patch0001 (clang21 `-Wno-error=`) <- [#19748](https://github.com/o3de/o3de/pull/19748) merged 2026-05-14
- Patch0002 (manifest.py `O3DE_ENGINE_PATH`) <- [#19751](https://github.com/o3de/o3de/pull/19751) merged 2026-05-14
- Patch0005 (AzQtComponents title propagation) <- [#19750](https://github.com/o3de/o3de/pull/19750) merged 2026-05-14
- Patch0007 (libtiff C99 typedefs) <- [#19734](https://github.com/o3de/o3de/pull/19734) merged 2026-05-08
- Patch0008 (drop AzCore Lua/lobject.h include) <- [#19733](https://github.com/o3de/o3de/pull/19733) merged 2026-05-08
- Patch0012 v2 (AssetBuilder parent-death watchdog) <- [#19747](https://github.com/o3de/o3de/pull/19747) merged 2026-05-15

Patch0012 is the v2 child-side watchdog after the v1 prctl approach was withdrawn 2026-05-12; the v1 patch file is retained in `sources/` as reference. Patch0013 is v4 of the vulkan-validationlayers Stage 1 gate; v3 failed cmake configure because the gem still expanded `${VULKAN_VALIDATION_LAYER}` in BUILD_DEPENDENCIES, v4 gates the variable assignment in PAL_linux.cmake. Each carries a `From: Nick Schuetz <nschuetz@redhat.com>` and `Subject:` header explaining why the patch exists.

| # | Target | Purpose | Upstream-worthy? |
|---|---|---|---|
| 0001 | `cmake/Platform/Common/Clang/Configurations_clang.cmake` | suppress clang 21+ warnings-as-errors that O3DE's `-Werror` would otherwise fail on. **TIMEBOMB:** upstream merged equivalent as [o3de/o3de#19748](https://github.com/o3de/o3de/pull/19748) (commit c2486d165441) into `development` on 2026-05-14 but NOT into `stabilization/26050` (our snapshot source branch); retires when stabilization absorbs the change. nick-l-o3de informally flagged this for 26.05.0 cherry-pick consideration ("we may need this one for this release"). | **landed in development** (waiting on stabilization, possible release cherry-pick) |
| 0002 | `scripts/o3de/o3de/manifest.py` | honor `O3DE_ENGINE_PATH` env var for engine-root detection in venv-installed setups. **TIMEBOMB:** upstream merged equivalent as [o3de/o3de#19751](https://github.com/o3de/o3de/pull/19751) (commit 0281a9bbc492) into `development` on 2026-05-14 but NOT into `stabilization/26050`; retires when stabilization absorbs the change. | **landed in development** (waiting on stabilization) |
| 0003 | `python/get_python.sh` | per-engine venv linkage + engine-id reconciliation + manifest.py refresh | **probably** -- helps multi-engine and read-only-engine installs; more involved than 0001/0002, more rebase-fragile |
| 0004 | `cmake/LYPython.cmake` | install Python packages from sdists (not editable) when `INSTALLED_ENGINE` | **yes** -- `pip install -e` against a read-only directory is straightforwardly broken; this is the right fix |
| 0005 | `Code/Framework/AzQtComponents/.../WindowDecorationWrapper.cpp` | propagate guest's initial title to wrapper in `OptionDisabled` mode (Linux/Mac) so Project Manager's WM-drawn titlebar shows the engine version. **TIMEBOMB:** upstream merged equivalent as [o3de/o3de#19750](https://github.com/o3de/o3de/pull/19750) (commit d8d1c9aeb1c6) into `development` on 2026-05-14 but NOT into `stabilization/26050`; retires when stabilization absorbs the change. | **landed in development** (waiting on stabilization) |
| 0006 | `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` | gate the upstream `ly_associate_package(... mikkelsen-1.0.0.4-linux ...)` line on a new `LY_USE_SYSTEM_MIKKELSEN` cmake variable, so distro packagers can opt out of the upstream fetcher in favor of a system mikktspace. First Stage 1 system-library swap. | **as part of an umbrella PR** -- see backlog note below |
| 0007 | `Gems/Atom/Asset/ImageProcessingAtom/.../TIFFLoader.cpp` + `Code/Editor/Util/ImageTIF.cpp` | replace every remaining legacy libtiff `uint8` / `uint16` / `uint32` typedef use with the standard C99 `*_t` form across both `<tiffio.h>` consumers. libtiff 4.5+ marks the legacy typedef `__attribute__((deprecated))`; with O3DE's `-Werror` every stale use is a hard build failure. Mechanical type rename; same underlying types. **TIMEBOMB:** upstream merged equivalent as [o3de/o3de#19734](https://github.com/o3de/o3de/pull/19734) (commit dda736e0) into `development` on 2026-05-08 but NOT into `stabilization/26050` (our snapshot source branch); retires when stabilization absorbs the change. | **landed in development** (waiting on stabilization) |
| 0008 | `Code/Framework/AzCore/Script/ScriptContext.cpp` | drop a redundant `<lua/lobject.h>` include whose member-access layout breaks under Lua 5.5 (the header was already pulled in transitively via lua.h; the explicit include was vestigial). Single blocker for system_lua activation on Fedora (lua-devel ships only public-API headers). **TIMEBOMB:** upstream merged equivalent as [o3de/o3de#19733](https://github.com/o3de/o3de/pull/19733) (commit 3e715c61) into `development` on 2026-05-08 but NOT into `stabilization/26050` (our snapshot source branch); retires when stabilization absorbs the change. | **landed in development** (waiting on stabilization) |
| 0009 | `Gems/PhysX/.../physx_pal_platform.cmake` | gate the upstream `ly_associate_package(... poly2tri ...)` line on `system_poly2tri` so the PhysX gem can resolve via Fedora's `poly2tri-devel` when the swap is active | **as part of the umbrella PR alongside Patch0006** |
| 0010 | `Code/Framework/AzCore/Script/ScriptContext.cpp` | Lua 5.5 introduced an extra `warnflag` argument to `lua_newstate`; provide a `#if LUA_VERSION_NUM >= 505` shim that adapts the call sites. Behavior-preserving on 5.4. | **yes** -- mechanical compat; upstream will want this when they bump the bundled Lua |
| 0011 | `Code/Tools/LuaIDE/.../WatchesPanel.cpp` | Lua 5.5 removed the `LUA_NUMTAGS` public macro; restore it under the same guard pattern as Patch0010 for the LuaIDE compile path | **yes** -- partner patch to 0010; ditto upstream-worthy |
| 0012 | `Code/Tools/AssetProcessor/AssetBuilder/main.cpp` | **v2 (active).** Adds `StartParentDeathWatchdog()` to AssetBuilder's `main()` -- detached thread polls `getppid()` every 2 seconds, calls `_exit(0)` when the parent PID changes (reparented to PID 1 / systemd-user because AP died). Independent of caller threading. POSIX (Linux + Mac) only; Windows port deferred. v1 (`m_tetherLifetime = true` enabling `prctl(PR_SET_PDEATHSIG)`) was withdrawn 2026-05-12 after runtime test showed every builder SIGTERM'd within ~21 ms of fork because BuilderManager forks from short-lived TaskWorker threads. v1 patch file kept in `sources/` as reference. Memory: `project_prctl_pdeathsig_thread_gotcha.md`. **TIMEBOMB:** upstream merged equivalent as [o3de/o3de#19747](https://github.com/o3de/o3de/pull/19747) (commit 6fd830546c72) into `development` on 2026-05-15 but NOT into `stabilization/26050`; retires when stabilization absorbs the change. | **landed in development** (waiting on stabilization) |
| 0013 | `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` + `Gems/Atom/RHI/Vulkan/Code/Source/Platform/Linux/PAL_linux.cmake` + `Gems/Atom/RHI/Vulkan/Code/Source/RHI/Instance.cpp` | three-hunk Stage 1 gate for the vulkan-validationlayers swap (`LY_USE_SYSTEM_VULKAN_VALIDATION_LAYERS`): skip the `ly_associate_package` line, leave `VULKAN_VALIDATION_LAYER` unset (so `${VULKAN_VALIDATION_LAYER}` in the gem's BUILD_DEPENDENCIES expands to nothing), and flip the `VK_LAYER_PATH` SetEnv overwrite flag from 1 to 0 so distro/Flatpak launchers pre-setting that env var win over the engine's exeDirectory default. Validated end-to-end on build 10457745 (2026-05-13/14, all three chroots green). | **as part of the umbrella PR alongside Patch0006/0009** -- same pattern, runtime-only dep so the system_X gate is a single-flag distro-packager convenience |

### Adding a new system-library swap

The end-to-end checklist for migrating one bundled 3rdParty package to its Fedora system equivalent. See ARCHITECTURE.md ("How a Stage 1 system-library swap resolves") for why each piece exists.

1. **Pre-flight: confirm the bundled copy is vanilla.** If O3DE's prebuilt is a patched fork, the system package cannot substitute. Watch for `-rev`/`_az` naming and diff its headers against the system version. (RapidXML's `-rev1` AZ-extension fork adding `isError()`/`getError()` is why `system_rapidxml` was walked back.)
2. **bcond** in `o3de.spec`: `%bcond_with system_<lib>`.
3. **Find shim**: add `sources/Find<X>-system.cmake` and declare it as a `Source3N:`. Most can delegate to cmake's stock `Find<X>` and just produce the `3rdParty::<X>` alias; add include-path or header-case bridging only if the consumer include syntax differs from Fedora's layout.
4. **`%prep` copy** (gated): `%if %{with system_<lib>}` then `cp %{SOURCE3N} cmake/3rdParty/Find<X>.cmake`. Note the rename to the canonical name (that is what `find_package(<X>)` looks for).
5. **Gate the associate line**: in the BuiltInPackages patch wrap `ly_associate_package(... <X> ...)` as `if (NOT LY_USE_SYSTEM_<X>) ... else() find_package(<X> REQUIRED) endif()`. Patch0006 holds the multiplatform + linux-core gates; gem-specific libraries (poly2tri -> Patch0009, vulkan-validation-layers -> Patch0013) get their own patch against the gem's cmake.
6. **cmake flag**: pass `-DLY_USE_SYSTEM_<X>=ON` from `%build`, gated on the bcond.
7. **The BR + Requires + Recommends trio** (all three; the Recommends is the one that gets forgotten): `BuildRequires: <X>-devel`, the runtime `Requires:`, and `Recommends: <X>-devel` so source-building consumers get the headers. Rule of thumb: any installed `Find<X>.cmake` with a `find_path` wants the matching Recommends.
8. **COPR chroots**: `copr-cli edit-chroot --rpmbuild-with system_<lib>` on every shipping project's chroots. The with-opts list is REPLACED, not appended, so pass the full intended set in one invocation and verify with `get-chroot`.
9. **Tests**: add a version-wildcarded row to the Tier 2 swap-health loop (`tests/integration-test.sh`) and the Tier 7 SONAME + symbol check (`tests/asset-bake-test.sh`). Never pin an exact F44 SONAME; rawhide drifts ABIs.
10. **Validate on `o3de-experimental` first**, then promote (experimental -> testing/stabilization -> stable), adding the `--rpmbuild-with` flag to each project's chroots as it ships.

### Upstream PR backlog -- status

This section was originally pre-flight planning. As of 2026-05-14/15 several PRs have actually been filed and merged. Current state:

**Merged to `o3de/o3de:development`** (carry-patches retire post-release when our snapshot pin moves):
- Patch0001 (clang21 `-Wno-error=`) -- [o3de/o3de#19748](https://github.com/o3de/o3de/pull/19748)
- Patch0002 (manifest.py `O3DE_ENGINE_PATH`) -- [o3de/o3de#19751](https://github.com/o3de/o3de/pull/19751)
- Patch0005 (AzQtComponents title propagation) -- [o3de/o3de#19750](https://github.com/o3de/o3de/pull/19750)
- Patch0007 (libtiff C99 typedefs) -- [o3de/o3de#19734](https://github.com/o3de/o3de/pull/19734)
- Patch0008 (drop AzCore `<Lua/lobject.h>` include) -- [o3de/o3de#19733](https://github.com/o3de/o3de/pull/19733)
- Patch0012 v2 (AssetBuilder parent-death watchdog) -- [o3de/o3de#19747](https://github.com/o3de/o3de/pull/19747) merged 2026-05-15
- Also: Microphone PAL libsamplerate gate -- [o3de/o3de#19737](https://github.com/o3de/o3de/pull/19737)
- Plus an AR-unblocker we filed during integration testing: ParticleBuilder cold-cache JobDependency fix -- [o3de/o3de#19756](https://github.com/o3de/o3de/pull/19756) merged 2026-05-15 (not a carry-patch; a new engine-side fix discovered via Tier 9)

**Still open / in review**:
- Patch0004 / [o3de/o3de#19752](https://github.com/o3de/o3de/pull/19752) (LYPython sdist for INSTALLED_ENGINE) -- nick-l-o3de investigating "larger problem"; let him lead.
- [o3de/o3de#19746](https://github.com/o3de/o3de/pull/19746) (ProcessWatcher prctl doc comment) -- doc-only; CI flaky pending #19756's effect across AR.
- Issue [o3de/o3de#19745](https://github.com/o3de/o3de/issues/19745) (BuilderManager design discussion).

**Held until post-release** (per `MEMORY.md` upstream-baking rule + `project_2605_stabilization_branch_locked.md`):
- Patch0003 (per-engine venv linkage / engine-id reconciliation in `get_python.sh`) -- sensitive bundled-Python territory; pitch as an issue first when bandwidth allows.
- Patch0006 + Patch0009 + Patch0013 (LY_USE_SYSTEM_<X> cmake gates -- mikkelsen, poly2tri, vulkan-validation-layers) -- propose as a single umbrella "distro packager opt-out convention" PR with all activated swaps documented.
- Patch0010 + Patch0011 (Lua 5.5 forward-compat) -- pitch as one Lua 5.5 compat bundle when upstream's bundled-Lua bump arrives.

**Regeneration** when an upstream change makes a patch fail to apply (we hit this once on patch 0001):

1. Find a stable anchor in the source — e.g. `-Werror` rather than a specific `-Wno-*` flag whose surrounding context might rearrange.
2. Extract the upstream file from the snapshot tarball: `tar -xzOf sources/o3de-<commit>.tar.gz <commit>/path/to/file > /tmp/orig`
3. Apply the intended change to a copy: `cp /tmp/orig /tmp/patched && $EDITOR /tmp/patched`
4. Diff: `diff -u /tmp/orig /tmp/patched > sources/000N-<name>.patch`
5. Add a `From:`/`Subject:` header explaining *why*, with the rationale a reviewer will ask for.

---

## Build flow (locally)

```bash
make snapshot REF=<git-ref>      # produce sources/o3de-<commit>.tar.gz, print pin values
$EDITOR o3de.spec                # paste snapshot_commit / snapshot_date / snapshot_sha256
make rpm-snapshot                # full -bb (profile only, ~30 min on a 32GB workstation)
make rpm-snapshot-debug          # full -bb + o3deNNNN-debug subpackage (~2x build time)
```

**Always use `make snapshot` (or equivalently `sources/make-snapshot-tarball.sh`) for snapshot bumps, never `curl https://github.com/o3de/o3de/archive/<sha>.tar.gz` directly.** The GitHub archive endpoint silently serves git-LFS POINTER files for any LFS-tracked content (fonts, large textures), producing a tarball that's about 50x smaller than expected (~39MB vs ~1.9GB) and ships 1300+ LFS placeholders into the install. The engine binaries link cleanly; assets bake to broken/empty products; the breakage surfaces a layer downstream (sample-project bakes, font rendering, etc.). The script does `git clone --depth 1 --branch <ref> + git lfs pull + tar` -- the LFS pull is the load-bearing step. Caught the hard way 2026-05-25 in stab build 10507773 -- see commit `3eea141` for the full incident write-up.

**A note on local-vs-COPR build times.** The "~30 min" above reflects the current Stage 1 + Stage 2 swap stack (14 Stage 1 system swaps + 3 Stage 2 -- mcpp/dxc/spirvcross -- as of 2026-05-14). Each swap removes a bundled-3p compile from the build, so build times have shortened substantially as the swap stack grew (was "~3-4 hours" in early-stage docs, "~70 min" by mid-2026). COPR builds still take 4-6 hours: shared hardware, no persistent ccache between builds, fresh mock chroot per submission. Use local rebuilds for the development iteration loop (test a spec change, rebuild, dnf reinstall, re-test in ~35 min total); use COPR for promotion of validated artifacts to testers.

Or run the test harness end-to-end:

```bash
make test-branch REF=<git-ref>   # snapshot + build + install + run integration tests
```

---

## Build flow (COPR)

Five related projects under the same owner (`hellaenergy`):

| Project | Purpose | Audience | Mid-flight changes? |
|---|---|---|---|
| `hellaenergy/o3de-dependencies` | Fedora-clean SRPMs for non-Fedora deps (custom Qt, PhysX, AWSNativeSDK, mikkelsen, the Stage 2 rebuilds, ...) | Consumed by the five engine projects via `additional_repos` | Rare; these are vetted system-library replacements |
| `hellaenergy/o3de` | Tagged-release engine builds | End users wanting a stable release | Only at upstream release cadence + post-soak promotions from `o3de-testing` |
| `hellaenergy/o3de-testing` | Pre-promotion soak channel for stable. Same engine source tag as stable, with packaging-side bug fixes + minor enhancements queued for promotion. Mirrors Fedora's `updates-testing` semantics. | Early adopters who want to validate packaging fixes before they reach broader stable | Push freely from main HEAD when user-facing fixes are ready; promote to stable after ~48h soak without regression reports |
| `hellaenergy/o3de-stabilization` | Pre-release validation builds from upstream `stabilization/<release>` (e.g., `stabilization/26050`). Active during a 4-week pre-release window per release cycle. | Community testers Nick has invited to validate engine-side pre-release | **Hands off when testers are active** during a stabilization window; dormant between windows |
| `hellaenergy/o3de-development` | Always tracks upstream `o3de/development` tip | Engine contributors validating the bleeding-edge branch | Push freely (ad-hoc cadence, no testers expecting regular cadence). For arbitrary other refs (e.g. qt6), create a dedicated COPR project per branch. |
| `hellaenergy/o3de-experimental` | Packagers' migration-work channel. New `system_<X>` swap candidates, COPR-rebuilt dep PoCs, structural spec rework validate here before promotion to stabilization (during a stab window) or testing (post-release). Distinguished by the `-experimental.<commit>` channel marker. | Just us, until validated | Push freely; promote to `-stabilization` or `-testing` when validated |

The five engine projects all set `enable_net=true` (so cmake can fetch the remaining bundles from `packages.o3de.org` at build time; current set: NvCloth + squish-ccr restricted-by-license, plus tiff + OpenSSL + OIIO/OCIO + pyside2 + the unaudited multiplatform deps still in transit toward Stage 1 or Stage 2 coverage) and pull `o3de-dependencies` via the chroot's `additional_repos` (build-time) and `runtime_dependencies` (consume-time, for end users).

**Promotion flow for user-facing packaging fixes** (the standard cadence between upstream release cycles): `main HEAD` -> `make copr-testing-and-test` (publishes to `o3de-testing`; testers see it; CI runs Tier 1-7) -> soak ~48 hours, no regression reports -> `make copr-stable` (publishes the same SRPM to `o3de`). The testing channel exists specifically to absorb "oh wait, the Recommends broke something on a chroot we didn't think about" before it reaches stable users. Skip the testing soak only for the tagged-release ceremony (upstream releases land directly in stable per `POST_RELEASE.md`).

Channel-marker bconds (set on the destination project's chroots via `--rpmbuild-with`): `--with experimental` on `o3de-experimental`, `--with stabilization` on `o3de-stabilization`, `--with development_snapshot` on `o3de-development`. Tagged-release builds going to `o3de` carry no channel bcond and the marker resolves to a clean version string. GUI version strings: `26.05.0-experimental.<sha>`, `26.05.0-stabilization`, `26.05.0-development.<sha>`, or `26.05.0` (stable). The marker reflects the destination *project*, not the active feature set (early Stage 1 logic used to infer `-experimental` from "any system_* swap active" but that broke once swaps graduated into the stab + stable channels too).

Each engine project hosts the **versioned** package(s) that match whatever the spec's `stable_tag` resolves to at build time — currently `o3de2605` (for the 26.05.x line). When the spec rolls forward to `2610.0`, the same projects will start producing `o3de2610` packages alongside (until the older line is pruned). The COPR project name (`o3de`, `o3de-stabilization`, …) is the *channel*; the package name (`o3de2605`, `o3de2610`, …) is the *major*. They're orthogonal.

Workflow:

```bash
make copr-init                       # prints one-time COPR setup commands (chroots, repos, etc.)
make copr-testing                    # build SRPM, upload to hellaenergy/o3de-testing (pre-stable soak)
make copr-stabilization              # build SRPM, upload to hellaenergy/o3de-stabilization
make copr-development                # always dev-branch, uploads to hellaenergy/o3de-development
make copr-experimental               # same SRPM, uploads to hellaenergy/o3de-experimental
make copr-stable                     # tagged release builds (and post-soak promotions from testing)
make copr-testing-and-test           # full pipeline: build + watch + fire CI tests against o3de-testing
make copr-stabilization-and-test     # same, against the stabilization project
make copr-development-and-test       # same, against the development project
make copr-experimental-and-test      # same, against the experimental project
```

---

## Testing

See [`tests/README.md`](tests/README.md) for the tier breakdown. The short version:

- `make test` — read-only checks (Tiers 1, 2, 4) — no state changes
- `make test-setup` — adds Tier 3 (per-user venv + engine register)
- `make test-full` — adds Tier 5 (project end-to-end)
- `make test-ui` — Tier 6 (Project Manager smoke under Xvfb)
- `make test-ui-full` — Tier 6 plus Editor automation
- `make test-asset-bake` — Tier 7 (system-swap library-health check)
- `make test-ap-spawn` — Tier 8 (AssetProcessor runtime smoke)
- `make test-multiplayer-sample` — Tier 9 (real community sample build + bake + launcher smoke; ~60-90 min cold). Builds the full multiplayer harness (client + headless server + spectator server + bare gem for AP). Launcher loads `startmenu` cleanly on Linux; `make play-mps-host` + `make play-mps-client` runs an end-to-end host+connect session.
- `make test-newspaper-delivery` — Tier 10 (sister community sample; ~30-60 min cold). Plays end-to-end: title screen, character control, gameplay HUD active.
- `make test-tier11` / `make test-tier11-multiplayer` — Tier 11 (post-load liveness smoke; ~60-90 s). Verifies the launcher survives running for a window after `LEVEL_LOAD_END`. Requires Tier 9 or 10 cache to be present.
- `make play-mps-host` / `make play-mps-client` / `make play-mps-stop` — manual MultiplayerSample play, not a test. Launches headless server + windowed client (the configuration that's stable for sustained play; see `FOLLOW_UPS.md` for why graphical server + settings menu crashes). Requires Tier 9 to have built the binaries first.
- `make test-branch REF=<git-ref>` — build snapshot from a ref + install + full test suite (Tiers 1-6; doesn't auto-fire Tiers 7-11 due to wall-time cost)

When you add new behavior, **add a corresponding test in the right tier**. Tier 1–2 for installed-state invariants, Tier 3–5 for runtime behavior, Tier 6+ for UI, Tier 7+ for explicit-only heavyweight validation (system-swap drift, AP lifecycle bugs, real community sample integration).

Tier 9 and Tier 10 are the community-sample validation tracks; both pass on Fedora 44 against `o3de2605` as of 2026-05-21 and the test scripts auto-recover from common upstream-side issues (LFS server transients, working-tree pointer files, AWS Lambda batch-size limits, level startup config quirks). The recovery logic lives in the test scripts themselves — read `tests/multiplayersample-build-test.sh` + `tests/newspaper-delivery-build-test.sh` for the inline rationale.

---

## CI

`.github/workflows/lint.yml` runs on every push touching the spec or sources/. It runs in a Fedora 44 container and does:

- `rpmspec --parse` in both stable and snapshot modes
- `rpmlint o3de.spec`
- `desktop-file-validate` on both desktop entries
- `appstream-util validate-relax --nonet` on the metainfo
- `bash -n` on every shell source
- best-effort `patch --dry-run` against the pinned snapshot commit

`.github/workflows/test-installed.yml` runs the integration test suite in clean Fedora containers (matrix: `fedora-44`, `fedora-rawhide`, extending as Fedora releases ship) against an RPM URL — typically a COPR build artifact. Three triggers:

- **Manual** (`workflow_dispatch`) — paste an RPM URL into the GitHub UI's "Run workflow" form.
- **Programmatic** (`repository_dispatch`, `event_type: copr-build-succeeded`) — fired by `make trigger-tests BUILD_ID=<copr-build-id>` after a COPR build succeeds, or end-to-end via `make copr-stabilization-and-test` (which submits, watches, then fires). Requires `gh` authenticated.
- **Cron** (every 4 hours, offset to `:17`) — polls COPR for the latest succeeded build in `hellaenergy/o3de-stabilization`. Dedup via `actions/cache` keyed on the COPR build ID, so the same build is never tested twice.

The full RPM build itself is too heavy for free GitHub runners (~25 GB output, multi-hour compile). COPR does that.

---

## Commit conventions

- **Imperative-mood subject under 70 chars.** "Drop foo" not "Dropping foo" or "Dropped foo".
- **Body explains why.** Reviewers can read the diff for what changed.
- **Reference patch numbers and roadmap stages by name.** `Patch0004`, `Stage 1`, `BUNDLED_LIBRARIES.md § "Restricted (cannot be packaged…)"`.
- **No AI self-attribution.** No `Co-Authored-By: Claude…`, no "Generated with…", no AI tooling credits anywhere.
- **One logical change per commit.** A commit that touches the spec to add `BuildRequires` *and* refactors the launcher belongs as two commits.
- **README + diagram updates land with the change that requires them**, not as a follow-up.

---

## When something breaks during your work

1. **Document it in `BUILD_NOTES.md` first.** What was the symptom, what was the root cause, what was the fix. This file is excluded from git but is the source of truth for working notes that will eventually become permanent docs or PR rationale.
2. **Mirror to `FLATPAK_NOTES.md`** if the finding has Flatpak relevance (compiler quirks, library bundling, sandboxing, file paths). Both files are working notes — drop neither into git, but maintain both.
3. **Make the fix in a commit that also documents the why** in the message body.
4. **Update permanent docs (README, FEDORA_ROADMAP.md, BUNDLED_LIBRARIES.md)** if the finding shifts the roadmap or the bundled-library status.

---

## What's in scope and what isn't

**In scope:**
- Anything affecting `o3de.spec` and how it builds
- Spec patches against upstream O3DE source (`sources/000N-*.patch`)
- The launcher wrapper, desktop entries, metainfo, icons, SBOM
- Tests (Tiers 1–10) and CI workflows
- Documentation that supports any of the above

**Not in scope (different repo or upstream effort):**
- Bug fixes in the engine itself — file upstream at [github.com/o3de/o3de/issues](https://github.com/o3de/o3de/issues)
- The Flatpak (will live in a sibling repo when it's started)
- The `o3de-dependencies` SRPM specs (separate workstream; lives in COPR + a future git repo)

---

## Memory / project conventions across sessions

A few project-level conventions that don't fit elsewhere:

- **Target distros:** Fedora 44+ and CentOS Stream 10+ only. No F43/CS9-or-earlier shims. (Earlier project framing said "RHEL 10+"; that was shorthand for the CS10 line, which is upstream of RHEL 10.)
- **O3DE bundles a custom-patched Qt 5.15-rev9.** Never add system Qt5 BRs/Requires; the rev9 patches are load-bearing.
- **Two restricted bundles today** (NvCloth, squish-ccr) cannot be hosted in Fedora or COPR. DXC retired from this set 2026-05-08 via the license-clean `o3de2605-dxc-spirv` rebuild; poly2tri retired 2026-05-07 via the Stage 1 swap reframe. See `BUNDLED_LIBRARIES.md` § "Restricted".
- **DXC is structurally a Clang/LLVM fork** with LLVM 12 + Clang 12 statically linked into `libdxcompiler.so`. The license-clean Linux rebuild shipped 2026-05-08 (see `BUNDLED_LIBRARIES.md` § "Binary-only / DXC-class dependencies" for iteration history and `FEDORA_ROADMAP.md` § "License-clean DXC rebuild" for the recap).

---

## License

This packaging is `Apache-2.0 OR MIT` to match upstream O3DE.
