# Fedora-inclusion roadmap

The goal: get the stable `o3de` package into the **Fedora repository proper**. Until that's reached, COPR (`hellaenergy/o3de` + `hellaenergy/o3de-snapshot`) is the interim distribution channel.

Fedora is one of **four** distribution targets the project is working toward — see the README's Distribution section for the full picture (COPR today, o3debinaries.org as the eventual upstream channel, Fedora long-term, Flathub when the Flatpak ships). Most of the work in this roadmap is shared infrastructure: the system-lib migration, OpenSSL port, and license-clean DXC rebuild all benefit the o3debinaries.org submission too. Fedora is the strictest target; if we satisfy Fedora, we satisfy everything.

This document is the staged plan, dependency map, and decision log. It lives in the repo so contributors can see the state of each blocker without spelunking through commit history.

---

## Stage 0 — COPR (interim, today)

**Status:** ✅ unblocked, in progress. Continues indefinitely as the user-facing distribution while later stages land.

**Deliverables:**
- `hellaenergy/o3de-dependencies` — Fedora-clean SRPMs for O3DE 3rdParty packages not in Fedora.
- `hellaenergy/o3de` (stable) and `hellaenergy/o3de-snapshot` (development branch) — built with `enable_net=true` so O3DE's `LY_PACKAGE_SERVER_URLS` fetcher can pull the four restricted bundles from `packages.o3de.org` (see "Restricted bundles" below).
- Spec validated end-to-end on F44 / commit `246b46f` from `stabilization/26050`.

**Status of `hellaenergy/o3de-dependencies`:** all 9 SRPMs have **succeeded builds** in COPR (verified via `copr-cli list-builds hellaenergy/o3de-dependencies`). Some required iteration — `o3de-qt5` took ten attempts before landing — but the repo is consumable today via `dnf copr enable hellaenergy/o3de-dependencies`. The remaining work for *integrating* those packages with the o3de spec (so cmake consumes them via `BuildRequires:` instead of fetching from `packages.o3de.org`) is Stage 1 below.

---

## Stage 1 — System library migration (the long tail)

**Status:** unblocked, large effort.

O3DE bundles ~30 3rdParty packages from its CDN at cmake configure time. Most of them have direct Fedora equivalents we can pivot to.

| Bundled package | Fedora package | Effort |
|---|---|---|
| zlib | `zlib-devel` | 1 cmake flag flip — `LY_BUILD_USE_SYSTEM_ZLIB=ON` (verify the var name in O3DE) |
| freetype | `freetype-devel` | 1 cmake flag flip |
| libcurl | `libcurl-devel` | 1 cmake flag flip |
| libpng | `libpng-devel` | 1 cmake flag flip |
| libtiff | `libtiff-devel` | 1 cmake flag flip |
| expat | `expat-devel` | 1 cmake flag flip |
| SQLite | `sqlite-devel` | 1 cmake flag flip |
| pcre2 | `pcre2-devel` | 1 cmake flag flip |
| Lua 5.4 | `lua-devel` | 1 cmake flag flip |
| lz4 | `lz4-devel` | 1 cmake flag flip |
| libsamplerate | `libsamplerate-devel` | 1 cmake flag flip |
| mcpp | `mcpp` | 1 cmake flag flip |
| OpenEXR | `openexr-devel` | 1 cmake flag flip; verify API version match |
| OpenImageIO | `OpenImageIO-devel` | 1 cmake flag flip; verify API version match |
| OpenColorIO | `OpenColorIO-devel` | 1 cmake flag flip |
| assimp | `assimp-devel` | 1 cmake flag flip |
| SPIRVCross | `spirv-cross-devel` | 1 cmake flag flip |
| vulkan-validationlayers | `vulkan-validation-layers-devel` | 1 cmake flag flip |
| googlebenchmark | `google-benchmark-devel` | test-only, can drop entirely |
| pyside2 | `python3-pyside2` | needs Stage 3 (Python migration) first |

Each migration is its own PR. The pattern:

1. Confirm O3DE has a `LY_BUILD_USE_SYSTEM_<name>` cmake option (or add a patch upstream if not).
2. Add the system `*-devel` to `BuildRequires`.
3. Drop the package from `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` (patch in our spec, upstream-able).
4. Build, verify auto-Requires now lists the system lib (`ldd` walks confirm the link target).
5. SBOM update.

---

## Stage 2 — Big-media bundle migration

**Status:** dependent on Stage 1 + version-checking.

OpenEXR / OpenImageIO / OpenColorIO are split out from Stage 1 because they pin specific API versions:

- O3DE bundles `OpenEXR-3.1.3-rev4-linux`. Fedora 44 ships OpenEXR 3.x. Likely compatible; verify.
- O3DE bundles `openimageio-opencolorio-2.3.17-rev2-linux`. Fedora 44 ships OIIO 3.x. **Likely API-incompatible** — needs O3DE upstream patches.

If the API gap is too large, this stage may temporarily stay bundled until O3DE upstream catches up.

---

## Stage 3 — Python migration (3.10 → system)

**Status:** unblocked, moderate effort.

Today: O3DE bundles Python 3.10.13 from `packages.o3de.org` and creates a per-user venv at `~/.o3de/Python/venv/<engine-id>/lib/python3.10/`. The launcher's `O3DE_PYTHON_VERSION` env var (default `3.10`) is already parameterized for this migration.

Target: use system Python (currently 3.13 in F44, 3.12 in RHEL 10).

**Steps:**
1. Patch `python/get_python.sh` to skip the bundled-Python download path entirely when `LY_USE_SYSTEM_PYTHON=ON` is set.
2. Patch `python/python.sh` and `python/pip.sh` to invoke `/usr/bin/python3` instead of the bundled `runtime/python-3.10.x-rev2-linux/python/bin/python3`.
3. Patch `cmake/LYPython.cmake` to honor system Python.
4. Update `requirements.txt` for any deps that pin Python 3.10 (look at PySide2 specifically — system pyside2 is on 3.13).
5. Bump `%global o3de_bundled_python` semantics: it becomes "the system Python series" instead of "the bundled Python series".
6. Validate `o3de.sh register --this-engine`, the editor launch, and Project Manager end-to-end.

**Risk:** PySide2 has been unmaintained since 2024-12. Some O3DE Python tooling depends on it. F44's `python3-pyside2` is on 5.15.x but built against 3.13. The editor's Python bindings will need patching.

---

## Stage 4 — Crypto migration (OpenSSL 1.1.1t → system 3.x)

**Status:** likely upstream-blocked.

Today: O3DE bundles OpenSSL 1.1.1t (EOL since 2023-09-11). Both COPR's policy and Fedora's are unsympathetic to vendored EOL crypto libraries.

Target: system OpenSSL 3.x.

**Why it's hard:**
- O3DE C++ code that uses OpenSSL is scattered across multiple Gems (HttpRequestor, AWSCore, etc.).
- 1.1 → 3.0 is a major API break (deprecated `EVP_*` functions, `BIO_*` changes, `SSL_*` ABI shifts).
- Each affected Gem needs porting + testing.
- Likely needs upstream cooperation; we can patch in our spec but it's a maintenance burden.

**Path forward:**
- File the migration request upstream with O3DE.
- Volunteer to do the porting work if upstream doesn't have bandwidth.
- Until done, the Fedora variant either ships affected Gems disabled or uses the runtime-fetcher pattern (see "Restricted bundles" below).

---

## Stage 5 — Compliance polish

**Status:** dependent on Stages 1–4 reaching mostly-done; some items are independent.

| Item | Description | Independent? |
|---|---|---|
| **License-clean DXC rebuild** | See dedicated section below. Highest-leverage Stage 5 task. | yes (mostly) |
| Real `-debuginfo` subpackage | Drop `%global debug_package %{nil}`; figure out why O3DE's binary layout trips rpmbuild's debug-symbol extraction; likely a `BUILD_ID` ambiguity from the Ninja Multi-Config split. May need patches to O3DE's link rules. | yes |
| `-debugsource` subpackage | Source code corresponding to each debuginfo line. Should fall out automatically once `debuginfo` works. | yes |
| Bundled Library Exception filing | Required for the custom Qt 5.15-rev9 (load-bearing). Justification doc in `BUNDLED_LIBRARIES.md`. | yes |
| Mock-clean SRPM build | `mock --rebuild o3de.src.rpm` must succeed with `--isolation=simple --no-network` enabled. | needs Stage 1 / 2 / 3 |
| Reproducible build | byte-identical RPM from the same SRPM on different hosts | needs all earlier stages |
| AppStream `<screenshots>` | Required by Flathub; nice-to-have for Fedora. Need actual editor screenshots from a working install. | yes |
| `<content_rating>` review | Currently `oars-1.1` empty (which means "no objectionable content"). Verify with O3DE upstream that no mature-content engine features need flagging. | yes |

### License-clean DXC rebuild — the critical sub-task

**Why this is on the critical path:** DXC is the only one of the four restricted bundles that's **non-optional for engine use** (see § "Restricted bundles" below — without DXC, the engine can't compile shaders). NvCloth/poly2tri/squish-ccr are all feature-gated and can be runtime-fetched (handling option B). DXC alone needs a different solution.

**The opportunity:** The licensing problem is *only* the Windows DXIL signing tooling, not DXC itself. The HLSL → SPIR-V (Vulkan) code path is fully open-source under NCSA/Apache-2.0. Linux O3DE doesn't use the DXIL path at all. So we can ship a Linux-only DXC built from upstream Microsoft sources without the DXIL bits, and it's redistributable.

**The technical context, so the work is unambiguous when we get to it:**

DXC is a fork of Clang/LLVM, not a separate project. Microsoft forked Clang ~2017 to add an HLSL frontend. Internally, DXC is structurally a full Clang/LLVM build with:
- HLSL parser/AST (alongside Clang's existing C/C++ frontend)
- DXIL backend (Windows shader format — the licensed-encumbered piece)
- SPIR-V backend (cross-platform — what we want)

This is also why the bundled DXC carries `libclang-12.so.1` and `libtinfo.so.6` — those are DXC's own internal LLVM 12 stack, RPATH-resolved from `Builders/DirectXShaderCompiler/lib/`. It's also why we need `%__requires_exclude` in the spec today.

**The migration plan (when we reach Stage 5):**

1. Build upstream Microsoft DXC (`github.com/microsoft/DirectXShaderCompiler`) from source against system clang/LLVM (Fedora 44 ships clang 22). The version we need to match is whatever O3DE's `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` pins — currently DXC `1.8.2505.1-o3de-rev3`.
2. Configure the build SPIR-V-only:
   ```
   -DENABLE_SPIRV_CODEGEN=ON
   -DSPIRV_BUILD_TESTS=OFF
   -DCLANG_INCLUDE_TESTS=OFF
   ```
   Do *not* enable any DXIL-target options.
3. Verify the resulting `libdxcompiler.so` and `dxc` binary link against system `libclang`/`libLLVM`, not bundled copies — `ldd` should show `/usr/lib64/libclang.so.*` etc.
4. Package as a new `o3de-dxc-spirv` SRPM in `hellaenergy/o3de-dependencies` (the COPR repo with `enable_net=false`). License is NCSA + Apache-2.0 with LLVM exception, both Fedora-compatible.
5. In `o3de.spec`, drop the upstream DXC fetch (remove the package from `BuiltInPackages_linux_x86_64.cmake` via patch), add `BuildRequires: o3de-dxc-spirv-devel`, and patch O3DE's cmake to find DXC via pkg-config or a `LY_DXC_PATH` cmake var.
6. **Drop** the `%__requires_exclude ^libclang-12\.so.*|^libtinfo\.so\.6.*` line from the spec (it's only there because DXC's bundled libclang/libtinfo aren't auto-Provided by rpm — system libclang from a clean rebuild *is*).

**Side benefits of completing this:**
- Eliminates the only mandatory restricted bundle, leaving NvCloth/poly2tri/squish as purely optional feature-gated bits (handling option A becomes viable).
- Drops the `__requires_exclude` workaround (one fewer thing to justify in the Fedora package review).
- Reduces the runtime-fetcher surface area dramatically — most users won't need it at all.

**Risk:** O3DE may have applied custom patches on top of upstream DXC for the `1.8.2505.1-o3de-rev3` build (the `-o3de-rev3` suffix suggests it). If those patches are non-trivial, we'd need to track them and rebase onto whatever DXC version we ship. Worth investigating early — `git log` on O3DE's DXC fork (if there is one) or the patch set inside the bundled tarball.

---

## Stage 6 — Submit to Fedora

**Status:** target.

When stages 1–5 are done:

1. Create a Fedora packager account (FAS).
2. Find a sponsor for the new package review.
3. File a Fedora Package Review bug at `bugzilla.redhat.com/enter_bug.cgi?product=Fedora&component=Package%20Review`.
4. Iterate on review feedback.
5. Once approved: `fedpkg request-repo o3de`, push to dist-git, build via Koji.

Realistic timeline from today: **9–18 months**. The crypto migration (Stage 4) is the wild card.

---

## Restricted bundles — the off-limits four

These four upstream-bundled packages **cannot** be hosted in COPR or Fedora because of license/redistribution conflicts. This is documented in `BUNDLED_LIBRARIES.md` per package, but called out here because it shapes the entire Fedora-inclusion strategy:

| Package | Why off-limits | What it enables |
|---|---|---|
| **DirectXShaderCompilerDxc** | Microsoft tooling with redistribution restrictions on DXIL signing | shader compilation — **non-optional** for engine use |
| **NvCloth** | NVIDIA proprietary, not Fedora-acceptable | the NvCloth Gem (cloth simulation) — optional |
| **poly2tri** | Specific O3DE-vendored fork has license-attribution issues | navmesh generation — significant feature |
| **squish-ccr** | Patent-encumbered texture compression algorithms | ImageProcessing Gem (asset bake) — significant |

**Three handling options for the Fedora-shippable variant:**

| Option | Description | Pro | Con |
|---|---|---|---|
| A. Disable affected Gems | Drop NvCloth Gem, replace squish with a system substitute, skip navmesh features | clean license posture | feature loss; DXC is still required so this alone isn't sufficient |
| B. Runtime fetcher | `/opt/o3de/python/fetch-restricted-deps.sh` — one-time post-install opt-in mirroring `get_python.sh`; downloads to `~/.o3de/3rdParty/` from `packages.o3de.org` | full feature set | requires user network action; some Fedora reviewers disapprove of this pattern |
| C. License-clean DXC rebuild | Build DXC from upstream NCSA/Apache-2.0 sources, configured Vulkan-only / SPIR-V-output (no Windows DXIL signing). Combined with A or B for the others. | best license posture | most engineering effort |

**Current preference:** **B** for short-term Fedora viability + **C as a follow-up** to reduce the runtime-fetch surface to just NvCloth/poly2tri/squish (all optional/feature-gated). DXC is the load-bearing one — making it license-clean is the hardest single win.

---

---

## Parallel goal — o3debinaries.org upstreaming

Independent track from Fedora-inclusion but **uses much of the same prep work**. The aim is to get the spec accepted into the upstream O3DE source tree so O3DE's own CI builds the RPM and hosts it at o3debinaries.org alongside the .deb / snap / Windows packages.

What's tractable today:
- The spec is already distribution-agnostic at the rpmbuild level. `hellaenergy/`-specific bits live in the Makefile (`copr-stable`/`copr-snapshot` targets), not in the spec or sources/. Upstream can adopt the spec verbatim.
- `make-snapshot-tarball.sh` and the patch files are similarly portable.
- The `--with snapshot` mode is what their CI would use for nightly builds; the default-mode is for tagged releases.

What's gated:
- O3DE's `cmake/Platform/Linux/Packaging/` directory may already have RPM packaging or .deb packaging conventions to align with. Need to study before submitting.
- The hellaenergy/o3de-dependencies COPR repo needs an upstream equivalent — those SRPMs (custom Qt 5.15-rev9, PhysX, AWSNativeSDK, …) need to either land at packages.o3de.org alongside the existing pre-built tarballs, or be packaged inline in the upstream spec via the `%bcond_with thirdparty_*` machinery.
- O3DE upstream's release engineering team needs to be in the loop. A pre-submission discussion in the O3DE community channel is the right starting point.

Stages 1–4 of the Fedora roadmap (system-lib migration, big-media bundles, Python migration, OpenSSL port) **all directly benefit upstreaming** — they reduce the bundled surface area, which makes the spec more maintainable upstream too. Stage 5's license-clean DXC rebuild also benefits upstream.

The submission process is much shorter than Fedora's: open a PR against the O3DE repo with the spec + sources/, get review from O3DE maintainers, iterate, merge. No FAS account, no sponsor, no Bugzilla bug — just a regular GitHub PR. Realistic timeline once Stages 1–3 are done: **2–4 months** for upstream PR review.

---

## Tracking

This document is the source of truth for stage status. Update this file (and link from PRs) whenever a stage moves forward.
