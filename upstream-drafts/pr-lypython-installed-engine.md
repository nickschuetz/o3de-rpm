# PR: LYPython: install from sdist when engine is installed (read-only)

**Branch:** `nickschuetz/o3de:lypython-non-editable-for-installed-engine`
**Target:** `o3de/o3de:development`
**File touched:** `cmake/LYPython.cmake` (+17 / -1)
**Single commit:** DCO-signed

## Title (for the PR form)

`LYPython: install from sdist when engine is installed (read-only)`

## Body (paste into PR description)

When a user project's `cmake configure` runs against a **system-installed engine** (`/opt/O3DE/<v>/` for the Fedora packaging, equivalent paths for `.deb`/`.snap`/`.flatpak`/`.msi`), the engine source directory is read-only. O3DE's `ly_pip_install_local_package_editable()` function (in `cmake/LYPython.cmake`) does:

```cmake
${LY_PYTHON_CMD} -m pip install -e ${package_folder_path} --no-deps ...
```

against several `Tools/*` and `scripts/o3de` packages during cmake-configure.

**Editable installs (and even non-editable installs of legacy setup.py packages) write `.egg-info` into the source directory.** Against a read-only engine root this fails with:

```
error: could not create '...scripts/o3de/o3de.egg-info': Read-only file system
```

### Fix

Add an `INSTALLED_ENGINE`-gated branch that:

1. **Drops the `-e` flag** -- editable doesn't make sense for a read-only engine source anyway.
2. **Prefers a pre-built sdist** under `<package>/dist/*.tar.gz` if one exists. `pip` then runs entirely from the sdist tarball and never touches the source directory.
3. **Falls back to plain non-editable install** of the source dir if no sdist is shipped, for forward-compatibility with future packages that haven't been pre-built into sdists.

```cmake
set(_pip_install_target ${package_folder_path})
set(_pip_install_mode_args "-e")
if (INSTALLED_ENGINE)
    set(_pip_install_mode_args "")
    file(GLOB _pip_sdist_candidates "${package_folder_path}/dist/*.tar.gz")
    if (_pip_sdist_candidates)
        list(GET _pip_sdist_candidates 0 _pip_install_target)
    endif()
endif()
```

Then pass `${_pip_install_mode_args} ${_pip_install_target}` into the `pip install` command instead of the hardcoded `-e ${package_folder_path}`.

### Behavior matrix

| Engine kind | `INSTALLED_ENGINE` | sdist present | pip args |
|---|---|---|---|
| Git checkout / dev tree | unset | (irrelevant) | `-e <source>` (unchanged) |
| Installed package, sdist shipped | set | yes | `<dist/*.tar.gz>` |
| Installed package, no sdist | set | no | `<source>` (non-editable; assumes engine root is writable enough for this package; safer than `-e` regardless) |

### Why this is conservative

- **Default unchanged.** Development builds in a writable git checkout don't set `INSTALLED_ENGINE` and keep the current editable install path bit-for-bit.
- **Gated by an explicit packager opt-in.** The `INSTALLED_ENGINE` cmake var is set by the package's cmake (e.g., the Fedora spec's `-DINSTALLED_ENGINE=TRUE`); without that, nothing changes.
- **Sdist-first is best-effort.** If a packager hasn't built sdists yet, the fallback non-editable install at least gets the package registered.

### Test plan

- Install engine into `/opt/O3DE/<v>/` (or equivalent) via the Fedora RPM (or any package).
- `cmake configure` a user project. With this patch: `pip install` runs from sdists if present; succeeds against read-only engine root. Without this patch: fails with `egg-info` write to read-only fs.
- Re-run cmake-configure in a git checkout (`INSTALLED_ENGINE` unset): editable install path used, bit-for-bit unchanged from current behavior.

### Background

Carry-patch in the Fedora packaging effort. Packagers like .deb / .snap / .flatpak hit the same problem; this is a generic mechanism that any package-based installer can use.
