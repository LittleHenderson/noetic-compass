"""Wait for verified CAS Forex phone browser/PWA proof."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.mobile_phone_verifier import (  # noqa: E402
    phone_proof_watch_status,
    phone_proof_watch_status_to_json,
    render_phone_proof_watch_status,
    wait_for_phone_proof,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch local CAS Forex evidence until a real phone opens Quick Start over LAN."
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0, help="How long to wait for verified proof.")
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="How often to check evidence while waiting.")
    parser.add_argument("--no-wait", action="store_true", help="Read the current proof status once and exit.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--exit-code-on-missing", action="store_true", help="Exit 1 unless phone proof is verified.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.no_wait:
        status = phone_proof_watch_status(workspace_root=_REPO_ROOT)
    else:
        if not args.json:
            initial = phone_proof_watch_status(workspace_root=_REPO_ROOT)
            if not initial.phone_browser_verified:
                print("Initial phone proof status:")
                print(render_phone_proof_watch_status(initial))
                print()
                print(
                    "Waiting up to "
                    f"{args.timeout_seconds:g}s for verified real-phone proof..."
                )
                print(flush=True)
        status = wait_for_phone_proof(
            workspace_root=_REPO_ROOT,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
    if args.json:
        print(phone_proof_watch_status_to_json(status))
    else:
        if not args.no_wait:
            print("Final phone proof status:")
        print(render_phone_proof_watch_status(status))
    if args.exit_code_on_missing and not status.phone_browser_verified:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
