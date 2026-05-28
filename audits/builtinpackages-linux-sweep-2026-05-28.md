# BuiltInPackages_linux_x86_64.cmake sweep, 2026-05-28

Snapshot inventory of every `ly_associate_package()` call in `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` against the engine source tree at `~/PROJECTS/o3de` (dev tip; superset of stabilization/26050). Status assigned against the current `o3de2605` packaging state on 26.05.0 GA.

Source file: `o3de/cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake`. Row count: 31. Six rows are multiplatform-shared (top of file), 25 are Linux-platform-specific.

## Status legend

- **swap-active** ships in `hellaenergy/o3de-stabilization` with a `system_<x>` bcond defaulted on for Fedora chroots; no bundled tarball reaches the user RPM
- **swap-parked** Stage 1 swap framework wired (bcond + Find shim + spec gates) but defaulted off pending an upstream resolution; bundled tarball still ships
- **copr-ship** rebuilt as a license-clean SRPM in `hellaenergy/o3de-dependencies`; engine consumes via `system_<x>` bcond
- **restricted-bundle** stays bundled from `packages.o3de.org` indefinitely; Bundling Library Exception filing required
- **blocked-stage-N** decision deferred until Stage N resolves; bundled today
- **unaudited** sweep finding 2026-05-28; not previously categorized in `BUNDLED_LIBRARIES.md`

## Inventory

| # | Package pin | Targets | Status | Notes |
|---|---|---|---|---|
| 1 | RapidJSON-1.1.0-rev1-multiplatform | RapidJSON | **swap-active** | Stage 1 swap landed as `system_rapidjson` in 2605.0-83. Fedora `rapidjson-devel-1.1.0^20241222git24b5e7a` is a post-1.1.0 main-branch snapshot; RapidJSON has not removed published API in the interval. Subdir layout matches engine consumers, so the find shim is trivial (no wrapper headers needed). |
| 2 | RapidXML-1.13-rev1-multiplatform | RapidXML | **swap-active** | Stage 1 swap landed as `system_rapidxml` in 2605.0-82. Fedora `rapidxml-1.13` is an exact version match. Build-time-only (header-only library; no runtime .so dependency). Find shim at `sources/FindRapidXML-system.cmake` emits four subdir-bridge wrapper headers in the build dir for the `<rapidxml/*.h>` consumer paths used by AzCore + AzNetworking. |
| 3 | pybind11-2.10.0-rev1-multiplatform | pybind11 | **unaudited** | Fedora ships `pybind11-devel-3.0.4`; engine pins 2.10. Major version bump (2.x to 3.x). 4 engine cmake consumers. Stage 1 candidate but needs API audit; pybind11 3.x removed some long-deprecated 2.x surfaces. Probably wait for upstream engine bump. |
| 4 | glad-2.0.0-beta-rev2-multiplatform | glad | **unaudited** | Fedora ships `glad-0.1.36` (glad1 generator + headers); engine bundles `glad2.0.0-beta` (different generator project). Not a drop-in substitute. Either ship glad1-generated headers (if engine permits) or keep bundled. 1 engine cmake consumer. |
| 5 | xxhash-0.7.4-rev1-multiplatform | xxhash | **swap-active** | Stage 1 swap landed as `system_xxhash` in 2605.0-84. Fedora `xxhash-devel-0.8.3` is API-compatible with 0.7. Find shim emits one subdir-bridge wrapper for `<xxhash/xxhash.h>` (engine consumer form) to `<xxhash.h>` (Fedora flat form). Header-only consumption despite Fedora packaging a real `.so`; mirrors the bundled xxhash package which also ships headers only. |
| 6 | cityhash-1.1-multiplatform | cityhash | **swap-active** (via copr-ship) | Stage 1 swap landed as `system_cityhash` in 2605.0-85. License-clean COPR rebuild as `o3de2605-cityhash` in `hellaenergy/o3de-dependencies` (build 10522180), from upstream `google/cityhash` at commit `f5dc541`. Engine consumer (AzCore Utils/TypeHash.cpp) includes `<city.h>` directly so no subdir bridge is needed. Spec wires BR/Requires/Recommends to `o3de2605-cityhash-devel` / `o3de2605-cityhash`. |
| 7 | expat-2.4.2-rev2-linux | expat | **swap-active** | `system_expat` bcond ON. Stage 1 14-pack member. |
| 8 | AWSNativeSDK-1.11.288-rev1-linux | AWSNativeSDK | **copr-ship** | `hellaenergy/o3de-dependencies/o3de-AWSNativeSDK-1.11.361` (version drift documented in BUNDLED_LIBRARIES.md cross-reference table). AWS SDK excision from core O3DE is upstream-planned (per Nick L. 2026-05-05); this bundle dissolves automatically when that lands. |
| 9 | tiff-4.2.0.15-rev3-linux | TIFF | **swap-parked, restricted-bundle effective** | Stage 1 framework wired, defaulted off after the 2026-05-05 Option A reproduction failure. Bundling Library Exception draft staged at `upstream-drafts/bundling-exception-libtiff.md`. Unblocks when upstream CryCommon C99 typedef migration lands. |
| 10 | freetype-2.11.1-rev1-linux | Freetype | **swap-active** | `system_freetype`. Stage 1 14-pack member. |
| 11 | Lua-5.4.4-rev1-linux | Lua | **swap-active** | `system_lua`. Stage 1 14-pack member; Patch0010 + Patch0011 cover Lua 5.5 forward-compat for rawhide. |
| 12 | mcpp-2.7.2_az.2-rev1-linux | mcpp | **copr-ship** (Stage 2) | `o3de2605-mcpp-az` in `hellaenergy/o3de-dependencies`; library-link variant. `system_mcpp` bcond ON. |
| 13 | mikkelsen-1.0.0.4-linux | mikkelsen | **swap-active** | `system_mikkelsen`. First Stage 1 swap shipped (PoC for the swap-pattern template). |
| 14 | googlebenchmark-1.7.0-rev1-linux | GoogleBenchmark | **swap-active** | `system_googlebenchmark`. Caught 2026-05-11 audit gap (the original PR #19738 was architecturally wrong; right path was the Stage 1 swap). |
| 15 | qt-5.15.2-rev9-linux | Qt | **restricted-bundle** | Custom rev9 patches load-bearing for editor styling. Bundling Library Exception required. Qt 6 migration is the 26.10.0 retirement path (vanilla Qt 6, system substitution viable). |
| 16 | png-1.6.37-rev2-linux | PNG | **swap-active** | `system_libpng`. Stage 1 14-pack member. |
| 17 | libsamplerate-0.2.1-rev2-linux | libsamplerate | **swap-active** | `system_libsamplerate`. Stage 1 14-pack member; PR #19737 (Microphone Gem PAL gate) landed upstream and unblocked this. |
| 18 | openimageio-opencolorio-2.3.17-rev2-linux | OpenImageIO, OpenColorIO, OpenColorIO::Runtime, OpenImageIO::Tools::Binaries, OpenImageIO::Tools::PythonPlugins | **blocked-stage-3** | Bundled; Python C Module ABI must match the editor's embedded Python. Activates when Stage 3 (Python migration) lands. |
| 19 | OpenEXR-3.1.3-rev4-linux | OpenEXR, Imath | **swap-active** | `system_openexr`. Stage 1 14-pack member; two-shim design (FindOpenEXR-system + FindImath-system). |
| 20 | OpenSSL-1.1.1t-rev1-linux | OpenSSL | **blocked-stage-4** | EOL since 2023-09-11. Upstream spike PR `o3de/3p-package-source#376` (filed 2026-05-28) rebuilds bundled Python against system OpenSSL 3.x; downstream activation waits for merge. |
| 21 | DirectXShaderCompilerDxc-1.8.2505.1-o3de-rev3-linux | DirectXShaderCompilerDxc | **copr-ship** (Stage 2) | `o3de2605-dxc-spirv` in `hellaenergy/o3de-dependencies`. License-clean rebuild shipped 2026-05-08; Stage 5 DXC exception filing dropped 2026-05-28. |
| 22 | SPIRVCross-1.3.275.0-rev1-linux | SPIRVCross | **copr-ship** (Stage 2) | `o3de2605-spirv-cross` in `hellaenergy/o3de-dependencies`. `system_spirvcross` bcond ON. |
| 23 | azslc-1.8.22-rev1-linux | azslc | **copr-ship** | `hellaenergy/o3de-dependencies/azslc-1.8.22`. Not in Fedora. |
| 24 | zlib-1.2.11-rev5-linux | ZLIB | **swap-active** | `system_zlib`. Stage 1 14-pack member. |
| 25 | squish-ccr-deb557d-rev1-linux | squish-ccr | **restricted-bundle** | BC7 patent encumbrance; cannot ship in Fedora or COPR. Audit 2026-05-07 (issue #7) confirmed. |
| 26 | astc-encoder-3.2-rev2-linux | astc-encoder | **copr-ship** | `hellaenergy/o3de-dependencies/astc-encoder-5.3.0`. ARM ASTC reference encoder; Apache-2.0. |
| 27 | ISPCTexComp-36b80aa-rev1-linux | ISPCTexComp | **copr-ship** | `hellaenergy/o3de-dependencies/ISPCTexComp-0-0.1.20230807git691513b`. Intel ISPC texture compressor; MIT. |
| 28 | lz4-1.9.4-rev2-linux | lz4 | **swap-active** | `system_lz4`. Stage 1 14-pack member. |
| 29 | pyside2-5.15.2.1-py3.10-rev7-linux | pyside2 | **blocked-stage-3** | Bundled because tied to bundled Python 3.10. F44 ships `python3-pyside2` 5.15.x built against Python 3.13; works after Stage 3. |
| 30 | SQLite-3.37.2-rev1-linux | SQLite | **swap-active** | `system_sqlite`. Stage 1 14-pack member. |
| 31 | AwsIotDeviceSdkCpp-1.15.2-rev1-linux | AwsIotDeviceSdkCpp | **copr-ship** | `hellaenergy/o3de-dependencies/aws-iot-device-sdk-cpp-v2-1.15.2`. Dep of AWSNativeSDK; same excision-path expectation. |
| 32 | vulkan-validationlayers-1.2.198-rev1-linux | vulkan-validationlayers | **swap-active** | `system_vulkan_validation_layers`. Stage 1 14-pack member; promoted 2026-05-14 via Patch0013 v4 three-hunk gate. |

## Summary counts

- **swap-active**: 18 (the original 14-pack: expat, freetype, libpng, expat, lz4, mikkelsen, openexr, poly2tri, lua, assimp, sqlite, libsamplerate, googlebenchmark, vulkan-validation-layers; plus zlib; plus the multiplatform additions rapidxml in 2605.0-82, rapidjson in -83, xxhash in -84, cityhash in -85)
- **copr-ship**: 9 (AWSNativeSDK, AwsIotDeviceSdkCpp, mcpp, DXC, SPIRVCross, azslc, astc-encoder, ISPCTexComp, plus the AwsGameliftServer dep in the COPR repo though not in this file)
- **swap-parked**: 1 (tiff)
- **restricted-bundle**: 2 (Qt 5.15-rev9, squish-ccr; tiff effectively also restricted today)
- **blocked-stage-3**: 2 (openimageio-opencolorio, pyside2)
- **blocked-stage-4**: 1 (OpenSSL)
- **unaudited**: 2 (pybind11, glad; RapidXML, RapidJSON, xxhash, cityhash promoted to swap-active in 2605.0-82, -83, -84, -85)

## Sweep findings (the 6 unaudited multiplatform deps)

Until this sweep, the `BUNDLED_LIBRARIES.md` inventory had zero rows for any of the six multiplatform-shared bundles at the top of `BuiltInPackages_linux_x86_64.cmake`. They are real, currently bundled, and have real engine consumers (1 to 5 cmake-target uses each). Recommended next steps:

| Bundle | Recommended next step | Effort |
|---|---|---|
| RapidJSON 1.1.0 | Stage 1 swap candidate; `find_package(RapidJSON)` plus `FindRapidJSON-system.cmake` shim. Header-only, low risk. | low |
| RapidXML 1.13 | Stage 1 swap candidate; exact version match in Fedora. Should be the lowest-effort flip of the six. | very low |
| pybind11 2.10.0 | Audit gap from 2.10 to Fedora 3.0.4 before deciding. Likely "wait for engine bump" rather than carry a packaging-side compat patch. | medium audit |
| glad 2.0.0-beta-rev2 | glad1 (Fedora) vs glad2 (engine) are different generators; not a drop-in. Likely keep bundled with a small exception filing, or rebuild glad2 as a COPR package. | low if exception, medium if rebuild |
| xxhash 0.7.4 | Stage 1 swap candidate; stable C ABI from 0.7 to 0.8.3. | low |
| cityhash 1.1 | NOT in Fedora. COPR-ship candidate (small, MIT). Or small exception filing. | low |

The four low-risk ones (RapidJSON, RapidXML, xxhash, cityhash) would extend the swap-active set from 14 to 17 plus add one COPR-ship if cityhash goes that way. pybind11 and glad are real audit work but not gating for 26.05.x.

## Coverage note

This sweep covered the Linux x86_64 platform file only. The engine has parallel files for other platforms (`Mac/`, `Windows/`, `iOS/`, `Android/`); they are out of scope for the Fedora packaging audit. Multiplatform-shared rows at the top of this file also drive those other platforms, but the audit lens here is Fedora-substitution feasibility.

## Cross-references

- `BUNDLED_LIBRARIES.md` is the living inventory; a follow-up commit can absorb the six unaudited rows from this sweep into its Stage 1 candidates section.
- `FEDORA_ROADMAP.md` Stage 5 exception list does not need updates from this sweep (no new exception candidates emerged; glad and cityhash are the only plausible additions and both are tiny).
- `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` is the upstream-authoritative source; re-run this sweep on any future engine snapshot pin bump that touches it.
