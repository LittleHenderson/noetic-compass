"""Build a human-review bundle for PCBA production component syntax."""

from __future__ import annotations

import hashlib
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from cas_forex.pcba_authority import build_pcba_licensing_report
from cas_forex.pcba_compiler import compile_pcba_component_expression
from cas_forex.pcba_syntax import (
    PcbaSyntaxError,
    parse_pcba_component_expression,
    roundtrip_pcba_component_expression,
)
from cas_forex.schemas.pcba import PcbaProductionFeature
from cas_forex.time_utils import utc_now


SEMANTICS_REVIEW_ARTIFACT_REFS = [
    r"docs\working\pcba_syntax_grammar_spec_20260617.md",
    r"cas-forex\cas_forex\pcba_syntax.py",
    r"cas-forex\cas_forex\pcba_compiler.py",
]

SEMANTICS_RECEIPT_ARTIFACT_REFS = [
    *SEMANTICS_REVIEW_ARTIFACT_REFS,
    r"docs\working\pcba_semantics_review_packet_20260617.md",
    r"docs\working\pcba_semantics_review_bundle_20260617.json",
    r"docs\working\pcba_semantics_review_bundle_20260617.md",
]

VALID_PARSE_CASES = [
    "Resistor< ^8^C_{F2}|A, R=50 >",
    "Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >",
    "OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >",
    "Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >",
    "Trace< ^2^P -> ^2^C >",
    "Via< layer=P, to_layer=C, transition=^2^P->^2^C >",
]

INVALID_PARSE_CASES = [
    "UnknownPart< ^2^P|A >",
    "Resistor<>",
    "Resistor< ^8^C|A, R=-1 >",
    "Resistor< ^8^C|A, R=nan >",
    "Fuse< ^8^O|E, threshold=2 >",
    "LogicGate< gate=XNOR, inputs=[a, b] >",
]

COMPILER_PASS_CASES = [
    "Resistor< ^8^C_{F2}|A, R=50 >",
    "OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >",
    "Trace< ^2^P -> ^2^C >",
    "Via< layer=P, to_layer=C, transition=^2^P->^2^C >",
]

COMPILER_FAIL_CASES = [
    "Resistor< ^2^Z_{F2}|A, R=50 >",
    "Diode< ^P -> ^C >",
]


def build_pcba_semantics_review_bundle(
    *,
    workspace_root: Path,
    local_evidence: Mapping[str, bool],
) -> dict[str, Any]:
    """Create a deterministic bundle for human PCBA semantics review."""

    artifacts = [_artifact_entry(workspace_root, ref) for ref in SEMANTICS_REVIEW_ARTIFACT_REFS]
    parse_cases = [_parse_case(expr) for expr in VALID_PARSE_CASES]
    invalid_cases = [_invalid_parse_case(expr) for expr in INVALID_PARSE_CASES]
    compiler_pass_cases = [_compiler_case(expr) for expr in COMPILER_PASS_CASES]
    compiler_fail_cases = [_compiler_case(expr) for expr in COMPILER_FAIL_CASES]

    report = build_pcba_licensing_report(local_evidence)
    checks = {check.feature: check for check in report.checks}
    syntax = checks[PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX]
    safety = checks[PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM]
    prompt = checks[PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM]
    broker_accept = checks[PcbaProductionFeature.BROKER_ACCEPT_CREATION]

    ready_for_human_signature = (
        all(item["exists"] for item in artifacts)
        and all(item["passed"] for item in parse_cases)
        and all(item["passed"] for item in invalid_cases)
        and all(item["valid"] for item in compiler_pass_cases)
        and all(not item["valid"] for item in compiler_fail_cases)
        and syntax.status.value == "OPEN"
        and syntax.missing_evidence == ["pcba_semantics_review_signed"]
        and safety.status.value == "NOT LICENSED"
        and prompt.status.value == "NOT LICENSED"
        and broker_accept.status.value == "NOT LICENSED"
    )

    return {
        "generated_at": utc_now().isoformat(),
        "bundle_kind": "pcba_semantics_review",
        "scope": "production_pcba_component_syntax only",
        "ready_for_human_signature": ready_for_human_signature,
        "licensed": False,
        "reviewed_artifacts": artifacts,
        "parse_cases": parse_cases,
        "invalid_parse_cases": invalid_cases,
        "compiler_pass_cases": compiler_pass_cases,
        "compiler_fail_cases": compiler_fail_cases,
        "syntax_gate": syntax.model_dump(mode="json"),
        "claim_boundaries": {
            "compiler_enforced_safety_claim": safety.model_dump(mode="json"),
            "prompt_injection_prevention_claim": prompt.model_dump(mode="json"),
            "broker_accept_creation": broker_accept.model_dump(mode="json"),
        },
        "receipt_to_sign": r"docs\working\pcba_semantics_review_request_20260617.json",
        "finalize_command": (
            r'python scripts\finalize_pcba_authority_receipt.py '
            r'--receipt "..\docs\working\pcba_semantics_review_request_20260617.json"'
        ),
        "verify_command": (
            r'python scripts\verify_pcba_semantics_receipt.py '
            r'--receipt "..\docs\working\pcba_semantics_review_request_20260617.json"'
        ),
        "summary": (
            "Ready for human semantics signature."
            if ready_for_human_signature
            else "Not ready for human semantics signature; inspect failed cases."
        ),
    }


def _artifact_entry(workspace_root: Path, ref: str) -> dict[str, Any]:
    # Artifact refs are persisted with Windows-style separators because the
    # owner workspace is normally opened from Windows. Normalize them here so
    # the same evidence bundle verifies under WSL/Linux CI as well.
    path = workspace_root.joinpath(*PureWindowsPath(ref).parts)
    exists = path.exists()
    return {
        "ref": ref,
        "exists": exists,
        "sha256": _sha256_file(path) if exists else None,
    }


def _parse_case(expression: str) -> dict[str, Any]:
    try:
        node = parse_pcba_component_expression(expression)
        roundtrip = roundtrip_pcba_component_expression(expression)
        return {
            "expression": expression,
            "passed": node == roundtrip,
            "component_kind": node.kind.value,
            "roundtrip_expression": roundtrip.to_expression(),
        }
    except Exception as exc:
        return {"expression": expression, "passed": False, "error": str(exc)}


def _invalid_parse_case(expression: str) -> dict[str, Any]:
    try:
        parse_pcba_component_expression(expression)
    except PcbaSyntaxError as exc:
        return {"expression": expression, "passed": True, "error": str(exc)}
    except ValueError as exc:
        return {"expression": expression, "passed": True, "error": str(exc)}
    return {"expression": expression, "passed": False, "error": "Invalid expression was accepted."}


def _compiler_case(expression: str) -> dict[str, Any]:
    try:
        report = compile_pcba_component_expression(expression)
        return report.model_dump(mode="json")
    except Exception as exc:
        return {
            "source_expression": expression,
            "component_name": None,
            "compiler_available": False,
            "checked_expressions": [],
            "skipped_shorthand": [],
            "valid": False,
            "reason": str(exc),
        }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
