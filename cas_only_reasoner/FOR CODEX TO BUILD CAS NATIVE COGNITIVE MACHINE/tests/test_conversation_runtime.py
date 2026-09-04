from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from cncm import (
    ClarificationReason,
    ConversationalMind,
    ProblemPacket,
    ReferenceStatus,
    TurnStatus,
)
from cncm.verification import VerificationReport


class ConversationalMindTests(unittest.TestCase):
    def test_fact_rule_question_runs_authoritative_packet(self) -> None:
        mind = ConversationalMind()

        fact = mind.turn("Alice is human.")
        rule = mind.turn("Every human is mortal.")
        answer = mind.turn("Is Alice mortal?")

        self.assertIs(fact.status, TurnStatus.ACKNOWLEDGED)
        self.assertIs(rule.status, TurnStatus.ACKNOWLEDGED)
        self.assertIs(answer.status, TurnStatus.ANSWERED)
        self.assertEqual(
            answer.response,
            "Yes. The committed result is: Alice is mortal.",
        )
        trace = answer.trace.to_dict()
        self.assertEqual(
            trace["response_plan"]["kind"],
            "RENDER_COMMITTED_RESULT",
        )
        self.assertTrue(trace["verification"]["valid"])
        self.assertEqual(
            trace["reasoning_bundle"]["summary"]["terminal_status"],
            "CONCLUDED",
        )
        parity = trace["execution_parity"]
        self.assertTrue(parity["performed"])
        self.assertTrue(parity["matches"])
        self.assertEqual(
            parity["claim_scope"],
            "same_compiled_packet_two_fresh_machines",
        )
        self.assertIn("language_parse_correctness", parity["does_not_establish"])
        self.assertTrue(all(parity["compared_fields"].values()))
        self.assertEqual(
            parity["primary_run"]["terminal_status"],
            parity["confirmation_run"]["terminal_status"],
        )
        self.assertEqual(
            parity["primary_run"]["problem_packet_hash"],
            parity["confirmation_run"]["problem_packet_hash"],
        )
        self.assertEqual(
            parity["primary_run"]["conclusion_key"],
            "mortal(alice)@global",
        )
        self.assertEqual(
            parity["primary_run"]["branch_digest"],
            parity["confirmation_run"]["branch_digest"],
        )
        self.assertEqual(
            parity["primary_run"]["trace_digest"],
            parity["confirmation_run"]["trace_digest"],
        )
        self.assertTrue(
            parity["evidence_verification"]["confirmation"]["valid"]
        )
        packet = ProblemPacket.from_dict(trace["problem_packet"])
        self.assertEqual(packet.query.key, "mortal(alice)@global")
        self.assertEqual(len(packet.facts), 1)
        self.assertEqual(len(packet.rules), 1)
        json.dumps(answer.to_dict(), sort_keys=True, allow_nan=False)

    def test_unambiguous_recent_pronoun_is_resolved(self) -> None:
        mind = ConversationalMind()
        mind.turn("Alice is human.")
        mind.turn("Every human is mortal.")

        answer = mind.turn("Is she mortal?")

        self.assertIs(answer.status, TurnStatus.ANSWERED)
        reference = answer.trace.references[0]
        self.assertIs(reference.status, ReferenceStatus.RESOLVED)
        self.assertEqual(reference.entity_id, "alice")
        self.assertEqual(answer.trace.selected_meaning["subject"], "alice")

    def test_ambiguous_pronoun_requires_and_consumes_typed_clarification(self) -> None:
        mind = ConversationalMind()
        mind.turn("Every human is mortal.")
        mind.turn("Alice is human.")
        mind.turn("Bob is human.")

        clarification = mind.turn("Is she mortal?")

        self.assertIs(
            clarification.status,
            TurnStatus.CLARIFICATION_REQUIRED,
        )
        self.assertEqual(
            clarification.trace.response_plan["reason"],
            ClarificationReason.AMBIGUOUS_REFERENT.value,
        )
        self.assertEqual(
            clarification.state.pending_reference.candidates,
            ("bob", "alice"),
        )
        self.assertIsNone(clarification.trace.reasoning_bundle)

        bad_choice = mind.turn("I mean Carol.")
        self.assertIs(
            bad_choice.status,
            TurnStatus.CLARIFICATION_REQUIRED,
        )
        self.assertEqual(
            bad_choice.trace.response_plan["reason"],
            ClarificationReason.INVALID_CHOICE.value,
        )
        self.assertIs(
            bad_choice.trace.references[0].status,
            ReferenceStatus.INVALID_CHOICE,
        )

        answer = mind.turn("I mean Alice.")
        self.assertIs(answer.status, TurnStatus.ANSWERED)
        self.assertEqual(
            answer.response,
            "Yes. The committed result is: Alice is mortal.",
        )
        self.assertIs(
            answer.trace.references[0].status,
            ReferenceStatus.RESOLVED_BY_CLARIFICATION,
        )

    def test_missing_pronoun_asks_then_reports_verified_no_commitment(self) -> None:
        mind = ConversationalMind()

        clarification = mind.turn("Is she mortal?")
        self.assertIs(
            clarification.status,
            TurnStatus.CLARIFICATION_REQUIRED,
        )
        self.assertEqual(
            clarification.trace.response_plan["reason"],
            ClarificationReason.MISSING_REFERENT.value,
        )

        result = mind.turn("I mean Alice.")
        self.assertIs(result.status, TurnStatus.NO_COMMITMENT)
        self.assertIn("cannot commit an answer", result.response)
        self.assertTrue(result.trace.verification["valid"])
        self.assertEqual(
            result.trace.reasoning_bundle["summary"]["terminal_status"],
            "NEEDS_INFORMATION",
        )

    def test_explicit_negative_fact_and_question(self) -> None:
        mind = ConversationalMind()
        mind.turn("Alice is not mortal.")

        answer = mind.turn("Is Alice not mortal?")

        self.assertIs(answer.status, TurnStatus.ANSWERED)
        self.assertEqual(
            answer.response,
            "Yes. The committed result is: Alice is not mortal.",
        )

    def test_chained_rules_commit_but_contradiction_never_renders_answer(self) -> None:
        chained = ConversationalMind()
        for text in (
            "Alice is human.",
            "Every human is mortal.",
            "Every mortal is finite.",
        ):
            chained.turn(text)
        answer = chained.turn("Is Alice finite?")
        self.assertIs(answer.status, TurnStatus.ANSWERED)
        self.assertTrue(answer.trace.verification["valid"])

        contradictory = ConversationalMind()
        contradictory.turn("Alice is mortal.")
        contradictory.turn("Alice is not mortal.")
        no_answer = contradictory.turn("Is Alice mortal?")
        self.assertIs(no_answer.status, TurnStatus.NO_COMMITMENT)
        self.assertNotIn("committed result", no_answer.response)
        self.assertEqual(
            no_answer.trace.reasoning_bundle["summary"]["terminal_status"],
            "CONFLICT_UNRESOLVED",
        )

    def test_unsupported_language_is_rejected_without_reasoning(self) -> None:
        mind = ConversationalMind()

        result = mind.turn("Please think freely about Alice.")

        self.assertIs(result.status, TurnStatus.REJECTED)
        self.assertEqual(result.trace.parse_candidates, ())
        self.assertIsNone(result.trace.problem_packet)
        self.assertIsNone(result.trace.reasoning_bundle)

    def test_pronoun_cannot_be_used_as_its_own_clarification(self) -> None:
        mind = ConversationalMind()
        mind.turn("Is she mortal?")

        result = mind.turn("I mean she.")

        self.assertIs(
            result.status,
            TurnStatus.CLARIFICATION_REQUIRED,
        )
        self.assertEqual(
            result.trace.response_plan["reason"],
            ClarificationReason.INVALID_CHOICE.value,
        )

    def test_evidence_failure_never_renders_committed_answer(self) -> None:
        mind = ConversationalMind()
        mind.turn("Alice is human.")
        mind.turn("Every human is mortal.")
        invalid = VerificationReport(
            False,
            (("forced_test_failure", False),),
            ("forced test failure",),
        )

        with patch(
            "cncm.conversation.verify_evidence",
            return_value=invalid,
        ) as verifier:
            result = mind.turn("Is Alice mortal?")

        self.assertEqual(verifier.call_count, 2)
        self.assertIs(result.status, TurnStatus.REJECTED)
        self.assertEqual(
            result.response,
            "I cannot render an answer because evidence verification failed.",
        )
        self.assertNotIn("committed result", result.response)
        self.assertEqual(result.trace.response_plan["kind"], "FAIL_CLOSED")

    def test_execution_parity_mismatch_fails_closed(self) -> None:
        mind = ConversationalMind()
        mind.turn("Alice is human.")
        mind.turn("Every human is mortal.")

        original = ConversationalMind._semantic_projection
        calls = 0

        def mismatching_projection(result):
            nonlocal calls
            calls += 1
            projection = original(result)
            if calls == 2:
                projection["trace_digest"] = "0" * 64
            return projection

        with patch.object(
            ConversationalMind,
            "_semantic_projection",
            side_effect=mismatching_projection,
        ):
            result = mind.turn("Is Alice mortal?")

        self.assertIs(result.status, TurnStatus.REJECTED)
        self.assertEqual(calls, 2)
        self.assertFalse(result.trace.execution_parity["matches"])
        self.assertFalse(
            result.trace.execution_parity["compared_fields"]["trace_digest"]
        )
        self.assertEqual(
            result.trace.response_plan,
            {"kind": "FAIL_CLOSED", "source": "execution_parity"},
        )
        self.assertNotIn("committed result", result.response)

    def test_same_dialogue_is_byte_deterministic_and_reset_clears_state(self) -> None:
        script = (
            "Alice is human.",
            "Every human is mortal.",
            "Is Alice mortal?",
        )
        first = ConversationalMind()
        second = ConversationalMind()

        first_result = [first.turn(item).to_dict() for item in script]
        second_result = [second.turn(item).to_dict() for item in script]

        first_bytes = json.dumps(
            first_result,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        second_bytes = json.dumps(
            second_result,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(first_bytes, second_bytes)

        state = first.reset()
        self.assertEqual(state.turn_index, 0)
        self.assertEqual(state.entities, ())
        self.assertEqual(state.facts, ())
        self.assertEqual(state.rules, ())


if __name__ == "__main__":
    unittest.main()
