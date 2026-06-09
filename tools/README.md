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

## check-qt6-merge.py

Probe: has the o3de/o3de `qt6` branch merged into `development` yet? Watches the
discriminating signal -- the Linux x86_64 3rdParty Qt association in
`cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` -- for the
flip from `qt-5.15.x` + `pyside2` to `qt-6.x` + `pyside6` (x86_64 is the file
that flips; the qt6 branch keeps aarch64 on Qt5), and reports the merge PR
(o3de/o3de#19567) status alongside.

Run locally:

    make check-qt6-merge
    # or:
    python3 tools/check-qt6-merge.py
    QT6_PROBE_BRANCH=qt6 python3 tools/check-qt6-merge.py   # exercise the MERGED path

Exit codes (so callers/CI can react):

- **0 NOT-YET** -- development is still Qt5; no action.
- **10 MERGED** -- development carries Qt6/PySide6; run the FOLLOW_UPS.md
  "TRIGGER: qt6 merges into o3de/development" chroot flip before the next
  o3de-development cron.
- **2 UNKNOWN** -- could not fetch/parse (network/API outage or a 3rdParty
  layout change); re-probe. An outage is reported as UNKNOWN, never as
  not-merged (outage is not drift).

Version-agnostic (matches the `qt-6` major, not the exact rev, so an upstream
rev bump does not spuriously flip the verdict) and outage-aware. The
`qt6-merge-gate` Makefile target builds on it: a pre-flight interlock wired into
`make copr-development` / `copr-development-debug` / `copr-development-and-test`
and the `snapshot-development.yml` cron, it hard-stops a build if development has
gone Qt6 but the target COPR chroots still lack the `qt6` bcond, printing the
exact `edit-chroot` flip commands.

Dependencies: stdlib + `gh` CLI (falls back to raw.githubusercontent if absent)
+ `copr-cli` (for the gate's chroot check). No PyPI packages.

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
