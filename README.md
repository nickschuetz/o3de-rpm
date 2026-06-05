# o3de-rpm

RPM packaging for the [Open 3D Engine](https://o3de.org), targeting **Fedora 44+** (including rawhide) and **CentOS Stream 10+**. Builds run on rpm 4.19 (CS10) and rpm 4.20+ (F44 / rawhide); spec authoring conventions handle the parser divergence between them (see `project_cs10_debuginfo_quirk.md` memory note for the two CS10 RPM 4.19 quirks worked around so far).

The same spec produces:

- **Stable release builds**, from upstream's tagged release tarball (`o3de_<tag>_lfs.tar.gz`). These ship to **`hellaenergy/o3de`** (the stable channel; broadest audience) and, before they're promoted there, to **`hellaenergy/o3de-testing`** (pre-promotion soak; Fedora updates-testing semantics; ~48h soak window for packaging-side fixes queued for stable). Both channels build from the same release tarball; the difference is whether the SRPM has soaked yet.
- **Snapshot builds**, from any git ref of `o3de/o3de`. Two upstream branches are common targets and they're *not* the same thing:
  - **`stabilization/<X>`** (e.g. `stabilization/26050`), the pre-release stabilization branch for the next tagged release. Ships to **`hellaenergy/o3de-stabilization`** during the upstream stabilization window (typically a 4-week period before each release tag). Dormant between cycles. When O3DE upstream tags `2605.0`, this branch's tip *is* the release, so snapshots from here are functionally release candidates.
  - **`development`**, the bleeding-edge integration branch where new features land daily. Ships to **`hellaenergy/o3de-development`**. Less stable than a stabilization branch; useful for engine contributors testing in-progress work, less appropriate for community testers expecting near-release quality.
  - Or any other ref, e.g. feature branches, specific commits, tags. Dedicated COPR project per ref rather than overloading the channels above.

It also provides an extension point for bundling pre-built **O3DE 3rdParty packages** into the RPM, gated by per-package `--with` flags so you only pay for what you use.

---

## Layout

```
o3de-rpm/
├── o3de.spec                                          # the spec
├── README.md                                          # this file
├── ARCHITECTURE.md                                    # source-to-RPM flowchart + design separations
├── Makefile                                           # lint / srpm / copr / test targets
├── FEDORA_ROADMAP.md                                  # path to Fedora inclusion
├── BUNDLED_LIBRARIES.md                               # per-bundle license + migration status
├── .github/workflows/                                 # CI
│   ├── lint.yml                                       #   spec parse, rpmlint, validators
│   ├── test-installed.yml                             #   integration tests against RPM URL (4h cron)
│   ├── check-deps-drift.yml                           #   weekly dep-pin drift report (Monday 06UTC)
│   └── snapshot-development.yml                       #   weekly dev-tip rebuild into o3de-development (Sunday 06UTC)
├── tests/                                             # post-install test suite
│   ├── README.md                                      #   tier breakdown + community usage
│   ├── integration-test.sh                            #   tiers 1–5 against installed RPM
│   ├── ui-smoke-test.sh                               #   tier 6: Project Manager + Editor smoke under Xvfb
│   └── test-branch.sh                                 #   build + install + test from git ref
├── copr-metadata/                                     # mirror of each COPR project's user-facing docs
│   └── <project>/{description,instructions}.md       #   pulled/pushed via scripts/copr-metadata.sh
│       {homepage,contact}.txt                        #   make copr-metadata-{pull,diff,push}
├── scripts/                                           # repo tooling (not packaged into the RPM)
│   └── copr-metadata.sh                               #   sync copr-metadata/ ↔ live COPR
└── sources/                                           # rpm SOURCES dir (sources + patches)
    ├── o3de-launcher.sh                               # /usr/bin/o3deNNNN wrapper (Project Manager / Editor GUI)
    ├── o3de-cli                                       # /usr/bin/o3deNNNN-cli wrapper (project / gem / engine management)
    ├── o3de.desktop                                   # .desktop entry (Project Manager) — mutated to <pkgname>.desktop at install
    ├── o3de-editor.desktop                            # .desktop entry (Editor) — NoDisplay=true; exists for dock-icon WM_CLASS pairing
    ├── o3de-material-editor.desktop                   # .desktop entry (Material Editor) — NoDisplay=true; same pattern
    ├── o3de-material-canvas.desktop                   # .desktop entry (Material Canvas) — NoDisplay=true; same pattern
    ├── o3de.metainfo.xml                              # AppStream metainfo — id mutated to org.o3de.O3DE<NNNN> at install
    ├── o3de2605.cdx.json                              # CycloneDX SBOM (one file per major; copy + edit when 26.10 ships)
    ├── make-snapshot-tarball.sh                       # snapshot builder (git clone + git lfs pull + tar; LFS pull is load-bearing)
    ├── o3de-{16,32,48,64,128,256}x*.png               # hicolor app icons (Project Manager — Windows ProjectManager-Icon.ico extract)
    ├── o3de-editor-{16,32,48,64,128,256}x*.png        # hicolor app icons (Editor — Windows o3de_editor.ico extract)
    ├── o3de-material-editor-*.png                     # hicolor app icons (Material Editor — Windows MaterialEditor.ico extract)
    ├── o3de-material-canvas-*.png                     # hicolor app icons (Material Canvas — Windows MaterialCanvas.ico extract)
    ├── 0001-clang21-warning-suppressions.patch        # 13 active patches (0001-0013); see "Patches" section for the table
    ├── 0002-manifest-py-engine-path-detection.patch   #   six carry TIMEBOMB notes (upstream-merged equivalents pending in stab)
    ├── ... (0003 through 0013)                        #   plus 0012-v2-assetbuilder-parent-watchdog.patch (the shipping v2)
    ├── Findmikkelsen-system.cmake                     # Stage 1 + Stage 2 find-shims (copied to cmake/3rdParty/Find<X>.cmake at %prep
    ├── Findexpat-system.cmake                         #   when the matching --with system_<lib> bcond is on):
    ├── FindZLIB-system.cmake                          #   Stage 1: mikkelsen, expat, ZLIB, Freetype, PNG, Lua, lz4, OpenEXR,
    ├── ... (FindFreetype, FindPNG, FindLua,           #     Imath, assimp, libsamplerate, poly2tri, SQLite, GoogleBenchmark,
    ├──      Find{RapidJSON,xxhash,cityhash},          #     RapidJSON (F44/rawhide only -- CS10 EPEL rapidjson too old), xxhash, cityhash
    ├──      Findlz4, FindOpenEXR, FindImath,          #     (no vulkan_validation_layers shim — that swap is runtime-discovered
    ├──      Findassimp, Findlibsamplerate,            #      via VK_LAYER_PATH, no cmake-side find shim)
    ├──      Findpoly2tri, FindSQLite,                 #   Stage 2 library-link: Findmcpp-system.cmake
    ├──      FindGoogleBenchmark)                      #   incl. FindTIFF-system.cmake (system_tiff active on experimental since -102
    ├── FindTIFF-system.cmake                          #     per the 2026-05-05 CryCommon int64 audit; shim kept for future activation)
    ├── Findmcpp-system.cmake                          # Stage 2 library-link find shim
    └── FindGoogleBenchmark-system.cmake               # ACTIVE in stab + experimental chroots since 2026-05-12
```

`rpmbuild` reads sources from `_sourcedir`, so build invocations point both `_sourcedir` and `_specdir` at this checkout — no copying into `~/rpmbuild/SOURCES`.

---

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the source-to-RPM flowchart and the load-bearing design separations (source mode, 3rdParty bundle toggles, system-library swaps, read-only engine + writable user state, multi-channel distribution).

---

## Build a stable release

```bash
# 1. Compute the upstream tarball SHA256 (one-time per release).
#    TAG must match `%global stable_tag` in o3de.spec — currently 2605.0.
TAG=2605.0
curl -fLO "https://github.com/o3de/o3de/releases/download/${TAG}/o3de_${TAG}_lfs.tar.gz"
sha256sum "o3de_${TAG}_lfs.tar.gz"
# Paste the hex into o3de.spec under %global stable_sha256.
mv "o3de_${TAG}_lfs.tar.gz" sources/

# 2. Build.
rpmbuild -bb \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

---

## Build from a git ref (`--with snapshot` mode)

The spec's `--with snapshot` mode builds from any git ref of `o3de/o3de` instead of an upstream-tagged release tarball. **Which COPR project the resulting RPM lands in depends on the git ref**, not on the rpm mode:

- **`stabilization/<release>`** (e.g. `stabilization/26050`, the next-release branch — currently the default `REF`) → `hellaenergy/o3de-stabilization`. Active during the upstream stabilization window (~4 weeks per release cycle); dormant between cycles. Invoke with `make srpm-stabilization` / `make copr-stabilization`.
- **`development`** → `hellaenergy/o3de-development` (auto-refreshed weekly Sunday 06:00 UTC via `.github/workflows/snapshot-development.yml`; the workflow dedups against the last successful build so quiet weeks skip). Manual fires: `make copr-development` locally, or workflow_dispatch from the Actions tab with the optional `force` input to bypass dedup.
- **arbitrary other ref** (e.g. a hypothetical `qt6` migration branch) → dedicated COPR project per branch (`hellaenergy/o3de-qt6` etc.). Build locally with `make srpm-snapshot-ref REF=<other>` and `copr-cli build` directly.

Both paths use `--with snapshot` under the hood; the project split is a publishing-channel choice, not a build-mode choice. See the bullets at the top of this README for the upstream-branch distinction.

```bash
# 1. Generate a reproducible snapshot tarball + checksum.
cd sources
./make-snapshot-tarball.sh stabilization/26050   # next-release branch → o3de-stabilization
# ./make-snapshot-tarball.sh development          # bleeding-edge          → o3de-development
# ./make-snapshot-tarball.sh <commit-sha>         # any specific ref       → dedicated COPR project
cd ..

# 2. Paste the printed snapshot_commit / snapshot_date / snapshot_sha256
#    into the corresponding %global lines in o3de.spec.

# 3. Build.
rpmbuild -bb --with snapshot \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

The resulting version string is `<stable_tag>^<YYYYMMDD>git<shortsha>` (e.g. `2605.0^20260427gitabc1234`). The `^` separator tells `dnf` this is a *pre-release* of the next release, so upgrading from a `--with snapshot` build to the next tagged release works correctly.

---

## Build with O3DE 3rdParty packages bundled

The engine fetches its `LY_3RDPARTY_PATH` packages from O3DE's package server during cmake configure by default. To make the RPM self-contained for an offline target, drop the bundle tarball into `sources/` and pass `--with thirdparty_<name>`.

The spec ships two example toggles (`physx`, `openexr`); add more by:

1. Drop the package tarball in `sources/`, e.g. `physx-5.1.1-rev1-linux.tar.xz`.
2. Add a `%bcond_with thirdparty_<name>` line.
3. Add a matching `Source10x: <filename>` line.
4. Add an extract line in `%prep`:
   ```
   %{?with_thirdparty_<name>:tar -xf %{SOURCE10x} -C %{_builddir}/%{o3de_source_dir}/3rdParty}
   ```

Then build with any subset of toggles:

```bash
rpmbuild -bb --with thirdparty_physx --with thirdparty_openexr \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

The full list of approved package names and revisions lives in O3DE's `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake`.

---

## Build with the debug subpackage

The default build ships only the profile-config binaries (sufficient for end-user game development). To also build debug-config binaries and ship them as the `o3deNNNN-debug` subpackage (e.g. `o3de2605-debug`):

```bash
rpmbuild -bb --with debug ...
```

This roughly doubles build time (debug compiles all the same TUs at `-O0` with full symbols). End users install both with `dnf install o3de2605 o3de2605-debug` to step through engine internals; `o3de2605-debug` requires the same exact NVR of `o3de2605` so they always upgrade in lockstep. Switching the launcher between configs is a runtime concern: `O3DE_BUILD_CONFIG=debug o3de2605`.

---

## Subpackages overview

### Why split

The o3de2605 RPM is split into a small number of subpackages so each install can match the actual workload. Concrete value:

- **Smaller default install.** The post-split main package is ~1.7 GB compressed (down from ~2.2 GB pre-split, roughly 22% smaller). On disk, runtime-only deployments save ~4 GB by skipping the engine static archives. (The default `dnf install o3de2605` still pulls `-devel` via `Recommends:` so project authors get a working build out of the box; runtime-only consumers opt out with `--setopt=install_weak_deps=False`.)
- **Right tool for your use case.** Three orthogonal install dimensions: *runtime* (the main package's binaries; sufficient to launch Project Manager + the Editor), *static-archive link surface for building projects* (`-devel`; auto-recommended), *step-through debuggability of engine internals* (`-debug`). Project authors get the runtime + `-devel` pair by default; engine-internal debuggers add `-debug`; pure runtime-only deployments opt out of `-devel`.
- **CI- and container-friendly.** Game distribution servers shipping pre-built games, CI test containers, and minimal Docker images can skip ~4 GB of compiler-side material. `dnf install --setopt=install_weak_deps=False o3de2605` opts out of even the project-build `*-devel` system Recommends list — the absolute floor for a runtime-only deployment.
- **Aligned with Fedora packaging guidelines.** Fedora's [Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/) require a `-devel` subpackage for any C/C++ package shipping static libraries, and recommend split-by-purpose for large packages. Doing this split proactively (rather than during the Fedora package review) removes one entire class of review friction. Same with the project-build `*-devel` Recommends pattern (clang, mesa-libGL[U]-devel, libxcb-devel, the xcb-util-*-devel suite (xcb-util-devel, xcb-util-image-devel, xcb-util-keysyms-devel, xcb-util-renderutil-devel, xcb-util-wm-devel), libxkbcommon-devel, libxkbcommon-x11-devel, fontconfig-devel, libcurl-devel, pcre2-devel, openssl-devel, libunwind-devel, libzstd-devel, zlib-devel, vim-common, plus per-active Stage 1 swap like mikkelsen-devel) — testers get a working build experience by default; minimal users opt out.
- **Forward-compatible with multi-major.** When `o3de2605-devel` and `o3de2610-devel` both exist someday, they're independent — install the devel surface only for the major you actually develop against, not all of them.

### What's in each package

The main RPM ships alongside up to two optional subpackages:

| Package | Contents | When to install |
|---|---|---|
| `o3de2605` (main) | Engine binaries (`bin/Linux/profile/Default/`), runtime cmake config + per-target import files, headers, gem sources, scripts, Templates, Editor assets, Python bootstrap, SBOM. **Recommends `o3de2605-devel`** so dnf pulls it in by default. | Always. The runtime + the materials needed to launch the Editor and Project Manager. |
| `o3de2605-devel` | Static archives (`lib/Linux/profile/Default/*.a` + `lib64/`), about 178 `.a` files totalling ~4 GB. Includes `libAzGameFramework.a`, `libAzCore` static surfaces, `libAtomCore.a`, `libAssetBuilderSDK.a`, and the rest of the engine's `.a` link surface. | Always for project authors. **Project Manager's "Build" workflow links any GameLauncher / ServerLauncher / HeadlessServerLauncher target against these archives**; without `-devel` the cmake `--build` step fails at ninja with `libAzGameFramework.a, needed by ..., missing`. The only case for skipping `-devel` is a pure runtime-only deployment (e.g., headless server host running pre-built binaries from elsewhere) which is rare. |
| `o3de2605-debug` | Debug-config binaries (`bin/Linux/debug/`) + matching static archives (`lib/Linux/debug/`). Full debug symbols, `-O0`. | Add when you need to step through engine code in a debugger. Set `O3DE_BUILD_CONFIG=debug` to launch the debug build. |

`dnf install o3de2605` (default) pulls in `o3de2605-devel` automatically via the main package's `Recommends:`. If you want to override this and install runtime-only, pass `--setopt=install_weak_deps=False`. The project-build `*-devel` system packages (clang, mesa-libGL[U]-devel, libxcb-devel, the xcb-util-*-devel suite (xcb-util-devel, xcb-util-image-devel, xcb-util-keysyms-devel, xcb-util-renderutil-devel, xcb-util-wm-devel), libxkbcommon-devel, libxkbcommon-x11-devel, fontconfig-devel, libcurl-devel, pcre2-devel, openssl-devel, libunwind-devel, libzstd-devel, zlib-devel, vim-common, plus the `*-devel` for any active Stage 1 system-library swap like mikkelsen-devel) are pulled in via the same `Recommends:` list; installed by default unless you pass `--setopt=install_weak_deps=False`.

---

## Using the installed RPM

Each major release ships as its own versioned package (`o3de2605`, `o3de2610`, …) so multiple O3DE versions can coexist. Two PATH-installed entry points per package — the examples below use 26.05.0 (`o3de2605`):

| Command | Purpose |
|---|---|
| `o3de2605` | Launches the GUI (Project Manager by default). Set `O3DE_BUILD_CONFIG=debug` for the debug-config engine if `o3de2605-debug` is also installed. |
| `o3de2605-cli` | Forwards to the upstream Python CLI at `/opt/O3DE/26.05.0/scripts/o3de.sh` for project / gem / engine management. |

The CLI covers ~25 sub-commands. Common ones:

```bash
o3de2605-cli --help                                # list sub-commands
o3de2605-cli register --this-engine                # one-time per-user setup (also runs from %post)
o3de2605-cli get-registered -df engines            # list registered engines (or projects/gems/templates)
o3de2605-cli create-project --project-path ~/MyGame --project-name MyGame
o3de2605-cli create-gem    --gem-path ~/MyGem --gem-name MyGem
o3de2605-cli enable-gem    --project-path ~/MyGame --gem-name Atom
o3de2605-cli edit-engine-properties --display-name "My Engine"
o3de2605-cli export-project   --project-path ~/MyGame   # bundle a runtime build
o3de2605-cli sha256 <file>                             # compute the hash O3DE expects in package manifests
```

State written by either command lives under `~/.o3de/` (engine registration manifest, per-user Python venvs keyed by engine path, project user data). The engine root at `/opt/O3DE/26.05.0/` is read-only.

The first launch of `o3de2605` (or first run of `o3de2605-cli`) bootstraps the per-user Python venv automatically — see `python/get_python.sh` in the engine root if you want to pre-bootstrap or inspect.

### Multiple O3DE versions on one machine

The `/opt/O3DE/<version>/` install layout matches upstream's `.deb` and Windows `.msi` exactly, so cross-platform users see the same path mental model on Fedora, Debian/Ubuntu, and Windows. dnf treats each major as an independent package:

```bash
sudo dnf install o3de2605 o3de2610            # both installed side-by-side
o3de2605                                      # launches 26.05.0 Project Manager
o3de2610                                      # launches 26.10.0 Project Manager
ls /opt/O3DE/                                 # 26.05.0  26.10.0
```

**On the manifest:** all installed o3deNNNN majors share `engine_name: "o3de"` in their `engine.json` (matching upstream's `.deb`, ensuring third-party gem `compatible_engines` checks resolve correctly). The user's `~/.o3de/o3de_manifest.json` keys engine registrations by name, so only ONE `o3de` engine is registered at a time. Switching the active engine between majors is a one-command operation:

```bash
# from inside the desired install root, register that engine as the active "o3de"
/opt/O3DE/26.10.0/scripts/o3de.sh register --this-engine    # to switch to 26.10
/opt/O3DE/26.05.0/scripts/o3de.sh register --this-engine    # to switch to 26.05
```

This matches upstream's multi-install UX. Files for both majors stay co-installed; only the active registration is single-slot. Project Manager from either launcher (`o3de2605` or `o3de2610`) routes to whichever engine is currently registered.

Project Manager auto-routes a project to the right engine via the project's `engine:` field in `project.json`. Subpackages follow the same versioning — `o3de2605-debug` and `o3de2610-debug` are independent and co-installable. Cross-major dnf upgrades are intentionally NOT automatic: different majors are different engine lines and you opt in explicitly with `dnf install o3de2610` when ready.

### Gems with system runtime dependencies

This RPM ships the engine plus the ~117 gems sourced from the `o3de/o3de` repository. Additional gems live in [`o3de/o3de-extras`](https://github.com/o3de/o3de-extras) and are discovered automatically by Project Manager via a default-registered remote gem repository — they appear in the gem catalog with a download-cloud icon and fetch on demand into `~/.o3de/gems/<gem-name>/` when you click "Download Gem". Some of those remote gems require external runtime libraries the engine RPM does NOT bundle (most notably the ROS 2 family, AudioEngineWwise, OpenXRVk). See [`docs/GEMS_WITH_SYSTEM_DEPS.md`](docs/GEMS_WITH_SYSTEM_DEPS.md) for which gems need what, install paths for each runtime on Fedora 44+ / CentOS Stream 10+, and the project-build workflow.

---

## Distribution

The o3de RPM has three distribution targets, in order of how soon each is reachable. The first (COPR) is itself a multi-channel layout (six projects) with a clear promotion flow described below.

### 1. COPR — `hellaenergy/o3de*` (today, ongoing)

The interim distribution channel. Five engine COPR projects (plus two debug-config siblings and a dependencies project), each with a distinct purpose:

- **[`hellaenergy/o3de-dependencies`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-dependencies/)**. Fedora-clean SRPMs for O3DE 3rdParty packages that aren't in Fedora proper (custom Qt 5.15-rev9, PhysX, AWSNativeSDK, azslc, mikkelsen, the Stage 2 rebuilds o3de2605-dxc-spirv / o3de2605-spirv-cross / o3de2605-mcpp-az / o3de2605-cityhash, ...). `enable_net=false`. Built first; consumed by the engine projects via `additional_repos` at build time and `runtime_dependencies` at consume time (so users get it auto-enabled when they enable any engine project).
- **[`hellaenergy/o3de`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/)**. stable channel. Tracks `o3de/o3de:main` (the upstream release branch where tagged releases land: `2510.2`, `2605.0`, etc.). End users on Fedora should `dnf copr enable` this for a stable, supportable install. See [`POST_RELEASE.md`](POST_RELEASE.md) for the post-release-ceremony runbook.
- **[`hellaenergy/o3de-testing`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-testing/)**. pre-promotion soak channel for stable. Same engine source tag as stable, with packaging-side bug fixes and minor enhancements that are queued for promotion to `hellaenergy/o3de`. Mirrors Fedora's `updates-testing` semantics: enable this channel if you want to validate the next set of packaging fixes a couple of days before they reach the broader stable channel. Promotion flow: `main HEAD -> testing (~48h soak) -> stable`. Pick ONE of `o3de` or `o3de-testing` to enable; enabling both is technically possible but `dnf` will always install the higher NVR (testing's) which defeats the purpose of stable.
- **[`hellaenergy/o3de-stabilization`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/)**. pre-release validation builds from upstream's `stabilization/<release>` branch. Active during the 4-week pre-release window when an upstream release is being stabilized (e.g., `stabilization/26050` was active April-May 2026). Dormant between release cycles (post-2605.0 / pre-`stabilization/26100`). The community testers' channel during active windows.
- **[`hellaenergy/o3de-development`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-development/)**. ad-hoc cadence builds from upstream's `development` branch (bleeding-edge engine). For arbitrary other engine refs (e.g. a hypothetical `qt6` migration channel) we'd create a dedicated COPR project per branch rather than overload this one.
- **[`hellaenergy/o3de-experimental`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-experimental/)**. packagers' migration-work channel. In-flight spec changes (new `system_<X>` swap candidates, COPR-rebuilt dep PoCs, structural spec rework) validate here before promotion to stabilization (during a stabilization window) or directly to testing (post-release). Distinguished by the `-experimental.<commit>` channel marker. Not for end-user testing; internal to the packaging effort.
- **[`hellaenergy/o3de-testing-debug`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-testing-debug/)** and **[`hellaenergy/o3de-development-debug`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-development-debug/)**. debug-config siblings of `o3de-testing` and `o3de-development`. Each builds the identical NVR as its namesake plus the `o3de2605-debug` subpackage (the `--with debug` engine config: `-O0` + full debug symbols), so a tester who hits a crash can `dnf install o3de2605-debug` and report a real stack trace instead of a profile build silently closing. Enable alongside the namesake channel (the `-debug` subpackage hard-requires the matching main package's exact NVR, so the two projects are refreshed in lockstep from the same SRPM). AppStream is off so the debug repo's copy of the main package doesn't show as a duplicate app in GNOME Software. `make copr-testing-debug` / `make copr-development-debug` refresh them.

All three engine projects use `enable_net=true` so cmake can still fetch the remaining bundles from `packages.o3de.org`. The licensing-restricted set is now two packages (NvCloth's NVIDIA license, squish-ccr's BC7 patent encumbrance); DXC retired from this set on 2026-05-08 when `o3de2605-dxc-spirv` shipped as a license-clean rebuild in `o3de-dependencies`. `poly2tri` was a fourth restricted entry until the 2026-05-07 audit reframed it as a Stage 1 swap candidate; it now resolves through Fedora's `poly2tri-devel` when the swap is active.

### 2. o3debinaries.org (eventual upstream)

The official O3DE binary distribution. The eventual goal is to upstream this spec into the O3DE source tree (likely under `cmake/Platform/Linux/Packaging/`) so O3DE's own CI can build the RPM and host it at o3debinaries.org alongside the .deb / snap / Windows packages. This reaches a much larger audience than COPR.

What needs to happen: align the spec with O3DE's existing packaging conventions, drop `hellaenergy/`-specific assumptions (the spec itself stays distribution-agnostic; `Makefile` targets stay local), get the spec accepted by O3DE upstream's release engineering team. Most of the prep work for Fedora inclusion carries over directly: system-lib migration (Stage 1), license-clean DXC rebuild (shipped 2026-05-08 as `o3de2605-dxc-spirv`).

### 3. Fedora repo proper (long-term)

See [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) for the staged plan. Six stages from system-lib migration through OpenSSL 3.x port, debuginfo subpackages, and Bundling Library Exception filings (current set: Qt 5.15-rev9, squish-ccr, NvCloth; DXC retired 2026-05-28 after the license-clean rebuild shipped; libtiff retired 2026-06-05 when Patch0016's TIFF_DISABLE_DEPRECATED unblocked the system_tiff swap) before the package review submission.

### Other Fedora-derivative downstreams (option-value)

The spec is RPM / DNF / mock-conformant with no Fedora-edition-specific assumptions, so it should build on any Fedora-derivative that consumes Fedora sources via the standard packaging pipeline. We don't currently target any beyond the three covered above (F44, rawhide, CS10), and we won't pre-emptively add chroots, but if a downstream community (e.g. the [Fedora Hummingbird SIG](https://fedoraproject.org/wiki/Hummingbird) targeting cloud-native builders, or any other RPM-based derivative) signals a felt need for an O3DE-on-X variant, the spec is ready to be a starting point. Likely-narrow shapes for those follow-ons: headless server-launcher containers, or asset-bake CI images that ship `o3de2605` without the Editor/UI subset. The wider Editor + GUI workload is a poor fit for distroless / minimal-image targets.

To consume (end users):

```bash
# Pick ONE channel. Don't enable multiple at the same time.
#
#   hellaenergy/o3de              stable. Most users want this. Tracks
#                                 upstream tagged releases (26.05.0,
#                                 26.05.1, ...) and post-soak promotions
#                                 from o3de-testing.
#
#   hellaenergy/o3de-testing      pre-promotion soak for stable. Same
#                                 engine source tag, slightly newer
#                                 packaging fixes queued for stable.
#                                 ~48h soak window. Enable this if you
#                                 want to validate packaging fixes a
#                                 couple of days before they reach
#                                 stable users; report regressions if
#                                 you hit any.
#
#   hellaenergy/o3de-stabilization
#                                 pre-release engine validation, active
#                                 during the 4-week upstream stabilization
#                                 window per release cycle. Dormant
#                                 between cycles. Enable only when an
#                                 upstream stabilization branch is
#                                 active and you want to validate the
#                                 NEXT release candidate.
sudo dnf copr enable hellaenergy/o3de                  # change to o3de-testing if you want pre-stable soak
sudo dnf install o3de2605                              # ~2 GB main + ~4 GB -devel (auto-pulled via Recommends);
                                                       # pass --setopt=install_weak_deps=False to skip -devel
                                                       # for runtime-only deployments.
o3de2605                                               # launch Project Manager (GUI)
o3de2605-cli --help                                    # CLI for project / gem / engine management
```

The package name follows a `o3deNNNN` convention (postgresql-style): `NNNN` is the upstream major as `YYMM` (`2605` for 26.05.x, `2610` for the next major). The install path under `/opt/O3DE/<DISPLAY_VERSION>/` matches what the upstream `.deb` and Windows `.msi` installers ship — same path mental model across distros and OSes.

`hellaenergy/o3de-dependencies` auto-enables alongside the engine project (via the engine project's `runtime_dependencies` setting) — no separate `dnf copr enable` needed. The per-user Python venv bootstraps on first launch automatically; pre-bootstrap manually with `/opt/O3DE/26.05.0/python/get_python.sh` if preferred.

When O3DE upstream tags a stable release, swap `o3de-stabilization` for `o3de` (the package name stays `o3de2605`; only the COPR project changes). Skip `o3de-development` (dev-branch builds) and `o3de-experimental` (packaging work) unless you have a specific reason to test those.

To publish from this checkout:

```bash
make snapshot REF=stabilization/26050    # generate tarball + print pin values
$EDITOR o3de.spec                        # paste the printed snapshot_* macros
make copr-stabilization                  # SRPM → hellaenergy/o3de-stabilization (testers)
make copr-stabilization-and-test         # same + watch build + fire CI tests on success
make copr-development                    # SRPM → hellaenergy/o3de-development (always dev-branch tip)
make copr-development-and-test           # same + watch + fire CI tests
make copr-experimental                   # SRPM → hellaenergy/o3de-experimental (Stage 1 batch)
make copr-experimental-and-test          # same + watch + fire CI tests
make copr-stable                         # SRPM → hellaenergy/o3de (when tagged)
make trigger-tests BUILD_ID=N            # fire CI tests against an existing COPR build
```

A `make copr-init` target prints the one-time setup commands for all the COPR projects (chroot configs, runtime-repo-dependency, `--rpmbuild-with` flags for active Stage 1 migrations). Run `make help` for the full target list.

CI (`.github/workflows/lint.yml`) runs spec-parse (stable + snapshot + stabilization + experimental modes) + rpmlint + desktop-file-validate + appstream-util validate + shell-syntax checks on every push, against a Fedora 44 container. CI (`.github/workflows/test-installed.yml`) runs the integration test suite (Tiers 1–6) against an existing COPR RPM URL in clean F44 + rawhide containers — triggered manually, by `make trigger-tests`, or by a 4-hourly cron polling `o3de-stabilization` for new builds. The full RPM build itself is too heavy for free runners (>2 hours, 14 GB output) — the COPR projects do that.

The longer-term goal is **inclusion in Fedora proper**. The roadmap lives in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) and the per-bundle Fedora-readiness status in [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md).

---

## Testing

A tiered post-install test suite lives in [`tests/`](tests/). It exists for three audiences:

- **This repo's maintainer** — catch regressions between spec changes
- **O3DE engine contributors** — validate that your branch builds and runs as a Fedora RPM before merging
- **O3DE release engineering** — gate releases on "does this work as a packaged engine on Fedora?"

The same suite serves all three. Differences are only in *which* git ref produced the RPM under test.

### Run the suite against an installed RPM

```bash
sudo dnf install -y ./o3de2605-*.rpm                  # or whichever o3deNNNN.rpm

# Quick pass (rpm-level + install integrity + engine smoke, no state changes)
make test

# Add per-user setup (downloads the bundled-Python venv, registers the engine)
make test-setup

# Full end-to-end (also creates a project + cmake-configures it)
make test-full

# UI smoke — Project Manager launches under Xvfb without crashing
sudo dnf install -y xorg-x11-server-Xvfb scrot xorg-x11-utils
make test-ui

# UI smoke + Editor scripted automation
make test-ui-full
```

Tier 6 (UI) uses Xvfb (virtual display) and Mesa lavapipe (software Vulkan in CI containers; real GPU on user workstations). Tier 11 (post-load liveness — launcher survives N seconds after level load without crash/freeze, catches "level loaded but engine froze immediately" failures Tier 9/10 can't detect) was implemented 2026-05-22; invoke via `make test-tier11` (default project NewspaperDeliveryGame) or `make test-tier11-multiplayer`. Tier 12 (render correctness — Vulkan render vs reference image; needs GPU-equipped runners) and Tier 13 (visual regression — screenshots → pixel-diff against per-Fedora-version baselines) are documented as future work in `tests/README.md`.

### Run a real game end-to-end

Two community O3DE samples are wired up as end-to-end tests on Fedora:

```bash
make test-multiplayer-sample    # Tier 9: o3de-multiplayersample
make test-newspaper-delivery    # Tier 10: NewspaperDeliveryGame (Paper_Kid)
```

**NewspaperDeliveryGame is fully playable** on Fedora 44 against the installed `o3de2605` RPM as of 2026-05-21 (title screen, character control, score / lives / home-time HUD, the neighborhood with houses + delivery truck + props all render and run cleanly).

**MultiplayerSample is playable on Linux** against the installed `o3de2605` RPM as of 2026-05-22: launcher loads `startmenu`, MULTIPLAYER SAMPLE title screen renders with the cyberpunk UI, network stack initializes, and (with `make play-mps-host` + `make play-mps-client`) a full host+connect session over loopback runs the actual NewStarbase gameplay. For Tier 9 to find AssetProcessor's BehaviorContext for scriptcanvas baking, build BOTH `MultiplayerSample.GameLauncher` and the bare `MultiplayerSample` target (the test script does this automatically; the upstream README at line 200+ now documents the requirement for manual builds via [PR #502](https://github.com/o3de/o3de-multiplayersample/pull/502)).

The test scripts auto-recover from common upstream-side issues (LFS server transients, working-tree pointer files, AWS Lambda batch-size limits, level startup overrides), so a clean clone + RPM install exercises the build and bake path without manual intervention. Wall time: Tier 9 ~60-90 min cold-cache (full C++ build + asset bake), ~3-10 min warm. Tier 10 ~30-60 min cold, ~3-10 min warm.

After running, launch the working sample directly:

```bash
# Paper_Kid: Newspaper Delivery Game (single-player, plays clean)
/opt/O3DE/26.05.0/bin/Linux/profile/Default/O3DE.GameLauncher \
  --project-path=$HOME/PROJECTS/NewspaperDeliveryGame \
  --engine-path=/opt/O3DE/26.05.0 \
  --regset="/O3DE/Autoexec/ConsoleCommands/LoadLevel=Neighborhood" \
  --regset="/O3DE/Autoexec/ConsoleCommands/bg_ConnectToAssetProcessor=0"

# MultiplayerSample client only (loads startmenu; for full host+join, use 'make play-mps-host' below)
$HOME/PROJECTS/o3de-multiplayersample/build/linux/bin/profile/MultiplayerSample.GameLauncher \
  --project-path=$HOME/PROJECTS/o3de-multiplayersample \
  --regset="/O3DE/Autoexec/ConsoleCommands/bg_ConnectToAssetProcessor=0"
```

### Run a MultiplayerSample multiplayer session locally

`make test-multiplayer-sample` (Tier 9) builds the full multiplayer harness: client + headless server + spectator-mode server + the bare gem AssetProcessor needs. After it completes, you can host + join a session on a single machine via three make targets:

```bash
make play-mps-host    # starts the headless server (NewStarbase, listens on UDP 33450)
make play-mps-client  # starts the windowed client (auto-connects to loopback)
make play-mps-stop    # kills all MPS launcher processes
```

The targets check for the binaries being built and bail with a helpful error if Tier 9 hasn't run yet. Variables `MPSAMPLE_PLAY_DIR` and `MPSAMPLE_ENGINE` let you override the project clone location or engine install path.

Behind the scenes the targets use `MultiplayerSample.HeadlessServerLauncher` (no GUI) + `MultiplayerSample.GameLauncher` with `r_fullscreen=0`. This is the configuration that's stable for sustained play; see [`FOLLOW_UPS.md`](FOLLOW_UPS.md) for the diagnosis of why the graphical `ServerLauncher` variant + client + in-game settings menu hit a dual-respawn crash. For dev/debug needing a server-side spectator view, run `MultiplayerSample.ServerLauncher` directly (built by Tier 9 alongside the other binaries) but don't touch the client's settings menu while it's up.

The project ships two console-command files at its root that drive the launch:

- `launch_server.cfg` -- loads `Levels/NewStarbase/NewStarbase.spawnable` and enables multithreaded connection updates
- `launch_client.cfg` -- issues `connect` with no IP, which defaults to loopback `127.0.0.1`

The launchers can also be invoked directly with explicit flags if you want a different config (different level, remote server IP, etc.). See [`Makefile`](Makefile) `play-mps-*` targets for the canonical command shape.

### Validate an arbitrary O3DE git ref end-to-end

For O3DE engine contributors who want to know "does my branch work as a Fedora RPM":

```bash
git clone https://github.com/nickschuetz/o3de-rpm
cd o3de-rpm
make test-branch REF=stabilization/26050   # or any git ref / release tag
```

This builds the snapshot tarball, patches the spec with the right pin values, runs `rpmbuild`, installs the resulting RPM, then runs the full test suite. Plan ~30-40 minutes for the build on a 32 GB workstation (Stage 1 + Stage 2 swaps now remove 17 bundled-3p compiles from the engine build: 14 Stage 1 system swaps + 3 Stage 2 swaps), plus ~10 minutes for install + test. ~70 GB free disk space required for the build tree + cached packages.

### CI for community use

`.github/workflows/test-installed.yml` runs the test suite in clean Fedora containers (matrix: `fedora-44`, `fedora-rawhide`, extending to `fedora-45+` as releases ship) against an RPM URL — typically a COPR build artifact. Trigger via GitHub UI with an `rpm_url` input. The CentOS Stream 10 chroot is exercised per-build on COPR (its own `centos-stream-10-x86_64` build of every SRPM) but not currently in the GH-Actions matrix; CS10 builds going green on COPR is the gate for that chroot.

For automated COPR → CI integration, configure a COPR webhook to fire this workflow on every successful build, giving any branch a "healthy on Fedora" signal.

See [`tests/README.md`](tests/README.md) for the full tier breakdown and contribution guide.

---

## Security posture

| Concern | Mitigation |
|---|---|
| Tampered upstream tarball | `%prep` verifies `Source0` against `%global stable_sha256` (or `snapshot_sha256`) with `sha256sum -c` before extraction. |
| Tampered snapshot | `make-snapshot-tarball.sh` is reproducible (sorted, fixed mtime, numeric owner) — re-running for the same commit produces a byte-identical tarball. The committed sha256 is the binding root of trust. |
| World-writable files under `/usr` | Removed. `/opt/O3DE/<version>/` is fully read-only after install; all writable state is per-user under `~/.o3de/`. |
| Network during build | LFS objects are bundled into the source tarball before build; no `git lfs pull` runs in `%build`. O3DE's own `LY_PACKAGE_SERVER_URLS` 3rdParty fetcher still runs at cmake configure unless every needed package is pre-bundled — see "3rdParty packages" above. |
| **⚠ Bundled OpenSSL 1.1.1t (EOL since 2023-09-11)** | Not our packaging defect — upstream O3DE pins it. Tracked as a hard blocker for Fedora inclusion in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) (stage 4). Surfaced here so consumers see it clearly. |
| Hardening flags (RELRO / BIND_NOW / stack-protector / `_FORTIFY_SOURCE`) | Restored explicitly via `CMAKE_*_LINKER_FLAGS_INIT` after unsetting Fedora's CFLAGS/CXXFLAGS/LDFLAGS bundle (the bundle's annobin specs file breaks clang feature tests). O3DE's `Configurations_clang.cmake` already supplies stack-protector and `_FORTIFY_SOURCE`. |
| Runtime escalation paths | Launcher wrapper is `/usr/bin/o3deNNNN` and CLI wrapper is `/usr/bin/o3deNNNN-cli`, both mode 0755, no setuid. All `mkdir -p` targets are under `$HOME`. |
| Patch reviewability | Real `.patch` files with `From:`/`Subject:` rationales — reviewable with `git log` or `interdiff`. |
| Source provenance auditability | CycloneDX 1.6 SBOM at `/usr/share/o3deNNNN/sbom/o3deNNNN.cdx.json` documents every bundled component, with purl, license expression, and EOL flags where applicable. |
| First-run state migration | Launcher's `<project>/user/project.json` rewrite is JSON-aware (`python3 -c json.load/dump`), only mutates known legacy prefixes, and is gated by a per-prefix marker file. Failures are silenced so a malformed home dir can't block the editor. |

---

## SBOM

A static CycloneDX 1.6 JSON SBOM is committed at `sources/o3de2605.cdx.json` (one file per major; `o3de2610.cdx.json` etc. ship alongside as future majors land) and installed at `/usr/share/o3deNNNN/sbom/o3deNNNN.cdx.json`. It documents:

- The package itself (`pkg:rpm/fedora/o3deNNNN@<version>-<release>`) with its license expression and source URLs.
- Build dependencies (cmake, ninja-build, gcc-c++, python3-devel, git-lfs).
- Direct runtime dependencies (Qt5, Vulkan, mesa, libcurl, openssl, …).
- Bundled components currently itemized in the SBOM JSON: custom Qt 5.15-rev9 (with the Fedora Bundling Library Exception flag), embedded clang toolchain, bundled Python 3.10, bundled OpenSSL 1.1.1t, and googletest (test-scaffolding fetch). Smaller bundled 3rdParty (pyside2/shiboken2, OpenEXR, OpenImageIO, OpenColorIO, PhysX, etc.) are NOT individually itemized today — adding them is tracked as SBOM completeness work in `FEDORA_ROADMAP.md`.
- **EOL flags** for bundled OpenSSL 1.1.1t.

To consume:

```bash
# After install (replace 2605 with whichever major is installed):
cyclonedx validate --input-file /usr/share/o3de2605/sbom/o3de2605.cdx.json

# Generate a runtime augmentation from the actual built RPM:
syft /opt/O3DE/26.05.0 -o cyclonedx-json
```

Re-generate the static SBOM when bumping the version: edit `sources/o3deNNNN.cdx.json` (or copy it to `sources/o3deMMMM.cdx.json` for a new major) to update `metadata.component.version`, the `version` field at the top level, the `name`/`purl`/`bom-ref` fields, and any external references.

---

## Patches

Sixteen patches declared (the applied set varies by bcond: 0014/0015 are swap_hook-only, 0016 is system_tiff-only). **Six carry TIMEBOMB notes** -- upstream-equivalents merged to `development` but NOT to `stabilization/26050` (our snapshot source branch); they retire when stabilization absorbs the changes: Patch0001 (clang21, [#19748](https://github.com/o3de/o3de/pull/19748) merged 2026-05-14), Patch0002 (manifest.py env var, [#19751](https://github.com/o3de/o3de/pull/19751) merged 2026-05-14), Patch0005 (AzQtComponents title, [#19750](https://github.com/o3de/o3de/pull/19750) merged 2026-05-14), Patch0007 (libtiff C99, [#19734](https://github.com/o3de/o3de/pull/19734) merged 2026-05-08), Patch0008 (AzCore lobject include, [#19733](https://github.com/o3de/o3de/pull/19733) merged 2026-05-08), Patch0012 v2 (AssetBuilder watchdog, [#19747](https://github.com/o3de/o3de/pull/19747) merged 2026-05-15). The `--with development_snapshot` bcond (2026-05-18) gates these six off so dev-branch-tip builds (`make copr-development`) succeed without patch-apply rejects; default OFF so stabilization / development / experimental channels apply all thirteen as before. Patch0013 v4 gates the vulkan-validationlayers Stage 1 swap (three-hunk: cmake gate + PAL_linux variable + Instance.cpp env-var fix), validated end-to-end on build 10457745 (2026-05-13/14). See [`CONTRIBUTING.md`](CONTRIBUTING.md#patches) for the full table including each patch's upstream-worthy assessment. Quick summary:

| # | Target | Purpose |
|---|---|---|
| 0001 | `cmake/Platform/Common/Clang/Configurations_clang.cmake` | Suppress clang 21+ `-Werror` failures. **TIMEBOMB:** [#19748](https://github.com/o3de/o3de/pull/19748) merged to `development` 2026-05-14 (release-cherry-pick candidate per nick-l-o3de). |
| 0002 | `scripts/o3de/o3de/manifest.py` | Honor `O3DE_ENGINE_PATH` for engine-root detection. **TIMEBOMB:** [#19751](https://github.com/o3de/o3de/pull/19751) merged to `development` 2026-05-14. |
| 0003 | `python/get_python.sh` | Per-user venv linkage + engine-id reconciliation |
| 0004 | `cmake/LYPython.cmake` | Non-editable pip install for read-only engine roots |
| 0005 | `Code/Framework/AzQtComponents/.../WindowDecorationWrapper.cpp` | Propagate guest title to WM-drawn titlebar in `OptionDisabled` mode. **TIMEBOMB:** [#19750](https://github.com/o3de/o3de/pull/19750) merged to `development` 2026-05-14. |
| 0006 | `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` | Establish the `LY_USE_SYSTEM_<X>` gating convention used by Stage 1 system-library swaps |
| 0007 | `.../TIFFLoader.cpp` + `Code/Editor/Util/ImageTIF.cpp` | Migrate legacy libtiff `uint8`/`uint16`/`uint32` typedefs to standard C99 (libtiff 4.5+ deprecates the legacy names). **TIMEBOMB:** upstream merged [#19734](https://github.com/o3de/o3de/pull/19734) into `development` on 2026-05-08 but not into `stabilization/26050`; retires when stabilization absorbs the change. |
| 0008 | `Code/Framework/AzCore/.../ScriptContext.cpp` | Drop the redundant `<lua/lobject.h>` include broken by Lua 5.5 layout changes. **TIMEBOMB:** upstream merged [#19733](https://github.com/o3de/o3de/pull/19733) into `development` on 2026-05-08 but not into `stabilization/26050`; retires when stabilization absorbs the change. |
| 0009 | `Gems/PhysX/.../physx-pal-platform.cmake` | Gate the upstream `poly2tri` association on the `system_poly2tri` swap |
| 0010 | `Code/Framework/AzCore/Script/ScriptContext.cpp` | Add a Lua 5.5 `lua_newstate` signature shim (warnflag arg added in 5.5) |
| 0011 | `Code/Tools/LuaIDE/.../WatchesPanel.cpp` | Restore `LUA_NUMTAGS` macro for the LuaIDE compile path under Lua 5.5 |
| 0012 | `Code/Tools/AssetProcessor/AssetBuilder/main.cpp` | Child-side parent-death watchdog. AssetBuilder polls `getppid()` every 2s; when reparented (AP died), `_exit(0)`. Replaces a withdrawn v1 attempt that used `m_tetherLifetime`/`prctl(PR_SET_PDEATHSIG)` -- that approach broke because the kernel binds PDEATHSIG to the forking thread, not the parent process, and AP forks from short-lived TaskWorker threads. v1 patch file retained in `sources/0012-assetprocessor-tether-resident-builders.patch` as reference; v2 is what ships. **TIMEBOMB:** [#19747](https://github.com/o3de/o3de/pull/19747) merged to `development` 2026-05-15. |
| 0013 | `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` + `Gems/Atom/RHI/Vulkan/Code/Source/Platform/Linux/PAL_linux.cmake` + `Gems/Atom/RHI/Vulkan/Code/Source/RHI/Instance.cpp` | Three-hunk gate for the `system_vulkan_validation_layers` Stage 1 swap. Skips the bundled `ly_associate_package`, leaves `VULKAN_VALIDATION_LAYER` unset (so `${VULKAN_VALIDATION_LAYER}` in the gem's BUILD_DEPENDENCIES expands to nothing), and flips the `VK_LAYER_PATH` SetEnv overwrite flag from 1 to 0 so distro/Flatpak launchers pre-setting `VK_LAYER_PATH=/usr/share/vulkan/explicit_layer.d` win over the engine's exeDirectory default. v1-v3 were partial; v4 added the PAL_linux variable gate after cmake configure failed at `find_package(vulkan-validationlayers)`. |
| 0014 | `cmake/3rdPartyPackages.cmake` | swap_hook prototype: central `LY_USE_SYSTEM_<NAME>` guard in `ly_download_associated_package()`, replaces Patch0006's per-line gating when enabled. Proposed upstream as [#19815](https://github.com/o3de/o3de/issues/19815). |
| 0015 | vulkan PAL_linux + Instance.cpp | swap_hook companion: Patch0013's runtime hunks minus the BuiltInPackages gate (unnecessary under the lazy model). |
| 0016 | the three `<tiffio.h>` consumer TUs | `TIFF_DISABLE_DEPRECATED` before the include: removes the libtiff legacy-typedef collision with CryCommon that parked system_tiff since -17. Validated 2026-06-05 (3 chroots + Tier 2 swap-health). |

Each patch carries a `From:`/`Subject:` header with the rationale. Stage 1 system-library swaps additionally ship companion `Find<X>-system.cmake` shims in `sources/` (`Findmikkelsen-system.cmake`, `Findexpat-system.cmake`, `FindZLIB-system.cmake`, etc.) — installed into `cmake/3rdParty/Find<X>.cmake` during `%prep` when the matching `--with system_<lib>` is enabled.

---

## Known limitations

- O3DE's 3rdParty package fetcher still runs at cmake configure unless every package is pre-bundled. Fully hermetic offline builds (mock without `--enable-net`) require staging every package the engine pulls — see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md).
- Two upstream-bundled packages (`NvCloth`, `squish-ccr`) cannot be hosted in Fedora or COPR for licensing reasons (NVIDIA license; BC7 patent encumbrance). The Fedora-shippable variant routes around them via feature-gated builds; see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) § "Restricted bundles". `DirectXShaderCompilerDxc` was a third entry until 2026-05-08, when the license-clean `o3de2605-dxc-spirv` rebuild shipped in `hellaenergy/o3de-dependencies` and replaced the bundle via the `system_dxc` swap. `poly2tri` was a fourth entry until the 2026-05-07 audit reframed it as a Stage 1 swap; it now resolves via Fedora's `poly2tri-devel`.
- Bundled OpenSSL 1.1.1t is end-of-life. Tracked for migration to system OpenSSL 3.x in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) (stage 4); likely upstream-blocked.
- `debuginfo` / `debugsource` subpackages are suppressed (`%global debug_package %{nil}`). Debug symbols are present in the binaries but not extracted into a separate package. Unblocking this is on the Fedora roadmap (stage 5).
- The Editor stalls at viewport creation under VirtualBox + software 3D + lavapipe Vulkan. Engine inits its RHI against `llvmpipe`, then hangs when creating the Editor's render viewport. `QT_QPA_PLATFORM=xcb` does not help — the engine forces XCB anyway. No known workaround; affects anyone running O3DE in a VM without GPU passthrough. Bare-metal Linux + native GPU + `vulkan-loader` is unaffected.
- **Bundled Qt 5.15-rev9 has no Wayland platform plugin.** `QT_QPA_PLATFORM=wayland` fails with `Could not find the Qt platform plugin 'wayland'`; only `xcb`, `offscreen`, and `minimal` are present in the bundle's `plugins/platforms/`. System `qt5-qtwayland` does not help because the bundled Qt is isolated from system Qt plugins (the engine bundles its own Qt 5.15 with custom O3DE patches; system Qt 5 is not a substitute for this engine version). GNOME / KDE Wayland users get XCB via XWayland, which works for the Editor and Project Manager. Will be resolved by the Qt 6 migration targeted for 26.10.0 (vanilla Qt 6 + Fedora's `qt6-qtwayland` substitution). Community report from a tester on Fedora 44 / GNOME Wayland / Ryzen 5500 + RX 5700XT, 2026-05-28.
- **Qt 5.15-rev9 auto-DPI mis-detection on Wayland XWayland.** Without `QT_FONT_DPI=100`, fonts in Project Manager render at the wrong scale on some HiDPI / 4K Wayland setups. The launcher now sets this automatically on Wayland sessions (when `XDG_SESSION_TYPE=wayland` and the user hasn't already set `QT_FONT_DPI`). The upstream Debian .deb package needs the same workaround. Manual override is still possible via `export QT_FONT_DPI=<value>` before launch. Qt5-only: on qt6-era builds (detected at runtime via `libQt6Core.so.6` in the engine's bin dir) the launcher skips this, because a fixed `QT_FONT_DPI` would suppress Qt 6's correct per-monitor scaling and the underlying Qt 5.15 bug does not exist there.
- **ROS2 environment autodetect.** Projects using the ROS2 gem need the ROS environment (`AMENT_PREFIX_PATH`, `librcl`/`librmw` on the library path) at Editor and AssetProcessor runtime. Terminal users source `/opt/ros/<distro>/setup.bash` themselves; menu launches used to arrive with a clean environment and fail with unsatisfied `librcl` deps. The launcher now detects `/opt/ros/<distro>/` (Open Robotics packages and the `hellaenergy/ros2*` COPR RPMs share this layout) and imports the ROS environment via whitelist. Newest distro wins by default (ROS 2 codenames are alphabetical by release); `O3DE_ROS_DISTRO=<name>` pins one; `O3DE_DISABLE_ROS2=1` opts out entirely. `PYTHONPATH` is deliberately not imported: the distro setup points it at system-Python site-packages, which segfault when imported into the engine's bundled Python 3.10 venv. The gem's C++ side needs only the library path, so ROS-via-C++ works without ROS Python.
- **Project Manager helper tools need extra packages a default install pulls in via `Recommends:`.** The per-project menu in the Project Manager (Open Export Settings, Open Android Project Generator, Open CMake GUI, Build) shells out to tooling the engine RPM does not ship. Two distinct cases: (1) **Export Settings and Android Project Generator** drive the editor's bundled Python via `tkinter`, whose `_tkinter` is built against Tk 8.6 (`libtk8.6.so` / `libtcl8.6.so`); Fedora 44 moved the default `tk` / `tcl` to 9.x and split the 8.6 runtime into `tk8` / `tcl8`, and Export Settings additionally needs `tix`. The launcher sets `TCLLIBPATH=/usr/lib64/tcl` so the bundled Tcl finds Fedora's Tix (installed outside the bundled Tcl's default search path). (2) **Open CMake GUI** execs the system `cmake-gui` binary, which on Fedora is a separate package from `cmake`; **Build** uses the Ninja generator (`ninja-build`); and **Open Project folder** (plus the build/export-log links) uses Qt's `QDesktopServices::openUrl`, which shells out to `xdg-open` from `xdg-utils`. A default `dnf install o3de2605` pulls `tk8`, `tcl8`, `tix`, `cmake-gui`, `ninja-build`, and `xdg-utils` automatically; minimal installs that opt out of weak deps (`--setopt=install_weak_deps=False`) must install those by hand. Upstream's `.deb` / Snap declare neither a Tk runtime nor `cmake-gui`, so these tools are broken on a clean Debian / Ubuntu install too. Community reports on Fedora 44, 2026-05-29.
- **Editor windows do not respond to GNOME / KDE mouse-drag tile-snap gestures on Linux.** Dragging the Editor's title bar to a screen edge releases at the cursor instead of half-tiling; dragging to the top releases instead of maximizing. Project Manager (same Qt 5.15 bundle) interacts with the window manager normally; only the Editor is affected. Root cause (confirmed by code read, 2026-06-04): on Linux the Editor's main window is wrapped by `AzQtComponents::WindowDecorationWrapper` with a custom Qt-rendered `TitleBar` (the `OptionDisabled` native-decoration path is macOS-only), and that title bar implements dragging as a client-side programmatic `move()` (`Titlebar.cpp` `dragWindow()`), so the window manager never participates in the drag and its edge gestures can never trigger. The fix shape is Qt 5.15's `QWindow::startSystemMove()`, which hands the drag to the WM (and is also the wayland-correct primitive for the Qt 6 era). Workaround: keyboard shortcuts go through the WM and work correctly. On GNOME: `Super+Up` to maximize / un-maximize, `Super+Left` / `Super+Right` to half-tile, `Alt+F7` to enter keyboard-driven move mode. Covers most of the tile-snap UX. KDE bindings are similar (`Meta+Up`, `Meta+Left`, `Meta+Right` by default).

## License

This packaging is `Apache-2.0 OR MIT` to match upstream O3DE. The packaging files (`o3de.spec`, `sources/*`, `patches/*`) are dedicated under the same dual license.
