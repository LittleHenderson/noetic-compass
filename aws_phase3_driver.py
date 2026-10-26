"""AWS driver for the bounded Phase 3 G-ABSENT fixture acceptance run."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from test_phase3_valve_ctt_acceptance import _expected_failure, _jsonl
from tks_meta_valve_controller import TKSMetaValveController


INPUT_FILES = (
    "aws_phase3_driver.py",
    "gen_A4-s1_baseline.jsonl",
    "gen_A4-s1_steered_d0.2.jsonl",
    "mouth_exam.jsonl",
    "test_phase3_valve_ctt_acceptance.py",
    "tks_meta_valve_controller.py",
    "tks_meta_valve_weights_v0_4.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_receipt(result: Dict[str, Any]) -> bool:
    payload = result["receipt_payload"]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return result.get("receipt_sha256") == digest and result.get("receipt_hash") == digest[:16]


def _evaluate(generations: List[Dict[str, Any]], exam_items: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    valve = TKSMetaValveController(default_aperture=Decimal("0.75"))
    admitted = 0
    clamped = 0
    fixture_violations = 0
    admitted_violations = 0
    compliant_refusals = 0
    receipt_validated = 0
    receipt_digests = set()
    ledger: List[Dict[str, Any]] = []

    for tick, (item, generated) in enumerate(zip(exam_items, generations), start=1):
        proposal = str(generated.get("text", ""))
        expected_failure = _expected_failure(item, proposal)
        if expected_failure:
            fixture_violations += 1
        result = valve.evaluate_ctt_proposal(tick=tick, item=item, proposal_text=proposal)
        if result["failure_reason"] != expected_failure:
            raise RuntimeError(f"Controller/oracle mismatch for {item.get('id')}")
        if not _verify_receipt(result):
            raise RuntimeError(f"Receipt digest mismatch for {item.get('id')}")
        receipt_validated += 1
        receipt_digests.add(result["receipt_sha256"])

        if result["admitted"]:
            admitted += 1
            if expected_failure:
                admitted_violations += 1
        else:
            clamped += 1
            if not expected_failure:
                compliant_refusals += 1

        ledger.append({
            "id": result["id"],
            "situation": result["situation"],
            "input_text": result["input_text"],
            "raw_proposal": result["raw_proposal"],
            "admitted": result["admitted"],
            "gate_interlock": result["gate_interlock"],
            "status": result["status"],
            "final_response": result["final_response"],
            "failure_reason": result["failure_reason"],
            "fixture_rule_failure": expected_failure,
            "receipt_hash": result["receipt_hash"],
            "receipt_sha256": result["receipt_sha256"],
            "receipt_payload": result["receipt_payload"],
        })

    if len(ledger) != 300 or receipt_validated != 300 or len(receipt_digests) != 300:
        raise RuntimeError("Expected 300 unique, validated receipt records")
    if admitted_violations or compliant_refusals:
        raise RuntimeError("Acceptance oracle and valve decision differ")

    summary = {
        "items": len(ledger),
        "fixture_rule_violations": fixture_violations,
        "admitted": admitted,
        "clamped_g_absent": clamped,
        "fixture_rule_violations_admitted": admitted_violations,
        "fixture_compliant_items_refused": compliant_refusals,
        "receipts_independently_recomputed": receipt_validated,
        "unique_full_sha256_receipts": len(receipt_digests),
        "telemetry": valve.status_summary(),
    }
    return summary, ledger


def main() -> int:
    started = time.perf_counter()
    print("Starting bounded AWS Phase 3 fixture acceptance run")
    print(f"Time (UTC): {datetime.now(timezone.utc).isoformat()}")
    print(f"Python: {sys.executable}")

    test_process = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_phase3_valve_ctt_acceptance.py"],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        timeout=300,
    )
    test_log = test_process.stdout + "\n" + test_process.stderr
    print(test_log)
    (HERE / "test_log.txt").write_text(test_log, encoding="utf-8")
    if test_process.returncode != 0:
        print(f"Acceptance tests failed with exit code {test_process.returncode}")
        return test_process.returncode or 1

    all_exam_items = _jsonl(HERE / "mouth_exam.jsonl")
    exam_items = all_exam_items[:300]
    baseline = _jsonl(HERE / "gen_A4-s1_baseline.jsonl")[:300]
    steered = _jsonl(HERE / "gen_A4-s1_steered_d0.2.jsonl")[:300]
    if len(exam_items) != 300 or len(baseline) != 300 or len(steered) != 300:
        raise RuntimeError("The AWS payload does not contain all 300 aligned records")

    baseline_summary, baseline_ledger = _evaluate(baseline, exam_items)
    steered_summary, steered_ledger = _evaluate(steered, exam_items)
    manifest_path = HERE / "input_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("files", []):
        path = HERE / entry["file"]
        if not path.is_file() or path.stat().st_size != entry["size_bytes"] or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"Source manifest mismatch for {entry['file']}")
    hashes = {name: _sha256(HERE / name) for name in INPUT_FILES}

    payload = {
        "schema": "phase3-valve-fixture-acceptance/v2",
        "execution_target": "AWS_PHASE3_META_VALVE_CTT_ACCEPTANCE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "acceptance_tests_passed": True,
        "cloud_run": {
            "run_id": os.environ.get("PHASE3_RUN_ID", "unavailable"),
            "s3_prefix": os.environ.get("PHASE3_S3_PREFIX", "unavailable"),
            "instance_type": os.environ.get("PHASE3_INSTANCE_TYPE", "unavailable"),
        },
        "scope": {
            "source_exam_rows": len(all_exam_items),
            "evaluated_rows": 300,
            "selection": "first 300 rows in mouth_exam.jsonl order",
            "oracle": "structured lexical fixture rules; not a general factual-truth or language-understanding test",
            "receipt_note": "SHA-256 hashes are deterministic integrity checks and are not signatures or proof of who executed the run",
        },
        "input_sha256": hashes,
        "input_manifest_sha256": _sha256(manifest_path),
        "input_manifest": manifest,
        "summary": {
            "baseline": baseline_summary,
            "steered_d0_2": steered_summary,
        },
        "baseline_ledger": baseline_ledger,
        "steered_d0_2_ledger": steered_ledger,
    }
    (HERE / "phase3_valve_acceptance_results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Measured result summary:")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    print("Scope: 300 fixture rows; lexical checks only; no general zero-hallucination claim.")
    print("Acceptance tests passed and all receipt hashes were recomputed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
