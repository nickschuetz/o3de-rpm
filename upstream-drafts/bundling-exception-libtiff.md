# Bundling Library Exception: libtiff

Draft Bundling Library Exception filing for inclusion in the Fedora package review of `o3de2605`. Companion filings are tracked under Stage 5 of `FEDORA_ROADMAP.md` (Qt 5.15-rev9, squish-ccr, NvCloth; DXC dropped out 2026-05-28 after the license-clean rebuild shipped).

## Library

- Name: `libtiff`
- Bundled version: `4.2.0.15-rev3` (sourced from `packages.o3de.org` as `tiff-4.2.0.15-rev3-linux`; verified pin: `tiff-4.2.0.15-rev3-linux` PACKAGE_HASH `2377f48b2ebc2d1628d9f65186c881544c92891312abe478a20d10b85877409a` in `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake`)
- Upstream license: libtiff license (MIT-style, Fedora-compatible)
- Fedora-available equivalent: `libtiff-devel` 4.6.x in Fedora 44 (functionally a strict superset)

## Why bundled

The blocker is not the libtiff package itself. It is a transitive C++ type-system collision between libtiff's standard typedefs (`int64`, `uint64` as `int64_t`/`uint64_t`, i.e. `long`/`unsigned long` on Linux LP64) and the engine's CryCommon legacy typedefs of the same names (`slonglong`/`ulonglong`, i.e. `long long`/`unsigned long long`). Both definitions enter the same translation units in the engine's two libtiff consumers, and they cannot coexist.

Concrete reproduction (recorded in spec changelog entry `2605.0-27`, commits `cda6b7b` to `9f2f099` in `nickschuetz/o3de-rpm`):

A local `rpmbuild -bb --with system_tiff` against the bundled engine source with `Patch0008` (Option A: narrow `O3DE_SYSTEM_LIBTIFF_COMPAT` guard around CryCommon's int64/uint64 plus a `SKIP_UNITY_BUILD_INCLUSION` for the affected .cpp files) fails at compile time:

```
Code/Legacy/CryCommon/Cry_ValidNumber.h:79: error: use of undeclared identifier 'uint64'
    #define DoubleU64(x)   (*((uint64*) &(x)))
```

The root cause is that `Cry_ValidNumber.h` uses bare `uint64` in its own `DoubleU64` / `DoubleU64ExpMask` / `DoubleU64FracMask` macro bodies. It is transitively included from the TIFF .cpp files (`Gems/Atom/Asset/ImageProcessingAtom/.../TIFFLoader.cpp` and `Code/Tools/RC/ResourceCompilerImage/Formats/ImageTIF.cpp`) via `EditorDefs.h` then `Cry_Math.h`, before `<tiffio.h>` brings libtiff's typedef into scope. Patch0008's narrow guard suppressed CryCommon's typedef in the affected translation units but left the macro bodies referring to an undeclared name.

Reordering `<tiffio.h>` ahead of the engine headers compiles cleanly (libtiff's typedef becomes visible first), but link-fails because libtiff's `int64 = int64_t = long` (LP64) does not match CryCommon's exported `long long` mangling for engine API symbols such as `CryGetTicks()`, producing undefined references at the final shared-object link step.

## Why we cannot package the patched version separately, or substitute system libtiff

The fix is not in libtiff; it is in the engine's own `CryCommon` headers. The clean resolution is migrating CryCommon's `int64` / `uint64` typedefs from `slonglong` / `ulonglong` to the C99 standard `int64_t` / `uint64_t` engine-wide. That change touches:

- Engine-wide template specializations keyed on the typedef
- Overload resolution for any function distinguishing `long long` from `long`
- printf format-specifier macros
- ABI for exported engine symbols on Linux (LP64 shifts `long long` -> `long`); on Windows LLP64 the shift is a no-op rename, so the migration is asymmetric across the engine's supported platforms

Per the O3DE engine sig-build response (Nick L., 2026-05-05), upstream characterizes this work as "legacy housework" that is in-scope for normal engine maintenance, but the migration has not been done. Until it lands upstream, the only options that compile and link correctly on Linux are:

1. Bundle libtiff (current state)
2. Migrate CryCommon engine-wide (not packaging-side work; requires upstream PR)

The "package a patched libtiff" path does not apply here, because no patch to libtiff itself can resolve the collision; the offending typedefs are libtiff's standard public API.

## What the package already patches

`Patch0007` (`0007-libtiff-c99-typedefs.patch`) is present and applied unconditionally, independent of any system libtiff swap. It migrates the engine's two `<tiffio.h>` consumers off the legacy `uint8` / `uint16` / `uint32` typedef spellings to the C99 `uint8_t` / `uint16_t` / `uint32_t` names. libtiff 4.5+ marks the legacy spellings `__attribute__((deprecated))` and the engine builds with `-Werror`, so this patch is required against any modern libtiff regardless of bundling stance. Two of the four engine-side patches in this change set were submitted upstream and merged (`o3de/o3de#19734`); the remaining two stay carried in this package because the o3de fork's stabilization branch did not pick the upstream merge before the 26.05.0 cut.

## Activation framework for a future system swap

The Stage 1 swap scaffolding is already wired and shipped, defaulted off, so the day the upstream CryCommon C99 migration lands the activation is a one-line build-time flip rather than a re-architecture:

- `%bcond_with system_tiff` (spec line 92)
- `Source35: FindTIFF-system.cmake` plus the `cp` into `cmake/3rdParty/FindTIFF.cmake` at `%prep`
- Conditional `BuildRequires: libtiff-devel` (spec line 733), `Requires: libtiff` (line 823), `Recommends: libtiff-devel` (line 933)
- Conditional `-DLY_USE_SYSTEM_TIFF=ON` cmake flag (line 1173)

Activation procedure once unblocked: `copr-cli edit-chroot --rpmbuild-with system_tiff ...` for each chroot, then a fresh build. No spec edits required.

## Maintenance commitment

(Proposed windows; Nick to sign off before filing.)

- The bundled `libtiff-4.2.0.15-rev3-linux` tarball is pinned by SHA-256 in the engine's `BuiltInPackages_linux_x86_64.cmake`. We track upstream O3DE bumps of this pin and rebuild downstream within 14 days of any O3DE point release that changes the libtiff pin.
- The package-system source tree for the libtiff rebuild lives at `github.com/o3de/3p-package-source/tree/main/package-system/tiff`; bumping in our own COPR repo is straightforward if upstream takes a security-only rebuild that the engine has not picked up yet.

## Security tracking

(Proposed windows; Nick to sign off before filing.)

- For libtiff CVEs we will, in order of preference:
  1. Wait for upstream O3DE to rebuild the bundled tarball with the fix and bump the pin; we rebuild downstream within 7 days of the upstream rebuild for HIGH/CRITICAL severity CVEs and within 14 days for MODERATE.
  2. If upstream is slow and the CVE is HIGH/CRITICAL severity AND exploitable from engine-loaded TIFFs (the engine reads TIFF assets at build time and at runtime via the ImageProcessing Gem), apply a vendor-backport patch as a `PatchNNNN:` in this spec within 7 days of CVE publication and bump the release.
- The engine's TIFF surface is not internet-facing in the runtime path; the highest-risk consumer is the asset-build pipeline parsing project-supplied TIFFs. The Fedora package review filing will note this risk profile.

## Window rationale (for the proposed numbers above)

The 7-day HIGH/CRITICAL and 14-day MODERATE windows mirror what we have committed to elsewhere in similar volunteer-driven Fedora packaging contexts. The 14-day upstream-rev-bump window matches our typical post-release packaging cadence (one weekly cycle of build + Tier validation + COPR push). Nick: please confirm or adjust before filing; both windows are tighter than the realistic worst case but achievable on the typical case, which matches the Fedora packaging guideline's expectation of "documented and defensible" rather than "best-case marketed".

## Removal condition

This exception retires when upstream O3DE merges the CryCommon C99 typedef migration (`int64`/`uint64` to `int64_t`/`uint64_t` engine-wide). Tracking signal: an `o3de/o3de` PR touching `Code/Legacy/CryCommon/BaseTypes.h` or equivalent. At that point a fresh local `rpmbuild -bb --with system_tiff` is expected to compile and link cleanly; we flip the bcond and drop the bundled tarball in the same release.

## Anchors

- Spec changelog entries `2605.0-27`, `-30`, and surrounding entries document the original Option A reproduction and the decision to ship Option C.
- Working notes: `BUNDLED_LIBRARIES.md` row "libtiff" under "Big-media bundles" (single source of truth for the per-bundle status).
- Memory: `project_system_tiff_option_c.md`, `project_crycommon_int64_legacy_housework.md`.
- Activation framework files: `sources/FindTIFF-system.cmake`, `sources/0007-libtiff-c99-typedefs.patch`.
