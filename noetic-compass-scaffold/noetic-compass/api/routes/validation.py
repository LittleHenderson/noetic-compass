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
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from api.validation.correlation import (
    compute_calibration_review,
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
from api.validation.calibration_sessions import (
    append_calibration_session,
    build_calibration_session_payload,
    load_calibration_sessions,
)
from api.validation.evidence import (
    append_evidence_entry,
    build_evidence_review,
    build_evidence_summary,
    build_evidence_trends,
    export_evidence_csv,
    load_evidence,
    seed_evidence_from_artifacts,
)
from api.validation.studies import (
    available_prompt_collections,
    list_study_artifacts,
    resolve_prompt_collection,
    run_and_archive_study,
    run_suite_matrix,
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


class ScorerAgreementSubmit(BaseModel):
    """Log a scorer-agreement comparison case."""

    generator_provider: str = Field(..., min_length=1, max_length=80)
    generator_model: str | None = Field(default=None, max_length=120)
    scorer_provider: str = Field(..., min_length=1, max_length=80)
    scorer_model: str | None = Field(default=None, max_length=120)
    prompt_excerpt: str = Field(..., min_length=1, max_length=1000)
    machine_score: float = Field(..., ge=0.0, le=10.0)
    scorer_score: float = Field(..., ge=0.0, le=10.0)
    notes: str = ""
    item_index: int | None = None


class BenchmarkSuiteSubmit(BaseModel):
    """Log a benchmark suite run for later validation analysis."""

    suite_name: str = Field(..., min_length=1, max_length=120)
    provider: str = Field(..., min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    scoring_mode: str = Field(default="heuristic_fallback", pattern="^(heuristic_fallback|secondary_llm|self_reported)$")
    scoring_provider: str | None = Field(default=None, max_length=80)
    scoring_model: str | None = Field(default=None, max_length=120)
    cases_run: int = Field(..., ge=1, le=10000)
    mean_score: float = Field(..., ge=0.0, le=100.0)
    variance: float = Field(..., ge=0.0)
    notes: str = ""


class ErrorCaseSubmit(BaseModel):
    """Log a false-positive or false-negative case."""

    kind: str = Field(..., pattern="^(false_positive|false_negative)$")
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    prompt_excerpt: str = Field(..., min_length=1, max_length=1000)
    expected_tier: str = Field(..., min_length=1, max_length=80)
    observed_tier: str = Field(..., min_length=1, max_length=80)
    notes: str = ""
    item_index: int | None = None


class BaselineRunSubmit(BaseModel):
    provider: str = Field(..., min_length=1, max_length=40)
    prompt_collection: str = Field(default="sample_prompts", min_length=1, max_length=240)
    count: int = Field(default=10, ge=1, le=500)
    label: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    scoring_mode: str = Field(default="heuristic_fallback", pattern="^(heuristic_fallback|secondary_llm|self_reported)$")
    scoring_provider: str | None = Field(default=None, max_length=80)
    scoring_model: str | None = Field(default=None, max_length=120)
    reseed: bool = True


class SuiteMatrixSubmit(BaseModel):
    provider: str = Field(..., min_length=1, max_length=40)
    suite_ids: list[str] = Field(default_factory=list)
    count_per_suite: int = Field(default=5, ge=1, le=100)
    model: str | None = Field(default=None, max_length=120)
    scoring_mode: str = Field(default="heuristic_fallback", pattern="^(heuristic_fallback|secondary_llm|self_reported)$")
    scoring_provider: str | None = Field(default=None, max_length=80)
    scoring_model: str | None = Field(default=None, max_length=120)
    reseed: bool = True


class CalibrationSessionSubmit(BaseModel):
    item_index: int = Field(..., ge=0)
    reconciler: str = Field(..., min_length=1, max_length=80)
    disposition: str = Field(
        ...,
        pattern="^(resolved_panel|resolved_machine|rubric_clarification|false_positive|false_negative|needs_more_review)$",
    )
    notes: str = Field(default="", max_length=4000)
    resolved_operator_scores: list[int] | None = Field(default=None)
    resolved_domain_scores: list[int] | None = Field(default=None)

    @field_validator("resolved_operator_scores")
    @classmethod
    def _resolved_ops_len(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if len(v) != 10:
            raise ValueError("resolved_operator_scores must have exactly 10 values")
        for score in v:
            if not (0 <= score <= 10):
                raise ValueError("resolved operator scores must be between 0 and 10")
        return v

    @field_validator("resolved_domain_scores")
    @classmethod
    def _resolved_domains_len(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError("resolved_domain_scores must have exactly 4 values")
        for score in v:
            if not (0 <= score <= 10):
                raise ValueError("resolved domain scores must be between 0 and 10")
        return v


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


def _timestamped_entry(payload: dict) -> dict:
    return {
        **payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
        "calibration": compute_calibration_review(labels, machine),
        "recommendations": recommendations,
        "operator_names": OPERATOR_NAMES,
        "domain_names": DOMAIN_NAMES,
        "evidence_summary": build_evidence_summary(load_evidence()),
    }


@router.get("/calibration")
async def get_calibration():
    """Return calibration/reconciliation summaries derived from current human labels."""
    labels = load_labels()
    machine = load_machine_results()
    return compute_calibration_review(labels, machine)


@router.get("/calibration/session")
async def get_calibration_session():
    """Return the active calibration queue plus recent reconciliation history."""
    labels = load_labels()
    machine = load_machine_results()
    sessions = load_calibration_sessions()
    return build_calibration_session_payload(labels, machine, sessions)


@router.post("/calibration/session")
async def save_calibration_session(submission: CalibrationSessionSubmit):
    """Persist a calibration/reconciliation decision for a disputed item."""
    store = append_calibration_session(
        _timestamped_entry(submission.model_dump()),
    )
    return {
        "status": "saved",
        "count": len(store),
        "entry": store[-1],
    }


@router.get("/admin/catalog")
async def get_validation_catalog():
    """List available prompt collections for baseline/suite runs."""
    return {"collections": available_prompt_collections()}


@router.get("/admin/studies")
async def get_validation_studies():
    """List archived validation study artifacts."""
    return {"studies": list_study_artifacts()}


@router.post("/admin/run-baseline")
async def run_validation_baseline(submission: BaselineRunSubmit):
    """Run a baseline study, archive it, and optionally reseed evidence."""
    prompts_path = resolve_prompt_collection(submission.prompt_collection)
    result = await run_and_archive_study(
        provider=submission.provider,
        count=submission.count,
        prompts_path=prompts_path,
        model=submission.model,
        scoring_mode=submission.scoring_mode,
        scoring_provider=submission.scoring_provider,
        scoring_model=submission.scoring_model,
        study_label=submission.label or Path(prompts_path).stem,
        update_default_output=True,
    )
    response = {
        "status": "completed",
        "summary": result["bundle"]["summary"],
        "archive_path": str(result["archive_path"]),
        "output_path": str(result["output_path"]) if result.get("output_path") else None,
    }
    if submission.reseed:
        store = seed_evidence_from_artifacts(replace=True)
        response["evidence_summary"] = build_evidence_summary(store)
    return response


@router.post("/admin/run-suite-matrix")
async def run_validation_suite_matrix(submission: SuiteMatrixSubmit):
    """Run multiple prompt collections and optionally reseed evidence."""
    result = await run_suite_matrix(
        provider=submission.provider,
        suite_ids=submission.suite_ids or None,
        count_per_suite=submission.count_per_suite,
        model=submission.model,
        scoring_mode=submission.scoring_mode,
        scoring_provider=submission.scoring_provider,
        scoring_model=submission.scoring_model,
    )
    response = {"status": "completed", **result}
    if submission.reseed:
        store = seed_evidence_from_artifacts(replace=True)
        response["evidence_summary"] = build_evidence_summary(store)
    return response


@router.get("/evidence")
async def get_evidence(
    kind: str | None = Query(default=None, pattern="^(scorer_agreement|benchmark_suites|error_cases)?$"),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Return evidence summary plus a filtered review slice."""
    store = load_evidence()
    return {
        "summary": build_evidence_summary(store),
        "review": build_evidence_review(
            store,
            kind=kind,
            provider=provider,
            model=model,
            q=q,
            limit=limit,
            offset=offset,
        ),
    }


@router.get("/evidence/trends")
async def get_evidence_trends():
    """Return aggregate validation-evidence trends by provider, model, and day."""
    return build_evidence_trends(load_evidence())


@router.post("/evidence/seed")
async def seed_evidence(replace: bool = Query(default=True)):
    """Populate validation evidence from the current baseline study and human labels."""
    store = seed_evidence_from_artifacts(replace=replace)
    summary = build_evidence_summary(store)
    return {
        "status": "seeded",
        "summary": summary,
        "counts": {
            "scorer_agreement": summary["scorer_agreement"]["count"],
            "benchmark_suites": summary["benchmark_suites"]["count"],
            "error_cases": summary["error_cases"]["count"],
        },
    }


@router.post("/evidence/scorer-agreement")
async def add_scorer_agreement(submission: ScorerAgreementSubmit):
    store = append_evidence_entry(
        "scorer_agreement",
        _timestamped_entry(submission.model_dump()),
    )
    return {
        "status": "saved",
        "count": len(store["scorer_agreement"]),
        "summary": build_evidence_summary(store)["scorer_agreement"],
    }


@router.post("/evidence/benchmark-case")
async def add_benchmark_case(submission: BenchmarkSuiteSubmit):
    store = append_evidence_entry(
        "benchmark_suites",
        _timestamped_entry(submission.model_dump()),
    )
    return {
        "status": "saved",
        "count": len(store["benchmark_suites"]),
        "summary": build_evidence_summary(store)["benchmark_suites"],
    }


@router.post("/evidence/error-case")
async def add_error_case(submission: ErrorCaseSubmit):
    store = append_evidence_entry(
        "error_cases",
        _timestamped_entry(submission.model_dump()),
    )
    return {
        "status": "saved",
        "count": len(store["error_cases"]),
        "summary": build_evidence_summary(store)["error_cases"],
    }


@router.get("/evidence/export")
async def export_evidence(
    format: str = Query("json", pattern="^(json|csv)$"),
    kind: str | None = Query(default=None, pattern="^(scorer_agreement|benchmark_suites|error_cases)?$"),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """Export validation evidence with optional filters."""
    store = load_evidence()
    if format == "json":
        return build_evidence_review(store, kind=kind, provider=provider, model=model, q=q, limit=100000, offset=0)
    return PlainTextResponse(
        export_evidence_csv(store, kind=kind, provider=provider, model=model, q=q),
        media_type="text/csv",
    )


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
