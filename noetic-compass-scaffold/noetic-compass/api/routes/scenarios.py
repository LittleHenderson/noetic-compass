"""Scenario catalog API — serves all scenario catalogs to the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

CATALOG_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios" / "catalog"


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
                s.setdefault("title", s.get("id", "Untitled"))
                s.setdefault("difficulty", "moderate")
            all_scenarios.extend(scenarios)
        except (json.JSONDecodeError, KeyError):
            continue

    return all_scenarios


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
