**You probably don't need to enable this repo directly.** It's auto-enabled by any of the four engine COPR projects ([o3de](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de/), [o3de-stabilization](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-stabilization/), [o3de-snapshot](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-snapshot/), [o3de-experimental](https://copr.fedorainfracloud.org/coprs/hellaenergy/o3de-experimental/)) via their `external_repos` configuration. When you `dnf copr enable hellaenergy/o3de2605` (or any sibling), `dnf` pulls deps from here automatically.

**If you want to enable it standalone** (e.g. you're packaging your own O3DE-derived project against this dependency stack):

    sudo dnf copr enable hellaenergy/o3de-dependencies

**What is this:** license-clean Linux COPR rebuilds of the Open 3D Engine 3rdParty packages that aren't packaged in Fedora proper but are needed by the engine. Each package's source is `o3de/3p-package-source/<package>/build_config.json`'s `git_url` + `git_tag`; we rebuild from those upstream sources rather than redistributing the prebuilt tarballs O3DE ships at packages.o3de.org.

**Currently shipped (~12 packages):**

- **o3de-qt5** (5.15.2-rev9) -- O3DE's custom-patched Qt 5.15. LGPL-3.0 / GPL-3.0 (Qt) + Apache-2.0 (rev9 patches). Required because the bundled rev9 patches are load-bearing (system Qt5 cannot substitute).
- **PhysX** (5.x) -- BSD-3-Clause. Open-source since NVIDIA's 2022 release; not in Fedora.
- **o3de-AWSNativeSDK**, **aws-iot-device-sdk-cpp-v2**, **aws-gamelift-server-sdk** -- Apache-2.0. Specific versions O3DE pins; not in Fedora.
- **azslc** (1.8.x) -- Apache-2.0. O3DE's shader language compiler.
- **ISPCTexComp** -- MIT. Intel ISPC texture compressor.
- **astc-encoder** (3.2-rev2) -- Apache-2.0. ARM ASTC reference encoder.
- **mikkelsen** (1.0.0.4) -- Public domain. Tangent-space generator (Morten Mikkelsen).
- **o3de-spirv-cross** (1.3.275.0) -- Apache-2.0 / MIT. KhronosGroup SPIR-V to GLSL/HLSL/MSL cross-compiler. Engine shells out to `/usr/bin/spirv-cross` at asset-build time. ✓ Green as of 2026-05-07.
- **o3de-dxc-spirv** (1.8.2505.1-o3de) -- NCSA + Apache-2.0 (LLVM exception). Microsoft DirectXShaderCompiler (HLSL to SPIR-V), o3de fork at tag `release-1.8.2505.1-o3de`. Linux/SPIR-V-only build (no Windows DXIL signing tooling). Engine shells out to `/usr/bin/dxc`. ✓ Green as of 2026-05-08.
- **o3de-mcpp-az** (2.7.2_az.2-rev1) -- BSD-2-Clause (upstream Kiyoshi Matsui) + Apache-2.0 OR MIT (Amazon `_az.2` patch series). License-clean rebuild of upstream mcpp 2.7.2 (abandonware-class C/C++ preprocessor, last upstream release 2008) + o3de/3p-package-source's 566-line `_az.2` patch series. **Library-link variant** of the DXC-class pattern: the engine `#include`s `<mcpp_lib.h>` and links `libmcpp.so` into its binaries at build time (vs. spirvcross/dxc which are shelled out to as binaries). Ships `/usr/bin/mcpp` (CLI tool + man page), `/usr/lib64/libmcpp.so.0.3.0` (main package), `/usr/include/mcpp_lib.h` + `mcpp_out.h` + `libmcpp.a` (devel subpackage). ✓ Green as of 2026-05-08.

**Rebuild strategy:** each package is built with `enable_net=false` (so the SRPM has no upstream dependency at COPR build time). License-clean inputs only. Where O3DE upstream carries patches over the canonical source (e.g. DXC's `-o3de` tag, mikkelsen's git-snapshot rev), we apply those same patches in our SRPM.

**Architectural shape:** the engine COPR projects build with `enable_net=true` so cmake's `LY_PACKAGE_SERVER_URLS` fetcher can pull from `packages.o3de.org` for any 3rdParty packages we don't yet rebuild here. Each new SRPM that lands in this repo shifts one bundle from the packages.o3de.org CDN to here. The endgame is the CDN holding only the genuinely-restricted bundles (NvCloth, squish-ccr); everything else is either in Fedora (Stage 1 system swaps) or in this COPR repo (Stage 2 license-clean rebuilds).

**Source + issues:** https://github.com/nickschuetz/o3de-rpm and https://github.com/nickschuetz/o3de-rpm/issues
