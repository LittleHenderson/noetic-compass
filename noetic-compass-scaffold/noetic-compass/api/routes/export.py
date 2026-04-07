"""GET /assessments/export — download assessments as CSV or JSON."""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from api.store import get_assessments

router = APIRouter()

# CSV column schema
_CSV_COLUMNS = [
    "timestamp",
    "text",
    "composite",
    "certification",
    "operator_profile",
    "domain_coherence",
    "drive_rpm_integrity",
    "pathway_quality",
    "inversion_resistance",
    "social_engineering",
    "co_0",
    "co_1",
    "co_2",
    "co_3",
    "co_4",
    "co_5",
    "co_6",
    "co_7",
    "co_8",
    "co_9",
    "domain_P",
    "domain_C",
    "domain_E",
    "domain_O",
    "provider",
    "elapsed_ms",
]


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten a stored assessment record into CSV-friendly dict."""
    resp = record.get("response", {})
    nccs = resp.get("nccs", {})
    provenance = resp.get("provenance", {})
    stages = resp.get("stages", [])

    # Extract per-operator scores from operator_scoring stage
    co_scores: list[float] = []
    domain_avgs: list[float] = []
    for stage in stages:
        name = stage.get("stage", "")
        data = stage.get("data", {})
        if name == "operator_scoring":
            co_scores = data.get("operator_scores", [])
        elif name == "domain_coherence":
            domain_avgs = data.get("domain_averages", [])

    row: dict[str, Any] = {
        "timestamp": record.get("timestamp", ""),
        "text": record.get("text", "")[:200],
        "composite": nccs.get("composite", ""),
        "certification": nccs.get("certification", ""),
        "operator_profile": nccs.get("operator_profile", ""),
        "domain_coherence": nccs.get("domain_coherence", ""),
        "drive_rpm_integrity": nccs.get("drive_rpm_integrity", ""),
        "pathway_quality": nccs.get("pathway_quality", ""),
        "inversion_resistance": nccs.get("inversion_resistance", ""),
        "social_engineering": nccs.get("social_engineering", ""),
    }

    # Per-operator scores
    for i in range(10):
        row[f"co_{i}"] = co_scores[i] if i < len(co_scores) else ""

    # Domain averages
    domain_keys = ["domain_P", "domain_C", "domain_E", "domain_O"]
    for i, key in enumerate(domain_keys):
        row[key] = domain_avgs[i] if i < len(domain_avgs) else ""

    row["provider"] = provenance.get("connector", "")
    row["elapsed_ms"] = provenance.get("elapsed_ms", "")

    return row


@router.get("/assessments/export")
async def export_assessments(
    request: Request,
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> Any:
    """Export stored assessments as JSON or CSV."""
    api_key = getattr(request.state, "api_key", "default")
    records = get_assessments(api_key)

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(_flatten_record(record))

        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=assessments.csv"},
        )

    # JSON format: return flattened records
    return JSONResponse(content=[_flatten_record(r) for r in records])
