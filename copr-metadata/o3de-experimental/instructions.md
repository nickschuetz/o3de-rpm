**Use hellaenergy/o3de-stabilization for end-user testing.** This repo is for the packagers' own validation — RPMs here may have un-vetted -devel splits, system-library swaps, or other in-flight changes.

**What is this:** O3DE experimental builds — Stage 1 system-library migration work (see `BUNDLED_LIBRARIES.md` in the source repo) and other structural changes that are not ready for the o3de-stabilization testers' channel. RPMs here graduate to o3de-stabilization once validated end-to-end. The `o3de-dependencies` repo auto-enables alongside this one (no separate `dnf copr enable` needed).

The package follows a **versioned-major naming convention** (`o3de2605` for the 26.05.x line, future `o3de2610` for 26.10) installing to `/opt/O3DE/<DISPLAY_VERSION>/`, matching upstream's `.deb` and Windows `.msi` install layout. Multiple majors can be installed side-by-side. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream); the manifest at `~/.o3de/o3de_manifest.json` is single-slot for active registration — switch via `<install-prefix>/scripts/o3de.sh register --this-engine`.

**Subpackage layout** — same as o3de-stabilization: main `o3de2605` (runtime + project-build essentials, ~1.7 GB compressed); optional `o3de2605-devel` (~500 MB compressed, engine static archives for native C++ gems that static-link engine internals); optional `o3de2605-debug` (debug-config binaries — only built when `--with debug` is set, currently NOT activated in this channel). Project-build `*-devel` system packages pulled in via Recommends; opt out with `--setopt=install_weak_deps=False`.

**Currently active in this channel:**
- **Stage 1 5-pack** — engine links to system `expat`, `freetype`, `libpng`, `mikkelsen` (`libmikktspace.so.0`), `zlib` instead of bundled copies. Find-shim refactor (commits 92bde6e / cba5059 / 6b14ffa / 0ca58e8) makes the cmake target wiring play nicely with O3DE's runtime-dependency walker.
- **`o3de2605-cli` PATH wrapper** — `/usr/bin/o3de2605-cli` forwards to `/opt/O3DE/26.05.0/scripts/o3de.sh` so the upstream Python CLI (project / gem / engine management, ~25 sub-commands) is reachable on `$PATH`.
- **Versioned multi-install architecture + devel split** — packages are `o3deNNNN`; main + `-devel` subpackage; runtime `engine_name="o3de"` for gem compat.
- **Patch0007** (libtiff C99 typedef migration in TIFFLoader.cpp + Code/Editor/Util/ImageTIF.cpp) — required for any build against modern libtiff regardless of `--with system_tiff` state.

**Stage 1 batch deferrals (separate Stage 1 PR pending):**
- `system_tiff` — libtiff 4.5+'s `<tiff.h>` defines `int64`/`uint64` as `int64_t`/`uint64_t` while CryCommon's `BaseTypes.h` defines them as `slonglong`/`ulonglong` — typedef redefinition error needing a CryCommon C99 migration. Plan filed.
- `system_lua` — needs an AzCore `<Lua/lobject.h>` carry-patch (Fedora's lua-devel doesn't ship internal headers).

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
