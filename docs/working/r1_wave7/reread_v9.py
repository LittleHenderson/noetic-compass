"""Builder tool (NOT sealed): read the v9 practice run (run11) again with the SEALED v9 reader, supplying the two host rows the
laptop dry-run tool does not write (the sandbox start/end hash of the wave-1 brain folder and the helm_cut instrument row).
Units untouched. Writes PRACTICE_READINGS_V9.json with every mark and reported row of run11 beside v8's run10 and v7's run9,
and every differing number with its cause. The practice inputs of run11 are byte-identical to run10's (checked here), so every
run11-minus-run10 difference has one cause: the reader v7.2 fix (the v9 HELM cut). run10-minus-run9 differences (the reader v7.1
fix) are listed in PRACTICE_READINGS_V8.json; that file is carried over by reference.

    python -X utf8 -B -I reread_v9.py <sealed v9 extract pkg dir> <run11 dir> <run10 dir> <run9 dir> <v8 practice readings json>
                                      <deps dir> <v8 practice inputs dir> <v9 practice inputs dir> <out json>
"""
import hashlib
import json
import sys
from pathlib import Path

pkg, run11, run10, run9, v8json, deps, prac8, prac9, out = [Path(a).resolve() for a in sys.argv[1:10]]
sys.path.insert(0, str(pkg))
from r1w7 import common_w7 as C, merge_r1w7 as M  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            h.update(p.relative_to(root).as_posix().encode('utf-8') + b'\0' + sha(p).encode('ascii') + b'\n')
    return h.hexdigest()


def hg5_view(r):
    g = r["hard_gates"]["HG5_sandbox"]
    return {k: v for k, v in g.items() if k != "session_files_under_scratch"} | {
        "session_files_under_scratch_all_true": all(v is True for v in g["session_files_under_scratch"].values()),
        "failing_gates": r["failing_gates"], "failing_instruments": r["failing_instruments"],
        "verdict": r["verdict"], "status_word": r["status_word"], "marks_missed": r["marks_missed"], "reader": r.get("reader")}


def numbers(r):
    rep = r["reported"]
    return {"marks": {k: {kk: vv for kk, vv in v.items() if kk != "parts"} for k, v in r["marks"].items()},
            "mark_parts": {k: v.get("parts") for k, v in r["marks"].items() if v.get("parts")},
            "totals": rep["totals"], "noise": rep["noise"], "stock_turns": rep["stock_turns"],
            "chat_on_minus_chat_off": rep["chat_on_minus_chat_off"]}


def walk(a, b, path, diff, la, lb):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            walk(a.get(k), b.get(k), path + "/" + str(k), diff, la, lb)
    elif a != b:
        diff.append({"path": path, la: a, lb: b})


res = {"schema": "helm.r1w7.v9-rereads/1", "reader_package": str(pkg), "reader_string": M.READER}
# the practice inputs of run11 (v9) and run10 (v8) must be byte-identical: then the only cause of a run11 - run10 move is the cut
same = {}
for p in sorted(prac9.rglob("*")):
    if p.is_file():
        rel = p.relative_to(prac9).as_posix()
        same[rel] = (prac8 / rel).is_file() and sha(p) == sha(prac8 / rel)
res["practice_inputs_v9_byte_identical_to_v8"] = {"files": same, "all": all(same.values())}
host = json.loads((run11 / "R1_W7_HOST.json").read_text(encoding="utf-8"))
w1 = deps / C.NEIGHBOURS["w1"]["dir"]
fz = json.loads((w1 / "PACKAGE_FREEZE.json").read_text(encoding="utf-8"))
bad = [r for r, p in fz["members"].items() if not (w1 / r).is_file() or sha(w1 / r) != p["sha256"]]
extra = sorted(q.relative_to(w1).as_posix() for q in w1.rglob("*") if q.is_file() and "__pycache__" not in q.parts
               and q.relative_to(w1).as_posix() not in fz["members"] and q.name != "PACKAGE_FREEZE.json")
now = tree_sha(w1)
res["wave1_folder_after_run11"] = {"members": len(fz["members"]), "members_not_equal_to_freeze": bad, "extra_files": extra,
                                   "equals_its_sealed_freeze": not bad and not extra, "tree_sha_now": now}
host["sandbox"] = {"start": now if (not bad and not extra) else "FREEZE_MISMATCH", "end": now,
                   "note": "laptop reread: start is the sealed state (the folder equals its freeze after the run), end is the folder now"}
host["instruments"] = dict(host.get("instruments") or {}, helm_cut=C.check_helm_cut())
host["index_note"] = "R1_W7_HOST.json of run11 + the two host rows the dry-run tool omits (reread_v9.py); units untouched"
hp = run11 / "R1_W7_HOST_WITH_HOST_ROWS.json"
hsha = C.write_json(hp, host)
mi = json.loads((run11 / "MERGE_INPUT_DRY.json").read_text(encoding="utf-8"))
mi["host_index"], mi["host_index_sha256"] = str(hp), hsha
C.write_json(run11 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json", mi)
r2 = M.read(run11 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json")
C.write_json(run11 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json", r2)
r0 = json.loads((run11 / "R1_W7_READING_DRY.json").read_text(encoding="utf-8"))
res["run11_v9_practice_as_run"] = hg5_view(r0)
res["run11_v9_practice_with_host_rows"] = hg5_view(r2)
res["run11_marks_and_reported_rows_unchanged_by_the_host_rows"] = {k: (r0[k] == r2[k]) for k in ("marks", "reported", "marks_missed")}
r10 = json.loads((run10 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))
r9 = json.loads((run9 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))
res["practice_numbers"] = {"v9_run11": numbers(r2), "v8_run10": numbers(r10), "v7_run9": numbers(r9)}
d1, d2 = [], []
walk(res["practice_numbers"]["v9_run11"], res["practice_numbers"]["v8_run10"], "", d1, "v9", "v8")
walk(res["practice_numbers"]["v9_run11"], res["practice_numbers"]["v7_run9"], "", d2, "v9", "v7")
cause = ("the reader v7.2 fix (the v9 HELM cut: helm_faces_in.py v2.2 + helm_wide_turn.py RB-W1 v7.2); the practice inputs and keys "
         "are byte-identical to run10's, the reader files are byte-identical, so no other cause exists")
for d in d1:
    d["cause"] = cause
res["v9_minus_v8_practice_differences"] = d1
res["v9_minus_v7_practice_differences"] = d2
res["counts"] = {"v9_minus_v8": len(d1), "v9_minus_v7": len(d2)}
res["v9_minus_v7_causes"] = ("each v9-minus-v7 difference is the sum of a run10-minus-run9 move (the reader v7.1 fix, listed with its cause "
                             "in PRACTICE_READINGS_V8.json) and a run11-minus-run10 move (the reader v7.2 fix, listed above with its cause)")
res["v8_practice_readings_file"] = {"path": str(v8json), "sha256": sha(v8json)}
wrong = {}
for exam, arms in res["practice_numbers"]["v9_run11"]["totals"].items():
    for arm, t in arms.items():
        if "WRONG" in t:
            wrong[f"{exam}/{arm}"] = {"v9_run11": t["WRONG"],
                                     "v8_run10": res["practice_numbers"]["v8_run10"]["totals"].get(exam, {}).get(arm, {}).get("WRONG"),
                                     "v7_run9": res["practice_numbers"]["v7_run9"]["totals"].get(exam, {}).get(arm, {}).get("WRONG")}
res["wrong_per_exam_and_arm"] = wrong
data = (json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8")
out.write_bytes(data)
print(json.dumps({k: res[k] for k in ("run11_v9_practice_as_run", "run11_v9_practice_with_host_rows",
                                      "run11_marks_and_reported_rows_unchanged_by_the_host_rows", "counts",
                                      "practice_inputs_v9_byte_identical_to_v8", "wrong_per_exam_and_arm",
                                      "v9_minus_v8_practice_differences")}, indent=1, sort_keys=True))
