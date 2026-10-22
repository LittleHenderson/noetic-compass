"""Stdlib tests for the parts of score_scribe_l4.py that run WITHOUT torch and WITHOUT the sealed 98.

Run (PYTHONPATH = language_v3 folder + the sdg_bridge_v2 and lacunarity_machine folders from PROVENANCE.md):
    C:\\Python314\\python.exe -X utf8 -B -m unittest -v test_score_scribe_l4_adapter
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import cce
import scoring
import score_scribe_l4 as S

HERE = Path(__file__).resolve().parent
DEV = HERE.parents[2] / "cas-synthetic" / "data" / "l4_split" / "real_dev_unparseables_99.jsonl"


def pred(subject="Mind", verb="processes", obj="Idea"):
    return {"turn_type": "ANSWER", "domain": "C", "register": "A", "drive": "F2", "verb": verb,
            "subject": subject, "object": obj}


class Adapter(unittest.TestCase):
    def test_no_torch_imported(self):
        self.assertNotIn("torch", sys.modules)

    def test_mind_clauses_round_trip_in_real_cce(self):
        for verb in ("intakes", "processes", "stores", "outputs"):
            for obj in ("Idea", "Vibration", "Rhythm", "Above/Cause", "Below/Effect"):
                c, why = S.scribe_to_cce(pred(verb=verb, obj=obj), cce)
                self.assertIsNone(why)
                self.assertTrue(cce.round_trip(c)["ok"], (verb, obj))

    def test_non_mind_subject_has_no_cce_frame(self):
        for subject in ("Positive", "Negative", "Male", "Female"):
            self.assertEqual(S.scribe_to_cce(pred(subject=subject), cce), (None, "NO_CCE_FRAME"))

    def test_clarify_is_a_refusal_not_a_pass(self):
        self.assertEqual(S.scribe_to_cce({"turn_type": "CLARIFY", "missing_slot": "meaning"}, cce),
                         (None, "CLARIFY"))

    def test_exact_match_against_a_recipe_gold_is_impossible(self):
        # DEV rows only (allowed). A one-clause Scribe content never equals a recipe gold.
        rows = [json.loads(x) for x in DEV.read_text("utf-8").splitlines() if x.strip()]
        adapted, _ = S.scribe_to_cce(pred(), cce)
        for r in rows:
            gold = scoring.content_from_parse(r["parsed"])
            self.assertIsNotNone(gold["recipe"])
            self.assertNotEqual(cce.normalize(adapted), cce.normalize(gold))

    def test_refuses_without_owner_approval(self):
        with tempfile.TemporaryDirectory() as d:
            ap = Path(d) / "approval.md"
            ap.write_text("no approval here\n", "utf-8")
            argv = ["score_scribe_l4.py"] + sum([["--" + k, str(ap)] for k in
                                                 ("weights", "vocab", "scribe-src", "lang-v3", "bridge", "sealed",
                                                  "approval")], []) + ["--out", str(Path(d) / "o.json")]
            old = sys.argv
            sys.argv = argv
            try:
                with self.assertRaises(SystemExit) as cm:
                    S.main()
            finally:
                sys.argv = old
            self.assertIn("REFUSED", str(cm.exception))
            self.assertNotIn("torch", sys.modules)


if __name__ == "__main__":
    unittest.main()
