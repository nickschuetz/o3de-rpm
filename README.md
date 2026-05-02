# o3de-rpm

RPM packaging for the [Open 3D Engine](https://o3de.org), targeting **Fedora 44** with **rpm 4.20+**.

The same spec produces:

- **Stable release builds** — from upstream's tagged release tarball (`o3de_<tag>_lfs.tar.gz`).
- **Development snapshot builds** — from any git ref of `o3de/o3de`, for testing the `development` branch or arbitrary pre-release commits.

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
    ├── o3de-launcher.sh                               # /usr/bin/o3de wrapper (Project Manager / Editor GUI)
    ├── o3de-cli                                       # /usr/bin/o3de-cli wrapper (project / gem / engine management)
    ├── o3de.desktop                                   # .desktop entry (Project Manager)
    ├── o3de.metainfo.xml                              # AppStream metainfo
    ├── o3de.cdx.json                                  # CycloneDX SBOM
    ├── make-snapshot-tarball.sh                       # snapshot builder
    ├── o3de-{16,32,48,64,128,256}x*.png               # hicolor app icons
    ├── 0001-clang21-warning-suppressions.patch
    ├── 0002-manifest-py-engine-path-detection.patch
    ├── 0003-get-python-sh-rpm-venv-fixes.patch
    ├── 0004-lypython-non-editable-pip-for-installed-engine.patch
    ├── 0005-windowdecorationwrapper-propagate-initial-title.patch
    ├── 0006-builtinpackages-gate-mikkelsen-on-system.patch
    └── Findmikkelsen-system.cmake                     # Stage 1 system-mikkelsen find module
```

`rpmbuild` reads sources from `_sourcedir`, so build invocations point both `_sourcedir` and `_specdir` at this checkout — no copying into `~/rpmbuild/SOURCES`.

---

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the source-to-RPM flowchart and the load-bearing design separations (source mode, 3rdParty bundle toggles, system-library swaps, read-only engine + writable user state, multi-channel distribution).

---

## Build a stable release

```bash
# 1. Compute the upstream tarball SHA256 (one-time per release).
TAG=2510.2
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

## Build a development snapshot

```bash
# 1. Generate a reproducible snapshot tarball + checksum.
cd sources
./make-snapshot-tarball.sh development      # or any git ref / commit sha
cd ..

# 2. Paste the printed snapshot_commit / snapshot_date / snapshot_sha256
#    into the corresponding %global lines in o3de.spec.

# 3. Build.
rpmbuild -bb --with snapshot \
    --define "_sourcedir $PWD/sources" \
    --define "_specdir   $PWD" \
    o3de.spec
```

The snapshot version string is `<stable_tag>^<YYYYMMDD>git<shortsha>` (e.g. `2510.2^20260427gitabc1234`). The `^` separator tells `dnf` this is a *pre-release* of the next release, so upgrading `snapshot → next-stable` works correctly.

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

The default build ships only the profile-config binaries (sufficient for end-user game development). To also build debug-config binaries and ship them as the `o3de-debug` subpackage:

```bash
rpmbuild -bb --with debug ...
```

This roughly doubles build time (debug compiles all the same TUs at `-O0` with full symbols). End users install both with `dnf install o3de o3de-debug` to step through engine internals; `o3de-debug` requires the same exact NVR of `o3de` so they always upgrade in lockstep. Switching the launcher between configs is a runtime concern: `O3DE_BUILD_CONFIG=debug o3de`.

---

## Using the installed RPM

Two PATH-installed entry points:

| Command | Purpose |
|---|---|
| `o3de` | Launches the GUI (Project Manager by default). Set `O3DE_BUILD_CONFIG=debug` for the debug-config engine if `o3de-debug` is also installed. |
| `o3de-cli` | Forwards to the upstream Python CLI at `/opt/o3de/scripts/o3de.sh` for project / gem / engine management. |

The CLI covers ~25 sub-commands. Common ones:

```bash
o3de-cli --help                                # list sub-commands
o3de-cli register --this-engine                # one-time per-user setup (also runs from %post)
o3de-cli get-registered -df engines            # list registered engines (or projects/gems/templates)
o3de-cli create-project --project-path ~/MyGame --project-name MyGame
o3de-cli create-gem    --gem-path ~/MyGem --gem-name MyGem
o3de-cli enable-gem    --project-path ~/MyGame --gem-name Atom
o3de-cli edit-engine-properties --display-name "My Engine"
o3de-cli export-project   --project-path ~/MyGame   # bundle a runtime build
o3de-cli sha256 <file>                         # compute the hash O3DE expects in package manifests
```

State written by either command lives under `~/.o3de/` (engine registration manifest, per-user Python venv, project user data). The engine root at `/opt/o3de/` is read-only.

The first launch of `o3de` (or first run of `o3de-cli`) bootstraps the per-user Python venv automatically — see `python/get_python.sh` in the engine root if you want to pre-bootstrap or inspect.

---

## Distribution

The o3de RPM has four distribution targets, in order of how soon each is reachable:

### 1. COPR — `hellaenergy/o3de` (today, ongoing)

The interim distribution channel. Two COPR projects under the same owner:

- **[`hellaenergy/o3de-dependencies`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-dependencies/)** — Fedora-clean SRPMs for O3DE 3rdParty packages that aren't in Fedora proper (custom Qt 5.15-rev9, PhysX, AWSNativeSDK, azslc, …). `enable_net=false`. Built first — depended on by the next one.
- **[`hellaenergy/o3de`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/)** *(stable)* and **[`hellaenergy/o3de-snapshot`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-snapshot/)** *(development branch)* — the engine itself. `enable_net=true` so cmake can still fetch the four restricted bundles from `packages.o3de.org` (DXC, NvCloth, poly2tri, squish-ccr) — those four cannot be redistributed via Fedora/COPR for licensing reasons.

### 2. o3debinaries.org (eventual upstream)

The official O3DE binary distribution. The eventual goal is to upstream this spec into the O3DE source tree (likely under `cmake/Platform/Linux/Packaging/`) so O3DE's own CI can build the RPM and host it at o3debinaries.org alongside the .deb / snap / Windows packages. This reaches a much larger audience than COPR.

What needs to happen: align the spec with O3DE's existing packaging conventions, drop `hellaenergy/`-specific assumptions (the spec itself stays distribution-agnostic; `Makefile` targets stay local), get the spec accepted by O3DE upstream's release engineering team. Some of the prep work for Fedora inclusion (system-lib migration, license-clean DXC) carries over directly.

### 3. Fedora repo proper (long-term)

See [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) for the staged plan. Six stages from system-lib migration through OpenSSL 3.x port, license-clean DXC rebuild, debuginfo subpackages, and Bundling Library Exception filing, before the package review submission.

### 4. Flathub (when the Flatpak ships)

A separate effort tracked in a sibling Flatpak repo. Reuses ~80% of this repo's `sources/` and `patches/` directly. See `FLATPAK_NOTES.md` (working notes, not committed) for carryover.

To consume:

```bash
sudo dnf copr enable hellaenergy/o3de-dependencies
sudo dnf copr enable hellaenergy/o3de            # stable
# OR
sudo dnf copr enable hellaenergy/o3de-snapshot   # development
sudo dnf install o3de
/opt/o3de/python/get_python.sh                   # one-time per-user venv setup
o3de                                             # launch
```

To publish from this checkout:

```bash
make snapshot REF=stabilization/26050   # generate tarball + print pin values
$EDITOR o3de.spec                       # paste the printed snapshot_* macros
make copr-snapshot                      # builds SRPM, uploads to hellaenergy/o3de-snapshot
make copr-stable                        # for stable releases
```

A `make copr-init` target prints the one-time setup commands for the COPR project. Run `make help` for the full target list.

CI (`.github/workflows/lint.yml`) runs spec-parse + rpmlint + desktop-file-validate + appstream-util validate on every push, against a Fedora 44 container. The full RPM build is too heavy for free runners (>2 hours, 14 GB output) — the COPR projects do that.

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
sudo dnf install -y ./o3de-*.rpm

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
| World-writable files under `/usr` | Removed. `/opt/o3de` is fully read-only after install; all writable state is per-user under `~/.o3de/`. |
| Network during build | LFS objects are bundled into the source tarball before build; no `git lfs pull` runs in `%build`. O3DE's own `LY_PACKAGE_SERVER_URLS` 3rdParty fetcher still runs at cmake configure unless every needed package is pre-bundled — see "3rdParty packages" above. |
| **⚠ Bundled OpenSSL 1.1.1t (EOL since 2023-09-11)** | Not our packaging defect — upstream O3DE pins it. Tracked as a hard blocker for Fedora inclusion in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) (stage 4). Surfaced here so consumers see it clearly. |
| Hardening flags (RELRO / BIND_NOW / stack-protector / `_FORTIFY_SOURCE`) | Restored explicitly via `CMAKE_*_LINKER_FLAGS_INIT` after unsetting Fedora's CFLAGS/CXXFLAGS/LDFLAGS bundle (the bundle's annobin specs file breaks clang feature tests). O3DE's `Configurations_clang.cmake` already supplies stack-protector and `_FORTIFY_SOURCE`. |
| Runtime escalation paths | Launcher wrapper is `/usr/bin/o3de` and CLI wrapper is `/usr/bin/o3de-cli`, both mode 0755, no setuid. All `mkdir -p` targets are under `$HOME`. |
| Patch reviewability | Real `.patch` files with `From:`/`Subject:` rationales — reviewable with `git log` or `interdiff`. |
| Source provenance auditability | CycloneDX 1.6 SBOM at `/usr/share/o3de/sbom/o3de.cdx.json` documents every bundled component, with purl, license expression, and EOL flags where applicable. |
| First-run state migration | Launcher's `<project>/user/project.json` rewrite is JSON-aware (`python3 -c json.load/dump`), only mutates known legacy prefixes, and is gated by a per-prefix marker file. Failures are silenced so a malformed home dir can't block the editor. |

---

## SBOM

A static CycloneDX 1.6 JSON SBOM is committed at `sources/o3de.cdx.json` and shipped as part of the RPM at `/usr/share/o3de/sbom/o3de.cdx.json`. It documents:

- The package itself (`pkg:rpm/fedora/o3de@<version>-<release>`) with its license expression and source URLs.
- Build dependencies (cmake, ninja-build, gcc-c++, python3-devel, git-lfs).
- Direct runtime dependencies (Qt5, Vulkan, mesa, libcurl, openssl, …).
- Bundled components (custom Qt 5.15-rev9, embedded clang toolchain, bundled Python — version follows the spec's `%global o3de_bundled_python` macro, currently 3.10, plus pyside2/shiboken2, OpenEXR, OpenImageIO, OpenColorIO, PhysX, etc.) — explicitly distinguished from system deps.
- **EOL flags** for bundled OpenSSL 1.1.1t.

To consume:

```bash
# After install:
cyclonedx validate --input-file /usr/share/o3de/sbom/o3de.cdx.json

# Generate a runtime augmentation from the actual built RPM:
syft /opt/o3de -o cyclonedx-json
```

Re-generate the static SBOM when bumping the version: edit `sources/o3de.cdx.json` to update `metadata.component.version`, the `version` field at the top level, and any external references.

---

## Patches

Applied via `%autosetup -p1`:

| # | File | Purpose |
|---|---|---|
| 0001 | `cmake/Platform/Common/Clang/Configurations_clang.cmake` | Add `-Wno-error=deprecated-volatile` and `-Wno-error=character-conversion` so clang 21+ doesn't fail O3DE's `-Werror` build. |
| 0002 | `scripts/o3de/o3de/manifest.py` | Honor `O3DE_ENGINE_PATH` env var for engine-root detection when the o3de Python package is installed inside a venv. |
| 0003 | `python/get_python.sh` | After per-user venv creation, link `engine.json`/`o3de` site-packages into the venv, reconcile the engine-id mismatch between get_python.sh and the O3DE binary, and refresh the patched `manifest.py` into the venv. |

Each patch carries a `From:`/`Subject:` header with the rationale.

---

## Known limitations

- O3DE's 3rdParty package fetcher still runs at cmake configure unless every package is pre-bundled. Fully hermetic offline builds (mock without `--enable-net`) require staging every package the engine pulls — see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md).
- Four upstream-bundled packages (`DirectXShaderCompilerDxc`, `NvCloth`, `poly2tri`, `squish-ccr`) cannot be hosted in Fedora or COPR for licensing reasons. The Fedora-shippable variant will need either a runtime-fetcher script or feature-gated builds — see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) § "Restricted bundles".
- Bundled OpenSSL 1.1.1t is end-of-life. Tracked for migration to system OpenSSL 3.x in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md) (stage 4); likely upstream-blocked.
- `debuginfo` / `debugsource` subpackages are suppressed (`%global debug_package %{nil}`). Debug symbols are present in the binaries but not extracted into a separate package. Unblocking this is on the Fedora roadmap (stage 5).

## License

This packaging is `Apache-2.0 OR MIT` to match upstream O3DE. The packaging files (`o3de.spec`, `sources/*`, `patches/*`) are dedicated under the same dual license.
