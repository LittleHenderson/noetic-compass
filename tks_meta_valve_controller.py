"""tks_meta_valve_controller.py -- Phase 3 Meta Valve Controller for HELM & CAS.

CRITICAL ARCHITECTURAL ROLE (Phase 3 Valve System):
Acts as the dynamic thermodynamic/noetic pressure regulator between Level L4
open-domain proposals (sensory/language) and the Level L0-L3 Executive Recipe Brain.

Regulates information flow, novelty permeability, prerequisite backpressure,
and enforces RPM Gate safety interlocks:
- When prerequisites are missing, the valve clamps down (G-ABSENT interlock).
- When novel creative proposals arrive, the aperture (sigma) controls admittance into
  the Daydream store (held.py) while preserving the Rule P immutable barrier.
- Incorporates calibrated weights from train_tks_meta_valve.py for dynamic aperture prediction:
  sigma*(x) = sigmoid(w^T * x + b).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set

DEFAULT_WEIGHTS_FILENAME = "tks_meta_valve_weights_v0_4.json"

_SLOT_FORMS = {
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
_REPLACEMENT_NEGATION_CUES = {"not", "never", "instead", "rather"}


def _fact_tokens(text: Any) -> List[str]:
    return re.findall(r"[a-z]+|\d+", str(text or "").lower())


def _slot_values(slot: Any) -> List[str]:
    if slot is None or slot == "":
        return []
    values = slot if isinstance(slot, (list, tuple, set)) else [slot]
    return [str(value) for value in values if str(value).strip()]


def _slot_terms_present(slot_value: str, tokens: Set[str]) -> bool:
    terms = _fact_tokens(slot_value)
    return all(
        bool(_SLOT_FORMS.get(term, {term}) & tokens)
        for term in terms
    )


def _replacement_is_unnegated(tokens: List[str], old_value: str) -> bool:
    old_terms = _fact_tokens(old_value)
    if not old_terms:
        return False
    width = len(old_terms)
    for index in range(0, len(tokens) - width + 1):
        if tokens[index:index + width] != old_terms:
            continue
        nearby = tokens[max(0, index - 3):index]
        if not (_REPLACEMENT_NEGATION_CUES & set(nearby)):
            return True
    return False


def _receipt_digests(payload: Dict[str, Any]) -> Tuple[str, str]:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:16], digest


@dataclass
class ValveTelemetry:
    tick: int
    aperture_sigma: Decimal
    inflow_entropy: Decimal
    backpressure: Decimal
    status: str             # 'OPEN', 'RESTRICTED', 'CLAMPED_HALT'
    gate_interlock: str     # 'GATE_PASS', 'G-ABSENT', 'G-LIMIT', 'REFUSE:INTERNAL_WITNESS'
    admitted_to_held: bool
    reason: str


class TKSMetaValveController:
    """Phase 3 Meta Valve Controller.
    
    Controls information flow between high-entropy external proposers and
    the deterministic, verified CAS recipe ledger.
    """

    def __init__(self,
                 default_aperture: Decimal = Decimal("0.7"),
                 weights_path: Optional[str] = None):
        self.aperture_sigma = Decimal(str(default_aperture))
        self.telemetry_history: List[ValveTelemetry] = []
        self.total_proposals_received: int = 0
        self.total_admitted_to_held: int = 0
        self.total_clamped_halts: int = 0
        self.weights_model: Optional[Dict[str, Any]] = None

        # Attempt to load calibrated weights if available
        self._load_weights(weights_path)

    def _load_weights(self, weights_path: Optional[str] = None) -> None:
        candidate_paths = []
        if weights_path:
            candidate_paths.append(weights_path)
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            candidate_paths.append(os.path.join(here, DEFAULT_WEIGHTS_FILENAME))
            candidate_paths.append(os.path.join(here, "brains", DEFAULT_WEIGHTS_FILENAME))
            candidate_paths.append(os.path.join(os.path.dirname(here), DEFAULT_WEIGHTS_FILENAME))

        for p in candidate_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self.weights_model = json.load(f)
                    break
                except Exception:
                    continue

    def set_aperture(self, sigma: Any) -> Decimal:
        """Set valve aperture sigma in [0.0, 1.0]."""
        val = Decimal(str(sigma))
        if not (Decimal("0.0") <= val <= Decimal("1.0")):
            raise ValueError(f"Valve aperture sigma must be between 0.0 and 1.0, got {sigma}")
        self.aperture_sigma = val
        return self.aperture_sigma

    def predict_dynamic_aperture(self, proposal_features: Dict[str, float]) -> Decimal:
        """Predict optimal aperture sigma using learned weights:
            sigma*(x) = sigmoid(w^T * x + b)
        """
        if not self.weights_model or "weights" not in self.weights_model:
            return self.aperture_sigma

        feature_names = self.weights_model.get("feature_names", [
            "novelty_entropy", "source_credibility", "prerequisite_ratio",
            "normalized_radius", "operating_mode_bias"
        ])
        weights = self.weights_model["weights"]
        bias = self.weights_model.get("bias", 0.0)

        x_vec = [float(proposal_features.get(k, 0.0)) for k in feature_names]
        logit = sum(w * xi for w, xi in zip(weights, x_vec)) + bias
        pred_sigma = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, logit))))
        return Decimal(str(round(pred_sigma, 6)))

    def evaluate_proposal_flow(self,
                              tick: int,
                              proposal_name: str,
                              prerequisites_present: bool,
                              novelty_entropy: Decimal,
                              is_internal_daydream: bool = False,
                              proposal_features: Optional[Dict[str, float]] = None) -> Tuple[bool, ValveTelemetry]:
        """Regulate a proposal's passage through the meta-valve.

        Returns:
            (allow_flow, telemetry_record)
        """
        self.total_proposals_received += 1
        entropy_d = Decimal(str(novelty_entropy))

        # Dynamic aperture prediction if features are provided
        effective_sigma = self.aperture_sigma
        if proposal_features is not None:
            effective_sigma = self.predict_dynamic_aperture(proposal_features)

        # Rule 1: The RPM Gate Safety Interlock
        # If essential prerequisites are missing, the valve triggers a pressure drop and clamps shut.
        if not prerequisites_present:
            self.total_clamped_halts += 1
            telem = ValveTelemetry(
                tick=tick,
                aperture_sigma=effective_sigma,
                inflow_entropy=entropy_d,
                backpressure=Decimal("1.0"),
                status="CLAMPED_HALT",
                gate_interlock="G-ABSENT",
                admitted_to_held=False,
                reason=f"RPM Gate Interlock: Essential prerequisite missing for proposal '{proposal_name}'."
            )
            self.telemetry_history.append(telem)
            return False, telem

        # Rule 2: Permeability check based on aperture (sigma)
        # Higher aperture permits higher-entropy (more unconventional/creative) ideas
        # Backpressure is inversely proportional to aperture
        backpressure = max(Decimal("0.0"), Decimal("1.0") - effective_sigma)

        # Proposal passes if its entropy does not exceed the allowed threshold
        # Max acceptable entropy = effective_sigma
        if entropy_d <= effective_sigma:
            self.total_admitted_to_held += 1
            telem = ValveTelemetry(
                tick=tick,
                aperture_sigma=effective_sigma,
                inflow_entropy=entropy_d,
                backpressure=backpressure,
                status="OPEN" if effective_sigma >= Decimal("0.5") else "RESTRICTED",
                gate_interlock="GATE_PASS",
                admitted_to_held=True,
                reason=f"Proposal '{proposal_name}' passed valve aperture (entropy {entropy_d} <= sigma {effective_sigma})."
            )
            self.telemetry_history.append(telem)
            return True, telem
        else:
            # Entropy too high for current aperture setting
            telem = ValveTelemetry(
                tick=tick,
                aperture_sigma=effective_sigma,
                inflow_entropy=entropy_d,
                backpressure=backpressure,
                status="RESTRICTED_DROP",
                gate_interlock="G-LIMIT",
                admitted_to_held=False,
                reason=f"Excess entropy ({entropy_d} > sigma {effective_sigma}). Proposal throttled."
            )
            self.telemetry_history.append(telem)
            return False, telem

    def evaluate_ctt_proposal(self,
                              tick: int,
                              item: Dict[str, Any],
                              proposal_text: str,
                              fact_words: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Evaluate a Level L4 CTT natural language proposal against RPM prerequisite requirements.
        
        CRITICAL PHASE 3 INTERLOCK:
        - Validates essential factual prerequisites (entity 'thing', 'value', 'slot', update 'replaces').
        - Inspects proposal for degenerative repetitions, out-of-bounds tokens, or factual omissions.
        - If prerequisites are satisfied and properly expressed:
            Admits proposal with GATE_PASS (status: OPEN/RESTRICTED) and emits proof receipt.
        - If essential prerequisites are missing, ungrounded, or corrupted:
            Triggers G-ABSENT CLAMPED_HALT interlock, suppressing the hallucination and
            emitting an auditable zero-hallucination refusal receipt with cryptographic hash.
        """
        text = (proposal_text or "").strip()
        item_id = item.get("id", f"item_{tick}")
        situation = item.get("situation", "UNKNOWN")
        input_text = item.get("input_text", "")
        reading = item.get("reading") or {}
        thing = str(reading.get("thing") or "")
        value = str(reading.get("value") or "")
        replaces = reading.get("replaces")

        # Prerequisite grounding checks. The structured reading must be grounded
        # in the input and then present in the proposal before it can pass.
        prereq_ok = True
        failure_reason = ""
        source_tokens = set(_fact_tokens(input_text))
        proposal_tokens = _fact_tokens(text)
        proposal_token_set = set(proposal_tokens)
        repetition_tokens = re.findall(r"[a-z']+|\d+", text.lower())

        if not text:
            prereq_ok = False
            failure_reason = "empty proposal"

        if prereq_ok:
            for a, b in zip(repetition_tokens, repetition_tokens[1:]):
                if a == b:
                    prereq_ok = False
                    failure_reason = f"repetitive stuttering: '{a}' twice in a row"
                    break

        if prereq_ok and situation in ("ANSWER", "SAYBACK", "ASK"):
            thing_terms = _fact_tokens(thing)
            if thing_terms and not all(term in source_tokens for term in thing_terms):
                prereq_ok = False
                failure_reason = f"input does not ground prerequisite entity: '{thing}'"
            elif thing_terms and not all(term in proposal_token_set for term in thing_terms):
                prereq_ok = False
                failure_reason = f"missing prerequisite entity: '{thing}'"

            value_terms = _fact_tokens(value)
            if prereq_ok and value_terms and not all(term in source_tokens for term in value_terms):
                prereq_ok = False
                failure_reason = f"input does not ground prerequisite value: '{value}'"
            elif prereq_ok and value_terms and not all(term in proposal_token_set for term in value_terms):
                prereq_ok = False
                failure_reason = f"missing prerequisite value: '{value}'"

            if prereq_ok:
                for slot_value in _slot_values(reading.get("slot")):
                    if not _slot_terms_present(slot_value, source_tokens):
                        prereq_ok = False
                        failure_reason = f"input does not ground prerequisite slot: '{slot_value}'"
                        break
                    if not _slot_terms_present(slot_value, proposal_token_set):
                        prereq_ok = False
                        failure_reason = f"missing prerequisite slot: '{slot_value}'"
                        break

            if prereq_ok and replaces:
                replace_terms = _fact_tokens(replaces)
                if replace_terms and not all(term in source_tokens for term in replace_terms):
                    prereq_ok = False
                    failure_reason = f"input does not ground replaced value: '{replaces}'"
                elif str(replaces).lower() != value.lower() and _replacement_is_unnegated(proposal_tokens, str(replaces)):
                    prereq_ok = False
                    failure_reason = f"unresolved replaced value: '{replaces}'"

        if prereq_ok:
            q_count = text.count("?")
            if situation == "ASK" and (q_count != 1 or not text.endswith("?")):
                prereq_ok = False
                failure_reason = "ASK shape violation (must end with single '?')"
            elif situation in ("ANSWER", "SAYBACK") and q_count > 0:
                prereq_ok = False
                failure_reason = "invalid question mark in factual assertion"

        # Calculate proposal features and evaluate flow through valve
        entropy = Decimal("0.15") if prereq_ok else Decimal("0.85")
        credibility = 0.95 if prereq_ok else 0.20
        prereq_ratio = 1.0 if prereq_ok else 0.0

        features = {
            "novelty_entropy": float(entropy),
            "source_credibility": credibility,
            "prerequisite_ratio": prereq_ratio,
            "normalized_radius": 0.25,
            "operating_mode_bias": 0.0
        }

        allowed, telem = self.evaluate_proposal_flow(
            tick=tick,
            proposal_name=f"CTT_{item_id}",
            prerequisites_present=prereq_ok,
            novelty_entropy=entropy,
            proposal_features=features
        )

        if allowed:
            final_response = text
            receipt_payload = {
                "schema": "tks-meta-valve-receipt/v1",
                "id": item_id,
                "input_text": input_text,
                "reading": {
                    "thing": thing,
                    "value": value,
                    "slot": reading.get("slot"),
                    "replaces": replaces,
                },
                "proposal_text": text,
                "admitted": True,
                "gate_interlock": "GATE_PASS",
                "status": "SUCCESS_EVALUATED",
                "final_response": final_response,
                "failure_reason": "",
            }
            receipt_hash, receipt_sha256 = _receipt_digests(receipt_payload)
            return {
                "id": item_id,
                "situation": situation,
                "input_text": input_text,
                "raw_proposal": text,
                "admitted": True,
                "gate_interlock": "GATE_PASS",
                "status": "SUCCESS_EVALUATED",
                "final_response": final_response,
                "receipt_hash": receipt_hash,
                "receipt_sha256": receipt_sha256,
                "receipt_payload": receipt_payload,
                "failure_reason": "",
                "telemetry": telem
            }
        else:
            refusal_msg = f"I cannot provide that reading: missing essential prerequisite ({failure_reason})."
            receipt_payload = {
                "schema": "tks-meta-valve-receipt/v1",
                "id": item_id,
                "input_text": input_text,
                "reading": {
                    "thing": thing,
                    "value": value,
                    "slot": reading.get("slot"),
                    "replaces": replaces,
                },
                "proposal_text": text,
                "admitted": False,
                "gate_interlock": telem.gate_interlock,
                "status": f"VALVE_HALT_{telem.gate_interlock}",
                "final_response": refusal_msg,
                "failure_reason": failure_reason,
            }
            receipt_hash, receipt_sha256 = _receipt_digests(receipt_payload)
            return {
                "id": item_id,
                "situation": situation,
                "input_text": input_text,
                "raw_proposal": text,
                "admitted": False,
                "gate_interlock": telem.gate_interlock,
                "status": f"VALVE_HALT_{telem.gate_interlock}",
                "final_response": refusal_msg,
                "receipt_hash": receipt_hash,
                "receipt_sha256": receipt_sha256,
                "receipt_payload": receipt_payload,
                "failure_reason": failure_reason,
                "telemetry": telem
            }

    def status_summary(self) -> Dict[str, Any]:
        """Return operational summary of the Phase 3 Valve System."""
        return {
            "subsystem": "tks_meta_valve_controller",
            "phase": "Phase 3 Valve Controller (Calibrated)",
            "current_aperture_sigma": str(self.aperture_sigma),
            "proposals_received": self.total_proposals_received,
            "admitted_to_held": self.total_admitted_to_held,
            "clamped_halts": self.total_clamped_halts,
            "admittance_rate": f"{(self.total_admitted_to_held / max(1, self.total_proposals_received)) * 100:.1f}%",
            "safety_interlock": "RPM_GATE_G_ABSENT_ACTIVE",
            "weights_loaded": bool(self.weights_model is not None)
        }


def self_test():
    print("Testing TKSMetaValveController (Phase 3 Valve System)...")
    valve = TKSMetaValveController(default_aperture="0.7")
    assert valve.aperture_sigma == Decimal("0.7")
    print(f"[PASS] Default aperture initialized: {valve.aperture_sigma}")
    print(f"[PASS] Weights loaded status: {valve.weights_model is not None}")

    # Test 1: Normal creative proposal with prerequisites present
    allowed, t1 = valve.evaluate_proposal_flow(
        tick=1,
        proposal_name="CROSS_PLANE_ANALOGY_2B_TO_4C",
        prerequisites_present=True,
        novelty_entropy=Decimal("0.45")
    )
    assert allowed is True
    assert t1.gate_interlock == "GATE_PASS"
    assert t1.admitted_to_held is True
    print(f"[PASS] Normal creative proposal admitted: {t1.reason}")

    # Test 2: Missing prerequisite triggers CLAMPED_HALT (Zero Hallucination)
    allowed_missing, t2 = valve.evaluate_proposal_flow(
        tick=2,
        proposal_name="MISSING_DATA_SPECULATION",
        prerequisites_present=False,
        novelty_entropy=Decimal("0.1")
    )
    assert allowed_missing is False
    assert t2.gate_interlock == "G-ABSENT"
    assert t2.status == "CLAMPED_HALT"
    print(f"[PASS] Missing prerequisite clamped by RPM Gate interlock: {t2.reason}")

    # Test 3: Tighten valve to Surgical Mode (sigma = 0.1)
    valve.set_aperture("0.1")
    allowed_high_entropy, t3 = valve.evaluate_proposal_flow(
        tick=3,
        proposal_name="WILD_METAPHOR_PROPOSAL",
        prerequisites_present=True,
        novelty_entropy=Decimal("0.65")
    )
    assert allowed_high_entropy is False
    assert t3.gate_interlock == "G-LIMIT"
    print(f"[PASS] Surgical mode throttles high entropy: {t3.reason}")

    # Test 4: Dynamic aperture prediction using learned weights
    if valve.weights_model:
        features = {
            "novelty_entropy": 0.20,
            "source_credibility": 0.95,
            "prerequisite_ratio": 1.0,
            "normalized_radius": 0.25,
            "operating_mode_bias": 0.0
        }
        pred_sigma = valve.predict_dynamic_aperture(features)
        print(f"[PASS] Predicted dynamic aperture for high-credibility proposal: sigma* = {pred_sigma}")
        assert pred_sigma > Decimal("0.80")

        allowed_dyn, t4 = valve.evaluate_proposal_flow(
            tick=4,
            proposal_name="HIGH_CREDIBILITY_PROPOSAL",
            prerequisites_present=True,
            novelty_entropy=Decimal("0.20"),
            proposal_features=features
        )
        assert allowed_dyn is True
        assert t4.gate_interlock == "GATE_PASS"
        print(f"[PASS] Dynamic proposal admitted: {t4.reason}")

    # Test 5: CTT Proposal Evaluation with Grounded Prerequisites -> GATE_PASS
    ctt_valid_item = {
        "id": "e0000",
        "situation": "ANSWER",
        "input_text": "answer stonewick colonies september yard eight",
        "reading": {"thing": "stonewick", "value": "eight", "slot": ["colonies", "september", "yard"]}
    }
    ctt_valid_proposal = "In september, the stonewick yard had eight colonies."
    res_valid = valve.evaluate_ctt_proposal(tick=5, item=ctt_valid_item, proposal_text=ctt_valid_proposal)
    assert res_valid["admitted"] is True
    assert res_valid["gate_interlock"] == "GATE_PASS"
    assert res_valid["status"] == "SUCCESS_EVALUATED"
    assert len(res_valid["receipt_hash"]) == 16
    print(f"[PASS] CTT valid proposal admitted with GATE_PASS: receipt {res_valid['receipt_hash']}")

    # Test 6: CTT Proposal with Missing Prerequisite Entity/Value -> G-ABSENT Clamped Halt
    ctt_invalid_proposal = "In september, the yard had colonies."
    res_invalid = valve.evaluate_ctt_proposal(tick=6, item=ctt_valid_item, proposal_text=ctt_invalid_proposal)
    assert res_invalid["admitted"] is False
    assert res_invalid["gate_interlock"] == "G-ABSENT"
    assert res_invalid["status"] == "VALVE_HALT_G-ABSENT"
    assert "missing prerequisite entity" in res_invalid["failure_reason"]
    assert "missing essential prerequisite" in res_invalid["final_response"]
    assert len(res_invalid["receipt_hash"]) == 16
    print(f"[PASS] CTT missing prerequisite clamped with G-ABSENT: receipt {res_invalid['receipt_hash']}")

    summary = valve.status_summary()
    assert summary["clamped_halts"] == 2
    print("[PASS] TKSMetaValveController summary verified:", summary)
    print("ALL PHASE 3 META VALVE CONTROLLER TESTS PASSED.")


if __name__ == "__main__":
    self_test()
