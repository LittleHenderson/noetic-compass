"""Traceable CAS-native turn execution.

This module bridges ``IntentIR`` and ``CASRuntimeFrame``. It does not make the
compiler smarter; it records the full runtime path for one cognitive turn:
pre-frame, recovered intent, admissible candidates, salience ranking, selected
transition, post-frame, and typed delta.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from cas_native.intent import IntentIR, build_candidate_expressions
from cas_native.runtime.runtime_frame import (
    CASRuntimeFrame,
    DriveLevel,
    DriveState,
    FeedbackEvent,
    FeedbackHistory,
    SalienceResult,
    TransitionTraceRecord,
)


@dataclass(frozen=True)
class CandidateTransition:
    """One compiler/admissibility candidate for a recovered intent."""

    expression: str
    compiler_validation: dict[str, Any] | None = None
    diagram_summary: dict[str, Any] | None = None
    admissible: bool = True
    candidate_weight: float = 1.0
    source: str = "builder"

    @property
    def is_admissible(self) -> bool:
        validation = self.compiler_validation or {}
        if validation.get("valid") is False:
            return False
        if validation.get("compiler_valid") is False:
            return False
        return self.admissible

    def to_dict(self) -> dict[str, Any]:
        return {
            "expression": self.expression,
            "compiler_validation": self.compiler_validation or {},
            "diagram_summary": self.diagram_summary or {},
            "admissible": self.admissible,
            "is_admissible": self.is_admissible,
            "candidate_weight": self.candidate_weight,
            "source": self.source,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.expression:
            errors.append("candidate transition requires expression")
        if self.candidate_weight < 0:
            errors.append("candidate_weight must be >= 0")
        return errors


@dataclass(frozen=True)
class CandidateSalience:
    """Ranked salience score for one admissible candidate."""

    candidate: CandidateTransition
    salience: SalienceResult
    total_score: float
    rank: int
    selected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "salience": self.salience.to_dict(),
            "total_score": self.total_score,
            "rank": self.rank,
            "selected": self.selected,
        }


@dataclass(frozen=True)
class RuntimeDelta:
    """Typed diff between runtime frame snapshots."""

    identity_persisted: bool
    drive_deltas: dict[str, dict[str, float]]
    facts_added: tuple[str, ...] = ()
    facts_removed: tuple[str, ...] = ()
    feedback_added: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_persisted": self.identity_persisted,
            "drive_deltas": self.drive_deltas,
            "facts_added": list(self.facts_added),
            "facts_removed": list(self.facts_removed),
            "feedback_added": list(self.feedback_added),
            "changed_paths": list(self.changed_paths),
        }


@dataclass(frozen=True)
class TurnExecutionRecord:
    """Full operational record for one CAS-native turn."""

    user_input: str
    predicted_intent_ir: IntentIR
    runtime_frame_pre: CASRuntimeFrame
    admissible_candidates: tuple[CandidateSalience, ...]
    selected_expression: str
    compiler_validation: dict[str, Any]
    diagram_summary: dict[str, Any]
    rendered_response: str
    runtime_frame_post: CASRuntimeFrame
    runtime_delta: RuntimeDelta
    transition_trace: TransitionTraceRecord
    schema_version: str = "turn_execution.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "user_input": self.user_input,
            "runtime_frame_pre": self.runtime_frame_pre.to_dict(),
            "predicted_intent_ir": self.predicted_intent_ir.to_dict(),
            "admissible_candidates": [
                candidate.to_dict() for candidate in self.admissible_candidates
            ],
            "selected_expression": self.selected_expression,
            "compiler_validation": self.compiler_validation,
            "diagram_summary": self.diagram_summary,
            "rendered_response": self.rendered_response,
            "runtime_frame_post": self.runtime_frame_post.to_dict(),
            "runtime_delta": self.runtime_delta.to_dict(),
            "transition_trace": self.transition_trace.to_dict(),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.user_input:
            errors.append("turn execution requires user_input")
        if not self.selected_expression:
            errors.append("turn execution requires selected_expression")
        if not self.admissible_candidates:
            errors.append("turn execution requires at least one admissible candidate")
        if not any(candidate.selected for candidate in self.admissible_candidates):
            errors.append("turn execution requires exactly one selected candidate")
        if sum(1 for candidate in self.admissible_candidates if candidate.selected) > 1:
            errors.append("turn execution requires exactly one selected candidate")
        errors.extend(self.predicted_intent_ir.validate())
        errors.extend(self.runtime_frame_pre.validate())
        errors.extend(self.runtime_frame_post.validate())
        errors.extend(self.transition_trace.validate())
        return errors


CandidateInput = str | CandidateTransition


def execute_turn(
    *,
    runtime_frame: CASRuntimeFrame,
    intent: IntentIR,
    user_input: str | None = None,
    candidates: Iterable[CandidateInput] | None = None,
    rendered_response: str = "",
    feedback_event: FeedbackEvent | None = None,
    drive_depletion_step: float = 0.02,
) -> TurnExecutionRecord:
    """Execute one traceable CAS-native turn.

    ``execute_turn`` assumes candidate expressions have already been compiled
    or will be compiled by a caller later. Candidate records can still carry
    validation artifacts; candidates marked invalid are excluded before
    salience ranking.
    """

    normalized = _normalize_candidates(candidates, intent)
    validation_errors = [error for candidate in normalized for error in candidate.validate()]
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    ranked = _rank_candidates(runtime_frame, intent, normalized)
    if not ranked:
        raise ValueError("no admissible candidates available for turn execution")

    selected = ranked[0]
    selected_candidate = selected.candidate
    post_frame = evolve_runtime_frame(
        runtime_frame,
        intent,
        feedback_event=feedback_event,
        drive_depletion_step=drive_depletion_step,
    )
    delta = diff_runtime_frames(runtime_frame, post_frame)
    trace = runtime_frame.trace_transition(
        intent,
        selected_candidate.expression,
        validation=selected_candidate.compiler_validation or {},
        diagram_summary=selected_candidate.diagram_summary or {},
    )

    return TurnExecutionRecord(
        user_input=user_input if user_input is not None else intent.model_input_text(),
        predicted_intent_ir=intent,
        runtime_frame_pre=runtime_frame,
        admissible_candidates=tuple(
            replace(candidate, selected=(candidate.rank == selected.rank))
            for candidate in ranked
        ),
        selected_expression=selected_candidate.expression,
        compiler_validation=selected_candidate.compiler_validation or {},
        diagram_summary=selected_candidate.diagram_summary or {},
        rendered_response=rendered_response,
        runtime_frame_post=post_frame,
        runtime_delta=delta,
        transition_trace=trace,
    )


def evolve_runtime_frame(
    frame: CASRuntimeFrame,
    intent: IntentIR,
    *,
    feedback_event: FeedbackEvent | None = None,
    drive_depletion_step: float = 0.02,
) -> CASRuntimeFrame:
    """Return the post-turn runtime frame after applying minimal dynamics."""

    selected_drive = intent.axis.drive
    drive_state = _deplete_drive(frame.drive_state, selected_drive, drive_depletion_step)
    feedback_history = frame.feedback_history
    if feedback_event is not None:
        feedback_history = FeedbackHistory(events=frame.feedback_history.events + (feedback_event,))
    facts = tuple(
        dict.fromkeys(
            frame.facts
            + (
                f"last_turn:{intent.transition_kind}",
                f"last_family:{intent.expression_family}",
            )
        )
    )
    return replace(
        frame,
        drive_state=drive_state,
        feedback_history=feedback_history,
        facts=facts,
    )


def diff_runtime_frames(pre: CASRuntimeFrame, post: CASRuntimeFrame) -> RuntimeDelta:
    """Build a typed, queryable diff between two runtime snapshots."""

    drive_deltas: dict[str, dict[str, float]] = {}
    pre_levels = {level.drive: level for level in pre.drive_state.levels}
    post_levels = {level.drive: level for level in post.drive_state.levels}
    for drive in sorted(set(pre_levels) | set(post_levels)):
        before = pre_levels.get(drive)
        after = post_levels.get(drive)
        if before is None or after is None:
            continue
        delta = {
            "activation": after.activation - before.activation,
            "depletion": after.depletion - before.depletion,
            "saturation": after.saturation - before.saturation,
            "priority": after.priority - before.priority,
            "effective_weight": after.effective_weight() - before.effective_weight(),
        }
        if any(value != 0 for value in delta.values()):
            drive_deltas[drive] = delta

    pre_facts = set(pre.facts)
    post_facts = set(post.facts)
    pre_feedback = {event.event_id for event in pre.feedback_history.events}
    post_feedback = {event.event_id for event in post.feedback_history.events}
    changed_paths: list[str] = []
    if drive_deltas:
        changed_paths.append("drive_state")
    if pre_facts != post_facts:
        changed_paths.append("facts")
    if pre_feedback != post_feedback:
        changed_paths.append("feedback_history")
    if pre.identity.continuity_key != post.identity.continuity_key:
        changed_paths.append("identity")

    return RuntimeDelta(
        identity_persisted=pre.identity.continuity_key == post.identity.continuity_key,
        drive_deltas=drive_deltas,
        facts_added=tuple(sorted(post_facts - pre_facts)),
        facts_removed=tuple(sorted(pre_facts - post_facts)),
        feedback_added=tuple(sorted(post_feedback - pre_feedback)),
        changed_paths=tuple(changed_paths),
    )


def _normalize_candidates(
    candidates: Iterable[CandidateInput] | None,
    intent: IntentIR,
) -> list[CandidateTransition]:
    raw_candidates = list(candidates) if candidates is not None else build_candidate_expressions(intent)
    normalized: list[CandidateTransition] = []
    for candidate in raw_candidates:
        if isinstance(candidate, CandidateTransition):
            normalized.append(candidate)
        else:
            normalized.append(CandidateTransition(expression=str(candidate)))
    return normalized


def _rank_candidates(
    frame: CASRuntimeFrame,
    intent: IntentIR,
    candidates: list[CandidateTransition],
) -> list[CandidateSalience]:
    base = frame.score_intent(intent)
    scored: list[tuple[float, CandidateTransition]] = []
    for candidate in candidates:
        if candidate.is_admissible:
            scored.append((base.score * candidate.candidate_weight, candidate))
    scored.sort(key=lambda item: (-item[0], item[1].expression))
    return tuple(
        CandidateSalience(
            candidate=candidate,
            salience=base,
            total_score=score,
            rank=index + 1,
        )
        for index, (score, candidate) in enumerate(scored)
    )


def _deplete_drive(
    drive_state: DriveState,
    selected_drive: str | None,
    step: float,
) -> DriveState:
    if selected_drive is None or step <= 0:
        return drive_state
    updated: list[DriveLevel] = []
    changed = False
    for level in drive_state.levels:
        if level.drive == selected_drive:
            updated.append(
                replace(level, depletion=min(1.0, level.depletion + step))
            )
            changed = True
        else:
            updated.append(level)
    if not changed:
        return drive_state
    return replace(drive_state, levels=tuple(updated))
