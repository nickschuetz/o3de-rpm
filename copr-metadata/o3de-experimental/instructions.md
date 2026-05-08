**Use [hellaenergy/o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/) for end-user testing.** This repo is for the packagers' own validation — RPMs here may have un-vetted -devel splits, system-library swaps, or other in-flight changes.

**If you're here anyway** (e.g. engine contributors validating Stage 1 migration work, or packagers debugging build issues):

    sudo dnf copr enable hellaenergy/o3de-experimental
    sudo dnf install o3de2605

The `o3de-dependencies` repo auto-enables alongside this one (no separate `dnf copr enable` needed). Add the optional `-devel` subpackage if you need engine static archives for native C++ gem development:

    sudo dnf install o3de2605-devel

**What is this:** O3DE experimental builds — Stage 1 system-library migration work (see `BUNDLED_LIBRARIES.md` in the source repo) and other structural changes that are not ready for the o3de-stabilization testers' channel. RPMs here graduate to o3de-stabilization once validated end-to-end.

The package follows a **versioned-major naming convention** (`o3de2605` for the 26.05.x line, future `o3de2610` for 26.10) installing to `/opt/O3DE/<DISPLAY_VERSION>/`, matching upstream's `.deb` and Windows `.msi` install layout. Multiple majors can be installed side-by-side. Each major's `engine.json` ships `engine_name: "o3de"` (matching upstream); the manifest at `~/.o3de/o3de_manifest.json` is single-slot for active registration — switch via `<install-prefix>/scripts/o3de.sh register --this-engine`.

**Subpackage layout** — same as o3de-stabilization: main `o3de2605` (runtime + project-build essentials, ~1.7 GB compressed); optional `o3de2605-devel` (~500 MB compressed, engine static archives for native C++ gems that static-link engine internals); optional `o3de2605-debug` (debug-config binaries — only built when `--with debug` is set, currently NOT activated in this channel). Project-build `*-devel` system packages pulled in via Recommends; opt out with `--setopt=install_weak_deps=False`.

**Currently active in this channel:**
- **Stage 1 9-pack** — engine links to system `expat`, `freetype`, `liblz4`, `mikkelsen` (`libmikktspace.so.0`), `libpng`, `openexr` (+ `imath`), `poly2tri`, `lua` (via `lua-libs`), `zlib` instead of bundled copies. **Validated end-to-end 2026-05-07**: build 10433646 succeeded on F44 + rawhide; CI passed Tiers 1+2+4+6 on both chroots. The 7-pack subset (everything except `system_lua` + `system_poly2tri`) is also live in `o3de-stabilization` as of the same day. Find-shim pattern (direct find_path/find_library, no stock-cmake-include, real INTERFACE IMPORTED 3rdParty target — keeps O3DE's runtime-dependency walker happy) is uniform across the swaps; OpenEXR uses a two-shim variant (`FindOpenEXR.cmake` + `FindImath.cmake`) because the bundled FindOpenColorIO calls `find_package(Imath)` independently of OpenEXR.
- **`system_poly2tri`** (added 2026-05-07 via Patch0009 + `Findpoly2tri-system.cmake`) — engine consumes poly2tri exclusively in `Gems/PhysX/Core/` Editor's `PolygonPrismMeshUtils` (polygon-prism shape colliders); zero refs in core `Code/`. Fedora's `poly2tri-devel` ships from Mason Green's BSD-3-Clause original tree (license-clean, independent of the bundled fork's attribution issue). Patch0009 gates `ly_associate_package(...)` in PhysX{4,5} `PAL_linux.cmake` on `LY_USE_SYSTEM_POLY2TRI`; the find shim bridges `<poly2tri.h>` to `/usr/include/poly2tri/poly2tri.h`.
- **`system_lua`** (activated 2026-05-07 via Patch0008) — drops AzCore `ScriptContext.cpp`'s redundant `#include <Lua/lobject.h>`. The only symbol consumed (`LUAI_MAXALIGN`) is already public Lua API via `luaconf.h`'s transitive include from `lauxlib.h`, so dropping the include is behavior-preserving. Same patch submitted upstream as o3de/o3de PR #19733 (approved by nick-l-o3de 2026-05-07, awaiting maintainer merge); when that lands, our Patch0008 becomes redundant.
- **`o3de2605-cli` PATH wrapper** — `/usr/bin/o3de2605-cli` forwards to `/opt/O3DE/26.05.0/scripts/o3de.sh` so the upstream Python CLI (project / gem / engine management, ~25 sub-commands) is reachable on `$PATH`.
- **Versioned multi-install architecture + devel split** — packages are `o3deNNNN`; main + `-devel` subpackage; runtime `engine_name="o3de"` for gem compat.
- **Patch0007** (libtiff C99 typedef migration in TIFFLoader.cpp + Code/Editor/Util/ImageTIF.cpp) — required for any build against modern libtiff regardless of `--with system_tiff` state.

**Stage 1 status of remaining bundles:**
- `system_tiff` — **OPTION C (Bundling Library Exception path, decided 2026-05-05).** Patch attempt at narrow guard (commit `cda6b7b`) failed because CryCommon's own internal headers (`Cry_ValidNumber.h`'s DoubleU64 macros) use `uint64` directly, transitively included from `EditorDefs.h` before `<tiffio.h>` brings libtiff's typedef into scope. Reordering the includes ABI-mismatches at link time. Engine-wide CryCommon C99 migration ruled out as out-of-scope. Bundle stays.
- **assimp** + **SQLite** + **libsamplerate** + **googlebenchmark** — all audited 2026-05-07 and confirmed Stage-1-swappable (clean candidates with various nuances). Pending implementation; not yet activated. See [`BUNDLED_LIBRARIES.md`](https://github.com/nickschuetz/o3de-rpm/blob/main/BUNDLED_LIBRARIES.md) for per-bundle audit findings.

**Stage 2 binary-only / DXC-class deps (sibling track to Stage 1):**
- **SPIRV-Cross PoC ✓ green (2026-05-07)** — `o3de-spirv-cross-1.3.275.0-1.rev2` is built and signed in `hellaenergy/o3de-dependencies`. License-clean rebuild from KhronosGroup at tag `vulkan-sdk-1.3.275.0`, Apache-2.0 OR MIT. 976KB compressed RPM ships `/usr/bin/spirv-cross`.
- **DXC PoC iterating** — `o3de-dxc-spirv` PoC building from `o3de/DirectXShaderCompiler` at tag `release-1.8.2505.1-o3de`. Reached step 1106/1111 (99.5%) in the build pipeline; final cmake-link issue with system SPIRV-Tools transitive deps still being worked out.

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
