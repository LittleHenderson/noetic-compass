"""Run the local CAS broker-funding contract sandbox."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.broker_funding_sandbox import create_broker_funding_sandbox_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8775)
    parser.add_argument(
        "--db-path",
        default=str(REPO_ROOT / "runtime" / "broker-funding-sandbox.sqlite3"),
    )
    parser.add_argument("--account-id", default="cas-sandbox-broker-account")
    parser.add_argument("--initial-balance-usd", type=float, default=10_000.0)
    parser.add_argument(
        "--api-key",
        default=os.environ.get(
            "CAS_BROKER_FUNDING_SANDBOX_API_KEY",
            "cas-local-sandbox-api-key",
        ),
    )
    parser.add_argument(
        "--admin-key",
        default=os.environ.get(
            "CAS_BROKER_FUNDING_SANDBOX_ADMIN_KEY",
            "cas-local-sandbox-admin-key",
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    app = create_broker_funding_sandbox_app(
        db_path=Path(args.db_path),
        bound_account_id=args.account_id,
        api_key=args.api_key,
        admin_key=args.admin_key,
        initial_balance_usd=args.initial_balance_usd,
    )
    uvicorn.run(app, host=args.host, port=args.port, workers=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
