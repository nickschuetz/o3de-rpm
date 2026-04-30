# Contributing to o3de-rpm

This document is for **packaging contributors** — anyone who wants to change the spec, the test suite, the build flow, or the documentation. End users and engine contributors who want to test their O3DE branch as a Fedora RPM should start with [`README.md`](README.md) and [`tests/README.md`](tests/README.md) instead.

---

## What this repo is

A single RPM spec (`o3de.spec`) plus its sources/, patches/, tests/, and CI infrastructure for building and shipping the [Open 3D Engine](https://o3de.org) as an installable Fedora package. The same spec produces:

- **Stable release builds** from upstream's tagged release tarball
- **Development snapshot builds** from any git ref (branch, tag, commit) of `o3de/o3de`

via a single `--with snapshot` toggle.

The longer-term goal is inclusion in Fedora proper. The roadmap to that lives in [`FEDORA_ROADMAP.md`](FEDORA_ROADMAP.md). The per-bundle Fedora-readiness assessment lives in [`BUNDLED_LIBRARIES.md`](BUNDLED_LIBRARIES.md).

---

## Repo layout, briefly

| Path | Purpose |
|---|---|
| `o3de.spec` | the spec itself (single source of truth for the RPM) |
| `README.md` | end-user / community-tester facing |
| `CONTRIBUTING.md` | this file |
| `Makefile` | `make help` lists the targets — lint, srpm, rpm, copr, test |
| `FEDORA_ROADMAP.md` | staged plan for Fedora inclusion |
| `BUNDLED_LIBRARIES.md` | per-bundle license / version / migration status |
| `sources/` | rpm SOURCES dir (sources + patches; rpm flattens these) |
| `tests/` | post-install integration test suite (Tiers 1–8) |
| `.github/workflows/` | CI: spec lint, RPM-install tests |

Two files **deliberately excluded from git** as working notes (see `.git/info/exclude`):

| Path | Purpose |
|---|---|
| `BUILD_NOTES.md` | scratchpad of build-test findings; rolled forward across sessions, deleted when each finding becomes a permanent doc or a fix |
| `FLATPAK_NOTES.md` | carry-over notes for a future Flatpak repo — what transfers, what differs, gotchas |

---

## How the spec is structured

Read `o3de.spec` top-to-bottom. The shape is:

1. **Build-mode toggles** (`%bcond_with`) — `snapshot`, `debug_only`, `thirdparty_*`
2. **Version pinning** — `stable_tag`, `engine_cmake_version` (derived 3-component for cmake), snapshot pins
3. **rpm build behavior** — `debug_package`, payload compression, `__requires_exclude` (load-bearing for DXC's bundled libclang/libtinfo — see in-spec comment + `MEMORY.md` if applicable)
4. **Name / Version / Release** with conditional logic for snapshot mode
5. **Source0** (the upstream tarball — release URL or local snapshot)
6. **Source10–25** (auxiliary files: launcher, desktops, metainfo, icons, SBOM, snapshot helper)
7. **Patch0001–0004** applied via `%autosetup -p1`
8. **BuildRequires / Requires** — minimal, validated against auto-Requires
9. **`%prep`, `%build`, `%install`, `%check`, `%files`** — standard rpm sections
10. **Scriptlets** (`%post`, `%postun`)
11. **Changelog**

If you change *anything* in the spec or sources/, **update the README's layout block, the Mermaid diagram, and any prose section that references the changed file** — in the same commit. This is a hard rule; doc drift is treated as a regression.

---

## Patches

Four patches in `sources/`. Each carries a `From: Nick Schuetz <nschuetz@redhat.com>` and `Subject:` header explaining why the patch exists.

| # | Target | Purpose |
|---|---|---|
| 0001 | `cmake/Platform/Common/Clang/Configurations_clang.cmake` | suppress clang 21+ warnings-as-errors that O3DE's `-Werror` would otherwise fail on |
| 0002 | `scripts/o3de/o3de/manifest.py` | honor `O3DE_ENGINE_PATH` env var for engine-root detection in venv-installed setups |
| 0003 | `python/get_python.sh` | per-engine venv linkage + engine-id reconciliation + manifest.py refresh |
| 0004 | `cmake/LYPython.cmake` | install Python packages from sdists (not editable) when `INSTALLED_ENGINE` |

**Regeneration** when an upstream change makes a patch fail to apply (we hit this once on patch 0001):

1. Find a stable anchor in the source — e.g. `-Werror` rather than a specific `-Wno-*` flag whose surrounding context might rearrange.
2. Extract the upstream file from the snapshot tarball: `tar -xzOf sources/o3de-<commit>.tar.gz <commit>/path/to/file > /tmp/orig`
3. Apply the intended change to a copy: `cp /tmp/orig /tmp/patched && $EDITOR /tmp/patched`
4. Diff: `diff -u /tmp/orig /tmp/patched > sources/000N-<name>.patch`
5. Add a `From:`/`Subject:` header explaining *why*, with the rationale a reviewer will ask for.

---

## Build flow (locally)

```bash
make snapshot REF=<git-ref>      # produce sources/o3de-<commit>.tar.gz, print pin values
$EDITOR o3de.spec                # paste snapshot_commit / snapshot_date / snapshot_sha256
make rpm-snapshot                # full -bb (debug + profile, ~2-3 hours)
make rpm-snapshot                # for --with debug_only, edit Makefile or invoke rpmbuild directly
```

Or run the test harness end-to-end:

```bash
make test-branch REF=<git-ref>   # snapshot + build + install + run integration tests
```

---

## Build flow (COPR)

Two related projects under the same owner (`hellaenergy`):

- `hellaenergy/o3de-dependencies` — Fedora-clean SRPMs for non-Fedora deps (custom Qt, PhysX, AWSNativeSDK, …). Pre-built; consumed via `additional_repos`.
- `hellaenergy/o3de` (stable) and `hellaenergy/o3de-snapshot` (development) — the engine itself; `enable_net=true` so cmake can fetch the four restricted bundles (DXC, NvCloth, poly2tri, squish-ccr) from `packages.o3de.org` at build time.

Workflow:

```bash
make copr-init           # prints one-time COPR setup commands (chroots, additional_repos)
make copr-snapshot       # builds SRPM, uploads to hellaenergy/o3de-snapshot
make copr-stable         # for tagged release builds
```

---

## Testing

See [`tests/README.md`](tests/README.md) for the tier breakdown. The short version:

- `make test` — read-only checks (Tiers 1, 2, 4) — no state changes
- `make test-setup` — adds Tier 3 (per-user venv + engine register)
- `make test-full` — adds Tier 5 (project end-to-end)
- `make test-ui` — Tier 6 (Project Manager smoke under Xvfb)
- `make test-ui-full` — Tier 6 plus Editor automation
- `make test-branch REF=<git-ref>` — build snapshot from a ref + install + full test suite

When you add new behavior, **add a corresponding test in the right tier**. Tier 1–2 for installed-state invariants, Tier 3–5 for runtime behavior, Tier 6+ for UI.

---

## CI

`.github/workflows/lint.yml` runs on every push touching the spec or sources/. It runs in a Fedora 44 container and does:

- `rpmspec --parse` in both stable and snapshot modes
- `rpmlint o3de.spec`
- `desktop-file-validate` on both desktop entries
- `appstream-util validate-relax --nonet` on the metainfo
- `bash -n` on every shell source
- best-effort `patch --dry-run` against the pinned snapshot commit

`.github/workflows/test-installed.yml` runs the integration test suite in clean Fedora containers (matrix: `fedora-44`, `fedora-rawhide`, extending as Fedora releases ship) against an RPM URL — typically a COPR build artifact. Triggered manually via the GitHub UI with an `rpm_url` input, or wireable to a COPR webhook for automatic post-build verification.

The full RPM build itself is too heavy for free GitHub runners (~25 GB output, multi-hour compile). COPR does that.

---

## Commit conventions

- **Imperative-mood subject under 70 chars.** "Drop foo" not "Dropping foo" or "Dropped foo".
- **Body explains why.** Reviewers can read the diff for what changed.
- **Reference patch numbers and roadmap stages by name.** `Patch0004`, `Stage 1`, `BUNDLED_LIBRARIES.md § "Restricted (cannot be packaged…)"`.
- **No AI self-attribution.** No `Co-Authored-By: Claude…`, no "Generated with…", no AI tooling credits anywhere.
- **One logical change per commit.** A commit that touches the spec to add `BuildRequires` *and* refactors the launcher belongs as two commits.
- **README + diagram updates land with the change that requires them**, not as a follow-up.

---

## When something breaks during your work

1. **Document it in `BUILD_NOTES.md` first.** What was the symptom, what was the root cause, what was the fix. This file is excluded from git but is the source of truth for working notes that will eventually become permanent docs or PR rationale.
2. **Mirror to `FLATPAK_NOTES.md`** if the finding has Flatpak relevance (compiler quirks, library bundling, sandboxing, file paths). Both files are working notes — drop neither into git, but maintain both.
3. **Make the fix in a commit that also documents the why** in the message body.
4. **Update permanent docs (README, FEDORA_ROADMAP.md, BUNDLED_LIBRARIES.md)** if the finding shifts the roadmap or the bundled-library status.

---

## What's in scope and what isn't

**In scope:**
- Anything affecting `o3de.spec` and how it builds
- Spec patches against upstream O3DE source (`sources/000N-*.patch`)
- The launcher wrapper, desktop entries, metainfo, icons, SBOM
- Tests (Tiers 1–8) and CI workflows
- Documentation that supports any of the above

**Not in scope (different repo or upstream effort):**
- Bug fixes in the engine itself — file upstream at [github.com/o3de/o3de/issues](https://github.com/o3de/o3de/issues)
- The Flatpak (will live in a sibling repo when it's started)
- The `o3de-dependencies` SRPM specs (separate workstream; lives in COPR + a future git repo)

---

## Memory / project conventions across sessions

A few project-level conventions that don't fit elsewhere:

- **Target distros:** Fedora 44+ and RHEL 10+ only. No F43-or-earlier shims.
- **O3DE bundles a custom-patched Qt 5.15-rev9.** Never add system Qt5 BRs/Requires; the rev9 patches are load-bearing.
- **Four restricted bundles** (DXC, NvCloth, poly2tri, squish-ccr) cannot be hosted in Fedora or COPR — they come from `packages.o3de.org` via cmake at build time. See `BUNDLED_LIBRARIES.md` § "Restricted".
- **DXC is a Clang/LLVM fork** — that's why it bundles libclang-12/libtinfo. The license-clean Linux rebuild path is documented in `FEDORA_ROADMAP.md` § Stage 5.

---

## License

This packaging is `Apache-2.0 OR MIT` to match upstream O3DE.
