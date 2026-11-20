Enable + install:

    sudo dnf copr enable hellaenergy/o3de
    sudo dnf install o3de2610 o3de2610-devel

**CentOS Stream 10:** enable CRB and EPEL 10 before installing. They provide libraries the engine needs (assimp, google-benchmark, libunwind, poly2tri); without them `dnf` stops with "nothing provides" errors for those. COPR's own EPEL setting only applies while building the packages, not on your machine.

    sudo dnf install dnf-plugins-core
    sudo dnf config-manager --set-enabled crb
    sudo dnf install epel-release

Then enable this project with the CentOS Stream repository named explicitly (a plain `dnf copr enable` looks for an `epel-10-x86_64` repository, which this project does not have, and fails):

    sudo dnf copr enable hellaenergy/o3de centos-stream-10-x86_64

**Current release: O3DE 26.10.0** (`o3de2610` 2610.0-134, COPR build 11326762, 2026-11-14; Fedora 44, Fedora 45, Fedora rawhide and CentOS Stream 10). Upstream had not yet tagged `2610.0` or published its release tarball when this was built, so the build uses `stabilization/26100` commit `5cfafc20`, the same source and patches that `hellaenergy/o3de-stabilization` testers ran as 2610.0-131. A later build moves to the upstream release tarball once it is published. **To stay on O3DE 26.05**, install `o3de2605 o3de2605-devel` instead (2605.0-95); both majors install side by side.

This channel tracks upstream's `main` branch. Each O3DE release lands on `main` and gets tagged there (the May 2026 release is `2605.0`; the October 2025 release line topped out at `2510.2`; 26.10 will be `2610.0`). Twice-yearly major release cadence plus occasional point releases. This is the channel for stable Fedora installs.

**hellaenergy/o3de-stabilization** keeps building `stabilization/26100` until upstream tags `2610.0`, then moves to the next release's stabilization branch. For dev-tip / bleeding-edge builds from `o3de/development`, use **hellaenergy/o3de-development**.

The `o3de-dependencies` repo auto-enables alongside this one. `o3de2610-devel` is part of the install line above on purpose. It carries the engine's static libraries, and every project build links its launchers against them (`AzGameFramework`, `Launcher.Static`), so Project Manager cannot build a project without it. The main package also Recommends it, but naming it explicitly keeps it installed where weak dependencies are off (containers, Toolbox/distrobox, minimal images, `install_weak_deps=False`).

**Building projects (the toolchain is installed for you):** a normal `sudo dnf install o3de2610` also pulls in everything needed to build a project from source, the compiler and build tools (`clang`, `cmake`, `ninja-build`) plus the `-devel` headers a project links against, declared as weak dependencies (Recommends) so dnf installs them by default while a runtime-only user can opt out. Heads-up for containers and minimal installs: if your environment has weak dependencies turned off, the toolchain is skipped and project builds fail on missing compilers or headers. This is common inside containers, Toolbox, and distrobox, on minimal/server images (which often set `install_weak_deps=False`), or when installing with `--no-install-recommends` / `--setopt=install_weak_deps=False`. Backfill the whole set with `sudo dnf install $(rpm -q --recommends o3de2610 | awk '{print $1}')`, which names the Recommends explicitly. A plain `sudo dnf install o3de2610` will not help here: dnf treats the already-installed package as "nothing to do" and never revisits the skipped weak deps.

The package follows a **versioned-major naming convention** (`o3deNNNN` where NNNN is `YYMM`, e.g. `o3de2605` for the 26.05.x line, `o3de2610` for the next major) installing to `/opt/O3DE/<DISPLAY_VERSION>/`, the same path pattern as upstream's `.deb` and Windows installer. Multiple majors are co-installable; upstream's `.deb` installs one release at a time, because every release has the package name `o3de`. Each major's `engine.json` ships `engine_name: "o3de"` (as in upstream's source `engine.json`; upstream's `.deb` installs as `o3de-sdk`); the manifest at `~/.o3de/o3de_manifest.json` can register several majors at once, and a project configures against the newest registered engine it accepts (new projects accept any major); to keep a project on an older major, pin it with `<install-prefix>/scripts/o3de.sh edit-project-properties -pp <project> --user --engine-path /opt/O3DE/<version>`.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
