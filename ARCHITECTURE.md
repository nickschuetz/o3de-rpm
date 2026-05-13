# Architecture

How `o3de.spec` turns the upstream Open 3D Engine source into a Fedora-installable RPM, and how that RPM behaves once installed. Intended audience: packaging contributors, reviewers evaluating the Fedora-inclusion request, and anyone debugging an unexpected build or runtime behavior.

For repo layout (which file goes where) see [`README.md`](README.md). For the per-bundle Fedora-readiness assessment see [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md). For the staged plan to inclusion see [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md).

```mermaid
flowchart TB
    subgraph SRC["Source acquisition"]
        S1["github.com/o3de/o3de releases<br/>tag tarball + LFS bundle"]
        S2["github.com/o3de/o3de.git<br/>any ref + git lfs pull"]
        SH["sources/make-snapshot-tarball.sh"]
        S2 --> SH --> SNAP["o3de-&lt;commit&gt;.tar.gz<br/>+ sha256"]
    end

    subgraph DEPS["Build-time dependencies"]
        DPK1["Fedora repos<br/>(13 Stage 1 system swaps:<br/>zlib, freetype, libpng, expat, lz4,<br/>mikkelsen, openexr, poly2tri, lua,<br/>assimp, sqlite, libsamplerate,<br/>googlebenchmark)"]
        DPK2["COPR<br/>hellaenergy/o3de-dependencies<br/>(Qt5-rev9, PhysX, AWS SDK, azslc,<br/>ISPCTexComp, astc-encoder, mikkelsen,<br/>o3de2605-spirv-cross + o3de2605-dxc-spirv + o3de2605-mcpp-az<br/>(Stage 2 PoCs, all green; o3deNNNN-<dep> naming))"]
        DPK3["packages.o3de.org CDN<br/>(remaining bundled 3rdParty:<br/>restricted bundles + as-yet-unmigrated)"]
    end

    subgraph SPEC["o3de.spec"]
        BC{"--with snapshot ?"}
        SHA["sha256sum -c verify"]
        AUTO["%autosetup -p1<br/>+ Patch0001..0009"]
        TP["%bcond_with thirdparty_*<br/>extract bundles to LY_3RDPARTY_PATH"]
        BUILD["cmake Ninja Multi-Config<br/>profile + (debug if --with debug)"]
        INST["cmake --install<br/>+ shebang normalization<br/>+ Stage 2 binary-overlay symlinks<br/>(system_spirvcross, system_dxc)"]
        DBG{"--with debug ?"}
        BC -->|no| S1
        BC -->|yes| SNAP
        S1 --> SHA
        SNAP --> SHA
        SHA --> AUTO --> TP --> BUILD --> INST
        INST --> DBG
        DPK1 -.-> BUILD
        DPK2 -.-> BUILD
        DPK3 -.-> BUILD
    end

    subgraph INSTALL["Installed layout (RPMs produced)"]
        MAIN["o3deNNNN package (e.g. o3de2605)<br/>/opt/O3DE/&lt;DISPLAY_VERSION&gt;/ (CORE + DEFAULT + profile binaries)<br/>/usr/bin/o3deNNNN + per-major .desktop + metainfo + icons + SBOM<br/>Recommends: project-build *-devel + system_X-devel<br/>Recommends: cmake (not Requires)"]
        DEVELPKG["o3deNNNN-devel subpackage<br/>(always produced)<br/>/opt/O3DE/&lt;DISPLAY_VERSION&gt;/lib/Linux/profile/Default/*.a (~178 .a)<br/>/opt/O3DE/&lt;DISPLAY_VERSION&gt;/lib64/ (Recast/Detour)<br/>Requires: o3deNNNN = same NVR"]
        DBGPKG["o3deNNNN-debug subpackage<br/>(only when --with debug)<br/>/opt/O3DE/&lt;DISPLAY_VERSION&gt;/bin/Linux/debug/"]
        DBG -->|no| MAIN
        DBG -->|yes| MAIN
        MAIN --> DEVELPKG
        DBG -->|yes| DBGPKG
    end

    subgraph RT["Runtime (per-user)"]
        WRAP["o3deNNNN wrapper<br/>O3DE_ENGINE_PATH=/opt/O3DE/&lt;DISPLAY_VERSION&gt;<br/>O3DE_PYTHON_VERSION=3.10"]
        MIG["first-run migration<br/>JSON-aware engine_path rewrite<br/>in &lt;project&gt;/user/project.json"]
        PY["~/.o3de/Python/venv/&lt;id&gt;/<br/>(get_python.sh, first run; one venv per engine path)"]
        UD["~/.o3de/user, ~/.o3de/Logs<br/>(writable state)"]
        ENG["/opt/O3DE/&lt;DISPLAY_VERSION&gt;/bin/Linux/<br/>$O3DE_BUILD_CONFIG/Default/o3de"]
        BIN --> WRAP --> ENG
        WRAP --> MIG
        WRAP --> PY
        WRAP --> UD
    end

    subgraph DIST["Distribution channels"]
        DC1A["COPR<br/>hellaenergy/o3de<br/>(stable releases)"]
        DC1B["COPR<br/>hellaenergy/o3de-stabilization<br/>(community testers -- pre-release)"]
        DC1S["COPR<br/>hellaenergy/o3de-snapshot<br/>(one-off development builds)"]
        DC1C["COPR<br/>hellaenergy/o3de-experimental<br/>(in-flight Stage 1 migrations)"]
        DC2["o3debinaries.org<br/>(upstream to O3DE CI)"]
        DC3["Fedora repo<br/>(see FEDORA_ROADMAP.md)"]
        DC4["Flathub<br/>(future, separate repo)"]
        INST -.-> DC1A
        INST -.-> DC1B
        INST -.-> DC1S
        INST -.-> DC1C
        INST -.-> DC2
        INST -.-> DC3
        INST -.-> DC4
    end

    subgraph TEST["Test gate (community-shared)"]
        T1["tests/integration-test.sh<br/>Tiers 1-5 (rpm / install / setup /<br/>engine smoke / project end-to-end)"]
        T2["tests/ui-smoke-test.sh<br/>Tier 6: Project Manager + Editor<br/>under Xvfb"]
        T4["tests/asset-bake-test.sh<br/>Tier 7: AssetProcessorBatch<br/>FBX-bake (catches assimp 5-to-6<br/>behavior deltas)"]
        T3[".github/workflows/test-installed.yml<br/>matrix: F44, rawhide, CS10, F45+, ...<br/>+ check-deps-drift.yml weekly cron"]
        DC1B -.-> T1
        DC1B -.-> T2
        DC1B -.-> T4
        DC1B -.-> T3
        DC1C -.-> T1
        DC1C -.-> T2
        DC1C -.-> T4
        DC1C -.-> T3
    end
```

## Eight separations to notice

> **Distro coverage note**: builds run against three chroots: **F44** (stable Fedora, primary production target), **fedora-rawhide** (forward-looking for the next Fedora release), and **CentOS Stream 10** (added 2026-05-08; upstream of RHEL 10, enables RHEL-derivative consumers). Each chroot exposes the engine to a different toolchain combination (F44: gcc 15 / clang 21 / glibc 2.42 / Lua 5.4; rawhide: same plus Lua 5.5; CS10: gcc 14 / clang 19+ / glibc 2.39 / Lua 5.4 / RPM 4.19 vs. F44+rawhide's RPM 6.x). Patches gated on `LUA_VERSION_NUM >= 505` (Patch0010 + Patch0011) fire only on rawhide; spec authoring conventions (e.g. escape `%%install` in comments) are driven by CS10's stricter RPM 4.19 parser. See [`project_cs10_engine_build_blockers.md`](../personal/projects/-home-nschuetz-o3de-rpm/memory/project_cs10_engine_build_blockers.md) memory note for the running CS10 toolchain compat list.

1. **Source-mode toggle** decides between a stable tarball and a reproducible snapshot tarball, but the rest of the spec is identical for both.
2. **3rdParty bundle toggles** are independent of source mode -- each `--with thirdparty_<pkg>` extracts its `Source10x` tarball into `LY_3RDPARTY_PATH` before configure.
3. **System-library swap toggles** (Stage 1, Fedora-inclusion track) -- each `--with system_<lib>` activates a Patch000N gate plus a `Find<lib>-system.cmake` stub, replacing one bundled 3rdParty package with its system equivalent. Independent of all other toggles. See [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md) for status.
4. **Read-only engine + writable user state** -- `/opt/O3DE/<version>/` is owned by root, all writable state lives in `~/.o3de/`. The launcher wrapper is the only piece that bridges them.
5. **One spec, multiple distribution channels** -- the same spec produces the binary for four COPR projects (`o3de` stable / `o3de-stabilization` community-tester / `o3de-snapshot` one-off dev builds / `o3de-experimental` in-flight migration), the upstream submission to o3debinaries.org, and (eventually) Fedora; the future Flatpak shares ~80% of the source tree (patches, launcher, snapshot helper) but uses its own manifest. The channel marker baked into the GUI version string (`-stabilization.<commit>`, `-snapshot.<commit>`, `-experimental.<commit>`, or none for stable) lets testers identify which channel a build came from at a glance.
6. **Versioned multi-install (postgresql-style at the package level; upstream-aligned at the engine level)** -- the spec parameterizes `Name:` as `o3deNNNN` (e.g. `o3de2605` for 26.05.x, `o3de2610` for the next major, derived from the spec's `stable_tag` macro) and the install prefix as `/opt/O3DE/<DISPLAY_VERSION>/` (matching upstream's `.deb` and Windows `.msi` exactly). Bumping `stable_tag` automatically produces the next major's package name and path with no other changes. Two majors install side-by-side on disk: `dnf install o3de2605 o3de2610` lands at `/opt/O3DE/26.05.0/` and `/opt/O3DE/26.10.0/` with no overlap; per-engine venvs in `~/.o3de/Python/venv/<engine-id>/` stay isolated automatically because cmake's `CalculateEnginePathId` hashes the engine root path. Subpackages (`o3deNNNN-debug`, `o3deNNNN-devel`) inherit the versioning via the standard `%{name}-debug` shorthand. **`engine.json`'s `engine_name` field is intentionally NOT versioned** -- it stays `"o3de"` (matching upstream's `.deb` default) so third-party gems' `compatible_engines` lists resolve correctly. The manifest at `~/.o3de/o3de_manifest.json` keys engine registrations by `engine_name`, so simultaneous active registration is single-slot -- users switch between installed majors via `scripts/o3de.sh register --this-engine`. Cross-major upgrades are NOT automatic -- different majors are different engine lines; users opt in explicitly.
7. **Three-source build-time dependency graph** -- Stage 1 system swaps pull from Fedora repos directly (13 active as of 2026-05-12: zlib, freetype, libpng, expat, lz4, mikkelsen, openexr, poly2tri, lua, assimp, sqlite, libsamplerate, googlebenchmark; the full 13-pack lives in `o3de-stabilization` for community testers as of the 2026-05-12 promotion alongside Patch0012 v2 AssetBuilder watchdog. CS10 (CentOS Stream 10) chroot achieved its first-ever successful engine build the same day via the `gcc-toolset-15-libatomic-devel` BR gated on `%if 0%{?rhel}`). Custom-rebuilt deps that aren't in Fedora live in the [`hellaenergy/o3de-dependencies`](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-dependencies/) COPR project: 9 production deps (Qt 5.15-rev9 with O3DE patches, PhysX 5.x, AWS SDK 1.11.361, azslc, ISPCTexComp, astc-encoder, mikkelsen, etc.) plus the three Stage 2 PoCs all ✓ green as of 2026-05-08: `o3de2605-spirv-cross` (binary shellout), `o3de2605-dxc-spirv` (binary shellout), `o3de2605-mcpp-az` (library link; first library-link variant of the Stage 2 pattern). All license-clean (Apache/BSD/MIT) but not packaged in Fedora proper, COPR-rebuilt as license-clean SRPMs for redistribution. Restricted bundles (NvCloth's NVIDIA license, squish-ccr's BC7 patent encumbrance) and the few engine deps not yet covered by either path (OpenSSL, openimageio-opencolorio, pyside2, vulkan-validationlayers per `tools/check-deps-drift.py`'s gap report) continue to flow from `packages.o3de.org`'s CDN at cmake-config time (requires `enable_net=true` on the COPR engine projects). Each Stage 1 swap that lands shifts one bundle from path #3 (CDN) -> path #1 (Fedora). Each Stage 2 PoC that lands in `o3de-dependencies` shifts one bundle from path #3 -> path #2. The endgame is path #3 holding only the genuinely-restricted bundles. Drift between paths is monitored by `tools/check-deps-drift.py` (weekly GHA cron at `.github/workflows/check-deps-drift.yml`) which posts a sticky issue on detected mismatches.

8. **Versioned-major COPR dep packages mirror upstream's CDN model** -- our `hellaenergy/o3de-dependencies` Stage 2 packages are named `o3deNNNN-<dep>` (e.g. `o3de2605-spirv-cross`, `o6de2605-dxc-spirv`, `o3de2605-mcpp-az`), with NNNN matching the engine package's `o3deNNNN` major. Each engine major's spec has `Requires:` lines for its own version of these packages, so installing `o3de2605` and a future `o3de2610` side-by-side gives each engine its own dep set without ABI skew. Mirrors Fedora's postgresql10/postgresql10-server family pattern in the main repo.

   The decision rests on three empirical observations about how upstream maintains 3rdParty packages (research recorded 2026-05-08; full notes in [`project_o3de_3p_versioning_research.md`](../personal/projects/-home-nschuetz-o3de-rpm/memory/project_o3de_3p_versioning_research.md) memory note for completeness):

   * **Cross-branch divergence is small.** Diffing `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` between `main` (last released 25.10 line, HEAD 2026-01-27), `stabilization/26050` (HEAD 2026-05-05), and `development` (HEAD 2026-05-08) shows only 1-3 line changes between any pair. Engine-team's 3p-pin update cadence is a few times per year, not per release. 26.05.x point releases (.0/.1/.2/...) all share the same pin set; same as how postgresql10 covers 10.0 through 10.23 over its support window.

   * **Upstream's CDN is "versioned keys in a single store."** Probing `packages.o3de.org`: it co-hosts versions needed by ANY active engine line (`DirectXShaderCompilerDxc-1.7.2308-o3de-rev2-linux` pinned by `main`/25.10 returns HTTP 200 alongside `1.8.2505.1-o3de-rev3-linux` pinned by stabilization/26050). Within-major-iteration supersessions get pruned (older `assimp-rev2` returns 403, replaced by `rev3`). The CDN's mental model is single-store + versioned-keys + co-existing across major lines, NOT per-major-store. `o3deNNNN-<dep>` package naming is the RPM-repo-equivalent of that pattern.

   * **`o3de/3p-package-source` has no engine-aligned branching.** Its only branches are `main` plus a `pyside6_support` feature branch. Pure rolling upstream. README explicitly recommends `FetchContent` for non-heavy 3p deps. Engine branches reaching back to old commits via point-in-time pins is the established mental model -- and our package versioning mirrors that.

   The rejected alternative was per-major COPR projects (`hellaenergy/o3de-dependencies-2605`, `hellaenergy/o3de-dependencies-2610`). Trade-off summary: the per-major-project shape would have doubled metadata maintenance overhead (5 -> 7 COPR projects), forced users to enable two repos for side-by-side installs (paying double dnf metadata-fetch cost), and diverged from upstream's single-CDN model. Versioned package names within a single project achieves the same isolation goal with none of those costs. The COPR project-scoped config audit confirmed nothing project-scoped (chroot list, enable_net, isolation, etc.) would meaningfully differ between 2605-deps and 2610-deps today, so single-project layout is also technically clean.

   **Migration semantics.** Each `o3de2605-<dep>` package carries `Obsoletes: o3de-<dep> < <new-version>` plus `Provides: o3de-<dep> = <new-version>` so any Requires line on the unversioned name keeps resolving and `dnf upgrade` transitions seamlessly. Stage 1 system swaps (`assimp`, `sqlite-libs`, etc.) are NOT renamed -- they consume Fedora-conventional package names that Fedora itself versions via SONAME conventions, and Fedora's own policy handles ABI compat. The rename applies only to packages we ship ourselves in `o3de-dependencies`.
