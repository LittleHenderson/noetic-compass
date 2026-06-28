"""Shape 2 verify-and-rerank service records.

Shape 2 records are the bridge between the near-term verification service and
the CAS Transformer corpus. Each accepted transition is stored with the prompt,
pre-state, candidate set, validation artifact, rendered response, recovered
trace, recovery-fidelity score, perturbations, and provenance.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from cas_synthetic.schemas.cas_transformer import (
    CASPerturbationExample,
    CASTrace,
    CASTraceEdge,
    CASTraceNode,
    CASTurnRecord,
    ValidationDiagnostic,
    validate_compound_transition,
)
from cas_synthetic.schemas.diagram_graph import diagram_summary
from cas_synthetic.validation.cas_transformer_recovery import (
    RecoveryFidelityResult,
    RecoveryFidelityScorer,
)


SHAPE2_SCHEMA_VERSION = "shape2_transition_record_v0"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_compile_expression():
    """Return the CAS notation compiler when this repo is checked out locally."""

    try:
        module = importlib.import_module("api.notation")
    except ImportError:
        noetic_root = _repo_root() / "noetic-compass-scaffold" / "noetic-compass"
        if noetic_root.exists() and str(noetic_root) not in sys.path:
            sys.path.insert(0, str(noetic_root))
        try:
            module = importlib.import_module("api.notation")
        except ImportError:
            return None
    compile_expression = getattr(module, "compile_expression", None)
    return compile_expression if callable(compile_expression) else None


def _unavailable_diagram(reason: str) -> dict[str, Any]:
    return {
        "kind": "cas_diagram",
        "schema_version": "1.0",
        "available": False,
        "reason": reason,
        "layouts": [],
        "nodes": [],
        "edges": [],
        "containers": [],
    }


def _compile_diagram(expression: str) -> dict[str, Any]:
    """Project an accepted CAS expression into the compiler graph schema."""

    compile_expression = _load_compile_expression()
    if compile_expression is None:
        return _unavailable_diagram("compiler_unavailable")
    try:
        artifact = compile_expression(expression)
    except Exception as exc:  # pragma: no cover - defensive integration guard
        return _unavailable_diagram(f"compiler_error: {exc}")
    if not getattr(artifact, "valid", False):
        return _unavailable_diagram(
            f"compiler_invalid: {getattr(artifact, 'error', 'unknown error')}"
        )
    diagram = artifact.diagram()
    if not isinstance(diagram, dict):
        return _unavailable_diagram("diagram_unavailable")
    result = dict(diagram)
    result["available"] = True
    result["source"] = "api.notation.compiler.diagram"
    return result


@dataclass(frozen=True)
class Shape2Candidate:
    """One candidate transition/trace considered by Shape 2."""

    candidate_id: str
    trace: list[CASTraceNode]
    trace_edges: list[CASTraceEdge] = field(default_factory=list)
    rendered_response: str = ""
    score: float | None = None
    validation_artifact: dict[str, Any] = field(default_factory=dict)
    accepted: bool = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "trace": [node.to_dict() for node in self.trace],
            "trace_edges": [edge.to_dict() for edge in self.trace_edges],
            "rendered_response": self.rendered_response,
            "validation_artifact": dict(self.validation_artifact),
            "accepted": self.accepted,
        }
        if self.score is not None:
            result["score"] = self.score
        return result

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.candidate_id:
            errors.append("candidate missing candidate_id")
        if not self.trace:
            errors.append(f"{self.candidate_id}: candidate must include trace nodes")
        trace_errors = CASTrace(self.trace, self.trace_edges).validate()
        errors.extend(f"{self.candidate_id}: {error}" for error in trace_errors)
        if not self.rendered_response:
            errors.append(f"{self.candidate_id}: candidate missing rendered_response")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            errors.append(f"{self.candidate_id}: score must be in [0, 1]")
        return errors


@dataclass(frozen=True)
class Shape2Record:
    """JSONL-ready Shape 2 transition capture record."""

    id: str
    prompt: str
    pre_state: dict[str, Any]
    candidates: list[Shape2Candidate]
    accepted_candidate_id: str
    accepted_transition: dict[str, Any]
    validation_artifact: dict[str, Any]
    rendered_response: str
    recovered_trace: dict[str, Any]
    rf_score: float
    perturbations: list[CASPerturbationExample] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SHAPE2_SCHEMA_VERSION,
            "id": self.id,
            "prompt": self.prompt,
            "pre_state": dict(self.pre_state),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "accepted_candidate_id": self.accepted_candidate_id,
            "accepted_transition": dict(self.accepted_transition),
            "validation_artifact": dict(self.validation_artifact),
            "rendered_response": self.rendered_response,
            "recovered_trace": dict(self.recovered_trace),
            "rf_score": self.rf_score,
            "perturbations": [item.to_dict() for item in self.perturbations],
            "provenance": dict(self.provenance),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id:
            errors.append("record missing id")
        if not self.prompt:
            errors.append(f"{self.id}: missing prompt")
        if not self.pre_state:
            errors.append(f"{self.id}: missing pre_state")
        if not self.candidates:
            errors.append(f"{self.id}: missing candidates")
        candidate_ids = {candidate.candidate_id for candidate in self.candidates}
        if self.accepted_candidate_id not in candidate_ids:
            errors.append(
                f"{self.id}: accepted_candidate_id {self.accepted_candidate_id!r} "
                "is not present in candidates"
            )
        accepted_count = sum(1 for candidate in self.candidates if candidate.accepted)
        if accepted_count != 1:
            errors.append(f"{self.id}: exactly one candidate must be accepted")
        for candidate in self.candidates:
            errors.extend(f"{self.id}: {error}" for error in candidate.validate())
        if not self.accepted_transition:
            errors.append(f"{self.id}: missing accepted_transition")
        if not self.validation_artifact:
            errors.append(f"{self.id}: missing validation_artifact")
        if not self.rendered_response:
            errors.append(f"{self.id}: missing rendered_response")
        if not self.recovered_trace:
            errors.append(f"{self.id}: missing recovered_trace")
        if not 0.0 <= self.rf_score <= 1.0:
            errors.append(f"{self.id}: rf_score must be in [0, 1]")
        if not self.perturbations:
            errors.append(f"{self.id}: missing perturbations")
        for perturbation in self.perturbations:
            errors.extend(
                f"{self.id}: {error}" for error in perturbation.validate()
            )
        return errors


class Shape2RecordWriter:
    """Append-only JSONL writer for Shape 2 transition records."""

    def __init__(
        self,
        output_path: str | Path,
        *,
        scorer: RecoveryFidelityScorer | None = None,
    ) -> None:
        self.output_path = Path(output_path)
        self.scorer = scorer or RecoveryFidelityScorer()

    def from_turn_record(
        self,
        record: CASTurnRecord,
        *,
        candidates: list[Shape2Candidate] | None = None,
        record_id: str | None = None,
    ) -> Shape2Record:
        """Build a Shape 2 record from an accepted CAS-turn record."""

        turn_errors = record.validate()
        recovery = self.scorer.score_record(record)
        accepted_id = f"{record.id}:accepted"
        accepted_candidate = Shape2Candidate(
            candidate_id=accepted_id,
            trace=list(record.trace),
            trace_edges=list(record.trace_edges),
            rendered_response=record.response,
            score=recovery.score,
            validation_artifact=_validation_artifact(record, recovery, turn_errors),
            accepted=True,
        )
        all_candidates = list(candidates or [])
        if not all_candidates:
            all_candidates.append(accepted_candidate)
        elif not any(candidate.accepted for candidate in all_candidates):
            all_candidates.insert(0, accepted_candidate)
        else:
            accepted = [candidate for candidate in all_candidates if candidate.accepted]
            accepted_id = accepted[0].candidate_id

        result = Shape2Record(
            id=record_id or f"shape2:{record.id}",
            prompt=record.prompt,
            pre_state=_pre_state(record),
            candidates=all_candidates,
            accepted_candidate_id=accepted_id,
            accepted_transition=_accepted_transition(record),
            validation_artifact=_validation_artifact(record, recovery, turn_errors),
            rendered_response=record.response,
            recovered_trace=recovery.to_dict(),
            rf_score=recovery.score,
            perturbations=list(record.perturbations),
            provenance={
                "source_record_id": record.id,
                "source_schema": "CASTurnRecord",
                "shape2_schema_version": SHAPE2_SCHEMA_VERSION,
                **dict(record.provenance),
            },
        )
        errors = result.validate()
        if errors:
            raise ValueError(f"{result.id} failed Shape 2 validation: {errors}")
        return result

    def write_record(self, record: Shape2Record) -> None:
        errors = record.validate()
        if errors:
            raise ValueError(f"{record.id} failed Shape 2 validation: {errors}")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def write_from_turn(self, record: CASTurnRecord) -> Shape2Record:
        shape2_record = self.from_turn_record(record)
        self.write_record(shape2_record)
        return shape2_record

    def write_many_from_turns(self, records: Iterable[CASTurnRecord]) -> list[Shape2Record]:
        written: list[Shape2Record] = []
        for record in records:
            written.append(self.write_from_turn(record))
        return written


def _pre_state(record: CASTurnRecord) -> dict[str, Any]:
    first = record.trace[0] if record.trace else None
    return {
        "facts": first.state_context.to_dict()["facts"] if first else [],
        "meta_logic_context": record.meta_logic_context.to_dict(),
        "trace_node_count": len(record.trace),
    }


def _accepted_transition(record: CASTurnRecord) -> dict[str, Any]:
    diagram = _compile_diagram(record.cas_expression)
    return {
        "trace": [node.to_dict() for node in record.trace],
        "trace_edges": [edge.to_dict() for edge in record.trace_edges],
        "cas_expression": record.cas_expression,
        "diagram": diagram,
        "diagram_summary": diagram_summary(diagram),
    }


def _validation_artifact(
    record: CASTurnRecord,
    recovery: RecoveryFidelityResult,
    turn_errors: list[str],
) -> dict[str, Any]:
    diagnostics = validate_compound_transition(
        CASTrace(list(record.trace), list(record.trace_edges))
    )
    return {
        "compiler": dict(record.compiler),
        "record_valid": not turn_errors,
        "record_errors": list(turn_errors),
        "compound_diagnostics": [
            _diagnostic_to_dict(diagnostic) for diagnostic in diagnostics
        ],
        "recovery": recovery.to_dict(),
    }


def _diagnostic_to_dict(diagnostic: ValidationDiagnostic) -> dict[str, Any]:
    return diagnostic.to_dict()
