#!/usr/bin/env python3
"""Snapshot the download counters shown on the hellaenergy COPR project pages.

COPR's API does not return these numbers, so this reads each project page's
"Repo Download" table. Each table row is one distro release (fedora-44,
centos-stream-10, ...) and carries two different counters, written as
separate CSV rows so nothing is counted twice:

  counter=packages        one row per release AND architecture: RPM/SRPM
                          files downloaded from that chroot ("(N)*" on the
                          page). COPR's backend counts these from its download
                          logs (copr_log_hitcounter, copr-aws-s3-hitcounter)
                          and pushes them to the frontend in batches; when
                          those jobs run is set in Fedora's infrastructure,
                          not in fedora-copr/copr, so measure the cadence from
                          the snapshots instead of assuming it.
  counter=repo_downloads  one row per release, arch left empty: requests for
                          the release's .repo file (dnf4 `dnf copr enable`, the
                          download button) or for api_3/rpmrepo (dnf5 `dnf copr
                          enable`). The frontend counts these on each request.

Both are running totals since the chroot was created; look at differences
between snapshots. Our own test installs count too.

Usage: scripts/copr-download-stats.py [--csv FILE] [project ...]
  With no projects: every project owned by hellaenergy.
  With --csv: append to FILE (header written when FILE is new); otherwise
  print to stdout. Exits 1 if any project could not be read; rows for the
  projects that were read are still written.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
import urllib.request

OWNER = "hellaenergy"
COPR = "https://copr.fedorainfracloud.org"
FIELDS = ["snapshot_utc", "project", "release", "arch", "counter", "value"]

ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
REPO_RE = re.compile(r'/repo/([^/"]+)/[^"]*\.repo".*?\((\d+) downloads\)', re.S)
ARCH_RE = re.compile(r"\b(x86_64|aarch64|ppc64le|s390x|i386)\b\s*(?:<a[^>]*>\[modified\]</a>)?\s*"
                     r'<small class="text-muted">\s*\((\d+)\)\*', re.S)


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def projects():
    data = json.loads(fetch(f"{COPR}/api_3/project/list?ownername={OWNER}&limit=200"))
    return sorted(p["name"] for p in data["items"])


def counters(project):
    """Yield (release, arch, counter, value) for one project page."""
    page = fetch(f"{COPR}/coprs/{OWNER}/{project}/").split("Repo Download", 1)
    if len(page) != 2:
        raise RuntimeError("no 'Repo Download' table on the project page")
    found = False
    for row in ROW_RE.findall(page[1].split("</table>", 1)[0]):
        repo = REPO_RE.search(row)
        if not repo:
            continue
        release = repo.group(1)
        found = True
        yield release, "", "repo_downloads", int(repo.group(2))
        for arch, packages in ARCH_RE.findall(row):
            yield release, arch, "packages", int(packages)
    if not found:
        raise RuntimeError("no counters parsed; has the page layout changed?")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="append rows to this CSV file")
    ap.add_argument("project", nargs="*")
    args = ap.parse_args()

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    rows, failed = [], []
    for project in args.project or projects():
        try:
            rows += [[stamp, project, *r] for r in counters(project)]
        except Exception as err:  # keep the other projects' rows
            failed.append(project)
            print(f"{project}: {err}", file=sys.stderr)

    new = bool(args.csv) and not os.path.exists(args.csv)
    out = open(args.csv, "a", newline="") if args.csv else sys.stdout
    writer = csv.writer(out)
    if new or not args.csv:
        writer.writerow(FIELDS)
    writer.writerows(rows)
    if args.csv:
        out.close()
        print(f"{len(rows)} rows appended to {args.csv}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
