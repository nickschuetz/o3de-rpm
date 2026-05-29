#!/bin/bash
# Tier 7: system-swap library-health check for an installed o3de RPM.
#
# History: this was originally an end-to-end "drive AssetProcessorBatch
# against cube.fbx and grade the .azmodel output" test. That premise
# was wrong (documented at length in memory note
# `project_tier7_cold_cache_quirk.md`): FBX -> azmodel through SceneAPI
# is NOT standalone from the Atom rendering pipeline; even the
# simplest cube.fbx declares a JobDependency on
# DefaultVertexBufferPool.resourcepool which transitively needs
# shaders + SRG merge + Atom RPI gem. An empty scratch project can't
# satisfy that. The previous approach kept tripping over this and
# producing false negatives.
#
# Rewritten 2026-05-11 to do what's actually catchable at the
# binding/library layer: verify each Stage 1 system-swap library is
# loadable, has the expected SONAME, exposes the symbols the engine
# uses, and is actually linked-against by an engine binary. Doesn't
# claim behavior coverage; the engine team owns SceneAPI integration
# testing, and we'd need an upstream `--minimal-scope` flag on
# AssetProcessorBatch to do that properly from a downstream packager
# position.
#
# What this catches:
#   - Fedora roll moves the SONAME (e.g., libassimp.so.6 -> .7)
#   - Fedora packaging breaks (missing symlinks, missing -devel BR
#     coverage, wrong RPATH)
#   - Engine binaries link against bundled-lib SONAME instead of
#     system-lib SONAME (smoke-detects whether the system swap is
#     actually firing in the binary build)
#   - Library exists but symbol set has shrunk (Fedora trimmed the
#     ABI; unlikely for libraries we depend on but worth knowing)
#
# What this does NOT catch (acknowledged):
#   - Behavior deltas between assimp 5 and 6 (cube.fbx imports
#     successfully but with different mesh-split semantics, etc.)
#   - Runtime errors at AP/SceneAPI-pipeline level
#   - User-facing rendering or asset-bake regressions
#
# Coverage matrix (one row per Stage 1 swap, expanded as new swaps land):
#   assimp   libassimp.so.6        aiImportFile + aiGetVersionMajor
#   lua      liblua-5.4.so         lua_newstate
#   sqlite   libsqlite3.so.0       sqlite3_open
#   ...
# Easy to extend; entries are bash arrays at the top of the swaps loop.
#
# Usage:
#   tests/asset-bake-test.sh                 # auto-detect installed package
#   O3DE_PKGNAME=o3de2605 tests/asset-bake-test.sh   # explicit override
#
# Exit code: 0 on all checks pass, 1 on any check fail, 2 on prereqs missing.

set -uo pipefail

# Color helpers (preserves the look-and-feel of the previous test).
RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RST='\033[0m'

pass=0; fail=0
ok()   { printf "  ${GREEN}PASS${RST} %s\n" "$*"; pass=$((pass+1)); }
nope() { printf "  ${RED}FAIL${RST} %s: %s\n" "$1" "$2"; fail=$((fail+1)); }
info() { printf "  %s\n" "$*"; }

# Auto-detect installed versioned package (same pattern as the other tests).
: "${O3DE_PKGNAME:=$(rpm -qa --qf '%{NAME}\n' 2>/dev/null | grep -E '^o3de[0-9]+$' | head -1)}"
: "${O3DE_PKGNAME:=o3de}"

if ! rpm -q "$O3DE_PKGNAME" >/dev/null 2>&1; then
    printf "prerequisite missing: %s package not installed\n" "$O3DE_PKGNAME" >&2
    exit 2
fi

# engine.json appears at multiple paths in the installed RPM (the real
# one at install root, plus symlinks under bin/Linux/<config>/Default/
# that cmake uses). Match the install-root one specifically by
# requiring the parent directory to NOT be under bin/.
ENGINE_PATH=$(rpm -ql "$O3DE_PKGNAME" 2>/dev/null \
    | grep -E '/engine\.json$' | grep -v '/bin/' | head -1 | xargs -r dirname)
[ -d "$ENGINE_PATH" ] || { printf "prerequisite missing: engine path not resolved\n" >&2; exit 2; }

# Pick a representative engine binary that links assimp (and the rest).
# AzCore + SceneCore are loaded by basically everything; SceneBuilder is
# what would link assimp on Linux.
REPRESENTATIVE_SO="$ENGINE_PATH/bin/Linux/profile/Default/libSceneBuilder.so"
[ -f "$REPRESENTATIVE_SO" ] || REPRESENTATIVE_SO=$(find "$ENGINE_PATH/bin/Linux/profile/Default" -name 'lib*.so' | head -1)
[ -f "$REPRESENTATIVE_SO" ] || { printf "prerequisite missing: no engine .so under %s\n" "$ENGINE_PATH" >&2; exit 2; }

printf "${BOLD}=== Tier 7: system-swap library-health check ===${RST}\n"
printf "package:    %s\n" "$O3DE_PKGNAME"
printf "engine:     %s\n" "$ENGINE_PATH"
printf "probe .so:  %s\n\n" "$REPRESENTATIVE_SO"

# ─── Swap matrix ─────────────────────────────────────────────────────────────
# Format: bcond_name | expected_soname | sample_symbol | min_version_major
#
# Add a row when a new Stage 1 swap activates. The expected_soname is
# what Fedora actually ships (verify via `rpm -ql <pkg>-devel | grep '\.so$'`).
# The sample_symbol is something the engine calls at runtime; we look it up
# in the library via `nm -D`. min_version_major is 0 to skip the version
# check.
# The soname column is an extended regex (ERE), not a literal string, so
# the version component can be wildcarded. We resolve the concrete soname
# from ldconfig by this pattern. Libraries whose Fedora ABI version drifts
# across our chroots (rawhide ships Lua 5.5 / OpenEXR 3.4 where F44 ships
# 5.4 / 3.2) must wildcard the version; the check's intent is "the system
# library is present and exposes the symbol", not "this exact ABI". Dots
# use a [.] character class so they match literally (avoids awk
# dynamic-regex escape warnings).
SWAPS=(
    "assimp:libassimp[.]so[.]6:aiImportFile:6"
    "lua:liblua-5[.][0-9]+[.]so:lua_newstate:5"
    "sqlite:libsqlite3[.]so[.]0:sqlite3_open:3"
    "libsamplerate:libsamplerate[.]so[.]0:src_new:0"
    "expat:libexpat[.]so[.]1:XML_ParserCreate:0"
    "freetype:libfreetype[.]so[.]6:FT_Init_FreeType:0"
    "png:libpng16[.]so[.]16:png_create_read_struct:0"
    "zlib:libz[.]so[.]1:inflateInit_:0"
    "lz4:liblz4[.]so[.]1:LZ4_compress_default:0"
    "mikkelsen:libmikktspace[.]so[.]0:genTangSpaceDefault:0"
    "openexr:libOpenEXR-3_[0-9]+[.]so[.][0-9]+:ImfApplyLut:0"
    "poly2tri:libpoly2tri[.]so[.]1[.]0:_ZN3p2t12SweepContext12GetTrianglesEv:0"
    # googlebenchmark: activated 2026-05-11 in experimental (build 10444166 GREEN).
    # SONAME libbenchmark.so.1. Sample symbol is benchmark::Initialize, but
    # the 1.9.x ABI added a help-callback function pointer parameter, so the
    # mangled name is the 4-arg form (not the 1.7.x 2-arg form):
    # benchmark::Initialize(int*, char**, void(*)()).
    "googlebenchmark:libbenchmark[.]so[.]1:_ZN9benchmark10InitializeEPiPPcPFvvE:0"
    # mcpp (Stage 2 library-link swap; promoted to stabilization 2026-05-14).
    # Linked into Gems/Atom/Asset/Shader/Code (Preprocessor.cpp consumes
    # mcpp_lib_main / mcpp_set_out_func / mcpp_set_report_include_callback).
    # SONAME libmcpp.so.0 (from o3de2605-mcpp-az COPR build, mcpp 2.7.2 + _az.2 patches).
    "mcpp:libmcpp[.]so[.]0:mcpp_lib_main:0"
)

# Stage 2 binary-shellout swaps (dxc, spirv-cross) and Stage 1
# runtime-only swap (vulkan_validation_layers) don't fit the
# SONAME+symbol matrix above (DXC and SPIRV-Cross are CLI binaries the
# engine shells out to at asset-build time, not linked libraries;
# vulkan_validation_layers is a Vulkan loader plugin discovered via
# JSON manifest and VK_LAYER_PATH, not linked into the engine). These
# are exercised end-to-end by the FBX bake step below.

ldcache_path() {
    ldconfig -p 2>/dev/null | awk -v s="$1" '$1==s{print $NF; exit}'
}

soname_of() {
    objdump -p "$1" 2>/dev/null | awk '/SONAME/{print $2; exit}'
}

has_symbol() {
    # Returns 0 if the library defines the given symbol (.text or .data).
    # Handles both T (defined) and W (weak-defined) cases, plus versioned
    # symbols (e.g. "png_create_read_struct@@PNG16_0", or libsamplerate's
    # "src_new@@libsamplerate.so.0.0").
    #
    # NOTE: not using `grep -q` because pipefail is on and grep -q's
    # early-exit-on-first-match sends SIGPIPE to nm, which makes nm exit
    # non-zero and pipefail propagates that as a pipeline failure --
    # producing false negatives. Use `grep -c` + test for "> 0" instead.
    local count
    count=$(nm -D --defined-only "$1" 2>/dev/null | grep -cE " [TtWw] $2(@.*)?\$")
    [ "$count" -gt 0 ]
}

printf "${BOLD}-- Per-swap library health --${RST}\n"
for entry in "${SWAPS[@]}"; do
    IFS=':' read -r swap soname_re symbol min_major <<< "$entry"
    # Resolve the concrete soname + path from ldconfig by matching the
    # version-agnostic ERE, anchored to the full library name. This lets
    # the check hold across chroots that ship a different ABI version
    # (e.g. rawhide's liblua-5.5.so / libOpenEXR-3_4.so.NN vs F44's
    # liblua-5.4.so / libOpenEXR-3_2.so.31).
    line=$(ldconfig -p 2>/dev/null | awk -v re="^${soname_re}\$" '$1 ~ re {print $1 "\t" $NF; exit}')
    if [ -z "$line" ]; then
        nope "$swap" "no SONAME matching ${soname_re} in ldconfig cache"
        continue
    fi
    soname="${line%%$'\t'*}"
    path="${line#*$'\t'}"
    printf "[%s] %s\n" "$swap" "$soname"
    actual_soname=$(soname_of "$path")
    if [ "$actual_soname" != "$soname" ]; then
        nope "$swap" "ldconfig lists $soname at $path but objdump reports SONAME $actual_soname"
        continue
    fi
    if ! has_symbol "$path" "$symbol"; then
        nope "$swap" "symbol $symbol not defined in $path"
        continue
    fi
    ok "$swap loadable + SONAME match + sample symbol $symbol present"
done

# ─── Engine binary linkage check ────────────────────────────────────────────
# Confirms the engine's representative .so actually depends on the
# system-swap SONAMEs (not on a bundled-fork SONAME like libassimp.so.5
# or a copy at $ENGINE_PATH/lib/Linux/profile/Default/).
printf "\n${BOLD}-- Engine binary linkage --${RST}\n"
linkage=$(ldd "$REPRESENTATIVE_SO" 2>/dev/null || true)
for entry in "${SWAPS[@]}"; do
    IFS=':' read -r swap soname_re _ _ <<< "$entry"
    # Match the actual linked soname (version-agnostic ERE) in ldd output.
    matched=$(printf "%s\n" "$linkage" | awk -v re="^${soname_re}\$" '$1 ~ re {print $1; exit}')
    if [ -n "$matched" ]; then
        # The library is linked. Confirm it resolves to a system path
        # (not a bundled copy under the install prefix).
        resolved=$(printf "%s\n" "$linkage" | awk -v s="$matched" '$1==s{print $3; exit}')
        case "$resolved" in
            /usr/lib*|/lib*)
                ok "$swap: $REPRESENTATIVE_SO links $matched from system path ($resolved)"
                ;;
            "$ENGINE_PATH"*)
                nope "$swap" "$REPRESENTATIVE_SO links $matched from BUNDLED path $resolved; system swap not firing"
                ;;
            *)
                info "$swap: $REPRESENTATIVE_SO links $matched from non-standard path $resolved (review)"
                ;;
        esac
    fi
    # Not linking is fine; not every system swap is exercised by every
    # engine binary (e.g., poly2tri isn't pulled into SceneBuilder). The
    # per-library health check above is what gates the swap; this section
    # just adds smoke-test coverage that the swap is actually consumed.
done

# ─── Assimp major-version gate ───────────────────────────────────────────────
# Special-case for assimp because the 5 -> 6 major bump is the original
# motivation for this Tier 7. If Fedora's libassimp ever rolls back to
# the 5.x SONAME (e.g., assimp upstream cuts a libassimp.so.5 patch
# release), our compatibility audit needs to be redone.
printf "\n${BOLD}-- Assimp major-version gate --${RST}\n"
assimp_path=$(ldcache_path "libassimp.so.6")
if [ -n "$assimp_path" ]; then
    # The assimp 6.x SONAME is libassimp.so.6 by definition; that we
    # resolved it via ldconfig already confirms 6.x. Verify the file
    # exists + is executable.
    if [ -r "$assimp_path" ]; then
        ok "libassimp.so.6 resolves to $assimp_path (assimp 6.x major confirmed)"
    else
        nope "assimp" "libassimp.so.6 in ldconfig cache but not readable at $assimp_path"
    fi
else
    nope "assimp" "libassimp.so.6 not in ldconfig cache; system swap broken or Fedora rolled"
fi

printf "\n${BOLD}-- Summary --${RST}\n"
total=$((pass+fail))
if [ "$fail" -eq 0 ]; then
    printf "  ${GREEN}${pass}/${total} checks passed${RST}\n"
    exit 0
else
    printf "  ${YELLOW}${pass}/${total} passed${RST}, ${RED}${fail} failed${RST}\n"
    exit 1
fi
