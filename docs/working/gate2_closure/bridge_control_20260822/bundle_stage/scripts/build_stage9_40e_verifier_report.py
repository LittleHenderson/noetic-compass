#!/usr/bin/env python3
"""Build a Stage 9 40E verifier decision report from an Evidence Packet.

This is a packet-level verifier for the Stage 9 original 40-Element validation
artifact. It does not rerun hidden-state inference and it does not create a
customer-production row verdict. It only converts an already-assembled packet
into an explicit verifier decision when the packet's proof chips and numeric
gates are pass-ready.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_stage9_40e_verifier_decision.v1"
SOURCE_PACKET_SCHEMA = "cas_harness_stage9_40e_evidence_packet.v1"
LOCKED_TKS_DEFINITION_SHA256 = "a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0"
DEFAULT_PACKET = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "working"
    / "gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json"
)
DEFAULT_OUTPUT_JSON = DEFAULT_PACKET.with_name(
    "gpt_neox_20b_stage9_original_40e_verifier_report_20260528T0455Z.json"
)
DEFAULT_OUTPUT_MARKDOWN = DEFAULT_OUTPUT_JSON.with_suffix(".md")
FINAL_VERDICTS = {"ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"}
LICENSE_GRADE_MODES = {"HIGH_PRECISION", "BALANCED"}
PASSING_PROOF_STATUSES = {"present", "verified"}
PASSING_UNIQUENESS_STATUSES = {
    "matched_taxonomy_validated",
    "uniqueness_validated",
    "condition3_validated",
    "condition_3_validated",
    "passed",
    "verified",
}
FAILING_UNIQUENESS_STATUSES = {
    "failed",
    "blocked",
    "matched_taxonomy_failed",
    "uniqueness_failed",
    "condition3_failed",
    "condition_3_failed",
}
STRICT_VERIFIED_PROOF_CHIPS = {
    "cas_readout",
    "causal_proof",
    "control_proof",
    "output_proof",
}
REQUIRED_PROOF_CHIPS = {
    "model_proof",
    "cas_readout",
    "causal_proof",
    "control_proof",
    "output_proof",
    "packet_proof",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"packet does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"packet is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"packet must be a JSON object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float_or_none(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value)


def _confidence_or_none(value: Any) -> float | None:
    out = _float_or_none(value)
    if out is None or not 0.0 <= out <= 1.0:
        return None
    return out


def _proof_chips(packet: dict[str, Any]) -> list[dict[str, Any]]:
    verification = _mapping_or_empty(packet.get("verification"))
    chips = verification.get("proof_chips")
    return [chip for chip in chips if isinstance(chip, dict)] if isinstance(chips, list) else []


def _chips_by_id(chips: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for chip in chips:
        chip_id = chip.get("id")
        status = chip.get("status")
        if isinstance(chip_id, str) and isinstance(status, str):
            out[chip_id] = status
    return out


def _chip_gate(chips: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = _chips_by_id(chips)
    missing = sorted(chip_id for chip_id in REQUIRED_PROOF_CHIPS if chip_id not in by_id)
    non_passing = sorted(
        chip_id
        for chip_id in REQUIRED_PROOF_CHIPS
        if chip_id in by_id and by_id[chip_id] not in PASSING_PROOF_STATUSES
    )
    not_verified = sorted(
        chip_id
        for chip_id in STRICT_VERIFIED_PROOF_CHIPS
        if by_id.get(chip_id) != "verified"
    )
    return {
        "passed": not missing and not non_passing and not not_verified,
        "missing": missing,
        "non_passing": non_passing,
        "core_not_verified": not_verified,
        "statuses": by_id,
    }


def _readout_gate(packet: dict[str, Any]) -> dict[str, Any]:
    baseline = _mapping_or_empty(packet.get("baseline_proof"))
    hidden = _confidence_or_none(baseline.get("hidden_probe_test_acc"))
    text = _confidence_or_none(baseline.get("confirmed_text_test_acc"))
    shuffled = _confidence_or_none(baseline.get("shuffled_label_hidden_mean_test_acc"))
    passed = (
        hidden is not None
        and text is not None
        and shuffled is not None
        and hidden > text
        and hidden > shuffled
    )
    return {
        "passed": passed,
        "hidden_probe_test_acc": hidden,
        "confirmed_text_test_acc": text,
        "shuffled_label_hidden_mean_test_acc": shuffled,
        "hidden_minus_confirmed_text": (
            round(hidden - text, 12) if hidden is not None and text is not None else None
        ),
    }


def _causal_gate(packet: dict[str, Any]) -> dict[str, Any]:
    causal = _mapping_or_empty(packet.get("causal_proof"))
    primary = _mapping_or_empty(_mapping_or_empty(causal.get("summary")).get("primary_result"))
    disruption = _float_or_none(primary.get("true_disruption"))
    random_max = _float_or_none(primary.get("random_same_rank_max_disruption"))
    guard_status = primary.get("guard_status")
    passed = (
        causal.get("status") == "present"
        and str(guard_status).lower() == "passed"
        and disruption is not None
        and random_max is not None
        and disruption > random_max
    )
    return {
        "passed": passed,
        "guard_status": guard_status,
        "true_disruption": disruption,
        "random_same_rank_max_disruption": random_max,
        "true_minus_random_max": (
            round(disruption - random_max, 12)
            if disruption is not None and random_max is not None
            else None
        ),
    }


def _control_gate(packet: dict[str, Any]) -> dict[str, Any]:
    control = _mapping_or_empty(packet.get("control_proof"))
    summary = _mapping_or_empty(control.get("summary"))
    matched = _mapping_or_empty(summary.get("matched_controls"))
    class_count = summary.get("class_count")
    random_classes = matched.get("random_same_size_classes")
    wrong_classes = matched.get("wrong_class_reference_classes")
    passed = (
        control.get("status") == "present"
        and isinstance(class_count, int)
        and class_count >= 40
        and isinstance(random_classes, int)
        and random_classes >= 40
        and isinstance(wrong_classes, int)
        and wrong_classes >= 40
    )
    return {
        "passed": passed,
        "class_count": class_count,
        "random_same_size_classes": random_classes,
        "wrong_class_reference_classes": wrong_classes,
        "caveat": summary.get("caveat"),
    }


def _bridge_gate(packet: dict[str, Any]) -> dict[str, Any]:
    bridge = _mapping_or_empty(packet.get("output_bridge_proof"))
    summary = _mapping_or_empty(bridge.get("summary"))
    key = _mapping_or_empty(summary.get("key_comparisons"))
    probe_prediction = _mapping_or_empty(summary.get("probe_prediction"))
    delta = _float_or_none(key.get("probe_readable_delta_vs_none"))
    margin = _float_or_none(key.get("probe_readable_minus_partner_readable_margin"))
    selected_acc = _confidence_or_none(probe_prediction.get("selected_element_accuracy"))
    passed = (
        bridge.get("status") == "present"
        and summary.get("probe_readable_gate_passed") is True
        and delta is not None
        and margin is not None
        and delta > 0.0
        and margin > 0.0
    )
    return {
        "passed": passed,
        "n_cases": summary.get("n_cases"),
        "selected_element_accuracy": selected_acc,
        "probe_readable_delta_vs_none": delta,
        "probe_readable_minus_partner_readable_margin": margin,
        "probe_raw_delta_vs_none": key.get("probe_raw_delta_vs_none"),
    }


def _packet_gate(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": packet.get("schema_version") == SOURCE_PACKET_SCHEMA
        and bool(packet.get("trace_id"))
        and bool(packet.get("run_id")),
        "schema_version": packet.get("schema_version"),
        "trace_id": packet.get("trace_id"),
        "run_id": packet.get("run_id"),
    }


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _nested_bool(mapping: dict[str, Any], *names: str) -> bool | None:
    for name in names:
        value = _bool_or_none(mapping.get(name))
        if value is not None:
            return value
    return None


def _control_status_bool(summary: dict[str, Any], *names: str) -> bool | None:
    for name in names:
        value = summary.get(name)
        if isinstance(value, dict):
            direct = _bool_or_none(value.get("passed"))
            if direct is not None:
                return direct
            status = str(value.get("status") or "").lower()
            if status in PASSING_UNIQUENESS_STATUSES:
                return True
            if status in FAILING_UNIQUENESS_STATUSES:
                return False
        direct = _bool_or_none(value)
        if direct is not None:
            return direct
    return None


def _clean_sha(value: Any) -> str | None:
    cleaned = str(value or "").strip().lower()
    return cleaned or None


def _uniqueness_definition_sha(proof: dict[str, Any], summary: dict[str, Any]) -> str | None:
    for mapping in (
        proof,
        summary,
        _mapping_or_empty(proof.get("definition_lock")),
        _mapping_or_empty(summary.get("definition_lock")),
        _mapping_or_empty(proof.get("cas_probe")),
        _mapping_or_empty(summary.get("cas_probe")),
    ):
        for key in (
            "definition_sha256",
            "tks_definition_sha256",
            "cas_definition_sha256",
            "source_definition_sha256",
        ):
            cleaned = _clean_sha(mapping.get(key))
            if cleaned:
                return cleaned
    return None


def _uniqueness_gate(packet: dict[str, Any]) -> dict[str, Any]:
    proof_key = None
    proof: dict[str, Any] = {}
    for candidate in (
        "matched_taxonomy_proof",
        "uniqueness_proof",
        "condition3_proof",
        "condition_3_proof",
    ):
        candidate_proof = _mapping_or_empty(packet.get(candidate))
        if candidate_proof:
            proof_key = candidate
            proof = candidate_proof
            break
    if not proof:
        return {
            "passed": None,
            "proof_key": None,
            "status": "missing",
            "reason": "matched-taxonomy/uniqueness proof was not supplied",
        }

    summary = _mapping_or_empty(proof.get("summary"))
    status = str(
        proof.get("status")
        or summary.get("status")
        or proof.get("verdict")
        or ""
    ).lower()
    condition3 = _nested_bool(
        summary,
        "condition3_passed",
        "condition_3_passed",
        "matched_taxonomy_gate_passed",
        "uniqueness_gate_passed",
    )
    control_b = _control_status_bool(summary, "control_b", "control_b_passed")
    control_c = _control_status_bool(summary, "control_c", "control_c_passed")
    definition_sha256 = _uniqueness_definition_sha(proof, summary)
    tks_definition_locked = definition_sha256 == LOCKED_TKS_DEFINITION_SHA256

    failed_flag = any(value is False for value in (condition3, control_b, control_c))
    if status in FAILING_UNIQUENESS_STATUSES or failed_flag:
        passed: bool | None = False
    elif not tks_definition_locked:
        passed = None
    elif (
        status in PASSING_UNIQUENESS_STATUSES
        or condition3 is True
        or (control_b is True and control_c is True)
    ):
        passed = True
    else:
        passed = None
    reason = summary.get("reason") or proof.get("reason")
    if passed is None and not tks_definition_locked:
        reason = "matched-taxonomy/uniqueness proof is not tied to the locked TKS definitions"

    return {
        "passed": passed,
        "proof_key": proof_key,
        "status": status or "present",
        "condition3_passed": condition3,
        "control_b_passed": control_b,
        "control_c_passed": control_c,
        "definition_sha256": definition_sha256,
        "tks_definition_locked": tks_definition_locked,
        "reason": reason,
    }


def _confidence_components(gates: dict[str, dict[str, Any]]) -> dict[str, float]:
    components: dict[str, float] = {}
    readout_acc = gates["readout"].get("hidden_probe_test_acc")
    selected_acc = gates["output_bridge"].get("selected_element_accuracy")
    if isinstance(readout_acc, float):
        components["hidden_probe_test_acc"] = readout_acc
    if isinstance(selected_acc, float):
        components["bridge_selected_element_accuracy"] = selected_acc
    components["causal_guard"] = 1.0 if gates["causal"]["passed"] else 0.0
    components["control_gate"] = 1.0 if gates["control"]["passed"] else 0.0
    components["uniqueness_gate"] = 1.0 if gates["uniqueness"]["passed"] is True else 0.0
    components["output_bridge_gate"] = 1.0 if gates["output_bridge"]["passed"] else 0.0
    components["packet_gate"] = 1.0 if gates["packet"]["passed"] else 0.0
    return components


def _decide(*, mode: str, gates: dict[str, dict[str, Any]]) -> tuple[str, float | None, list[str]]:
    reasons: list[str] = []
    if mode not in {"HIGH_PRECISION", "BALANCED", "MAX_COVERAGE_TRIAGE"}:
        reasons.append(f"unknown_verification_mode:{mode}")
        return "FLAG_FOR_HUMAN_REVIEW", 0.0, reasons

    hard_failures = [
        name
        for name in ("readout", "causal", "control", "output_bridge", "packet")
        if gates[name]["passed"] is False
    ]
    if hard_failures:
        reasons.extend(f"{name}_gate_failed" for name in hard_failures)
        return "SUPPRESS", 0.9, reasons

    if gates["proof_chips"]["passed"] is False:
        reasons.append("proof_chip_gate_blocked")
        return "FLAG_FOR_HUMAN_REVIEW", 0.0, reasons

    if gates["uniqueness"]["passed"] is False:
        reasons.append("uniqueness_gate_failed")
        return "SUPPRESS", 0.9, reasons

    if gates["uniqueness"]["passed"] is not True:
        reasons.append("uniqueness_gate_unavailable")
        return "FLAG_FOR_HUMAN_REVIEW", 0.0, reasons

    if mode not in LICENSE_GRADE_MODES:
        reasons.append("max_coverage_triage_does_not_emit_final_accept")
        components = _confidence_components(gates)
        confidence = min(components.values()) if components else 0.0
        return "FLAG_FOR_HUMAN_REVIEW", round(confidence, 12), reasons

    components = _confidence_components(gates)
    confidence = min(components.values()) if components else None
    if confidence is None:
        reasons.append("confidence_unavailable")
        return "FLAG_FOR_HUMAN_REVIEW", 0.0, reasons

    reasons.append("all_stage9_40e_validation_gates_passed")
    return "ACCEPT", round(confidence, 12), reasons


def build_report(
    *,
    packet_path: Path,
    mode: str = "BALANCED",
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    generated = generated_at or datetime.now(UTC)
    chips = _proof_chips(packet)
    gates = {
        "packet": _packet_gate(packet),
        "proof_chips": _chip_gate(chips),
        "readout": _readout_gate(packet),
        "causal": _causal_gate(packet),
        "control": _control_gate(packet),
        "uniqueness": _uniqueness_gate(packet),
        "output_bridge": _bridge_gate(packet),
    }
    verdict, confidence, reasons = _decide(mode=mode, gates=gates)
    components = _confidence_components(gates)
    action = {
        "ACCEPT": "allow",
        "SUPPRESS": "suppress",
        "FLAG_FOR_HUMAN_REVIEW": "caveat",
    }[verdict]
    decision = {
        "verdict": verdict,
        "confidence": confidence,
        "source": "stage9_40e_packet_verifier",
        "reason": "; ".join(reasons),
        "mode": mode,
        "coverage": {
            "basis": "stage9_40e_validation_cases",
            "case_count": gates["output_bridge"].get("n_cases"),
            "class_count": gates["control"].get("class_count"),
        },
        "decision_scope": "stage9_40e_validation_packet",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": f"STAGE9_40E_VERIFIER_{verdict}",
        "created_at": generated.isoformat(),
        "source_packet": str(packet_path),
        "source_packet_sha256": _sha256_file(packet_path),
        "trace_id": packet.get("trace_id"),
        "run_id": packet.get("run_id"),
        "mode": mode,
        "explicit_verifier_decision": decision,
        "verification_stack": {
            "proof_chip_gate": "passed" if gates["proof_chips"]["passed"] else "blocked",
            "proof_chips": chips,
            "gates": gates,
        },
        "generation_readiness": {
            "generation_readiness": action,
            "mode": mode,
            "policy_version": "stage9_40e_packet_verifier_v1",
            "reasons": reasons,
            "risk_score": 0.0 if verdict == "ACCEPT" else confidence,
        },
        "confidence_basis": {
            "formula": (
                "ACCEPT confidence = min(hidden_probe_test_acc, "
                "bridge_selected_element_accuracy, causal_guard, control_gate, "
                "uniqueness_gate, output_bridge_gate, packet_gate). SUPPRESS confidence is a "
                "blocking-risk score. FLAG confidence is unavailable unless a "
                "risk score is present."
            ),
            "components": components,
            "important_limit": (
                "This is packet-level validation confidence, not mathematical "
                "certainty and not a per-customer row confidence unless the source "
                "packet is a production row."
            ),
        },
        "important_limit": (
            "This verifier report is explicit and evidence-bound, but it is built "
            "over the Stage 9 40E validation packet. It does not claim live "
            "customer inference unless the packet source is a live production run."
        ),
        "rejected_claims": [
            "raw_cas_symbol_understanding",
            "complete_neuron_by_neuron_causal_map",
            "per-customer production verdict from validation artifact alone",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["explicit_verifier_decision"]
    gates = report["verification_stack"]["gates"]
    components = report["confidence_basis"]["components"]
    component_rows = "\n".join(
        f"| {name} | {value:.6g} |" for name, value in components.items()
    )
    gate_rows = "\n".join(
        f"| {name} | {'passed' if gate.get('passed') else 'blocked'} |"
        for name, gate in gates.items()
    )
    return f"""# Stage 9 40E Verifier Report

- Status: `{report["status"]}`
- Verdict: `{decision["verdict"]}`
- Confidence: `{decision["confidence"]}`
- Source: `{decision["source"]}`
- Trace ID: `{report["trace_id"]}`
- Mode: `{report["mode"]}`

## Gates

| Gate | Status |
| --- | --- |
{gate_rows}

## Confidence Components

| Component | Value |
| --- | ---: |
{component_rows}

## Reason

{decision["reason"]}

## Boundary

{report["important_limit"]}
"""


def write_report(report: dict[str, Any], output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument(
        "--mode",
        choices=("HIGH_PRECISION", "BALANCED", "MAX_COVERAGE_TRIAGE"),
        default="BALANCED",
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_OUTPUT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(packet_path=args.packet, mode=args.mode)
    write_report(report, args.output_json, args.output_markdown)
    decision = report["explicit_verifier_decision"]
    print(f"wrote JSON verifier report: {args.output_json}")
    print(f"wrote markdown verifier report: {args.output_markdown}")
    print(f"verdict: {decision['verdict']}")
    print(f"confidence: {decision['confidence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
