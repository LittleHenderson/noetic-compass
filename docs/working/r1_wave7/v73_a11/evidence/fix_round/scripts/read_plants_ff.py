"""read_plants_ff.py <pkg_root> <out_json> -- the package's OWN reader (r1w7.merge_r1w7.read) on the synthetic fixture run, the
clean run and one run per plant (the five A-R1W7-11 plants and the existing K4 / K3 plants). Fix round 2026-10-21 (reviewer
G-9): the output also records, AT RUN TIME, the state of the fix: whether the package copy carries r1w7/honest_ask_w7.py
(and its sha256), the sha256 of the copy's score_w7.py / merge_r1w7.py / fixture_run.py, the copy's merge READER string,
and the sha256 of every file in the amendment's source folder (docs/working/r1_wave7/a_r1w7_11/). Scratch evidence only."""
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
A11_SRC = Path(r"C:\tmp\helm-ctt2r-c49-read\docs\working\r1_wave7\a_r1w7_11")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).is_file() else None


fix_state = {
    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "pkg_has_honest_ask_w7": (PKG / "r1w7" / "honest_ask_w7.py").is_file(),
    "pkg_honest_ask_w7_sha256": sha(PKG / "r1w7" / "honest_ask_w7.py"),
    "pkg_has_test_honest_ask_w7": (PKG / "tests_r1w7" / "test_honest_ask_w7.py").is_file(),
    "pkg_score_w7_sha256": sha(PKG / "r1w7" / "score_w7.py"),
    "pkg_merge_r1w7_sha256": sha(PKG / "r1w7" / "merge_r1w7.py"),
    "pkg_fixture_run_sha256": sha(PKG / "tests_r1w7" / "fixture_run.py"),
    "amendment_source_folder": {p.name: sha(p) for p in sorted(A11_SRC.iterdir()) if p.is_file()},
}
sys.path.insert(0, str(PKG))
from r1w7 import merge_r1w7 as M          # noqa: E402
from tests_r1w7 import fixture_run as FX  # noqa: E402

fix_state["pkg_merge_reader"] = M.READER
PLANTS = [None, "K4_A11", "K4_A11_CLARIFY", "K4_A11_PHANTOM", "K4_A11_NO_SAMPLE", "K3_A11_WRONG", "K4", "K3"]
K4_FIELDS = ("value", "unexplained_asks_strict", "unexplained_asks_strict_after_a11", "a11_strict_recount", "a11_consistent",
             "a11_exempted_ids", "a11_flag_for_human_review", "sample_real_sha256", "amendment")


def main() -> int:
    out = {"pkg": str(PKG), "fix_state_at_run_time": fix_state, "runs": {}}
    print("FIX STATE", json.dumps(fix_state, sort_keys=True))
    with tempfile.TemporaryDirectory() as td:
        for plant in PLANTS:
            name = plant or "CLEAN"
            r = M.read(FX.make_run(Path(td) / name, plant=plant)["merge_input"])
            k4 = r["marks"]["K4_HONEST"]
            row = {"marks_missed": r["marks_missed"], "failing_gates": r["failing_gates"], "verdict": r["verdict"],
                   "word_if_verdict_PASS": M.status_word("PASS", r["marks"])["word"],
                   "K4": {k: k4.get(k, "(field absent)") for k in K4_FIELDS},
                   "K3": {k: r["marks"]["K3_SAFE"].get(k) for k in ("value", "real_wrong_answers", "real_wrong_lessons")}}
            out["runs"][name] = row
            print(name, json.dumps(row, sort_keys=True))
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
