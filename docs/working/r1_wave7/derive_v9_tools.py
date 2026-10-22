"""Builder tool: derive reread_v9.py and frozen_conv_per_item_run11.py from the v8 tools by exact once-only replacements
(written as a script file, never through a shell here-string).

    python -X utf8 -B -I derive_v9_tools.py     (from r1_wave7/build_v9/build)
"""
from pathlib import Path

B = Path(__file__).resolve().parent
V8 = B.parent.parent / "build_v8" / "build"


def derive(src, dst, reps):
    s = (V8 / src).read_text(encoding="utf-8")
    for a, b in reps:
        if s.count(a) != 1:
            raise SystemExit(f"{src}: anchor not found exactly once: {a[:70]!r}")
        s = s.replace(a, b)
    (B / dst).write_text(s, encoding="utf-8", newline="\n")


Q = "'"
derive("reread_v8.py", "reread_v9.py", [
    ("read the v8 practice run (run10) again with the SEALED v8 reader", "read the v9 practice run (run11) again with the SEALED v9 reader"),
    ("Units untouched. Writes PRACTICE_READINGS_V8.json with every mark and reported row of run10 beside v7's run9 and v6's run8,",
     "Units untouched. Writes PRACTICE_READINGS_V9.json with every mark and reported row of run11 beside v8's run10 and v7's run9,"),
    ("and every differing number with its cause. The practice inputs of run10 are byte-identical to run9's (checked here), so every\n"
     "run10-minus-run9 difference has one cause: the reader v7.1 fix (the v8 HELM cut). run9-minus-run8 differences were split in\n"
     "PRACTICE_READINGS_V7.json between the reader-gap code and amendment A-R1W7-7; that split is carried over by file reference.",
     "and every differing number with its cause. The practice inputs of run11 are byte-identical to run10's (checked here), so every\n"
     "run11-minus-run10 difference has one cause: the reader v7.2 fix (the v9 HELM cut). run10-minus-run9 differences (the reader v7.1\n"
     "fix) are listed in PRACTICE_READINGS_V8.json; that file is carried over by reference."),
    ("python -X utf8 -B -I reread_v8.py <sealed v8 extract pkg dir> <run10 dir> <run9 dir> <run8 dir> <v7 practice readings json>\n"
     "                                      <deps dir> <v7 practice inputs dir> <v8 practice inputs dir> <out json>",
     "python -X utf8 -B -I reread_v9.py <sealed v9 extract pkg dir> <run11 dir> <run10 dir> <run9 dir> <v8 practice readings json>\n"
     "                                      <deps dir> <v8 practice inputs dir> <v9 practice inputs dir> <out json>"),
    ("pkg, run10, run9, run8, v7json, deps, prac7, prac8, out = [Path(a).resolve() for a in sys.argv[1:10]]",
     "pkg, run11, run10, run9, v8json, deps, prac8, prac9, out = [Path(a).resolve() for a in sys.argv[1:10]]"),
    ('res = {"schema": "helm.r1w7.v8-rereads/1"', 'res = {"schema": "helm.r1w7.v9-rereads/1"'),
    ("# the practice inputs of run10 (v8) and run9 (v7) must be byte-identical: then the only cause of a run10 - run9 move is the cut",
     "# the practice inputs of run11 (v9) and run10 (v8) must be byte-identical: then the only cause of a run11 - run10 move is the cut"),
    ('for p in sorted(prac8.rglob("*")):\n    if p.is_file():\n        rel = p.relative_to(prac8).as_posix()\n'
     '        same[rel] = (prac7 / rel).is_file() and sha(p) == sha(prac7 / rel)\nres["practice_inputs_v8_byte_identical_to_v7"]',
     'for p in sorted(prac9.rglob("*")):\n    if p.is_file():\n        rel = p.relative_to(prac9).as_posix()\n'
     '        same[rel] = (prac8 / rel).is_file() and sha(p) == sha(prac8 / rel)\nres["practice_inputs_v9_byte_identical_to_v8"]'),
    ('host = json.loads((run10 / "R1_W7_HOST.json")', 'host = json.loads((run11 / "R1_W7_HOST.json")'),
    ('res["wave1_folder_after_run10"]', 'res["wave1_folder_after_run11"]'),
    ('host["index_note"] = "R1_W7_HOST.json of run10 + the two host rows the dry-run tool omits (reread_v8.py); units untouched"',
     'host["index_note"] = "R1_W7_HOST.json of run11 + the two host rows the dry-run tool omits (reread_v9.py); units untouched"'),
    ('hp = run10 / "R1_W7_HOST_WITH_HOST_ROWS.json"', 'hp = run11 / "R1_W7_HOST_WITH_HOST_ROWS.json"'),
    ('mi = json.loads((run10 / "MERGE_INPUT_DRY.json")', 'mi = json.loads((run11 / "MERGE_INPUT_DRY.json")'),
    ('C.write_json(run10 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json", mi)\nr2 = M.read(run10 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json")\n'
     'C.write_json(run10 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json", r2)\nr0 = json.loads((run10 / "R1_W7_READING_DRY.json")',
     'C.write_json(run11 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json", mi)\nr2 = M.read(run11 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json")\n'
     'C.write_json(run11 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json", r2)\nr0 = json.loads((run11 / "R1_W7_READING_DRY.json")'),
    ('res["run10_v8_practice_as_run"] = hg5_view(r0)\nres["run10_v8_practice_with_host_rows"] = hg5_view(r2)\n'
     'res["run10_marks_and_reported_rows_unchanged_by_the_host_rows"]',
     'res["run11_v9_practice_as_run"] = hg5_view(r0)\nres["run11_v9_practice_with_host_rows"] = hg5_view(r2)\n'
     'res["run11_marks_and_reported_rows_unchanged_by_the_host_rows"]'),
    ('r9 = json.loads((run9 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))\n'
     'r8 = json.loads((run8 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))\n'
     'res["practice_numbers"] = {"v8_run10": numbers(r2), "v7_run9": numbers(r9), "v6_run8": numbers(r8)}',
     'r10 = json.loads((run10 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))\n'
     'r9 = json.loads((run9 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))\n'
     'res["practice_numbers"] = {"v9_run11": numbers(r2), "v8_run10": numbers(r10), "v7_run9": numbers(r9)}'),
    ('walk(res["practice_numbers"]["v8_run10"], res["practice_numbers"]["v7_run9"], "", d1, "v8", "v7")\n'
     'walk(res["practice_numbers"]["v8_run10"], res["practice_numbers"]["v6_run8"], "", d2, "v8", "v6")',
     'walk(res["practice_numbers"]["v9_run11"], res["practice_numbers"]["v8_run10"], "", d1, "v9", "v8")\n'
     'walk(res["practice_numbers"]["v9_run11"], res["practice_numbers"]["v7_run9"], "", d2, "v9", "v7")'),
    ('cause = ("the reader v7.1 fix (the v8 HELM cut: helm_faces_in.py v2.1 + helm_wide_turn.py RB-W1 v7.1); the practice inputs and keys "\n'
     '         "are byte-identical to run9' + Q + 's, the reader files are byte-identical, so no other cause exists")',
     'cause = ("the reader v7.2 fix (the v9 HELM cut: helm_faces_in.py v2.2 + helm_wide_turn.py RB-W1 v7.2); the practice inputs and keys "\n'
     '         "are byte-identical to run10' + Q + 's, the reader files are byte-identical, so no other cause exists")'),
    ('res["v8_minus_v7_practice_differences"] = d1\nres["v8_minus_v6_practice_differences"] = d2\n'
     'res["counts"] = {"v8_minus_v7": len(d1), "v8_minus_v6": len(d2)}\n'
     'res["v8_minus_v6_causes"] = ("each v8-minus-v6 difference is the sum of a run9-minus-run8 move (split in PRACTICE_READINGS_V7.json between the "\n'
     '                             "reader-gap code, dialogue rows only, and amendment A-R1W7-7, real-recipe denominators only) and a run10-minus-run9 "\n'
     '                             "move (the reader v7.1 fix, listed above with its cause)")\n'
     'res["v7_practice_readings_file"] = {"path": str(v7json), "sha256": sha(v7json)}',
     'res["v9_minus_v8_practice_differences"] = d1\nres["v9_minus_v7_practice_differences"] = d2\n'
     'res["counts"] = {"v9_minus_v8": len(d1), "v9_minus_v7": len(d2)}\n'
     'res["v9_minus_v7_causes"] = ("each v9-minus-v7 difference is the sum of a run10-minus-run9 move (the reader v7.1 fix, listed with its cause "\n'
     '                             "in PRACTICE_READINGS_V8.json) and a run11-minus-run10 move (the reader v7.2 fix, listed above with its cause)")\n'
     'res["v8_practice_readings_file"] = {"path": str(v8json), "sha256": sha(v8json)}'),
    ('for exam, arms in res["practice_numbers"]["v8_run10"]["totals"].items():\n    for arm, t in arms.items():\n        if "WRONG" in t:\n'
     '            wrong[f"{exam}/{arm}"] = {"v8_run10": t["WRONG"],\n'
     '                                     "v7_run9": res["practice_numbers"]["v7_run9"]["totals"].get(exam, {}).get(arm, {}).get("WRONG"),\n'
     '                                     "v6_run8": res["practice_numbers"]["v6_run8"]["totals"].get(exam, {}).get(arm, {}).get("WRONG")}',
     'for exam, arms in res["practice_numbers"]["v9_run11"]["totals"].items():\n    for arm, t in arms.items():\n        if "WRONG" in t:\n'
     '            wrong[f"{exam}/{arm}"] = {"v9_run11": t["WRONG"],\n'
     '                                     "v8_run10": res["practice_numbers"]["v8_run10"]["totals"].get(exam, {}).get(arm, {}).get("WRONG"),\n'
     '                                     "v7_run9": res["practice_numbers"]["v7_run9"]["totals"].get(exam, {}).get(arm, {}).get("WRONG")}'),
    ('print(json.dumps({k: res[k] for k in ("run10_v8_practice_as_run", "run10_v8_practice_with_host_rows",\n'
     '                                      "run10_marks_and_reported_rows_unchanged_by_the_host_rows", "counts",\n'
     '                                      "practice_inputs_v8_byte_identical_to_v7", "wrong_per_exam_and_arm",\n'
     '                                      "v8_minus_v7_practice_differences")}',
     'print(json.dumps({k: res[k] for k in ("run11_v9_practice_as_run", "run11_v9_practice_with_host_rows",\n'
     '                                      "run11_marks_and_reported_rows_unchanged_by_the_host_rows", "counts",\n'
     '                                      "practice_inputs_v9_byte_identical_to_v8", "wrong_per_exam_and_arm",\n'
     '                                      "v9_minus_v8_practice_differences")}'),
])

derive("frozen_conv_per_item_run10.py", "frozen_conv_per_item_run11.py", [
    ("through the sealed v8\npackage, `common_w7.setup(helm=False)`) for run10 (v8 cut, reader v7.1), run9 (v7 cut) and run8 (v6 cut)",
     "through the sealed v9\npackage, `common_w7.setup(helm=False)`) for run11 (v9 cut, reader v7.2), run10 (v8 cut, reader v7.1) and run9 (v7 cut)"),
    ("python -X utf8 -B -I frozen_conv_per_item_run10.py <sealed v8 extract pkg> <run10 dir> <run9 dir> <run8 dir> <practice inputs dir> <out json>",
     "python -X utf8 -B -I frozen_conv_per_item_run11.py <sealed v9 extract pkg> <run11 dir> <run10 dir> <run9 dir> <practice inputs dir> <out json>"),
    ("pkg, run10, run9, run8, prac, out = [Path(a).resolve() for a in sys.argv[1:7]]",
     "pkg, run11, run10, run9, prac, out = [Path(a).resolve() for a in sys.argv[1:7]]"),
    ('res = {"schema": "helm.r1w7.frozen-conv-per-item/2", "units": {}}', 'res = {"schema": "helm.r1w7.frozen-conv-per-item/3", "units": {}}'),
    ('for tag, d in (("run10", run10), ("run9", run9), ("run8", run8)):', 'for tag, d in (("run11", run11), ("run10", run10), ("run9", run9)):'),
    ('moved = {i: {"run8": row["run8"]["per_item"].get(i), "run9": row["run9"]["per_item"].get(i), "run10": v, "family": fam[i]}\n'
     '             for i, v in row["run10"]["per_item"].items() if row["run9"]["per_item"].get(i) != v}\n'
     '    wrong10 = sorted(i for i, v in row["run10"]["per_item"].items() if v == "WRONG")',
     'moved = {i: {"run9": row["run9"]["per_item"].get(i), "run10": row["run10"]["per_item"].get(i), "run11": v, "family": fam[i]}\n'
     '             for i, v in row["run11"]["per_item"].items() if row["run10"]["per_item"].get(i) != v}\n'
     '    wrong11 = sorted(i for i, v in row["run11"]["per_item"].items() if v == "WRONG")'),
    ('for i, v in row["run10"]["per_item"].items():\n        f = by_fam', 'for i, v in row["run11"]["per_item"].items():\n        f = by_fam'),
    ('res["units"][name] = {"run10_totals": row["run10"]["totals"], "run9_totals": row["run9"]["totals"], "run8_totals": row["run8"]["totals"],\n'
     '                          "run10_wrong_items": [(i, fam[i], row["run9"]["per_item"].get(i), row["run8"]["per_item"].get(i)) for i in wrong10],\n'
     '                          "run10_by_family": by_fam,\n'
     '                          "run10_wrong_per_family": {f: v["WRONG"] for f, v in sorted(by_fam.items())},\n'
     '                          "moved_items_run9_to_run10": moved,\n'
     '                          "moved_counts_run9_to_run10": {k: sum(1 for m in moved.values() if f"{m[' + Q + 'run9' + Q + ']}->{m[' + Q + 'run10' + Q + ']}" == k)\n'
     '                                                         for k in sorted({f"{m[' + Q + 'run9' + Q + ']}->{m[' + Q + 'run10' + Q + ']}" for m in moved.values()})}}',
     'res["units"][name] = {"run11_totals": row["run11"]["totals"], "run10_totals": row["run10"]["totals"], "run9_totals": row["run9"]["totals"],\n'
     '                          "run11_wrong_items": [(i, fam[i], row["run10"]["per_item"].get(i), row["run9"]["per_item"].get(i)) for i in wrong11],\n'
     '                          "run11_by_family": by_fam,\n'
     '                          "run11_wrong_per_family": {f: v["WRONG"] for f, v in sorted(by_fam.items())},\n'
     '                          "moved_items_run10_to_run11": moved,\n'
     '                          "moved_counts_run10_to_run11": {k: sum(1 for m in moved.values() if f"{m[' + Q + 'run10' + Q + ']}->{m[' + Q + 'run11' + Q + ']}" == k)\n'
     '                                                         for k in sorted({f"{m[' + Q + 'run10' + Q + ']}->{m[' + Q + 'run11' + Q + ']}" for m in moved.values()})}}'),
    ('print(json.dumps({n: {k: v[k] for k in ("run10_totals", "run9_totals", "run8_totals", "run10_wrong_items", "run10_wrong_per_family",\n'
     '                                        "moved_items_run9_to_run10", "moved_counts_run9_to_run10")}',
     'print(json.dumps({n: {k: v[k] for k in ("run11_totals", "run10_totals", "run9_totals", "run11_wrong_items", "run11_wrong_per_family",\n'
     '                                        "moved_items_run10_to_run11", "moved_counts_run10_to_run11")}'),
])
print("derived")
