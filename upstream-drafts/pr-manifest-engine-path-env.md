# PR: manifest.py: honor O3DE_ENGINE_PATH env var for engine-root resolution

**Branch:** `nickschuetz/o3de:manifest-py-engine-path-env`
**Target:** `o3de/o3de:development`
**File touched:** `scripts/o3de/o3de/manifest.py` (+5 lines)
**Single commit:** DCO-signed

## Title (for the PR form)

`manifest.py: honor O3DE_ENGINE_PATH env var for engine-root resolution`

## Body (paste into PR description)

`get_this_engine_path()` resolves the engine root by walking up from the `manifest.py` file location: `Path(__file__).parents[3]`. This assumes a git-checkout layout where `scripts/o3de/o3de/manifest.py` lives 3 directories below the engine root.

**For package-based installs** (`.deb`, `.rpm`, `.snap`, `.flatpak`) where the `o3de` Python package is `pip install`-ed into a venv, the assumption breaks. `__file__.parents[3]` resolves to the venv's `lib/` directory, not the engine root. The engine list, project registration, gem resolution -- everything that walks the manifest -- gets the wrong base path.

The function already has a snap-specific bypass for the same reason:

```python
if "SNAP" in os.environ and "SNAP_BUILD" in os.environ:
    return pathlib.Path(os.environ.get('SNAP')) / os.environ.get('SNAP_BUILD')
```

This patch adds a parallel **generic** bypass keyed on `O3DE_ENGINE_PATH`, so any other package-based installer (rpm/deb/flatpak) can use the same mechanism without needing manifest.py to learn each installer's specifics:

```python
elif "O3DE_ENGINE_PATH" in os.environ:
    return pathlib.Path(os.environ.get('O3DE_ENGINE_PATH')).resolve()
```

### Behavior matrix

| Install style | Env present | Path returned |
|---|---|---|
| Snap | `SNAP` + `SNAP_BUILD` | Existing snap-specific resolution (unchanged) |
| RPM/deb/flatpak (this patch) | `O3DE_ENGINE_PATH` | The value of `O3DE_ENGINE_PATH` (resolved) |
| Git checkout | neither | Existing `__file__.parents[3]` fallback (unchanged) |

### Why this is safe

- **Three independent branches.** Adding a new elif doesn't affect either existing branch.
- **Opt-in.** Setting `O3DE_ENGINE_PATH` is a deliberate choice by the launcher wrapper; nothing changes for users who don't set it.
- **Mirrors the existing snap-bypass pattern** in style and intent.

### Test plan

- Set `O3DE_ENGINE_PATH=/tmp/test-engine` in a venv-installed environment; verify `get_this_engine_path()` returns the configured path.
- Unset `O3DE_ENGINE_PATH`; verify fallback to `__file__.parents[3]`.
- In a snap context (if testable), verify the snap branch still fires first.

### Background

Carry-patch in the Fedora packaging effort (`o3de2605`). The launcher wrapper at `/usr/bin/o3deNNNN` sets `O3DE_ENGINE_PATH=/opt/O3DE/<version>/` before invoking Project Manager; without this patch, the venv-installed `o3de` Python package can't find the engine. The same mechanism would help any future Debian/Ubuntu `.deb` or Flatpak packaging.
