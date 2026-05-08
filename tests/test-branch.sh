#!/bin/bash
# End-to-end test driver for an arbitrary O3DE git ref on Fedora.
# Builds a snapshot RPM from <ref>, installs it, runs the integration
# test suite. Designed for O3DE community use: validate that your
# development branch / release candidate works as a Fedora RPM
# without needing to know rpmbuild internals.
#
# Usage:
#   tests/test-branch.sh <git-ref>                 # snapshot mode
#   tests/test-branch.sh --tag <release-tag>       # stable mode
#   tests/test-branch.sh stabilization/26050
#   tests/test-branch.sh main
#
# Requirements (fail fast if missing):
#   - Fedora 44+ (or CentOS Stream 10+, F45 etc.)
#   - rpmbuild, git, git-lfs, sudo, dnf
#   - ~70 GB free disk for build artifacts
#   - 4+ hours patience (full build of debug + profile)
#
# Exit code: 0 on full pass, non-zero otherwise. Output is structured
# enough to grep for PASS/FAIL summaries.

set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
MODE=snapshot
REF=""

while [ $# -gt 0 ]; do
    case "$1" in
        --tag)    MODE=stable; REF="$2"; shift 2 ;;
        --help|-h)
            sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        -*) echo "unknown flag: $1" >&2; exit 2 ;;
        *)  REF="$1"; shift ;;
    esac
done

[ -n "$REF" ] || { echo "missing git ref" >&2; exit 2; }

# Distro check
. /etc/os-release
case "$ID-$VERSION_ID" in
    fedora-44|fedora-45|fedora-46|fedora-rawhide) ;;
    rhel-10*|centos-10*) ;;
    *) echo "warning: untested on $PRETTY_NAME — proceeding anyway" >&2 ;;
esac

cd "$REPO_DIR"

if [ "$MODE" = snapshot ]; then
    echo "=== Building snapshot tarball for ref: $REF ==="
    cd sources
    ./make-snapshot-tarball.sh "$REF"
    cd ..
    # Extract the printed values and patch the spec
    TARBALL=$(ls -t sources/o3de-*.tar.gz | head -1)
    COMMIT=$(basename "$TARBALL" | sed 's/^o3de-//; s/\.tar\.gz$//')
    DATE=$(date -d "@$(stat -c %Y "$TARBALL")" +%Y%m%d)
    SHA=$(sha256sum "$TARBALL" | awk '{print $1}')

    # Patch the spec in-place (safe: not committing this)
    sed -i \
        -e "s/^%global snapshot_commit .*/%global snapshot_commit $COMMIT/" \
        -e "s/^%global snapshot_date .*/%global snapshot_date   $DATE/" \
        -e "s/^%global snapshot_sha256 .*/%global snapshot_sha256 $SHA/" \
        o3de.spec

    BUILD_FLAGS="--with snapshot"
else
    echo "=== Stable build for tag: $REF ==="
    # User must have placed the tarball + sha256 already
    BUILD_FLAGS=""
fi

echo
echo "=== Building RPM (this takes hours) ==="
date '+%Y-%m-%d %H:%M:%S %Z'
rpmbuild -bb $BUILD_FLAGS \
    --define "_sourcedir $REPO_DIR/sources" \
    --define "_specdir   $REPO_DIR" \
    o3de.spec

# Match versioned package names (o3de2605, o3de2610, ...) plus the
# legacy unversioned `o3de` form for back-compat during the rename
# transition.
RPM=$(ls -t ~/rpmbuild/RPMS/x86_64/o3de[0-9]*-*.rpm ~/rpmbuild/RPMS/x86_64/o3de-*.rpm 2>/dev/null | head -1)
[ -f "$RPM" ] || { echo "no RPM produced" >&2; exit 1; }
echo "Built: $RPM"

echo
echo "=== Installing ==="
# Remove any previously-installed o3de* package(s) — covers both the
# legacy `o3de` and the versioned `o3de2605` / `o3de2610` forms.
INSTALLED=$(rpm -qa --qf '%{NAME}\n' 2>/dev/null \
    | grep -E '^(o3de[0-9]*)(-debug|-devel)?$' || true)
[ -n "$INSTALLED" ] && sudo dnf remove -y $INSTALLED 2>/dev/null || true
sudo dnf install -y "$RPM"

echo
echo "=== Running integration test suite ==="
"$REPO_DIR/tests/integration-test.sh" --setup --with-project
