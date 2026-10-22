"""read_plants.py <pkg_root> <out_json> -- the package's OWN reader (r1w7.merge_r1w7.read) on the synthetic fixture run, the
clean run and one run per plant: the five A-R1W7-11 plants (DESIGN_V73_A11.md T2) and the existing K4 / K3 plants. Prints
and writes, per run: marks_missed, failing_gates, the K4 and K3 mark fields, and the word a PASS verdict would give
(status_word("PASS", marks); the fixture's own verdict is always INSTRUMENT_ERROR by design: no sealed zip, no approval).
Scratch evidence only; nothing here is a result."""
import json
import sys
import tempfile
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PKG))
from r1w7 import merge_r1w7 as M          # noqa: E402
from tests_r1w7 import fixture_run as FX  # noqa: E402

PLANTS = [None, "K4_A11", "K4_A11_CLARIFY", "K4_A11_PHANTOM", "K4_A11_NO_SAMPLE", "K3_A11_WRONG", "K4", "K3"]
K4_FIELDS = ("value", "unexplained_asks_strict", "unexplained_asks_strict_after_a11", "a11_strict_recount", "a11_consistent",
             "a11_exempted_ids", "a11_flag_for_human_review", "sample_real_sha256", "amendment")


def main() -> int:
    out = {"pkg": str(PKG), "reader": M.READER, "runs": {}}
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
