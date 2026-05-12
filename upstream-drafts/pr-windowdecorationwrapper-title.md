# PR: AzQtComponents: propagate guest initial title in OptionDisabled mode

**Branch:** `nickschuetz/o3de:azqtcomponents-propagate-guest-title`
**Target:** `o3de/o3de:development`
**File touched:** `Code/Framework/AzQtComponents/AzQtComponents/Components/WindowDecorationWrapper.cpp` (+1 line)
**Single commit:** DCO-signed

## Title (for the PR form)

`AzQtComponents: propagate guest initial title in OptionDisabled mode`

## Body (paste into PR description)

`WindowDecorationWrapper::setGuest()` connects the guest's `windowTitleChanged` signal so subsequent title changes propagate to the wrapper. But the `OptionDisabled` branch (Linux + Mac, where the WM draws the titlebar instead of a Qt-rendered custom titlebar) returns early WITHOUT copying the guest's **current** title.

The non-disabled branch (Windows) just below handles this for the custom titlebar:

```
m_titleBar->setWindowTitleOverride(guest->windowTitle());
```

Project Manager's title is set by `ProjectManagerWindow`'s constructor -- which runs BEFORE `Application.cpp` wires up the wrapper via `setGuest()` -- so on Linux the WM titlebar ends up showing the `QApplication` name ("O3DE") instead of the guest's full title ("O3DE 26.05.0 Project Manager", or the failure-path "O3DE Project Manager").

### Fix

Add the equivalent `setWindowTitle()` call in the `OptionDisabled` branch so the WM-rendered titlebar shows the same string the custom titlebar would on Windows.

```
if (m_options & OptionDisabled)
{
    setWindowTitle(guest->windowTitle());   // <-- this line
    return;
}
```

One-line change, mirrors the existing pattern on the non-disabled branch.

### Why this is conservative

- **One line added, none changed.** Cannot regress the existing Windows behavior (different code path).
- **Subsequent title changes still propagate** via the `windowTitleChanged` signal connection earlier in `setGuest()`. This only handles the **initial** title which was previously being silently dropped on Linux/Mac.
- **No new Qt features** -- `QWidget::setWindowTitle()` has been part of Qt since 4.0.

### Test plan

Launch Project Manager on Linux (`o3de` or `o3deNNNN` -- the Fedora RPM packaging surfaces this as version-suffixed binaries):

**Before this patch:** WM titlebar reads just `O3DE`.

**After this patch:** WM titlebar reads `O3DE <DISPLAY_VERSION> Project Manager`, matching what Windows users see.

Same fix applies to any other consumer of `WindowDecorationWrapper` with `OptionDisabled` set whose guest had a meaningful title set before `setGuest()` ran -- though Project Manager appears to be the only such consumer in the current codebase.

### Background

Carry-patch in the Fedora packaging effort (`o3de2605`) for ~3 months; the missing-version-in-titlebar was reported by community testers expecting parity with Windows. This is the upstream of a packaging carry-patch.
