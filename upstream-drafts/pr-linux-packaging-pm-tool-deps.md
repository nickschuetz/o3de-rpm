<!--
FILED as o3de/o3de#19796 (2026-05-30)
Title:  Declare the Project Manager tool runtime deps for the Linux .deb and Snap
Branch: fix/linux-packaging-pm-tool-deps (nickschuetz/o3de)  ->  o3de/o3de:development
Commit: 6157614b34 (DCO signed)
Relates to issue #19793; pairs with PR #19794. No auto-close keyword used.
-->

Several Project Manager per-project tools shell out to system packages that the Linux `.deb` and Snap do not declare, so they fail on a clean install:

- **Open Export Settings** and **Open Android Project Generator** drive the editor's bundled Python via `tkinter`, which needs the Tk 8.6 runtime (`libtk8.6` / `libtcl8.6`). The `.deb`'s `CPACK_DEBIAN_PACKAGE_DEPENDS` did not list them. On a desktop they are usually present transitively (which is why the earlier reports #18291 / #18246 surfaced as the Tix error rather than a missing-Tk error), but a minimal or CI install is missing them. The snapcraft `stage-packages` already listed `libtcl8.6` / `libtk8.6`.
- **Open CMake GUI** runs a bare `cmake-gui` resolved via `PATH` (`Code/Tools/ProjectManager/Platform/Linux/ProjectUtils_linux.cpp`), not the bundled `cmake/runtime/`, so it needs the system cmake-gui package, which on Debian/Ubuntu is `cmake-qt-gui`. Neither the `.deb` nor the Snap declared it.

## What changed

- `.deb` (`cmake/Platform/Linux/Packaging_linux.cmake`): add `libtk8.6`, `libtcl8.6`, `cmake-qt-gui` to `package_dependencies`.
- Snap (`snapcraft.yaml.in` and `snapcraft_core20.yaml.in`): add `cmake-qt-gui` to `stage-packages` (the Tk runtime was already present there).

## How the need was verified

The dependency requirements were confirmed from the engine source, not guessed:
- `tkinter` usage in `scripts/o3de/o3de/ui/export_project.py` (and the bundled Python's `_tkinter` links `libtk8.6` / `libtcl8.6`) for Export Settings and Android Project Generator.
- `ProjectUtils_linux.cpp` calls `process.setProgram("cmake-gui")`, a bare binary resolved via `PATH`, so the system cmake-gui package is required regardless of the bundled cmake.
- `libtk8.6` / `libtcl8.6` package names are confirmed by the snapcraft `stage-packages` already using them; `cmake-qt-gui` is the standard Debian/Ubuntu package providing `cmake-gui`.

Note: the `.deb`/Snap are built at release time, not in PR CI, so this dependency-list change is not exercised by the per-PR build matrix.

## Related

Pairs with #19794 (removes the deprecated `tkinter.tix` dependency, so Export Settings no longer needs the `tix` package; the Tk 8.6 runtime is still required). Relates to #19793.
