"""Fixture-level acceptance checks for the Phase 3 G-ABSENT interlock.

The test oracle is lexical and limited to the structured fields in mouth_exam:
entity, value, slot, replacement, repeated-token, and reply-shape checks. It is
not a general test of factual truth or natural-language understanding.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tks_meta_valve_controller import TKSMetaValveController


SLOT_FORMS = {
    "moved": {"move", "moves", "moving", "moved"},
    "went": {"go", "goes", "going", "went", "gone"},
    "ended": {"end", "ends", "ending", "ended"},
    "came": {"come", "comes", "coming", "came"},
    "drove": {"drive", "drives", "driving", "drove", "driven"},
    "looked": {"look", "looks", "looking", "looked"},
    "colonies": {"colony", "colonies"},
    "buses": {"bus", "buses"},
    "queens": {"queen", "queens"},
}
REPLACEMENT_NEGATION_CUES = {"not", "never", "instead", "rather"}


def _jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _fact_tokens(text: Any) -> List[str]:
    return re.findall(r"[a-z]+|\d+", str(text or "").lower())


def _slot_values(slot: Any) -> List[str]:
    if slot is None or slot == "":
        return []
    values = slot if isinstance(slot, (list, tuple, set)) else [slot]
    return [str(value) for value in values if str(value).strip()]


def _slot_present(slot_value: str, tokens: Set[str]) -> bool:
    return all(bool(SLOT_FORMS.get(term, {term}) & tokens) for term in _fact_tokens(slot_value))


def _unnegated_replacement(tokens: List[str], old_value: str) -> bool:
    old_terms = _fact_tokens(old_value)
    width = len(old_terms)
    for index in range(0, len(tokens) - width + 1):
        if tokens[index:index + width] != old_terms:
            continue
        nearby = tokens[max(0, index - 3):index]
        if not (REPLACEMENT_NEGATION_CUES & set(nearby)):
            return True
    return False


def _expected_failure(item: Dict[str, Any], proposal_text: str) -> str:
    """Independent fixture oracle; keep its checks explicit for auditability."""
    text = (proposal_text or "").strip()
    if not text:
        return "empty proposal"

    repeat_words = re.findall(r"[a-z']+|\d+", text.lower())
    for left, right in zip(repeat_words, repeat_words[1:]):
        if left == right:
            return f"repetitive stuttering: '{left}' twice in a row"

    situation = item.get("situation", "UNKNOWN")
    reading = item.get("reading") or {}
    source_tokens = set(_fact_tokens(item.get("input_text", "")))
    proposal_tokens = _fact_tokens(text)
    proposal_token_set = set(proposal_tokens)

    if situation in ("ANSWER", "SAYBACK", "ASK"):
        thing = str(reading.get("thing") or "")
        thing_terms = _fact_tokens(thing)
        if thing_terms and not all(term in source_tokens for term in thing_terms):
            return f"input does not ground prerequisite entity: '{thing}'"
        if thing_terms and not all(term in proposal_token_set for term in thing_terms):
            return f"missing prerequisite entity: '{thing}'"

        value = str(reading.get("value") or "")
        value_terms = _fact_tokens(value)
        if value_terms and not all(term in source_tokens for term in value_terms):
            return f"input does not ground prerequisite value: '{value}'"
        if value_terms and not all(term in proposal_token_set for term in value_terms):
            return f"missing prerequisite value: '{value}'"

        for slot_value in _slot_values(reading.get("slot")):
            if not _slot_present(slot_value, source_tokens):
                return f"input does not ground prerequisite slot: '{slot_value}'"
            if not _slot_present(slot_value, proposal_token_set):
                return f"missing prerequisite slot: '{slot_value}'"

        replaces = str(reading.get("replaces") or "")
        if replaces:
            replace_terms = _fact_tokens(replaces)
            if replace_terms and not all(term in source_tokens for term in replace_terms):
                return f"input does not ground replaced value: '{replaces}'"
            if replaces.lower() != value.lower() and _unnegated_replacement(proposal_tokens, replaces):
                return f"unresolved replaced value: '{replaces}'"

    question_marks = text.count("?")
    if situation == "ASK" and (question_marks != 1 or not text.endswith("?")):
        return "ASK shape violation (must end with single '?')"
    if situation in ("ANSWER", "SAYBACK") and question_marks > 0:
        return "invalid question mark in factual assertion"
    return ""


def _expected_receipt_payload(item: Dict[str, Any], proposal: str, result: Dict[str, Any]) -> Dict[str, Any]:
    reading = item.get("reading") or {}
    return {
        "schema": "tks-meta-valve-receipt/v1",
        "id": item.get("id", f"item_{result['telemetry'].tick}"),
        "input_text": item.get("input_text", ""),
        "reading": {
            "thing": str(reading.get("thing") or ""),
            "value": str(reading.get("value") or ""),
            "slot": reading.get("slot"),
            "replaces": reading.get("replaces"),
        },
        "proposal_text": (proposal or "").strip(),
        "admitted": result["admitted"],
        "gate_interlock": result["gate_interlock"],
        "status": result["status"],
        "final_response": result["final_response"],
        "failure_reason": result["failure_reason"],
    }


class TestPhase3ValveCTTAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exam_path = HERE / "mouth_exam.jsonl"
        cls.baseline_gen_path = HERE / "gen_A4-s1_baseline.jsonl"
        cls.steered_gen_path = HERE / "gen_A4-s1_steered_d0.2.jsonl"
        cls.all_exam_items = _jsonl(cls.exam_path)
        cls.exam_items = cls.all_exam_items[:300]
        cls.baseline_gen = _jsonl(cls.baseline_gen_path)[:300]
        cls.steered_gen = _jsonl(cls.steered_gen_path)[:300]

    def _evaluate_set(self, generations: List[Dict[str, Any]]) -> Dict[str, Any]:
        valve = TKSMetaValveController(default_aperture="0.75")
        admitted = 0
        clamped = 0
        fixture_violations = 0
        admitted_violations = 0
        refused_compliant = 0
        hashes: Set[str] = set()
        receipts: List[Dict[str, Any]] = []

        for tick, (item, generated) in enumerate(zip(self.exam_items, generations), start=1):
            proposal = str(generated.get("text", ""))
            expected_reason = _expected_failure(item, proposal)
            if expected_reason:
                fixture_violations += 1
            result = valve.evaluate_ctt_proposal(tick=tick, item=item, proposal_text=proposal)

            self.assertEqual(result["id"], item.get("id"))
            self.assertEqual(result["failure_reason"], expected_reason)
            self.assertEqual(result["receipt_payload"], _expected_receipt_payload(item, proposal, result))
            canonical = json.dumps(result["receipt_payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            full_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            self.assertEqual(result["receipt_sha256"], full_digest)
            self.assertEqual(result["receipt_hash"], full_digest[:16])
            self.assertEqual(len(result["receipt_hash"]), 16)
            self.assertEqual(len(result["receipt_sha256"]), 64)
            hashes.add(result["receipt_sha256"])

            if expected_reason:
                self.assertFalse(result["admitted"])
                self.assertEqual(result["gate_interlock"], "G-ABSENT")
                self.assertEqual(result["status"], "VALVE_HALT_G-ABSENT")
                self.assertTrue(result["final_response"].startswith("I cannot provide that reading: missing essential prerequisite ("))
                self.assertNotEqual(result["final_response"], proposal)
                clamped += 1
            else:
                self.assertTrue(result["admitted"])
                self.assertEqual(result["gate_interlock"], "GATE_PASS")
                self.assertEqual(result["status"], "SUCCESS_EVALUATED")
                self.assertEqual(result["final_response"], proposal.strip())
                admitted += 1

            if result["admitted"] and expected_reason:
                admitted_violations += 1
            if not result["admitted"] and not expected_reason:
                refused_compliant += 1

            receipts.append({
                "id": result["id"],
                "situation": result["situation"],
                "input_text": result["input_text"],
                "raw_proposal": result["raw_proposal"],
                "admitted": result["admitted"],
                "gate_interlock": result["gate_interlock"],
                "status": result["status"],
                "final_response": result["final_response"],
                "failure_reason": result["failure_reason"],
                "receipt_hash": result["receipt_hash"],
                "receipt_sha256": result["receipt_sha256"],
                "receipt_payload": result["receipt_payload"],
            })

        self.assertEqual(len(receipts), 300)
        self.assertEqual(len(hashes), 300)
        self.assertEqual(admitted + clamped, 300)
        self.assertEqual(admitted_violations, 0)
        self.assertEqual(refused_compliant, 0)
        summary = valve.status_summary()
        self.assertEqual(summary["proposals_received"], 300)
        self.assertEqual(summary["admitted_to_held"], admitted)
        self.assertEqual(summary["clamped_halts"], clamped)
        return {
            "admitted": admitted,
            "clamped": clamped,
            "fixture_violations": fixture_violations,
            "admitted_violations": admitted_violations,
            "refused_compliant": refused_compliant,
            "unique_receipts": len(hashes),
            "ledger": receipts,
            "telemetry": summary,
        }

    def test_01_data_integrity(self) -> None:
        self.assertGreaterEqual(len(self.all_exam_items), 300)
        self.assertEqual(len(self.exam_items), 300)
        self.assertEqual(len(self.baseline_gen), 300)
        self.assertEqual(len(self.steered_gen), 300)
        exam_ids = [item.get("id") or item.get("input_key") for item in self.exam_items]
        self.assertEqual(len(set(exam_ids)), 300)
        for item, baseline, steered in zip(self.exam_items, self.baseline_gen, self.steered_gen):
            expected_id = item.get("id") or item.get("input_key")
            self.assertEqual(baseline.get("id") or baseline.get("input_key"), expected_id)
            self.assertEqual(steered.get("id") or steered.get("input_key"), expected_id)

    def test_02_baseline_prerequisites_and_receipts(self) -> None:
        result = self._evaluate_set(self.baseline_gen)
        self.assertGreaterEqual(result["fixture_violations"], 78)
        self.assertEqual(result["admitted"], 300 - result["fixture_violations"])
        print(
            "\n[FIXTURE CHECK] Baseline proposals: "
            f"{result['admitted']} admitted, {result['clamped']} clean refusals; "
            f"{result['fixture_violations']} fixture-rule violations; "
            f"{result['unique_receipts']} receipts independently recomputed."
        )

    def test_03_steered_prerequisites_and_receipts(self) -> None:
        result = self._evaluate_set(self.steered_gen)
        print(
            "[FIXTURE CHECK] Steered proposals: "
            f"{result['admitted']} admitted, {result['clamped']} clean refusals; "
            f"{result['fixture_violations']} fixture-rule violations; "
            f"{result['unique_receipts']} receipts independently recomputed."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
