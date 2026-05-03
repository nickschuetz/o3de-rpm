# o3de-rpm

RPM packaging for the [Open 3D Engine](https://o3de.org), targeting **Fedora 44** with **rpm 4.20+**.

The same spec produces:

- **Stable release builds** — from upstream's tagged release tarball (`o3de_<tag>_lfs.tar.gz`).
- **Snapshot builds** — from any git ref of `o3de/o3de`. Two upstream branches are common targets for this and they're *not* the same thing:
  - **`stabilization/<X>`** (e.g. `stabilization/26050`) — the pre-release stabilization branch for the next tagged release (in this case 26.05). This is what `hellaenergy/o3de-stabilization` (the community testers' channel) ships from. When O3DE upstream tags `2605.0`, this branch's tip *is* the release — so snapshots from here are functionally release candidates.
  - **`development`** — the bleeding-edge integration branch where new features land daily. Less stable than a stabilization branch; useful for engine contributors testing in-progress work, less appropriate for community testers expecting near-release quality.
  - Or any other ref — feature branches, specific commits, tags.

It also provides an extension point for bundling pre-built **O3DE 3rdParty packages** into the RPM, gated by per-package `--with` flags so you only pay for what you use.

---

## Layout

```
o3de-rpm/
├── o3de.spec                                          # the spec
├── README.md                                          # this file
├── ARCHITECTURE.md                                    # source-to-RPM flowchart + design separations
├── Makefile                                           # lint / srpm / copr / test targets
├── FEDORA_ROADMAP.md                                  # path to Fedora inclusion
├── BUNDLED_LIBRARIES.md                               # per-bundle license + migration status
├── .github/workflows/                                 # CI
│   ├── lint.yml                                       #   spec parse, rpmlint, validators
│   └── test-installed.yml                             #   integration tests against RPM URL
├── tests/                                             # post-install test suite
│   ├── README.md                                      #   tier breakdown + community usage
│   ├── integration-test.sh                            #   tiers 1–5 against installed RPM
│   ├── ui-smoke-test.sh                               #   tier 6: Project Manager + Editor smoke under Xvfb
│   └── test-branch.sh                                 #   build + install + test from git ref
└── sources/                                           # rpm SOURCES dir (sources + patches)
    ├── o3de-launcher.sh                               # /usr/bin/o3deNNNN wrapper (Project Manager / Editor GUI)
    ├── o3de-cli                                       # /usr/bin/o3deNNNN-cli wrapper (project / gem / engine management)
    ├── o3de.desktop                                   # .desktop entry (Project Manager) — mutated to <pkgname>.desktop at install
    ├── o3de.metainfo.xml                              # AppStream metainfo — id mutated to org.o3de.O3DE<NNNN> at install
    ├── o3de2605.cdx.json                              # CycloneDX SBOM (one file per major; copy + edit when 26.10 ships)
    ├── make-snapshot-tarball.sh                       # snapshot builder
    ├── o3de-{16,32,48,64,128,256}x*.png               # hicolor app icons
    ├── 0001-clang21-warning-suppressions.patch
    ├── 0002-manifest-py-engine-path-detection.patch
    ├── 0003-get-python-sh-rpm-venv-fixes.patch
    ├── 0004-lypython-non-editable-pip-for-installed-engine.patch
    ├── 0005-windowdecorationwrapper-propagate-initial-title.patch
    ├── 0006-builtinpackages-gate-mikkelsen-on-system.patch     # Stage 1 LY_USE_SYSTEM_<X> gates
    ├── 0007-tiffloader-c99-typedefs.patch                       # libtiff 4.5+ compat (deprecation)
    ├── Findmikkelsen-system.cmake                              # Stage 1 system-* find shims
    ├── Findexpat-system.cmake                                  #   (copied to cmake/3rdParty/
    ├── FindZLIB-system.cmake                                   #    during %prep when the matching
    ├── FindFreetype-system.cmake                               #    --with system_<lib> bcond is on)
    ├── FindPNG-system.cmake
    ├── FindTIFF-system.cmake
    └── FindLua-system.cmake
```

`rpmbuild` reads sources from `_sourcedir`, so build invocations point both `_sourcedir` and `_specdir` at this checkout — no copying into `~/rpmbuild/SOURCES`.

---

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the source-to-RPM flowchart and the load-bearing design separations (source mode, 3rdParty bundle toggles, system-library swaps, read-only engine + writable user state, multi-channel distribution).

---

## Build a stable release

```bash
# 1. Compute the upstream tarball SHA256 (one-time per release).
#    TAG must match `%global stable_tag` in o3de.spec — currently 2605.0.
TAG=2605.0
curl -fLO "https://github.com/o3de/o3de/releases/download/${TAG}/o3de_${TAG}_lfs.tar.gz"
sha256sum "o3de_${TAG}_lfs.tar.gz"
# Paste the hex into o3de.spec under %global stable_sha256.
mv "o3de_${TAG}_lfs.tar.gz" sources/

# 2. Build.
rpmbuild -bb \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

---

## Build from a git ref (`--with snapshot` mode)

The spec's `--with snapshot` mode builds from any git ref of `o3de/o3de` instead of an upstream-tagged release tarball. **Which COPR project the resulting RPM lands in depends on the git ref**, not on the rpm mode:

- **`stabilization/<release>`** (e.g. `stabilization/26050`, the next-release branch — currently the default `REF`) → `hellaenergy/o3de-stabilization` (the community testers' channel). Invoke with `make srpm-stabilization` / `make copr-stabilization`.
- **`development`** or a specific commit/tag → `hellaenergy/o3de-snapshot` (one-off / ad-hoc builds, no continuous tester cadence). Invoke with `make srpm-snapshot` / `make copr-snapshot`.

Both paths use `--with snapshot` under the hood; the project split is a publishing-channel choice, not a build-mode choice. See the bullets at the top of this README for the upstream-branch distinction.

```bash
# 1. Generate a reproducible snapshot tarball + checksum.
cd sources
./make-snapshot-tarball.sh stabilization/26050   # next-release branch → o3de-stabilization
# ./make-snapshot-tarball.sh development          # bleeding-edge          → o3de-snapshot
# ./make-snapshot-tarball.sh <commit-sha>         # any specific ref       → o3de-snapshot
cd ..

# 2. Paste the printed snapshot_commit / snapshot_date / snapshot_sha256
#    into the corresponding %global lines in o3de.spec.

# 3. Build.
rpmbuild -bb --with snapshot \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

The resulting version string is `<stable_tag>^<YYYYMMDD>git<shortsha>` (e.g. `2605.0^20260427gitabc1234`). The `^` separator tells `dnf` this is a *pre-release* of the next release, so upgrading from a `--with snapshot` build to the next tagged release works correctly.

---

## Build with O3DE 3rdParty packages bundled

The engine fetches its `LY_3RDPARTY_PATH` packages from O3DE's package server during cmake configure by default. To make the RPM self-contained for an offline target, drop the bundle tarball into `sources/` and pass `--with thirdparty_<name>`.

The spec ships two example toggles (`physx`, `openexr`); add more by:

1. Drop the package tarball in `sources/`, e.g. `physx-5.1.1-rev1-linux.tar.xz`.
2. Add a `%bcond_with thirdparty_<name>` line.
3. Add a matching `Source10x: <filename>` line.
4. Add an extract line in `%prep`:
   ```
   %{?with_thirdparty_<name>:tar -xf %{SOURCE10x} -C %{_builddir}/%{o3de_source_dir}/3rdParty}
   ```

Then build with any subset of toggles:

```bash
rpmbuild -bb --with thirdparty_physx --with thirdparty_openexr \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

The full list of approved package names and revisions lives in O3DE's `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake`.

---

## Build with the debug subpackage

The default build ships only the profile-config binaries (sufficient for end-user game development). To also build debug-config binaries and ship them as the `o3deNNNN-debug` subpackage (e.g. `o3de2605-debug`):

```bash
rpmbuild -bb --with debug ...
```

This roughly doubles build time (debug compiles all the same TUs at `-O0` with full symbols). End users install both with `dnf install o3de2605 o3de2605-debug` to step through engine internals; `o3de2605-debug` requires the same exact NVR of `o3de2605` so they always upgrade in lockstep. Switching the launcher between configs is a runtime concern: `O3DE_BUILD_CONFIG=debug o3de2605`.

---

## Using the installed RPM

Each major release ships as its own versioned package (`o3de2605`, `o3de2610`, …) so multiple O3DE versions can coexist. Two PATH-installed entry points per package — the examples below use 26.05.0 (`o3de2605`):

| Command | Purpose |
|---|---|
| `o3de2605` | Launches the GUI (Project Manager by default). Set `O3DE_BUILD_CONFIG=debug` for the debug-config engine if `o3de2605-debug` is also installed. |
| `o3de2605-cli` | Forwards to the upstream Python CLI at `/opt/O3DE/26.05.0/scripts/o3de.sh` for project / gem / engine management. |

The CLI covers ~25 sub-commands. Common ones:

```bash
o3de2605-cli --help                                # list sub-commands
o3de2605-cli register --this-engine                # one-time per-user setup (also runs from %post)
o3de2605-cli get-registered -df engines            # list registered engines (or projects/gems/templates)
o3de2605-cli create-project --project-path ~/MyGame --project-name MyGame
o3de2605-cli create-gem    --gem-path ~/MyGem --gem-name MyGem
o3de2605-cli enable-gem    --project-path ~/MyGame --gem-name Atom
o3de2605-cli edit-engine-properties --display-name "My Engine"
o3de2605-cli export-project   --project-path ~/MyGame   # bundle a runtime build
o3de2605-cli sha256 <file>                             # compute the hash O3DE expects in package manifests
```

State written by either command lives under `~/.o3de/` (engine registration manifest, per-user Python venvs keyed by engine path, project user data). The engine root at `/opt/O3DE/26.05.0/` is read-only.

The first launch of `o3de2605` (or first run of `o3de2605-cli`) bootstraps the per-user Python venv automatically — see `python/get_python.sh` in the engine root if you want to pre-bootstrap or inspect.

### Multiple O3DE versions on one machine

The `/opt/O3DE/<version>/` install layout matches upstream's `.deb` and Windows `.msi` exactly, so cross-platform users see the same path mental model on Fedora, Debian/Ubuntu, and Windows. dnf treats each major as an independent package:

```bash
sudo dnf install o3de2605 o3de2610            # both installed side-by-side
o3de2605                                      # launches 26.05.0 Project Manager
o3de2610                                      # launches 26.10.0 Project Manager
ls /opt/O3DE/                                 # 26.05.0  26.10.0
```

Project Manager auto-routes a project to the right engine via the project's `engine:` field in `project.json`. Subpackages follow the same versioning — `o3de2605-debug` and `o3de2610-debug` are independent and co-installable. Cross-major dnf upgrades are intentionally NOT automatic: different majors are different engine lines and you opt in explicitly with `dnf install o3de2610` when ready.

---

## Distribution

The o3de RPM has four distribution targets, in order of how soon each is reachable:

### 1. COPR — `hellaenergy/o3de*` (today, ongoing)

The interim distribution channel. Four COPR projects under the same owner, each with a distinct purpose:

- **[`hellaenergy/o3de-dependencies`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-dependencies/)** — Fedora-clean SRPMs for O3DE 3rdParty packages that aren't in Fedora proper (custom Qt 5.15-rev9, PhysX, AWSNativeSDK, azslc, mikkelsen, …). `enable_net=false`. Built first — depended on by the engine projects via `additional_repos` at build time and `runtime_dependencies` at consume time (so users get it auto-enabled when they enable any engine project).
- **[`hellaenergy/o3de`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/)** — tagged stable releases. Currently a placeholder; populated when O3DE upstream ships a release tag we package.
- **[`hellaenergy/o3de-stabilization`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/)** — pre-release validation builds from upstream's `stabilization/<release>` branch (currently `stabilization/26050`). The community testers' channel. Becomes the next tagged release when O3DE upstream tags it.
- **[`hellaenergy/o3de-snapshot`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-snapshot/)** — one-off / ad-hoc builds from upstream's `development` branch or any specific commit. Used when someone wants to test a non-stabilization ref without disrupting the regular tester channel.
- **[`hellaenergy/o3de-experimental`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-experimental/)** — in-flight Stage 1 system-library migration validation (see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) Stage 1). Not for end-user testing; internal to the packaging effort.

All three engine projects use `enable_net=true` so cmake can still fetch the four restricted bundles from `packages.o3de.org` (DXC, NvCloth, poly2tri, squish-ccr) — those four cannot be redistributed via Fedora/COPR for licensing reasons.

### 2. o3debinaries.org (eventual upstream)

The official O3DE binary distribution. The eventual goal is to upstream this spec into the O3DE source tree (likely under `cmake/Platform/Linux/Packaging/`) so O3DE's own CI can build the RPM and host it at o3debinaries.org alongside the .deb / snap / Windows packages. This reaches a much larger audience than COPR.

What needs to happen: align the spec with O3DE's existing packaging conventions, drop `hellaenergy/`-specific assumptions (the spec itself stays distribution-agnostic; `Makefile` targets stay local), get the spec accepted by O3DE upstream's release engineering team. Some of the prep work for Fedora inclusion (system-lib migration, license-clean DXC) carries over directly.

### 3. Fedora repo proper (long-term)

See [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) for the staged plan. Six stages from system-lib migration through OpenSSL 3.x port, license-clean DXC rebuild, debuginfo subpackages, and Bundling Library Exception filing, before the package review submission.

### 4. Flathub (when the Flatpak ships)

A separate effort tracked in a sibling Flatpak repo. Reuses ~80% of this repo's `sources/` and `patches/` directly. See `FLATPAK_NOTES.md` (working notes, not committed) for carryover.

To consume (end users):

```bash
sudo dnf copr enable hellaenergy/o3de-stabilization   # pre-release tester channel
sudo dnf install o3de2605                              # ~2 GB download (compressed)
o3de2605                                               # launch Project Manager (GUI)
o3de2605-cli --help                                    # CLI for project / gem / engine management
```

The package name follows a `o3deNNNN` convention (postgresql-style): `NNNN` is the upstream major as `YYMM` (`2605` for 26.05.x, `2610` for the next major). The install path under `/opt/O3DE/<DISPLAY_VERSION>/` matches what the upstream `.deb` and Windows `.msi` installers ship — same path mental model across distros and OSes.

`hellaenergy/o3de-dependencies` auto-enables alongside the engine project (via the engine project's `runtime_dependencies` setting) — no separate `dnf copr enable` needed. The per-user Python venv bootstraps on first launch automatically; pre-bootstrap manually with `/opt/O3DE/26.05.0/python/get_python.sh` if preferred.

When O3DE upstream tags a stable release, swap `o3de-stabilization` for `o3de` (the package name stays `o3de2605`; only the COPR project changes). Skip `o3de-snapshot` (one-off dev builds) and `o3de-experimental` (packaging work) unless you have a specific reason to test those.

To publish from this checkout:

```bash
make snapshot REF=stabilization/26050    # generate tarball + print pin values
$EDITOR o3de.spec                        # paste the printed snapshot_* macros
make copr-stabilization                  # SRPM → hellaenergy/o3de-stabilization (testers)
make copr-stabilization-and-test         # same + watch build + fire CI tests on success
make copr-snapshot                       # SRPM → hellaenergy/o3de-snapshot (one-off dev builds)
make copr-snapshot-and-test              # same + watch + fire CI tests
make copr-experimental                   # SRPM → hellaenergy/o3de-experimental (Stage 1 batch)
make copr-experimental-and-test          # same + watch + fire CI tests
make copr-stable                         # SRPM → hellaenergy/o3de (when tagged)
make trigger-tests BUILD_ID=N            # fire CI tests against an existing COPR build
```

A `make copr-init` target prints the one-time setup commands for all the COPR projects (chroot configs, runtime-repo-dependency, `--rpmbuild-with` flags for active Stage 1 migrations). Run `make help` for the full target list.

CI (`.github/workflows/lint.yml`) runs spec-parse (stable + snapshot + stabilization + experimental modes) + rpmlint + desktop-file-validate + appstream-util validate + shell-syntax checks on every push, against a Fedora 44 container. CI (`.github/workflows/test-installed.yml`) runs the integration test suite (Tiers 1–6) against an existing COPR RPM URL in clean F44 + rawhide containers — triggered manually, by `make trigger-tests`, or by a 4-hourly cron polling `o3de-stabilization` for new builds. The full RPM build itself is too heavy for free runners (>2 hours, 14 GB output) — the COPR projects do that.

The longer-term goal is **inclusion in Fedora proper**. The roadmap lives in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) and the per-bundle Fedora-readiness status in [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md).

---

## Testing

A tiered post-install test suite lives in [`tests/`](tests/). It exists for three audiences:

- **This repo's maintainer** — catch regressions between spec changes
- **O3DE engine contributors** — validate that your branch builds and runs as a Fedora RPM before merging
- **O3DE release engineering** — gate releases on "does this work as a packaged engine on Fedora?"

The same suite serves all three. Differences are only in *which* git ref produced the RPM under test.

### Run the suite against an installed RPM

```bash
sudo dnf install -y ./o3de2605-*.rpm                  # or whichever o3deNNNN.rpm

# Quick pass (rpm-level + install integrity + engine smoke, no state changes)
make test

# Add per-user setup (downloads the bundled-Python venv, registers the engine)
make test-setup

# Full end-to-end (also creates a project + cmake-configures it)
make test-full

# UI smoke — Project Manager launches under Xvfb without crashing
sudo dnf install -y xorg-x11-server-Xvfb scrot xorg-x11-utils
make test-ui

# UI smoke + Editor scripted automation
make test-ui-full
```

Tier 6 (UI) uses Xvfb (virtual display) and Mesa lavapipe (software Vulkan in CI containers; real GPU on user workstations). Tier 7 (visual regression) and Tier 8 (render correctness) are documented as future work in `tests/README.md`.

### Validate an arbitrary O3DE git ref end-to-end

For O3DE engine contributors who want to know "does my branch work as a Fedora RPM":

```bash
git clone https://github.com/nickschuetz/o3de-rpm
cd o3de-rpm
make test-branch REF=stabilization/26050   # or any git ref / release tag
```

This builds the snapshot tarball, patches the spec with the right pin values, runs `rpmbuild`, installs the resulting RPM, then runs the full test suite. Plan ~3–4 hours per run, ~70 GB free disk space.

### CI for community use

`.github/workflows/test-installed.yml` runs the test suite in clean Fedora containers (matrix: `fedora-44`, `fedora-rawhide`, extending to `fedora-45+` as releases ship) against an RPM URL — typically a COPR build artifact. Trigger via GitHub UI with an `rpm_url` input.

For automated COPR → CI integration, configure a COPR webhook to fire this workflow on every successful build, giving any branch a "healthy on Fedora" signal.

See [`tests/README.md`](tests/README.md) for the full tier breakdown and contribution guide.

---

## Security posture

| Concern | Mitigation |
|---|---|
| Tampered upstream tarball | `%prep` verifies `Source0` against `%global stable_sha256` (or `snapshot_sha256`) with `sha256sum -c` before extraction. |
| Tampered snapshot | `make-snapshot-tarball.sh` is reproducible (sorted, fixed mtime, numeric owner) — re-running for the same commit produces a byte-identical tarball. The committed sha256 is the binding root of trust. |
| World-writable files under `/usr` | Removed. `/opt/O3DE/<version>/` is fully read-only after install; all writable state is per-user under `~/.o3de/`. |
| Network during build | LFS objects are bundled into the source tarball before build; no `git lfs pull` runs in `%build`. O3DE's own `LY_PACKAGE_SERVER_URLS` 3rdParty fetcher still runs at cmake configure unless every needed package is pre-bundled — see "3rdParty packages" above. |
| **⚠ Bundled OpenSSL 1.1.1t (EOL since 2023-09-11)** | Not our packaging defect — upstream O3DE pins it. Tracked as a hard blocker for Fedora inclusion in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) (stage 4). Surfaced here so consumers see it clearly. |
| Hardening flags (RELRO / BIND_NOW / stack-protector / `_FORTIFY_SOURCE`) | Restored explicitly via `CMAKE_*_LINKER_FLAGS_INIT` after unsetting Fedora's CFLAGS/CXXFLAGS/LDFLAGS bundle (the bundle's annobin specs file breaks clang feature tests). O3DE's `Configurations_clang.cmake` already supplies stack-protector and `_FORTIFY_SOURCE`. |
| Runtime escalation paths | Launcher wrapper is `/usr/bin/o3deNNNN` and CLI wrapper is `/usr/bin/o3deNNNN-cli`, both mode 0755, no setuid. All `mkdir -p` targets are under `$HOME`. |
| Patch reviewability | Real `.patch` files with `From:`/`Subject:` rationales — reviewable with `git log` or `interdiff`. |
| Source provenance auditability | CycloneDX 1.6 SBOM at `/usr/share/o3deNNNN/sbom/o3deNNNN.cdx.json` documents every bundled component, with purl, license expression, and EOL flags where applicable. |
| First-run state migration | Launcher's `<project>/user/project.json` rewrite is JSON-aware (`python3 -c json.load/dump`), only mutates known legacy prefixes, and is gated by a per-prefix marker file. Failures are silenced so a malformed home dir can't block the editor. |

---

## SBOM

A static CycloneDX 1.6 JSON SBOM is committed at `sources/o3de2605.cdx.json` (one file per major; `o3de2610.cdx.json` etc. ship alongside as future majors land) and installed at `/usr/share/o3deNNNN/sbom/o3deNNNN.cdx.json`. It documents:

- The package itself (`pkg:rpm/fedora/o3deNNNN@<version>-<release>`) with its license expression and source URLs.
- Build dependencies (cmake, ninja-build, gcc-c++, python3-devel, git-lfs).
- Direct runtime dependencies (Qt5, Vulkan, mesa, libcurl, openssl, …).
- Bundled components (custom Qt 5.15-rev9, embedded clang toolchain, bundled Python — version follows the spec's `%global o3de_bundled_python` macro, currently 3.10, plus pyside2/shiboken2, OpenEXR, OpenImageIO, OpenColorIO, PhysX, etc.) — explicitly distinguished from system deps.
- **EOL flags** for bundled OpenSSL 1.1.1t.

To consume:

```bash
# After install (replace 2605 with whichever major is installed):
cyclonedx validate --input-file /usr/share/o3de2605/sbom/o3de2605.cdx.json

# Generate a runtime augmentation from the actual built RPM:
syft /opt/O3DE/26.05.0 -o cyclonedx-json
```

Re-generate the static SBOM when bumping the version: edit `sources/o3deNNNN.cdx.json` (or copy it to `sources/o3deMMMM.cdx.json` for a new major) to update `metadata.component.version`, the `version` field at the top level, the `name`/`purl`/`bom-ref` fields, and any external references.

---

## Patches

Seven patches applied via `%autosetup -p1`. See [`CONTRIBUTING.md`](CONTRIBUTING.md#patches) for the full table including each patch's upstream-worthy assessment. Quick summary:

| # | Target | Purpose |
|---|---|---|
| 0001 | `cmake/Platform/Common/Clang/Configurations_clang.cmake` | Suppress clang 21+ `-Werror` failures |
| 0002 | `scripts/o3de/o3de/manifest.py` | Honor `O3DE_ENGINE_PATH` for engine-root detection |
| 0003 | `python/get_python.sh` | Per-user venv linkage + engine-id reconciliation |
| 0004 | `cmake/LYPython.cmake` | Non-editable pip install for read-only engine roots |
| 0005 | `Code/Framework/AzQtComponents/.../WindowDecorationWrapper.cpp` | Propagate guest title to WM-drawn titlebar in `OptionDisabled` mode |
| 0006 | `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` | Establish the `LY_USE_SYSTEM_<X>` gating convention used by Stage 1 system-library swaps |
| 0007 | `Gems/Atom/Asset/ImageProcessingAtom/.../TIFFLoader.cpp` | Migrate legacy libtiff `uint32` typedef uses to standard C99 `uint32_t` (libtiff 4.5+ deprecates the legacy name) |

Each patch carries a `From:`/`Subject:` header with the rationale. Stage 1 system-library swaps additionally ship companion `Find<X>-system.cmake` shims in `sources/` (`Findmikkelsen-system.cmake`, `Findexpat-system.cmake`, `FindZLIB-system.cmake`, etc.) — installed into `cmake/3rdParty/Find<X>.cmake` during `%prep` when the matching `--with system_<lib>` is enabled.

---

## Known limitations

- O3DE's 3rdParty package fetcher still runs at cmake configure unless every package is pre-bundled. Fully hermetic offline builds (mock without `--enable-net`) require staging every package the engine pulls — see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md).
- Four upstream-bundled packages (`DirectXShaderCompilerDxc`, `NvCloth`, `poly2tri`, `squish-ccr`) cannot be hosted in Fedora or COPR for licensing reasons. The Fedora-shippable variant will need either a runtime-fetcher script or feature-gated builds — see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) § "Restricted bundles".
- Bundled OpenSSL 1.1.1t is end-of-life. Tracked for migration to system OpenSSL 3.x in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) (stage 4); likely upstream-blocked.
- `debuginfo` / `debugsource` subpackages are suppressed (`%global debug_package %{nil}`). Debug symbols are present in the binaries but not extracted into a separate package. Unblocking this is on the Fedora roadmap (stage 5).

## License

This packaging is `Apache-2.0 OR MIT` to match upstream O3DE. The packaging files (`o3de.spec`, `sources/*`, `patches/*`) are dedicated under the same dual license.
