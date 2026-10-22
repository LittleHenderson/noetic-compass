"""g2_first_version.py <out_json> -- reviewer G-2: the scorer-path item AUTHOR73:RANOUT_AMBIG was revised after the builder's
first scratch run (line 0 '2 cups apples with peel' -> '3 cups'). This reads that FIRST run's own score files (the builder's
authored recipes, scratch; no exam data) and writes the first version's outcome, labelled as the result of record, beside
the revised version's outcome from the kept run. Scratch evidence only."""
import hashlib
import json
import sys
from pathlib import Path

S = Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
         r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch\scorer_path")
FIRST = S / "run_20261022T044727Z_4688"
KEPT = Path(r"C:\tmp\helm-ctt2r-c49-read\docs\working\r1_wave7\v73_a11\scorer_path\SCORER_PATH_V73.json")
IID = "AUTHOR73:RANOUT_AMBIG"
FIELDS = ("q", "lessons", "lesson_statuses", "lesson_ingredients", "lesson_learned_in_taught_unit", "key_q")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(out):
    raw_p = FIRST / "inputs_pkg_v72" / "RAW_LINES_AUTHOR_V73.json"
    first = {"run_dir": str(FIRST), "raw_lines_file": str(raw_p), "raw_lines_sha256": sha(raw_p),
             "raw_lines": json.loads(raw_p.read_text(encoding="utf-8"))["raw_by_id"][IID], "by_unit": {}}
    for f in sorted((FIRST / "scores").glob("*.json")):
        x = json.loads(f.read_text(encoding="utf-8"))["items"][IID]
        first["by_unit"][f.stem] = {"file_sha256": sha(f), **{k: x.get(k) for k in FIELDS}}
    kept = json.loads(KEPT.read_text(encoding="utf-8"))
    revised = {"file": str(KEPT), "file_sha256": sha(KEPT), "raw_lines": kept["per_item"][IID]["raw_lines"],
               "by_reader_arm": {f"{r}|{a}": {k: kept["per_item"][IID][r][a].get(k) for k in FIELDS}
                                 for r in ("v7.2", "v7.3") for a in ("CHAT_ON", "LOOP_ON")}}
    doc = {"item": IID, "deviation": "DEVIATION (G-2): the item was revised after a scratch run showed its first version did "
           "not show v7.2's wrong bind as WRONG; the design says such an item is 'reported as such, not tuned'. The FIRST "
           "version's outcome is the result of record; the revised version is reported beside it, labelled.",
           "first_version_result_of_record": first, "revised_version_reported_only": revised,
           "scorer_limit_seen": "the frozen rbw1t.keys_rbw1t.score_lessons grades a lesson LEARNED when its admitted number "
           "equals the key's number, whatever line it was bound to: on the first version v7.2 bound the ran-out phrase to "
           "the diced-apple line (doubled 2 cups) and the key's line-0 amount was also 2, so the wrong-line bind read LEARNED "
           "(FLAG_FOR_HUMAN_REVIEW)"}
    Path(out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
