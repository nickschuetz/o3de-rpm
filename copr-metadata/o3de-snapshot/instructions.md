**One-off / ad-hoc dev builds.** This project is used when someone wants to build O3DE from upstream's `development` branch or a specific commit, without disrupting the regular `o3de-stabilization` tester channel.

**For regular pre-release tester builds, use [hellaenergy/o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/) instead.** That's the channel that ships builds from upstream's `stabilization/<release>` branch — closer to release quality, validated continuously.

**If you're here looking for development-branch builds anyway:** `sudo dnf copr enable hellaenergy/o3de-snapshot && sudo dnf install o3de2605`. The `o3de-dependencies` repo auto-enables alongside this one. The package name follows a versioned-major convention (`o3de2605` for the 26.05.x line); multiple O3DE majors can be installed side-by-side at `/opt/O3DE/<version>/`, matching upstream's `.deb` and Windows `.msi` install layout.

**Optional subpackage:** `sudo dnf install o3de2605-devel` if you write native C++ gems with O3DE-specific APIs that need to static-link against engine internals (test framework, builder targets). End users and Lua/ScriptCanvas project authors do not need it.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
