# Post-release runbook

Step-by-step for pushing an upstream O3DE stable release into the `hellaenergy/o3de` COPR channel after upstream tags and merges the release into `main`.

This applies twice yearly (May + October major releases) plus on point releases. Estimated wall-clock: 30-45 minutes start to push, plus 4-6 hours for the COPR build to complete.

## Inputs

- The release tag landed upstream (verify at `https://github.com/o3de/o3de/releases`)
- Upstream's `main` branch tip is the release merge commit (e.g., commit `cf85af7` was the 25.10.2 release merge)
- Release tarball is published at the standard URL pattern: `https://github.com/o3de/o3de/releases/download/<TAG>/o3de_<TAG>_lfs.tar.gz`

## Sequence

### 1. Confirm upstream state

```bash
# Verify the release tag exists upstream
gh api repos/o3de/o3de/tags --jq '.[] | select(.name == "<TAG>") | .commit.sha'

# Verify the tarball URL responds
curl -sI "https://github.com/o3de/o3de/releases/download/<TAG>/o3de_<TAG>_lfs.tar.gz" | head -3
```

If either check fails, stop and ask upstream sig-release (Mike_C usually drives release-day mechanics).

### 2. Pull and checksum the tarball

```bash
cd ~/rpmbuild/SOURCES/
curl -L -O "https://github.com/o3de/o3de/releases/download/<TAG>/o3de_<TAG>_lfs.tar.gz"
sha256sum o3de_<TAG>_lfs.tar.gz
```

Note the sha256 value -- you'll paste it into the spec next.

### 3. Spec updates

In `o3de.spec`:

- `%global stable_tag <TAG>` (e.g., `2605.0`)
- `%global stable_sha256 <sha256-from-step-2>`
- `Release: 1%{?dist}` (resets to 1 for a new upstream version)
- Add `%changelog` entry at the top:
  ```
  * <Day Mon DD YYYY> Nick Schuetz <nschuetz@redhat.com> - <TAG>-1
  - Upstream O3DE <TAG> stable release. Tarball pulled from
    https://github.com/o3de/o3de/releases/download/<TAG>/
    sha256: <sha256>.
  - <list any spec changes that landed alongside the release bump>
  ```

If the release is a major (YYMM bump rather than point release):
- Bump `%global o3de_major_tag` if applicable (e.g., 2605 -> 2610)
- The Makefile's `PKGNAME` derivation will pick up the new tag automatically

### 4. SBOM bump

In `sources/o3de2605.cdx.json` (or whichever `o3deNNNN` SBOM is current):
- Set `"version": "<TAG>-1"` in both the metadata.component and components entries

If a major bump: rename the SBOM file to match the new pkgname (`o3de2610.cdx.json`), update the spec's Source13 reference, update the install path in `%install`.

### 5. Local validation

```bash
make spec-parse    # all four bcond modes
make srpm          # builds the SRPM locally; verifies sha256 against Source0
ls -la ~/rpmbuild/SRPMS/o3de*-<TAG>-*.src.rpm
```

If `make srpm` fails on sha256 mismatch, the tarball you downloaded doesn't match the value you pasted in step 3 -- recompute and try again.

### 6. Commit + push

```bash
git add o3de.spec sources/o3de*.cdx.json
git commit -s -m "release: upstream <TAG> stable

Upstream tagged <TAG> on main as commit <merge-sha>. Pulled
o3de_<TAG>_lfs.tar.gz, sha256 <sha256>, into Sources. Spec
bumps stable_tag, stable_sha256, Release; SBOM follows.

This is the first build to hit hellaenergy/o3de for this
release line."

git push origin main
```

### 7. Push to COPR

```bash
make copr-stable
```

This fires the build into `hellaenergy/o3de`. Wall time ~4-6 hours across F44 + rawhide + CS10 chroots.

While waiting: optionally trigger the post-build CI test via `make trigger-tests RPM_URL=<url-from-copr-build>`.

### 8. COPR project metadata update

Update `copr-metadata/o3de/description.md` and `instructions.md` to reflect the live release. Push via the COPR API:

```bash
make copr-metadata-push
```

This refreshes the COPR project page that end users see when they `dnf copr enable hellaenergy/o3de`.

### 9. Update README

In `README.md`, update any version strings that point at the prior release. Bump examples that show `dnf install o3de2605` to the new version if a major changed.

### 10. Announce

If you want to surface the build to community testers, post in the O3DE sig-release Discord:
- "26.05.0 RPM is live at hellaenergy/o3de; F44 / rawhide / CS10. `sudo dnf copr enable hellaenergy/o3de && sudo dnf install o3de2605`"

The announcement is a manual step; no auto-post from the test infrastructure.

## After the first build is GREEN

- Tag the spec commit (e.g., `release/2605.0`) so the post-release state is bookmarked.
- Move on to dev-snapshot cadence: fire `make copr-snapshot-development` to push a build of the new development tip into `hellaenergy/o3de-snapshot`. This kicks off the next cycle's tracking.

## Failure modes

- **sha256 mismatch in make srpm**: redownload the tarball; GitHub's CDN may have served partial bytes. Retry the sha256 + paste sequence.
- **COPR build fails at %prep on a carry-patch**: the release tarball may differ from stabilization tip's last state. Check whether any of our 13 carry-patches need to retire (they should, since they targeted stabilization/26050 and that branch's tip is now folded into main). Sequence: confirm the upstream PR merged, identify the snapshot source branch, verify the merge is reachable from main at the release tag, grep the target file on the release tarball -- only retire when all four checks pass.
- **CS10 fails but F44/rawhide pass**: known historical gaps (libunwind-devel in EPEL-10 not base CS10, RPM 4.19 spec-parser quirks). Check the build log against known CS10-specific blockers before assuming a real regression.

## Related

- `CONTRIBUTING.md` -- "COPR Projects" section explains channel topology
- `tests/README.md` -- Tier matrix for post-install validation
- `MEMORY.md` -- session-history references
