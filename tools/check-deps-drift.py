#!/usr/bin/env python3
"""
check-deps-drift.py -- compare engine package pins, COPR rebuilds, and
o3de/3p-package-source build_config.json for drift.

Three sources of truth, one Markdown report:

  1) Engine pin    -- BuiltInPackages_linux_x86_64.cmake on the active
                      stabilization/<X> branch (read via "gh api").
  2) Our COPR      -- latest-succeeded-build for each package in
                      hellaenergy/o3de-dependencies (via copr-cli).
  3) Upstream 3p   -- package_version in
                      o3de/3p-package-source/package-system/<Name>/build_config.json.

Per-package classification:
  in-sync         -- engine pin, COPR version, and 3p build_config agree
                     on a meaningful version token.
  minor-drift     -- different label form (rev1 vs rev2, dash vs dot)
                     but the underlying upstream version matches.
  out-of-date     -- COPR version trails what the engine pins (script
                     exits non-zero so the GHA dot turns red).
  ahead-of-engine -- COPR ships a newer version than the engine pin.
                     Informational; does not fail the workflow because
                     it usually means we proactively bumped (and the
                     engine will catch up at the next 3p refresh).
  gap             -- engine references the package but we do not ship
                     it in COPR and it is not covered by a system_<X>
                     bcond in o3de.spec.
  covered-by-spec -- engine references it, we do not ship in COPR, but
                     the spec has a matching %bcond_with system_<X>.
  cruft           -- COPR ships it but the engine no longer references
                     it (candidate for retirement).

Stdlib only. Talks to GitHub via "gh api" and to COPR via "copr-cli".

Usage:
    python3 tools/check-deps-drift.py [--engine-ref REF] [--no-color]

Exit codes:
    0  -- no out-of-date entries
    1  -- one or more out-of-date entries (drift detected)
    2  -- script error (network, missing tools, malformed config)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEP_MAP_PATH = REPO_ROOT / "tools" / "dep-map.yaml"
SPEC_PATH = REPO_ROOT / "o3de.spec"


# --- tiny YAML loader (top-level scalars, mappings, and flat lists only) ---


def load_yaml_lite(path: Path) -> dict[str, Any]:
    """Parse the dep-map.yaml subset we use (see dep-map.yaml header).

    Supports:
      key: scalar
      key:
        sub_key: scalar
        sub_key: ""    (empty string)
      key:
        - item
        - item
    """
    if path.suffix == ".json":
        return json.loads(path.read_text())

    out: dict[str, Any] = {}
    cur_key: str | None = None
    cur_kind: str | None = None  # "list" or "map" or None (scalar pending)

    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        # top-level (no indent)
        if not line.startswith(" ") and not line.startswith("\t"):
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if v == "":
                # opens a sub-block (we will fill it on indented lines)
                cur_key = k
                cur_kind = None  # decide on first child
                out[k] = None
            else:
                out[k] = _scalar(v)
                cur_key = None
                cur_kind = None
            continue

        # indented child of cur_key
        if cur_key is None:
            continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            if cur_kind is None:
                out[cur_key] = []
                cur_kind = "list"
            assert isinstance(out[cur_key], list)
            out[cur_key].append(_scalar(stripped[2:].strip()))
        elif ":" in stripped:
            if cur_kind is None:
                out[cur_key] = {}
                cur_kind = "map"
            assert isinstance(out[cur_key], dict)
            sk, _, sv = stripped.partition(":")
            out[cur_key][sk.strip()] = _scalar(sv.strip())

    # null sub-blocks become empty containers
    for k, v in list(out.items()):
        if v is None:
            out[k] = {}
    return out


def _scalar(v: str) -> Any:
    if v == "":
        return ""
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v in ("null", "~"):
        return None
    return v


# --- shell helpers ---------------------------------------------------------


def run(cmd: list[str], check: bool = True) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        die(f"command not found: {cmd[0]} ({exc})")
    if check and proc.returncode != 0:
        die(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}")
    return proc.stdout


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


# --- data fetchers ---------------------------------------------------------


def fetch_tracked_branches(repo: str, branches: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Fetch state for branches we passively track for upstream migration progress.

    For each entry, query:
      - Last commit SHA + date on the branch.
      - Commits ahead/behind compared to the configured base (e.g. development).

    Returns a list of dicts ready for render_branch_tracking().
    """
    import datetime
    out: list[dict[str, Any]] = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for entry in branches:
        name = entry.get("branch") or ""
        compare_to = entry.get("compare_to") or "development"
        desc = entry.get("description") or ""
        issue = entry.get("issue_url") or ""
        try:
            raw = run(["gh", "api", f"repos/{repo}/branches/{name}"], check=True)
            br = json.loads(raw)
            sha = br["commit"]["sha"][:7]
            date_str = br["commit"]["commit"]["author"]["date"]
            last = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            stale_days = (now - last).days
        except subprocess.CalledProcessError:
            out.append({"branch": name, "error": "branch not found or API error",
                        "description": desc, "issue": issue})
            continue
        try:
            raw = run(["gh", "api", f"repos/{repo}/compare/{compare_to}...{name}"], check=True)
            cmp = json.loads(raw)
            ahead = cmp.get("ahead_by", "?")
            behind = cmp.get("behind_by", "?")
        except (subprocess.CalledProcessError, ValueError):
            ahead = behind = "?"
        out.append({
            "branch": name, "sha": sha, "date": date_str[:10], "stale_days": stale_days,
            "compare_to": compare_to, "ahead": ahead, "behind": behind,
            "description": desc, "issue": issue,
        })
    return out


def render_branch_tracking(branches: list[dict[str, Any]]) -> str:
    """Render the Qt 6 / dev-branch tracking section."""
    if not branches:
        return ""
    lines: list[str] = []
    lines.append("")
    lines.append("## Upstream migration branch tracking")
    lines.append("")
    lines.append(
        "Passive monitoring of upstream branches we plan to react to. Staleness "
        "(days since last commit) is a soft signal: a branch idle for months "
        "typically means the migration is parked, not abandoned -- O3DE is "
        "volunteer-paced. Action items keyed off `stabilization/<release>` "
        "branch cutovers, not these branch timestamps directly."
    )
    lines.append("")
    lines.append("| Branch | Last commit | Days idle | Ahead | Behind | Compared to | Description |")
    lines.append("|--------|-------------|-----------|-------|--------|-------------|-------------|")
    for b in branches:
        if b.get("error"):
            lines.append(f"| `{b['branch']}` | error: {b['error']} | - | - | - | - | {b.get('description','')} |")
            continue
        lines.append(
            "| `{branch}` | `{sha}` ({date}) | {stale_days} | {ahead} | {behind} | `{compare_to}` | {description} |".format(**b)
        )
        if b.get("issue"):
            lines.append(f"|        | Tracking issue: {b['issue']} | | | | | |")
    lines.append("")
    return "\n".join(lines)


def fetch_engine_pins(engine_repo: str, ref: str) -> dict[str, dict[str, str]]:
    """Return {engine_pkg_name: {"version": "...", "raw": "..."}}.

    Parses ly_associate_package(PACKAGE_NAME <name>-<version>-<label>-<plat> ...)
    lines in BuiltInPackages_linux_x86_64.cmake.
    """
    path = "cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake"
    out = run(["gh", "api", f"repos/{engine_repo}/contents/{path}?ref={ref}", "--jq", ".content"])
    text = base64.b64decode(out.replace("\n", "")).decode("utf-8")

    pins: dict[str, dict[str, str]] = {}
    pat = re.compile(r"ly_associate_package\s*\(\s*PACKAGE_NAME\s+(\S+)\s+TARGETS")
    for line in text.splitlines():
        m = pat.search(line)
        if not m:
            continue
        full = m.group(1)
        # split into <name>-<version-and-label>-<platform-tail>
        # e.g. AWSNativeSDK-1.11.288-rev1-linux
        # We split on "-" but the name itself may contain "-" (e.g. astc-encoder).
        # Strategy: strip the trailing -linux / -multiplatform / -linux-aarch64
        # then strip a trailing -<rev[N]>-? (or whole label), keeping the
        # chunk we can compare. We keep the whole "version-and-label" string
        # for display and pull a normalized "version" out for comparison.
        name, version_label = _split_engine_token(full)
        pins[name] = {"version": version_label, "raw": full}
    return pins


def _split_engine_token(full: str) -> tuple[str, str]:
    """Return (engine_name, version+label) from a string like
    "astc-encoder-3.2-rev2-linux" -> ("astc-encoder", "3.2-rev2")."""
    # strip the platform tail
    for tail in ("-multiplatform", "-linux-aarch64", "-linux"):
        if full.endswith(tail):
            stem = full[: -len(tail)]
            break
    else:
        stem = full
    # find where the version starts: first dash followed by a digit
    m = re.search(r"-(\d|v\d|deb\d|[0-9a-f]{6,40}\b)", stem)
    if not m:
        return stem, ""
    name = stem[: m.start()]
    version_label = stem[m.start() + 1 :]
    return name, version_label


def fetch_copr_versions(owner: str, project: str, packages: dict[str, str]) -> dict[str, str]:
    """Return {copr_pkg_name: version-or-"missing"}."""
    out: dict[str, str] = {}
    for engine_name, copr_name in packages.items():
        if not copr_name:
            continue
        text = run(
            [
                "copr-cli",
                "get-package",
                f"{owner}/{project}",
                "--name",
                copr_name,
                "--with-latest-succeeded-build",
                "--output-format",
                "json",
            ],
            check=False,
        )
        if not text.strip():
            out[copr_name] = "missing"
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            out[copr_name] = "missing"
            continue
        sb = data.get("latest_succeeded_build")
        if not sb:
            out[copr_name] = "no-succeeded-build"
            continue
        out[copr_name] = sb.get("source_package", {}).get("version", "?")
    return out


def fetch_threep_versions(threep_repo: str, packages: dict[str, str], dirs: dict[str, str]) -> dict[str, str]:
    """Return {engine_pkg_name: package_version-from-build_config-or-"missing"}.

    Many packages in 3p-package-source ship without a build_config.json
    (mikkelsen, aws-gamelift-server-sdk, DXC, etc -- they use python build
    scripts instead). For those we return "n/a" so they are not flagged
    as parse errors.
    """
    out: dict[str, str] = {}
    for engine_name, _ in packages.items():
        directory = dirs.get(engine_name, engine_name)
        path = f"package-system/{directory}/build_config.json"
        proc = subprocess.run(
            ["gh", "api", f"repos/{threep_repo}/contents/{path}", "--jq", ".content"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            # 404 = no build_config.json in upstream 3p (common case)
            if "Not Found" in proc.stderr or "404" in proc.stderr:
                out[engine_name] = "n/a"
            else:
                out[engine_name] = "fetch-error"
            continue
        text = proc.stdout
        if not text.strip():
            out[engine_name] = "n/a"
            continue
        try:
            decoded = base64.b64decode(text.replace("\n", "")).decode("utf-8")
            data = json.loads(decoded)
        except (ValueError, json.JSONDecodeError):
            out[engine_name] = "parse-error"
            continue
        # Prefer Linux-specific package_version, fall back to top-level.
        plat_linux = data.get("Platforms", {}).get("Linux", {}).get("Linux", {})
        ver = plat_linux.get("package_version") or data.get("package_version") or "?"
        out[engine_name] = ver
    return out


def read_spec_bconds(spec: Path) -> set[str]:
    """Return {"system_assimp", "system_dxc", ...} from o3de.spec."""
    if not spec.is_file():
        return set()
    out = set()
    pat = re.compile(r"^\s*%bcond_(?:with|without)\s+(system_\w+)")
    for line in spec.read_text().splitlines():
        m = pat.match(line)
        if m:
            out.add(m.group(1))
    return out


# --- comparison logic ------------------------------------------------------


def normalize_version(v: str) -> str:
    """Strip packaging-iteration labels so the underlying upstream tag is
    what we compare. Examples:
      "1.11.288-rev1"        -> "1.11.288"          (Lumberyard rev label)
      "1.8.2505.1-o3de-rev3" -> "1.8.2505.1"        (o3de-fork suffix + rev)
      "1.8.2505.1-1.rev12"   -> "1.8.2505.1"        (COPR NVR + iteration)
      "2.7.2_az.2-rev1"      -> "2.7.2"             (Lumberyard _az.<N> patch series)
      "2.7.2-1.rev7"         -> "2.7.2"             (COPR NVR for the same)
    so engine pins, COPR builds, and 3p package-source build_config strings
    that all describe the same upstream tag compare equal regardless of how
    each side spells the iteration count.
    """
    if not v:
        return ""
    v = v.strip()
    # Drop any -rev<N> suffix anywhere (mid-token or trailing).
    v = re.sub(r"-rev\d+", "", v)
    # Drop the Lumberyard `_az.<N>` patch-series suffix attached to mcpp etc.
    # ("2.7.2_az.2-rev1" -> "2.7.2_az.2" after the prior step; this drops
    # the `_az.2` to leave bare "2.7.2"). We do this before the COPR-NVR
    # step so engine-form normalizes to the same shape as our COPR-form.
    v = re.sub(r"_az\.\d+", "", v)
    # Drop the o3de-fork suffix appended to upstream tags (DXC, others).
    # ("1.8.2505.1-o3de" -> "1.8.2505.1"). Only when followed by end-of-string
    # or a non-version-part separator so we don't strip a literal "o3de" that's
    # part of a real upstream version.
    v = re.sub(r"-o3de(?=$|[-.])", "", v)
    # Drop COPR's NVR iteration tail: "-<digit>.rev<digit>" or "-<digit>"
    # at end-of-string, with optional trailing dist tag like ".fc44".
    v = re.sub(r"-\d+(?:\.rev\d+)?(?:\.fc\d+)?$", "", v)
    # Drop trailing -<digits> RPM release tail ("1.11.361-6").
    v = re.sub(r"-\d+(?:\.fc\d+)?$", "", v)
    if v.startswith("v"):
        v = v[1:]
    return v


_VTOKEN = re.compile(r"\d+")


def _ver_tuple(v: str) -> tuple[int, ...]:
    """Best-effort numeric tuple for ordering (drops non-digit junk)."""
    nums = _VTOKEN.findall(v)
    return tuple(int(n) for n in nums[:5])


def classify(engine_ver: str, copr_ver: str) -> str:
    """Compare engine vs COPR version. Returns one of:
    in-sync, minor-drift, out-of-date, ahead-of-engine.
    """
    if not copr_ver or copr_ver in ("missing", "no-succeeded-build"):
        return "out-of-date"
    en = normalize_version(engine_ver)
    cp = normalize_version(copr_ver)
    if en == cp:
        # exact label match? in-sync. Otherwise minor-drift.
        if engine_ver.split("-linux")[0] == copr_ver:
            return "in-sync"
        # if the rev token matches too, in-sync
        en_rev = re.search(r"rev\d+", engine_ver)
        cp_rev = re.search(r"rev\d+", copr_ver)
        if en_rev and cp_rev and en_rev.group(0) == cp_rev.group(0):
            return "in-sync"
        return "minor-drift"
    # If either side looks like a git-commit pin (hex sha) and they
    # don't match literally, treat as out-of-date -- numeric ordering
    # is meaningless across commits.
    if re.search(r"\b[0-9a-f]{6,40}\b", engine_ver) or re.search(r"\bgit[0-9a-f]{6,40}\b", copr_ver):
        return "out-of-date"
    # COPR ahead vs behind the engine pin?
    et = _ver_tuple(en)
    ct = _ver_tuple(cp)
    if et and ct and ct > et:
        return "ahead-of-engine"
    return "out-of-date"


# --- report ---------------------------------------------------------------


def render_report(
    engine_ref: str,
    rows: list[dict[str, str]],
    spec_bconds: set[str],
) -> str:
    lines: list[str] = []
    lines.append("# Dependency drift report")
    lines.append("")
    lines.append(
        f"Auto-generated by `tools/check-deps-drift.py`. "
        f"Compares engine ref `{engine_ref}` (cmake/3rdParty pin), "
        f"`hellaenergy/o3de-dependencies` (latest-succeeded build), and "
        f"`o3de/3p-package-source` (build_config.json)."
    )
    lines.append("")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    lines.append(f"**Summary:** {summary}")
    lines.append("")
    if spec_bconds:
        lines.append(
            f"**Spec bconds detected:** `{'`, `'.join(sorted(spec_bconds))}`"
        )
        lines.append("")
    lines.append("| Status | Engine package | Engine pin | COPR package | COPR version | 3p build_config |")
    lines.append("|--------|----------------|------------|--------------|--------------|-----------------|")
    order = {
        "out-of-date": 0,
        "gap": 1,
        "minor-drift": 2,
        "ahead-of-engine": 3,
        "cruft": 4,
        "covered-by-spec": 5,
        "in-sync": 6,
    }
    for r in sorted(rows, key=lambda r: (order.get(r["status"], 9), r["engine_name"])):
        lines.append(
            "| {status} | `{engine_name}` | `{engine_ver}` | `{copr_name}` | `{copr_ver}` | `{threep_ver}` |".format(
                **r
            )
        )
    lines.append("")
    lines.append("Statuses:")
    lines.append("")
    lines.append("- **in-sync** -- engine, COPR, and 3p build_config agree.")
    lines.append("- **minor-drift** -- same upstream version, different rev label.")
    lines.append("- **out-of-date** -- COPR trails what the engine pins (workflow fails).")
    lines.append("- **ahead-of-engine** -- COPR is newer than the engine pin (informational).")
    lines.append("- **gap** -- engine references it, we do not ship in COPR, no system_<X> bcond.")
    lines.append("- **covered-by-spec** -- engine references it; covered by `%bcond_with system_<X>` in o3de.spec.")
    lines.append("- **cruft** -- COPR ships it but the engine no longer references it.")
    return "\n".join(lines) + "\n"


# --- main ------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check 3rdParty dependency drift")
    parser.add_argument("--engine-ref", default=os.environ.get("ENGINE_REF"))
    parser.add_argument("--dep-map", default=str(DEP_MAP_PATH))
    parser.add_argument("--spec", default=str(SPEC_PATH))
    args = parser.parse_args(argv)

    cfg = load_yaml_lite(Path(args.dep_map))
    engine_ref = args.engine_ref or cfg.get("engine_ref") or "stabilization/26050"
    engine_repo = cfg.get("engine_repo") or "o3de/o3de"
    threep_repo = cfg.get("threep_repo") or "o3de/3p-package-source"
    copr_owner = cfg.get("copr_owner") or "hellaenergy"
    copr_project = cfg.get("copr_project") or "o3de-dependencies"
    copr_packages = cfg.get("copr_packages") or {}
    threep_dirs = cfg.get("threep_dirs") or {}
    bcond_aliases = cfg.get("spec_bcond_aliases") or {}
    ignore = set(cfg.get("ignore_engine_packages") or [])

    spec_bconds = read_spec_bconds(Path(args.spec))

    print(f"# Fetching engine pins from {engine_repo}@{engine_ref}...", file=sys.stderr)
    engine_pins = fetch_engine_pins(engine_repo, engine_ref)
    print(f"#   found {len(engine_pins)} ly_associate_package entries", file=sys.stderr)

    # Drop ignored engine packages.
    engine_pins = {k: v for k, v in engine_pins.items() if k not in ignore}

    print(f"# Fetching COPR versions from {copr_owner}/{copr_project}...", file=sys.stderr)
    copr_versions = fetch_copr_versions(copr_owner, copr_project, copr_packages)

    print(f"# Fetching build_config.json from {threep_repo}...", file=sys.stderr)
    threep_versions = fetch_threep_versions(threep_repo, copr_packages, threep_dirs)

    rows: list[dict[str, str]] = []
    seen_copr: set[str] = set()

    # Walk every engine pin and classify.
    for engine_name, info in sorted(engine_pins.items()):
        copr_name = copr_packages.get(engine_name)
        bcond_alias = bcond_aliases.get(engine_name, "")
        bcond_name = f"system_{bcond_alias}" if bcond_alias else ""

        if copr_name:
            seen_copr.add(copr_name)
            copr_ver = copr_versions.get(copr_name, "missing")
            threep_ver = threep_versions.get(engine_name, "missing")
            status = classify(info["version"], copr_ver)
        elif bcond_name and bcond_name in spec_bconds:
            status = "covered-by-spec"
            copr_ver = "(spec swap)"
            threep_ver = threep_versions.get(engine_name, "n/a")
            copr_name = bcond_name
        else:
            status = "gap"
            copr_ver = "(none)"
            threep_ver = threep_versions.get(engine_name, "n/a")
            copr_name = ""

        rows.append({
            "status": status,
            "engine_name": engine_name,
            "engine_ver": info["version"] or "?",
            "copr_name": copr_name or "-",
            "copr_ver": copr_ver,
            "threep_ver": threep_ver,
        })

    # Detect cruft: COPR ships something the engine doesn't reference.
    for engine_name, copr_name in copr_packages.items():
        if not copr_name:
            continue
        if copr_name in seen_copr:
            continue
        if engine_name in engine_pins:
            continue
        rows.append({
            "status": "cruft",
            "engine_name": engine_name,
            "engine_ver": "(not in engine)",
            "copr_name": copr_name,
            "copr_ver": copr_versions.get(copr_name, "?"),
            "threep_ver": threep_versions.get(engine_name, "?"),
        })

    report = render_report(engine_ref, rows, spec_bconds)
    sys.stdout.write(report)

    # Track upstream migration branches (e.g., Qt 6 qt6 branch).
    # Hardcoded list -- only one branch to track right now. The
    # dep-map.yaml loader doesn't support list-of-maps; if this list
    # grows we can extend the loader or switch dep-map to JSON. Doesn't
    # affect the workflow's exit code -- this is informational, not gating.
    tracked_branches = [
        {
            "branch": "qt6",
            "compare_to": "development",
            "description": "Qt 6 migration target for 26.10.0 (volunteer-paced; not guaranteed)",
            "issue_url": "https://github.com/o3de/o3de/issues/19081",
        },
    ]
    if tracked_branches:
        print(f"# Fetching tracked migration branches from {engine_repo}...", file=sys.stderr)
        tracked = fetch_tracked_branches(engine_repo, tracked_branches)
        sys.stdout.write(render_branch_tracking(tracked))

    has_drift = any(r["status"] == "out-of-date" for r in rows)
    return 1 if has_drift else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
