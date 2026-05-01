"""Runtime frame for CAS-native transition firing.

IntentIR recovers the formal structure implied by user input. CASRuntimeFrame
adds the missing runtime layer: continuity, drive dynamics, salience, temporal
grain, affect, ambiguity, feedback, and resting-state distribution. This is the
typed state that lets a CAS-native agent explain why one admissible transition
fired instead of another.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cas_native.intent.intent_ir import (
    DOMAINS,
    DRIVES,
    REGISTERS,
    AmbiguityOption,
    IntentIR,
)


TEMPORAL_GRAINS: tuple[str, ...] = (
    "reflex",
    "perceptual",
    "simple_reasoning",
    "deliberation",
    "strategy",
)
AFFECT_TYPES: tuple[str, ...] = (
    "neutral",
    "anger",
    "grief",
    "joy",
    "contentment",
    "shame",
    "awe",
    "fear",
    "curiosity",
    "care",
)
AMBIGUITY_POLICIES: tuple[str, ...] = (
    "hold_until_context",
    "clarify_now",
    "resolve_by_salience",
)


@dataclass(frozen=True)
class IdentityState:
    """Continuity anchor for a running CAS-native agent."""

    agent_id: str
    continuity_key: str
    session_id: str | None = None
    persistent_tags: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "continuity_key": self.continuity_key,
            "session_id": self.session_id,
            "persistent_tags": list(self.persistent_tags),
            "memory_refs": list(self.memory_refs),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.agent_id:
            errors.append("identity_state requires agent_id")
        if not self.continuity_key:
            errors.append("identity_state requires continuity_key")
        return errors


@dataclass(frozen=True)
class DriveLevel:
    """Dynamic level for one F1-F7 drive."""

    drive: str
    activation: float = 0.5
    depletion: float = 0.0
    saturation: float = 0.0
    priority: float = 1.0

    def effective_weight(self) -> float:
        return self.activation * self.priority * (1.0 - self.depletion) * (1.0 - self.saturation)

    def to_dict(self) -> dict[str, float | str]:
        return {
            "drive": self.drive,
            "activation": self.activation,
            "depletion": self.depletion,
            "saturation": self.saturation,
            "priority": self.priority,
            "effective_weight": self.effective_weight(),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.drive not in DRIVES:
            errors.append(f"unknown drive {self.drive!r}")
        for field_name in ("activation", "depletion", "saturation"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                errors.append(f"{self.drive}.{field_name} must be within [0, 1]")
        if self.priority < 0:
            errors.append(f"{self.drive}.priority must be >= 0")
        return errors


@dataclass(frozen=True)
class DriveState:
    """Runtime drive profile with depletion, saturation, and competition hooks."""

    levels: tuple[DriveLevel, ...] = field(
        default_factory=lambda: tuple(DriveLevel(drive=drive) for drive in DRIVES)
    )
    competition: dict[tuple[str, str], float] = field(default_factory=dict)

    def level_for(self, drive: str | None) -> DriveLevel | None:
        if drive is None:
            return None
        for level in self.levels:
            if level.drive == drive:
                return level
        return None

    def effective_weight(self, drive: str | None) -> float:
        level = self.level_for(drive)
        return level.effective_weight() if level is not None else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "levels": [level.to_dict() for level in self.levels],
            "competition": [
                {"source": source, "target": target, "weight": weight}
                for (source, target), weight in sorted(self.competition.items())
            ],
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        for level in self.levels:
            if level.drive in seen:
                errors.append(f"duplicate drive level {level.drive!r}")
            seen.add(level.drive)
            errors.extend(level.validate())
        for (source, target), weight in self.competition.items():
            if source not in DRIVES or target not in DRIVES:
                errors.append(f"drive competition has unknown edge {source!r}->{target!r}")
            if weight < 0:
                errors.append(f"drive competition {source}->{target} must be >= 0")
        return errors


@dataclass(frozen=True)
class TemporalGrain:
    """Characteristic time scale for a transition."""

    name: str = "simple_reasoning"
    min_ms: int = 500
    max_ms: int = 5000

    def to_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.name not in TEMPORAL_GRAINS:
            errors.append(f"unknown temporal grain {self.name!r}")
        if self.min_ms < 0:
            errors.append("temporal grain min_ms must be >= 0")
        if self.max_ms < self.min_ms:
            errors.append("temporal grain max_ms must be >= min_ms")
        return errors


@dataclass(frozen=True)
class AffectState:
    """Specific affect state, separate from register mode."""

    affect_type: str = "neutral"
    valence: float = 0.0
    arousal: float = 0.0
    register_bias: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "affect_type": self.affect_type,
            "valence": self.valence,
            "arousal": self.arousal,
            "register_bias": self.register_bias,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.affect_type not in AFFECT_TYPES:
            errors.append(f"unknown affect_type {self.affect_type!r}")
        if not -1.0 <= self.valence <= 1.0:
            errors.append("affect valence must be within [-1, 1]")
        if not 0.0 <= self.arousal <= 1.0:
            errors.append("affect arousal must be within [0, 1]")
        if self.register_bias is not None and self.register_bias not in REGISTERS:
            errors.append(f"unknown affect register_bias {self.register_bias!r}")
        return errors


@dataclass(frozen=True)
class AmbiguityState:
    """Held superposition of unresolved interpretations."""

    options: tuple[AmbiguityOption, ...] = ()
    policy: str = "hold_until_context"
    clarification_threshold: float = 0.75

    def should_clarify(self) -> bool:
        if self.policy == "clarify_now":
            return bool(self.options)
        if not self.options:
            return False
        unresolved = [
            1.0 - option.confidence
            for option in self.options
            if option.confidence is not None
        ]
        return bool(unresolved) and max(unresolved) >= self.clarification_threshold

    def penalty(self) -> float:
        return max(0.5, 1.0 - 0.05 * len(self.options))

    def to_dict(self) -> dict[str, Any]:
        return {
            "options": [option.to_dict() for option in self.options],
            "policy": self.policy,
            "clarification_threshold": self.clarification_threshold,
            "should_clarify": self.should_clarify(),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.policy not in AMBIGUITY_POLICIES:
            errors.append(f"unknown ambiguity policy {self.policy!r}")
        if not 0.0 <= self.clarification_threshold <= 1.0:
            errors.append("clarification_threshold must be within [0, 1]")
        for option in self.options:
            errors.extend(option.validate())
        return errors


@dataclass(frozen=True)
class FeedbackEvent:
    """Observation after a prior CAS action."""

    event_id: str
    action_id: str
    observation: str
    outcome: str
    reward_signal: float = 0.0
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action_id": self.action_id,
            "observation": self.observation,
            "outcome": self.outcome,
            "reward_signal": self.reward_signal,
            "confidence": self.confidence,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.event_id:
            errors.append("feedback event requires event_id")
        if not self.action_id:
            errors.append("feedback event requires action_id")
        if not self.observation:
            errors.append("feedback event requires observation")
        if not self.outcome:
            errors.append("feedback event requires outcome")
        if not -1.0 <= self.reward_signal <= 1.0:
            errors.append("feedback reward_signal must be within [-1, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append("feedback confidence must be within [0, 1]")
        return errors


@dataclass(frozen=True)
class FeedbackHistory:
    """Prior action-perception feedback events."""

    events: tuple[FeedbackEvent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"events": [event.to_dict() for event in self.events]}

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        for event in self.events:
            if event.event_id in seen:
                errors.append(f"duplicate feedback event {event.event_id!r}")
            seen.add(event.event_id)
            errors.extend(event.validate())
        return errors


@dataclass(frozen=True)
class DefaultStateDistribution:
    """Resting distribution over CAS state literals."""

    weights: dict[str, float] = field(default_factory=dict)

    def normalized(self) -> dict[str, float]:
        total = sum(max(0.0, value) for value in self.weights.values())
        if total <= 0:
            return {}
        return {state: max(0.0, value) / total for state, value in self.weights.items()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": dict(self.weights),
            "normalized": self.normalized(),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        for state, weight in self.weights.items():
            if not state:
                errors.append("default state distribution has empty state key")
            if weight < 0:
                errors.append(f"{state}: default state weight must be >= 0")
        return errors


@dataclass(frozen=True)
class SaliencePolicy:
    """Typed firing rule for admissible transitions."""

    base_weight: float = 1.0
    family_weights: dict[str, float] = field(default_factory=dict)
    transition_weights: dict[str, float] = field(default_factory=dict)
    domain_weights: dict[str, float] = field(default_factory=dict)
    drive_weights: dict[str, float] = field(default_factory=dict)
    register_weights: dict[str, float] = field(default_factory=dict)
    affect_register_gain: float = 0.25
    ambiguity_penalty_enabled: bool = True

    def score(self, intent: IntentIR, frame: CASRuntimeFrame) -> SalienceResult:
        drive = intent.axis.drive
        register = intent.axis.register or _first_register(intent)
        components: dict[str, float] = {
            "base": self.base_weight,
            "family": self.family_weights.get(intent.expression_family, 1.0),
            "transition": self.transition_weights.get(intent.transition_kind, 1.0),
            "domain": self.domain_weights.get(intent.axis.domain or "", 1.0),
            "drive_policy": self.drive_weights.get(drive or "", 1.0),
            "drive_runtime": frame.drive_state.effective_weight(drive),
            "register": self.register_weights.get(register or "", 1.0),
            "affect": _affect_multiplier(frame.affect_state, register, self.affect_register_gain),
            "ambiguity": frame.ambiguity_state.penalty() if self.ambiguity_penalty_enabled else 1.0,
        }
        total = 1.0
        for value in components.values():
            total *= value
        return SalienceResult(
            intent_id=intent.id,
            score=total,
            components=components,
            selected_drive=drive,
            selected_register=register,
            temporal_grain=frame.temporal_grain.name,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_weight": self.base_weight,
            "family_weights": dict(self.family_weights),
            "transition_weights": dict(self.transition_weights),
            "domain_weights": dict(self.domain_weights),
            "drive_weights": dict(self.drive_weights),
            "register_weights": dict(self.register_weights),
            "affect_register_gain": self.affect_register_gain,
            "ambiguity_penalty_enabled": self.ambiguity_penalty_enabled,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.base_weight < 0:
            errors.append("salience base_weight must be >= 0")
        for name, weights in (
            ("domain", self.domain_weights),
            ("drive", self.drive_weights),
            ("register", self.register_weights),
        ):
            for key, value in weights.items():
                if value < 0:
                    errors.append(f"{name} salience weight {key!r} must be >= 0")
        unknown_domains = sorted(key for key in self.domain_weights if key not in DOMAINS)
        unknown_drives = sorted(key for key in self.drive_weights if key not in DRIVES)
        unknown_registers = sorted(key for key in self.register_weights if key not in REGISTERS)
        if unknown_domains:
            errors.append(f"salience has unknown domain weight(s) {unknown_domains}")
        if unknown_drives:
            errors.append(f"salience has unknown drive weight(s) {unknown_drives}")
        if unknown_registers:
            errors.append(f"salience has unknown register weight(s) {unknown_registers}")
        if self.affect_register_gain < 0:
            errors.append("affect_register_gain must be >= 0")
        return errors


@dataclass(frozen=True)
class SalienceResult:
    """Traceable score for why an intent fired."""

    intent_id: str
    score: float
    components: dict[str, float]
    selected_drive: str | None = None
    selected_register: str | None = None
    temporal_grain: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "score": self.score,
            "components": dict(self.components),
            "selected_drive": self.selected_drive,
            "selected_register": self.selected_register,
            "temporal_grain": self.temporal_grain,
        }


@dataclass(frozen=True)
class TransitionTraceRecord:
    """Runtime trace for one accepted candidate transition."""

    intent_id: str
    candidate_expression: str
    identity: IdentityState
    salience: SalienceResult
    temporal_grain: TemporalGrain
    validation: dict[str, Any] = field(default_factory=dict)
    diagram_summary: dict[str, Any] = field(default_factory=dict)
    feedback_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "candidate_expression": self.candidate_expression,
            "identity": self.identity.to_dict(),
            "salience": self.salience.to_dict(),
            "temporal_grain": self.temporal_grain.to_dict(),
            "validation": self.validation,
            "diagram_summary": self.diagram_summary,
            "feedback_refs": list(self.feedback_refs),
        }

    def validate(self) -> list[str]:
        errors = self.identity.validate()
        if not self.intent_id:
            errors.append("transition trace requires intent_id")
        if not self.candidate_expression:
            errors.append("transition trace requires candidate_expression")
        errors.extend(self.temporal_grain.validate())
        return errors


@dataclass(frozen=True)
class CASRuntimeFrame:
    """Complete runtime frame used to fire and audit CAS transitions."""

    identity: IdentityState
    drive_state: DriveState = field(default_factory=DriveState)
    salience_policy: SaliencePolicy = field(default_factory=SaliencePolicy)
    temporal_grain: TemporalGrain = field(default_factory=TemporalGrain)
    affect_state: AffectState = field(default_factory=AffectState)
    ambiguity_state: AmbiguityState = field(default_factory=AmbiguityState)
    feedback_history: FeedbackHistory = field(default_factory=FeedbackHistory)
    default_state_distribution: DefaultStateDistribution = field(
        default_factory=DefaultStateDistribution
    )
    facts: tuple[str, ...] = ()
    schema_version: str = "cas_runtime_frame.v1"

    def score_intent(self, intent: IntentIR) -> SalienceResult:
        return self.salience_policy.score(intent, self)

    def trace_transition(
        self,
        intent: IntentIR,
        candidate_expression: str,
        *,
        validation: dict[str, Any] | None = None,
        diagram_summary: dict[str, Any] | None = None,
    ) -> TransitionTraceRecord:
        return TransitionTraceRecord(
            intent_id=intent.id,
            candidate_expression=candidate_expression,
            identity=self.identity,
            salience=self.score_intent(intent),
            temporal_grain=self.temporal_grain,
            validation=validation or {},
            diagram_summary=diagram_summary or {},
            feedback_refs=tuple(event.event_id for event in self.feedback_history.events),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "drive_state": self.drive_state.to_dict(),
            "salience_policy": self.salience_policy.to_dict(),
            "temporal_grain": self.temporal_grain.to_dict(),
            "affect_state": self.affect_state.to_dict(),
            "ambiguity_state": self.ambiguity_state.to_dict(),
            "feedback_history": self.feedback_history.to_dict(),
            "default_state_distribution": self.default_state_distribution.to_dict(),
            "facts": list(self.facts),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        errors.extend(self.identity.validate())
        errors.extend(self.drive_state.validate())
        errors.extend(self.salience_policy.validate())
        errors.extend(self.temporal_grain.validate())
        errors.extend(self.affect_state.validate())
        errors.extend(self.ambiguity_state.validate())
        errors.extend(self.feedback_history.validate())
        errors.extend(self.default_state_distribution.validate())
        return errors


def _first_register(intent: IntentIR) -> str | None:
    if intent.register_intent.registers:
        return intent.register_intent.registers[0]
    return None


def _affect_multiplier(
    affect: AffectState,
    register: str | None,
    gain: float,
) -> float:
    if affect.register_bias is None or register != affect.register_bias:
        return 1.0
    return 1.0 + gain * affect.arousal
