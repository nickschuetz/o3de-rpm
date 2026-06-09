#!/usr/bin/env python3
"""Probe: has the o3de/o3de qt6 branch merged into the development branch yet?

Why this exists: when qt6 merges into development, the o3de-development Sunday
cron starts building a Qt6 engine. Our spec's Qt6 build deps, dangling-Requires
excludes, and PySide6 rpath cleanup are all fenced behind the `qt6` bcond, which
is NOT set on the o3de-development chroots today. The flip (add `qt6` to those
chroots) has to land in the window between the merge and the next cron, or the
cron build fails at link / ships dangling requires. We cannot pre-flip, because
--with qt6 on a still-Qt5 tree is wrong. So we watch for the merge instead.

The discriminating signal (Linux x86_64 3rdParty Qt association on development):
  today (Qt5, NOT merged):  qt-5.15.2-revN-linux  + pyside2-5.15.2.1-...-linux
  after the qt6 merge:      qt-6.x-revN-linux      + pyside6-6.x-...-linux
Note: the qt6 branch keeps aarch64 on Qt5, so x86_64 (our Fedora target arch) is
the file that actually flips.

Matching is version-agnostic on purpose (qt-6 major, not the exact rev) so an
upstream rev bump does not spuriously flip the verdict. See
feedback_ci_tests_must_be_version_agnostic.

Outage vs drift: a failed/timed-out fetch, a missing file, or an unparseable
layout returns UNKNOWN, never NOT-YET. A red probe might be the probe failing to
see, not the merge having happened. See feedback_drift_detector_outage_vs_drift.

Exit codes:
  0   NOT-YET   development is still Qt5; no action.
  10  MERGED    development carries Qt6/PySide6 now; run the FOLLOW_UPS.md
                "TRIGGER: qt6 merges into o3de/development" flip BEFORE the next
                o3de-development cron tick.
  2   UNKNOWN   could not fetch or parse; re-probe, do not assume not-merged.
"""

import base64
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

REPO = "o3de/o3de"
# Override only for testing (e.g. QT6_PROBE_BRANCH=qt6 to exercise the MERGED
# path against the branch we expect to land). Production watches development.
BRANCH = os.environ.get("QT6_PROBE_BRANCH", "development")
FILE_PATH = "cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake"
# The qt6 -> development merge PR (o3de/o3de#19567, "Build against Qt6.10.2",
# base development <- head qt6). Reported as an informational signal; the
# authoritative verdict stays the BuiltInPackages Qt pin, which is what a build
# actually pulls (the pin flips to Qt6 in the same commit the PR merges).
MERGE_PR = 19567
TIMEOUT = 20

NOT_YET, MERGED, UNKNOWN = 0, 10, 2

# Match the package whose TARGETS is exactly "Qt" (not pyside*), version-agnostic.
QT_LINE = re.compile(r"PACKAGE_NAME\s+(qt-\S+)\s+TARGETS\s+Qt\b")
PYSIDE_ANY = re.compile(r"PACKAGE_NAME\s+(pyside\S+)")


def fetch_via_gh():
    """Authenticated fetch through the gh CLI (handles rate limits / private)."""
    out = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{FILE_PATH}",
         "-f", f"ref={BRANCH}", "--jq", ".content"],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"gh api failed: {out.stderr.strip() or 'empty output'}")
    return base64.b64decode(out.stdout).decode("utf-8", "replace")


def fetch_via_raw():
    """Fallback: unauthenticated raw.githubusercontent fetch."""
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{FILE_PATH}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch():
    errors = []
    for name, fn in (("gh api", fetch_via_gh), ("raw.githubusercontent", fetch_via_raw)):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - any failure means try the next source
            errors.append(f"{name}: {exc}")
    print("UNKNOWN: could not fetch the 3rdParty manifest from either source.")
    for e in errors:
        print(f"  - {e}")
    return None


def pr_status_line():
    """Best-effort one-line status of the qt6 -> development merge PR (gh only)."""
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{REPO}/pulls/{MERGE_PR}",
             "--jq", "[.state, (.merged|tostring), (.mergeable_state // \"?\")] | @tsv"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        state, merged, mstate = (out.stdout.strip().split("\t") + ["?", "?", "?"])[:3]
        if merged == "true":
            return f"  merge PR #{MERGE_PR}: MERGED"
        return f"  merge PR #{MERGE_PR}: {state} (mergeable_state={mstate})"
    except Exception:  # noqa: BLE001 - informational only; never block the verdict
        return None


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    print(f"qt6-merge probe @ {stamp}  ({REPO}:{BRANCH})")
    print(f"  file: {FILE_PATH}")
    pr_line = pr_status_line()
    if pr_line:
        print(pr_line)

    content = fetch()
    if content is None:
        return UNKNOWN

    qt_match = QT_LINE.search(content)
    pyside = PYSIDE_ANY.findall(content)

    if not qt_match:
        print("UNKNOWN: could not find the 'TARGETS Qt' association line. The "
              "3rdParty layout may have changed; inspect the file by hand.")
        return UNKNOWN

    qt_pkg = qt_match.group(1)
    print(f"  Qt package: {qt_pkg}")
    print(f"  PySide:     {', '.join(pyside) if pyside else '(none found)'}")

    has_pyside6 = any(p.startswith("pyside6") for p in pyside)

    if qt_pkg.startswith("qt-6") or has_pyside6:
        print()
        print("MERGED: development now carries Qt6/PySide6. The qt6 branch has "
              "landed. ACTION: add `qt6` to the o3de-development chroots BEFORE "
              "the next cron tick (see FOLLOW_UPS.md > 'TRIGGER: qt6 merges into "
              "o3de/development'), then rebuild.")
        return MERGED

    if qt_pkg.startswith("qt-5"):
        print()
        print("NOT-YET: development is still Qt5. No action.")
        return NOT_YET

    print()
    print(f"UNKNOWN: unexpected Qt major in '{qt_pkg}'. Inspect by hand.")
    return UNKNOWN


if __name__ == "__main__":
    sys.exit(main())
