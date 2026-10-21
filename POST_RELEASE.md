# Post-release runbook

Step-by-step for pushing an upstream O3DE stable release into the `hellaenergy/o3de` COPR channel after upstream tags and merges the release into `main`.

This applies twice yearly (May + October major releases) plus on point releases. Estimated wall-clock: 30-45 minutes start to push, plus 4-6 hours for the COPR build to complete.

## Inputs

- The release tag landed upstream (verify at `https://github.com/o3de/o3de/releases`)
- Upstream's `main` branch tip is the release merge commit (e.g., commit `cf85af7` was the 25.10.2 release merge)
- Release tarball is published at the standard URL pattern: `https://github.com/o3de/o3de/releases/download/<TAG>/o3de-<TAG>-lfs.tar.gz`

## Sequence

### 1. Confirm upstream state

```bash
# Verify the release tag exists upstream
gh api repos/o3de/o3de/tags --jq '.[] | select(.name == "<TAG>") | .commit.sha'

# Verify the tarball URL responds
curl -sI "https://github.com/o3de/o3de/releases/download/<TAG>/o3de-<TAG>-lfs.tar.gz" | head -3
```

If either check fails, stop and ask upstream sig-release (Mike_C usually drives release-day mechanics).

### 2. Pull and checksum the tarball

```bash
cd sources/
curl -L -O "https://github.com/o3de/o3de/releases/download/<TAG>/o3de-<TAG>-lfs.tar.gz"
sha256sum o3de-<TAG>-lfs.tar.gz
```

Put it in this repo's `sources/` rather than `~/rpmbuild/SOURCES/`; the Makefile's `_sourcedir` override and the `release-stable` preflight both expect it there.

Note the sha256 value. You'll paste it into the spec next.

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

If the release is a major (YYMM bump rather than point release), nothing else needs bumping: `o3de_major_tag`, the package name (e.g., `o3de2610`) and the install prefix are all derived from `stable_tag`, and the Makefile's `PKGNAME` derivation follows.

### 4. SBOM bump

In `sources/o3de2605.cdx.json` (or whichever `o3deNNNN` SBOM is current):
- Set `"version": "<TAG>-1"` in both the metadata.component and components entries

If a major bump: the spec's Source13 is `%{o3de_pkgname}.cdx.json`, so it picks the new major's file (`o3de2610.cdx.json`) automatically; create that file if it does not exist yet, and keep the previous major's file for its line.

### 5. Local validation

```bash
make lint          # spec-parse in all four bcond modes, plus rpmlint and the validators
make srpm          # builds the SRPM locally (needs the tarball in sources/)
ls -la ~/rpmbuild/SRPMS/o3de*-<TAG>-*.src.rpm
```

The sha256 is checked by `make release-stable` (step 7) and again in `%prep`. If it reports a mismatch, the tarball you downloaded doesn't match the value you pasted in step 3. Recompute and try again.

### 6. Commit + push

```bash
git add o3de.spec sources/o3de*.cdx.json
git commit -s -m "release: upstream <TAG> stable

Upstream tagged <TAG> on main as commit <merge-sha>. Pulled
o3de-<TAG>-lfs.tar.gz, sha256 <sha256>, into Sources. Spec
bumps stable_tag, stable_sha256, Release; SBOM follows.

This is the first build to hit hellaenergy/o3de for this
release line."

git push origin main
```

### 7. Push to COPR

If the release is a major, first bring the `hellaenergy/o3de` and `hellaenergy/o3de-testing` chroots onto the new line's `--rpmbuild-with` set. They still carry the previous major's set, and `--with` flags on the SRPM do not propagate to the COPR rebuild. Compare against the `o3de-stabilization` chroots (`copr-cli get-chroot hellaenergy/o3de-stabilization/<chroot>`), which built this line during the stabilization window. `edit-chroot --rpmbuild-with` replaces the whole list, so pass the full set and verify with `get-chroot` afterwards.

```bash
make release-stable
```

`release-stable` checks that the spec's sha256 is real and matches the tarball in `sources/`, then runs `make copr-stable`, which fires the build into `hellaenergy/o3de`. Wall time ~4-6 hours across F44 + F45 + rawhide + CS10 chroots.

While waiting: optionally trigger the post-build CI test via `make trigger-tests BUILD_ID=<copr-build-id> COPR_PROJECT=o3de`.

### 8. COPR project metadata update

Update `copr-metadata/o3de/description.md` and `instructions.md` to reflect the live release. Push via the COPR API:

```bash
make copr-metadata-push
```

This refreshes the COPR project page that end users see when they `dnf copr enable hellaenergy/o3de`.

### 9. Update README

In `README.md`, update any version strings that point at the prior release. Bump examples that show `dnf install o3de2605 o3de2605-devel` to the new version if a major changed (install lines always name the `-devel` subpackage too).

### 10. Announce

If you want to surface the build to community testers, post in the O3DE sig-release Discord:
- "26.05.0 RPM is live at hellaenergy/o3de; F44 / F45 / rawhide / CS10. `sudo dnf copr enable hellaenergy/o3de && sudo dnf install o3de2605 o3de2605-devel`"

The announcement is a manual step; no auto-post from the test infrastructure.

## After the first build is GREEN

- Tag the spec commit (e.g., `release/2605.0`) so the post-release state is bookmarked.
- Move on to dev-snapshot cadence: fire `make copr-development` to push a build of the new development tip into `hellaenergy/o3de-development`. This kicks off the next cycle's tracking.

## Between releases (post-release packaging fixes)

The release ceremony above goes direct to stable because the release has soaked in `o3de-stabilization` for weeks already. Routine post-release packaging fixes (a community-reported `Recommends:` gap, a Wayland workaround, a launcher tweak) do NOT go direct to stable. They flow through `hellaenergy/o3de-testing` first:

```bash
make copr-testing-and-test     # build + push to o3de-testing + fire CI tests
# soak ~48 hours; watch for regression reports on the testing channel
make copr-stable               # promote the same SRPM to o3de
```

See `CONTRIBUTING.md` "COPR Projects" section for the channel layout and the rationale.

## Failure modes

- **sha256 mismatch in make srpm**: redownload the tarball; GitHub's CDN may have served partial bytes. Retry the sha256 + paste sequence.
- **COPR build fails at %prep on a carry-patch**: the release tarball may differ from stabilization tip's last state. Check whether any carry-patch needs to retire (on the 26.10 line the stabilization flag set applies only 0003, 0010, 0011, 0014, 0018 and 0020). Sequence: confirm the upstream PR merged, identify the snapshot source branch, verify the merge is reachable from main at the release tag, grep the target file on the release tarball. Only retire when all four checks pass.
- **CS10 fails but F44/F45/rawhide pass**: known historical gaps (libunwind-devel in EPEL-10 not base CS10, RPM 4.19 spec-parser quirks). Check the build log against known CS10-specific blockers before assuming a real regression.

## Related

- `CONTRIBUTING.md`: "COPR Projects" section explains channel topology
- `tests/README.md`: Tier matrix for post-install validation
