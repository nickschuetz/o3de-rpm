#!/bin/bash
# Build a reproducible source tarball from a git ref of o3de/o3de.
# Used for snapshot RPM builds.
#
# Two upstream branches are common targets and they're NOT the same:
#   stabilization/<release>  pre-release stabilization branch — becomes
#                            the next tagged release; ships to community
#                            testers via hellaenergy/o3de-snapshot
#   development              bleeding-edge integration branch — daily
#                            new-feature merges; for engine-contributor
#                            testing of in-progress work
#
# Usage:
#   make-snapshot-tarball.sh [ref]                 # ref defaults to stabilization/26050
#   make-snapshot-tarball.sh stabilization/26050   # next-release branch (recommended)
#   make-snapshot-tarball.sh development           # bleeding-edge HEAD
#   make-snapshot-tarball.sh <commit-sha>          # pinned commit
#
# Output: o3de-<full-commit-sha>.tar.gz in $PWD, plus prints the values to
# paste into o3de.spec (snapshot_commit / snapshot_date / sha256).
set -euo pipefail

REF="${1:-stabilization/26050}"
REPO_URL="${O3DE_REPO_URL:-https://github.com/o3de/o3de.git}"
OUT_DIR="${OUT_DIR:-$PWD}"

command -v git >/dev/null || { echo "error: git not found" >&2; exit 1; }
command -v git-lfs >/dev/null || { echo "error: git-lfs not found (dnf install git-lfs)" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "error: sha256sum not found" >&2; exit 1; }

# O3DE checkout including LFS content is ~5-8 GB; tmpfs /tmp (default
# mktemp target on most Fedora installs) is typically too small. Prefer
# $TMPDIR if set, otherwise $HOME/.cache/o3de-snapshot-tarball which
# lives on the user's home filesystem.
SNAPSHOT_TMP="${TMPDIR:-$HOME/.cache/o3de-snapshot-tarball}"
mkdir -p "$SNAPSHOT_TMP"
WORK="$(mktemp -d -p "$SNAPSHOT_TMP")"
trap 'rm -rf "$WORK"' EXIT

echo ">> cloning $REPO_URL @ $REF"
git -C "$WORK" clone --depth 1 --branch "$REF" "$REPO_URL" o3de

pushd "$WORK/o3de" >/dev/null
COMMIT="$(git rev-parse HEAD)"
COMMIT_DATE="$(git show -s --format=%cd --date=format:%Y%m%d HEAD)"

echo ">> fetching LFS objects"
git lfs pull

# Drop git metadata so the tarball is reproducible across clones.
rm -rf .git .gitattributes
popd >/dev/null

mv "$WORK/o3de" "$WORK/o3de-$COMMIT"
TARBALL="$OUT_DIR/o3de-$COMMIT.tar.gz"

echo ">> creating $TARBALL"
# Sorted, fixed mtime, fixed owner/group → reproducible tarball.
tar --sort=name \
    --owner=0 --group=0 --numeric-owner \
    --mtime="@$(git -C /dev/null log -1 --format=%ct 2>/dev/null || echo 0)" \
    -C "$WORK" \
    -czf "$TARBALL" "o3de-$COMMIT"

SHA="$(sha256sum "$TARBALL" | awk '{print $1}')"

cat <<EOF

Snapshot tarball built: $TARBALL

Update o3de.spec with these values:
  %global snapshot_commit $COMMIT
  %global snapshot_date   $COMMIT_DATE
  %global snapshot_sha256 $SHA

Then build:
  rpmbuild --with snapshot --define "_sourcedir \$PWD/sources" \\
           --define "_specdir \$PWD" -bb o3de.spec
EOF
