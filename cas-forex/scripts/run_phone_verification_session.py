"""Write and print the latest CAS Forex phone verification session."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.phone_verification_session import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    build_phone_verification_session,
    render_phone_verification_session,
    write_phone_verification_session,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize current CAS Forex phone/PWA/APK verification state and next actions."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Evidence output directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown text.")
    parser.add_argument("--no-write", action="store_true", help="Do not write the evidence packet.")
    parser.add_argument(
        "--exit-code-on-any-gate",
        action="store_true",
        help="Exit 1 unless the phone verification session has no remaining gates.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_phone_verification_session(workspace_root=_REPO_ROOT)
    paths = None if args.no_write else write_phone_verification_session(
        report,
        workspace_root=_REPO_ROOT,
        output_dir=args.output_dir,
    )
    payload = dict(report)
    if paths:
        payload["written_paths"] = paths
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_phone_verification_session(payload))
        if paths:
            print(f"Written JSON: {paths['json_path']}")
            print(f"Written README: {paths['readme_path']}")
    if args.exit_code_on_any_gate and report.get("status") != "verified":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
