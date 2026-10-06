"""
Plan the Render -> AWS hostname sweep across the repository.

The Render customer API host appears in 42 files. Not all of them should change:

* historical records (CHANGELOG, the migration document) describe what happened and must
  keep naming Render;
* the Render blueprints and its control manifest describe Render infrastructure that still
  exists and are retired separately;
* the production runbook was already updated by hand and records Render under a
  "Superseded" heading.

Everything else - application code, evidence-collector scripts, the Atlas viewer and its
tests, the landing site, and the test suite - should point at the AWS origin.

Run with --apply to write the changes. Default is a dry run.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

OLD = "cas-harness-customer-api.onrender.com"
DEFAULT_NEW = "api.noeticcompass.com"

# Files that must keep naming Render, with the reason.
EXCLUDE = {
    "noetic-compass-scaffold/noetic-compass/CHANGELOG.md":
        "historical record of the outage and migration",
    "noetic-compass-scaffold/noetic-compass/docs/working/render_to_aws_lane_migration_2026_09_26.md":
        "the migration record itself",
    "noetic-compass-scaffold/noetic-compass/docs/working/render_to_aws_lane_migration_2026_09_26.md":
        "the migration record itself",
    ".render/blueprint-control.json":
        "describes Render infrastructure that still exists; retired in step 7",
    "render.customer.yaml":
        "Render blueprint, retired with the Render services",
    "render.canary.yaml":
        "Render blueprint, retired with the Render services",
    "render.yaml":
        "Render blueprint, retired with the Render services",
    "noetic-compass-scaffold/noetic-compass/docs/runbooks/customer_production_acceptance.md":
        "already edited by hand: names the AWS origin and keeps Render under a Superseded heading",
    "noetic-compass-scaffold/noetic-compass/docs/DEPLOYMENT.md":
        "documents both providers by design; needs a hand edit, not a blind replace",
    "scripts/verify_aws_deployment_control.py":
        "this verifier greps FOR the Render host to prove the runbook no longer names it",
    "scripts/verify_render_blueprint_control.py":
        "the Render verifier; retired with the Render services in step 7",
    "scripts/tests/test_verify_render_blueprint_control.py":
        "tests the Render verifier; retired with it",
}


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "grep", "-l", OLD, "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # `git grep <pattern> HEAD` prefixes each path with "HEAD:".
        files.append(line.split(":", 1)[1] if line.startswith("HEAD:") else line)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--new", default=DEFAULT_NEW, help="replacement hostname")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    files = tracked_files(root)

    to_change, kept = [], []
    for rel in files:
        (kept if rel in EXCLUDE else to_change).append(rel)

    print(f"files naming {OLD}: {len(files)}")
    print(f"  would rewrite: {len(to_change)}")
    print(f"  left alone:    {len(kept)}")
    print()
    print("left alone deliberately:")
    for rel in kept:
        print(f"  {rel}\n      {EXCLUDE[rel]}")
    print()
    print(f"would rewrite {OLD} -> {args.new}:")
    total = 0
    for rel in to_change:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        hits = text.count(OLD)
        total += hits
        print(f"  {hits:>2}  {rel}")
    print()
    print(f"total occurrences to rewrite: {total}")

    if not args.apply:
        print("\ndry run: nothing written. Re-run with --apply to make the changes.")
        return 0

    for rel in to_change:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(OLD, args.new), encoding="utf-8")
    print(f"\nrewrote {len(to_change)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
