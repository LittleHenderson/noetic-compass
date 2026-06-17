from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.cas_harness_goal_claim_auditor import audit_active_goal_claims


DEFAULT_OUT = (
    ROOT
    / "docs"
    / "working"
    / "cas_harness_active_goal_claim_audit_20260617.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the six active CAS Harness goal claims against current artifacts."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--fail-on-open",
        action="store_true",
        help="Exit nonzero when any active-goal claim remains OPEN / NOT LICENSED.",
    )
    args = parser.parse_args()

    result = audit_active_goal_claims(args.root)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    if args.fail_on_open and not result["goal_complete"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

