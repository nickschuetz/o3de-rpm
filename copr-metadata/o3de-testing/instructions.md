Enable + install:

    sudo dnf copr enable hellaenergy/o3de-testing
    sudo dnf install o3de2605

This channel is the pre-promotion soak buffer between the `main` HEAD of the [o3de-rpm](https://github.com/nickschuetz/o3de-rpm) repository and the stable channel `hellaenergy/o3de`. Mirrors Fedora's `updates-testing` semantics.

**Promotion flow:**

    main HEAD
        |
        v   make copr-testing-and-test
    hellaenergy/o3de-testing (community testers see it; ~48h soak window)
        |
        v   make copr-stable  (after soak completes with no regression reports)
    hellaenergy/o3de (broad user base)

**When to enable this channel:**

- You want to validate the next set of packaging fixes a couple of days before they reach the broader stable channel.
- You want to help catch regressions before they affect the general stable audience.
- You are comfortable reporting issues if something doesn't work.

**When to NOT enable this channel:**

- You want maximum stability. Use `hellaenergy/o3de` instead.
- You are running production workloads. Use `hellaenergy/o3de` instead.

**Pick one: do NOT enable hellaenergy/o3de-testing AND hellaenergy/o3de at the same time.** If you do, dnf will install the higher NVR (always testing's), which defeats the purpose of being on stable. The two channels are mutually exclusive in practice.

**What's in this channel vs stable:**

- Same upstream engine source (tagged release; same SRPM as stable except for the destination COPR project).
- Same active Stage 1 system-library swap set (14-pack: zlib, freetype, libpng, expat, lz4, mikkelsen, openexr, poly2tri, lua, assimp, sqlite, libsamplerate, googlebenchmark, vulkan-validation-layers).
- Same active Stage 2 binary-shellout / library-link swaps (DXC, SPIRV-Cross, mcpp).
- Slightly newer packaging-side fixes that have not yet reached stable: typically Recommends changes, launcher tweaks, README corrections, and similar small enhancements. Each commit in main between the stable channel's published NVR and this channel's NVR is one fix; review the changelog at `dnf updateinfo info o3de2605` to see what's queued.

**Reporting issues:** if you hit a regression on this channel, please open an issue at https://github.com/nickschuetz/o3de-rpm/issues so it can be addressed before promotion to stable.

The `o3de-dependencies` repo auto-enables alongside this one. The optional `o3de2605-devel` subpackage (auto-pulled by `dnf install o3de2605` via Recommends) adds the static archives that Project Manager's "Build" workflow links against (`libAzGameFramework.a` and friends).
