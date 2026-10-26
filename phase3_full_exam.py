"""Phase 3 valve acceptance on the FULL exam (1,517 rows) — extension of CAS-LAB-013.

Reuses the same controller and the same fixture oracle as the accepted 300-row run, but does not assert a fixed
row count. Diagnostic only until run on AWS under a preregistration.

    python phase3_full_exam.py --generation <jsonl> --exam <jsonl> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from aws_phase3_driver import _verify_receipt
from test_phase3_valve_ctt_acceptance import _expected_failure
from tks_meta_valve_controller import TKSMetaValveController

from decimal import Decimal


def rows(path: str):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def evaluate(generations, exam_items):
    valve = TKSMetaValveController(default_aperture=Decimal("0.75"))
    s = {"items": 0, "fixture_rule_violations": 0, "admitted": 0, "clamped_g_absent": 0,
         "fixture_rule_violations_admitted": 0, "fixture_compliant_items_refused": 0,
         "receipts_recomputed": 0, "unique_full_receipts": 0}
    digests = set()
    mismatches = []
    for tick, (item, gen) in enumerate(zip(exam_items, generations), start=1):
        proposal = str(gen.get("text", ""))
        expected = _expected_failure(item, proposal)
        result = valve.evaluate_ctt_proposal(tick=tick, item=item, proposal_text=proposal)
        if result["failure_reason"] != expected:
            mismatches.append({"id": item.get("id"), "controller": result["failure_reason"], "oracle": expected})
        if not _verify_receipt(result):
            mismatches.append({"id": item.get("id"), "error": "receipt_digest_mismatch"})
        s["items"] += 1
        s["receipts_recomputed"] += 1
        digests.add(result["receipt_sha256"])
        if expected:
            s["fixture_rule_violations"] += 1
        if result["admitted"]:
            s["admitted"] += 1
            if expected:
                s["fixture_rule_violations_admitted"] += 1
        else:
            s["clamped_g_absent"] += 1
            if not expected:
                s["fixture_compliant_items_refused"] += 1
    s["unique_full_receipts"] = len(digests)
    return s, mismatches


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generation", required=True)
    ap.add_argument("--exam", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    exam = rows(a.exam)
    gens = rows(a.generation)
    n = min(len(exam), len(gens))
    summary, mism = evaluate(gens[:n], exam[:n])
    out = {"generation": a.generation, "exam": a.exam, "exam_rows": len(exam), "generation_rows": len(gens),
           "evaluated": n, "summary": summary, "mismatches": mism}
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
