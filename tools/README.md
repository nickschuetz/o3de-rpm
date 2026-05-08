# tools/

Utility scripts for o3de-rpm maintenance.

## check-deps-drift.py

Audits drift between three sources of truth for O3DE 3rdParty packages:

1. **Engine pins** -- `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake`
   on the active stabilization branch (default `stabilization/26050`).
2. **Our COPR rebuilds** -- `hellaenergy/o3de-dependencies` latest-succeeded builds.
3. **Upstream 3p package-source** -- `o3de/3p-package-source/package-system/<Name>/build_config.json`.

Run locally:

    make check-deps-drift
    # or:
    python3 tools/check-deps-drift.py
    python3 tools/check-deps-drift.py --engine-ref development

Per-package classification:

- **in-sync** -- engine, COPR, and 3p build_config agree.
- **minor-drift** -- same upstream version, different rev label (e.g. rev1 vs rev2).
- **out-of-date** -- COPR trails the engine pin (script exits 1; workflow fails).
- **ahead-of-engine** -- COPR ships newer than the engine pin (informational).
- **gap** -- engine references it, we do not ship in COPR, no `system_<X>` bcond in the spec.
- **covered-by-spec** -- engine references it; covered by `%bcond_with system_<X>` in `o3de.spec`.
- **cruft** -- COPR ships it but the engine no longer references it.

Dependencies: stdlib + `gh` CLI + `copr-cli`. No PyPI packages.

## .github/workflows/check-deps-drift.yml

Scheduled weekly (Monday 06:00 UTC) and `workflow_dispatch`. Runs the
script in a Fedora 44 container, then either creates or edits a sticky
issue titled "Dependency drift report" with the latest output. Fails the
workflow (red dot) when the script exits non-zero.

## Updating dep-map.yaml

When a package is added to or removed from `hellaenergy/o3de-dependencies`,
or when the engine adds a new `ly_associate_package` entry, edit
`tools/dep-map.yaml`:

- `copr_packages:` -- engine package name -> COPR source package name.
  Use `""` to indicate "not in COPR" (the script will then check whether
  the spec covers it via a `system_<X>` bcond).
- `threep_dirs:` -- only add an entry when the upstream 3p directory name
  differs from the engine package name (e.g. `qt: Qt`).
- `spec_bcond_aliases:` -- engine package name -> bcond suffix (so
  `Lua: lua` lets the script know `system_lua` covers `Lua`). Use `""`
  for "no spec swap available".
- `ignore_engine_packages:` -- multiplatform header-only or build-tooling
  deps the script should silently skip.

The YAML loader in `check-deps-drift.py` is a minimal regex-only parser
that handles the structure described in the file's own header. If you
add anchors, flow style, or multi-line strings, switch the file to
`.json` (the loader auto-detects extension) or expand the parser.

## Conventions

- ASCII-only output (no em-dashes, smart quotes, etc).
- stdlib + system tools only.
- `tools/` is for maintenance scripts; build/test wrappers live under
  `tests/` and `scripts/`.
