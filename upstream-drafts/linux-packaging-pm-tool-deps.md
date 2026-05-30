# DRAFT (for Nick's review -- NOT submitted)

## O3DE Project Manager Linux tools fail on a clean install (and the deeper cause is a deprecated Tix dependency)

Status: draft. Nothing filed. Needs Nick's sign-off and a re-verify against
`development` at filing time. Verified 2026-05-29 against `origin/development`:
the gap still exists there (see below), so this is not stale.

### The symptom

Several Project Manager per-project menu tools fail on a clean Linux
install because they depend on software the install does not provide:

- **Open Export Settings** -- drives the bundled Python's `tkinter`, and
  specifically `tkinter.tix` (`package require Tix`).
- **Open Android Project Generator** -- plain `tkinter` (Tk 8.6 runtime:
  `libtk8.6.so` / `libtcl8.6.so`).
- **Open CMake GUI** -- execs the system `cmake-gui` binary.
- **Build** -- uses the Ninja generator.

### Why this is upstream-wide, not one distro's problem

The exact `_tkinter.TclError: can't find package Tix` was reported on
**Ubuntu with the `.deb`** in 2024: o3de/o3de#18291 and #18246 (identical
traceback at `tkinter/tix.py:221`). Both were closed by o3de/o3de#18252
("Improve messaging for missing Tix package"), which only edited
`export_project.py` to print a friendlier "install tix" message, plus a
docs PR. That was a fair triage at the time, but it left the user to
hand-install the dependency and did not address CMake GUI or the Tix
lookup problem. Verified against `origin/development` (2026-05-29): the
`.deb` `package_dependencies` still carries only `ninja-build` +
`libxcb-keysyms1-dev` with no Tk runtime / tix / cmake-gui, and the Snap
`stage-packages` still has `libtk8.6`/`libtcl8.6` but no tix / cmake-gui.
So the functional gap persists on dev.

A shipped menu item that fails on a clean install with a Python traceback
is a poor first-run experience; the user did nothing wrong. So rather than
keep pushing the dependency onto the user, the better outcomes are
engine-side.

### Proposed fixes, strongest first

**1. (Preferred, fixes every platform) Drop the deprecated `tkinter.tix`.**
The export-settings UI (`scripts/o3de/o3de/ui/export_project.py`) uses
`tkinter.tix`, which Python itself reports as deprecated and unmaintained
("the tkinter.tix wrapper module is deprecated in favor of tkinter.ttk").
Migrating that UI to `tkinter.ttk` removes the `tix` dependency entirely
on every platform -- no tix package to ship, and no Tix-lookup-path
problem to solve. Scope depends on which Tix widgets the panel uses (ttk
has direct equivalents for most; some Tix-specific widgets may need a
small reimplementation), so this is a real but bounded code change. This
is the fix that actually retires the problem.

**2. (Interim engine fix, if Tix is kept) Make the bundled Tcl find a
system Tix.** When `tix` IS installed, the bundled Python's Tcl still
cannot load it because the package lands outside the bundled Tcl's
`auto_path`, and the location is distro-specific (Fedora:
`/usr/lib64/tcl/Tix*`; Debian elsewhere). So "just install tix" is not
sufficient even with tix present. The engine could append the right
directory to `auto_path` / `TCLLIBPATH` before `Tix.Tk()`. Because the
path differs per distro, this is inherently messy compared to option 1 --
which is the main argument for option 1.

**3. (Complementary packaging, per distro) Declare the runtime deps.**
Independent of the Tix question, the PM tools need their runtime present:
the Tk 8.6 runtime (Android Generator + Export Settings if Tix is kept),
the `cmake-gui` binary (CMake GUI), and Ninja (Build). O3DE can lead by
example in its own `.deb`/Snap:
- `.deb` `package_dependencies` (`cmake/Platform/Linux/Packaging_linux.cmake`):
  add the Tk 8.6 runtime + the CMake-GUI package (Ubuntu names to verify,
  likely `libtk8.6`, `libtcl8.6`, `cmake-qt-gui`; `tix` only if option 1
  is not taken).
- Snap `stage-packages` (`snapcraft.yaml.in` + the core20 variant): add
  the CMake-GUI package (`libtk8.6`/`libtcl8.6` already present; `tix`
  only if option 1 is not taken).
Downstream packagers (Fedora, etc.) do the equivalent for their distro.

### Open questions before filing

1. Which Tix widgets does `export_project.py` actually use -- i.e. how big
   is the ttk migration (option 1)?
2. Exact Ubuntu package names for the `.deb` (`cmake-qt-gui` vs
   `cmake-gui`; Tk runtime), and confirm `ninja-build` covers the PM Build
   action on the `.deb`.
3. Was #18252's messaging-only resolution a deliberate "keep the package
   lean" stance? If so, frame option 1 as removing the dependency rather
   than adding to it -- which should align with that goal.

### Downstream reference (what Fedora did, as the interim)

hellaenergy o3de2605 RPM: `Recommends: tk8 tcl8 tix cmake-gui ninja-build`
+ launcher `TCLLIBPATH=/usr/lib64/tcl` (option 2, Fedora-specific path).
Reproduced and verified against the bundled python 3.10. This unblocks
Fedora users today, but it is exactly the per-distro workaround that
option 1 would make unnecessary everywhere.
