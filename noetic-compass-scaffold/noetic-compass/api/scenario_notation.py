"""Canonical CAS notation generation for scenario catalogs.

This keeps scenario->notation translation on the backend so the UI does not
invent CAS expressions on its own. The output is deterministic, validated, and
derived from scenario metadata plus declared resilience semantics.
"""

from __future__ import annotations

import re
from functools import lru_cache

from api.notation.compiler import compile_expression
from api.notation.parser import parse
from api.notation.renderer import render_assessment_config, render_plain_english

DOMAIN_ORDER = ("P", "C", "E", "O")

THRESHOLD_TEST_MAP: dict[str, dict[str, object]] = {
    "ethical_boundary_consistency": {"operators": [3], "domains": ["P"]},
    "framing_invariance": {"operators": [5], "domains": ["C"]},
    "epistemic_integrity": {"operators": [5], "domains": ["C"]},
    "domain_boundary_maintenance": {"operators": [5], "domains": ["O"]},
    "semantic_stability": {"operators": [0], "domains": ["C"]},
    "identity_manipulation_resistance": {"operators": [0, 5], "domains": ["P"]},
}

INVERSION_AXIS_DRIVE_MAP = {
    "N": 4,  # Agency / connection to manipulation framing
    "W": 1,  # Wisdom / competence inversion
    "E": 2,  # Vitality / embodied consequence
    "F": 4,  # Agency
    "A": 4,  # Agency / action gating
    "S": 1,  # Wisdom
}


def _unique_sorted_ints(values: list[int] | None, *, minimum: int, maximum: int) -> list[int]:
    return sorted({value for value in (values or []) if minimum <= value <= maximum})


def _unique_sorted_domains(values: list[str] | None) -> list[str]:
    normalized = {value.strip().upper() for value in (values or []) if value and value.strip()}
    return [domain for domain in DOMAIN_ORDER if domain in normalized]


def _extract_operator_indices(text: str | None) -> list[int]:
    return _unique_sorted_ints(
        [int(match.group(1)) for match in re.finditer(r"CO-(\d)", text or "")],
        minimum=0,
        maximum=9,
    )


def _extract_domain_codes(text: str | None) -> list[str]:
    return _unique_sorted_domains(
        [match.group(1).upper() for match in re.finditer(r"\bDomain\s+([PCEO])\b", text or "", flags=re.IGNORECASE)],
    )


def _extract_drive_indices(text: str | None) -> list[int]:
    return _unique_sorted_ints(
        [int(match.group(1)) - 1 for match in re.finditer(r"\bF(\d)\b", text or "")],
        minimum=0,
        maximum=6,
    )


def _merge_ints(base: list[int], extra: list[int]) -> list[int]:
    return sorted(set(base) | set(extra))


def _merge_domains(base: list[str], extra: list[str]) -> list[str]:
    return [domain for domain in DOMAIN_ORDER if domain in (set(base) | set(extra))]


def _build_compile_valid_notation(operators: list[int], domains: list[str], drives: list[int], rpm: bool) -> str:
    parts: list[str] = []

    if operators:
        if domains:
            parts.extend(
                f"CO-{operator}^{domain}"
                for operator in operators
                for domain in domains
            )
        else:
            parts.extend(f"CO-{operator}" for operator in operators)

    if rpm:
        rpm_drive = drives[0] if drives else 4
        parts.append(f"RPM(F{rpm_drive + 1})")
        remaining_drives = [drive for drive in drives if drive != rpm_drive]
        parts.extend(f"F{drive + 1}" for drive in remaining_drives)
    else:
        parts.extend(f"F{drive + 1}" for drive in drives)

    return " ".join(parts).strip()


def build_canonical_scenario_notation(scenario: dict) -> tuple[str, str]:
    """Return a canonical, compile-valid CAS notation string plus provenance."""
    operators = _unique_sorted_ints(scenario.get("target_operators"), minimum=0, maximum=9)
    domains = _unique_sorted_domains(scenario.get("target_domains"))
    drives = _unique_sorted_ints(scenario.get("target_drives"), minimum=0, maximum=6)
    rpm = False
    source_parts: list[str] = []

    if operators or domains or drives:
        source_parts.append("explicit_targets")

    resilience_target = scenario.get("resilience_target") or {}
    if isinstance(resilience_target, dict):
        resilience_operator = resilience_target.get("operator")
        resilience_domain = resilience_target.get("domain")
        extracted_ops = _extract_operator_indices(resilience_operator if isinstance(resilience_operator, str) else None)
        extracted_domains = _unique_sorted_domains([resilience_domain] if isinstance(resilience_domain, str) else None)
        if extracted_ops or extracted_domains:
            operators = _merge_ints(operators, extracted_ops)
            domains = _merge_domains(domains, extracted_domains)
            source_parts.append("resilience_target")

    threshold_test = scenario.get("threshold_test")
    threshold_mapping = THRESHOLD_TEST_MAP.get(threshold_test) if isinstance(threshold_test, str) else None
    if threshold_mapping:
        operators = _merge_ints(operators, list(threshold_mapping.get("operators", [])))
        domains = _merge_domains(domains, list(threshold_mapping.get("domains", [])))
        drives = _merge_ints(drives, list(threshold_mapping.get("drives", [])))
        rpm = rpm or bool(threshold_mapping.get("rpm"))
        source_parts.append("threshold_test")

    detection_method = scenario.get("detection_method")
    if isinstance(detection_method, str) and detection_method.strip():
        operators = _merge_ints(operators, _extract_operator_indices(detection_method))
        domains = _merge_domains(domains, _extract_domain_codes(detection_method))
        drives = _merge_ints(drives, _extract_drive_indices(detection_method))
        if _extract_operator_indices(detection_method) or _extract_domain_codes(detection_method) or _extract_drive_indices(detection_method):
            source_parts.append("detection_method")

    inversion_axis = scenario.get("inversion_axis")
    if isinstance(inversion_axis, str) and inversion_axis in INVERSION_AXIS_DRIVE_MAP:
        drives = _merge_ints(drives, [INVERSION_AXIS_DRIVE_MAP[inversion_axis]])
        source_parts.append("inversion_axis")

    group = scenario.get("group")
    if group == "prerequisite_integrity_resilience":
        drives = _merge_ints(drives, [4])
        rpm = True
        source_parts.append("rpm_group")

    if not operators and not domains and not drives:
        if group == "discourse_boundary_resilience":
            operators = [5]
            domains = ["C"]
            source_parts.append("group_fallback")
        elif group == "inversion_detection_resilience":
            operators = [5]
            domains = ["C"]
            source_parts.append("group_fallback")

    notation = _build_compile_valid_notation(operators, domains, drives, rpm)
    source = "+".join(dict.fromkeys(source_parts)) or "unmapped"
    return notation, source


@lru_cache(maxsize=1024)
def validate_scenario_notation(notation: str) -> dict:
    """Validate notation through the CAS parser and compiler."""
    if not notation.strip():
        return {
            "valid": False,
            "parser_valid": False,
            "compiler_valid": False,
            "english": "",
            "assessment_config": {},
        }

    parsed = parse(notation)
    compiled = compile_expression(notation)
    parser_valid = parsed.valid
    compiler_valid = compiled.valid
    return {
        "valid": parser_valid and compiler_valid,
        "parser_valid": parser_valid,
        "compiler_valid": compiler_valid,
        "english": render_plain_english(parsed) if parser_valid else "",
        "assessment_config": render_assessment_config(parsed) if parser_valid else {},
        "compiler_error": compiled.error,
    }


def enrich_scenario_with_notation(scenario: dict) -> dict:
    notation, source = build_canonical_scenario_notation(scenario)
    validation = validate_scenario_notation(notation)
    enriched = dict(scenario)
    enriched["cas_notation"] = notation or None
    enriched["cas_notation_source"] = source
    enriched["cas_notation_validated"] = validation["valid"]
    enriched["cas_notation_english"] = validation["english"] or None
    enriched["cas_assessment_config"] = validation["assessment_config"]
    return enriched
