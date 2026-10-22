"""test_scorer_path_v73.py -- DESIGN_V73_A11.md T3: runs run_scorer_path_v73.py ONCE (a fresh scratch run: two fresh v9
extracts, the package's own unit runner on X7_REAL CHAT_ON and LOOP_ON, the package's real score_w7.score_real) and
asserts the facts from the per-item verdicts it wrote:

  1. the dangling-"or" item has a WRONG lesson under reader v7.2 and no WRONG lesson under reader v7.3 (each arm);
  2. the ambiguous ran-out item is never WRONG under v7.3: its ran-out lesson is refused
     (TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH) and scores NOT_LEARNED (each arm);
  3. an ordinary "sugar" / "brown sugar" item scores the same under both readers (question and lessons, each arm);
  4. an ordinary one-line "X or Y" item scores the same under both readers (each arm).
Plus plumbing checks (two different readers really ran; no crash; nothing imported from outside helm_now) and the
design's section 6 stop rule (no WRONG lesson or answer under v7.3 on any authored item), reported as its own test.

    python -X utf8 -B -I test_scorer_path_v73.py [-v]

Laptop only, 0 USD, no network; scratch output under V73_SCORER_PATH_SCRATCH (default: the session scratchpad's
v73_scratch\\scorer_path). Standard library only. Claim status: a scratch test; nothing here is LICENSED.
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
SCRIPT = HERE / "run_scorer_path_v73.py"
SCRATCH = Path(os.environ.get("V73_SCORER_PATH_SCRATCH",
                              r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
                              r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch\scorer_path"))
ARMS = ("CHAT_ON", "LOOP_ON")
REFUSED = "TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH"
DANGLING, AMBIG, SUGAR, ORLINE = ("AUTHOR73:OR_DANGLING", "AUTHOR73:RANOUT_AMBIG", "AUTHOR73:SUGAR_PAIR",
                                  "AUTHOR73:OR_ONE_LINE")


class ScorerPathV73(unittest.TestCase):
    doc = None
    proc = None

    @classmethod
    def setUpClass(cls):
        root = SCRATCH / ("test_%s_%d" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), os.getpid()))
        root.mkdir(parents=True, exist_ok=False)
        cls.out = root / "SCORER_PATH_V73.json"
        cls.proc = subprocess.run([sys.executable, "-X", "utf8", "-B", "-I", str(SCRIPT), "--out", str(cls.out),
                                   "--scratch-root", str(root)], capture_output=True, text=True, timeout=3600)
        if cls.proc.returncode == 0 and cls.out.is_file():
            cls.doc = json.loads(cls.out.read_text(encoding="utf-8"))

    def setUp(self):
        if self.doc is None:
            self.fail("run_scorer_path_v73.py did not finish: exit %s\n%s" % (
                self.proc.returncode, (self.proc.stdout + self.proc.stderr)[-3000:]))

    def cell(self, iid, reader, arm):
        return self.doc["per_item"][iid][reader][arm]

    # ---- plumbing
    def test_two_different_readers_ran_through_the_package(self):
        c = self.doc["copies"]
        self.assertIn("v7.2", c["v7.2"]["reader_version"])
        self.assertIn("v7.3", c["v7.3"]["reader_version"])
        self.assertEqual(c["v7.2"]["reader_sha256"], c["v7.2"]["sealed_reader_sha256"])
        self.assertEqual(c["v7.3"]["reader_sha256"], self.doc["worktree_reader"]["sha256"])
        self.assertTrue(c["v7.3"]["swapped"]["commit_field_unchanged"])
        self.assertTrue(c["v7.3"]["swapped"]["source_cut_equals_contract"])
        self.assertNotIn("helm_wide_turn.py", [d["file"] for d in c["v7.3"]["cut_vs_worktree"]["differ_from_worktree"]])
        self.assertIn("helm_wide_turn.py", [d["file"] for d in c["v7.2"]["cut_vs_worktree"]["differ_from_worktree"]])
        self.assertEqual(len(self.doc["units"]), 4)
        for u in self.doc["units"]:
            self.assertEqual(u["crashed"], 0, u)
            self.assertEqual(u["items"], self.doc["authored"]["items"], u)
            self.assertEqual(u["helm_outside"], [], u)
            self.assertEqual(u["netguard"], {"installed": True, "attempts": 0}, u)
        self.assertTrue(self.doc["scratch_only"])
        self.assertTrue(self.doc["cut_commit_field_is_plumbing"])

    # ---- fact 1
    def test_dangling_or_wrong_lesson_under_v72_none_under_v73(self):
        for arm in ARMS:
            v72 = self.cell(DANGLING, "v7.2", arm)["lessons"]
            v73 = self.cell(DANGLING, "v7.3", arm)["lessons"]
            self.assertIn("WRONG", v72, (arm, v72))
            self.assertNotIn("WRONG", v73, (arm, v73))
        self.assertTrue(self.doc["facts"]["dangling_or_wrong_under_v72_not_under_v73"]["holds"])

    # ---- fact 2
    def test_ambiguous_ran_out_never_wrong_under_v73_refused_not_learned(self):
        for arm in ARMS:
            x = self.cell(AMBIG, "v7.3", arm)
            self.assertNotIn("WRONG", x["lessons"], (arm, x["lessons"]))
            self.assertNotEqual(x["q"], "WRONG", arm)
            self.assertEqual(x["lessons"][0], "NOT_LEARNED", (arm, x["lessons"]))
            self.assertEqual(x["lesson_statuses"][0], REFUSED, (arm, x["lesson_statuses"]))
        self.assertTrue(self.doc["facts"]["ambiguous_ran_out_never_wrong_under_v73"]["holds"])

    # ---- facts 3 and 4
    def test_sugar_and_brown_sugar_score_the_same_under_both_readers(self):
        for arm in ARMS:
            p, q = self.cell(SUGAR, "v7.2", arm), self.cell(SUGAR, "v7.3", arm)
            self.assertEqual((p["q"], p["lessons"]), (q["q"], q["lessons"]), arm)
        self.assertTrue(self.doc["facts"]["sugar_brown_sugar_same_under_both"]["holds"])

    def test_one_line_x_or_y_scores_the_same_under_both_readers(self):
        for arm in ARMS:
            p, q = self.cell(ORLINE, "v7.2", arm), self.cell(ORLINE, "v7.3", arm)
            self.assertEqual((p["q"], p["lessons"]), (q["q"], q["lessons"]), arm)
        self.assertTrue(self.doc["facts"]["one_line_or_same_under_both"]["holds"])

    def test_the_scorer_was_the_package_score_w7(self):
        for k, v in self.doc["score_files"].items():
            self.assertIn("HELM_R1_W6_20261019", v["score_w6_file"], k)
        for reader in ("v7.2", "v7.3"):
            for arm in ARMS:
                self.assertIn("lessons_WRONG", self.doc["totals"][reader][arm])

    # ---- the design's section 6 stop rule (reported as its own test; a failure here is a STOP, reported as found)
    def test_design_stop_rule_no_wrong_lesson_or_answer_under_v73(self):
        for arm in ARMS:
            t = self.doc["totals"]["v7.3"][arm]
            self.assertEqual((t["lessons_WRONG"], t["WRONG"]), (0, 0), arm)


if __name__ == "__main__":
    unittest.main()
