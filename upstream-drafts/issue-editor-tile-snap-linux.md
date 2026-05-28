Title: Editor windows do not honor GNOME tile-snap / edge-drag gestures on Linux

## Describe the issue

On Linux with GNOME (Mutter compositor), the Editor's main window doesn't snap or maximize when its title bar is mouse-dragged to a screen edge. Project Manager (using the same Qt 5.15 bundle and the same WM session) interacts with Mutter normally and tile-snaps as expected. The behavior difference is reproducible on Fedora 44 / GNOME 47 / X11 session.

## Repro

1. Install O3DE on a Fedora 44 / GNOME workstation (any install method; reproduced against the upstream `.deb` and against our Fedora RPM packaging).
2. Open Project Manager. Mouse-drag the Project Manager title bar to the left or right screen edge: window tile-snaps to half the screen. Mouse-drag to the top: window maximizes. This is the expected GNOME behavior.
3. Open or create a project, then click Edit Project to launch the Editor.
4. Mouse-drag the Editor title bar to a screen edge or to the top.

Expected: same tile-snap / maximize behavior as Project Manager.
Actual: drag releases at the cursor position; no snap, no maximize.

## Workaround that exists today

`Super+Up` / `Super+Left` / `Super+Right` keyboard shortcuts (GNOME's WM bindings) work on the Editor because they go through a different code path than the mouse-drag-to-edge gesture. `Alt+F7` for keyboard-driven move also works. Covers most of the tile-snap UX without the mouse gesture; documents around the issue rather than fixing it.

## Suspected source

Difference between Project Manager and Editor on the window-management surface is `AzQtComponents::WindowDecorationWrapper`. PM does not wrap its main window in it; the Editor does. The wrapper is at:

`Code/Framework/AzQtComponents/AzQtComponents/Components/WindowDecorationWrapper.{h,cpp}`

In `OptionDisabled` mode (the Linux/Mac path where the native WM is supposed to draw the title bar rather than the Qt-rendered custom one), the wrapper still:

- Sets itself up as a top-level `Qt::Window` QFrame with `setAttribute(Qt::WA_NativeWindow, true)` (line 124 in dev tip), making the wrapper rather than the guest QMainWindow the window the WM sees.
- Installs `eventFilter`, `childEvent`, `nativeEvent`, `changeEvent`, `resizeEvent`, `hideEvent`, `showEvent`, and `closeEvent` overrides on that top-level frame.
- Wraps the guest widget (Editor's QMainWindow) as an internal child.

`handleNativeEvent` has Windows-specific Aero Snap support inside a `#ifdef Q_OS_WIN` block (the `WM_NCHITTEST` + `DefWindowProc` dance around line 544-585). On non-Windows, that path falls through and returns false. So the Windows side is explicitly engineered to preserve native tile-snap; the Linux/Mac side has nothing equivalent and relies on Qt's default native event flow to reach the WM intact.

This is plausibly where the snap gesture gets lost (either because the wrap-in-frame structure means the WM is interacting with a frame that isn't passing the drag intent down to the right window handle, or because one of the event-filter overrides is consuming the gesture before Qt's default handling can forward it). Haven't pinned down the exact swallowing site; tagging it as a candidate region rather than a confirmed cause.

## What it would help to know from sig-content / sig-platform

1. Is the OptionDisabled path expected to be fully transparent to the WM on Linux, or is some level of event interception load-bearing for other features (dock-icon attachment, multi-monitor chrome adaptation, child-window management)?
2. If it's expected to be transparent: any thoughts on whether the right fix is at the `nativeEvent` / `handleNativeEvent` level (some non-Windows passthrough that mirrors the Windows Aero Snap intent), at the constructor level (different `Qt::Window` flag combination in OptionDisabled mode that doesn't claim the native window so aggressively), or by skipping the wrap-in-frame entirely in OptionDisabled mode and letting the guest widget be the top-level window?
3. Wayland-side equivalent: should this work via XDG decorations on Wayland, or does the same wrapper hierarchy break it there too? (Issue #18513 tracks Wayland support more broadly.)

Happy to put together a draft PR once we have a direction. Reproducer is reliable; the architectural piece is what I'd value input on first.

## Environment

- Distro: Fedora 44 / GNOME 47 / X11 session, NVIDIA proprietary driver, RTX 2080 Ti
- O3DE engine version: 26.05.0 (also reproduced against stabilization/26050 snapshots back to ~April 2026)
- Qt: 5.15.2-rev9 (the bundled custom Qt from packages.o3de.org)

## Cross-references

- #18513 (Wayland support feature request) — related but broader; this is the X11-side gesture interaction specifically
- #19750 (the title-propagation fix in the same wrapper, merged 2026-05-14) — unrelated code path; included for context on recent WindowDecorationWrapper touches
