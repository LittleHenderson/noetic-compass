"""Print a combined CAS Forex phone/APK/Docker proof session."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.mobile_proof_session import (  # noqa: E402
    build_mobile_proof_session,
    mobile_proof_session_to_json,
    render_mobile_proof_session,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show the current CAS Forex external mobile proof gates in one owner session."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--watch-phone", action="store_true", help="Wait for real phone proof before printing final state.")
    parser.add_argument("--timeout-seconds", type=float, default=180.0, help="Phone-proof wait timeout.")
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="Phone-proof polling interval.")
    parser.add_argument("--exit-code-on-any-gate", action="store_true", help="Exit 1 unless all proof gates are verified.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    session = build_mobile_proof_session(
        workspace_root=_REPO_ROOT,
        watch_phone=args.watch_phone,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    print(mobile_proof_session_to_json(session) if args.json else render_mobile_proof_session(session))
    if args.exit_code_on_any_gate and session.status != "verified":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
