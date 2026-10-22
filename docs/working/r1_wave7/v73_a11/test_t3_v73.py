"""test_t3_v73.py -- DESIGN_V73_A11.md T3 as assertions (fix round 2026-10-21, reviewer G-1): runs t3_score_v73.py ONCE (three
fresh v9 extracts: pkg_v72, pkg_v73r, pkg_v73; the design's 13 frozen items; the package's own unit runner on X7_REAL
CHAT_ON and LOOP_ON; the package's real score_w7.score_real with A-R1W7-11) and asserts the design's pass condition and the
section 6 step 3 STOP rule, each as its own test:
  1. no WRONG lesson and no WRONG answer under v7.3 (pkg_v73r and pkg_v73, both arms);
  2. the exempted ids are exactly [AUTHOR:M1, AUTHOR:P1] on every copy and arm;
  3. C1, C2, C3 are never exempted;
  4. pkg_v72 shows at least one WRONG lesson among D1, D3, A1, X2 on each arm (the test exercises the fault);
  5. the STOP rule does not fire.
Plus plumbing (three different cuts ran; no crash; nothing imported from outside helm_now; the frozen item list).

    python -X utf8 -B -I test_t3_v73.py [-v]

Laptop only (the 500 MB rule is checked by the driver), 0 USD, no network; scratch output under V73_T3_SCRATCH (default:
the session scratchpad's v73_scratch\\t3). Standard library only. Claim status: a scratch test; nothing here is LICENSED.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "t3_score_v73.py"
SCRATCH = Path(os.environ.get("V73_T3_SCRATCH", r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
                              r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch\t3"))
ARMS = ("CHAT_ON", "LOOP_ON")
COPIES = ("v7.2", "v7.3r", "v7.3")


class T3V73(unittest.TestCase):
    doc = None
    proc = None

    @classmethod
    def setUpClass(cls):
        root = SCRATCH / ("test_%s_%d" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), os.getpid()))
        root.mkdir(parents=True, exist_ok=False)
        cls.out = root / "T3_V73.json"
        cls.proc = subprocess.run([sys.executable, "-X", "utf8", "-B", "-I", str(SCRIPT), "--out", str(cls.out),
                                   "--scratch-root", str(root)], capture_output=True, text=True, timeout=3600)
        if cls.proc.returncode == 0 and cls.out.is_file():
            cls.doc = json.loads(cls.out.read_text(encoding="utf-8"))

    def setUp(self):
        if self.doc is None:
            self.fail("t3_score_v73.py did not finish: exit %s\n%s" % (self.proc.returncode,
                                                                      (self.proc.stdout + self.proc.stderr)[-3000:]))

    def test_plumbing_three_cuts_ran_through_the_package(self):
        d = self.doc
        self.assertEqual(d["kind"], "T3")
        self.assertTrue(d["items"]["frozen_t3_list"])
        self.assertEqual(d["items"]["count"], 13)
        self.assertIn("v7.2", d["copies"]["v7.2"]["reader_version"])
        self.assertIn("v7.3", d["copies"]["v7.3r"]["reader_version"])
        self.assertIn("v7.3", d["copies"]["v7.3"]["reader_version"])
        self.assertEqual(sorted(r["file"] for r in d["copies"]["v7.3r"]["swap"]["swapped"]),
                         ["helm_wide_turn.py", "test_helm_cas_address.py", "test_helm_reader_gap.py"])
        self.assertEqual(d["copies"]["v7.3"]["cut_files_still_differing_from_worktree"], [])
        for c in ("v7.3r", "v7.3"):
            self.assertTrue(d["copies"][c]["swap"]["commit_field_unchanged"])
            self.assertTrue(d["copies"][c]["swap"]["source_cut_equals_contract"])
        self.assertEqual(len(d["units"]), 6)
        for u in d["units"]:
            self.assertEqual(u["crashed"], 0, u)
            self.assertEqual(u["items"], 13, u)
            self.assertEqual(u["helm_outside"], [], u)
            self.assertEqual(u["netguard"], {"installed": True, "attempts": 0}, u)
        self.assertTrue(d["scratch_only"])
        self.assertTrue(d["cut_commit_field_is_plumbing"])

    def test_1_no_wrong_lesson_or_answer_under_v73(self):
        for c in ("v7.3r", "v7.3"):
            for arm in ARMS:
                t = self.doc["totals"][c][arm]
                self.assertEqual((t["lessons_WRONG"], t["WRONG"]), (0, 0), (c, arm))

    def test_2_exempted_exactly_m1_p1_every_copy_and_arm(self):
        for c in COPIES:
            for arm in ARMS:
                self.assertEqual(self.doc["a_r1w7_11"][c][arm]["a11_exempted_ids"], ["AUTHOR:M1", "AUTHOR:P1"], (c, arm))

    def test_3_phantoms_c1_c2_c3_never_exempted(self):
        for c in COPIES:
            for arm in ARMS:
                got = set(self.doc["a_r1w7_11"][c][arm]["a11_exempted_ids"] or [])
                self.assertEqual(got & {"AUTHOR:C1", "AUTHOR:C2", "AUTHOR:C3"}, set(), (c, arm))

    def test_4_v72_exercises_the_fault_on_each_arm(self):
        for arm in ARMS:
            wrong = [i for i in ("AUTHOR:D1", "AUTHOR:D3", "AUTHOR:A1", "AUTHOR:X2")
                     if "WRONG" in self.doc["per_item"][i]["v7.2"][arm]["lessons"]]
            self.assertTrue(wrong, arm)

    def test_5_stop_rule_does_not_fire_and_pass_condition_holds(self):
        self.assertFalse(self.doc["stop_rule_section_6_step_3"]["STOP"], self.doc["stop_rule_section_6_step_3"])
        self.assertTrue(self.doc["pass_condition"]["holds"], self.doc["pass_condition"])


if __name__ == "__main__":
    unittest.main()
