**Installation:**

    sudo dnf copr enable hellaenergy/o3de-stabilization
    sudo dnf install o3de2610

This channel now builds the **26.10 pre-release line** (`o3de2610`, from upstream `stabilization/26100`, cut 2026-08-11; targeting release around Oct 28 2026). The `o3de-dependencies` repo auto-enables alongside this one. Launch with `o3de2610` (Project Manager) or via the desktop entry; the upstream Python CLI is on PATH as `o3de2610-cli`.

**Upgrading from the pre-rename `o3de` package?** The package was renamed from `o3de` to `o3de2605` (versioned-major convention; install path moved from `/opt/o3de/` to `/opt/O3DE/26.05.0/`). `dnf` won't auto-replace the old package, so a clean transition needs:

    sudo dnf remove o3de                      # remove the pre-rename package first
    rm -rf ~/.o3de                            # clear stale manifest + per-engine venvs
    sudo dnf install o3de2605                 # then install the renamed package

Skip this if you're a fresh installer (you'll just get `o3de2605` directly). This note will go away once the o3de→o3de2605 cohort has fully migrated.

**Optional subpackage:** add this if you write native C++ gems with O3DE-specific APIs that need to static-link against engine internals (test framework, builder targets):

    sudo dnf install o3de2610-devel

End users running games and Lua/ScriptCanvas project authors do **not** need `-devel`. The main `o3de2610` package ships everything needed to run the Editor, build projects against the engine's `.so`s, and develop most native projects. `dnf install o3de2610` (default) also pulls in the `*-devel` system packages your project compilation needs (clang, mesa-libGL[U]-devel, libxcb-devel, fontconfig-devel, libcurl-devel, pcre2-devel, openssl-devel, libunwind-devel, libzstd-devel, vim-common, mikkelsen-devel) via Recommends; pass `--setopt=install_weak_deps=False` for a runtime-only minimal install (CI test containers, game distribution servers).

**Building in a container?** That project-build toolchain is pulled via weak deps, so containers, Toolbox/distrobox, and minimal/server images that already run with `install_weak_deps=False` will skip it, and project builds then fail on missing compilers or headers. Backfill the whole set with `sudo dnf install $(rpm -q --recommends o3de2610 | awk '{print $1}')` (naming the Recommends explicitly). A plain `sudo dnf install o3de2610` no-ops once the package is already installed, so it will not pull the skipped weak deps.

The package follows a **versioned-major naming convention** (`o3deNNNN` where NNNN is `YYMM`: `o3de2605` for the 26.05.x line, `o3de2610` for the next major). Multiple O3DE majors can be installed side-by-side: `dnf install o3de2605 o3de2610` puts them at `/opt/O3DE/26.05.0/` and `/opt/O3DE/26.10.0/` respectively, matching upstream's `.deb` and Windows `.msi` install layout. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream, third-party gems' `compatible_engines` lists resolve correctly), and the user manifest at `~/.o3de/o3de_manifest.json` keys engine registrations by name, so only ONE `o3de` engine is *registered* at a time. Switch the active engine between installed majors via `<install-prefix>/scripts/o3de.sh register --this-engine` (e.g. `/opt/O3DE/26.10.0/scripts/o3de.sh register --this-engine` to switch to 26.10).

**What is this:** Builds from O3DE upstream's **stabilization branch** (currently `stabilization/26100`, the pre-release branch for the upcoming **26.10** release, cut 2026-08-11 from the development tip; targeting release around Oct 28 2026). This is *not* a nightly bleeding-edge build; when O3DE tags 2610.0, this branch's tip becomes the release. Quality target: near-RC. If something breaks here, we want to know before it ships to users.

**Current 26.10 configuration:**
- **Qt6 6.10.2 is BUNDLED.** 26.10 is a Qt6 engine. The Fedora system-Qt6 swap is implemented but held back for now (the bundled PySide6 needs a Qt private-API symbol that Fedora's Qt6 does not export, which makes a system-Qt6 build uninstallable on a clean box), so 26.10 ships the vanilla bundled Qt 6.10.2 for now. This keeps the QtForPython / DccScriptingInterface editor tooling working. Restore path is a PySide6 rebuild against system Qt6 (tracked as "Option B").
- **17-library Stage-1 system-swap set active** (14 Fedora system libraries: assimp, expat, freetype, google-benchmark, libsamplerate, lua, lz4, mikkelsen, openexr+imath, libpng, poly2tri, sqlite, vulkan-validation-layers, zlib; plus the 3-pack Stage-2 rebuilds dxc / spirv-cross / mcpp from `o3de-dependencies`). Only Qt6 remains bundled among the migration targets.
- **Chroots:** fedora-44, fedora-45, fedora-rawhide (now Fedora 46), centos-stream-10.

**26.05 stabilization cycle (historical record, kept for provenance):**
- **Stage 1 14-pack**: engine links to / runtime-discovers system `expat`, `freetype`, `liblz4`, `libpng`, `mikkelsen` (`libmikktspace.so.0`), `openexr` (+ `imath`), `zlib`, `lua-libs`, `poly2tri`, `assimp`, `sqlite-libs`, `libsamplerate`, `google-benchmark`, **`vulkan-validation-layers`** instead of bundled copies. 12-pack subset promoted to this channel 2026-05-11 (build 10444167); the 13th (`system_googlebenchmark`) promoted 2026-05-12 alongside the Patch0012 v2 AssetBuilder watchdog fix; the 14th (`system_vulkan_validation_layers`) promoted 2026-05-14 after Patch0013 v4 validated in experimental build 10457745.
- **Stage 2 3-pack**: `o3de2605-dxc-spirv` + `o3de2605-spirv-cross` + `o3de2605-mcpp-az` from the sibling `hellaenergy/o3de-dependencies` COPR (auto-enabled). DXC + SPIRV-Cross are binary shellouts the engine calls at asset-build / shader-compile time; mcpp is a library-link swap into the engine's AZSL preprocessor pipeline. All three promoted from experimental on 2026-05-14 after 6+ days of green soak (PoCs ✓ green since 2026-05-08).
- **Patch0012 v2 (AssetBuilder watchdog)**: child-side parent-death watchdog in `AssetBuilder/main.cpp` that prevents `AssetBuilder` orphans from accumulating across `AssetProcessor` crashes / restarts. The watchdog polls `getppid()` every 2 seconds; when the parent process changes (the builder has been reparented because AP died), the builder exits cleanly. Active in this channel as of the 2026-05-12 promotion; upstream-tracked as [o3de/o3de#19747](https://github.com/o3de/o3de/pull/19747).
- **CS10 (CentOS Stream 10) chroot**: with_opts gap fully closed 2026-05-14; CS10 now runs the same 18 swap activations as F44 + rawhide. **First CS10 stabilization build with the full pack: 10460860 GREEN** (2026-05-14). CS10's `additional_repos` includes both `https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/` (for `assimp-devel`, `google-benchmark-devel`, `poly2tri-devel`, `libunwind-devel`) and `copr://hellaenergy/o3de-dependencies` (for Stage 2 packages).

**Cherry-picks landed in stabilization/26050 absorbed in build 10476214 GREEN across F44 + rawhide + CS10** (2026-05-18 tip, NVR `2605.0^20260518git2956111`):
- **[PR #19758](https://github.com/o3de/o3de/pull/19758)** (MSVC 2026 compile fixes).
- **[PR #19757](https://github.com/o3de/o3de/pull/19757)** (preWarm particle migrated to new OPS formats).
- **[PR #19739](https://github.com/o3de/o3de/pull/19739)** (project-local AzTestRunner for SDK-installed builds).

**Release-final stabilization/26050 tip** (2026-05-23, NVR `2605.0^20260523git8e75050`) absorbs the last two pre-release-blessing commits on top of the `d86e2cb6` cherry-pick set below:
- **[PR #19778](https://github.com/o3de/o3de/pull/19778)** (engine internal version bumped to 2.6.0 per the sig-release Internal Version Number convention).
- **[PR #19779](https://github.com/o3de/o3de/pull/19779)** (Editor splashscreen updated for 26.05.0).

With these in, the stabilization/26050 tip is essentially what 2605.0 will ship on 2026-05-27.

**Latest validated build** as of 2026-05-26: **build 10511780** (NVR `2605.0^20260523git8e75050-1.fc44`, all three chroots green: F44 + rawhide + CS10). This build carries:
- The release-final tip described above
- LFS-expanded source tarball (previous build 10507773 was built from an LFS-stripped tarball that shipped 1,359 git-LFS pointer files instead of real assets, breaking sample-project asset bakes; force-swap via `dnf reinstall` if you installed before 10511780)
- Application menu polished: only `O3DE 26.05.0` (Project Manager) is visible. Editor, Material Editor, and Material Canvas are intentionally hidden from the menu: launching them cold from a menu entry can't supply a project context, so they error or fall through to PM. The canonical path is open a project from PM, then launch the standalone tools from inside the running Editor's Tools menu, which inherits the project context. Per-tool icons (extracted from upstream's Windows `.ico` files) still pair to running windows via `StartupWMClass` matching.

**Cherry-picks landed in stabilization/26050 since the 10476214 baseline** (2026-05-18 NVR `2605.0^20260518git2956111`):
- **[PR #19772](https://github.com/o3de/o3de/pull/19772)** (cherry-pick: UV-transform Vulkan rendering fix from `o3de/development`).
- **[PR #19776](https://github.com/o3de/o3de/pull/19776)** (AssetProcessor "Assets" tab search field restored on Linux).
- **[PR #19777](https://github.com/o3de/o3de/pull/19777)** (MSVC 14.50 stdext compatibility, the fix for the 26.05.0 Windows release-blocker [issue #19754](https://github.com/o3de/o3de/issues/19754)).

**Upstream patches MERGED this cycle** (will retire from our local patch series on next snapshot rebase):
- **[PR #19733](https://github.com/o3de/o3de/pull/19733)** (AzCore Lua include cleanup; MERGED 2026-05-08). Our Patch0008 becomes redundant.
- **[PR #19734](https://github.com/o3de/o3de/pull/19734)** (libtiff C99 typedefs; MERGED 2026-05-08). Our Patch0007 becomes redundant.
- **[PR #19737](https://github.com/o3de/o3de/pull/19737)** (Microphone libsamplerate PAL-trait gate; MERGED 2026-05-10). Corresponding local patch becomes redundant.

**Lua 5.5 forward-compat** (Patch0010 + Patch0011) carries the engine through Fedora rawhide's Lua 5.5 transition. Behavior-preserving on Lua 5.4 (F44); engine compiles green on Lua 5.5 (rawhide) with `liblua-5.5.so` linkage confirmed via build 10442708 (2026-05-11).

**For bleeding-edge `development`-branch builds**, see `hellaenergy/o3de-development` (ad-hoc cadence).

**Gems with system runtime dependencies:** some o3de-extras gems (ROS 2 family, AudioEngineWwise, OpenXRVk, etc.) require external system runtimes the engine RPM does not bundle. Project Manager surfaces the requirement on each gem's information icon. See [`docs/GEMS_WITH_SYSTEM_DEPS.md`](https://github.com/nickschuetz/o3de-rpm/blob/main/docs/GEMS_WITH_SYSTEM_DEPS.md) for install paths and the project-build workflow.

**Reporting issues:** https://github.com/nickschuetz/o3de-rpm/issues. Include `rpm -q o3de2610` and the COPR build ID. Engine bugs that aren't packaging-related should go upstream to https://github.com/o3de/o3de/issues.
