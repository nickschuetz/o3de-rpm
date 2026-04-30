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
ENGINE_PATH="${O3DE_ENGINE_PATH:-/opt/o3de}"
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
nope()  { printf '  '"$FAIL"' %s — %s\n' "$1" "$2"; fail+=1; failures+=("$1: $2"); }
nope_v(){ # capture stderr/stdout into the failure msg
    local name="$1"; shift
    local out; out=$("$@" 2>&1)
    if [ $? -eq 0 ]; then ok "$name"; else nope "$name" "${out//$'\n'/ }"; fi
}
skipped(){ printf '  '"$SKIP"' %s — %s\n' "$1" "$2"; skip+=1; }

require() { command -v "$1" >/dev/null 2>&1 || { printf 'prerequisite missing: %s\n' "$1" >&2; exit 2; }; }
for cmd in rpm desktop-file-validate appstreamcli; do require "$cmd"; done

# ── Tier 1: RPM-level integrity ──────────────────────────────────────────────
printf "$HEADER" "Tier 1 — package metadata"

rpm -q o3de >/dev/null && ok "o3de package is installed" || {
    nope "o3de package installed" "(rpm -q o3de failed; install the RPM first)"
    exit 1
}

VERSION=$(rpm -q --qf '%{VERSION}' o3de)
ok "rpm version: $VERSION"

rpm -V o3de --nofiles >/dev/null 2>&1 && \
    ok "rpm -V: header consistent" || \
    nope "rpm -V" "header verification reported issues"

# License + provides + auto-Requires resolve cleanly
LIC=$(rpm -q --qf '%{LICENSE}' o3de)
[ "$LIC" = "Apache-2.0 OR MIT" ] && ok "license: $LIC" || nope "license" "expected 'Apache-2.0 OR MIT', got '$LIC'"

# ── Tier 2: install integrity ────────────────────────────────────────────────
printf "$HEADER" "Tier 2 — installed file integrity"

# Required entry points
for path in \
    /usr/bin/o3de \
    /usr/share/applications/o3de.desktop \
    /usr/share/applications/o3de-editor.desktop \
    /usr/share/metainfo/o3de.metainfo.xml \
    /usr/share/icons/hicolor/256x256/apps/o3de.png \
    /usr/share/icons/hicolor/16x16/apps/o3de.png \
    /usr/share/o3de/sbom/o3de.cdx.json \
    "$ENGINE_PATH/engine.json" \
    "$ENGINE_PATH/python/get_python.sh" \
    "$ENGINE_PATH/scripts/o3de.sh" \
    "$ENGINE_PATH/cmake/CalculateEnginePathId.cmake"
do
    if [ -e "$path" ]; then ok "exists: $path"
    else nope "exists: $path" "missing"; fi
done

# Launcher is executable, valid shell, has correct shebang
[ -x /usr/bin/o3de ] && ok "/usr/bin/o3de is executable" || nope "/usr/bin/o3de executable" "not +x"
head -1 /usr/bin/o3de | grep -qE '^#!/(usr/bin/)?bash' && \
    ok "launcher shebang is bash" || nope "launcher shebang" "unexpected"
nope_v "launcher syntax (bash -n)" bash -n /usr/bin/o3de

# Desktop file + metainfo validation
nope_v "o3de.desktop validates" desktop-file-validate /usr/share/applications/o3de.desktop
nope_v "o3de-editor.desktop validates" desktop-file-validate /usr/share/applications/o3de-editor.desktop
nope_v "metainfo validates" appstreamcli validate-relax --no-net /usr/share/metainfo/o3de.metainfo.xml

# AppStream sees the package
if appstreamcli search org.o3de.O3DE 2>/dev/null | grep -q '^Identifier: org.o3de.O3DE'; then
    ok "AppStream registers org.o3de.O3DE"
else
    nope "AppStream search" "GNOME Software / KDE Discover won't find this package"
fi

# StartupWMClass values (for dock icon matching)
grep -q '^StartupWMClass=O3DE$' /usr/share/applications/o3de.desktop && \
    ok "Project Manager StartupWMClass=O3DE" || \
    nope "ProjectManager StartupWMClass" "missing or wrong"
grep -q '^StartupWMClass=O3DE Editor$' /usr/share/applications/o3de-editor.desktop && \
    ok "Editor StartupWMClass=O3DE Editor" || \
    nope "Editor StartupWMClass" "missing or wrong"

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
    nope "display_version" "still '00.00' — splash will say 'Development Build'"

# No world-writable files in the engine root
WW=$(find "$ENGINE_PATH" -perm -o+w -type f 2>/dev/null | head -3)
[ -z "$WW" ] && ok "no world-writable files in $ENGINE_PATH" || \
    nope "no world-writable" "found: $WW"

# Pre-built sdists for the python packages O3DE installs editable
for pkg in scripts/o3de Tools/LyTestTools Tools/RemoteConsole/ly_remote_console; do
    sdists=$(ls "$ENGINE_PATH/$pkg/dist/"*.tar.gz 2>/dev/null | head -1)
    if [ -n "$sdists" ]; then ok "sdist present: $pkg/dist/$(basename "$sdists")"
    else nope "sdist: $pkg" "missing — user-project cmake configure will fail"; fi
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

# ── Tier 3: first-run user setup (opt-in) ────────────────────────────────────
printf "$HEADER" "Tier 3 — user-side first-run setup"

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
        nope "manifest.py patch" "venv copy missing the env-var branch — engine path resolution will misbehave"
    fi

    # Engine registration
    if env -u O3DE_HOME "$ENGINE_PATH/scripts/o3de.sh" register --this-engine >/tmp/o3de-test-register.log 2>&1; then
        ok "o3de.sh register --this-engine succeeded"
    else
        nope "o3de.sh register" "see /tmp/o3de-test-register.log"
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
printf "$HEADER" "Tier 4 — engine binary smoke"

# Launcher resolves to *some* config (auto-detection works)
if env -u O3DE_HOME bash -c '
    set -e
    source <(awk "/^ENGINE_PATH=/,/^fi$/" /usr/bin/o3de | sed "/^exec/q;/^if/,/^fi$/!d")
    [ -n "${BIN_DIR:-}" ] && [ -x "$BIN_DIR/o3de" ]
' 2>/dev/null; then
    ok "launcher auto-detects an installed config"
else
    # Fallback: just check that one of the known paths is present
    if [ -x "$ENGINE_PATH/bin/Linux/profile/Default/o3de" ] || [ -x "$ENGINE_PATH/bin/Linux/debug/Default/o3de" ]; then
        ok "at least one engine config installed"
    else
        nope "engine config" "no engine binary at bin/Linux/{profile,debug}/Default/"
    fi
fi

# Vulkan loader links work (engine uses Vulkan via dlopen)
if ldconfig -p 2>/dev/null | grep -q 'libvulkan.so.1'; then
    ok "system libvulkan.so.1 present (engine will dlopen)"
else
    nope "vulkan-loader" "libvulkan.so.1 not in ldconfig — install vulkan-loader"
fi

# ── Tier 5: end-to-end project (opt-in) ──────────────────────────────────────
printf "$HEADER" "Tier 5 — project cmake configure"

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
                [ -f build/linux/build-debug.ninja ] && ok "ninja file generated for debug" || \
                    nope "ninja file" "build-debug.ninja missing"
                # Don't actually compile — would take hours on a fresh project.
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
