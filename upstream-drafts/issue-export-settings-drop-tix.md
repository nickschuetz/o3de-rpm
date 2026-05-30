<!--
DRAFT GitHub issue for o3de/o3de  (NOT filed)
Title:  Remove the deprecated tkinter.tix dependency from the project export settings UI
Labels: kind/bug, sig/build
-->

## Summary

The Project Manager's **Open Export Settings** tool (and `o3de.sh export-project --configure`) depends on Python's `tkinter.tix`. The Python standard library has deprecated `tkinter.tix` in favor of `tkinter.ttk`, and it requires the separate, unmaintained system `tix` package. On a clean Linux install that package is frequently absent, and even when it is installed the engine's bundled Python often cannot locate it because distributions install Tix outside the bundled Tcl's default search path. Either way, Export Settings fails to open:

```
  File ".../python3.10/tkinter/tix.py", line 221, in __init__
    self.tk.eval('package require Tix')
_tkinter.TclError: can't find package Tix
```

This symptom was reported earlier on Ubuntu in #18291 and #18246; #18252 improved the error message at the time. This issue proposes removing the dependency itself, so the tool works out of the box rather than asking each user to install `tix` by hand.

## Why the fix is small

The export UI (`scripts/o3de/o3de/ui/export_project.py`) already builds with `ttk`. Its entire Tix footprint is two things:

- the root window: `class MainWindow(tkinter.tix.Tk)`
- a single `tkinter.tix.Balloon` tooltip, used through `bind_widget(widget, balloonmsg=...)` calls

Migrating the root to `tkinter.Tk` and replacing the one `Balloon` with a small standard-tkinter tooltip helper (preserving the same `bind_widget(widget, balloonmsg=...)` API) removes `tkinter.tix` entirely, with no other call-site changes. The companion `scripts/o3de/o3de/export_project.py` then drops its now-unnecessary Tix availability pre-flight check.

## Not distro-specific

This is not a single distribution's problem. The `.deb` and Snap packaging do not declare a Tk/Tix runtime either, so the same failure occurs there. Removing the dependency fixes every Linux packaging target at once, with no per-distro packaging changes required.

This also helps older and minimal distributions rather than hurting them. The engine bundles its own Python (currently 3.10) via `get_python.sh`, so the system Python version does not factor in; the bundled `_tkinter` already links Tk 8.6, which this keeps; and the UI already uses `ttk`. The change only removes the `tix` extension, which is the piece most often missing on older or minimal installs. So the export tool becomes usable on more systems, not fewer.

## A question for sig-build

Was the messaging-only approach in #18252 a deliberate choice to keep the packages lean? If so, removing the dependency aligns with that goal rather than working against it.

A PR implementing this is ready.
