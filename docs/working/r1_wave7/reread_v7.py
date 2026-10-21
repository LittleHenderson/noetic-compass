"""Builder tool (NOT sealed): read the v7 practice run (run9) again with the SEALED v7 reader, supplying the two host rows the
laptop dry-run tool does not write (the sandbox start/end hash of the wave-1 brain folder and the helm_cut instrument row).
Units untouched. Writes PRACTICE_READINGS_V7.json with every mark and reported row of run9 beside v6's run8, and separates
the two causes of any move: the v7 HELM cut (the reader-gap code; run9's units) and amendment A-R1W7-7 (the practice keys),
by reading run9's units once more against the v6 practice keys (same inputs byte for byte; only the keys differ).

    python -X utf8 -B -I reread_v7.py <sealed v7 extract pkg dir> <run9 dir> <run8 dir> <v6 practice readings json> <deps dir>
                                      <v6 practice inputs dir> <out json>
"""
import hashlib
import json
import sys
from pathlib import Path

pkg, run9, run8, v6json, deps, prac6, out = [Path(a).resolve() for a in sys.argv[1:8]]
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


res = {"schema": "helm.r1w7.v7-rereads/1", "reader_package": str(pkg), "reader_string": M.READER}
host = json.loads((run9 / "R1_W7_HOST.json").read_text(encoding="utf-8"))
w1 = deps / C.NEIGHBOURS["w1"]["dir"]
fz = json.loads((w1 / "PACKAGE_FREEZE.json").read_text(encoding="utf-8"))
bad = [r for r, p in fz["members"].items() if not (w1 / r).is_file() or sha(w1 / r) != p["sha256"]]
extra = sorted(q.relative_to(w1).as_posix() for q in w1.rglob("*") if q.is_file() and "__pycache__" not in q.parts
               and q.relative_to(w1).as_posix() not in fz["members"] and q.name != "PACKAGE_FREEZE.json")
now = tree_sha(w1)
res["wave1_folder_after_run9"] = {"members": len(fz["members"]), "members_not_equal_to_freeze": bad, "extra_files": extra,
                                  "equals_its_sealed_freeze": not bad and not extra, "tree_sha_now": now}
host["sandbox"] = {"start": now if (not bad and not extra) else "FREEZE_MISMATCH", "end": now,
                   "note": "laptop reread: start is the sealed state (the folder equals its freeze after the run), end is the folder now"}
host["instruments"] = dict(host.get("instruments") or {}, helm_cut=C.check_helm_cut())
host["index_note"] = "R1_W7_HOST.json of run9 + the two host rows the dry-run tool omits (reread_v7.py); units untouched"
hp = run9 / "R1_W7_HOST_WITH_HOST_ROWS.json"
hsha = C.write_json(hp, host)
mi = json.loads((run9 / "MERGE_INPUT_DRY.json").read_text(encoding="utf-8"))
mi["host_index"], mi["host_index_sha256"] = str(hp), hsha
C.write_json(run9 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json", mi)
r2 = M.read(run9 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json")
C.write_json(run9 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json", r2)
# the same units read against the v6 practice KEYS (inputs identical; isolates the amendment from the reader-gap code)
mi6 = dict(mi, x7_exam_dir=str(prac6 / "exam"), note="run9's units (the v7 cut) read against the v6 practice keys: isolates A-R1W7-7")
C.write_json(run9 / "MERGE_INPUT_DRY_WITH_HOST_ROWS_V6_KEYS.json", mi6)
r6k = M.read(run9 / "MERGE_INPUT_DRY_WITH_HOST_ROWS_V6_KEYS.json")
C.write_json(run9 / "R1_W7_READING_DRY_WITH_HOST_ROWS_V6_KEYS.json", r6k)
r0 = json.loads((run9 / "R1_W7_READING_DRY.json").read_text(encoding="utf-8"))
res["run9_v7_practice_as_run"] = hg5_view(r0)
res["run9_v7_practice_with_host_rows"] = hg5_view(r2)
res["run9_marks_and_reported_rows_unchanged_by_the_host_rows"] = {k: (r0[k] == r2[k]) for k in ("marks", "reported", "marks_missed")}
r8 = json.loads((run8 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))
res["practice_numbers"] = {"v7_run9": numbers(r2), "v7_run9_units_read_with_v6_keys": numbers(r6k), "v6_run8": numbers(r8)}
d1, d2, d3 = [], [], []
walk(res["practice_numbers"]["v7_run9"], res["practice_numbers"]["v6_run8"], "", d1, "v7", "v6")
walk(res["practice_numbers"]["v7_run9_units_read_with_v6_keys"], res["practice_numbers"]["v6_run8"], "", d2, "v7_cut_v6_keys", "v6")
walk(res["practice_numbers"]["v7_run9"], res["practice_numbers"]["v7_run9_units_read_with_v6_keys"], "", d3, "v7_keys", "v6_keys")
res["v7_minus_v6_practice_differences"] = d1
res["reader_gap_code_alone_v7_units_with_v6_keys_minus_v6"] = d2
res["amendment_7_alone_v7_units_v7_keys_minus_v6_keys"] = d3
res["counts"] = {"v7_minus_v6": len(d1), "reader_gap_code_alone": len(d2), "amendment_7_alone": len(d3)}
res["v6_practice_readings_file"] = {"path": str(v6json), "sha256": sha(v6json)}
data = (json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8")
out.write_bytes(data)
print(json.dumps({k: res[k] for k in ("run9_v7_practice_as_run", "run9_v7_practice_with_host_rows",
                                      "run9_marks_and_reported_rows_unchanged_by_the_host_rows", "counts",
                                      "v7_minus_v6_practice_differences", "reader_gap_code_alone_v7_units_with_v6_keys_minus_v6",
                                      "amendment_7_alone_v7_units_v7_keys_minus_v6_keys")}, indent=1, sort_keys=True))
