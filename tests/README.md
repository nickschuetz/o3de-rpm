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
| **7** | System-swap library-health check (per-swap SONAME + sample-symbol verification + engine-binary linkage smoke). Catches Fedora-version SONAME rolls + broken engine-side system-swap linkage. Does NOT cover behavior deltas (was originally an end-to-end FBX asset-bake test; rewritten 2026-05-11 after discovering SceneAPI's hard dependency on Atom RPI gem chain made the empty-scratch-project approach unworkable -- see memory `project_tier7_cold_cache_quirk.md` + upstream issue [o3de/o3de#19743](https://github.com/o3de/o3de/issues/19743) for the proper-fix design space). | RPM installed | <1 s |
| **8** | AssetProcessor runtime smoke -- spawn AP, verify at least one AssetBuilder child reaches "alive" state and sustains it across a 5s persistence window. Catches process-lifecycle bugs that pass build-time + linkage checks but fail at runtime. Caught its motivating bug retroactively: Patch0012 v1 (m_tetherLifetime / prctl) built green and shipped, then every spawned AssetBuilder got SIGTERM'd within 21 ms of fork -- this dual-sample design would have shown PIDs in sample 1 but none surviving to sample 2, failing the persistence phase immediately. | Tier 3 done (manifest exists), regular user | ~10-15 s |
| **9** | MultiplayerSample build+bake+playable-game smoke -- clone `o3de-multiplayersample` + companion `o3de-multiplayersample-assets` from the maintainer's fork (`nickschuetz/...`), auto-recover LFS objects if pointer files detected (fork-URL + batchSize=10 workaround), register gems+project against the installed engine, cmake configure + ninja-build the GameLauncher, run AssetProcessorBatch over the full project on `--platforms=linux`, smoke the launcher binary requiring a positive "Game Level Load Time:" marker in the engine's `user/log/Game.log`. Catches regressions that the cube.fbx Tier 7 health-check can't: project-build pipeline (cmake configure against installed engine, gem resolution, AzslcCompile, ShaderAssetBuilder), multi-level asset tree, and a real community game with networking/replication/gameplay scripting. Branch alignment: multiplayersample tracks O3DE's `development`; no `stabilization/26050` branch exists in multiplayersample (last was `stabilization/25100`), so the 26.05.x engine + multiplayersample-dev pairing is a known directional mismatch -- still the best signal until multiplayersample cuts a 26.05 release branch. PASSES end-to-end on Fedora 44 / NVIDIA RTX 2080 Ti / Vulkan RHI as of 2026-05-21 (loads `Levels/startmenu/startmenu.spawnable`). Depends on [o3de/o3de-multiplayersample-assets#177](https://github.com/o3de/o3de-multiplayersample-assets/pull/177) for the Linux case-sensitive material-type fix; works against Nick's fork as of `80ad5d8`. **NOT** part of `make test` (build/disk footprint); explicit-only via `make test-multiplayer-sample`. | RPM installed, ~10 GB disk, network, `git lfs`, clang/cmake/ninja | ~60-90 min cold / ~3-10 min warm |
| **10** | NewspaperDeliveryGame (Paper_Kid) build+bake+playable-game smoke -- clones from `nickschuetz/NewspaperDeliveryGame` (fork) at a pinned SHA, auto-recovers LFS objects if pointer files detected (fork-URL + batchSize=10), registers the project against the installed engine, cmake configure, runs AssetProcessorBatch over the full project on `--platforms=linux` (2-pass absorber), launcher smoke under DISPLAY with `--regset LoadLevel=CharacterSample` + `bg_ConnectToAssetProcessor=0` overrides, requires a positive "Game Level Load Time:" success marker. Sister tier to Tier 9 but a different project shape: `script_only=true` (no native C++ gem code), single-player, heavy LyShine + LandscapeCanvas + WhiteBox + EMotionFX surface. Lower cost than Tier 9 (no native link phase). PASSES end-to-end on Fedora 44 / NVIDIA RTX 2080 Ti / Vulkan RHI as of 2026-05-21 -- the test infrastructure validates a real playable game (Newspaper Delivery Game's title screen, character control, gameplay HUD: score / lives / home-time timer / newspaper count). Uses Nick's fork rather than upstream directly so the `test` branch can carry Linux-specific fixes without diverging public-facing `main`. **NOT** part of `make test`; explicit-only via `make test-newspaper-delivery`. First clean pass 2026-05-21 after [o3de/NewspaperDeliveryGame#19](https://github.com/o3de/NewspaperDeliveryGame/issues/19) (LFS-server 403) was fixed Amazon-side. | RPM installed, ~2-3 GB disk, network, clang/cmake/ninja | ~30-60 min cold-cache / ~3-10 min warm-cache |
| **11** *(future)* | Visual regression (pixel-diff screenshots vs baseline) | maintained baselines per Fedora version | varies |
| **12** *(future)* | Render correctness (compare rendered scene to reference) | GPU-equipped runner | varies |

Tiers 1, 2, 4 are read-only and safe on a developer machine. Tier 3 modifies `~/.o3de/` (creates the per-user venv). Tier 5 creates a temporary project that's cleaned up on exit.

## Running tests

### Against an existing install
```bash
sudo dnf install -y ./o3de2605-*.rpm        # or whichever o3deNNNN.rpm

# Non-UI tiers
tests/integration-test.sh                          # tiers 1, 2, 4
tests/integration-test.sh --setup                  # also tier 3
tests/integration-test.sh --setup --with-project   # also tier 5

# UI smoke (tier 6) — Project Manager + (optional) Editor
sudo dnf install -y xorg-x11-server-Xvfb scrot xdpyinfo
tests/ui-smoke-test.sh                             # Project Manager smoke
tests/ui-smoke-test.sh --editor                    # also Editor scripted run
tests/ui-smoke-test.sh --editor --screenshot      # with screenshots

# System-swap library-health check (tier 7) -- per-swap SONAME + symbol +
# engine linkage smoke for all active Stage 1 swaps. Runs in seconds.
tests/asset-bake-test.sh                           # default: auto-detect installed pkg
O3DE_PKGNAME=o3de2605 tests/asset-bake-test.sh     # explicit pkg override

# AssetProcessor runtime smoke (tier 8) -- spawn AP against a registered
# project + verify a builder reaches and sustains "alive" state across a
# 5s persistence window. Catches process-lifecycle bugs that build-time
# checks miss (e.g., Patch0012 v1's thread-death prctl misuse).
tests/ap-spawn-smoke-test.sh                       # auto-pick first manifest project
O3DE_TEST_PROJECT_PATH=/path tests/ap-spawn-smoke-test.sh   # explicit

# MultiplayerSample build+bake smoke (tier 9) -- clone the
# o3de-multiplayersample project + its companion -assets gem repo,
# register both against the installed engine, cmake configure + ninja
# build the GameLauncher, run AssetProcessorBatch for the project,
# smoke the GameLauncher under DISPLAY (when available). Long-running
# (~10-30 min cold); NOT part of `make test`.
tests/multiplayersample-build-test.sh                      # full run
MPSAMPLE_SKIP_BAKE=1 tests/multiplayersample-build-test.sh # skip the slow asset bake
MPSAMPLE_BRANCH=stabilization/25100 tests/multiplayersample-build-test.sh   # pin branch
MPSAMPLE_DIR=/path tests/multiplayersample-build-test.sh   # custom clone dir
```

`make test`, `make test-setup`, `make test-full`, `make test-ui`, `make test-ui-full`, `make test-asset-bake`, `make test-ap-spawn`, `make test-multiplayer-sample`, `make test-newspaper-delivery` are shortcuts for the above.

The test scripts auto-detect which versioned package is installed (matching `^o3de[0-9]+$` from `rpm -qa`) and derive `$ENGINE_PATH` from its installed `engine.json`. To force a specific package when multiple majors are installed (e.g., both `o3de2605` and `o3de2610`):

```bash
O3DE_PKGNAME=o3de2605 tests/integration-test.sh
O3DE_PKGNAME=o3de2610 tests/integration-test.sh
```

`O3DE_ENGINE_PATH` is also still honored for explicit engine-root overrides (legacy variable name preserved).

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
- No world-writable files in the install prefix (`/opt/O3DE/<version>/`)
- Pre-built sdists for `scripts/o3de`, `Tools/LyTestTools`, `Tools/RemoteConsole/ly_remote_console`
- `ldd` clean on engine binaries
- Stage 1 system-library swap consistency (when an `o3de` RPM declares e.g. `Requires: mikkelsen`, an engine .so under `bin/Linux/profile/Default/` must actually link to `libmikktspace.so.*` — catches regressions where the spec activates the swap but cmake silently falls back to bundling)
- Project Manager window-title carries a version-shaped string (`\d+\.\d+\.\d+`) — Tier 6 regression guard for Patch0005's WindowDecorationWrapper title propagation
- get_python.sh + o3de.sh register success
- manifest.py patch active in venv
- Engine registered in user manifest
- `o3de create-project` + `cmake configure` against installed engine
- Tier 7 asset-bake regression: drive `AssetProcessorBatch` against a known FBX (default: `Gems/AtomContent/TestData/Assets/TestData/Objects/cube/cube.fbx`), smoke the resulting `.azmodel` + `.azmaterial` for non-emptiness and AssImp-importer error cleanliness. Catches `assimp` 5 -> 6 major-version behavior deltas from the Stage 1 system swap.

❌ **Not covered (yet):**
- Compile of the sample project (currently only `cmake configure`; full build takes hours)
- Full upgrade path test (install old → install new → verify state migrated)
- Cross-Fedora upgrade test (install on F44, upgrade to F45)
- Per-field azmodel comparison vs a checked-in reference (Tier 7 today is structural-only: file-presence + size + POSITION-marker + error-log clean. Adding a vertex-count + per-channel comparison against a reference baked under bundled-assimp is the obvious next iteration)
- Tier 11: visual regression (screenshots → pixel-diff against baselines per Fedora version) — pattern documented, not yet implemented
- Tier 12: render correctness (Vulkan render vs reference image) — needs GPU-equipped runners

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
