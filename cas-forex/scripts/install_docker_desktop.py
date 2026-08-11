"""Install Docker Desktop through winget and record the attempt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.docker_desktop_install import (  # noqa: E402
    render_docker_desktop_install_attempt,
    run_docker_desktop_install_attempt,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Docker Desktop through winget and save evidence.")
    parser.add_argument("--timeout-seconds", type=float, default=900.0, help="Maximum winget install time.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--exit-code-on-failure", action="store_true", help="Exit 1 if the install attempt did not complete.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_docker_desktop_install_attempt(timeout_seconds=args.timeout_seconds)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_docker_desktop_install_attempt(report))
    if args.exit_code_on_failure and not report.get("success"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
