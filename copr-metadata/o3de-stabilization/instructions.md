**Installation:**

    sudo dnf copr enable hellaenergy/o3de-stabilization
    sudo dnf install o3de2605

The `o3de-dependencies` repo auto-enables alongside this one. Launch with `o3de2605` (Project Manager) or via the desktop entry; the upstream Python CLI is on PATH as `o3de2605-cli`.

**Upgrading from the pre-rename `o3de` package?** The package was renamed from `o3de` to `o3de2605` (versioned-major convention; install path moved from `/opt/o3de/` to `/opt/O3DE/26.05.0/`). `dnf` won't auto-replace the old package, so a clean transition needs:

    sudo dnf remove o3de                      # remove the pre-rename package first
    rm -rf ~/.o3de                            # clear stale manifest + per-engine venvs
    sudo dnf install o3de2605                 # then install the renamed package

Skip this if you're a fresh installer (you'll just get `o3de2605` directly). This note will go away once the o3de→o3de2605 cohort has fully migrated.

**Optional subpackage:** add this if you write native C++ gems with O3DE-specific APIs that need to static-link against engine internals (test framework, builder targets):

    sudo dnf install o3de2605-devel

End users running games and Lua/ScriptCanvas project authors do **not** need `-devel`. The main `o3de2605` package ships everything needed to run the Editor, build projects against the engine's `.so`s, and develop most native projects. `dnf install o3de2605` (default) also pulls in the `*-devel` system packages your project compilation needs (clang, mesa-libGL[U]-devel, libxcb-devel, fontconfig-devel, libcurl-devel, pcre2-devel, openssl-devel, libunwind-devel, libzstd-devel, vim-common, mikkelsen-devel) via Recommends; pass `--setopt=install_weak_deps=False` for a runtime-only minimal install (CI test containers, game distribution servers).

The package follows a **versioned-major naming convention** (`o3deNNNN` where NNNN is `YYMM` — `o3de2605` for the 26.05.x line, `o3de2610` for the next major). Multiple O3DE majors can be installed side-by-side: `dnf install o3de2605 o3de2610` puts them at `/opt/O3DE/26.05.0/` and `/opt/O3DE/26.10.0/` respectively, matching upstream's `.deb` and Windows `.msi` install layout. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream — third-party gems' `compatible_engines` lists resolve correctly), and the user manifest at `~/.o3de/o3de_manifest.json` keys engine registrations by name, so only ONE `o3de` engine is *registered* at a time. Switch the active engine between installed majors via `<install-prefix>/scripts/o3de.sh register --this-engine` (e.g. `/opt/O3DE/26.10.0/scripts/o3de.sh register --this-engine` to switch to 26.10).

**What is this:** Builds from O3DE upstream's **stabilization branch** (currently `stabilization/26050`, the pre-release branch for the upcoming 26.05 release). This is *not* a nightly bleeding-edge build — when O3DE tags 2605.0, this branch's tip becomes the release. Quality target: near-RC. If something breaks here, we want to know before it ships to users.

**Currently active in this channel (Stage 1 / Fedora-track):**
- **Stage 1 12-pack** -- engine links to system `expat`, `freetype`, `liblz4`, `libpng`, `mikkelsen` (`libmikktspace.so.0`), `openexr` (+ `imath`), `zlib`, `lua-libs`, `poly2tri`, `assimp`, `sqlite-libs`, `libsamplerate` instead of bundled copies. Promoted to this channel 2026-05-11 (build 10444167 succeeded on F44 + rawhide); the 7-pack subset had >1 week of community soak before this promotion. The 13th swap (`system_googlebenchmark`) is currently exercised in `o3de-experimental` and awaits a separate soak window before graduating here.

**Upstream patches MERGED this cycle** (will retire from our local patch series on next snapshot rebase):
- **[PR #19733](https://github.com/o3de/o3de/pull/19733)** (AzCore Lua include cleanup; MERGED 2026-05-08) -- our Patch0008 becomes redundant.
- **[PR #19734](https://github.com/o3de/o3de/pull/19734)** (libtiff C99 typedefs; MERGED 2026-05-08) -- our Patch0007 becomes redundant.
- **[PR #19737](https://github.com/o3de/o3de/pull/19737)** (Microphone libsamplerate PAL-trait gate; MERGED 2026-05-10) -- corresponding local patch becomes redundant.

**Lua 5.5 forward-compat** (Patch0010 + Patch0011) carries the engine through Fedora rawhide's Lua 5.5 transition. Behavior-preserving on Lua 5.4 (F44); engine compiles green on Lua 5.5 (rawhide) with `liblua-5.5.so` linkage confirmed via build 10442708 (2026-05-11).

**For bleeding-edge `development`-branch builds**, see `hellaenergy/o3de-snapshot` (one-off, ad-hoc cadence).

**Gems with system runtime dependencies:** some o3de-extras gems (ROS 2 family, AudioEngineWwise, OpenXRVk, etc.) require external system runtimes the engine RPM does not bundle. Project Manager surfaces the requirement on each gem's information icon. See [`docs/GEMS_WITH_SYSTEM_DEPS.md`](https://github.com/nickschuetz/o3de-rpm/blob/main/docs/GEMS_WITH_SYSTEM_DEPS.md) for install paths and the project-build workflow.

**Reporting issues:** https://github.com/nickschuetz/o3de-rpm/issues. Include `rpm -q o3de2605` and the COPR build ID. Engine bugs that aren't packaging-related should go upstream to https://github.com/o3de/o3de/issues.
