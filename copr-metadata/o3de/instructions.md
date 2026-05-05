This project will be populated when O3DE upstream tags a stable release we package. For now, use **hellaenergy/o3de-stabilization** for community testing of pre-release builds from O3DE's stabilization branch (the same branch that becomes the next tagged release).

**When stable releases land here:**

    sudo dnf copr enable hellaenergy/o3de
    sudo dnf install o3de2605

The `o3de-dependencies` repo auto-enables alongside this one. Optional `o3de2605-devel` subpackage adds the static-archive surface for native C++ gem development:

    sudo dnf install o3de2605-devel

The package follows a **versioned-major naming convention** (`o3deNNNN` where NNNN is `YYMM` — `o3de2605` for the 26.05.x line, `o3de2610` for the next major) installing to `/opt/O3DE/<DISPLAY_VERSION>/`. Multiple majors are co-installable. This matches upstream's `.deb` and Windows `.msi` install layout. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream); the manifest at `~/.o3de/o3de_manifest.json` is single-slot for active registration — switch via `<install-prefix>/scripts/o3de.sh register --this-engine`.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
