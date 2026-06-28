"""Top-level dialectic orchestrator.

Pipeline:
    1. Detect query CAS-content via rewrite_shim.
    2. Pick top max_rotations axis-rotations via ``select_rotations``.
    3. For each rotation: run instances A and B with axis priming, then
       integrate their predictions into a candidate ``Attractor``.
    4. Score every attractor against the query.
    5. Pick top_k by composite score.
    6. Render the load-bearing attractor's expression as English.
    7. Return a ``DialecticResponse`` with the full trace.

Run-time guarantees: this module never trains, never modifies the
predictor, and never makes network calls. It composes the existing
inference predictor and scoring helpers under a deterministic,
pure-Python orchestration layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .attractor import (
    Attractor,
    AttractorScore,
    integrate_predictions,
    score_attractor,
)
from .instance import AxisPriming, CASInstance, InstancePrediction
from .rotator import select_rotations
from .selector import select_top_attractors


# --------------------------------------------------------------------------
# Response dataclass
# --------------------------------------------------------------------------

@dataclass
class DialecticResponse:
    """Full output of a single ``DialecticOrchestrator.respond`` call.

    Fields:
        query: original input string (verbatim).
        final_expression: the chosen attractor's CAS expression.
        final_english: natural-language rendering of the chosen
            attractor's leading prediction.
        attractors_evaluated: every attractor produced by the rotation
            pass, in rotation order.
        scores: parallel list of scores for ``attractors_evaluated``.
        chosen_idx: index into ``attractors_evaluated`` of the top pick.
            -1 if no attractor was selected (no rotations or all errored).
        chosen_indices: indices of all top-K picks (may be just [chosen_idx]
            for top_k=1).
        rotation_trace: human-readable per-step trace lines.
        elapsed_ms: total wall-clock for the call.
        notes: free-form trace notes from sub-components.
    """

    query: str
    final_expression: str
    final_english: str
    attractors_evaluated: list[Attractor]
    scores: list[AttractorScore]
    chosen_idx: int
    chosen_indices: list[int]
    rotation_trace: list[str]
    elapsed_ms: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "final_expression": self.final_expression,
            "final_english": self.final_english,
            "attractors_evaluated": [a.to_dict() for a in self.attractors_evaluated],
            "scores": [s.to_dict() for s in self.scores],
            "chosen_idx": self.chosen_idx,
            "chosen_indices": list(self.chosen_indices),
            "rotation_trace": list(self.rotation_trace),
            "elapsed_ms": round(self.elapsed_ms, 3),
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

class DialecticOrchestrator:
    """Glues the predictor, rotator, and scorer into a single entry point.

    Construction:
        orch = DialecticOrchestrator(predictor)

    Usage:
        response = orch.respond("I keep practicing the same scale every day")
        print(response.final_expression)
        print(response.final_english)
        for line in response.rotation_trace:
            print(line)

    Configuration:
        max_rotations: how many rotations from ``select_rotations`` to run.
            Default 2. Each rotation costs 2 forward passes through the
            predictor, so total cost is ``2 * max_rotations`` calls.
        top_k: how many attractors to return as load-bearing. Default 1.
        instance_a_name / instance_b_name: optional logical names for
            trace readability. Defaults: "instance_A" / "instance_B".
        score_weights: optional override for AttractorScore composite
            weights. See ``attractor.DEFAULT_WEIGHTS``.

    Note: the orchestrator does not own the predictor lifecycle. The
    caller is responsible for ``load_predictor`` (one-time, expensive)
    and may share a single predictor across many orchestrators.
    """

    def __init__(
        self,
        predictor: Any,
        *,
        max_rotations: int = 2,
        top_k: int = 1,
        instance_a_name: str = "instance_A",
        instance_b_name: str = "instance_B",
        score_weights: Optional[dict[str, float]] = None,
    ) -> None:
        if predictor is None:
            raise ValueError("predictor must not be None")
        if max_rotations < 1:
            raise ValueError(f"max_rotations must be >= 1, got {max_rotations!r}")
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k!r}")
        self.predictor = predictor
        self.max_rotations = int(max_rotations)
        self.top_k = int(top_k)
        self.score_weights = dict(score_weights) if score_weights else None
        self.instance_a = CASInstance(predictor, instance_a_name)
        self.instance_b = CASInstance(predictor, instance_b_name)

    def respond(self, query: str) -> DialecticResponse:
        """Run the full rotation -> integration -> scoring -> selection pipeline."""
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query).__name__}")

        t0 = time.perf_counter()
        trace: list[str] = []
        notes: list[str] = []

        # 1. Pick rotations.
        rotations = select_rotations(query, k=self.max_rotations)
        trace.append(
            f"select_rotations: k={self.max_rotations} -> "
            f"{len(rotations)} rotations chosen"
        )
        for i, (a_p, b_p) in enumerate(rotations):
            trace.append(
                f"  rotation[{i}]: "
                f"{a_p.short_label()} vs {b_p.short_label()}"
            )

        attractors: list[Attractor] = []
        scores: list[AttractorScore] = []

        if not rotations:
            notes.append("no_rotations_selected")
            return DialecticResponse(
                query=query,
                final_expression="",
                final_english="",
                attractors_evaluated=[],
                scores=[],
                chosen_idx=-1,
                chosen_indices=[],
                rotation_trace=trace,
                elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                notes=notes,
            )

        # 2. For each rotation, run A/B and integrate.
        for i, (priming_a, priming_b) in enumerate(rotations):
            label = f"{priming_a.short_label()} vs {priming_b.short_label()}"
            try:
                pred_a = self.instance_a.predict(query, priming=priming_a)
                pred_b = self.instance_b.predict(query, priming=priming_b)
            except Exception as exc:
                trace.append(f"  [rot {i}] PREDICT_ERROR: {exc!s}")
                notes.append(f"rotation_{i}_predict_error:{exc!s}")
                continue

            attractor = integrate_predictions(
                rotation_label=label,
                a_prediction=pred_a.prediction,
                b_prediction=pred_b.prediction,
                metadata={
                    "priming_a": priming_a.to_dict(),
                    "priming_b": priming_b.to_dict(),
                    "elapsed_ms_a": pred_a.elapsed_ms,
                    "elapsed_ms_b": pred_b.elapsed_ms,
                    "notes_a": pred_a.notes,
                    "notes_b": pred_b.notes,
                },
            )
            try:
                score = score_attractor(
                    attractor, query, weights=self.score_weights
                )
            except Exception as exc:
                trace.append(f"  [rot {i}] SCORE_ERROR: {exc!s}")
                notes.append(f"rotation_{i}_score_error:{exc!s}")
                continue

            attractors.append(attractor)
            scores.append(score)
            trace.append(
                f"  [rot {i}] {label}: "
                f"kind={attractor.integration_kind} "
                f"expr={attractor.integrated_expression!r} "
                f"composite={score.composite:.3f} "
                f"(adm={score.admissibility:.2f}, "
                f"bal={score.invariant_balance:.2f}, "
                f"rel={score.relevance:.2f}, "
                f"sub={score.substance:.2f})"
            )

        if not attractors:
            notes.append("no_attractors_produced")
            return DialecticResponse(
                query=query,
                final_expression="",
                final_english="",
                attractors_evaluated=[],
                scores=[],
                chosen_idx=-1,
                chosen_indices=[],
                rotation_trace=trace,
                elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                notes=notes,
            )

        # 3. Top-K selection.
        scored_pairs = list(zip(attractors, scores))
        top = select_top_attractors(scored_pairs, k=self.top_k)
        chosen_indices: list[int] = []
        for chosen in top:
            for idx, attr in enumerate(attractors):
                if attr is chosen and idx not in chosen_indices:
                    chosen_indices.append(idx)
                    break

        chosen_idx = chosen_indices[0] if chosen_indices else -1

        if chosen_idx < 0:
            final_expression = ""
            final_english = ""
        else:
            chosen_attractor = attractors[chosen_idx]
            final_expression = chosen_attractor.integrated_expression
            final_english = self._render_english(chosen_attractor)
            trace.append(
                f"select_top: chose idx={chosen_idx} "
                f"(label={chosen_attractor.rotation_label!r})"
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return DialecticResponse(
            query=query,
            final_expression=final_expression,
            final_english=final_english,
            attractors_evaluated=attractors,
            scores=scores,
            chosen_idx=chosen_idx,
            chosen_indices=chosen_indices,
            rotation_trace=trace,
            elapsed_ms=elapsed_ms,
            notes=notes,
        )

    # ---------------------------------------------------------------- #

    def _render_english(self, attractor: Attractor) -> str:
        """Render a short English explanation for the chosen attractor.

        Strategy: render whichever of the two instance predictions is
        more "loaded" (more axes specified, or has_omega/has_meta set).
        Then prepend a one-line summary of the integration kind so the
        user knows whether they're seeing a co-presence, set-spec, or
        fallback. The two-instance integration is conveyed by the
        ``integrated_expression`` printed alongside.
        """
        try:
            from cas_native.inference.cas_renderer import render_cas_prediction
        except Exception:
            return f"[{attractor.integration_kind}] {attractor.integrated_expression}"

        # Prefer the "richer" prediction.
        a = attractor.instance_a_prediction
        b = attractor.instance_b_prediction
        scored_a = self._english_richness(a)
        scored_b = self._english_richness(b)
        chosen_pred = a if scored_a >= scored_b else b
        try:
            body = render_cas_prediction(chosen_pred)
        except Exception as exc:
            body = (
                f"[render_cas_prediction failed: {exc!s}] "
                f"raw expr: {attractor.integrated_expression}"
            )

        kind_lead = {
            "co_presence": "Co-presence reading",
            "integration": "Cross-register integration reading",
            "set_spec": "Register-set specification reading",
            "fallback": "Both instances agreed",
        }.get(attractor.integration_kind, "Reading")

        return (
            f"{kind_lead} ({attractor.rotation_label}): "
            f"{attractor.integrated_expression}. {body}"
        )

    @staticmethod
    def _english_richness(prediction: dict[str, Any]) -> int:
        """Cheap "which prediction is richer" heuristic."""
        score = 0
        if prediction.get("noetic") is not None:
            score += 1
        if prediction.get("domain"):
            score += 1
        if prediction.get("drive"):
            score += 1
        if prediction.get("registers"):
            score += 1 + len(prediction.get("registers") or ())
        if prediction.get("has_omega"):
            score += 2
        if prediction.get("has_meta_logic"):
            score += 1
        if prediction.get("meta_relations"):
            score += len(prediction.get("meta_relations") or ())
        return score


__all__ = [
    "DialecticOrchestrator",
    "DialecticResponse",
]
