"""Run PCBA compiler-enforced safety negative evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_safety import run_pcba_negative_safety_eval  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=r"..\docs\working\pcba_safety_eval_20260617.json")
    parser.add_argument("--store", default=r"..\docs\working\pcba_safety_eval_20260617.jsonl")
    args = parser.parse_args()

    report = run_pcba_negative_safety_eval(store_path=args.store)
    text = json.dumps(report.model_dump(mode="json"), indent=2)
    print(text)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    return 0 if report.negative_safety_eval_pass and report.evidence_anchor_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
