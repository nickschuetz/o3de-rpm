<!--
DRAFT GitHub PR for o3de/o3de  (NOT filed)
Title:  Drop deprecated tkinter.tix from the project export settings UI
Branch: fix/export-settings-drop-tix  ->  o3de/o3de:development
Note:   "Addresses #ISSUE" is used intentionally (not "Fixes") to avoid an
        accidental auto-close. Replace #ISSUE with the real number; change
        "Addresses" to "Fixes" only if you want the issue auto-closed on merge.
-->

The **Open Export Settings** window used `tkinter.tix` for its root window and a single `Balloon` tooltip. `tkinter.tix` is deprecated in the Python standard library in favor of `tkinter.ttk`, and it depends on the separate, unmaintained system `tix` package. On a clean Linux install that package is often absent, and even when present the engine's bundled Python may not find it because distributions install Tix outside the bundled Tcl's default search path. Either way **Open Export Settings** fails with:

```
_tkinter.TclError: can't find package Tix
```

## What changed

- **`scripts/o3de/o3de/ui/export_project.py`**: swap the root from `tkinter.tix.Tk` to `tkinter.Tk`, and replace the one Tix `Balloon` with a small standard-tkinter tooltip helper that keeps the same `bind_widget(widget, balloonmsg=...)` signature the call sites already use (no call-site changes). The window was already built with `ttk`.
- **`scripts/o3de/o3de/export_project.py`**: remove the now-unnecessary Tix availability pre-flight check and its "tix is not installed" branch; the configure window now gates only on `tkinter` being importable.

Result: project export settings no longer depends on the `tix` package on any platform.

## How it was tested

Ran the export-settings UI with the engine's bundled Python in the failing condition: no `TCLLIBPATH` set, so a system Tix is unfindable. That is the exact state where the current code throws `can't find package Tix`.

- Current code: fails with `_tkinter.TclError: can't find package Tix`.
- This change: constructs and renders the full window successfully; tooltips display correctly on hover; the existing `ttk` UI is unchanged.

## Compatibility (older and minimal distros)

This change lowers the runtime requirements rather than raising them, so it is safe for older and minimal Linux installs:

- O3DE ships its own Python (currently 3.10) via `get_python.sh`, identical on every platform, so the distribution's system Python version does not factor in here.
- The bundled Python's `_tkinter` already links Tk/Tcl 8.6, and this change keeps that. It removes only the separate `tix` extension, which is the piece most often absent on minimal or older installs.
- The window already used `ttk` (`ttk.Frame`, `ttk.Notebook`). The only widgets this change adds are `tkinter.Tk`, `tkinter.Toplevel`, and `ttk.Label`, all available since Tk 8.5.

Net effect: the export tool works on more systems, not fewer. Verified against the engine's bundled Python (Tk 8.6).

## Related

The missing-Tix failure was reported in #18291 and #18246; #18252 added a clearer message. Addresses #ISSUE.
