"""Advance the owner-approved Risen live handoff without placing an order."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.risen_live_handoff import (
    STATUS_READY_FOR_PREFLIGHT,
    run_risen_live_handoff,
)


DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "risen-live-handoff-latest.json"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the configured Risen live account, start read-only broker truth, "
            "and apply evidence-qualified recovery without placing an order."
        )
    )
    parser.add_argument("--interval-seconds", type=int, default=120)
    parser.add_argument("--no-start-monitor", action="store_true")
    parser.add_argument("--no-apply-recovery", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = run_risen_live_handoff(
        interval_seconds=max(5, int(args.interval_seconds)),
        start_monitor=not args.no_start_monitor,
        apply_recovery=not args.no_apply_recovery,
    )
    _write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report.get("status") == STATUS_READY_FOR_PREFLIGHT else 2


if __name__ == "__main__":
    raise SystemExit(main())
