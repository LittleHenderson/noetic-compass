"""Human Validation Study API.

Endpoints:
- GET  /validation/items              list all items with label status
- GET  /validation/next                get next unlabeled item for a rater
- POST /validation/label               submit a human label
- GET  /validation/stats               headline statistics
- GET  /validation/leaderboard         full correlation data
- GET  /validation/export              download labels as CSV or JSON
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from api.validation.correlation import (
    compute_inter_rater_kappa,
    compute_operator_correlations,
    compute_stats,
    generate_recommendations,
    load_labels,
    load_machine_results,
    save_labels,
    OPERATOR_NAMES,
    DOMAIN_NAMES,
)

router = APIRouter(prefix="/validation", tags=["validation"])


# ── Pydantic Schemas ──


class LabelSubmit(BaseModel):
    """Human label submission."""

    item_index: int = Field(..., description="Index of the item in baseline_results.json")
    rater: str = Field(..., min_length=1, max_length=80)
    operator_scores: list[int] = Field(..., description="10 scores, each 0-10")
    domain_scores: list[int] = Field(..., description="4 scores, each 0-10")
    notes: str = ""

    @field_validator("operator_scores")
    @classmethod
    def _ops_len(cls, v: list[int]) -> list[int]:
        if len(v) != 10:
            raise ValueError("operator_scores must have exactly 10 values")
        for s in v:
            if not (0 <= s <= 10):
                raise ValueError(f"operator score {s} out of range (must be 0-10)")
        return v

    @field_validator("domain_scores")
    @classmethod
    def _doms_len(cls, v: list[int]) -> list[int]:
        if len(v) != 4:
            raise ValueError("domain_scores must have exactly 4 values")
        for s in v:
            if not (0 <= s <= 10):
                raise ValueError(f"domain score {s} out of range (must be 0-10)")
        return v


class ItemSummary(BaseModel):
    """Light item summary with label status."""

    item_index: int
    prompt: str
    model: str = ""
    labeled_by: list[str] = Field(default_factory=list)
    label_count: int = 0


class LabelResponse(BaseModel):
    """Response after submitting a label."""

    status: str
    label_count: int
    machine_scores: list[float] | None = None
    machine_domain_averages: list[float] | None = None


# ── Helpers ──


def _item_to_summary(item: dict, labels_by_index: dict[int, list[dict]]) -> ItemSummary:
    idx = int(item.get("index", -1))
    existing = labels_by_index.get(idx, [])
    prompt = str(item.get("prompt", ""))
    llm = item.get("llm_response")
    model = ""
    if isinstance(llm, dict):
        model = str(llm.get("model", ""))
    return ItemSummary(
        item_index=idx,
        prompt=prompt,
        model=model,
        labeled_by=[str(l.get("rater", "")) for l in existing],
        label_count=len(existing),
    )


def _labels_by_index(labels: list[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for label in labels:
        idx = label.get("item_index")
        if idx is None:
            continue
        out.setdefault(int(idx), []).append(label)
    return out


# ── Endpoints ──


@router.get("/items")
async def list_items():
    """List all items with label status."""
    labels = load_labels()
    machine = load_machine_results()
    by_idx = _labels_by_index(labels)
    items = [_item_to_summary(item, by_idx) for item in machine]
    return {
        "items": [i.model_dump() for i in items],
        "total": len(items),
        "labeled": sum(1 for i in items if i.label_count > 0),
    }


@router.get("/next")
async def get_next_item(
    rater: str = Query(..., min_length=1, max_length=80),
    include_response: bool = Query(True),
):
    """Return the next item this rater hasn't labeled yet, with full prompt + response."""
    labels = load_labels()
    machine = load_machine_results()
    by_idx = _labels_by_index(labels)

    # Find first item this rater hasn't labeled
    for item in machine:
        idx = int(item.get("index", -1))
        existing = by_idx.get(idx, [])
        if any(str(l.get("rater")) == rater for l in existing):
            continue

        llm = item.get("llm_response")
        response_text = ""
        model = ""
        if isinstance(llm, dict):
            response_text = str(llm.get("text", ""))
            model = str(llm.get("model", ""))

        total_labeled_by_rater = sum(
            1 for l in labels if str(l.get("rater")) == rater
        )

        return {
            "item_index": idx,
            "prompt": str(item.get("prompt", "")),
            "response": response_text if include_response else "",
            "model": model,
            "total_items": len(machine),
            "rater_progress": total_labeled_by_rater,
        }

    return {
        "item_index": None,
        "prompt": "",
        "response": "",
        "model": "",
        "total_items": len(machine),
        "rater_progress": sum(1 for l in labels if str(l.get("rater")) == rater),
        "complete": True,
    }


@router.post("/label", response_model=LabelResponse)
async def submit_label(submission: LabelSubmit):
    """Save a new human label and return machine scores for comparison."""
    labels = load_labels()
    machine = load_machine_results()

    # Build the label record
    item = next(
        (m for m in machine if int(m.get("index", -1)) == submission.item_index),
        None,
    )
    prompt = str(item.get("prompt", "")) if item else ""

    new_label = {
        "prompt": prompt,
        "rater": submission.rater,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operator_scores": submission.operator_scores,
        "domain_scores": submission.domain_scores,
        "item_index": submission.item_index,
        "notes": submission.notes,
    }

    # Append and save
    labels.append(new_label)
    save_labels(labels)

    # Return machine scores for the reveal panel (scaled to 0-10)
    machine_scores = None
    machine_domain_avgs = None
    if item:
        raw_ops = item.get("operator_scores", [])
        machine_scores = [round(float(s) * 10, 2) for s in raw_ops]
        raw_doms = item.get("domain_averages", [])
        # Scale domain averages (sum to 1) to 0-10 each relative to equal share (0.25 = 2.5)
        machine_domain_avgs = [round(float(d) * 40, 2) for d in raw_doms]

    count_for_rater = sum(1 for l in labels if str(l.get("rater")) == submission.rater)

    return LabelResponse(
        status="saved",
        label_count=count_for_rater,
        machine_scores=machine_scores,
        machine_domain_averages=machine_domain_avgs,
    )


@router.get("/stats")
async def get_stats():
    """Return headline validation statistics."""
    labels = load_labels()
    machine = load_machine_results()
    return compute_stats(labels, machine)


@router.get("/leaderboard")
async def get_leaderboard():
    """Return complete leaderboard data: stats, per-operator correlations, kappa, recommendations."""
    labels = load_labels()
    machine = load_machine_results()

    stats = compute_stats(labels, machine)
    correlations = compute_operator_correlations(labels, machine)
    inter_rater = compute_inter_rater_kappa(labels)
    recommendations = generate_recommendations(correlations)

    return {
        "stats": stats,
        "operator_correlations": correlations,
        "inter_rater": inter_rater,
        "recommendations": recommendations,
        "operator_names": OPERATOR_NAMES,
        "domain_names": DOMAIN_NAMES,
    }


@router.get("/export")
async def export_labels(format: str = Query("json", pattern="^(json|csv)$")):
    """Export all labels as JSON or CSV."""
    labels = load_labels()
    if format == "json":
        return {"labels": labels, "count": len(labels)}

    # CSV export
    buf = io.StringIO()
    if not labels:
        return PlainTextResponse("no labels\n", media_type="text/csv")

    fields = ["item_index", "rater", "timestamp"] + [f"CO-{i}" for i in range(10)] + ["P", "C", "E", "O", "notes"]
    writer = csv.writer(buf)
    writer.writerow(fields)
    for label in labels:
        ops = label.get("operator_scores") or [""] * 10
        doms = label.get("domain_scores") or [""] * 4
        writer.writerow(
            [
                label.get("item_index", ""),
                label.get("rater", ""),
                label.get("timestamp", ""),
                *ops,
                *doms,
                label.get("notes", ""),
            ]
        )
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")
