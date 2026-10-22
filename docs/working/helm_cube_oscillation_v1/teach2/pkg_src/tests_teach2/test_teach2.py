"""Package tests of TEACH-2 (standard library only; no HELM run, no GPU). Run from the package root:
    python -X utf8 -B -m unittest discover -s tests_teach2 -t .
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from teach2 import common_t2 as C
from teach2 import exam_t2 as E
from teach2 import reader_t2 as R
from teach2 import seed_rule_t2 as SR
from teach2 import turns_t2 as T
from teach2 import worlds_t2 as W

PRACTICE = SR.practice_seeds()


def _worlds(n=4):
    return W.build_all(PRACTICE["WORLD"], n)


class FrozenAndPins(unittest.TestCase):
    def test_frozen_file_equals_common(self):
        frozen = C.frozen()
        for k, v in frozen.items():
            if k in ("schema", "HELM_CUT_COMMIT"):
                continue
            self.assertEqual(json.loads(json.dumps(getattr(C, k), default=str)), v, k)

    def test_ctt_weights_match_their_pins(self):
        self.assertTrue(C.check_ctt()["ok"])

    def test_helm_cut_matches_its_contract(self):
        self.assertTrue(C.check_helm_cut()["ok"])

    def test_disjoint_check_holds(self):
        self.assertTrue(C.read_json(C.PKG / "contract" / "DISJOINT_CHECK_TEACH2.json")["ok"])

    def test_arm_tables_agree(self):
        self.assertEqual(set(C.ARM_SET), set(C.ARMS))
        self.assertEqual(len(C.ARMS), 11)
        for a in C.CUBE_ARMS + C.CTT_ARMS + C.RULE_ARMS + C.REPORTED_ARMS:
            self.assertIn(a, C.ARMS)
        self.assertEqual(sum(C.PLAN_COUNTS.values()), C.TEACHING_TURNS)


class Plan(unittest.TestCase):
    def test_every_world_has_the_frozen_plan(self):
        for w in _worlds():
            plan = W.teaching_plan(w, PRACTICE["WORLD"], PRACTICE["TRAP"])
            kinds = [s["kind"] for s in plan]
            for k, n in C.PLAN_COUNTS.items():
                self.assertEqual(kinds.count(k), n, (w["world_id"], k))
            roles = [s["trap_role"] for s in plan if s["kind"] == "TRAP"]
            self.assertEqual(sorted(roles), ["FIRST", "FIRST", "RESTATE", "RESTATE"])
            first = {s["fact_id"]: s["turn_index"] for s in plan
                     if s["kind"] in ("FACT", "UNKNOWN") or (s["kind"] == "TRAP" and s["trap_role"] == "FIRST")}
            self.assertEqual(set(first), {f["id"] for f in w["facts"]})
            for s in plan:
                if s["kind"] in ("FIX", "RESTATE") or (s["kind"] == "TRAP" and s["trap_role"] == "RESTATE"):
                    self.assertGreater(s["turn_index"], first[s["fact_id"]])

    def test_trap_keeps_the_true_value_and_a_different_decoy(self):
        for w in _worlds():
            facts = {f["id"]: f for f in w["facts"]}
            for s in W.teaching_plan(w, PRACTICE["WORLD"], PRACTICE["TRAP"]):
                if s["kind"] != "TRAP":
                    continue
                f = facts[s["fact_id"]]
                self.assertIn(f["value"], s["text"])
                self.assertFalse(f["unknown"])
                self.assertNotIn("fix", f)
                if s["trap"]["decoy"]:
                    self.assertNotEqual(s["trap"]["decoy"], f["value"])

    def test_practice_turns_pass_the_checker(self):
        ws = _worlds(2)
        for w in ws:
            plan = W.teaching_plan(w, PRACTICE["WORLD"], PRACTICE["TRAP"])
            rep = T.check_turns(w, T.practice_turns(w, plan, PRACTICE["WORLD"]), sealed=False, split={})
            self.assertTrue(rep["ok"], rep)
            self.assertEqual(rep["traps"], 4)

    def test_sealed_checker_refuses_rule_written_turns(self):
        w = _worlds(1)[0]
        plan = W.teaching_plan(w, PRACTICE["WORLD"], PRACTICE["TRAP"])
        rep = T.check_turns(w, T.practice_turns(w, plan, PRACTICE["WORLD"]), sealed=True, split=T.split_hashes([w]))
        self.assertFalse(rep["ok"])

    def test_checker_refuses_a_missing_trap(self):
        w = _worlds(1)[0]
        plan = W.teaching_plan(w, PRACTICE["WORLD"], PRACTICE["TRAP"])
        turns = T.practice_turns(w, plan, PRACTICE["WORLD"])
        for t in turns:
            if t["kind"] == "TRAP":
                t["kind"] = "FACT"
                break
        self.assertFalse(T.check_turns(w, turns, sealed=False, split={})["ok"])

    def test_exam_carrier_round_trip_and_offline(self):
        with tempfile.TemporaryDirectory() as d:
            E.build_exam(PRACTICE, d, practice=True, count=3)
            ex = E.load_exam(d)
            self.assertTrue(ex["practice_mock"])
            self.assertEqual(set(ex["offline"].values()) <= set(C.QUIZZES), True)
            self.assertTrue(E.check_exam(ex)["all_ok"])


class Seeds(unittest.TestCase):
    def test_bands_are_above_every_used_range_and_disjoint(self):
        top = max(hi for _n, _lo, hi in C.USED_RANGES)
        spans = sorted(C.BANDS.values())
        self.assertGreater(spans[0][0], top + C.SEED_GAP - 1)
        for (a_lo, a_hi), (b_lo, _b_hi) in zip(spans, spans[1:]):
            self.assertGreater(b_lo, a_hi)
        self.assertLess(spans[-1][1], C.INT32_MAX)

    def test_derive_is_deterministic_and_in_band(self):
        z = "a" * 64
        d1, d2 = SR.derive("CUBE EXAM at 1 USD", z), SR.derive("CUBE EXAM at 1 USD", z)
        self.assertEqual(d1, d2)
        self.assertEqual(d1["overlap_check"], "PASS")
        for p, (lo, hi) in C.BANDS.items():
            self.assertTrue(lo <= d1[p] <= hi)


class Scoring(unittest.TestCase):
    def setUp(self):
        self.world = _worlds(1)[0]
        self.item = {"kind": "TAUGHT", "slot": "count", "value": "eight"}

    def test_current_value_rule(self):
        world = {"values": {"count": ["eight", "two"], "person": [], "place": []}}
        for reply, want in (("It was eight.", "RIGHT"), ("Eight, not two.", "RIGHT"), ("It was eight, instead of two.", "RIGHT"),
                            ("Eight. It used to be two.", "RIGHT"), ("Eight; two was replaced.", "RIGHT"),
                            ("It was eight; it was two before.", "RIGHT"), ("It was two.", "WRONG"),
                            ("Eight or two.", "WRONG"), ("Which one do you mean?", "ASK"),
                            ("I don't remember.", "UNKNOWN_SAID")):
            self.assertEqual(R.score_answer(reply, self.item, world), want, reply)

    def test_replaced_patterns(self):
        self.assertTrue(R.replaced("not two", "2"))
        self.assertTrue(R.replaced("it was two before", "2"))
        self.assertTrue(R.replaced("earlier i said two", "2"))
        self.assertFalse(R.replaced("two buses", "2"))

    def test_label_check(self):
        rows = [{"label": "EXACT", "exact_now": True, "verbatim": True, "where": "live", "cloud_online": True},
                {"label": "EXACT", "exact_now": False, "verbatim": True, "where": "cloud", "cloud_online": False},
                {"label": "RECONSTRUCTED", "exact_now": False, "verbatim": True, "where": "cloud", "cloud_online": False},
                {"label": "RECONSTRUCTED", "exact_now": True, "verbatim": True, "where": "device", "cloud_online": True}]
        served, ok, bad, offline = R.label_check(rows)
        self.assertEqual((served, ok, len(bad), offline), (4, 2, 2, 1))

    def test_number_scan(self):
        self.assertEqual(R._scan_numbers([{"c": ["yard", "colonies"], "q": "12ab"}]), [])
        self.assertEqual(R._scan_numbers([{"c": ["yard", "eight"]}]), ["eight"])
        self.assertEqual(R._scan_numbers([{"cas": {"notation": "^1^C + ^4^E", "sentence": "you intake yard 12"}}]), ["12"])

    def test_cube_rows_wrong_and_revision(self):
        w = self.world
        f = next(x for x in w["facts"] if x["kind"] == "count" and not x["unknown"] and not x.get("fix"))
        u = {"turns": [{"turn_id": 1, "kind": "FACT", "fact_id": f["id"]}, {"turn_id": 2, "kind": "SMALL", "fact_id": None}],
             "refresh": [], "quiz": [],
             "branches_end": [
                 {"branch_id": "b1", "source": "thing_" + f["unit"].lower(), "target": "thing_x",
                  "commonality": {"kind": "colonies yard", "referent": f["value"], "amount": f["value"]}, "provenance_refs": ["turn:1"]},
                 {"branch_id": "b2", "source": "thing_y", "target": "thing_z",
                  "commonality": {"kind": "k", "referent": "q"}, "provenance_refs": ["turn:2"]}],
             "branch_snapshots": [["b1"], ["b1", "b2"]], "osc_log": [{"rounds": 2, "kept": True}]}
        c = R.cube_rows(u, w)
        self.assertEqual((c["CUBES_STORED"], c["CUBES_WRONG"]), (2, 1))
        self.assertTrue(c["REVISION_OK"])
        u["branch_snapshots"] = [["b1", "b2"], ["b2"]]
        self.assertFalse(R.cube_rows(u, w)["REVISION_OK"])

    def test_limit_stretch_rule(self):
        u = {"compactions": {}, "receipts_end": [], "refresh": [], "bytes_log": [
            {"working_bytes": 900}, {"working_bytes": 1100, "flags_raised": ["BATCH_NO_GAIN"]},
            {"working_bytes": 1200, "flags_raised": []}, {"working_bytes": 900}, {"working_bytes": 1300, "flags_raised": []},
            {"working_bytes": 1300, "flags_raised": ["MOVE_FAILED"]}]}
        self.assertEqual(R.mem_rows(u, 1000)["LIMIT_UNEXPLAINED"], 2)


class Limits(unittest.TestCase):
    def test_limit_rule(self):
        from teach2 import run_t2
        with tempfile.TemporaryDirectory() as d:
            for w, b in (("W01", 5022), ("W02", 4800), ("W03", 6100)):
                C.write_json(Path(d) / f"UNIT_VERBATIM_ONLY_{w}.json", {"phase_marks": {"Q_REFRESHED": {"working_bytes": b}}})
            lim = run_t2.limits_from_verbatim(Path(d), ["W01", "W02", "W03"])
            self.assertEqual((lim["working_limit_bytes"], lim["device_limit_bytes"]), (2500, 2500))


class CTTClientBatching(unittest.TestCase):
    def test_three_copies_share_one_request_per_round(self):
        from teach2 import ctt_client
        cl = ctt_client.CTTClient.__new__(ctt_client.CTTClient)
        cl.died, cl._pending_text, cl._pending, cl._consumed = False, None, {}, set()
        calls = []
        cl._ask = lambda copies, texts: calls.append((tuple(copies), tuple(texts))) or {c: ["x"] for c in copies}
        for _round in range(2):
            for c in C.VOTING_COPIES:
                cl.read(c, "line")
        self.assertEqual(len(calls), 2)          # one request per round, never cached across rounds
        cl.read(C.VOTING_COPIES[0], "other")
        self.assertEqual(len(calls), 3)

    def test_dead_server_gives_no_reading(self):
        from teach2 import ctt_client
        cl = ctt_client.CTTClient.__new__(ctt_client.CTTClient)
        cl.died, cl._pending_text, cl._pending, cl._consumed = True, None, {}, set()
        cl.requests, cl.lines = 0, 0
        self.assertEqual(cl.read(C.VOTING_COPIES[0], "line"), "")


if __name__ == "__main__":
    unittest.main()
