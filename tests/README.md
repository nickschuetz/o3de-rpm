# Test suite for the O3DE RPM

Automated integration tests for an installed `o3de` RPM. Designed for three audiences:

1. **This repo's maintainer**, catching regressions between spec changes.
2. **O3DE engine contributors**, validating that their development branch builds and runs as a Fedora RPM before merging.
3. **O3DE release engineering**, gating releases on "does this work as a packaged engine on Fedora?"

The same test suite serves all three. Differences are only in *which* git ref or release tag the RPM was built from.

## Tiered design

Each tier requires more state from the prior. You can run any subset.

| Tier | What it covers | What it requires | Runtime |
|---|---|---|---|
| **1** | RPM-level integrity (license, version, rpm -V) | RPM installed | <1 s |
| **2** | Install integrity (entry points, desktop+metainfo+icons, AppStream registration, no world-writable, ldd, sdists, version pinning) | RPM installed | ~1 s |
| **3** | First-run user setup (`get_python.sh`, `o3de.sh register`, manifest.py patch active) | regular user, network | ~3 min (first run) |
| **4** | Engine binary smoke (launcher, vulkan loader) | nothing extra | <1 s |
| **5** | Project end-to-end (`o3de create-project` + `cmake -B build/linux -S .`) | Tier 3 done, network for 3rdParty CDN | ~5–10 min |
| **6** | UI smoke (Project Manager + Editor launch under Xvfb, don't crash) | Xvfb, scrot, software Vulkan (lavapipe) for CI | ~30 s (PM only) / ~90 s (with --editor) |
| **7** *(future)* | Visual regression (pixel-diff screenshots vs baseline) | maintained baselines per Fedora version | varies |
| **8** *(future)* | Render correctness (compare rendered scene to reference) | GPU-equipped runner | varies |

Tiers 1, 2, 4 are read-only and safe on a developer machine. Tier 3 modifies `~/.o3de/` (creates the per-user venv). Tier 5 creates a temporary project that's cleaned up on exit.

## Running tests

### Against an existing install
```bash
sudo dnf install -y ./o3de-*.rpm

# Non-UI tiers
tests/integration-test.sh                          # tiers 1, 2, 4
tests/integration-test.sh --setup                  # also tier 3
tests/integration-test.sh --setup --with-project   # also tier 5

# UI smoke (tier 6) — Project Manager + (optional) Editor
sudo dnf install -y xorg-x11-server-Xvfb scrot xdpyinfo
tests/ui-smoke-test.sh                             # Project Manager smoke
tests/ui-smoke-test.sh --editor                    # also Editor scripted run
tests/ui-smoke-test.sh --editor --screenshot      # with screenshots
```

`make test`, `make test-setup`, `make test-full`, `make test-ui`, `make test-ui-full` are shortcuts for the above.

### End-to-end from a git ref
```bash
# Builds a snapshot RPM from <ref>, installs it, runs the full test suite.
# Takes hours (it's a real build).
make test-branch REF=stabilization/26050
make test-branch REF=development
make test-branch REF=v1.0.0       # any git ref
```

This is the workflow we expect O3DE engine contributors to use to validate their branches as Fedora RPMs.

### CI (GitHub Actions)

`.github/workflows/test-installed.yml` runs the test suite in clean Fedora containers (current matrix: `fedora-44`, `fedora-rawhide`) against an RPM URL — typically a COPR build artifact.

Trigger via GitHub UI ("Run workflow") with:
- **`rpm_url`** — URL of the RPM to test (e.g. `https://download.copr.fedorainfracloud.org/results/.../o3de-...rpm`)
- **`run_setup`** — also run Tier 3 (default: yes)
- **`run_project`** — also run Tier 5 (default: no, takes longer)

For automated COPR → CI integration, configure a COPR webhook that triggers this workflow with the build artifact URL. That gives the O3DE community a "branch X is healthy on Fedora" badge per build.

## Tests roadmap (what's covered today vs missing)

✅ **Today:**
- Package metadata (license, version, rpm-V)
- File presence (entry points, scripts, configs, icons, metainfo, SBOM)
- Launcher syntax + executability + shebang
- Desktop file + metainfo XML validation (`desktop-file-validate`, `appstreamcli validate-relax`)
- AppStream registration (`appstreamcli search org.o3de.O3DE`)
- StartupWMClass values (Project Manager + Editor)
- 3-component engine.json version + non-placeholder display_version
- No world-writable files in `/opt/o3de`
- Pre-built sdists for `scripts/o3de`, `Tools/LyTestTools`, `Tools/RemoteConsole/ly_remote_console`
- `ldd` clean on engine binaries
- Stage 1 system-library swap consistency (when an `o3de` RPM declares e.g. `Requires: mikkelsen`, an engine .so under `bin/Linux/profile/Default/` must actually link to `libmikktspace.so.*` — catches regressions where the spec activates the swap but cmake silently falls back to bundling)
- Project Manager window-title carries a version-shaped string (`\d+\.\d+\.\d+`) — Tier 6 regression guard for Patch0005's WindowDecorationWrapper title propagation
- get_python.sh + o3de.sh register success
- manifest.py patch active in venv
- Engine registered in user manifest
- `o3de create-project` + `cmake configure` against installed engine

❌ **Not covered (yet):**
- Compile of the sample project (currently only `cmake configure`; full build takes hours)
- Asset Processor functional test (needs assets to process)
- Full upgrade path test (install old → install new → verify state migrated)
- Cross-Fedora upgrade test (install on F44, upgrade to F45)
- Tier 7: visual regression (screenshots → pixel-diff against baselines per Fedora version) — pattern documented, not yet implemented
- Tier 8: render correctness (Vulkan render vs reference image) — needs GPU-equipped runners

The "not covered" items are tracked here so contributors can pick them up. None are blockers for a useful first version.

## Adding a new test

Append to `integration-test.sh` under the appropriate Tier section. The helpers are:

```bash
ok "<name>"                          # passing test
nope "<name>" "<reason>"             # failing test (added to summary)
nope_v "<name>" cmd arg arg          # run a command, ok if exit 0, nope on output
skipped "<name>" "<reason>"          # explicitly not run (e.g. requires --setup)
```

Tests should be:
- **Idempotent** — running twice produces the same result
- **Independent** — a Tier 2 test doesn't assume Tier 3 has run
- **Self-explanatory** — the test name is enough to understand what failed
- **Fast** — sub-second where possible; minutes for Tier 5 only

## License

Same as the repo: Apache-2.0 OR MIT.
