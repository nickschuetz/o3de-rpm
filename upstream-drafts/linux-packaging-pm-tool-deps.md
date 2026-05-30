# DRAFT (for Nick's review -- NOT submitted)

## Upstream gap: O3DE Linux packaging does not declare the Project Manager tool dependencies

Status: draft. Nothing filed. Needs Nick's sign-off ("fully baked") and a
re-check against `development` before anything goes to o3de/o3de. Package
names below are from the 26.05.0 install + Ubuntu conventions and must be
verified against the .deb's target Ubuntu version.

### Summary

Several Project Manager per-project tools shell out to software the
Linux installers do not declare as dependencies, so they fail on a clean
install:

- **Open Export Settings** and **Open Android Project Generator** drive
  the bundled Python's `tkinter`. `_tkinter` is DT_NEEDED-linked to
  `libtk8.6.so` + `libtcl8.6.so`; Export Settings also uses
  `tkinter.tix` (`package require Tix`).
- **Open CMake GUI** execs the system `cmake-gui` binary.
- **Build** uses the Ninja generator.

### Evidence this is cross-platform, not Fedora-specific

Read from the engine's own packaging configs (26.05.0):

- `.deb` (`cmake/Platform/Linux/Packaging_linux.cmake`,
  `CPACK_DEBIAN_PACKAGE_DEPENDS`) declares clang, ninja-build, the Qt/xcb
  build libs incl. `libxcb-keysyms1-dev`, libxkbcommon, pcre2, zlib,
  unwind, zstd -- but **no Tk runtime, no tix, no cmake-gui**.
- Snap (`cmake/Platform/Linux/Packaging/snapcraft.yaml.in`,
  `stage-packages`) adds `libtcl8.6` + `libtk8.6` -- but still **no tix
  and no cmake-gui**.

Prior upstream reports, both on Ubuntu with the `.deb`, both the exact
`_tkinter.TclError: can't find package Tix` from `tkinter/tix.py:221`:

- o3de/o3de#18291 (24.09, Ubuntu .deb, "Open Export settings")
- o3de/o3de#18246 (stabilization/2409, Ubuntu 22, `o3de.sh export-project`)

Both were closed by **o3de/o3de#18252 "Improve messaging for missing Tix
package"** (+ cherry-pick #18320), which only edited
`scripts/o3de/o3de/export_project.py` to print a friendlier "install
tix" message, plus a docs PR (o3de.org#2580). That was a reasonable
triage for the time, but it deliberately left the dependency for the
user to install by hand; it did not declare tix/tk in the `.deb`/Snap,
and it did not address `cmake-gui` or the Tix lookup-path problem. So the
functional gap persists on `development` / 26.05.0 (re-reported by a
Fedora tester 2026-05-29; reproduced + fixed downstream).

### Proposed change (the actual dependency declarations)

`.deb` -- add to `package_dependencies` in
`cmake/Platform/Linux/Packaging_linux.cmake` (verify exact names on the
target Ubuntu): `libtk8.6`, `libtcl8.6`, `tix`, `cmake-qt-gui`.

Snap -- add to `stage-packages` in `snapcraft.yaml.in` (+ the core20
variant): `tix`, `cmake-qt-gui` (libtk8.6/libtcl8.6 already present).

### Open questions to resolve before filing

1. **Tix lookup path.** On Fedora, installing `tix` is not sufficient:
   Fedora puts Tix under `/usr/lib64/tcl/` which the bundled Tcl's
   `auto_path` does not cover, so we set `TCLLIBPATH=/usr/lib64/tcl` in
   our launcher. Need to confirm whether Ubuntu's `tix` installs into a
   path the bundled Tcl already searches, or whether the engine needs an
   equivalent `TCLLIBPATH` (or `auto_path` append) for the `.deb`/Snap
   too -- in which case the right fix is engine-side in `o3de.sh` /
   `export_project.py`, benefiting all platforms including ours.
2. **cmake-gui package name** on the target Ubuntu (`cmake-qt-gui` vs
   `cmake-gui`); confirm `ninja-build` is sufficient for the PM Build
   action on the `.deb`.
3. Whether to split these into a runtime-only group vs the current
   combined build+runtime `package_dependencies` (the list mixes `-dev`
   build deps with runtime libs today).

### Downstream reference (what Fedora did)

hellaenergy o3de2605 RPM: `Recommends: tk8 tcl8 tix cmake-gui
ninja-build` + launcher `TCLLIBPATH=/usr/lib64/tcl`. Reproduced and
verified against the bundled python 3.10. The cleanest upstream outcome
would be (1) declare the deps in `.deb`/Snap and (2) move the Tix
`auto_path`/TCLLIBPATH handling engine-side so every platform's
packaging benefits, not just ours.
