**Development-branch builds.** This project tracks upstream's `development` branch. Refreshed automatically by a weekly Sunday 06:00 UTC cron (`.github/workflows/snapshot-development.yml`), which skips the build when upstream's `development` tip has not moved since the last successful build; packagers can also fire a manual rebuild at any time.

**Release game export works here.** These builds ship the monolithic (release, static) engine permutation alongside the default profile engine, so exporting a project in the release configuration (Project Manager "Export Launcher" with Build Monolithic on, or `o3de export-project ... -cfg release`) links and runs directly against the installed RPM, no source build of the engine required.

**For stable releases, use [hellaenergy/o3de](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/)** -- that channel tracks upstream's `main` branch (where each release is merged + tagged).

**For pre-release validation of the next release line, use [hellaenergy/o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/)** -- that channel ships builds from upstream's `stabilization/<release>` branch, closer to release quality, validated continuously.

**For an in-progress migration branch:** a separate dedicated COPR project is created rather than overloading this one (as was done for the Qt6 migration, which has since merged into development). This project (`o3de-development`) is exclusively for the `development` branch so chroot config can stay simple and predictable.

**If you're here looking for development-branch builds:**

    sudo dnf copr enable hellaenergy/o3de-development
    sudo dnf install o3de2605

The `o3de-dependencies` repo auto-enables alongside this one. The package name follows a versioned-major convention (`o3de2605` for the 26.05.x line); multiple O3DE majors can be installed side-by-side at `/opt/O3DE/<version>/`, matching upstream's `.deb` and Windows `.msi` install layout.

**Maintainer note on `make copr-development` builds:** because this project tracks `o3de/development` tip, seven of our carry-patches (Patch0001/0002/0004/0005/0007/0008/0012) have upstream equivalents that already merged into development and would fail to apply against the source tree at `%prep` (Patch0004 is the newest, superseded by o3de/o3de#19752 on 2026-06-09). The spec's `%bcond_with development_snapshot` gates them off when active, and the Makefile's `copr-development` target sets `--with development_snapshot` automatically at SRPM-build time. **The bcond set is also configured on the chroots** via `copr-cli edit-chroot --rpmbuild-with 'development_snapshot qt6 monolithic' hellaenergy/o3de-development/<chroot>` (because `--with` flags don't propagate through COPR's SRPM rebuild). The `monolithic` bcond adds a second release-config engine build so a release game export works (promoted from o3de-experimental on 2026-08-03 after end-to-end export validation); it costs roughly +0.7 GB and +1.5 h per build. A `qt6-merge-gate` pre-flight halts the build if upstream `development` has flipped to Qt6 while these chroots do not yet carry the `qt6` bcond.

**Optional subpackage** for native C++ gem development that needs to static-link against engine internals (test framework, builder targets):

    sudo dnf install o3de2605-devel

End users and Lua/ScriptCanvas project authors do not need it.

**Building projects (the toolchain is installed for you):** a normal `sudo dnf install o3de2605` also pulls in everything needed to build a project from source, the compiler and build tools (`clang`, `cmake`, `ninja-build`) plus the `-devel` headers a project links against, declared as weak dependencies (Recommends) so dnf installs them by default while a runtime-only user can opt out. Heads-up for containers and minimal installs: if your environment has weak dependencies turned off, the toolchain is skipped and project builds fail on missing compilers or headers. This is common inside containers, Toolbox, and distrobox, on minimal/server images (which often set `install_weak_deps=False`), or when installing with `--no-install-recommends` / `--setopt=install_weak_deps=False`. Backfill the whole set with `sudo dnf install $(rpm -q --recommends o3de2605 | awk '{print $1}')`, which names the Recommends explicitly. A plain `sudo dnf install o3de2605` will not help here: dnf treats the already-installed package as "nothing to do" and never revisits the skipped weak deps.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
