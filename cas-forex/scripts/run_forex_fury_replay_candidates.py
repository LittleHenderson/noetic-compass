"""Build CAS replay/backtest candidates from the latest Forex Fury set import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.forex_fury_candidates import (
    DEFAULT_OUTPUT_DIR,
    build_forex_fury_replay_candidates,
    write_forex_fury_replay_candidate_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated CAS Forex replay-candidate reports.",
    )
    parser.add_argument("--min-profit-factor", type=float, default=1.2)
    parser.add_argument("--max-equity-drawdown-pct", type=float, default=70.0)
    parser.add_argument("--max-candidates", type=int, default=24)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the normalized summary without writing report files.",
    )
    args = parser.parse_args()

    if args.summary_only:
        report = build_forex_fury_replay_candidates(
            min_profit_factor=args.min_profit_factor,
            max_equity_drawdown_pct=args.max_equity_drawdown_pct,
            max_candidates=args.max_candidates,
        )
        print(json.dumps(report["summary"], indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    paths = write_forex_fury_replay_candidate_report(
        args.output_dir,
        min_profit_factor=args.min_profit_factor,
        max_equity_drawdown_pct=args.max_equity_drawdown_pct,
        max_candidates=args.max_candidates,
    )
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

