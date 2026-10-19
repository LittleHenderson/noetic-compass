"""test_helm_end_to_end_loop.py -- tests for the live loop wired to the canonical brain (fixes C and D, 2026-10-18).

Each fix has its own test:
  canonical brain is the default; the 22x40 cookie brain is a demo stand-in only     test_01, test_02, test_03
  no Decimal("10") fill: a mention without an amount is not filled                    test_04
  round trip actually checked; missing checker = NOT_VERIFIED                         test_05, test_06, test_07
  absent ingredient -> RPM gate -> UNDETERMINED / CLARIFY, zero writes                test_08
  the real gate is called with a real GateRequest (no label field)                    test_09
  store write only after gate PROCEED and read-back receipt; success path             test_10
  repair child opened, run, and its ACTUAL result glued back                          test_11
  repair child opened on a REAL DETECTED failure (no planted flag)                     test_12
  valve is a written rule (ENGINEERED-NOT-VALIDATED), essentials from the recipe      test_13
  unparseable English -> CLARIFY, zero writes                                          test_14
  live end-to-end trace                                                                test_18
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_end_to_end_loop as E2E
from helm_end_to_end_loop import HELMEndToEndLoop, HELMVoiceAdapter
from helm_brain_canonical import CanonicalRecipeBrain, LOADED_MEMBERS, TORCH_ONLY_MEMBERS, EXPECTED_FREEZE_SHA256
import tks_meta_valve_controller as VALVE
from tks_meta_valve_controller import TKSMetaValveController


def taught_loop(**kw) -> HELMEndToEndLoop:
    """A loop whose brain has seen two honest Bread batches: Flour needs 2, Water needs 1."""
    loop = HELMEndToEndLoop(**kw)
    a = loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 5, "Flour", tick=1)
    b = loop.witness_batch("Bread", {"Flour": 10, "Water": 2}, 2, "Water", tick=2)
    assert a["loop_status"] == "WITNESS_ADMITTED" and b["loop_status"] == "WITNESS_ADMITTED", (a, b)
    return loop


class TestCanonicalBrainWiring(unittest.TestCase):

    def test_01_canonical_brain_is_station_s0(self):
        loop = HELMEndToEndLoop()
        self.assertIsInstance(loop.brain, CanonicalRecipeBrain)
        prov = loop.brain.provenance()
        self.assertEqual(prov["package_freeze_sha256"], EXPECTED_FREEZE_SHA256)
        self.assertEqual(sorted(prov["members_sha256"]), sorted(LOADED_MEMBERS))
        self.assertEqual(len(loop.brain.ingredients), 8)
        self.assertEqual(loop.brain.support_of("Bread"), ["Flour", "Water"])
        self.assertIsNotNone(loop.cube_store)
        self.assertIsNone(loop.valve.weights_model)

    def test_02_cookie_brain_is_demo_standin_never_default(self):
        import helm_brain_22x40 as demo
        self.assertTrue(hasattr(demo, "DEMO_STANDIN"))
        self.assertFalse(demo.IS_CANONICAL)
        loop = HELMEndToEndLoop()
        self.assertNotIsInstance(loop.brain, demo.DEMO_STANDIN)
        src = inspect.getsource(E2E)
        self.assertNotIn("import helm_brain_22x40", src)
        self.assertNotIn("from helm_brain_22x40", src)

    def test_03_torch_only_parts_not_imported(self):
        HELMEndToEndLoop()
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("numpy", sys.modules)
        for member in TORCH_ONLY_MEMBERS:
            mod = member[:-3].replace("/", ".")
            self.assertNotIn(mod, sys.modules, member)
        self.assertTrue(CanonicalRecipeBrain().provenance()["torch_blocker"]["blocker_installed"])

    def test_04_no_invented_quantity(self):
        loop = HELMEndToEndLoop()
        self.assertEqual(loop.extract_ingredient_quantities("Can we bake with Flour and Water?"), {})
        got = loop.extract_ingredient_quantities("We have 15 units of Flour, 8 Water and no Sugar.")
        self.assertEqual(got, {"Flour": Decimal("15"), "Water": Decimal("8")})
        self.assertNotIn('Decimal("10")', inspect.getsource(E2E))


class TestRoundTrip(unittest.TestCase):

    def test_05_round_trip_checked(self):
        loop = HELMEndToEndLoop()
        ok = loop.verify_cce_round_trip("There is 12 of Ω_Flour.")
        self.assertTrue(ok["verified"])
        self.assertTrue(ok["parse_render_parse_equal"])
        self.assertEqual(ok["content_hash_in"], ok["content_hash_out"])
        bad = loop.verify_cce_round_trip("What is going on with the project today?")
        self.assertFalse(bad["verified"])
        self.assertTrue(bad["rejection"].startswith("CCE_PARSE_REFUSED"))

    def test_06_round_trip_mismatch_refuses_with_zero_writes(self):
        loop = HELMEndToEndLoop()
        real_render = E2E.cce.render

        def lying_render(content, rng=None):         # renders a different amount than the content holds
            return real_render(content, rng).replace("12", "13")

        with mock.patch.object(E2E.cce, "render", lying_render):
            res = loop.process_turn("There is 12 of Ω_Flour.", tick=1)
        self.assertEqual(res["loop_status"], "CLARIFY_ROUND_TRIP_FAILED")
        self.assertEqual(res["cubes_written"], [])
        self.assertEqual(loop.cube_store.write_history, [])
        self.assertEqual(loop.stock, {})

    def test_07_missing_checker_is_not_verified(self):
        loop = HELMEndToEndLoop()
        with mock.patch.object(E2E, "cce", None):
            self.assertFalse(loop.verify_cce_round_trip("There is 12 of Ω_Flour.")["verified"])
            res = loop.process_turn("There is 12 of Ω_Flour.", tick=1)
        self.assertEqual(res["loop_status"], "REFUSE_NOT_VERIFIED")
        self.assertEqual(res["cubes_written"], [])


class TestCircuit(unittest.TestCase):

    def test_08_absent_ingredient_is_undetermined(self):
        loop = taught_loop()
        loop.process_turn("There is 12 of Ω_Flour.", tick=3)
        writes = len(loop.cube_store.write_history)
        res = loop.process_turn("Topic: Ω_Bread.", tick=4)
        self.assertEqual(res["loop_status"], "UNDETERMINED_CLARIFY")
        self.assertEqual(res["gate_verdict"]["verdict"], "REPAIR")
        self.assertEqual(res["gate_verdict"]["gap"], "the stock of Ω_Water")
        self.assertIsNone(res["output_value"])
        self.assertIsNone(res["recipe_receipt"])
        self.assertEqual(res["cubes_written"], [])
        self.assertEqual(len(loop.cube_store.write_history), writes)
        self.assertNotIn("Water", loop.stock)
        self.assertEqual(res["valve_telemetry"]["gate_interlock"], "G-ABSENT")
        self.assertIn("Water", res["response"])
        self.assertEqual(res["repair"]["outcome"], "CHILD_REFUSED")

    def test_09_real_gate_called_with_real_request(self):
        loop = taught_loop()
        seen = []
        real = E2E.RPM.rpm_gate

        def spy(request):
            seen.append(request)
            return real(request)

        with mock.patch.object(E2E.RPM, "rpm_gate", spy):
            loop.process_turn("There is 12 of Ω_Flour. There is 9 of Ω_Water.", tick=3)
            loop.process_turn("Topic: Ω_Bread.", tick=4)
        self.assertGreaterEqual(len(seen), 2)
        for request in seen:
            self.assertIsInstance(request, E2E.GateRequest)
            names = tuple(f.name for f in __import__("dataclasses").fields(request))
            self.assertEqual(names, E2E.RPM.GATE_REQUEST_FIELDS)
            self.assertNotIn("label", names)

    def test_10_success_writes_only_after_gate_and_receipt(self):
        loop = taught_loop()
        loop.process_turn("There is 12 of Ω_Flour.", tick=3)
        loop.process_turn("There is 9 of Ω_Water.", tick=4)
        res = loop.process_turn("Topic: Ω_Bread.", tick=5)
        self.assertEqual(res["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(res["output_value"], "6")
        self.assertEqual(res["limiting_reagent"], "Flour")
        self.assertEqual(res["gate_verdict"]["verdict"], "PROCEED")
        self.assertTrue(res["recipe_receipt"]["eta_eps_read_back"]["pass"])
        self.assertEqual(res["cubes_written"], ["yield_bread_t5"])
        self.assertTrue(res["cube_receipt"]["read_back_ok"])
        self.assertEqual(loop.cube_store.nodes["yield_bread_t5"].provenance.source, "CHECKED")
        stations = [r["station"] for r in loop.trace if r["tick"] == 5]
        for name in ("CCE skin", "S0 atlas head", "S1 trigger ^8", "S2 Bias ^5", "S3 arrival ^9",
                     "S4 operating point", "S5 RPM link", "brain", "store", "S6 next"):
            self.assertIn(name, stations)
        self.assertLess(stations.index("S5 RPM link"), stations.index("brain"))
        self.assertLess(stations.index("brain"), stations.index("store"))

    def test_11_repair_child_glues_actual_result(self):
        first = taught_loop()
        first.process_turn("There is 9 of Ω_Water.", tick=3)
        later = HELMEndToEndLoop(cube_store=first.cube_store, brain=first.brain)
        later.process_turn("There is 20 of Ω_Flour.", tick=4)
        res = later.process_turn("Topic: Ω_Bread.", tick=5)
        self.assertEqual(res["repair"]["outcome"], "REPAIRED")
        self.assertEqual(res["repair"]["glued"], {"Water": "9"})
        whats = [line["what"] for line in res["repair"]["ledger"]]
        self.assertEqual(whats[:3], ["parent_gate", "depth_check", "child_run"])
        self.assertIn("parent_gate_after_glue", whats)
        self.assertEqual(res["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(res["output_value"], "9")
        self.assertEqual(res["limiting_reagent"], "Water")

    def test_12_repair_opens_on_real_detected_failure(self):
        loop = taught_loop()
        digest_before = loop.brain.brain.learned_digest()
        writes = len(loop.cube_store.write_history)
        gate_requests = []
        real = E2E.RPM.rpm_gate

        def spy(request):
            gate_requests.append(request)
            return real(request)

        with mock.patch.object(E2E.RPM, "rpm_gate", spy):
            # Same stock as batch 1, but 4 made instead of 5: Flour per Bread would be 5/2, the brain holds 2.
            res = loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 4, "Flour", tick=3)
        self.assertEqual(res["loop_status"], "CONFLICT_UNDETERMINED")
        detected = res["repair"]["detected"]
        self.assertEqual(detected["reason"], "REFUSED_CONFLICT")                 # the brain's writer said so
        self.assertEqual(detected["candidate"], "refused_conflict")
        self.assertEqual(detected["detail"], {"old": "2/1", "new": "5/2"})
        self.assertIn("rb2.writer_b.teach_step_b", detected["detected_by"])
        # The cause the gate read was built from the detection, not passed in by this test.
        causes = [r.cause.unsatisfied for r in gate_requests]
        self.assertIn(("a requirement of Ω_Flour for Ω_Bread that agrees with every witnessed batch",), causes)
        self.assertEqual(res["gate_verdict"]["verdict"], "REPAIR")
        whats = [line["what"] for line in res["repair"]["ledger"]]
        self.assertIn("child_run", whats)
        child = [line for line in res["repair"]["ledger"] if line["what"] == "child_run"][0]
        self.assertFalse(child["ok"])
        self.assertIn("REFUSED_CONFLICT", child["detail"])
        self.assertEqual(res["repair"]["outcome"], "CHILD_REFUSED")
        self.assertEqual(res["cubes_written"], [])
        self.assertEqual(len(loop.cube_store.write_history), writes)
        self.assertEqual(loop.brain.brain.learned_digest(), digest_before)
        # Control: a batch that agrees with the brain is admitted and opens no repair.
        ok = loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 5, "Flour", tick=4)
        self.assertEqual(ok["loop_status"], "WITNESS_ADMITTED")
        self.assertIsNone(ok["repair"])
        # Nothing in the source plants the failure: there is no flag the test or loop sets to fake it.
        src = inspect.getsource(HELMEndToEndLoop.witness_batch)
        self.assertNotIn("planted", src.lower())


class TestValveRule(unittest.TestCase):

    def test_13_written_rule(self):
        self.assertIn("ENGINEERED-NOT-VALIDATED", VALVE.__doc__)
        self.assertEqual(VALVE.STATUS_WORD, "ENGINEERED-NOT-VALIDATED")
        src = inspect.getsource(VALVE)
        self.assertNotIn("json.load", src)
        self.assertNotIn("math.exp", src)
        self.assertNotIn('"Flour"', src.split("def self_test")[0])
        valve = TKSMetaValveController(default_aperture="0.75",
                                       weights_path=os.path.join(HERE, "tks_meta_valve_weights_v0_4.json"))
        self.assertIsNone(valve.weights_model)
        ok, t = valve.evaluate_reagents(1, "Meringue", ["Sugar", "Egg", "Salt"], ["Sugar", "Egg", "Salt"])
        self.assertTrue(ok)
        self.assertEqual(t.aperture_sigma, Decimal("0.75"))
        ok, t = valve.evaluate_reagents(2, "Meringue", ["Sugar", "Egg", "Salt"], ["Sugar", "Egg"])
        self.assertFalse(ok)
        self.assertEqual((t.gate_interlock, t.missing_reagents, t.aperture_sigma), ("G-ABSENT", ["Salt"], Decimal("0")))
        ok, t = valve.evaluate_reagents(3, "Meringue", ["Sugar"], ["Sugar"], noise_level="HIGH")
        self.assertEqual((ok, t.gate_interlock), (False, "G-LIMIT"))
        ok, t = valve.evaluate_reagents(4, "Unknown", [], ["Sugar"])
        self.assertEqual((ok, t.gate_interlock), (False, "G-ABSENT"))
        self.assertTrue(os.path.exists(os.path.join(HERE, "tks_meta_valve_weights_v0_4.json")))  # kept as history


class TestEdges(unittest.TestCase):

    def test_14_unparseable_english_clarifies_with_zero_writes(self):
        loop = HELMEndToEndLoop()
        for text in ("How much bread could we bake with whatever is around?", "We have 50 Flour and 30 Sugar.",
                     "I have an affinity for the offer."):
            res = loop.process_turn(text, tick=1)
            self.assertEqual(res["loop_status"], "CLARIFY_NOT_CCE", text)
            self.assertEqual(res["cubes_written"], [], text)
        self.assertEqual(loop.cube_store.write_history, [])

    def test_15_stated_recipe_not_taken(self):
        loop = HELMEndToEndLoop()
        res = loop.process_turn("To make Ω_Bread, use 2 of Ω_Flour; plus 1 of Ω_Water.", tick=1)
        self.assertEqual(res["loop_status"], "STATED_RECIPE_NOT_TAKEN")
        self.assertEqual(res["cubes_written"], [])
        self.assertEqual(loop.brain.unlearned("Bread"), ["Flour", "Water"])

    def test_16_pantry_read_writes_nothing(self):
        loop = HELMEndToEndLoop()
        loop.process_turn("There is 50 of Ω_Flour. There is 30 of Ω_Sugar. There is 20 of Ω_Butter.", tick=1)
        res = loop.process_turn("list what is in the pantry", tick=2)
        self.assertEqual(res["loop_status"], "READ_COMPLETED")
        self.assertEqual(res["cubes_written"], [])
        self.assertIn("50 Flour", res["response"])
        self.assertIn("20 Butter", res["response"])

    def test_17_kept_paths_and_voice(self):
        loop = HELMEndToEndLoop()
        res = loop.process_turn("What is the quantum temperature of a Tuesday electron sandwich?", tick=1)
        self.assertEqual(res["loop_status"], "CLARIFY_REFUSAL")
        res = loop.process_turn("Audit the local environment and verify tests.", tick=2)
        self.assertEqual(res["loop_status"], "AGENTIC_PLAN_EXECUTED")
        msg = HELMVoiceAdapter.format_success("Bread", "13/2", "Flour", "a1b2c3d4e5f60718")
        self.assertIn("6.5 Bread", msg)
        self.assertIn("Flour runs out first", msg)

    def test_18_live_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trace.jsonl")
            out = E2E.run_live_trace(path)
            statuses = [t["loop_status"] for t in out["turns"]]
            self.assertEqual(statuses, ["WITNESS_ADMITTED", "WITNESS_ADMITTED", "INVENTORY_RECORDED",
                                        "UNDETERMINED_CLARIFY", "CLARIFY_NOT_CCE", "INVENTORY_RECORDED",
                                        "SUCCESS_EVALUATED", "CONFLICT_UNDETERMINED", "INVENTORY_RECORDED",
                                        "SUCCESS_EVALUATED"])
            with open(path, encoding="utf-8") as fh:
                records = [json.loads(line) for line in fh]
            stations = {r["station"] for r in records}
            for name in ("header", "user", "CCE skin", "S0 atlas head", "S1 trigger ^8", "S2 Bias ^5",
                         "S3 arrival ^9", "S4 operating point", "S5 RPM link", "brain", "store", "S6 next"):
                self.assertIn(name, stations)
            self.assertEqual(len(out["sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
