"""Generate the read-only CAS Forex adaptive cockpit artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.adaptive_cockpit import (
    build_adaptive_cockpit_payload,
    write_adaptive_cockpit_html,
    write_adaptive_cockpit_payload,
)
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead-id", default="index_tsmom_126_d1", choices=["index_tsmom_126_d1"])
    parser.add_argument("--output-dir", default="evidence_runs/index_tsmom_126_paper_proof")
    parser.add_argument("--mt-history-summary-json", help="Optional MT history import report JSON file.")
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    mt_history = _load_json(args.mt_history_summary_json) if args.mt_history_summary_json else None
    payload = build_adaptive_cockpit_payload(plan, args.output_dir, imported_history_summary=mt_history)
    json_path = write_adaptive_cockpit_payload(payload, args.output_dir)
    html_path = write_adaptive_cockpit_html(payload, args.output_dir)
    print(json.dumps({"json_path": str(json_path), "html_path": str(html_path), "payload": payload}, indent=2, default=str))
    return 0


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

