"""Deterministic controlled-English facade for the bounded CNCM kernel.

This module is intentionally not a general natural-language interface.  It
accepts only four explicit forms::

    Alice is human.
    Alice is not human.
    Every human is mortal.
    Is Alice mortal?

The subject of a fact or question may be ``he``, ``she``, ``they``, or ``it``
only when the bounded dialogue focus contains exactly one entity.  Otherwise
the caller receives a typed clarification request and may answer with
``I mean Alice.``.

Assertions are dialogue data, not kernel conclusions.  A question is compiled
into the frozen ``ProblemPacket`` contract and executed by a fresh
``CognitiveMachine``.  The fresh machine prevents hidden episodic carry-over:
only facts and rules explicitly retained in ``DialogueState`` enter the
packet.  A conversational answer is rendered only after evidence verification,
an exact committed-query check, and a matching execution of that same compiled
packet on a second fresh machine.  This execution-parity receipt checks
deterministic runtime behavior; it does not prove that the language parse is
semantically correct.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from hashlib import sha256
import re
from typing import Any, Mapping

from .api import verify_evidence
from .canonical import digest
from .engine import CognitiveMachine, RunResult
from .model import ProblemPacket, TerminalStatus


_TOKEN = r"[A-Za-z][A-Za-z0-9_-]*"
_PRONOUNS = frozenset({"he", "she", "they", "it"})
_MAX_INPUT_CHARACTERS = 512
_MAX_ENTITIES = 64
_MAX_FACTS = 128
_MAX_RULES = 128


class TurnStatus(str, Enum):
    """Typed conversational outcome; it does not grant action authority."""

    ACKNOWLEDGED = "ACKNOWLEDGED"
    ANSWERED = "ANSWERED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    NO_COMMITMENT = "NO_COMMITMENT"
    REJECTED = "REJECTED"


class ClarificationReason(str, Enum):
    """Why a controlled reference could not be bound safely."""

    MISSING_REFERENT = "MISSING_REFERENT"
    AMBIGUOUS_REFERENT = "AMBIGUOUS_REFERENT"
    INVALID_CHOICE = "INVALID_CHOICE"


class ReferenceStatus(str, Enum):
    """Deterministic reference-resolution disposition."""

    EXPLICIT = "EXPLICIT"
    RESOLVED = "RESOLVED"
    RESOLVED_BY_CLARIFICATION = "RESOLVED_BY_CLARIFICATION"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"
    INVALID_CHOICE = "INVALID_CHOICE"


class _Act(str, Enum):
    FACT = "FACT"
    RULE = "RULE"
    QUESTION = "QUESTION"
    CLARIFICATION = "CLARIFICATION"


@dataclass(frozen=True, slots=True)
class DialogueEntity:
    entity_id: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"entity_id": self.entity_id, "label": self.label}


@dataclass(frozen=True, slots=True)
class DialogueFact:
    entity_id: str
    predicate_id: str
    polarity: bool
    source_turn: int

    @property
    def semantic_key(self) -> tuple[str, str, bool]:
        return (self.entity_id, self.predicate_id, self.polarity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "predicate_id": self.predicate_id,
            "polarity": self.polarity,
            "source_turn": self.source_turn,
        }


@dataclass(frozen=True, slots=True)
class DialogueRule:
    antecedent_predicate_id: str
    consequent_predicate_id: str
    consequent_polarity: bool
    source_turn: int

    @property
    def semantic_key(self) -> tuple[str, str, bool]:
        return (
            self.antecedent_predicate_id,
            self.consequent_predicate_id,
            self.consequent_polarity,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "antecedent_predicate_id": self.antecedent_predicate_id,
            "consequent_predicate_id": self.consequent_predicate_id,
            "consequent_polarity": self.consequent_polarity,
            "source_turn": self.source_turn,
        }


@dataclass(frozen=True, slots=True)
class _ParsedMeaning:
    act: _Act
    subject_token: str | None = None
    predicate_id: str | None = None
    polarity: bool = True
    antecedent_predicate_id: str | None = None
    choice_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "grammar_rule": self.act.value.lower(),
            "act": self.act.value,
        }
        if self.act is not _Act.CLARIFICATION:
            result["polarity"] = self.polarity
        if self.subject_token is not None:
            result["subject"] = self.subject_token
        if self.predicate_id is not None:
            result["predicate_id"] = self.predicate_id
        if self.antecedent_predicate_id is not None:
            result["antecedent_predicate_id"] = self.antecedent_predicate_id
        if self.choice_token is not None:
            result["choice"] = self.choice_token
        return result


@dataclass(frozen=True, slots=True)
class _PendingReference:
    meaning: _ParsedMeaning
    token: str
    reason: ClarificationReason
    candidates: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "meaning": self.meaning.to_dict(),
            "token": self.token,
            "reason": self.reason.value,
            "candidates": list(self.candidates),
        }


@dataclass(frozen=True, slots=True)
class DialogueState:
    """Immutable snapshot of explicit conversational semantics."""

    turn_index: int = 0
    entities: tuple[DialogueEntity, ...] = ()
    facts: tuple[DialogueFact, ...] = ()
    rules: tuple[DialogueRule, ...] = ()
    recent_entities: tuple[str, ...] = ()
    pending_reference: _PendingReference | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cncm.dialogue-state/0.1",
            "turn_index": self.turn_index,
            "entities": [
                item.to_dict()
                for item in sorted(self.entities, key=lambda item: item.entity_id)
            ],
            "facts": [
                item.to_dict()
                for item in sorted(self.facts, key=lambda item: item.semantic_key)
            ],
            "rules": [
                item.to_dict()
                for item in sorted(self.rules, key=lambda item: item.semantic_key)
            ],
            "recent_entities": list(self.recent_entities),
            "pending_reference": (
                self.pending_reference.to_dict()
                if self.pending_reference is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ReferenceResolution:
    token: str
    status: ReferenceStatus
    entity_id: str | None = None
    candidates: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "status": self.status.value,
            "entity_id": self.entity_id,
            "candidates": list(self.candidates),
        }


@dataclass(frozen=True, slots=True)
class ConversationTrace:
    """JSON-compatible audit trace for one facade turn."""

    turn_index: int
    input_text: str
    parse_candidates: tuple[Mapping[str, Any], ...]
    selected_meaning: Mapping[str, Any] | None
    references: tuple[ReferenceResolution, ...]
    problem_packet: Mapping[str, Any] | None
    reasoning_bundle: Mapping[str, Any] | None
    verification: Mapping[str, Any] | None
    execution_parity: Mapping[str, Any] | None
    response_plan: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cncm.conversation-trace/0.1",
            "turn_index": self.turn_index,
            "input": self.input_text,
            "parse_candidates": [dict(item) for item in self.parse_candidates],
            "selected_meaning": (
                dict(self.selected_meaning)
                if self.selected_meaning is not None
                else None
            ),
            "references": [item.to_dict() for item in self.references],
            "problem_packet": (
                dict(self.problem_packet)
                if self.problem_packet is not None
                else None
            ),
            "reasoning_bundle": (
                dict(self.reasoning_bundle)
                if self.reasoning_bundle is not None
                else None
            ),
            "verification": (
                dict(self.verification) if self.verification is not None else None
            ),
            "execution_parity": (
                dict(self.execution_parity)
                if self.execution_parity is not None
                else None
            ),
            "response_plan": dict(self.response_plan),
        }


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    status: TurnStatus
    response: str
    state: DialogueState
    trace: ConversationTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cncm.conversation-turn/0.1",
            "status": self.status.value,
            "response": self.response,
            "state": self.state.to_dict(),
            "trace": self.trace.to_dict(),
        }


class ConversationalMind:
    """Stateful, deterministic facade for a small controlled-English grammar.

    Construction never accepts memory or a prior ``DialogueState``.  Reuse one
    instance for a dialogue and call :meth:`reset` to discard its explicit
    conversational knowledge.
    """

    _FACT = re.compile(
        rf"^(?P<subject>{_TOKEN})\s+is\s+(?P<negation>not\s+)?"
        rf"(?P<predicate>{_TOKEN})\.$",
        re.IGNORECASE,
    )
    _RULE = re.compile(
        rf"^Every\s+(?P<antecedent>{_TOKEN})\s+is\s+"
        rf"(?P<negation>not\s+)?(?P<consequent>{_TOKEN})\.$",
        re.IGNORECASE,
    )
    _QUESTION = re.compile(
        rf"^Is\s+(?P<subject>{_TOKEN})\s+(?P<negation>not\s+)?"
        rf"(?P<predicate>{_TOKEN})\?$",
        re.IGNORECASE,
    )
    _CLARIFICATION = re.compile(
        rf"^I\s+mean\s+(?P<choice>{_TOKEN})\.$",
        re.IGNORECASE,
    )
    SUPPORTED_FORMS = (
        "Name is property.",
        "Name is not property.",
        "Every property is property.",
        "Every property is not property.",
        "Is Name property?",
        "Is Name not property?",
        "I mean Name.",
    )

    def __init__(self) -> None:
        self._state = DialogueState()

    @property
    def state(self) -> DialogueState:
        return self._state

    def reset(self) -> DialogueState:
        """Discard all explicit dialogue knowledge; no memory is imported."""

        self._state = DialogueState()
        return self._state

    def turn(self, text: str) -> ConversationTurn:
        if not isinstance(text, str):
            raise TypeError("conversation input must be a string")

        input_text = text.strip()
        state = replace(self._state, turn_index=self._state.turn_index + 1)
        candidates = self._parse(input_text)
        candidate_dicts = tuple(item.to_dict() for item in candidates)

        if not input_text or len(input_text) > _MAX_INPUT_CHARACTERS:
            detail = "nonempty" if not input_text else "at most 512 characters"
            return self._complete(
                state,
                input_text,
                candidate_dicts,
                TurnStatus.REJECTED,
                f"Input must be {detail} and use the controlled grammar.",
                response_plan={
                    "kind": "SHOW_GRAMMAR",
                    "source": "controlled_grammar",
                },
            )

        if state.pending_reference is not None:
            if len(candidates) == 1 and candidates[0].act is _Act.CLARIFICATION:
                return self._consume_clarification(
                    state,
                    input_text,
                    candidates[0],
                    candidate_dicts,
                )
            return self._clarification_turn(
                state,
                input_text,
                candidate_dicts,
                state.pending_reference,
            )

        if not candidates:
            return self._complete(
                state,
                input_text,
                (),
                TurnStatus.REJECTED,
                (
                    "I only accept: 'Alice is human.', 'Every human is mortal.', "
                    "'Is Alice mortal?', and clarification as 'I mean Alice.'."
                ),
                response_plan={
                    "kind": "SHOW_GRAMMAR",
                    "source": "controlled_grammar",
                },
            )

        if len(candidates) != 1:
            return self._complete(
                state,
                input_text,
                candidate_dicts,
                TurnStatus.REJECTED,
                "The controlled input has more than one parse; please rephrase.",
                response_plan={
                    "kind": "REJECT_AMBIGUOUS_PARSE",
                    "source": "controlled_grammar",
                },
            )

        meaning = candidates[0]
        if meaning.act is _Act.CLARIFICATION:
            return self._complete(
                state,
                input_text,
                candidate_dicts,
                TurnStatus.REJECTED,
                "There is no unresolved reference to clarify.",
                selected_meaning=meaning.to_dict(),
                response_plan={
                    "kind": "REJECT_UNSOLICITED_CLARIFICATION",
                    "source": "dialogue_state",
                },
            )

        if meaning.act is _Act.RULE:
            return self._record_rule(
                state,
                input_text,
                meaning,
                candidate_dicts,
            )

        assert meaning.subject_token is not None
        reference = self._resolve_reference(state, meaning.subject_token)
        if reference.status in {ReferenceStatus.MISSING, ReferenceStatus.AMBIGUOUS}:
            reason = (
                ClarificationReason.MISSING_REFERENT
                if reference.status is ReferenceStatus.MISSING
                else ClarificationReason.AMBIGUOUS_REFERENT
            )
            pending = _PendingReference(
                meaning=meaning,
                token=meaning.subject_token,
                reason=reason,
                candidates=reference.candidates,
            )
            state = replace(state, pending_reference=pending)
            return self._clarification_turn(
                state,
                input_text,
                candidate_dicts,
                pending,
                references=(reference,),
            )

        assert reference.entity_id is not None
        resolved = replace(meaning, subject_token=reference.entity_id)
        try:
            state = self._ensure_entity(
                state,
                reference.entity_id,
                meaning.subject_token,
            )
        except ValueError:
            return self._limit_rejection(
                state,
                input_text,
                candidate_dicts,
                resolved,
                (reference,),
                "entity",
            )
        if resolved.act is _Act.FACT:
            return self._record_fact(
                state,
                input_text,
                resolved,
                candidate_dicts,
                (reference,),
            )
        return self._answer_question(
            state,
            input_text,
            resolved,
            candidate_dicts,
            (reference,),
        )

    @staticmethod
    def _normalize(token: str) -> str:
        return token.lower()

    @classmethod
    def _parse(cls, text: str) -> tuple[_ParsedMeaning, ...]:
        candidates: list[_ParsedMeaning] = []

        rule_match = cls._RULE.fullmatch(text)
        if rule_match:
            candidates.append(
                _ParsedMeaning(
                    act=_Act.RULE,
                    antecedent_predicate_id=cls._normalize(
                        rule_match.group("antecedent")
                    ),
                    predicate_id=cls._normalize(rule_match.group("consequent")),
                    polarity=rule_match.group("negation") is None,
                )
            )

        fact_match = cls._FACT.fullmatch(text)
        if fact_match:
            candidates.append(
                _ParsedMeaning(
                    act=_Act.FACT,
                    subject_token=fact_match.group("subject"),
                    predicate_id=cls._normalize(fact_match.group("predicate")),
                    polarity=fact_match.group("negation") is None,
                )
            )

        question_match = cls._QUESTION.fullmatch(text)
        if question_match:
            candidates.append(
                _ParsedMeaning(
                    act=_Act.QUESTION,
                    subject_token=question_match.group("subject"),
                    predicate_id=cls._normalize(question_match.group("predicate")),
                    polarity=question_match.group("negation") is None,
                )
            )

        clarification_match = cls._CLARIFICATION.fullmatch(text)
        if clarification_match:
            candidates.append(
                _ParsedMeaning(
                    act=_Act.CLARIFICATION,
                    choice_token=clarification_match.group("choice"),
                )
            )

        return tuple(candidates)

    @staticmethod
    def _entity_map(state: DialogueState) -> dict[str, DialogueEntity]:
        return {item.entity_id: item for item in state.entities}

    @classmethod
    def _resolve_reference(
        cls,
        state: DialogueState,
        token: str,
    ) -> ReferenceResolution:
        normalized = cls._normalize(token)
        if normalized not in _PRONOUNS:
            return ReferenceResolution(
                token=token,
                status=ReferenceStatus.EXPLICIT,
                entity_id=normalized,
            )
        if not state.recent_entities:
            return ReferenceResolution(
                token=token,
                status=ReferenceStatus.MISSING,
            )
        if len(state.recent_entities) > 1:
            return ReferenceResolution(
                token=token,
                status=ReferenceStatus.AMBIGUOUS,
                candidates=state.recent_entities,
            )
        return ReferenceResolution(
            token=token,
            status=ReferenceStatus.RESOLVED,
            entity_id=state.recent_entities[0],
            candidates=state.recent_entities,
        )

    @classmethod
    def _ensure_entity(
        cls,
        state: DialogueState,
        entity_id: str,
        source_label: str,
    ) -> DialogueState:
        if entity_id in cls._entity_map(state):
            return state
        if len(state.entities) >= _MAX_ENTITIES:
            raise ValueError("dialogue entity limit reached")
        label = source_label if cls._normalize(source_label) == entity_id else entity_id
        entity = DialogueEntity(entity_id=entity_id, label=label)
        return replace(state, entities=(*state.entities, entity))

    @staticmethod
    def _focus(state: DialogueState, entity_id: str) -> DialogueState:
        recent = (entity_id,) + tuple(
            item for item in state.recent_entities if item != entity_id
        )
        return replace(state, recent_entities=recent[:2])

    def _record_fact(
        self,
        state: DialogueState,
        input_text: str,
        meaning: _ParsedMeaning,
        parse_candidates: tuple[Mapping[str, Any], ...],
        references: tuple[ReferenceResolution, ...],
    ) -> ConversationTurn:
        assert meaning.subject_token is not None
        assert meaning.predicate_id is not None
        fact = DialogueFact(
            entity_id=meaning.subject_token,
            predicate_id=meaning.predicate_id,
            polarity=meaning.polarity,
            source_turn=state.turn_index,
        )
        duplicate = any(
            item.semantic_key == fact.semantic_key for item in state.facts
        )
        if not duplicate:
            if len(state.facts) >= _MAX_FACTS:
                return self._limit_rejection(
                    state,
                    input_text,
                    parse_candidates,
                    meaning,
                    references,
                    "fact",
                )
            state = replace(state, facts=(*state.facts, fact))
        state = self._focus(state, meaning.subject_token)
        clause = self._clause(state, fact.entity_id, fact.predicate_id, fact.polarity)
        prefix = "Already recorded" if duplicate else "Recorded"
        return self._complete(
            state,
            input_text,
            parse_candidates,
            TurnStatus.ACKNOWLEDGED,
            f"{prefix}: {clause}.",
            selected_meaning=meaning.to_dict(),
            references=references,
            response_plan={
                "kind": "ACKNOWLEDGE_EXPLICIT_FACT",
                "source": "dialogue_state",
                "duplicate": duplicate,
            },
        )

    def _record_rule(
        self,
        state: DialogueState,
        input_text: str,
        meaning: _ParsedMeaning,
        parse_candidates: tuple[Mapping[str, Any], ...],
    ) -> ConversationTurn:
        assert meaning.antecedent_predicate_id is not None
        assert meaning.predicate_id is not None
        rule = DialogueRule(
            antecedent_predicate_id=meaning.antecedent_predicate_id,
            consequent_predicate_id=meaning.predicate_id,
            consequent_polarity=meaning.polarity,
            source_turn=state.turn_index,
        )
        duplicate = any(
            item.semantic_key == rule.semantic_key for item in state.rules
        )
        if not duplicate:
            if len(state.rules) >= _MAX_RULES:
                return self._limit_rejection(
                    state,
                    input_text,
                    parse_candidates,
                    meaning,
                    (),
                    "rule",
                )
            state = replace(state, rules=(*state.rules, rule))
        consequent = self._predicate_phrase(
            rule.consequent_predicate_id,
            rule.consequent_polarity,
        )
        prefix = "Already recorded" if duplicate else "Recorded rule"
        return self._complete(
            state,
            input_text,
            parse_candidates,
            TurnStatus.ACKNOWLEDGED,
            f"{prefix}: every {rule.antecedent_predicate_id} is {consequent}.",
            selected_meaning=meaning.to_dict(),
            response_plan={
                "kind": "ACKNOWLEDGE_EXPLICIT_RULE",
                "source": "dialogue_state",
                "duplicate": duplicate,
            },
        )

    def _consume_clarification(
        self,
        state: DialogueState,
        input_text: str,
        clarification: _ParsedMeaning,
        parse_candidates: tuple[Mapping[str, Any], ...],
    ) -> ConversationTurn:
        pending = state.pending_reference
        assert pending is not None
        assert clarification.choice_token is not None
        choice = self._normalize(clarification.choice_token)

        if choice in _PRONOUNS or (
            pending.candidates and choice not in pending.candidates
        ):
            invalid = ReferenceResolution(
                token=clarification.choice_token,
                status=ReferenceStatus.INVALID_CHOICE,
                candidates=pending.candidates,
            )
            replacement = replace(
                pending,
                reason=ClarificationReason.INVALID_CHOICE,
            )
            state = replace(state, pending_reference=replacement)
            return self._clarification_turn(
                state,
                input_text,
                parse_candidates,
                replacement,
                references=(invalid,),
            )

        try:
            state = self._ensure_entity(state, choice, clarification.choice_token)
        except ValueError:
            return self._limit_rejection(
                state,
                input_text,
                parse_candidates,
                replace(pending.meaning, subject_token=choice),
                (),
                "entity",
            )
        state = replace(
            state,
            pending_reference=None,
            recent_entities=(choice,),
        )
        resolved = replace(pending.meaning, subject_token=choice)
        reference = ReferenceResolution(
            token=pending.token,
            status=ReferenceStatus.RESOLVED_BY_CLARIFICATION,
            entity_id=choice,
            candidates=pending.candidates,
        )

        if resolved.act is _Act.FACT:
            return self._record_fact(
                state,
                input_text,
                resolved,
                parse_candidates,
                (reference,),
            )
        return self._answer_question(
            state,
            input_text,
            resolved,
            parse_candidates,
            (reference,),
        )

    def _clarification_turn(
        self,
        state: DialogueState,
        input_text: str,
        parse_candidates: tuple[Mapping[str, Any], ...],
        pending: _PendingReference,
        *,
        references: tuple[ReferenceResolution, ...] = (),
    ) -> ConversationTurn:
        entity_map = self._entity_map(state)
        labels = tuple(
            entity_map[item].label if item in entity_map else item
            for item in pending.candidates
        )
        if labels:
            joined = " or ".join(labels)
            response = (
                f"Does '{pending.token}' refer to {joined}? "
                "Reply with 'I mean Name.'."
            )
        else:
            response = (
                f"Who does '{pending.token}' refer to? "
                "Reply with 'I mean Name.'."
            )
        return self._complete(
            state,
            input_text,
            parse_candidates,
            TurnStatus.CLARIFICATION_REQUIRED,
            response,
            references=references,
            response_plan={
                "kind": "ASK_CLARIFICATION",
                "source": "reference_resolver",
                "reason": pending.reason.value,
                "candidates": list(pending.candidates),
            },
        )

    def _answer_question(
        self,
        state: DialogueState,
        input_text: str,
        meaning: _ParsedMeaning,
        parse_candidates: tuple[Mapping[str, Any], ...],
        references: tuple[ReferenceResolution, ...],
    ) -> ConversationTurn:
        assert meaning.subject_token is not None
        assert meaning.predicate_id is not None
        state = replace(state, recent_entities=(meaning.subject_token,))

        packet: ProblemPacket | None = None
        bundle: Mapping[str, Any] | None = None
        stage = "problem_contract"
        try:
            packet = self._compile_packet(state, meaning)
            stage = "conversational_reasoning"
            result = CognitiveMachine().run(packet)
            bundle = result.to_dict()
            stage = "conversational_evidence_verification"
            verification = verify_evidence(bundle)
            stage = "confirmation_reasoning"
            confirmation_result = CognitiveMachine().run(packet)
            confirmation_bundle = confirmation_result.to_dict()
            stage = "confirmation_evidence_verification"
            confirmation_verification = verify_evidence(confirmation_bundle)
            stage = "execution_parity"
            execution_parity = self._compare_reexecutions(
                result,
                confirmation_result,
                verification.to_dict(),
                confirmation_verification.to_dict(),
            )
        except Exception as exc:
            return self._complete(
                state,
                input_text,
                parse_candidates,
                TurnStatus.REJECTED,
                (
                    "I cannot render an answer because the controlled reasoning "
                    "checks did not complete."
                ),
                selected_meaning=meaning.to_dict(),
                references=references,
                problem_packet=packet.to_dict() if packet is not None else None,
                reasoning_bundle=bundle,
                execution_parity={
                    "schema_version": "cncm.execution-parity/0.1",
                    "performed": False,
                    "matches": False,
                    "claim_scope": "same_compiled_packet_two_fresh_machines",
                    "stage": stage,
                    "error_type": type(exc).__name__,
                },
                response_plan={
                    "kind": "FAIL_CLOSED",
                    "source": stage,
                    "error_type": type(exc).__name__,
                },
            )

        verification_dict = verification.to_dict()
        packet_dict = packet.to_dict()
        if not verification.valid or not confirmation_verification.valid:
            return self._complete(
                state,
                input_text,
                parse_candidates,
                TurnStatus.REJECTED,
                "I cannot render an answer because evidence verification failed.",
                selected_meaning=meaning.to_dict(),
                references=references,
                problem_packet=packet_dict,
                reasoning_bundle=bundle,
                verification=verification_dict,
                execution_parity=execution_parity,
                response_plan={
                    "kind": "FAIL_CLOSED",
                    "source": "evidence_verifier",
                },
            )

        if not execution_parity["matches"]:
            return self._complete(
                state,
                input_text,
                parse_candidates,
                TurnStatus.REJECTED,
                (
                    "I cannot render an answer because the deterministic "
                    "second-execution check failed."
                ),
                selected_meaning=meaning.to_dict(),
                references=references,
                problem_packet=packet_dict,
                reasoning_bundle=bundle,
                verification=verification_dict,
                execution_parity=execution_parity,
                response_plan={
                    "kind": "FAIL_CLOSED",
                    "source": "execution_parity",
                },
            )

        clause = self._clause(
            state,
            meaning.subject_token,
            meaning.predicate_id,
            meaning.polarity,
        )
        conclusion = result.final_state.commitment_state.conclusion
        exact_commitment = (
            result.terminal_status is TerminalStatus.CONCLUDED
            and conclusion is not None
            and conclusion.key == packet.query.key
        )
        if exact_commitment:
            return self._complete(
                state,
                input_text,
                parse_candidates,
                TurnStatus.ANSWERED,
                f"Yes. The committed result is: {clause}.",
                selected_meaning=meaning.to_dict(),
                references=references,
                problem_packet=packet_dict,
                reasoning_bundle=bundle,
                verification=verification_dict,
                execution_parity=execution_parity,
                response_plan={
                    "kind": "RENDER_COMMITTED_RESULT",
                    "source": "verified_commitment",
                    "terminal_status": result.terminal_status.value,
                    "conclusion_key": conclusion.key,
                },
            )

        if result.terminal_status is TerminalStatus.CONCLUDED:
            response = (
                "I cannot render an answer because the commitment does not match "
                "the controlled query."
            )
            source = "commitment_mismatch"
        elif result.terminal_status is TerminalStatus.NEEDS_INFORMATION:
            response = (
                "I cannot commit an answer: the stated facts and rules do not "
                f"establish whether {clause}."
            )
            source = "verified_terminal_status"
        elif result.terminal_status is TerminalStatus.CONFLICT_UNRESOLVED:
            response = (
                "I cannot commit an answer: the stated knowledge is contradictory."
            )
            source = "verified_terminal_status"
        else:
            response = (
                "I cannot commit an answer; the reasoner halted with "
                f"{result.terminal_status.value}."
            )
            source = "verified_terminal_status"
        return self._complete(
            state,
            input_text,
            parse_candidates,
            TurnStatus.NO_COMMITMENT,
            response,
            selected_meaning=meaning.to_dict(),
            references=references,
            problem_packet=packet_dict,
            reasoning_bundle=bundle,
            verification=verification_dict,
            execution_parity=execution_parity,
            response_plan={
                "kind": "REPORT_NO_COMMITMENT",
                "source": source,
                "terminal_status": result.terminal_status.value,
            },
        )

    @staticmethod
    def _semantic_projection(result: RunResult) -> dict[str, Any]:
        conclusion = result.final_state.commitment_state.conclusion
        branches = tuple(
            sorted(
                result.final_state.branch_table,
                key=lambda item: item.branch_id,
            )
        )
        return {
            "run_id": result.final_state.run_id,
            "problem_packet_hash": result.problem.input_hash,
            "terminal_status": result.terminal_status.value,
            "conclusion_key": conclusion.key if conclusion is not None else None,
            "branch_ids": [item.branch_id for item in branches],
            "branch_digest": digest([item.to_dict() for item in branches]),
            "trace_head": result.final_state.trace_head,
            "trace_digest": result.trace_digest,
            "final_state_hash": result.final_state.state_hash,
            "evidence_digest": result.evidence["evidence_digest"],
        }

    @classmethod
    def _compare_reexecutions(
        cls,
        primary_result: RunResult,
        confirmation_result: RunResult,
        primary_verification: Mapping[str, Any],
        confirmation_verification: Mapping[str, Any],
    ) -> dict[str, Any]:
        primary = cls._semantic_projection(primary_result)
        confirmation = cls._semantic_projection(confirmation_result)
        compared_fields = {
            key: primary[key] == confirmation[key]
            for key in (
                "run_id",
                "problem_packet_hash",
                "terminal_status",
                "conclusion_key",
                "branch_ids",
                "branch_digest",
                "trace_head",
                "trace_digest",
                "final_state_hash",
                "evidence_digest",
            )
        }
        return {
            "schema_version": "cncm.execution-parity/0.1",
            "performed": True,
            "matches": all(compared_fields.values()),
            "claim_scope": "same_compiled_packet_two_fresh_machines",
            "does_not_establish": [
                "language_parse_correctness",
                "general_english_understanding",
                "premise_truth",
            ],
            "compared_fields": compared_fields,
            "primary_run": primary,
            "confirmation_run": confirmation,
            "evidence_verification": {
                "primary": dict(primary_verification),
                "confirmation": dict(confirmation_verification),
            },
        }

    @staticmethod
    def _compile_packet(
        state: DialogueState,
        meaning: _ParsedMeaning,
    ) -> ProblemPacket:
        assert meaning.subject_token is not None
        assert meaning.predicate_id is not None

        predicate_ids = {meaning.predicate_id}
        predicate_ids.update(item.predicate_id for item in state.facts)
        for item in state.rules:
            predicate_ids.add(item.antecedent_predicate_id)
            predicate_ids.add(item.consequent_predicate_id)

        facts = []
        for item in sorted(state.facts, key=lambda item: item.semantic_key):
            facts.append(
                {
                    "predicate": item.predicate_id,
                    "arguments": [item.entity_id],
                    "polarity": item.polarity,
                    "evidence_status": "asserted",
                    "provenance": [
                        {
                            "source_type": "conversation",
                            "source_id": f"turn_{item.source_turn:04d}",
                            "detail": "explicit controlled-English fact",
                        }
                    ],
                }
            )

        rules = []
        for item in sorted(state.rules, key=lambda item: item.semantic_key):
            rule_identity = "\0".join(
                (
                    item.antecedent_predicate_id,
                    item.consequent_predicate_id,
                    "1" if item.consequent_polarity else "0",
                )
            )
            rule_digest = sha256(rule_identity.encode("utf-8")).hexdigest()[:16]
            rules.append(
                {
                    "rule_id": f"dialogue_rule_{rule_digest}",
                    "operation": "INFER_MODUS_PONENS",
                    "antecedents": [
                        {
                            "predicate": item.antecedent_predicate_id,
                            "arguments": ["?x"],
                            "polarity": True,
                        }
                    ],
                    "consequent": {
                        "predicate": item.consequent_predicate_id,
                        "arguments": ["?x"],
                        "polarity": item.consequent_polarity,
                    },
                    "provenance": [
                        {
                            "source_type": "conversation",
                            "source_id": f"turn_{item.source_turn:04d}",
                            "detail": "explicit controlled-English rule",
                        }
                    ],
                }
            )

        document = {
            "schema_version": "cncm.problem/0.1",
            "problem_id": f"dialogue_turn_{state.turn_index:04d}",
            "goal_id": f"answer_turn_{state.turn_index:04d}",
            "seed": 0,
            "entities": [
                {"entity_id": item.entity_id, "entity_type": "individual"}
                for item in sorted(state.entities, key=lambda item: item.entity_id)
            ],
            "predicates": [
                {
                    "predicate_id": predicate_id,
                    "argument_types": ["individual"],
                    "transitive": False,
                }
                for predicate_id in sorted(predicate_ids)
            ],
            "facts": facts,
            "rules": rules,
            "query": {
                "predicate": meaning.predicate_id,
                "arguments": [meaning.subject_token],
                "polarity": meaning.polarity,
            },
            "budgets": {
                "max_ticks": 512,
                "max_branches": 4,
                "max_rpm_depth": 2,
                "max_inference_steps": 256,
                "max_memory_queries": 1,
                "max_repeat_states": 3,
            },
        }
        return ProblemPacket.from_dict(document)

    def _limit_rejection(
        self,
        state: DialogueState,
        input_text: str,
        parse_candidates: tuple[Mapping[str, Any], ...],
        meaning: _ParsedMeaning,
        references: tuple[ReferenceResolution, ...],
        item_type: str,
    ) -> ConversationTurn:
        return self._complete(
            state,
            input_text,
            parse_candidates,
            TurnStatus.REJECTED,
            f"The bounded dialogue {item_type} limit has been reached.",
            selected_meaning=meaning.to_dict(),
            references=references,
            response_plan={
                "kind": "REJECT_BUDGET",
                "source": "dialogue_limits",
                "item_type": item_type,
            },
        )

    @classmethod
    def _clause(
        cls,
        state: DialogueState,
        entity_id: str,
        predicate_id: str,
        polarity: bool,
    ) -> str:
        entity = cls._entity_map(state).get(entity_id)
        label = entity.label if entity is not None else entity_id
        return f"{label} is {cls._predicate_phrase(predicate_id, polarity)}"

    @staticmethod
    def _predicate_phrase(predicate_id: str, polarity: bool) -> str:
        display = predicate_id.replace("_", "-")
        return display if polarity else f"not {display}"

    def _complete(
        self,
        state: DialogueState,
        input_text: str,
        parse_candidates: tuple[Mapping[str, Any], ...],
        status: TurnStatus,
        response: str,
        *,
        selected_meaning: Mapping[str, Any] | None = None,
        references: tuple[ReferenceResolution, ...] = (),
        problem_packet: Mapping[str, Any] | None = None,
        reasoning_bundle: Mapping[str, Any] | None = None,
        verification: Mapping[str, Any] | None = None,
        execution_parity: Mapping[str, Any] | None = None,
        response_plan: Mapping[str, Any],
    ) -> ConversationTurn:
        self._state = state
        trace = ConversationTrace(
            turn_index=state.turn_index,
            input_text=input_text,
            parse_candidates=parse_candidates,
            selected_meaning=selected_meaning,
            references=references,
            problem_packet=problem_packet,
            reasoning_bundle=reasoning_bundle,
            verification=verification,
            execution_parity=execution_parity,
            response_plan=response_plan,
        )
        return ConversationTurn(
            status=status,
            response=response,
            state=state,
            trace=trace,
        )


__all__ = [
    "ClarificationReason",
    "ConversationTrace",
    "ConversationTurn",
    "ConversationalMind",
    "DialogueState",
    "ReferenceResolution",
    "ReferenceStatus",
    "TurnStatus",
]
