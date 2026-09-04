from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests._support import ROOT, SCHEMAS


CONVERSATION_FIXTURES = ROOT / "fixtures" / "conversation"
PROTOCOL = ROOT / "spec" / "CAS_CONVERSATION_PROTOCOL_v0.1.md"
CONVERSATION_SCHEMAS = {
    "dialogue_state.schema.json",
    "dialogue_turn.schema.json",
    "dialogue_act.schema.json",
    "semantic_packet.schema.json",
    "referent.schema.json",
    "response_plan.schema.json",
}
EXPECTED_CATEGORIES = {
    "single_turn",
    "multi_turn",
    "pronoun_reference",
    "ambiguity",
    "clarification",
    "correction_learning",
    "topic_switching",
    "memory_recall",
}
EQUIVALENCE_DIMENSIONS = {
    "SEMANTIC_CONTENT",
    "TERMINAL_DISPOSITION",
    "BRANCH_TOPOLOGY",
    "INFERENCE_TRACE",
    "RPM_SUBGOALS",
    "COMMITTED_RESULT",
    "MEMORY_EFFECTS",
    "RESPONSE_PLAN",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                yield child
            yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)


def resolve_pointer(document, fragment: str):
    if fragment in ("", "#"):
        return document
    if not fragment.startswith("#/"):
        raise AssertionError(f"unsupported JSON pointer: {fragment}")
    current = document
    for raw in fragment[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


class ConversationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = sorted(CONVERSATION_FIXTURES.glob("*/case.json"))
        cls.cases = {path.parent.name: read_json(path) for path in cls.paths}

    def test_required_fixture_categories_exist_once(self) -> None:
        self.assertEqual(set(self.cases), EXPECTED_CATEGORIES)
        self.assertEqual(len(self.paths), len(EXPECTED_CATEGORIES))

    def test_protocol_schemas_parse_and_refs_are_local(self) -> None:
        paths = [SCHEMAS / name for name in sorted(CONVERSATION_SCHEMAS)]
        self.assertTrue(all(path.is_file() for path in paths))
        documents = {path.resolve(): read_json(path) for path in SCHEMAS.glob("*.schema.json")}
        ids = []
        for path in paths:
            document = documents[path.resolve()]
            self.assertEqual(
                document["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )
            ids.append(document["$id"])
            for reference in walk_refs(document):
                target_name, separator, fragment_text = reference.partition("#")
                self.assertNotIn("://", target_name, "remote schema refs are prohibited")
                target = (path.parent / target_name).resolve() if target_name else path.resolve()
                self.assertEqual(target.parent, SCHEMAS.resolve())
                self.assertIn(target, documents)
                fragment = f"#{fragment_text}" if separator else ""
                resolve_pointer(documents[target], fragment)
        self.assertEqual(len(ids), len(set(ids)))

    def test_fixture_claims_are_honest_and_bounded(self) -> None:
        fixture_ids = set()
        for category, case in self.cases.items():
            with self.subTest(category=category):
                self.assertEqual(case["fixture_version"], "cas.conversation_fixture/0.1")
                self.assertEqual(case["category"], category)
                self.assertNotIn(case["fixture_id"], fixture_ids)
                fixture_ids.add(case["fixture_id"])
                self.assertEqual(
                    case["qualification"],
                    {
                        "contract_status": "SUPPORTED",
                        "capability_claim": "PROVISIONAL",
                        "implementation_status": "UNSUPPORTED",
                        "evidence_status": "NOT_RUN",
                        "direct_semantic_runtime_status": "NOT_RUN",
                    },
                )
                self.assertEqual(case["expected"]["runtime_execution"], "NOT_RUN")
                for plan in case["response_plans"]:
                    self.assertNotEqual(
                        plan["memory_write"]["proposal_status"],
                        "AUTHORIZED_BY_KERNEL",
                    )
                    self.assertEqual(plan["renderer_status"], "PROVISIONAL_NOT_IMPLEMENTED")

    def test_turns_form_one_deterministic_revision_chain(self) -> None:
        for category, case in self.cases.items():
            with self.subTest(category=category):
                turns = case["turns"]
                self.assertTrue(turns)
                conversation_id = case["final_state"]["conversation_id"]
                turn_ids = []
                previous_after = None
                if "initial_state" in case:
                    self.assertEqual(case["initial_state"]["conversation_id"], conversation_id)
                    previous_after = case["initial_state"]["state_revision"]
                for turn in turns:
                    self.assertEqual(turn["conversation_id"], conversation_id)
                    self.assertEqual(turn["state_after_revision"], turn["state_before_revision"] + 1)
                    if previous_after is not None:
                        self.assertEqual(turn["state_before_revision"], previous_after)
                    previous_after = turn["state_after_revision"]
                    turn_ids.append(turn["turn_id"])
                self.assertEqual(case["final_state"]["state_revision"], previous_after)
                self.assertEqual(len(turn_ids), len(set(turn_ids)))
                for turn_id in turn_ids:
                    self.assertIn(turn_id, case["final_state"]["prior_turn_ids"])

    def test_language_and_direct_packets_are_static_semantic_twins(self) -> None:
        for category, case in self.cases.items():
            with self.subTest(category=category):
                packet_by_id = {}
                for pair in case["semantic_pairs"]:
                    language = pair["language_packet"]
                    direct = pair["direct_packet"]
                    packet_by_id[language["packet_id"]] = language
                    packet_by_id[direct["packet_id"]] = direct
                    self.assertEqual(pair["equivalence_id"], language["equivalence"]["equivalence_id"])
                    self.assertEqual(pair["equivalence_id"], direct["equivalence"]["equivalence_id"])
                    self.assertEqual(language["construction_mode"], "CONTROLLED_ENGLISH")
                    self.assertEqual(language["language_profile"], "CCB-L1-CE-0.1")
                    self.assertEqual(direct["construction_mode"], "DIRECT_SEMANTIC")
                    self.assertEqual(direct["language_profile"], "NONE")
                    self.assertEqual(language["semantic_content"], direct["semantic_content"])
                    self.assertEqual(
                        language["equivalence"]["paired_packet_id"],
                        direct["packet_id"],
                    )
                    self.assertEqual(
                        direct["equivalence"]["paired_packet_id"],
                        language["packet_id"],
                    )
                    self.assertEqual(
                        set(language["equivalence"]["required_dimensions"]),
                        EQUIVALENCE_DIMENSIONS,
                    )
                    self.assertEqual(
                        set(direct["equivalence"]["required_dimensions"]),
                        EQUIVALENCE_DIMENSIONS,
                    )
                    self.assertEqual(language["equivalence"]["runtime_status"], "NOT_RUN")
                    self.assertEqual(direct["equivalence"]["runtime_status"], "NOT_RUN")

                for turn in case["turns"]:
                    for packet_id in turn["semantic_packet_ids"]:
                        self.assertIn(packet_id, packet_by_id)
                        packet = packet_by_id[packet_id]
                        self.assertEqual(packet["source_turn_id"], turn["turn_id"])
                        self.assertEqual(packet["dialogue_act"]["semantic_packet_id"], packet_id)

    def test_ambiguity_and_clarification_are_exact_and_non_actuating(self) -> None:
        question = "Which object should I move, and which object should I place it beside?"
        ambiguity = self.cases["ambiguity"]
        self.assertTrue(ambiguity["expected"]["clarification_required"])
        self.assertEqual(ambiguity["expected"]["exact_question"], question)
        self.assertFalse(ambiguity["expected"]["external_action_occurred"])
        self.assertEqual(
            ambiguity["final_state"]["pending_clarification"]["exact_question"],
            question,
        )
        ambiguous_packet = ambiguity["semantic_pairs"][0]["language_packet"]
        self.assertEqual(ambiguous_packet["interpretation_status"], "AMBIGUOUS")
        self.assertEqual(
            ambiguous_packet["kernel_handoff"]["adapter_status"],
            "BLOCKED_AMBIGUITY",
        )
        self.assertEqual(len(ambiguous_packet["ambiguity_candidates"]), 2)

        clarification = self.cases["clarification"]
        self.assertTrue(clarification["expected"]["parent_goal_resumed"])
        self.assertFalse(clarification["expected"]["external_action_occurred"])
        self.assertIsNone(clarification["final_state"]["pending_clarification"])
        self.assertEqual(
            clarification["response_plans"][0]["exact_clarification"]["question_text"],
            question,
        )

    def test_reference_correction_topic_and_memory_expectations_are_source_bound(self) -> None:
        pronoun = self.cases["pronoun_reference"]
        self.assertEqual(pronoun["expected"]["surface_form"], "it")
        self.assertEqual(pronoun["expected"]["resolved_referent_id"], "ref_laptop")
        anaphora = pronoun["semantic_pairs"][0]["language_packet"]["semantic_content"][
            "discourse"
        ]["anaphora"]
        self.assertEqual(anaphora[0]["referent_id"], "ref_laptop")

        correction = self.cases["correction_learning"]
        self.assertEqual(correction["expected"]["durable_memory_write"], "NOT_AUTHORIZED")
        self.assertTrue(correction["expected"]["same_conversation_application"])
        self.assertEqual(
            correction["response_plans"][0]["memory_write"]["proposal_status"],
            "PROPOSED",
        )

        topics = self.cases["topic_switching"]
        self.assertEqual(topics["final_state"]["current_topic"], "topic_laptop")
        self.assertIn("topic_atlas", topics["expected"]["suspended_topics"])
        self.assertEqual(
            {topic["topic_id"] for topic in topics["final_state"]["topic_stack"]},
            {"topic_atlas", "topic_laptop"},
        )

        memory = self.cases["memory_recall"]
        memory_id = memory["expected"]["memory_record_id"]
        self.assertFalse(memory["expected"]["similarity_retrieval_used"])
        self.assertIn(
            memory_id,
            memory["response_plans"][0]["ordered_content_units"][0]["source_refs"],
        )
        admitted_ids = {
            link["memory_record_id"]
            for link in memory["final_state"]["memory_links"]
            if link["use_status"] == "ADMITTED"
        }
        self.assertIn(memory_id, admitted_ids)

    def test_protocol_explicitly_separates_compact_runtime_transport(self) -> None:
        text = PROTOCOL.read_text(encoding="utf-8")
        self.assertIn("cncm.conversation-turn/0.1", text)
        self.assertIn("not directly validated by the six protocol schemas", text)
        self.assertIn("replaceable peripheral", text)
        self.assertIn("must not choose an ambiguous referent", text)
        self.assertIn("runtime equivalence", text)
        self.assertIn("NOT_RUN", text)


if __name__ == "__main__":
    unittest.main()

