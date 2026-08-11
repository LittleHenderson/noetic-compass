"""Print the current CAS Forex mobile/web verification plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.mobile_verification_plan import (
    DEFAULT_OUTPUT_DIR,
    build_mobile_verification_plan,
    mobile_verification_plan_to_json,
    render_mobile_verification_plan,
    write_mobile_verification_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Evidence output directory.")
    parser.add_argument("--json", action="store_true", help="Print the redacted plan as JSON instead of text.")
    parser.add_argument("--no-write", action="store_true", help="Do not write the evidence packet.")
    parser.add_argument(
        "--exit-code-on-any-gate",
        action="store_true",
        help="Exit 1 unless the verification plan status is verified.",
    )
    args = parser.parse_args()

    plan = build_mobile_verification_plan(workspace_root=_REPO_ROOT)
    paths = None if args.no_write else write_mobile_verification_plan(
        plan,
        workspace_root=_REPO_ROOT,
        output_dir=args.output_dir,
    )
    if args.json:
        payload = dict(plan)
        if paths:
            payload["written_paths"] = paths
        print(mobile_verification_plan_to_json(payload))
    else:
        print(render_mobile_verification_plan(plan))
        if paths:
            print(f"Written JSON: {paths['json_path']}")
            print(f"Written README: {paths['readme_path']}")
    if args.exit_code_on_any_gate and plan.get("status") != "verified":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
