#!/bin/bash
# O3DE post-install integration test suite.
#
# Validates that an installed o3de RPM gives a working end-user experience.
# Run as the user who'll be using O3DE (NOT as root for Tiers 3-5).
#
# Usage:
#   sudo dnf install -y ./o3de-*.rpm
#   tests/integration-test.sh                           # tiers 1, 2, 4
#   tests/integration-test.sh --setup                   # also run tier 3 (one-time user-side setup)
#   tests/integration-test.sh --with-project            # also run tier 5 (full end-to-end)
#   tests/integration-test.sh --setup --with-project    # everything
#
# Exit code: 0 on full pass, 1 on any failure, 2 on prerequisites missing.

set -uo pipefail

RUN_SETUP=0
RUN_PROJECT=0

# Auto-detect the installed versioned package (o3de2605, o3de2610, ...).
# Override via O3DE_PKGNAME env var when multiple are installed and you
# want to test a specific one. Falls back to legacy "o3de" so tests still
# run during the transition window after the 2026-05-03 rename.
: "${O3DE_PKGNAME:=$(rpm -qa --qf '%{NAME}\n' 2>/dev/null | grep -E '^o3de[0-9]+$' | head -1)}"
: "${O3DE_PKGNAME:=o3de}"

# Engine path defaults from O3DE_ENGINE_PATH (legacy name preserved), or
# auto-detect from the package's installed engine.json, or last-resort
# default. Prefer the actual install when O3DE_PKGNAME resolves to a
# real package; handles both /opt/o3de (legacy) and /opt/O3DE/<v>/
# (post-rename) layouts transparently.
if [ -n "${O3DE_ENGINE_PATH:-}" ]; then
    ENGINE_PATH="$O3DE_ENGINE_PATH"
else
    # The package contains TWO engine.json files:
    #   - /opt/O3DE/<v>/engine.json          (engine-root marker; what we want)
    #   - /opt/O3DE/<v>/bin/Linux/profile/Default/engine.json  (per-build artifact)
    # Pick the shorter path (= shallower in the tree = the engine root).
    ENGINE_PATH=$(rpm -ql "$O3DE_PKGNAME" 2>/dev/null \
        | grep '/engine\.json$' \
        | awk '{ print length, $0 }' | sort -n | head -1 | cut -d' ' -f2- \
        | xargs -r dirname 2>/dev/null)
    : "${ENGINE_PATH:=/opt/O3DE/26.05.0}"
fi
HEADER='\n\033[1;36m▶▶▶ %s\033[0m\n'
PASS='\033[1;32m✓\033[0m'
FAIL='\033[1;31m✗\033[0m'
SKIP='\033[1;33m⊘\033[0m'

declare -i pass=0 fail=0 skip=0
declare -a failures=()

while [ $# -gt 0 ]; do
    case "$1" in
        --setup) RUN_SETUP=1; shift ;;
        --with-project) RUN_PROJECT=1; shift ;;
        --engine-path=*) ENGINE_PATH="${1#*=}"; shift ;;
        -h|--help)
            sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *)
            printf 'unknown arg: %s\n' "$1" >&2
            exit 2 ;;
    esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
ok()    { printf '  '"$PASS"' %s\n' "$1"; pass+=1; }
nope()  { printf '  '"$FAIL"' %s: %s\n' "$1" "$2"; fail+=1; failures+=("$1: $2"); }
nope_v(){ # capture stderr/stdout into the failure msg
    local name="$1"; shift
    local out; out=$("$@" 2>&1)
    if [ $? -eq 0 ]; then ok "$name"; else nope "$name" "${out//$'\n'/ }"; fi
}
skipped(){ printf '  '"$SKIP"' %s: %s\n' "$1" "$2"; skip+=1; }

require() { command -v "$1" >/dev/null 2>&1 || { printf 'prerequisite missing: %s\n' "$1" >&2; exit 2; }; }
for cmd in rpm desktop-file-validate appstream-util; do require "$cmd"; done

# ── Tier 1: RPM-level integrity ──────────────────────────────────────────────
printf "$HEADER" "Tier 1: package metadata"

# Derive the version-suffix that's appended to several installed names
# (e.g., AppStream component ID `org.o3de.O3DE2605`, WM_CLASS `O3DE-2605`).
# For a legacy `o3de` package (no digit suffix), MAJOR_TAG is empty;
# tests fall back to the un-versioned identifiers.
MAJOR_TAG="${O3DE_PKGNAME#o3de}"
APPSTREAM_ID="org.o3de.O3DE${MAJOR_TAG}"
WMCLASS="O3DE${MAJOR_TAG:+-$MAJOR_TAG}"

rpm -q "$O3DE_PKGNAME" >/dev/null && ok "$O3DE_PKGNAME package is installed" || {
    nope "$O3DE_PKGNAME package installed" "(rpm -q $O3DE_PKGNAME failed; install the RPM first)"
    exit 1
}

VERSION=$(rpm -q --qf '%{VERSION}' "$O3DE_PKGNAME")
ok "rpm version: $VERSION"

rpm -V "$O3DE_PKGNAME" --nofiles >/dev/null 2>&1 && \
    ok "rpm -V: header consistent" || \
    nope "rpm -V" "header verification reported issues"

# License + provides + auto-Requires resolve cleanly
LIC=$(rpm -q --qf '%{LICENSE}' "$O3DE_PKGNAME")
[ "$LIC" = "Apache-2.0 OR MIT" ] && ok "license: $LIC" || nope "license" "expected 'Apache-2.0 OR MIT', got '$LIC'"

# ── Tier 2: install integrity ────────────────────────────────────────────────
printf "$HEADER" "Tier 2: installed file integrity"

# Required entry points (always required); all derived from $O3DE_PKGNAME.
for path in \
    "/usr/bin/$O3DE_PKGNAME" \
    "/usr/share/applications/$O3DE_PKGNAME.desktop" \
    "/usr/share/applications/$O3DE_PKGNAME-editor.desktop" \
    "/usr/share/metainfo/$O3DE_PKGNAME.metainfo.xml" \
    "/usr/share/icons/hicolor/256x256/apps/$O3DE_PKGNAME.png" \
    "/usr/share/icons/hicolor/16x16/apps/$O3DE_PKGNAME.png" \
    "/usr/share/$O3DE_PKGNAME/sbom/$O3DE_PKGNAME.cdx.json" \
    "$ENGINE_PATH/engine.json" \
    "$ENGINE_PATH/python/get_python.sh" \
    "$ENGINE_PATH/scripts/o3de.sh" \
    "$ENGINE_PATH/cmake/CalculateEnginePathId.cmake"
do
    if [ -e "$path" ]; then ok "exists: $path"
    else nope "exists: $path" "missing"; fi
done

# Launcher is executable, valid shell, has correct shebang
[ -x "/usr/bin/$O3DE_PKGNAME" ] && ok "/usr/bin/$O3DE_PKGNAME is executable" \
    || nope "/usr/bin/$O3DE_PKGNAME executable" "not +x"
head -1 "/usr/bin/$O3DE_PKGNAME" | grep -qE '^#!/(usr/)?bin/bash([[:space:]]|$)|^#!/usr/bin/env[[:space:]]+bash' && \
    ok "launcher shebang is bash" || nope "launcher shebang" "got '$(head -1 /usr/bin/$O3DE_PKGNAME)'"

# CLI wrapper. Detect whether the installed RPM is supposed to ship it
# (older snapshot RPMs predate the wrapper); only enforce when the RPM
# manifest declares it.
if rpm -ql "$O3DE_PKGNAME" 2>/dev/null | grep -qx "/usr/bin/${O3DE_PKGNAME}-cli"; then
    [ -x "/usr/bin/${O3DE_PKGNAME}-cli" ] && ok "/usr/bin/${O3DE_PKGNAME}-cli is executable" || \
        nope "/usr/bin/${O3DE_PKGNAME}-cli executable" "RPM declares it but not +x or missing"
    # Reachability check: the wrapper should exec the bundled o3de.sh, which
    # then either prints argparse output (full Tier-3-ready path) OR the
    # "Python has not been downloaded" message from python.sh on a fresh
    # install. Both prove the wrapper reached the bundled script chain;
    # only one demands the per-user venv exist. Distinguish them in the
    # success message so Tier-2 readers know whether further setup is
    # needed before the cli is actually usable.
    cli_out=$("/usr/bin/${O3DE_PKGNAME}-cli" --help </dev/null 2>&1)
    if printf '%s\n' "$cli_out" | grep -qE 'usage: o3de\.py|Sub-Commands'; then
        ok "/usr/bin/${O3DE_PKGNAME}-cli --help reaches the upstream o3de.py argparse"
    elif printf '%s\n' "$cli_out" | grep -qE 'Python has not been downloaded|get_python\.sh first'; then
        ok "/usr/bin/${O3DE_PKGNAME}-cli is reachable (wrapper -> o3de.sh -> python.sh; venv setup pending; run get_python.sh or pass --setup)"
    else
        nope "/usr/bin/${O3DE_PKGNAME}-cli reachable" "no argparse and no Python-setup hint; wrapper or o3de.sh path broken: ${cli_out//$'\n'/ | }"
    fi
else
    skipped "/usr/bin/${O3DE_PKGNAME}-cli checks" "RPM doesn't declare it (pre-CLI build); skipping"
fi
nope_v "launcher syntax (bash -n)" bash -n "/usr/bin/$O3DE_PKGNAME"

# Desktop file + metainfo validation
nope_v "$O3DE_PKGNAME.desktop validates" desktop-file-validate "/usr/share/applications/$O3DE_PKGNAME.desktop"
nope_v "$O3DE_PKGNAME-editor.desktop validates" desktop-file-validate "/usr/share/applications/$O3DE_PKGNAME-editor.desktop"
nope_v "metainfo validates" appstream-util validate-relax --nonet "/usr/share/metainfo/$O3DE_PKGNAME.metainfo.xml"

# AppStream sees the package (appstreamcli is optional; only if installed)
if command -v appstreamcli >/dev/null 2>&1; then
    if appstreamcli search "$APPSTREAM_ID" 2>/dev/null | grep -qE "^Identifier: ${APPSTREAM_ID}"; then
        ok "AppStream registers $APPSTREAM_ID"
    else
        nope "AppStream search" "GNOME Software / KDE Discover won't find this package (looking for $APPSTREAM_ID)"
    fi
else
    skipped "AppStream search" "appstreamcli not installed"
fi

# StartupWMClass values (for dock icon matching).
# Project Manager: versioned to match what the launcher's Qt -name arg
#   sets at runtime; multiple installed majors get distinct dock identities.
# Editor: NOT versioned. The Editor is exec'd by Project Manager directly,
#   bypassing our launcher, so its WM_CLASS comes from Qt's internal
#   setApplicationName("O3DE Editor"). Verified live via xprop:
#     WM_CLASS(STRING) = "Editor", "O3DE Editor"
#   The desktop file's StartupWMClass must match that exactly for GNOME/KDE
#   to attach our icon to the running Editor window. Two installed majors'
#   Editors share the same dock icon (acceptable: PM is the user-facing
#   launcher and retains its versioned identity).
grep -q "^StartupWMClass=${WMCLASS}\$" "/usr/share/applications/$O3DE_PKGNAME.desktop" && \
    ok "Project Manager StartupWMClass=$WMCLASS" || \
    nope "ProjectManager StartupWMClass" "missing or wrong (looking for $WMCLASS)"
grep -q "^StartupWMClass=O3DE Editor\$" "/usr/share/applications/$O3DE_PKGNAME-editor.desktop" && \
    ok "Editor StartupWMClass=O3DE Editor (matches Qt's setApplicationName)" || \
    nope "Editor StartupWMClass" "missing or wrong (looking for 'O3DE Editor')"

# Engine.json carries a 3-component MAJOR.MINOR.PATCH version
EJ_VERSION=$(grep '"version"' "$ENGINE_PATH/engine.json" | awk -F'"' '{print $4}')
if [[ "$EJ_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    ok "engine.json version is 3-component: $EJ_VERSION"
else
    nope "engine.json version" "got '$EJ_VERSION', need MAJOR.MINOR.PATCH"
fi

# display_version isn't the "00.00" placeholder
DV=$(grep '"display_version"' "$ENGINE_PATH/engine.json" | awk -F'"' '{print $4}')
[ "$DV" != "00.00" ] && [ -n "$DV" ] && \
    ok "display_version set: $DV (splash will show this, not 'Development Build')" || \
    nope "display_version" "still '00.00'; splash will say 'Development Build'"

# No world-writable files in the engine root
WW=$(find "$ENGINE_PATH" -perm -o+w -type f 2>/dev/null | head -3)
[ -z "$WW" ] && ok "no world-writable files in $ENGINE_PATH" || \
    nope "no world-writable" "found: $WW"

# Pre-built sdists for the python packages O3DE installs editable
for pkg in scripts/o3de Tools/LyTestTools Tools/RemoteConsole/ly_remote_console; do
    sdists=$(ls "$ENGINE_PATH/$pkg/dist/"*.tar.gz 2>/dev/null | head -1)
    if [ -n "$sdists" ]; then ok "sdist present: $pkg/dist/$(basename "$sdists")"
    else nope "sdist: $pkg" "missing; user-project cmake configure will fail"; fi
done

# ldd on the launcher's eventual target binary (needs symlinks first)
for cfg in profile debug; do
    BIN="$ENGINE_PATH/bin/Linux/$cfg/Default/o3de"
    if [ -x "$BIN" ]; then
        # Returns "not found" lines for any unresolved deps
        unresolved=$(ldd "$BIN" 2>/dev/null | grep -c 'not found')
        if [ "$unresolved" -eq 0 ]; then ok "ldd clean: $cfg/o3de"
        else nope "ldd: $cfg/o3de" "$unresolved unresolved deps"; fi
    fi
done

# Stage 1 system-library swap consistency. For each migration where the
# RPM declares a system Requires:, verify the package's auto-Requires
# (computed by RPM walking ldd of every .so it ships) includes the
# expected soname; catches the failure mode where the spec activates
# the swap but cmake silently falls through to the upstream bundle
# (which would link statically, leaving the soname missing from auto-
# Requires entirely).
#
# Use rpm's own auto-Requires output rather than re-walking the install
# tree with ldd: rpm walks every shipped binary anyway, and auto-
# detected .so dependencies appear as `libfoo.so.N()(64bit)` lines in
# `rpm -q --requires`. That's a single source of truth and doesn't
# depend on us guessing where the consuming binary lives in the install
# layout (which can vary across gem/component structure changes).
#
# Add a row per activated migration. Format:
#   "<rpm-package-name>:<soname-ere>"
#   rpm-package: matches `rpm -q --requires o3de` to detect activation
#   soname-ere : an extended regex matched against `rpm -q --requires`
#                 (auto-Requires tokens look like `libfoo.so.N()(64bit)`).
#
# The soname is matched as an ERE with the version component wildcarded
# rather than a fixed string. The test's job is to confirm the swap took
# effect (the system soname appears in auto-Requires, i.e. the bundle is
# NOT statically linked); the specific ABI version is irrelevant to that
# and drifts across our chroots. e.g. rawhide ships Lua 5.5
# (liblua-5.5.so) and OpenEXR 3.4 (libOpenEXR-3_4.so.NN) where F44 ships
# Lua 5.4 / OpenEXR 3.2; pinning the F44 version string made the rawhide
# test job spuriously fail even though the swap was working. Wildcarding
# the version keeps the "did the swap take effect" assertion intact while
# being distro-version agnostic.
for swap in \
    "expat:libexpat\.so\.[0-9]+" \
    "freetype:libfreetype\.so\.[0-9]+" \
    "mikkelsen:libmikktspace\.so\.[0-9]+" \
    "libpng:libpng16\.so\.[0-9]+" \
    "libtiff:libtiff\.so\.[0-9]+" \
    "zlib:libz\.so\.[0-9]+" \
    "assimp:libassimp\.so\.[0-9]+" \
    "lua-libs:liblua-5\.[0-9]+\.so" \
    "lz4-libs:liblz4\.so\.[0-9]+" \
    "openexr-libs:libOpenEXR-3_[0-9]+\.so\.[0-9]+" \
    "libsamplerate:libsamplerate\.so\.[0-9]+" \
    "sqlite-libs:libsqlite3\.so\.[0-9]+" \
    "poly2tri:libpoly2tri\.so\.[0-9]+(\.[0-9]+)*" \
    "google-benchmark:libbenchmark\.so\.[0-9]+" \
    "o3de2605-mcpp-az:libmcpp\.so\.[0-9]+" \
    "o3de2605-cityhash:libcityhash\.so\.[0-9]+" \
; do
    # Stage 2 binary-shellout swaps (o3de2605-dxc-spirv, o3de2605-spirv-cross)
    # don't appear in auto-Requires (engine shells out to the binaries at
    # asset-build time; no link-time dep). vulkan-validation-layers is a
    # runtime-discovered Vulkan layer plugin (not linked); the binary just
    # needs the Vulkan loader to find /usr/share/vulkan/explicit_layer.d/*.json.
    # imath: openexr-libs auto-pulls imath transitively, no separate check needed.
    pkg="${swap%%:*}"
    soname="${swap#*:}"
    if rpm -q --requires "$O3DE_PKGNAME" 2>/dev/null | grep -qE "^${pkg}(\\s|\$|>|=)"; then
        # Capture the concrete soname token (e.g. liblua-5.5.so) for the
        # message; the soname column is a version-wildcarded ERE. Match
        # the soname up to its trailing "(" (start of the "()(64bit)"
        # suffix in auto-Requires) so we anchor on a complete token, then
        # strip that "(" for display.
        match=$(rpm -q --requires "$O3DE_PKGNAME" 2>/dev/null | grep -oE "${soname}\\(" | head -1)
        match="${match%(}"
        if [ -n "$match" ]; then
            ok "system-lib swap took effect: $O3DE_PKGNAME Requires:$pkg AND $match appears in auto-Requires"
        else
            nope "system-lib swap: $pkg" "RPM declares Requires:$pkg but no ${soname} soname in auto-Requires; likely the swap regressed and the bundle is still being statically linked"
        fi
    fi
done

# ── Tier 3: first-run user setup (opt-in) ────────────────────────────────────
printf "$HEADER" "Tier 3: user-side first-run setup"

if [ "$RUN_SETUP" -eq 1 ]; then
    # get_python.sh sets up the per-user venv. This downloads ~200MB of pip
    # deps on the first run; idempotent on subsequent runs.
    if env -u O3DE_HOME "$ENGINE_PATH/python/get_python.sh" >/tmp/o3de-test-getpython.log 2>&1; then
        ok "get_python.sh succeeded"
    else
        nope "get_python.sh" "see /tmp/o3de-test-getpython.log"
    fi

    # Engine ID dir got created
    venv_count=$(ls "$HOME/.o3de/Python/venv/" 2>/dev/null | wc -l)
    [ "$venv_count" -ge 1 ] && ok "venv dir created ($venv_count entries)" || \
        nope "venv dir" "no entries under ~/.o3de/Python/venv/"

    # Patched manifest.py (with O3DE_ENGINE_PATH branch) is present in venv
    if grep -q 'O3DE_ENGINE_PATH' "$HOME/.o3de/Python/venv/"*/lib/python*/site-packages/o3de/manifest.py 2>/dev/null; then
        ok "manifest.py patch active in venv (O3DE_ENGINE_PATH branch)"
    else
        nope "manifest.py patch" "venv copy missing the env-var branch; engine path resolution will misbehave"
    fi

    # Engine registration. Prefer the PATH-installed CLI wrapper (which
    # forwards to <engine>/scripts/o3de.sh) when available; this double-
    # duties as an end-to-end reachability test of the wrapper now that
    # the per-user venv is set up. Fall back to the absolute path for
    # older RPMs that don't ship the wrapper.
    if rpm -ql "$O3DE_PKGNAME" 2>/dev/null | grep -qx "/usr/bin/${O3DE_PKGNAME}-cli"; then
        register_cmd="/usr/bin/${O3DE_PKGNAME}-cli"
    else
        register_cmd="$ENGINE_PATH/scripts/o3de.sh"
    fi
    if env -u O3DE_HOME "$register_cmd" register --this-engine >/tmp/o3de-test-register.log 2>&1; then
        ok "$register_cmd register --this-engine succeeded"
    else
        nope "$(basename "$register_cmd") register" "see /tmp/o3de-test-register.log"
    fi

    # Manifest's engines list includes us
    if python3 -c "
import json, sys
m = json.load(open('$HOME/.o3de/o3de_manifest.json'))
sys.exit(0 if '$ENGINE_PATH' in m.get('engines', []) else 1)
"; then ok "manifest engines includes $ENGINE_PATH"
    else nope "manifest engines" "$ENGINE_PATH not registered"; fi
else
    skipped "Tier 3 user-setup tests" "pass --setup to run; modifies ~/.o3de"
fi

# ── Tier 4: engine smoke ─────────────────────────────────────────────────────
printf "$HEADER" "Tier 4: engine binary smoke"

# Launcher resolves to *some* config (auto-detection works)
if env -u O3DE_HOME bash -c "
    set -e
    source <(awk \"/^ENGINE_PATH=/,/^fi\\\$/\" /usr/bin/$O3DE_PKGNAME | sed \"/^exec/q;/^if/,/^fi\\\$/!d\")
    [ -n \"\${BIN_DIR:-}\" ] && [ -x \"\$BIN_DIR/o3de\" ]
" 2>/dev/null; then
    ok "launcher auto-detects an installed config"
else
    # Fallback: just check that one of the known paths is present
    if [ -x "$ENGINE_PATH/bin/Linux/profile/Default/o3de" ] || [ -x "$ENGINE_PATH/bin/Linux/debug/Default/o3de" ]; then
        ok "at least one engine config installed"
    else
        nope "engine config" "no engine binary at bin/Linux/{profile,debug}/Default/"
    fi
fi

# Vulkan loader present (engine dlopens libvulkan.so.1; auto-Requires misses dlopen)
if rpm -q vulkan-loader >/dev/null 2>&1 && [ -e /usr/lib64/libvulkan.so.1 ]; then
    ok "vulkan-loader installed (engine will dlopen libvulkan.so.1)"
else
    nope "vulkan-loader" "vulkan-loader package or /usr/lib64/libvulkan.so.1 missing"
fi

# Regression guard for the engine-path / venv-id mismatch (build #5/#6):
# Without --engine-path passed by the launcher, Project Manager hashes the
# scan-up-discovered engine root to a different SHA1 than get_python.sh
# uses, then raises "Failed to start Python". This check runs the launcher
# headlessly for ~6 seconds, captures stderr, and fails if the dialog text
# is present. The engine's normal logging on a healthy launch does not
# include this string. We don't need a display server because the error
# is logged to stderr before Qt tries to show the modal.
if [ "$RUN_SETUP" -eq 1 ] || [ -d "$HOME/.o3de/Python/venv/" ] && \
   ls "$HOME/.o3de/Python/venv/"*/lib/python*/site-packages/o3de >/dev/null 2>&1; then
    LAUNCH_LOG=$(mktemp)
    QT_QPA_PLATFORM=offscreen timeout 8 "/usr/bin/$O3DE_PKGNAME" </dev/null >"$LAUNCH_LOG" 2>&1 || :
    if grep -q "Missing python venv file at\|Python home path does not exist" "$LAUNCH_LOG"; then
        nope "engine-path / venv-id sync" "launcher didn't pass --engine-path; engine looks for venv at wrong ID. Log: $LAUNCH_LOG"
    else
        ok "engine-path / venv-id sync (Project Manager Python init reaches engine root)"
        rm -f "$LAUNCH_LOG"
    fi
else
    skipped "engine-path / venv-id sync" "no per-user venv; pass --setup or run get_python.sh first"
fi

# ── Tier 5: end-to-end project (opt-in) ──────────────────────────────────────
printf "$HEADER" "Tier 5: project cmake configure"

if [ "$RUN_PROJECT" -eq 1 ]; then
    if [ "$RUN_SETUP" -eq 0 ] && [ ! -f "$HOME/.o3de/Python/venv/"*/lib/python*/site-packages/o3de/__init__.py ]; then
        skipped "Tier 5 project test" "user venv not set up; pass --setup or run get_python.sh first"
    else
        TMPDIR=$(mktemp -d)
        trap 'rm -rf "$TMPDIR"' EXIT
        cd "$TMPDIR"

        # Use the bundled project template
        if env -u O3DE_HOME "$ENGINE_PATH/scripts/o3de.sh" create-project \
                --project-path "$TMPDIR/integration-test-project" \
                --template-name MinimalProject \
                >/tmp/o3de-test-create.log 2>&1; then
            ok "o3de create-project (MinimalProject template)"
            cd "$TMPDIR/integration-test-project"

            mkdir -p "$HOME/.o3de/3rdParty"
            if cmake -B build/linux -S . -GNinja\ Multi-Config \
                    -DLY_3RDPARTY_PATH="$HOME/.o3de/3rdParty" \
                    >/tmp/o3de-test-cmake.log 2>&1; then
                ok "cmake configure against installed engine"
                # O3DE's Ninja Multi-Config configure generates the profile config by
                # default; debug is opt-in via a separate cmake invocation.
                [ -f build/linux/build-profile.ninja ] && ok "ninja file generated for profile" || \
                    nope "ninja file" "build-profile.ninja missing (cmake configure produced no per-config ninja file)"
                # Don't actually compile; would take hours on a fresh project.
            else
                nope "cmake configure" "see /tmp/o3de-test-cmake.log"
            fi
        else
            nope "create-project" "see /tmp/o3de-test-create.log"
        fi
    fi
else
    skipped "Tier 5 project test" "pass --with-project to run; takes ~5min + uses network"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
total=$((pass + fail + skip))
printf '\n────────────────────────────────────────\n'
printf '  %s %d passed   %s %d failed   %s %d skipped   (of %d)\n' \
    "$PASS" "$pass" "$FAIL" "$fail" "$SKIP" "$skip" "$total"
if [ "$fail" -gt 0 ]; then
    printf '\nFailures:\n'
    for f in "${failures[@]}"; do printf '  - %s\n' "$f"; done
    exit 1
fi
exit 0
