"""test_helm_memory.py -- Unit tests for HELM v0.8 Multi-Turn Conversational Memory.

Tests:
1. Turn recording and JSONL persistence.
2. Working memory context updates (files, inventory, goals).
3. Anaphora and pronoun resolution ('it' -> active file).
4. Relative quantity updates ('add 10 water').
5. Meta-queries ('what did we do', 'what is in stock').
6. Bounded FIFO capacity to strictly preserve local memory ceiling.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from helm_memory import (
    ConversationTurn,
    WorkingMemoryContext,
    AnaphoraResolver,
    HELMConversationalMemory
)


class TestHELMConversationalMemory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory = HELMConversationalMemory(
            session_id="test-session-v08",
            max_turns=5,
            storage_dir=self.test_dir
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_record_turn_and_persistence(self):
        t1 = self.memory.record_turn(
            user_raw_text="Check git status.",
            resolved_text="Check git status.",
            intent="GIT_CONTROL",
            entities={},
            helm_response="Git status clean.",
            gate_code="GATE_PASS",
            duration=0.05
        )
        self.assertEqual(len(self.memory.turns), 1)
        self.assertEqual(t1.turn_id, 1)
        self.assertTrue(os.path.exists(self.memory.session_file))

    def test_anaphora_file_resolution(self):
        ctx = self.memory.context
        ctx.update_files(["auth_service.py"])

        raw = "Now run tests on it."
        resolved, entities = AnaphoraResolver.resolve(raw, ctx)
        self.assertIn("auth_service.py", resolved)
        self.assertEqual(entities.get("resolved_file"), "auth_service.py")

    def test_relative_inventory_addition(self):
        ctx = self.memory.context
        ctx.inventory["Flour"] = Decimal("50")

        raw = "Add 25 units of Flour and 10 Water."
        resolved, entities = AnaphoraResolver.resolve(raw, ctx)

        self.assertEqual(ctx.inventory["Flour"], Decimal("75"))
        self.assertEqual(ctx.inventory["Water"], Decimal("10"))

    def test_meta_query_recognition(self):
        ctx = self.memory.context
        _, ent1 = AnaphoraResolver.resolve("What did we just do?", ctx)
        self.assertTrue(ent1.get("query_last_result"))

        _, ent2 = AnaphoraResolver.resolve("What do we have in stock?", ctx)
        self.assertTrue(ent2.get("query_inventory"))

    def test_bounded_fifo_memory_ceiling(self):
        # Configured max_turns is 5
        for i in range(12):
            self.memory.record_turn(
                user_raw_text=f"Turn {i}",
                resolved_text=f"Turn {i}",
                intent="INQUIRY",
                entities={},
                helm_response=f"Response {i}"
            )
        # Verify in-memory turns are bounded at 5
        self.assertEqual(len(self.memory.turns), 5)
        # Oldest turn in memory should be Turn 8 (index 7)
    def test_user_facts_retention_and_summary(self):
        ctx = self.memory.context
        ctx.add_user_fact("My grandfather kept bees in the south of France.")
        self.assertIn("My grandfather kept bees in the south of France", ctx.user_facts)

        ctx.last_goal = "Write a program that counts the hives."
        summary = self.memory.summarize_session_state()
        self.assertIn("My grandfather kept bees in the south of France", summary)
        self.assertIn("'Write a program that counts the hives'.", summary)
        self.assertNotIn(".'", summary)


if __name__ == "__main__":
    unittest.main()
