"""B-4 product-routing eval — measures shipped product behavior, not raw model.

Companion to ``b4_failure_eval.py``. The raw-model harness measures what the
B-3 native generator produces when wired directly to the K=9 classifier.
This harness measures what the **user actually sees** after the OOD routing
gate (committed in ``cas_native.inference.ood_gate``) intercepts the request
flow and short-circuits casual / confused / frustrated prompts to canned
plain-English replies before the native generator ever runs.

Why this exists
---------------

The B-4.1 human audit (``docs/working/path_B4_human_relevance_failure_2026_05_07.md``)
recorded an 86.7% raw-model fail rate on 60 prompts. The failure mode was
specifically: casual prompts ("what up", "this shit is wack") landed at the
native generator and produced confidently-wrong CAS-flavored prose. The fix
shipped in chat.py is the OODGate — a pure routing layer that consults the
K=9 detector's existing OOD verdict and emits canned plain-English when the
prompt is clearly outside CAS distribution.

After that fix, the right question stops being "what does the raw model
produce?" and becomes "what does the **product** produce?". This harness
answers that. It runs the same 60-prompt fixture through the full shipped
pipeline (gate -> optional pipeline) and reports:

  * per-category fail rates (PRODUCT behavior — what the user sees)
  * per-category route_match accuracy (does the gate route the way the
    fixture says it should?)
  * a comparison block against the raw-model harness manifest, per category,
    so the headline value of the gate is visible at a glance.

Hard constraints
----------------

  * Does NOT modify ``cas_native.inference.ood_gate`` (committed contract).
  * Does NOT modify ``cas_native.inference.chat`` (committed).
  * Does NOT modify ``b4_failure_eval.py`` (the raw-model eval is preserved
    intact for regression measurement).
  * Does NOT add prompts to the fixture; reuses the 60-prompt fixture.

Category-aware scoring policy
-----------------------------

Per-prompt scoring depends on the gate decision AND the category:

  * ``casual_greeting / confusion / frustration`` — fixture's expected_route
    is ``fallback`` or ``clarification``. Gated routing IS success: if the
    gate intercepts, this prompt PASSES. If the gate green-lights the CAS
    pipeline (regression), score the resulting reply with the same policy
    as the raw-model harness.

  * ``valid_cas_notation / v76_production / v77_omega / meta_logic /
    fractal_composition`` — fixture's expected_route is ``cas_pipeline``.
    Gated routing IS failure: if the gate blocks the pipeline for these,
    that's a regression and counts as FAIL. If the gate green-lights, run
    the full Stage 1 + Stage 2 + 7-dim + preservation scoring.

  * ``simple_cas_question`` — fixture's expected_route is ``cas_pipeline``.
    Same policy as the valid-CAS bucket above.

  * ``invalid_cas`` — fixture's expected_route is ``cas_pipeline`` (the
    user expects a useful response to a malformed CAS string). Gated
    routing to clarification or conversational fallback is OK; gated
    routing producing a non-empty canned response counts as PASS.

CLI
---

    python -m cas_native.evaluation.b4_product_routing_eval \
        --checkpoint <path-to-runs/b3_full_50k_prodshape_20260507> \
        --prompts cas-native/evaluation/fixtures/b4_failure_prompts.jsonl \
        --out cas-native/evaluation/runs/b4_product_routing_eval_<date>.json \
        [--raw-model-manifest cas-native/evaluation/runs/b4_failure_eval_b3_full_50k_prodshape.json]

When ``--raw-model-manifest`` is given, the manifest produced by THIS harness
includes a ``comparison`` block showing raw-model vs product fail rate per
category. That block is the headline value of this eval.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import types
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Path bootstrap — mirror b4_failure_eval.py / chat.py
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT_CANDIDATE = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if _REPO_ROOT_CANDIDATE.exists():
    REPO_ROOT = _REPO_ROOT_CANDIDATE
else:
    REPO_ROOT = _THIS_FILE.resolve().parents[2]

if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Reuse machinery from the raw-model harness
# ---------------------------------------------------------------------------

from cas_native.evaluation.b4_failure_eval import (  # noqa: E402
    HarnessConfig,
    _CATEGORY_FAIL_POLICY,
    _expression_from_prediction,
    _load_b3_native_generator,
    _placeholder_score_preservation,
    _resolve_preservation_scorer,
    detect_leakage,
    load_prompts,
    run_stage_2_reply,
    score_compiler_validity,
    score_directness,
    score_non_rambling,
    score_plain_language_clarity,
    score_relevance,
    write_manifest,
)
from cas_native.inference.ood_gate import (  # noqa: E402
    GateResult,
    OODGate,
    RouteDecision,
)


# ---------------------------------------------------------------------------
# Expected-route -> RouteDecision mapping
# ---------------------------------------------------------------------------
#
# The fixture's ``expected_route`` field uses a small, deliberately-loose
# vocabulary ({cas_pipeline, clarification, fallback}) that does not
# distinguish between the gate's CONVERSATIONAL_FALLBACK and NEED_CONTEXT
# branches. ``need_context`` is a "low-confidence CAS" branch that — for the
# purposes of this fixture — semantically aligns with ``clarification`` (in
# both, the model says "I don't have enough to ship a confident CAS reply").
# ``conv_fallback`` aligns with ``fallback``.

_EXPECTED_TO_DECISIONS: dict[str, set[RouteDecision]] = {
    "cas_pipeline": {RouteDecision.CAS_PIPELINE},
    "clarification": {RouteDecision.CLARIFICATION, RouteDecision.NEED_CONTEXT},
    "fallback": {RouteDecision.CONVERSATIONAL_FALLBACK},
}


def is_route_match(expected: str, actual: RouteDecision) -> bool:
    """Return True iff ``actual`` is in the set of decisions ``expected`` allows."""
    allowed = _EXPECTED_TO_DECISIONS.get(expected)
    if allowed is None:
        return False
    return actual in allowed


# ---------------------------------------------------------------------------
# Categories — which expect to be gated, which expect CAS pipeline
# ---------------------------------------------------------------------------
#
# Categories where gating is the correct outcome (prompt should NEVER reach
# the native generator). For these, ``decision != CAS_PIPELINE`` is success.
_CATEGORIES_GATED_IS_SUCCESS = {
    "casual_greeting",
    "confusion",
    "frustration",
}

# Categories where the gate should green-light the pipeline. For these,
# ``decision != CAS_PIPELINE`` is a routing regression and counts as failure.
_CATEGORIES_PIPELINE_REQUIRED = {
    "valid_cas_notation",
    "v76_production",
    "v77_omega",
    "meta_logic",
    "fractal_composition",
    "simple_cas_question",
}

# Categories where either outcome is potentially acceptable. ``invalid_cas``
# expects ``cas_pipeline`` per the fixture (the user wants a constructive
# answer about a malformed expression), but a clarification / fallback that
# produces a constructive canned response is also acceptable since the input
# is not parseable CAS to begin with.
_CATEGORIES_EITHER_ACCEPTABLE = {
    "invalid_cas",
}


# ---------------------------------------------------------------------------
# Simulated K=9 result construction (mirror chat.py exactly)
# ---------------------------------------------------------------------------
#
# chat.py ``_predict_and_show`` pre-computes a ``k9_result_for_gate`` dict by
# (a) running the predictor, (b) appending the OOD-detection note string into
# a ``notes`` list when ``detect_cas_signal`` reports no signal. We mirror
# that exact construction so the gate sees the same input it sees in chat.py.
#
# The OOD-note text is the load-bearing sentinel substring the gate matches
# on; we copy it verbatim from chat.py (it begins with "no CAS signal
# detected" — the gate matches the prefix, not the full sentence).

_CHAT_OOD_NOTE = (
    "no CAS signal detected in free-form input; predicting on the "
    "raw text. The K=9 baseline tends to collapse to its prior on "
    "out-of-distribution colloquial English (documented modality "
    "limitation)."
)


def build_k9_result_for_gate(
    prediction: dict[str, Any],
    *,
    has_cas_signal: bool,
) -> dict[str, Any]:
    """Build the dict chat.py passes to ``OODGate.route``.

    Mirror of chat.py:_predict_and_show k9_result_for_gate construction:

        k9_result_for_gate: dict[str, Any] = dict(prediction)
        gate_notes: list[str] = []
        if ood_note is not None:
            gate_notes.append(ood_note)
        if gate_notes:
            k9_result_for_gate["notes"] = gate_notes

    The gate looks for the OOD-note sentinel substring in any string-valued
    note field. If ``has_cas_signal`` is True we omit the note (the gate
    will fall through to the confidence floor and otherwise CAS_PIPELINE).
    """
    out: dict[str, Any] = dict(prediction or {})
    if not has_cas_signal:
        out["notes"] = [_CHAT_OOD_NOTE]
    return out


def _detect_signal_safe(text: str) -> dict[str, Any]:
    """Wrap ``detect_cas_signal`` to never raise; degrade to no-signal on error.

    The rewrite_shim API is the contract chat.py consumes. We import lazily
    so the harness module can be imported (and unit-tested) without the
    rewrite_shim being importable.
    """
    try:
        from cas_native.inference.rewrite_shim import detect_cas_signal  # type: ignore
    except Exception:
        # If the shim is not importable for any reason, default to "no signal"
        # — that is the conservative branch for routing (gate gets the OOD
        # sentinel and routes to clarification/fallback).
        return {"has_signal": False}

    try:
        signal = detect_cas_signal(text)
    except Exception:
        return {"has_signal": False}
    if not isinstance(signal, dict):
        return {"has_signal": False}
    return signal


# ---------------------------------------------------------------------------
# Per-prompt result row
# ---------------------------------------------------------------------------


@dataclass
class PerPromptRoutingResult:
    """One row in the product-routing manifest.

    Two flavors of row:

    * Gated rows (``gated=True``): gate intercepted; canned response shown;
      Stage 1/Stage 2 fields omitted; relevance/directness scored on the
      canned response (which is plain English, addresses the user, and is
      short — so it scores well by construction for casual/confusion/
      frustration buckets).

    * Pipeline rows (``gated=False``): gate green-lit the pipeline; full
      Stage 1 + Stage 2 + 7-user-facing dims + 10 preservation booleans
      reported, mirroring the raw-model harness.
    """

    id: str
    category: str
    prompt_text: str
    expected_route: str
    actual_route: str
    route_match: bool
    gated: bool
    gate_canned_response: str | None
    gate_reason: str
    ground_truth_cas: str | None
    notes: str | None

    # Stage 1 (always populated; gate is consulted AFTER predictor runs)
    stage1_prediction: dict[str, Any] = field(default_factory=dict)
    stage1_expression: str = ""
    stage1_register: str | None = None

    # Stage 2 (None when gated)
    stage2_reply: str | None = None
    stage2_n_steps: int | None = None
    stage2_stopped_on_eos: bool | None = None

    # Auto-scored user-facing dimensions. Always populated; for gated rows
    # the scored "reply" is the canned response.
    relevance_score: int = 0
    relevance_raw: float = 0.0
    relevance_source: str = ""

    directness_score: int = 0
    directness_info: dict[str, Any] = field(default_factory=dict)

    non_rambling_score: int = 0
    non_rambling_info: dict[str, Any] = field(default_factory=dict)

    compiler_validity: bool = False
    compiler_validity_info: dict[str, Any] = field(default_factory=dict)

    plain_language_clarity_score: int = 0
    plain_language_clarity_info: dict[str, Any] = field(default_factory=dict)

    leakage: bool = False
    leakage_hits: list[str] = field(default_factory=list)

    # Delegated structural-preservation (Agent D); empty / placeholder for
    # gated rows (we never run Stage 1 against the user's prompt for those
    # in the sense of "did the model preserve the recipe shape" — the user
    # never asked for a recipe).
    preservation: dict[str, Any] = field(default_factory=dict)

    # Aggregate failure flags
    failed: bool = False
    failure_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Failure policy — category-aware
# ---------------------------------------------------------------------------


def apply_routing_failure_policy(row: PerPromptRoutingResult) -> None:
    """Set ``row.failed`` / ``row.failure_reasons`` per category-aware policy.

    Rules:

      1. ``_CATEGORIES_PIPELINE_REQUIRED`` and the gate did NOT route to
         CAS_PIPELINE: ``regression_gate_blocked_pipeline`` (FAIL).

      2. ``_CATEGORIES_GATED_IS_SUCCESS`` and the gate DID route to
         CAS_PIPELINE (no gating happened): score the row using the
         raw-model failure policy from b4_failure_eval (relevance/
         directness/non_rambling/leakage/stage2_empty).

      3. ``_CATEGORIES_GATED_IS_SUCCESS`` and the gate gated the prompt:
         PASS by definition (gate did its job). The canned reply is checked
         for surface integrity (non-empty, non-leaky) but those are sanity
         checks rather than failure conditions.

      4. ``_CATEGORIES_PIPELINE_REQUIRED`` and the gate green-lit the
         pipeline: score Stage 2 using the raw-model failure policy
         restricted to the rules that apply for this category.

      5. ``_CATEGORIES_EITHER_ACCEPTABLE`` (``invalid_cas``): PASS as long
         as the user got *some* non-empty response (canned or generated).
    """
    reasons: list[str] = []

    cat = row.category

    # ---- Routing regressions -----------------------------------------------
    if cat in _CATEGORIES_PIPELINE_REQUIRED and row.gated:
        reasons.append("regression_gate_blocked_pipeline")
        # We still set leakage / preservation fields for diagnostic reporting,
        # but a routing regression is itself the headline failure.
        row.failure_reasons = reasons
        row.failed = True
        return

    # ---- Gated-rows for casual/confusion/frustration (PASS path) -----------
    if cat in _CATEGORIES_GATED_IS_SUCCESS and row.gated:
        # Sanity: ensure the canned response is non-empty and non-leaky. The
        # OODGate canned strings are hard-coded plain English so this is a
        # contract check. Empty or leaky here means the gate API contract has
        # been broken.
        if row.stage2_reply is None and not (row.gate_canned_response or "").strip():
            reasons.append("gate_returned_empty_canned_response")
        if row.leakage:
            reasons.append("gate_canned_response_leaks_cas_notation")
        row.failure_reasons = reasons
        row.failed = bool(reasons)
        return

    # ---- Either-acceptable (invalid_cas) -----------------------------------
    if cat in _CATEGORIES_EITHER_ACCEPTABLE:
        # PASS as long as some non-empty response exists.
        served = (row.gate_canned_response or "") if row.gated else (row.stage2_reply or "")
        if not served.strip():
            reasons.append("empty_response")
        row.failure_reasons = reasons
        row.failed = bool(reasons)
        return

    # ---- Pipeline rows for casual/confusion/frustration (gate failed
    #      to intercept; raw-model failure policy applies) ------------------
    # ---- Pipeline rows for valid_cas_notation / v76_production / v77_omega /
    #      meta_logic / fractal_composition / simple_cas_question (raw-model
    #      failure policy applies) -------------------------------------------
    rules = _CATEGORY_FAIL_POLICY.get(cat, [])
    if "leakage" in rules and row.leakage:
        reasons.append("leakage")
    if "non_rambling_lt_3" in rules and row.non_rambling_score < 3:
        reasons.append("non_rambling_lt_3")
    if "plain_lt_3" in rules and row.plain_language_clarity_score < 3:
        reasons.append("plain_language_lt_3")
    if "relevance_lt_3" in rules and row.relevance_score < 3:
        reasons.append("relevance_lt_3")
    if "directness_lt_3" in rules and row.directness_score < 3:
        reasons.append("directness_lt_3")
    if "stage2_empty" in rules:
        if row.stage2_reply is None or not row.stage2_reply.strip():
            reasons.append("stage2_empty")
    if "preservation_failed" in rules:
        is_placeholder = bool(row.preservation.get("placeholder", False))
        score = None
        if isinstance(row.preservation, dict):
            score = row.preservation.get("preservation_score")
            if score is None:
                score = row.preservation.get("score")
        if not is_placeholder and (score is None or score < 0.6):
            reasons.append("preservation_failed")

    row.failure_reasons = reasons
    row.failed = bool(reasons)


# ---------------------------------------------------------------------------
# Per-prompt evaluation
# ---------------------------------------------------------------------------


def evaluate_prompt_routing(
    *,
    prompt: dict[str, Any],
    predictor: Any,
    native_generator: dict[str, Any] | None,
    preservation_scorer: Any,
    config: HarnessConfig,
    gate: OODGate,
    apply_rewrite: bool = True,
) -> PerPromptRoutingResult:
    """Run the per-prompt product-routing evaluation.

    Pipeline ordering mirrors chat.py:_predict_and_show:

      1. detect_cas_signal -> (signal, optional_rewrite, optional_ood_note)
      2. predictor(rewritten_or_raw_text) -> prediction
      3. build k9_result_for_gate
      4. gate.route(prompt_text, k9_result_for_gate) -> GateResult
      5. branch on decision: gated or pipeline

    The PROMPT TEXT passed to gate.route is the user's ORIGINAL prompt (not
    the rewrite). chat.py passes ``text`` (original), not ``target_text``
    (rewrite), to the gate so the casual-token regex sees the original
    free-form English.
    """
    expected_route = str(prompt.get("expected_route", "cas_pipeline"))
    row = PerPromptRoutingResult(
        id=str(prompt["id"]),
        category=str(prompt["category"]),
        prompt_text=str(prompt["prompt_text"]),
        expected_route=expected_route,
        actual_route="",  # filled below
        route_match=False,
        gated=False,
        gate_canned_response=None,
        gate_reason="",
        ground_truth_cas=prompt.get("ground_truth_cas"),
        notes=prompt.get("notes"),
    )

    # ---- Step 1: detect_cas_signal -----------------------------------------
    signal: dict[str, Any] | None = None
    target_text = row.prompt_text
    has_cas_signal = False
    if apply_rewrite:
        signal = _detect_signal_safe(row.prompt_text)
        if signal.get("has_signal"):
            has_cas_signal = True
            try:
                from cas_native.inference.rewrite_shim import (  # type: ignore
                    rewrite_to_training_surface,
                )
                target_text = rewrite_to_training_surface(row.prompt_text)
            except Exception:
                # If rewrite shim fails, predict on raw text (chat.py degrades
                # in the same way: signal-but-rewrite-fails path is rare).
                target_text = row.prompt_text

    # ---- Step 2: predictor -------------------------------------------------
    try:
        prediction = predictor(target_text)
    except Exception as exc:  # pragma: no cover - defensive
        prediction = {"_error": f"predictor failed: {exc}"}
    if not isinstance(prediction, dict):
        prediction = {"_raw": str(prediction)}
    row.stage1_prediction = prediction
    row.stage1_expression = (
        _expression_from_prediction(prediction) if isinstance(prediction, dict) else ""
    )
    registers_list = (
        prediction.get("registers") if isinstance(prediction, dict) else None
    ) or []
    row.stage1_register = str(registers_list[0]) if registers_list else "T"

    # ---- Step 3: build k9_result_for_gate ----------------------------------
    k9_result_for_gate = build_k9_result_for_gate(
        prediction, has_cas_signal=has_cas_signal
    )

    # ---- Step 4: gate.route ------------------------------------------------
    gate_result: GateResult = gate.route(row.prompt_text, k9_result_for_gate)
    row.actual_route = gate_result.decision.value
    row.gate_reason = gate_result.reason
    row.route_match = is_route_match(expected_route, gate_result.decision)
    row.gated = gate_result.decision is not RouteDecision.CAS_PIPELINE
    row.gate_canned_response = gate_result.canned_response

    # ---- Step 5: branch on decision ----------------------------------------
    if row.gated:
        # Gate intercepted. The user-facing reply IS the canned response.
        # We score it for surface integrity. We do NOT run Stage 2; the
        # native generator never sees this prompt under the product flow.
        user_facing_reply = gate_result.canned_response or ""
        # Score relevance / directness / non_rambling / clarity / leakage on
        # the canned response. The gate's canned strings are hard-coded plain
        # English by design — these scores are sanity checks, not the
        # headline metric.
        rel_score, rel_raw, rel_source = score_relevance(row.prompt_text, user_facing_reply)
        row.relevance_score = rel_score
        row.relevance_raw = rel_raw
        row.relevance_source = rel_source

        dir_score, dir_info = score_directness(row.prompt_text, user_facing_reply)
        row.directness_score = dir_score
        row.directness_info = dir_info

        nr_score, nr_info = score_non_rambling(user_facing_reply)
        row.non_rambling_score = nr_score
        row.non_rambling_info = nr_info

        plc_score, plc_info = score_plain_language_clarity(user_facing_reply)
        row.plain_language_clarity_score = plc_score
        row.plain_language_clarity_info = plc_info

        leaks, hits = detect_leakage(user_facing_reply)
        row.leakage = leaks
        row.leakage_hits = hits

        # Compiler validity / preservation: not applicable for gated rows.
        row.compiler_validity = False
        row.compiler_validity_info = {"reason": "gated_no_stage1_expression_to_compile"}
        row.preservation = {
            "placeholder": True,
            "skipped": True,
            "reason": "gated_no_pipeline_run",
        }
    else:
        # Pipeline run. Mirror the raw-model harness exactly from here on.
        if native_generator is not None and "_error" not in native_generator:
            try:
                stage2_out = run_stage_2_reply(
                    native_generator=native_generator,
                    prompt_text=row.prompt_text,
                    expression=row.stage1_expression or "",
                    register=row.stage1_register or "T",
                    config=config,
                )
                row.stage2_reply = str(stage2_out.get("reply_text", ""))
                row.stage2_n_steps = int(stage2_out.get("n_steps", 0))
                row.stage2_stopped_on_eos = bool(stage2_out.get("stopped_on_eos", False))
            except Exception as exc:
                row.stage2_reply = ""
                row.stage2_n_steps = 0
                row.stage2_stopped_on_eos = False
                row.failure_reasons.append(f"stage2_exception:{exc}")

        user_facing_reply = row.stage2_reply if row.stage2_reply is not None else ""

        rel_score, rel_raw, rel_source = score_relevance(row.prompt_text, user_facing_reply)
        row.relevance_score = rel_score
        row.relevance_raw = rel_raw
        row.relevance_source = rel_source

        dir_score, dir_info = score_directness(row.prompt_text, user_facing_reply)
        row.directness_score = dir_score
        row.directness_info = dir_info

        nr_score, nr_info = score_non_rambling(user_facing_reply)
        row.non_rambling_score = nr_score
        row.non_rambling_info = nr_info

        cv, cv_info = score_compiler_validity(row.stage1_expression)
        row.compiler_validity = cv
        row.compiler_validity_info = cv_info

        plc_score, plc_info = score_plain_language_clarity(user_facing_reply)
        row.plain_language_clarity_score = plc_score
        row.plain_language_clarity_info = plc_info

        leaks, hits = detect_leakage(user_facing_reply)
        row.leakage = leaks
        row.leakage_hits = hits

        if not row.ground_truth_cas:
            row.preservation = {
                "placeholder": True,
                "skipped": True,
                "reason": "no_ground_truth",
            }
        else:
            try:
                preservation = preservation_scorer(row.ground_truth_cas, row.stage1_expression)
                if hasattr(preservation, "__dataclass_fields__"):
                    row.preservation = asdict(preservation)
                    row.preservation.setdefault("placeholder", False)
                elif hasattr(preservation, "__dict__"):
                    row.preservation = dict(preservation.__dict__)
                elif isinstance(preservation, dict):
                    row.preservation = dict(preservation)
                else:
                    row.preservation = {"_raw": str(preservation)}
            except Exception as exc:  # pragma: no cover - defensive
                row.preservation = {
                    "placeholder": True,
                    "error": f"scorer raised: {exc}",
                }

    # ---- Failure policy ----------------------------------------------------
    apply_routing_failure_policy(row)
    return row


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_routing_results(rows: list[PerPromptRoutingResult]) -> dict[str, Any]:
    """Per-category fail rates, route_match accuracy, and reason breakdowns.

    Output shape:

        {
            "total": {
                "n", "n_failed", "fail_rate",
                "n_route_match", "route_match_rate",
                "n_gated", "gated_rate",
            },
            "categories": {
                <cat>: {
                    "n", "n_failed", "fail_rate",
                    "n_route_match", "route_match_rate",
                    "n_gated", "gated_rate",
                    "failure_reason_breakdown": {...},
                    "actual_route_breakdown": {...},
                },
                ...
            },
        }
    """
    by_cat: dict[str, list[PerPromptRoutingResult]] = defaultdict(list)
    for r in rows:
        by_cat[r.category].append(r)

    categories: dict[str, dict[str, Any]] = {}
    for cat, cat_rows in by_cat.items():
        n = len(cat_rows)
        n_failed = sum(1 for r in cat_rows if r.failed)
        n_route_match = sum(1 for r in cat_rows if r.route_match)
        n_gated = sum(1 for r in cat_rows if r.gated)

        reason_counts: dict[str, int] = defaultdict(int)
        for r in cat_rows:
            for reason in r.failure_reasons:
                reason_counts[reason] += 1

        actual_route_counts: dict[str, int] = defaultdict(int)
        for r in cat_rows:
            actual_route_counts[r.actual_route] += 1

        categories[cat] = {
            "n": n,
            "n_failed": n_failed,
            "fail_rate": n_failed / n if n else 0.0,
            "n_route_match": n_route_match,
            "route_match_rate": n_route_match / n if n else 0.0,
            "n_gated": n_gated,
            "gated_rate": n_gated / n if n else 0.0,
            "failure_reason_breakdown": dict(reason_counts),
            "actual_route_breakdown": dict(actual_route_counts),
        }

    n_total = len(rows)
    n_failed_total = sum(1 for r in rows if r.failed)
    n_route_match_total = sum(1 for r in rows if r.route_match)
    n_gated_total = sum(1 for r in rows if r.gated)
    return {
        "total": {
            "n": n_total,
            "n_failed": n_failed_total,
            "fail_rate": n_failed_total / n_total if n_total else 0.0,
            "n_route_match": n_route_match_total,
            "route_match_rate": n_route_match_total / n_total if n_total else 0.0,
            "n_gated": n_gated_total,
            "gated_rate": n_gated_total / n_total if n_total else 0.0,
        },
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# Comparison block — raw-model fail rate vs product fail rate, per category
# ---------------------------------------------------------------------------


def build_comparison_block(
    *,
    raw_manifest: dict[str, Any] | None,
    product_aggregate: dict[str, Any],
) -> dict[str, Any]:
    """Build the headline comparison block.

    Output shape:

        {
            "available": True | False,
            "per_category": {
                <cat>: {
                    "raw_model_fail_rate": float,
                    "product_fail_rate": float,
                    "delta": float,           # product - raw (negative = improvement)
                    "raw_n": int,
                    "product_n": int,
                },
                ...
            },
            "total": {
                "raw_model_fail_rate": float,
                "product_fail_rate": float,
                "delta": float,
            },
        }

    When ``raw_manifest`` is None we still produce the block with
    ``available=False`` so downstream consumers can pattern-match without a
    KeyError.
    """
    if raw_manifest is None:
        return {"available": False}

    raw_agg = (raw_manifest or {}).get("aggregate", {})
    raw_cats = raw_agg.get("categories", {})
    raw_total = raw_agg.get("total", {})

    prod_cats = product_aggregate.get("categories", {})
    prod_total = product_aggregate.get("total", {})

    per_category: dict[str, Any] = {}
    all_cats = set(raw_cats.keys()) | set(prod_cats.keys())
    for cat in sorted(all_cats):
        raw_rate = float(raw_cats.get(cat, {}).get("fail_rate", 0.0))
        prod_rate = float(prod_cats.get(cat, {}).get("fail_rate", 0.0))
        per_category[cat] = {
            "raw_model_fail_rate": raw_rate,
            "product_fail_rate": prod_rate,
            "delta": prod_rate - raw_rate,
            "raw_n": int(raw_cats.get(cat, {}).get("n", 0)),
            "product_n": int(prod_cats.get(cat, {}).get("n", 0)),
        }

    return {
        "available": True,
        "per_category": per_category,
        "total": {
            "raw_model_fail_rate": float(raw_total.get("fail_rate", 0.0)),
            "product_fail_rate": float(prod_total.get("fail_rate", 0.0)),
            "delta": float(prod_total.get("fail_rate", 0.0))
            - float(raw_total.get("fail_rate", 0.0)),
        },
    }


def load_raw_manifest(path: Path | None) -> dict[str, Any] | None:
    """Load the raw-model manifest if path is given and readable."""
    if path is None:
        return None
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="B-4 product-routing eval — measures shipped product behavior."
    )
    p.add_argument("--checkpoint", type=Path, required=True,
                   help="Path to a CAS-Native run dir (B-3 prodshape).")
    p.add_argument("--prompts", type=Path, required=True,
                   help="Path to the 60-prompt fixture JSONL (re-uses b4_failure_prompts).")
    p.add_argument("--out", type=Path, required=True,
                   help="Path to write the manifest JSON.")
    p.add_argument("--raw-model-manifest", type=Path, default=None,
                   help="Optional path to the raw-model manifest for the comparison block.")
    p.add_argument("--device", default="cpu", help="torch device (cpu|cuda)")
    p.add_argument("--max-new-tokens", type=int, default=120)
    p.add_argument("--sampling", default="top_p", choices=["greedy", "temperature", "top_p"])
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--use-cas-prefix", action="store_true",
                   help="Pass cas_prefix_ids into generation. Default OFF (matches training).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--stage1-checkpoint", type=Path, default=None,
                   help="Optional override for the Stage-1 K=9 predictor run dir.")
    p.add_argument("--gate-confidence-threshold", type=float, default=0.4,
                   help="OODGate confidence threshold (default 0.4).")
    p.add_argument("--gate-casual-word-limit", type=int, default=10,
                   help="OODGate casual word-limit (default 10).")
    p.add_argument("--limit", type=int, default=None,
                   help="Optional cap on number of prompts (smoke testing).")
    p.add_argument("--no-rewrite", action="store_true",
                   help="Skip the detect_cas_signal/rewrite step (debug only).")
    return p.parse_args(argv)


def _default_stage1_dir() -> Path:
    return (
        REPO_ROOT
        / "cas-native"
        / "training"
        / "runs"
        / "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Programmatic entry point. Returns the manifest dict."""
    from cas_native.inference.predict_cas import load_predictor

    config = HarnessConfig(
        checkpoint=str(args.checkpoint),
        prompts=str(args.prompts),
        out_path=str(args.out),
        device=str(args.device),
        max_new_tokens=int(args.max_new_tokens),
        sampling=str(args.sampling),
        temperature=float(args.temperature),
        top_p=float(args.top_p),
        use_cas_prefix=bool(args.use_cas_prefix),
        seed=int(args.seed),
    )

    prompts = load_prompts(args.prompts)
    if args.limit is not None and args.limit > 0:
        prompts = prompts[: args.limit]

    stage1_dir = (
        args.stage1_checkpoint if args.stage1_checkpoint is not None else _default_stage1_dir()
    )
    predictor = load_predictor(stage1_dir, device=str(args.device))

    native_generator = _load_b3_native_generator(args.checkpoint, device=str(args.device))
    if native_generator is None:
        generator_status = "missing_files"
    elif "_error" in native_generator:
        generator_status = native_generator["_error"]
    else:
        generator_status = "loaded"

    preservation_scorer = _resolve_preservation_scorer()
    preservation_status = (
        "loaded_from_agent_d"
        if preservation_scorer is not _placeholder_score_preservation
        else "placeholder"
    )

    gate = OODGate(
        confidence_threshold=float(args.gate_confidence_threshold),
        casual_word_limit=int(args.gate_casual_word_limit),
    )

    rows: list[PerPromptRoutingResult] = []
    for prompt in prompts:
        row = evaluate_prompt_routing(
            prompt=prompt,
            predictor=predictor,
            native_generator=native_generator
            if isinstance(native_generator, dict) and "_error" not in native_generator
            else None,
            preservation_scorer=preservation_scorer,
            config=config,
            gate=gate,
            apply_rewrite=not args.no_rewrite,
        )
        rows.append(row)

    aggregate = aggregate_routing_results(rows)

    raw_manifest = load_raw_manifest(args.raw_model_manifest)
    comparison = build_comparison_block(
        raw_manifest=raw_manifest, product_aggregate=aggregate
    )

    manifest = {
        "schema_version": "b4_product_routing_eval.v1",
        "config": asdict(config),
        "stage1_dir": str(stage1_dir),
        "generator_status": generator_status,
        "preservation_scorer_status": preservation_status,
        "gate_config": {
            "confidence_threshold": float(args.gate_confidence_threshold),
            "casual_word_limit": int(args.gate_casual_word_limit),
        },
        "raw_model_manifest_path": (
            str(args.raw_model_manifest) if args.raw_model_manifest is not None else None
        ),
        "n_prompts": len(prompts),
        "rows": [asdict(r) for r in rows],
        "aggregate": aggregate,
        "comparison": comparison,
    }
    write_manifest(args.out, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = run(args)
    agg = manifest["aggregate"]
    comp = manifest["comparison"]
    summary: dict[str, Any] = {
        "event": "b4_product_routing_eval_done",
        "n_prompts": manifest["n_prompts"],
        "generator_status": manifest["generator_status"],
        "preservation_scorer_status": manifest["preservation_scorer_status"],
        "fail_rate_total": agg["total"]["fail_rate"],
        "route_match_rate_total": agg["total"]["route_match_rate"],
        "gated_rate_total": agg["total"]["gated_rate"],
        "category_fail_rates": {
            cat: round(c["fail_rate"], 3) for cat, c in agg["categories"].items()
        },
        "category_route_match": {
            cat: round(c["route_match_rate"], 3) for cat, c in agg["categories"].items()
        },
        "out_path": manifest["config"]["out_path"],
    }
    if comp.get("available"):
        summary["comparison_total"] = comp["total"]
        summary["comparison_per_category"] = {
            cat: {
                "raw": round(v["raw_model_fail_rate"], 3),
                "product": round(v["product_fail_rate"], 3),
                "delta": round(v["delta"], 3),
            }
            for cat, v in comp["per_category"].items()
        }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
