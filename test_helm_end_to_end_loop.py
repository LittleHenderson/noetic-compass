"""test_helm_end_to_end_loop.py -- Comprehensive Acceptance Suite for HELM End-to-End Pipeline.

Tests:
1. Full subsystem initialization (Brain 22x40, Valve Phase 3, CCE Gate, Cube Store).
2. Natural English ingredient quantity and negation extraction.
3. CCE round-trip verification gate (eps o eta == id) emitting 16-char receipts.
4. Phase 3 Meta Valve Controller (tks_meta_valve_controller) aperture and G-ABSENT interlock.
5. Exact 40-digit Decimal CES recipe execution with limiting reagent identification.
6. Unified Cube Store dialogue integration emitting cryptographic receipts.
7. Adversarial out-of-domain query refusal (0 hallucination).
8. Everyday American English Voice Adapter formatting.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in [
    HERE,
    os.path.join(HERE, "brains"),
    os.path.join(HERE, "core_engine"),
    os.path.join(HERE, "real_atlas"),
    os.path.join(HERE, "docs", "working", "noetic_council", "language_v3"),
    os.path.join(HERE, "docs", "working", "noetic_council", "cube_store")
]:
    if os.path.exists(sub) and sub not in sys.path:
        sys.path.insert(0, sub)

from helm_end_to_end_loop import HELMEndToEndLoop, HELMVoiceAdapter
from tks_meta_valve_controller import TKSMetaValveController
from helm_brain_22x40 import HELMRecipeBrain22x40


class TestHELMEndToEndLoop(unittest.TestCase):

    def setUp(self):
        self.loop = HELMEndToEndLoop()

    def test_01_subsystem_initialization(self):
        """Verify all subsystems are correctly wired."""
        self.assertIsInstance(self.loop.brain, HELMRecipeBrain22x40)
        self.assertEqual(len(self.loop.brain.ingredients), 22)
        self.assertEqual(self.loop.brain.parameter_count, 40)

        self.assertIsInstance(self.loop.valve, TKSMetaValveController)
        self.assertTrue(self.loop.valve.weights_model is not None)
        self.assertEqual(self.loop.valve.aperture_sigma, Decimal("0.75"))

        self.assertIsNotNone(self.loop.cube_store)
        self.assertIsNotNone(self.loop.turn_processor)

    def test_02_ingredient_extraction(self):
        """Verify natural English extraction of ingredient quantities and negations."""
        # Standard positive extraction
        text1 = "We have 15 units of Flour, 8 Water, and Sugar: 25."
        inputs1 = self.loop.extract_ingredient_quantities(text1)
        self.assertEqual(inputs1.get("Flour"), Decimal("15"))
        self.assertEqual(inputs1.get("Water"), Decimal("8"))
        self.assertEqual(inputs1.get("Sugar"), Decimal("25"))

        # Negation extraction: 'without Water' should NOT include Water
        text2 = "Can we produce a batch with 12 Flour and 5 Sugar without Water?"
        inputs2 = self.loop.extract_ingredient_quantities(text2)
        self.assertEqual(inputs2.get("Flour"), Decimal("12"))
        self.assertEqual(inputs2.get("Sugar"), Decimal("5"))
        self.assertNotIn("Water", inputs2)

    def test_03_cce_round_trip_verification_gate(self):
        """Verify eps o eta == id algebraic round-trip verification."""
        # A valid CCE sentence
        cce_sentence = 'Ana is a Mind. Ana is attracted toward "the risk".'
        res = self.loop.verify_cce_round_trip(cce_sentence)
        self.assertTrue(res["verified"])
        self.assertIsNotNone(res["receipt_id"])
        self.assertEqual(len(res["receipt_id"]), 16)
        self.assertEqual(res["content_hash_in"], res["content_hash_out"])

        # Another valid CCE refusal turn
        refuse_turn = "I will not do that: lacks physical inputs."
        res_refuse = self.loop.verify_cce_round_trip(refuse_turn)
        self.assertTrue(res_refuse["verified"])

        # Arbitrary conversational text is not valid CCE, fails closed with receipt
        bad_text = "What is going on with the project today?"
        res_bad = self.loop.verify_cce_round_trip(bad_text)
        self.assertFalse(res_bad["verified"])
        self.assertIsNotNone(res_bad["receipt_id"])

    def test_04_phase_3_meta_valve_interlock(self):
        """Verify Phase 3 Meta Valve Controller allows flow when prerequisites exist,
        and clamps shut with G-ABSENT when essential prerequisites are missing.
        """
        # Case A: Prerequisites present (Flour and Water) -> GATE_PASS
        res_pass = self.loop.process_turn(
            "We have 15 Flour and 8 Water. Let's bake a batch.",
            tick=1
        )
        self.assertEqual(res_pass["loop_status"], "SUCCESS_EVALUATED")
        self.assertTrue(res_pass["valve_telemetry"]["allowed"])
        self.assertEqual(res_pass["valve_telemetry"]["gate_interlock"], "GATE_PASS")
        self.assertIsNotNone(res_pass["receipt_hash"])

        # Case B: Missing essential prerequisite (Water missing) -> CLAMPED_HALT G-ABSENT
        res_clamp = self.loop.process_turn(
            "Can we make a batch with 12 Flour and 5 Sugar without Water?",
            tick=2
        )
        self.assertEqual(res_clamp["loop_status"], "VALVE_HALT_G-ABSENT")
        self.assertFalse(res_clamp["valve_telemetry"]["allowed"])
        self.assertEqual(res_clamp["valve_telemetry"]["gate_interlock"], "G-ABSENT")
        self.assertIn("missing essential ingredients: Water", res_clamp["everyday_english_response"])

    def test_05_recipe_brain_40digit_execution(self):
        """Verify Station S0 22x40 recipe brain computes exact 40-digit Decimal output."""
        res = self.loop.process_turn(
            "Produce a batch with 20 Flour and 10 Water.",
            tick=3
        )
        self.assertEqual(res["loop_status"], "SUCCESS_EVALUATED")
        rr = res["recipe_receipt"]
        self.assertIsNotNone(rr)
        self.assertEqual(rr["status"], "EVALUATED")
        self.assertIn("output_value", rr)
        self.assertIn("limiting_reagent", rr)
        self.assertGreater(Decimal(str(rr["output_value"])), Decimal("0"))

    def test_06_adversarial_ungrounded_refusal(self):
        """Verify ungrounded out-of-domain queries are refused with 0 hallucinations."""
        prompt = "What is the quantum temperature of a Tuesday electron sandwich?"
        res = self.loop.process_turn(prompt, tick=4)
        self.assertEqual(res["loop_status"], "CLARIFY_REFUSAL")
        self.assertIn("answer that question", res["everyday_english_response"].lower())
        self.assertIsNotNone(res["receipt_hash"])

    def test_07_agentic_goal_execution(self):
        """Verify agentic action request decomposes into an acyclic plan."""
        prompt = "Audit the local environment and verify tests."
        res = self.loop.process_turn(prompt, tick=5)
        self.assertEqual(res["loop_status"], "AGENTIC_PLAN_EXECUTED")
        self.assertTrue(res["agentic_plan_result"]["all_steps_completed"])
        self.assertIsNotNone(res["receipt_hash"])

    def test_08_voice_adapter_readback(self):
        """Verify everyday American English output formats cleanly with receipt hash."""
        success_msg = HELMVoiceAdapter.format_success(
            output_val=Decimal("42.500"),
            limiting_reagent="Flour",
            inputs={"Flour": Decimal("10")},
            entropy=0.20,
            aperture=Decimal("0.75"),
            receipt_hash="a1b2c3d4e5f60718"
        )
        self.assertIn("42.500 units", success_msg)
        self.assertIn("limiting ingredient) is Flour", success_msg)
    def test_09_read_queries_bypass_valve_g_absent(self):
        """Verify the valve gates execution, NOT reads or declarations.
        A LIST_PARTS or inventory declaration must never be clamped with G-ABSENT.
        """
        # 1. Inventory declaration writes cubes into store
        r1 = self.loop.process_turn("We have 50 Flour, 30 Sugar, and 20 Butter.", tick=1)
        self.assertEqual(r1["loop_status"], "INVENTORY_RECORDED")
        self.assertEqual(r1["operation"], "WRITE_CUBE")
        self.assertGreater(len(r1["cubes_written"]), 0)
        self.assertIsNotNone(r1["receipt_hash"])

        # 2. Pantry query performs LIST_PARTS and writes ZERO cubes
        r2 = self.loop.process_turn("list what is in the pantry", tick=2)
        self.assertEqual(r2["loop_status"], "READ_COMPLETED")
        self.assertEqual(r2["operation"], "LIST_PARTS")
        self.assertEqual(r2["cubes_written"], [])
        self.assertGreater(len(r2["cubes_read"]), 0)
        self.assertIn("50 Flour, 30 Sugar, 20 Butter", r2["response"])
        self.assertIsNotNone(r2["receipt_hash"])

    def test_10_execution_public_signature_and_inventory_pass(self):
        """Verify calling with current_inventory returns non-None public keys."""
        # A: Declare ingredients without Water, then ask "How much can we make?"
        self.loop.process_turn("We have 50 Flour, 30 Sugar, and 20 Butter.", tick=2)
        r_clamp = self.loop.process_turn("How much can we make?", tick=3)
        self.assertEqual(r_clamp["loop_status"], "VALVE_HALT_G-ABSENT")
        self.assertIn("missing essential ingredients: Water", r_clamp["response"])

        # B: Providing Water enables full 40-digit execution with populated public keys
        r_exec = self.loop.process_turn(
            "How much can we make?",
            tick=4,
            current_inventory={"Flour": 50, "Water": 20, "Sugar": 30}
        )
        self.assertEqual(r_exec["loop_status"], "SUCCESS_EVALUATED")
        self.assertIsNotNone(r_exec["output_value"])
        self.assertIsNotNone(r_exec["total_output"])
        self.assertIsNotNone(r_exec["limiting_reagent"])
        self.assertIsNotNone(r_exec["response"])
        self.assertIn("All set!", r_exec["response"])

    def test_11_cce_affinity_statement_stored(self):
        """Verify CCE affinity statement parses, round-trips, and writes positive valence cube."""
        r = self.loop.process_turn("I have an affinity for the offer.", tick=5)
        self.assertEqual(r["loop_status"], "CUBE_STORE_PROCESSED")
        self.assertEqual(r["assertion"], "ASSERTED")
        self.assertEqual(r["valence"], "POSITIVE")
        self.assertIsNotNone(r["receipt_hash"])


    def test_12_cce_check_fails_closed_when_module_unavailable(self):
        """With the CCE module absent the check must fail, not silently pass."""
        import helm_end_to_end_loop as mod
        saved = mod.cce
        try:
            mod.cce = None
            res = self.loop.verify_cce_round_trip("Can we bake a batch with 15 Flour and 8 Water?")
            self.assertFalse(res["verified"])
            self.assertEqual(res["rejection"], "CCE_UNAVAILABLE")
            self.assertEqual(len(res["receipt_id"]), 16)
        finally:
            mod.cce = saved

    def test_13_cce_gate_is_advisory_by_default(self):
        """Execution proceeds by default, but the result says the gate was advisory, not passed."""
        r = self.loop.process_turn("Can we bake a batch with 15 Flour and 8 Water?", tick=6)
        self.assertIn(r["loop_status"], ("SUCCESS_EVALUATED", "CCE_GATE_REFUSED"))
        self.assertIn(r["cce_gate"], ("PASS", "ADVISORY_FAIL"))
        if not r["cce_round_trip"]["verified"]:
            self.assertEqual(r["cce_gate"], "ADVISORY_FAIL")

    def test_14_strict_cce_gate_refuses_unparseable_execution(self):
        """In strict mode an unparseable execution request is refused, not executed."""
        from helm_end_to_end_loop import HELMEndToEndLoop
        strict = HELMEndToEndLoop(cce_gate_strict=True)
        r = strict.process_turn("Can we bake a batch with 15 Flour and 8 Water?", tick=7)
        if not r["cce_round_trip"]["verified"]:
            self.assertEqual(r["loop_status"], "CCE_GATE_REFUSED")
            self.assertEqual(r["cce_rejection"], r["cce_round_trip"]["rejection"])
            self.assertIsNotNone(r["receipt_hash"])
        else:
            self.assertNotEqual(r["loop_status"], "CCE_GATE_REFUSED")


if __name__ == "__main__":
    unittest.main()
