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

### Who actually does this

O3DE's Linux packaging (.deb / Snap) is, in practice, thinly maintained:
there is no active dedicated maintainer for it right now, and the closest
person is already overloaded. That reality is itself an argument for
option 1 below: a single engine-side change fixes every platform in one
PR that the core / sig-build review path can take, instead of N separate
per-distro packaging changes that each need an owner who does not exist.
This is effectively on us (sig-build / the Fedora effort). The realistic
path is for us to author the small engine-side fix and shepherd it,
rather than file an issue and wait for a maintainer to pick it up.

### Proposed fixes, strongest first

**1. (Preferred, fixes every platform) Drop the deprecated `tkinter.tix`.**
The export-settings UI (`scripts/o3de/o3de/ui/export_project.py`) imports
`tkinter.tix`, which Python itself reports as deprecated and unmaintained
("the tkinter.tix wrapper module is deprecated in favor of tkinter.ttk").
The migration is small and well-scoped: that 539-line file already builds
its UI with `ttk` (`ttk.Frame`, `ttk.Notebook`), and its entire Tix
footprint is exactly two things:
- `class MainWindow(tkp.Tk)` -- swap the root to the standard
  `tkinter.Tk`.
- one `tkp.Balloon` tooltip, used through ~10 uniform
  `tool_tip.bind_widget(widget, balloonmsg=...)` calls.
There are no other Tix-only APIs (no `Tix` widgets beyond Balloon, no
`package require Tix` evals). A drop-in tooltip helper (~30 lines of
standard tkinter: a Toplevel shown on `<Enter>` / hidden on `<Leave>`)
that keeps the same `bind_widget(widget, balloonmsg=...)` signature
replaces the one `tkp.Balloon` construction with no churn at the ~10 call
sites. Net result: the `tix` dependency and the Tix-lookup-path problem
are gone on every platform. This is the fix that actually retires the
problem, and it is genuinely small.

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

### Status of the open items (none block filing the issue)

The first contact here is an issue / sig-build proposal, not a finished
PR, so these do not all need answers up front:

1. RESOLVED (folded into option 1 above): the ttk migration is small --
   only `tkp.Tk` + one `tkp.Balloon` tooltip; the rest is already ttk.
2. PR-time detail, not issue-blocking: exact Ubuntu package names for the
   `.deb` (`cmake-qt-gui` vs `cmake-gui`; Tk runtime), and confirming
   `ninja-build` covers the PM Build action there. These belong with the
   per-distro packaging change (option 3). Since Linux packaging is
   effectively unmaintained, if we want option 3 done we likely carry it
   ourselves; but it does not gate option 1, which is the priority.
3. A question to pose to sig-build in the issue, not something to
   pre-answer: was #18252's messaging-only resolution a deliberate
   "keep the package lean" stance? Either way, option 1 *removes* a
   dependency, which aligns with a lean-package goal -- worth stating
   that explicitly when raising it.

### Downstream reference (what Fedora did, as the interim)

hellaenergy o3de2605 RPM: `Recommends: tk8 tcl8 tix cmake-gui ninja-build`
+ launcher `TCLLIBPATH=/usr/lib64/tcl` (option 2, Fedora-specific path).
Reproduced and verified against the bundled python 3.10. This unblocks
Fedora users today, but it is exactly the per-distro workaround that
option 1 would make unnecessary everywhere.
