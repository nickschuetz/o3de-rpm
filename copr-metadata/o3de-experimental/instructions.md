**For end-user testing use [hellaenergy/o3de](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/) (stable) or [hellaenergy/o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/) (during a pre-release window).** This repo is for the packagers' own validation; RPMs here track the bleeding-edge development branch and carry in-flight changes.

**If you're here anyway** (e.g. engine contributors on the development branch, or packagers validating the monolithic release-export path):

    sudo dnf copr enable hellaenergy/o3de-experimental
    sudo dnf install o3de2610

The `o3de-dependencies` repo auto-enables alongside this one (no separate `dnf copr enable` needed). Add the optional `-devel` subpackage if you need engine static archives for native C++ gem development:

    sudo dnf install o3de2610-devel

**What is this:** O3DE experimental builds. Realigned 2026-07-24 onto upstream's `development` branch (Qt6, same source as [hellaenergy/o3de-development](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-development/)) plus the **monolithic (release, static) engine permutation**. It was formerly the Stage-1 system-library-swap validation channel; that 17-swap set is now validated and shipping on the community channels. With the 26.10 stabilization branch (`stabilization/26100`) open and the shipping channels reverted to bundled Qt6, this channel now validates forward-looking, riskier changes that aren't ready for community testers, including the **system-Qt6 swap** held back from the shipping RPMs (Option B, pending a PySide6 rebuild against system Qt6).

**Why the monolithic permutation matters:** the default channels build only the `profile` (shared-library) configuration, which is fine for the editor and for running a game locally, but a **release game export** (Project Manager "Export Launcher", or `o3de2610-cli export-project --config release`) needs the engine's release/static libraries in the install. Without them the export fails with `No monolithic artifacts are detected in the engine installation`. This channel additionally builds and ships that permutation (`lib/Linux/release/Monolithic/*.a` + `cmake/Platform/Linux/Monolithic/ConfigurationTypes_release.cmake`), so a release export links a self-contained monolithic game launcher. Cost: a larger package (~+0.7 GB installed) and a longer build. Validated end-to-end (a release export produces a working monolithic GameLauncher, root-free).

Note: a downstream workaround is carried for an upstream gap where the engine doesn't install `libmeshoptimizer.a` into the SDK (its installer Find file is an empty interface, unlike miniaudio/ogg); without it the monolithic launcher link fails on undefined `meshopt_*` symbols. The workaround installs the static lib and a proper `STATIC IMPORTED` Find file; it retires when the upstream fix lands.

The package follows a **versioned-major naming convention** (`o3de2610` for the 26.10.x line) installing to `/opt/O3DE/<DISPLAY_VERSION>/`, matching upstream's `.deb` and Windows `.msi` install layout. Multiple majors can be installed side-by-side. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream); the manifest at `~/.o3de/o3de_manifest.json` is single-slot for active registration: switch via `<install-prefix>/scripts/o3de.sh register --this-engine`.

**Subpackage layout**, same as the other channels: main `o3de2610` (runtime + project-build essentials; larger here because of the monolithic static libs); optional `o3de2610-devel` (engine static archives for native C++ gems that static-link engine internals); optional `o3de2610-debug` (debug-config binaries, only when `--with debug` is set, NOT activated in this channel). Project-build `*-devel` system packages pulled in via Recommends; opt out with `--setopt=install_weak_deps=False`. Note the inverse: containers, Toolbox/distrobox, and minimal/server images that already run with `install_weak_deps=False` will skip the toolchain, so project builds fail on missing compilers/headers until you backfill with `sudo dnf install $(rpm -q --recommends o3de2610 | awk '{print $1}')` (naming the Recommends explicitly, since a plain `sudo dnf install o3de2610` no-ops when it is already installed).

**`o3de2610-cli` PATH wrapper**: `/usr/bin/o3de2610-cli` forwards to `/opt/O3DE/26.10.0/scripts/o3de.sh` so the upstream Python CLI (project / gem / engine management, ~25 sub-commands, including `export-project`) is reachable on `$PATH`.

**Gems with system runtime dependencies:** some o3de-extras gems (ROS 2 family, AudioEngineWwise, OpenXRVk, etc.) require external system runtimes the engine RPM does not bundle. Project Manager surfaces the requirement on each gem's information icon. See [`docs/GEMS_WITH_SYSTEM_DEPS.md`](https://github.com/nickschuetz/o3de-rpm/blob/main/docs/GEMS_WITH_SYSTEM_DEPS.md) for install paths and the project-build workflow.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
