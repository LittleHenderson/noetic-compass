"""Shared helpers for open-weight CAS probe dataset capture/evaluation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DOMAIN_VALUES = {"P", "C", "E", "O"}
REGISTER_VALUES = {"T", "A", "f", "E"}


@dataclass(frozen=True)
class LabeledProbeScenario:
    scenario_id: str
    prompt: str
    labels: dict[str, str]


def load_labeled_scenarios(path: Path) -> list[LabeledProbeScenario]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = (
        payload.get("scenarios")
        or payload.get("records")
        or payload.get("rows")
        or payload
        if isinstance(payload, dict)
        else payload
    )
    if not isinstance(items, list):
        raise RuntimeError("Scenario file must be a list or contain scenarios/records/rows.")
    scenarios: list[LabeledProbeScenario] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or item.get("prompt_text") or item.get("text") or "").strip()
        if not prompt:
            continue
        labels = extract_labels(item)
        if not labels:
            continue
        scenarios.append(
            LabeledProbeScenario(
                scenario_id=str(item.get("id") or item.get("scenario_id") or f"scenario-{index + 1:04d}"),
                prompt=prompt,
                labels=labels,
            )
        )
    if not scenarios:
        raise RuntimeError("No labeled scenarios found.")
    return scenarios


def extract_labels(item: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    expected = item.get("expected_cas_axes")
    if isinstance(expected, dict):
        domain = _clean_label(expected.get("domain"))
        drive = _clean_label(expected.get("drive"))
        register = _clean_label(expected.get("register"))
        foundation = _normalise_foundation(expected.get("foundation"))
        element = _normalise_element(expected.get("element"))
        noetic = _clean_label(expected.get("noetic"))
        operator = _clean_label(expected.get("operator"))
        if domain and _single_or_combo_domain(domain):
            labels["domain"] = domain
        if drive and drive.startswith("F"):
            labels["drive"] = drive
        if register in REGISTER_VALUES:
            labels["register"] = register
        if foundation:
            labels["foundation"] = foundation
        if element:
            labels["element"] = element
        if operator and operator.startswith("^"):
            labels["operator"] = operator
        if noetic:
            labels["noetic"] = noetic

    domain = _first_clean(item.get("target_domain"), item.get("target_domains"))
    if domain and domain in DOMAIN_VALUES:
        labels.setdefault("domain", domain)
    drive = _first_drive(item.get("target_drives"))
    if drive is not None:
        labels.setdefault("drive", f"F{drive + 1}")
    operator = _first_int(item.get("target_operators"))
    if operator is not None:
        labels.setdefault("operator", f"^{operator}")
    if labels.get("drive") and labels.get("register"):
        labels.setdefault("foundation", f"{labels['drive']}|{labels['register']}")
    if labels.get("operator") and labels.get("domain"):
        labels.setdefault("element", f"{labels['operator']}|{labels['domain']}")
    return labels


def label_distributions(scenarios: list[LabeledProbeScenario]) -> dict[str, dict[str, int]]:
    counters: dict[str, Counter[str]] = {}
    for scenario in scenarios:
        for axis, label in scenario.labels.items():
            counters.setdefault(axis, Counter())[label] += 1
    return {axis: dict(sorted(counter.items())) for axis, counter in sorted(counters.items())}


def _single_or_combo_domain(value: str) -> bool:
    if value in DOMAIN_VALUES:
        return True
    return all(part in DOMAIN_VALUES for part in value.split("+"))


def _first_clean(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, list):
            for item in value:
                cleaned = _clean_label(item)
                if cleaned:
                    return cleaned
        else:
            cleaned = _clean_label(value)
            if cleaned:
                return cleaned
    return None


def _first_drive(value: Any) -> int | None:
    raw = _first_int(value)
    if raw is None:
        return None
    if 0 <= raw <= 6:
        return raw
    if 1 <= raw <= 7:
        return raw - 1
    return None


def _first_int(value: Any) -> int | None:
    if isinstance(value, list):
        for item in value:
            parsed = _parse_int(item)
            if parsed is not None:
                return parsed
    return _parse_int(value)


def _parse_int(value: Any) -> int | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_label(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalise_foundation(value: Any) -> str | None:
    text = _clean_label(value)
    if not text:
        return None
    if "|" in text:
        drive, register = text.split("|", 1)
        if drive.startswith("F") and register in REGISTER_VALUES:
            return f"{drive}|{register}"
    if len(text) >= 3 and text[0] == "F":
        drive = text[:-1]
        register = text[-1]
        if drive.startswith("F") and register in REGISTER_VALUES:
            return f"{drive}|{register}"
    return None


def _normalise_element(value: Any) -> str | None:
    text = _clean_label(value)
    if not text:
        return None
    if "|" in text:
        operator, domain = text.split("|", 1)
        if operator.startswith("^") and domain in DOMAIN_VALUES:
            return f"{operator}|{domain}"
    return None
