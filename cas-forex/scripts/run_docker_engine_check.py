"""Run the CAS Forex Docker Engine diagnosis used by mobile readiness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.mobile_release_readiness import (  # noqa: E402
    docker_check_to_dict,
    render_docker_engine_check,
    run_docker_engine_check,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose local Docker Engine availability for CAS Forex.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--exit-code-on-failure", action="store_true", help="Exit 1 when Docker Engine is not ready.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    check = run_docker_engine_check()
    if args.json:
        print(json.dumps(docker_check_to_dict(check), indent=2, sort_keys=True))
    else:
        print(render_docker_engine_check(check))
    if args.exit_code_on_failure and not check.success:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
