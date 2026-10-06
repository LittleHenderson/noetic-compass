"""Fixture-backed evaluation for the shadow-only Instruction Integrity scanner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Mapping

from api.services.cas_harness_instruction_integrity import (
    build_instruction_integrity_report,
)


BENCHMARK_SCHEMA_VERSION = "cas_harness_instruction_integrity_benchmark.v0"
BenchmarkLane = Literal["clean", "injected", "control"]
EvaluationRole = Literal["development_benchmark", "held_out_evaluation"]
_LANES: tuple[BenchmarkLane, ...] = ("clean", "injected", "control")
_EVALUATION_ROLES: tuple[EvaluationRole, ...] = (
    "development_benchmark",
    "held_out_evaluation",
)


class InstructionIntegrityBenchmarkError(ValueError):
    """Raised when an evaluation fixture cannot be trusted."""


def load_instruction_integrity_benchmark_suite(path: str | Path) -> dict[str, Any]:
    fixture_path = Path(path)
    with fixture_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise InstructionIntegrityBenchmarkError(
            "Instruction-integrity benchmark must be an object"
        )
    return raw


def run_instruction_integrity_benchmark_suite(
    suite: Mapping[str, Any],
) -> dict[str, Any]:
    """Run a frozen clean/injected/control suite against the shadow scanner."""

    if suite.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
        raise InstructionIntegrityBenchmarkError(
            "Unsupported instruction-integrity benchmark schema_version"
        )
    suite_id = _required_string(suite.get("suite_id"), "suite_id")
    evaluation_role = suite.get("evaluation_role", "development_benchmark")
    if evaluation_role not in _EVALUATION_ROLES:
        raise InstructionIntegrityBenchmarkError("Unsupported evaluation_role")
    raw_cases = suite.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise InstructionIntegrityBenchmarkError(
            "Instruction-integrity benchmark cases must be a non-empty array"
        )

    case_results = [_run_case(raw_case, index) for index, raw_case in enumerate(raw_cases)]
    metrics = _build_metrics(case_results)
    gate_results = _build_gate_results(metrics, suite.get("gates"))

    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "suite_id": suite_id,
        "evaluation_role": evaluation_role,
        "suite_sha256": _suite_sha256(suite),
        "mode": "shadow",
        "verdict_effect": "none_shadow_only",
        "cases_run": len(case_results),
        "passed": sum(1 for result in case_results if result["passed"]),
        "failed": sum(1 for result in case_results if not result["passed"]),
        "metrics": metrics,
        "gates": gate_results,
        "case_results": case_results,
    }


def _run_case(raw_case: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw_case, Mapping):
        raise InstructionIntegrityBenchmarkError(f"Benchmark case {index} must be an object")

    case_id = _required_string(raw_case.get("case_id"), f"cases[{index}].case_id")
    lane = _parse_lane(raw_case.get("lane"), case_id)
    expected_status = _required_string(
        raw_case.get("expected_status"), f"{case_id}.expected_status"
    )
    if expected_status not in {"present", "FLAG_FOR_HUMAN_REVIEW"}:
        raise InstructionIntegrityBenchmarkError(
            f"{case_id}.expected_status is unsupported"
        )

    report = build_instruction_integrity_report(
        prompt_text=_nullable_string(raw_case.get("prompt_text")),
        scenario_text=_nullable_string(raw_case.get("scenario_text")),
        output_text=_nullable_string(raw_case.get("output_text")),
        evidence_packet_trace_id=_nullable_string(
            raw_case.get("evidence_packet_trace_id")
        ),
        proof_chips=_proof_chips(raw_case.get("proof_chips")),
    ).to_dict()

    actual_findings = sorted({finding["kind"] for finding in report["findings"]})
    actual_flags = sorted(report["gluing"]["lacunarity_flags"])
    actual_claim_support = sorted(
        {claim["support_status"] for claim in report["claim_grounding"]}
    )

    required_findings = _string_set(
        raw_case.get("required_findings"), case_id, "required_findings"
    )
    forbidden_findings = _string_set(
        raw_case.get("forbidden_findings"), case_id, "forbidden_findings"
    )
    required_flags = _string_set(
        raw_case.get("required_lacunarity_flags"),
        case_id,
        "required_lacunarity_flags",
    )
    forbidden_flags = _string_set(
        raw_case.get("forbidden_lacunarity_flags"),
        case_id,
        "forbidden_lacunarity_flags",
    )
    required_claim_support = _string_set(
        raw_case.get("required_claim_support_statuses"),
        case_id,
        "required_claim_support_statuses",
    )

    missing_required_findings = sorted(required_findings - set(actual_findings))
    unexpected_findings = sorted(forbidden_findings & set(actual_findings))
    missing_required_flags = sorted(required_flags - set(actual_flags))
    unexpected_flags = sorted(forbidden_flags & set(actual_flags))
    missing_required_claim_support = sorted(
        required_claim_support - set(actual_claim_support)
    )
    routing = report["review_routing"]
    shadow_contract_pass = (
        report["mode"] == "shadow"
        and report["verdict_effect"] == "none_shadow_only"
        and routing["automatic_action"] == "none"
        and routing["live_blocking"] is False
        and routing["auto_removal"] is False
        and routing["automatic_accept"] is False
    )
    passed = (
        report["status"] == expected_status
        and shadow_contract_pass
        and not missing_required_findings
        and not unexpected_findings
        and not missing_required_flags
        and not unexpected_flags
        and not missing_required_claim_support
    )

    return {
        "case_id": case_id,
        "lane": lane,
        "expected_status": expected_status,
        "actual_status": report["status"],
        "passed": passed,
        "actual_findings": actual_findings,
        "actual_lacunarity_flags": actual_flags,
        "actual_claim_support_statuses": actual_claim_support,
        "missing_required_findings": missing_required_findings,
        "unexpected_findings": unexpected_findings,
        "missing_required_lacunarity_flags": missing_required_flags,
        "unexpected_lacunarity_flags": unexpected_flags,
        "missing_required_claim_support_statuses": missing_required_claim_support,
        "review_route": routing["route"],
        "shadow_contract_pass": shadow_contract_pass,
        "verdict_effect": report["verdict_effect"],
    }


def _build_metrics(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    lane_counts = {lane: 0 for lane in _LANES}
    passed_by_lane = {lane: 0 for lane in _LANES}
    for result in case_results:
        lane = result["lane"]
        lane_counts[lane] += 1
        if result["passed"]:
            passed_by_lane[lane] += 1

    injected_count = lane_counts["injected"]
    benign_count = lane_counts["clean"] + lane_counts["control"]
    injected_flagged = sum(
        1
        for result in case_results
        if result["lane"] == "injected"
        and result["actual_status"] == "FLAG_FOR_HUMAN_REVIEW"
    )
    benign_flagged = sum(
        1
        for result in case_results
        if result["lane"] in {"clean", "control"}
        and result["actual_status"] == "FLAG_FOR_HUMAN_REVIEW"
    )

    return {
        "case_counts_by_lane": lane_counts,
        "passed_by_lane": passed_by_lane,
        "injected_recall": _ratio(injected_flagged, injected_count),
        "benign_false_positive_rate": _ratio(benign_flagged, benign_count),
        "failed_case_ids": [
            result["case_id"] for result in case_results if not result["passed"]
        ],
    }


def _build_gate_results(metrics: Mapping[str, Any], raw_gates: Any) -> dict[str, Any]:
    gates = raw_gates if isinstance(raw_gates, Mapping) else {}
    min_recall = _float_gate(gates.get("min_injected_recall"), default=1.0)
    max_false_positive_rate = _float_gate(
        gates.get("max_benign_false_positive_rate"), default=0.0
    )
    all_cases_pass = not metrics["failed_case_ids"]
    recall_pass = (
        metrics["injected_recall"] is not None
        and metrics["injected_recall"] >= min_recall
    )
    false_positive_pass = (
        metrics["benign_false_positive_rate"] is not None
        and metrics["benign_false_positive_rate"] <= max_false_positive_rate
    )
    return {
        "min_injected_recall": min_recall,
        "max_benign_false_positive_rate": max_false_positive_rate,
        "all_cases_pass": all_cases_pass,
        "injected_recall_pass": recall_pass,
        "benign_false_positive_rate_pass": false_positive_pass,
        "overall_pass": all_cases_pass and recall_pass and false_positive_pass,
    }


def _suite_sha256(suite: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(suite), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_lane(raw: Any, case_id: str) -> BenchmarkLane:
    if raw in _LANES:
        return raw
    raise InstructionIntegrityBenchmarkError(f"{case_id}.lane is unsupported")


def _required_string(raw: Any, field_name: str) -> str:
    if isinstance(raw, str) and raw.strip():
        return raw
    raise InstructionIntegrityBenchmarkError(
        f"{field_name} must be a non-empty string"
    )


def _nullable_string(raw: Any) -> str | None:
    return raw if isinstance(raw, str) else None


def _proof_chips(raw: Any) -> list[Mapping[str, Any]] | None:
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(
        isinstance(chip, Mapping) for chip in raw
    ):
        raise InstructionIntegrityBenchmarkError(
            "proof_chips must be an array of objects when provided"
        )
    return raw


def _string_set(raw: Any, case_id: str, field_name: str) -> set[str]:
    if raw is None:
        return set()
    if not isinstance(raw, list) or not all(isinstance(value, str) for value in raw):
        raise InstructionIntegrityBenchmarkError(
            f"{case_id}.{field_name} must be an array of strings"
        )
    return set(raw)


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _float_gate(raw: Any, *, default: float) -> float:
    if raw is None:
        return default
    if isinstance(raw, (int, float)):
        return float(raw)
    raise InstructionIntegrityBenchmarkError(
        "Benchmark gate thresholds must be numeric"
    )
