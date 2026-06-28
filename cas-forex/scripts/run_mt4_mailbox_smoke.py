"""Create a CAS Forex MT4 mailbox smoke probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.broker.mt4_mailbox_bridge import build_mt4_mailbox_probe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mailbox-dir",
        default="evidence_runs/mt4_mailbox_smoke",
        help="Mailbox directory to create/use.",
    )
    parser.add_argument(
        "--status-path",
        default=None,
        help="Optional path for the smoke status JSON. Defaults to <mailbox-dir>/mt4-mailbox-smoke-status.json.",
    )
    args = parser.parse_args()

    report = build_mt4_mailbox_probe(args.mailbox_dir)
    status_path = Path(args.status_path) if args.status_path else Path(args.mailbox_dir) / "mt4-mailbox-smoke-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    report["status_path"] = str(status_path)
    status_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
