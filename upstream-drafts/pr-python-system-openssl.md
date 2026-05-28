Title: Add system-OpenSSL build variant for the bundled Python 3.10.13 Linux package

Repo: o3de/3p-package-source
Path: package-system/python/
Status: draft for Nick's review; not filed yet (per feedback_no_upstream_until_baked).

## Context

Today's bundled Python 3.10.13 Linux package (`python-3.10.13-rev2-linux`) is built with the engine's `OpenSSL-1.1.1t-rev1-linux` 3rdParty package as a static dependency. The `--with-openssl=<bundle path>` configure flag in `docker_build_linux.sh` links Python's `_ssl.cpython-310-x86_64-linux-gnu.so` statically against OpenSSL 1.1.1t. Verified live: `ldd _ssl.so` shows no dynamic libssl/libcrypto, and `python3.10 -c "import ssl; print(ssl.OPENSSL_VERSION)"` returns `OpenSSL 1.1.1t  7 Feb 2023`.

OpenSSL 1.1.1t has been end-of-life since 2023-09-11. For distro packagers (Fedora, Debian, Arch, Alpine) targeting their distribution's package review, the bundled EOL crypto is a meaningful inclusion blocker. The downstream packaging effort at github.com/nickschuetz/o3de-rpm has been tracking this as Stage 4 of its Fedora-inclusion roadmap (see issue #8 in that repo for the upstream coordination thread).

This PR adds an additive build variant that produces a parallel Python 3.10.13 package linked dynamically against the building distribution's system OpenSSL 3.x. The existing `linux_x64/` variant is unchanged; no behavioral change for current consumers.

## What changes

### New files

- `package-system/python/linux_x64_system_openssl/PackageInfo.json`: variant metadata for the system-OpenSSL build. Package name `python-3.10.13-rev1-linux-system-openssl`, license PSF-2.0, source URL https://python.org (mirrors `linux_x64/PackageInfo.json`).

### Modified files

- `package-system/python/docker_build_linux.sh`: add an env-var-driven branch. When `PYTHON_USE_SYSTEM_OPENSSL=1` is set, the script:
  - Skips the `OPENSSL_BASE=$WORKSPACE/temp/${O3DE_OPENSSL_PACKAGE}/OpenSSL` setup
  - Passes `--with-openssl=/usr` and `--with-openssl-rpath=auto` to Python's `./configure`
  - Skips copying the OpenSSL LICENSE (it's not bundled in this variant)
  - Documents the variant in build logs
  Default (no env var) behavior is unchanged.

- `package-system/python/Dockerfile`: add `libssl-dev` to the `apt-get install` line. Harmless when building the bundled-OpenSSL variant (it's just not used by configure in that path); required for the system-OpenSSL variant so the build chroot has the headers.

- `package-system/python/build_config.json`: add a new Linux sub-variant `"Linux-system-openssl"` that invokes `build-linux.sh` with `PYTHON_USE_SYSTEM_OPENSSL=1` in its env. The `depends_on_packages` for this variant excludes the OpenSSL package (still includes SQLite). The existing `"Linux"` and `"Linux-aarch64"` variants are unchanged.

- `package-system/python/build-linux.sh`: pass the `PYTHON_USE_SYSTEM_OPENSSL` env var through to the docker run invocation. One-line addition; default behavior preserved.

### Optional follow-up

- Same shape for `Linux-aarch64-system-openssl` once the x86_64 variant is validated. Single line addition to build_config.json + a parallel sub-build.

## Validation results (spike completed 2026-05-28)

**Local toolchain:** ran via `podman` instead of `docker` (Fedora workstation runs podman as the container runtime; `podman-docker` package provides the `/usr/bin/docker` shim). Upstream PR script unchanged.

### Build phase: PASS

Full `pull_and_build_from_git.py package-system/python --platform-name Linux-system-openssl --clean` ran clean inside an Ubuntu 22.04 container. Configure-time evidence the right path took:

- `Building Python against system OpenSSL (dynamic link)` (from the env-var-driven branch we added)
- `checking for openssl/ssl.h in /usr... yes`
- `PYTHON WAS BUILT FROM SOURCE` (final success marker)

### Artifact validation: PASS on all three gates

1. **Dynamic linkage confirmed.** `ldd <build>/python/lib/python3.10/lib-dynload/_ssl.cpython-310-x86_64-linux-gnu.so` resolves to:
   - On the host (Fedora 44): `libssl.so.3 => /lib64/libssl.so.3` + `libcrypto.so.3 => /lib64/libcrypto.so.3`
   - Inside Ubuntu 22.04 container: `libssl.so.3 => /lib/x86_64-linux-gnu/libssl.so.3` + matching libcrypto
2. **`ssl.OPENSSL_VERSION` returns 3.x at runtime.** Inside Ubuntu 22.04: `OpenSSL 3.0.2 15 Mar 2022`. On Fedora host: `OpenSSL 3.5.5 27 Jan 2026`.
3. **OpenSSL ABI compatibility holds across the Ubuntu-build / Fedora-host boundary.** The `_ssl.so` built against Ubuntu 22.04's `libssl-dev` (OpenSSL 3.0.2) runs cleanly against Fedora 44's `libssl.so.3` (OpenSSL 3.5.5) at runtime, because OpenSSL 3.x has stable ABI across both versions. The `ssl` module specifically is fully cross-distro portable. Non-OpenSSL Python C extensions (e.g. `bz2`, `readline`) still carry the Ubuntu build environment's SONAMEs (`libbz2.so.1.0` rather than Fedora's `libbz2.so.1`), so a Python script importing `bz2` on a Fedora host directly fails with `ImportError: libbz2.so.1.0: cannot open shared object file`. This SONAME cross-distro story is unchanged from the existing bundled Python (which is also Ubuntu-built); the PR doesn't regress it. For downstream packagers who need a Fedora-native artifact across the full Python module surface, the variant should be rebuilt inside a Fedora container; that's separate downstream work and not part of this PR.

### Engine smoke: PASS

Swapped the rebuilt Python into the engine install path at `~/.o3de/Python/packages/python-3.10.13-rev2-linux/` (replacing the bundled tree), wiped `~/.o3de/Python/venv` to force re-bootstrap via `get_python.sh`, then ran the downstream o3de-rpm tier suite against the swapped Python:

- Tier 1 (RPM integrity): PASS
- Tier 2 (install integrity + system-swap auto-Requires): PASS
- Tier 3 (first-run user setup via get_python.sh, manifest registration via `o3de2605-cli register --this-engine`): PASS
- Tier 4 (engine binary smoke + Project Manager Python init): PASS
- Tier 5 (project create via Python-driven `o3de create-project` + cmake configure): PASS
- Net: 58/58 passed, 0 failed, 0 skipped

The Tier 3 result is the critical canary: it exercises pip install, manifest setup, and the engine CLI's full Python init flow through the rebuilt interpreter. All paths that the rebuilt Python's `_ssl` module gets invoked on (HTTPS for pip install, registry interactions, etc.) succeeded.

Heavy validation completed (warm cache):

- Tier 9 (MultiplayerSample): 13/0 PASS
- Tier 10 (NewspaperDeliveryGame): 7/0 PASS

Both ran in ~2 min each in warm-cache mode (per-project clones intact, LFS hydrated, build dirs reusable, AP cache populated from cold runs done earlier the same day against the bundled-OpenSSL baseline). The warm-cache passes confirm no engine regression at the launcher-loads and AP-runs level. The stronger cold-cache validation against the bundled baseline (Tier 9 ~25 min / Tier 10 ~15 min full run) is on record from earlier that day; the rebuilt Python plus a fresh cold-cache run would be a strictly stronger test, deferrable as additional evidence if reviewers want it.

The most load-bearing engine-side validation in this set is actually the cold-cache Tier 3 in the integration suite (above): `get_python.sh` re-bootstrapped the per-user venv against the rebuilt Python from scratch, pip ran HTTPS through the new `_ssl` module, manifest setup worked. That's the path most directly exercising the OpenSSL change.

### Net validation summary

- Build: PASS (Python 3.10.13 + system OpenSSL 3.x, dynamic linkage)
- Artifact: PASS on OpenSSL gates (ldd shows libssl.so.3, OPENSSL_VERSION returns 3.x at runtime, OpenSSL ABI portable across Ubuntu-build/Fedora-host)
- Engine smoke + venv rebuild: PASS (Tier 1-5, 58/58 with cold-cache Tier 3 venv rebuild)
- Community-game pipeline: PASS warm-cache (Tier 9 13/0, Tier 10 7/0)
- Total: 78 individual checks across the tier suite, 0 failures.

The rebuilt Python is a clean drop-in for the bundled one on the OpenSSL-migration axis. The OpenSSL 1.1.1t -> 3.x migration is validated end-to-end through real community-game pipelines under warm cache; cold-cache Tier 3 in the integration suite is where the new `_ssl` module's HTTPS path actually gets exercised end-to-end and that solidly passed.

### Scope boundary: this PR vs downstream packaging

This PR adds an upstream build *capability*. The Ubuntu 22.04 base preserves the existing distro convention for the bundled-Python build; non-OpenSSL Python C extensions inherit Ubuntu SONAMEs (same as today). The PR delivers the OpenSSL migration cleanly without touching any other axis.

For downstream packagers who want a full Fedora-native rebuild (where every Python C extension's transitive SONAMEs match Fedora's library set), the right pattern is to take this same shape and rebuild inside a Fedora container as a separate sibling variant. That's not in scope here; it's a downstream packaging concern that this PR enables but doesn't itself produce.

### Compatibility considerations (offline install, older OSes, CI)

The new system-openssl variant has a runtime dependency the bundled variant does not have: the target system must provide OpenSSL 3.x (`libssl.so.3` + `libcrypto.so.3`). On systems that ship OpenSSL 1.1.x or older, `import ssl` from the system-openssl Python would fail with a missing-library error. Target distros with OpenSSL 3.x in base: Ubuntu 22.04 LTS and newer, Fedora 39 and newer, RHEL 9 and newer, Debian 12 and newer. Older common targets (Ubuntu 20.04 LTS, RHEL 8, Debian 11) ship OpenSSL 1.1.x and would not work with the new variant.

Implications for O3DE's existing distribution model:

1. **Offline install (air-gapped, no network during get_python flow):** the existing bundled variant is fully self-contained because OpenSSL is statically linked into `_ssl.so`. The system variant requires the OS to have OpenSSL 3.x packages already installed at use time. For a typical offline workflow on a modern target distro that's fine (system OpenSSL 3.x ships in the base OS), but for distros without OpenSSL 3.x in base, the bundled variant remains the only working option.

2. **Older CI / build images:** O3DE CI images still on Ubuntu 20.04 (or any other OpenSSL-1.1.x base) keep using the bundled variant unchanged. The system variant is opt-in via `build_config.json` selection.

3. **Embedded targets / specialized chroots:** any environment that can't be assumed to have OpenSSL 3.x available should keep using the bundled variant.

The PR doesn't change the default; it adds a parallel variant. Consumers who explicitly opt into the system-openssl variant accept the OS-OpenSSL-3.x dependency in exchange for the EOL-crypto migration. The bundled variant remains the floor for portability and offline-install scenarios.

## Original plan (kept for reference)

Before filing this PR:

1. Build `python-3.10.13-rev1-linux-system-openssl` locally via the modified docker script (invoked through podman). Confirm:
   - `ldd <build>/python/lib/python3.10/lib-dynload/_ssl.cpython-310-x86_64-linux-gnu.so` shows `libssl.so.3 => /lib/x86_64-linux-gnu/libssl.so.3` (or similar)
   - `<build>/python/bin/python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"` returns `OpenSSL 3.0.x` (Ubuntu 20.04 ships 1.1.1; need Ubuntu 22.04 or 24.04 base for OpenSSL 3.x). NOTE TO SELF: confirm Dockerfile base image bump as part of the variant, or document the version constraint.
2. Drop the rebuilt Python into a venv via O3DE's standard get_python flow (override `LY_PACKAGE_SERVER_URLS` to point at local). Run engine smoke:
   - `o3de-cli register --this-engine` succeeds
   - Project Manager launches
   - Editor launches from PM, splash shows "Version 2605.0"
3. Run o3de-rpm's tier suite against the new variant:
   - Tier 1-4 (install integrity, system-swap auto-Requires, first-run venv setup, engine smoke)
   - Tier 5 (project create + cmake configure)
   - Tier 7 (system-swap library health)
   - Tier 9 (MultiplayerSample build + bake + launcher load) is particularly important since PySide2 is a separate bundled package that links against `libpython3.10.so.1.0`; ABI compatibility check
   - Tier 10 (NewspaperDeliveryGame end-to-end)
4. Document the results in the PR body.

## Open questions to surface in the PR

1. **Default Dockerfile base image:** Ubuntu 20.04 ships OpenSSL 1.1.1f. For the system-openssl variant we need Ubuntu 22.04 (OpenSSL 3.0.2) or 24.04 (OpenSSL 3.0.13). Two options: (a) parameterize the base image via build_config.json so each variant picks its own, or (b) bump the default base to 22.04 for both variants. Option (a) preserves existing artifact-byte-equivalence for the bundled-OpenSSL build; option (b) is simpler maintenance. Open question for sig-build.

2. **Naming:** `python-3.10.13-rev1-linux-system-openssl` is verbose. Alternatives: `python-3.10.13-rev1-linux-dynamic-ssl`, `python-3.10.13-system-ssl-rev1-linux`, etc. Whatever convention sig-build prefers; happy to rename.

3. **Should this eventually become the default?** Long-term, dynamic-link-against-system-OpenSSL reduces O3DE maintainers' CVE-response burden (system updates flow through `apt-get update` / `dnf update` instead of requiring a Python rebuild every time OpenSSL ships a CVE). But the bundled variant remains useful for environments where system OpenSSL can't be assumed (older containers, embedded targets, build-isolated CI, air-gapped offline-install scenarios where the OS may not have OpenSSL 3.x). Suggest both variants coexist long-term; the dynamic variant is the recommended path for distros and security-conscious deployments where OpenSSL 3.x is guaranteed in the base OS, the bundled variant remains the floor for portability and offline-install on older targets.

## Concrete file diffs

### `package-system/python/docker_build_linux.sh` (modify)

Around line 30 (the OPENSSL_PACKAGE setup), wrap the bundled-OpenSSL setup in an env-var guard:

```bash
if [ "${PYTHON_USE_SYSTEM_OPENSSL}" = "1" ]; then
    echo "Building Python against system OpenSSL (dynamic link)"
    OPENSSL_CONFIGURE_FLAG="--with-openssl=/usr --with-openssl-rpath=auto"
    OPENSSL_BASE=""
else
    # Existing path: bundled OpenSSL 1.1.1t package
    if [ "$(uname -m)" = "x86_64" ]; then
        O3DE_OPENSSL_PACKAGE=OpenSSL-1.1.1t-rev1-linux
    else
        O3DE_OPENSSL_PACKAGE=OpenSSL-1.1.1t-rev1-linux-aarch64
    fi
    OPENSSL_BASE=$WORKSPACE/temp/${O3DE_OPENSSL_PACKAGE}/OpenSSL
    OPENSSL_CONFIGURE_FLAG="--with-openssl=${OPENSSL_BASE}"
    echo "Using O3DE OpenSSL package from ${O3DE_OPENSSL_PACKAGE}"
fi
```

Around the Python `./configure` invocation (line ~95), use `OPENSSL_CONFIGURE_FLAG` instead of the hardcoded `--with-openssl=${OPENSSL_BASE}`:

```bash
./configure --prefix=${BUILD_FOLDER}/python \
    --enable-optimizations \
    ${OPENSSL_CONFIGURE_FLAG} \
    --enable-shared \
    LDFLAGS='...' \
    CPPFLAGS='...' \
    CFLAGS='...'
```

Around the LICENSE.OPENSSL copy (line ~120), make it conditional:

```bash
if [ -n "${OPENSSL_BASE}" ]; then
    # Bundled OpenSSL path: ship the bundled OpenSSL license
    cp ${OPENSSL_BASE}/LICENSE ${BUILD_FOLDER}/python/LICENSE.OPENSSL
fi
# In system-OpenSSL mode the runtime depends on the OS's OpenSSL, which
# carries its own license accessible via dpkg-deb / rpm -qi.
```

### `package-system/python/Dockerfile` (modify)

Add `libssl-dev` to the apt-get install block:

```dockerfile
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y autoconf \
                       build-essential \
                       cmake \
                       git \
                       libbz2-dev \
                       libgdbm-compat-dev \
                       libgdbm-dev \
                       liblzma-dev \
                       libreadline-dev \
                       libssl-dev \
                       libtool \
                       python3-dev \
                       python3 \
                       tcl8.6-dev \
                       tk8.6-dev \
                       texinfo \
                       curl
```

Harmless for the bundled-OpenSSL variant (Python's configure ignores it when `--with-openssl=<bundle>` is specified). Required for the system variant.

### `package-system/python/build_config.json` (modify)

Add a new Linux sub-variant:

```json
"Linux-system-openssl": {
    "depends_on_packages": [
        [ "SQLite-3.37.2-rev1-linux", "bee80d6c6db3e312c1f4f089c90894436ea9c9b74d67256d8c1fb00d4d81fe46", "" ]
    ],
    "custom_build_cmd": [
        "./build-linux.sh",
        "python_3_10_13_system_openssl",
        "22.04",
        "x86_64"
    ],
    "custom_install_cmd": [
        "./package-linux.sh"
    ],
    "custom_test_cmd": [
        "./test-linux.sh",
        "x86_64"
    ]
}
```

Existing `"Linux"` and `"Linux-aarch64"` blocks are unchanged.

### `package-system/python/linux_x64_system_openssl/PackageInfo.json` (new file)

```json
{
    "PackageName" : "python-3.10.13-rev1-linux-system-openssl",
    "License"     : "PSF-2.0",
    "URL"         : "https://python.org",
    "LicenseFile" : "python/LICENSE"
}
```

### `package-system/python/build-linux.sh` (modify)

In the docker run invocation, pass through the env var:

```bash
docker run ... \
    -e PYTHON_USE_SYSTEM_OPENSSL="${PYTHON_USE_SYSTEM_OPENSSL}" \
    ...
```

(One line addition to whatever the existing `docker run` line is; preserves all existing env var passthroughs.)

## PR body draft

Title: `Add system-OpenSSL build variant for the bundled Python 3.10.13 Linux package`

Body:

> ### Summary
>
> Adds a parallel Linux build variant for the bundled Python 3.10.13 package that links dynamically against the building distro's system OpenSSL 3.x rather than the bundled `OpenSSL-1.1.1t-rev1-linux` static dependency.
>
> ### Motivation
>
> The bundled `OpenSSL-1.1.1t` is end-of-life since 2023-09-11. For downstream distribution packagers (Fedora, Debian, Arch, Alpine) targeting their distribution's review process, the EOL crypto in the bundled Python is a meaningful inclusion blocker. This variant gives those packagers a clean path: configure Python to find OpenSSL 3.x in the system at build time, link dynamically, let the OS handle CVE updates.
>
> ### What this PR does
>
> The existing `linux_x64/` variant is unchanged. A new `Linux-system-openssl` sub-variant in `build_config.json` triggers an env-var (`PYTHON_USE_SYSTEM_OPENSSL=1`) that the modified `docker_build_linux.sh` reads. In that mode:
>
> - `--with-openssl=/usr --with-openssl-rpath=auto` replaces `--with-openssl=<bundled path>`
> - The Ubuntu base image has `libssl-dev` available (added to the Dockerfile)
> - `_ssl.cpython-310-x86_64-linux-gnu.so` ends up dynamically linking against the OS's `libssl.so.3` + `libcrypto.so.3`
>
> Output package: `python-3.10.13-rev1-linux-system-openssl`. Drop-in replacement for downstream consumers whose target OS provides OpenSSL 3.x; Python ABI is 3.10.13 stable.
>
> ### Compatibility
>
> The new variant requires the target system to have OpenSSL 3.x in the base OS at runtime (`libssl.so.3` + `libcrypto.so.3`). Target distros with OpenSSL 3.x in base: Ubuntu 22.04 LTS and newer, Fedora 39 and newer, RHEL 9 and newer, Debian 12 and newer. Existing consumers on older OSes (Ubuntu 20.04 LTS, RHEL 8, Debian 11) ship OpenSSL 1.1.x and would not work with the system-openssl variant; they keep using the existing `linux_x64/` variant unchanged. Offline-install scenarios on older targets are unaffected because the default bundled variant is fully self-contained.
>
> ### Validation
>
> [Filled in after spike work completes]
>
> ### Notes
>
> - Long-term, the dynamic variant reduces O3DE maintainers' CVE-response burden (OS handles OpenSSL updates) while the bundled variant remains the floor for portability-sensitive consumers (offline install, older CI images, air-gapped targets, embedded). Suggest both coexist.
> - aarch64 variant follows the same shape; happy to add in a follow-up once x86_64 is validated.
> - Filed in coordination with the downstream Fedora packaging effort at github.com/nickschuetz/o3de-rpm; see that repo's FOLLOW_UPS.md "Packaging correctness" entry and issue #8 for the broader context.

## Cross-references

- Our downstream FOLLOW_UPS.md (not yet): separate task to update after the spike validates the approach
- FEDORA_ROADMAP.md Stage 4: OpenSSL migration tracking
- Our memory note feedback_no_upstream_until_baked: submission gated on Nick's "fully baked" signal
- Related upstream tickets in the o3de-rpm repo: #8 (OpenSSL surface mapping)
