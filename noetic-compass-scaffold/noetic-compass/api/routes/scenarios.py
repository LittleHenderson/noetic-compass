"""Scenario catalog API — serves all scenario catalogs to the dashboard."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from api.scenario_notation import enrich_scenario_with_notation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

CATALOG_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios" / "catalog"
RAW_ID_TITLE_PATTERN = re.compile(r"^[a-z]{2,4}-\d{2,3}$", re.IGNORECASE)


def _humanize_identifier(value: str) -> str:
    words = value.replace("-", " ").replace("_", " ").split()
    if not words:
        return value

    minor_words = {"a", "an", "and", "as", "at", "for", "in", "of", "on", "or", "the", "to", "vs"}
    formatted: list[str] = []
    for index, word in enumerate(words):
        lower = word.lower()
        if lower == "ai":
            formatted.append("AI")
        elif index > 0 and index < len(words) - 1 and lower in minor_words:
            formatted.append(lower)
        else:
            formatted.append(lower.capitalize())
    return " ".join(formatted)


def _derive_display_title(scenario: dict) -> str:
    title = (scenario.get("title") or "").strip()
    scenario_id = (scenario.get("id") or "").strip()

    if title and title != scenario_id and not RAW_ID_TITLE_PATTERN.fullmatch(title):
        return title

    for field in ("attack_pattern", "threshold_test", "drift_measurement"):
        value = scenario.get(field)
        if isinstance(value, str) and value.strip():
            candidate = value.strip()
            if field == "drift_measurement":
                candidate = candidate.split("?", 1)[0].strip()
            return _humanize_identifier(candidate)

    group_label = scenario.get("group_label")
    if isinstance(group_label, str) and group_label.strip():
        return group_label.strip()

    if scenario_id:
        return _humanize_identifier(scenario_id)
    return "Untitled"


def _load_all() -> list[dict]:
    """Load and merge all scenario catalog JSON files."""
    all_scenarios: list[dict] = []
    if not CATALOG_DIR.exists():
        return all_scenarios

    for json_file in sorted(CATALOG_DIR.glob("*.json")):
        if json_file.name.startswith("generate"):
            continue
        try:
            data = json.loads(json_file.read_text())
            scenarios = data.get("scenarios", [])
            for s in scenarios:
                # Normalize field names (some catalogs use prompt_text, some use prompt)
                if "prompt_text" in s and "prompt" not in s:
                    s["prompt"] = s["prompt_text"]
                elif "prompt" in s and "prompt_text" not in s:
                    s["prompt_text"] = s["prompt"]
                # Ensure category
                s.setdefault("category", data.get("metadata", {}).get("category", json_file.stem))
                s["title"] = _derive_display_title(s)
                s.setdefault("difficulty", "moderate")
            all_scenarios.extend(scenarios)
        except (json.JSONDecodeError, KeyError):
            continue

    # Enrich every scenario with backend-validated CAS notation
    enriched: list[dict] = []
    for scenario in all_scenarios:
        try:
            enriched.append(enrich_scenario_with_notation(scenario))
        except Exception:
            logger.exception("Notation enrichment failed for scenario %s", scenario.get("id"))
            enriched.append(scenario)

    return enriched


@router.get("")
@router.get("/")
async def get_all_scenarios(
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    group: Optional[str] = Query(None, description="Filter by group (adversarial sub-group)"),
    co: Optional[int] = Query(None, description="Filter by target operator index (0-9)"),
    drive: Optional[int] = Query(None, description="Filter by target drive index (0-6)"),
    q: Optional[str] = Query(None, description="Search text in prompts and titles"),
):
    """Return all scenarios, optionally filtered."""
    scenarios = _load_all()

    if category:
        scenarios = [s for s in scenarios if s.get("category") == category]
    if difficulty:
        scenarios = [s for s in scenarios if s.get("difficulty") == difficulty]
    if group:
        scenarios = [s for s in scenarios if s.get("group") == group]
    if co is not None:
        scenarios = [s for s in scenarios if co in s.get("target_operators", [])]
    if drive is not None:
        scenarios = [s for s in scenarios if drive in s.get("target_drives", [])]
    if q:
        q_lower = q.lower()
        scenarios = [
            s for s in scenarios
            if q_lower in (s.get("prompt_text") or s.get("prompt", "")).lower()
            or q_lower in s.get("title", "").lower()
            or q_lower in s.get("what_it_tests", "").lower()
        ]

    return {"scenarios": scenarios, "total": len(scenarios)}


@router.get("/categories")
async def get_categories():
    """Return list of categories with scenario counts."""
    scenarios = _load_all()
    cats: dict[str, int] = {}
    for s in scenarios:
        cat = s.get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1
    return {
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(cats.items(), key=lambda x: -x[1])
        ],
        "total": len(scenarios),
    }


@router.get("/{scenario_id}")
async def get_scenario_by_id(scenario_id: str):
    """Return a single scenario by ID."""
    for s in _load_all():
        if s.get("id") == scenario_id:
            return s
    return {"error": f"Scenario '{scenario_id}' not found"}
