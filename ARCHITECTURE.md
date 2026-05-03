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

    subgraph SPEC["o3de.spec"]
        BC{"--with snapshot ?"}
        SHA["sha256sum -c verify"]
        AUTO["%autosetup -p1<br/>+ Patch0001..0006"]
        TP["%bcond_with thirdparty_*<br/>extract bundles to LY_3RDPARTY_PATH"]
        BUILD["cmake Ninja Multi-Config<br/>profile + (debug if --with debug)"]
        INST["cmake --install<br/>+ shebang normalization"]
        DBG{"--with debug ?"}
        BC -->|no| S1
        BC -->|yes| SNAP
        S1 --> SHA
        SNAP --> SHA
        SHA --> AUTO --> TP --> BUILD --> INST
        INST --> DBG
    end

    subgraph INSTALL["Installed layout (RPMs produced)"]
        MAIN["o3de package<br/>/opt/o3de/ (CORE + DEFAULT + profile binaries)<br/>/usr/bin/o3de + .desktop + metainfo + icons + SBOM"]
        DBGPKG["o3de-debug subpackage<br/>(only when --with debug)<br/>/opt/o3de/bin/Linux/debug/"]
        DBG -->|no| MAIN
        DBG -->|yes| MAIN
        DBG -->|yes| DBGPKG
    end

    subgraph RT["Runtime (per-user)"]
        WRAP["o3de wrapper<br/>O3DE_ENGINE_PATH=/opt/o3de<br/>O3DE_PYTHON_VERSION=3.10"]
        MIG["first-run migration<br/>JSON-aware engine_path rewrite<br/>in &lt;project&gt;/user/project.json"]
        PY["~/.o3de/Python/venv/&lt;id&gt;/<br/>(get_python.sh, first run)"]
        UD["~/.o3de/user, ~/.o3de/Logs<br/>(writable state)"]
        ENG["/opt/o3de/bin/Linux/<br/>$O3DE_BUILD_CONFIG/Default/o3de"]
        BIN --> WRAP --> ENG
        WRAP --> MIG
        WRAP --> PY
        WRAP --> UD
    end

    subgraph DIST["Distribution channels"]
        DC1A["COPR<br/>hellaenergy/o3de<br/>(stable releases)"]
        DC1B["COPR<br/>hellaenergy/o3de-stabilization<br/>(community testers — pre-release)"]
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
        T1["tests/integration-test.sh<br/>Tiers 1–5 (rpm / install / setup /<br/>engine smoke / project end-to-end)"]
        T2["tests/ui-smoke-test.sh<br/>Tier 6: Project Manager + Editor<br/>under Xvfb"]
        T3[".github/workflows/test-installed.yml<br/>matrix: F44, rawhide, F45+, …"]
        DC1B -.-> T1
        DC1B -.-> T2
        DC1B -.-> T3
        DC1C -.-> T1
        DC1C -.-> T2
        DC1C -.-> T3
    end
```

## Five separations to notice

1. **Source-mode toggle** decides between a stable tarball and a reproducible snapshot tarball, but the rest of the spec is identical for both.
2. **3rdParty bundle toggles** are independent of source mode — each `--with thirdparty_<pkg>` extracts its `Source10x` tarball into `LY_3RDPARTY_PATH` before configure.
3. **System-library swap toggles** (Stage 1, Fedora-inclusion track) — each `--with system_<lib>` activates a Patch000N gate plus a `Find<lib>-system.cmake` stub, replacing one bundled 3rdParty package with its system equivalent. Independent of all other toggles. See [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md) for status.
4. **Read-only engine + writable user state** — `/opt/o3de` is owned by root, all writable state lives in `~/.o3de/`. The launcher wrapper is the only piece that bridges them.
5. **One spec, multiple distribution channels** — the same spec produces the binary for four COPR projects (`o3de` stable / `o3de-stabilization` community-tester / `o3de-snapshot` one-off dev builds / `o3de-experimental` in-flight migration), the upstream submission to o3debinaries.org, and (eventually) Fedora; the future Flatpak shares ~80% of the source tree (patches, launcher, snapshot helper) but uses its own manifest. The channel marker baked into the GUI version string (`-stabilization.<commit>`, `-snapshot.<commit>`, `-experimental.<commit>`, or none for stable) lets testers identify which channel a build came from at a glance.
