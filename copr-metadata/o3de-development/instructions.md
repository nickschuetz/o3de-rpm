**Development-branch builds.** This project tracks upstream's `development` branch. Ad-hoc cadence: rebuilds are fired by the packagers when there's something worth validating on the bleeding-edge integration branch, not on a fixed schedule.

**For stable releases, use [hellaenergy/o3de](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/)** -- that channel tracks upstream's `main` branch (where each release is merged + tagged).

**For pre-release validation of the next release line, use [hellaenergy/o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/)** -- that channel ships builds from upstream's `stabilization/<release>` branch, closer to release quality, validated continuously.

**For other branches** (e.g. a hypothetical `qt6` migration channel): a separate dedicated COPR project gets created. This project (`o3de-development`) is exclusively for the `development` branch so chroot config can stay simple and predictable.

**If you're here looking for development-branch builds:**

    sudo dnf copr enable hellaenergy/o3de-development
    sudo dnf install o3de2605

The `o3de-dependencies` repo auto-enables alongside this one. The package name follows a versioned-major convention (`o3de2605` for the 26.05.x line); multiple O3DE majors can be installed side-by-side at `/opt/O3DE/<version>/`, matching upstream's `.deb` and Windows `.msi` install layout.

**Maintainer note on `make copr-development` builds:** because this project tracks `o3de/development` tip, six of our carry-patches (Patch0001/0002/0005/0007/0008/0012) have upstream equivalents that already merged into development and would fail to apply against the source tree at `%prep`. The spec's `%bcond_with development_snapshot` gates them off when active, and the Makefile's `copr-development` target sets `--with development_snapshot` automatically at SRPM-build time. **The flag is also configured on the chroot** via `copr-cli edit-chroot --rpmbuild-with development_snapshot hellaenergy/o3de-development/<chroot>` (because `--with` flags don't propagate through COPR's SRPM rebuild).

**Optional subpackage** for native C++ gem development that needs to static-link against engine internals (test framework, builder targets):

    sudo dnf install o3de2605-devel

End users and Lua/ScriptCanvas project authors do not need it.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
