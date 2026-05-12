# PR: Clang: -Wno-error=deprecated-volatile and -Wno-error=character-conversion

**Branch:** `nickschuetz/o3de:clang21-warning-suppressions`
**Target:** `o3de/o3de:development`
**File touched:** `cmake/Platform/Common/Clang/Configurations_clang.cmake` (+4 lines)
**Single commit:** DCO-signed, conservative scope

## Title (for the PR form)

`Clang: -Wno-error=deprecated-volatile and -Wno-error=character-conversion`

## Body (paste into PR description)

Clang 21 (in Fedora 44's updates repo, on user systems now and imminent in stable) promoted two existing warnings to errors:

- `-Wdeprecated-volatile` (was warning in clang 19/20)
- `-Wcharacter-conversion` (was warning in clang 19/20)

Combined with O3DE's `-Werror`, this turns "engine compiles cleanly on my Linux machine" into "engine fails to build with the latest clang in my distro's package manager." Affects every Linux contributor rolling forward into Fedora 44+, Ubuntu 24.10+, Arch, NixOS, and similar modern-toolchain distributions.

The build failure looks like:

```
error: 'deprecated-volatile' is now an error [-Werror,-Wdeprecated-volatile]
error: 'character-conversion' is now an error [-Werror,-Wcharacter-conversion]
```

### Fix

Keep `-Werror` (no policy regression) but selectively demote the two clang-21 promotions back to warnings via `-Wno-error=`. The warnings still print -- they just don't fail the build. Adjacent to the existing `-Werror` line in `cmake/Platform/Common/Clang/Configurations_clang.cmake`.

### Why this is conservative

- **Specific, not broad.** Only the two clang-21 promotions are demoted. Doesn't touch any other warning.
- **Demotes to warning, not silence.** `-Wno-error=` keeps the diagnostic; downstream readers still see "hey, you used a deprecated volatile compound assignment, here's the line." Just doesn't blow up the build.
- **No-op on older clang.** clang 19/20 don't emit the warnings these flags reference, so `-Wno-error=deprecated-volatile` and `-Wno-error=character-conversion` are silently ignored on those toolchains. Existing CI runners are unaffected.
- **Forward-compatible.** Reviewing this two years from now when clang 21 is the floor: the flags continue to do the right thing.

### Test plan

- Verified locally on Fedora 44 with clang 21+: engine builds clean with this change applied.
- Build matrix on existing CI (clang 19/20) unaffected -- the `-Wno-error=` flags reference warnings the older clang doesn't emit.
- No file/path/binary changes; only adds 4 lines to a cmake configuration list.

### Companion context

This is part of a Fedora-packaging effort to ship O3DE as a regular distro RPM (`o3de2605`). Several engine-side compatibility fixes have already landed (libtiff C99 typedef migration #19734, libunwind/`Wayland` Qt forcing XCB, etc.); this one closes the next forward-compat gap. Carry-patch in the packaging repo today; retires when this lands upstream.
