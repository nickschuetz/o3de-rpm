Enable + install:

    sudo dnf copr enable hellaenergy/o3de
    sudo dnf install o3de2605

This channel tracks upstream's `main` branch. Each O3DE release lands on `main` and gets tagged there (the May 2026 release is `2605.0`; the October 2025 release line topped out at `2510.2`). Twice-yearly major release cadence (May + October) plus occasional point releases. This is the channel for stable Fedora installs.

For pre-release validation of the next release line (currently `stabilization/26050`), use **hellaenergy/o3de-stabilization**. For dev-tip / bleeding-edge builds from `o3de/development`, use **hellaenergy/o3de-development**.

The `o3de-dependencies` repo auto-enables alongside this one. Optional `o3de2605-devel` subpackage adds the static-archive surface for native C++ gem development:

    sudo dnf install o3de2605-devel

**Building projects (the toolchain is installed for you):** a normal `sudo dnf install o3de2605` also pulls in everything needed to build a project from source, the compiler and build tools (`clang`, `cmake`, `ninja-build`) plus the `-devel` headers a project links against, declared as weak dependencies (Recommends) so dnf installs them by default while a runtime-only user can opt out. Heads-up for containers and minimal installs: if your environment has weak dependencies turned off, the toolchain is skipped and project builds fail on missing compilers or headers. This is common inside containers, Toolbox, and distrobox, on minimal/server images (which often set `install_weak_deps=False`), or when installing with `--no-install-recommends` / `--setopt=install_weak_deps=False`. Backfill the whole set with `sudo dnf install $(rpm -q --recommends o3de2605 | awk '{print $1}')`, which names the Recommends explicitly. A plain `sudo dnf install o3de2605` will not help here: dnf treats the already-installed package as "nothing to do" and never revisits the skipped weak deps.

The package follows a **versioned-major naming convention** (`o3deNNNN` where NNNN is `YYMM`, e.g. `o3de2605` for the 26.05.x line, `o3de2610` for the next major) installing to `/opt/O3DE/<DISPLAY_VERSION>/`. Multiple majors are co-installable. This matches upstream's `.deb` and Windows `.msi` install layout. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream); the manifest at `~/.o3de/o3de_manifest.json` is single-slot for active registration; switch via `<install-prefix>/scripts/o3de.sh register --this-engine`.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
