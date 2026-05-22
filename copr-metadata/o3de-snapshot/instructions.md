**One-off / ad-hoc dev builds.** This project is used when someone wants to build O3DE from upstream's `development` branch or a specific commit, without disrupting the regular `o3de-stabilization` tester channel.

**For stable releases, use [hellaenergy/o3de](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/)** -- that channel tracks upstream's `main` branch (where each release is merged + tagged).

**For pre-release validation of the next release line, use [hellaenergy/o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/)** -- that channel ships builds from upstream's `stabilization/<release>` branch, closer to release quality, validated continuously.

**If you're here looking for development-branch builds anyway:**

    sudo dnf copr enable hellaenergy/o3de-snapshot
    sudo dnf install o3de2605

The `o3de-dependencies` repo auto-enables alongside this one. The package name follows a versioned-major convention (`o3de2605` for the 26.05.x line); multiple O3DE majors can be installed side-by-side at `/opt/O3DE/<version>/`, matching upstream's `.deb` and Windows `.msi` install layout.

**Maintainer note on `make copr-snapshot-development` builds (added 2026-05-18):** when this project hosts a build sourced from `o3de/development` tip, six of our carry-patches (Patch0001/0002/0005/0007/0008/0012) have upstream equivalents that already merged into development and would fail to apply against the source tree at `%prep`. The spec's `%bcond_with development_snapshot` gates them off when active, and the Makefile's `copr-snapshot-development` target sets `--with development_snapshot` automatically at SRPM-build time. **The flag also needs to be configured on the chroot** via `copr-cli edit-chroot --rpmbuild-with development_snapshot hellaenergy/o3de-snapshot/<chroot>`, because `--with` flags don't propagate through COPR's SRPM rebuild. Unset the chroot config when subsequent builds target a non-development ref (e.g. the `qt6` branch is also off `development` but maintains its own state and may still need the gated patches).

**Optional subpackage** for native C++ gem development that needs to static-link against engine internals (test framework, builder targets):

    sudo dnf install o3de2605-devel

End users and Lua/ScriptCanvas project authors do not need it.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
