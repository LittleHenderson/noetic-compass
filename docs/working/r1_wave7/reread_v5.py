"""Builder tool (NOT sealed): read the v5 practice run again with the SEALED v5 reader, supplying the two host rows the laptop
dry-run tool does not write (the host runner writes them on AWS): the sandbox start/end hash of the wave-1 brain folder and
the helm_cut instrument row. Units untouched. Writes PRACTICE_READINGS_V5.json with every mark and reported row of the v5
practice beside v4's practice numbers (read from PRACTICE_READINGS_V4.json and run6's reading).

    python -X utf8 -B -I reread_v5.py <sealed v5 extract pkg dir> <run7 dir> <run6 dir> <v4 practice readings json> <deps dir> <out json>
"""
import hashlib
import json
import sys
from pathlib import Path

pkg, run7, run6, v4json, deps, out = [Path(a).resolve() for a in sys.argv[1:7]]
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


res = {"schema": "helm.r1w7.v5-rereads/1", "reader_package": str(pkg), "reader_string": M.READER}
host = json.loads((run7 / "R1_W7_HOST.json").read_text(encoding="utf-8"))
w1 = deps / C.NEIGHBOURS["w1"]["dir"]
fz = json.loads((w1 / "PACKAGE_FREEZE.json").read_text(encoding="utf-8"))
bad = [r for r, p in fz["members"].items() if not (w1 / r).is_file() or sha(w1 / r) != p["sha256"]]
extra = sorted(q.relative_to(w1).as_posix() for q in w1.rglob("*") if q.is_file() and "__pycache__" not in q.parts
               and q.relative_to(w1).as_posix() not in fz["members"] and q.name != "PACKAGE_FREEZE.json")
now = tree_sha(w1)
res["wave1_folder_after_run7"] = {"members": len(fz["members"]), "members_not_equal_to_freeze": bad, "extra_files": extra,
                                  "equals_its_sealed_freeze": not bad and not extra, "tree_sha_now": now}
host["sandbox"] = {"start": now if (not bad and not extra) else "FREEZE_MISMATCH", "end": now,
                   "note": "laptop reread: start is the sealed state (the folder equals its freeze after the run), end is the folder now"}
host["instruments"] = dict(host.get("instruments") or {}, helm_cut=C.check_helm_cut())
host["index_note"] = "R1_W7_HOST.json of run7 + the two host rows the dry-run tool omits (reread_v5.py); units untouched"
hp = run7 / "R1_W7_HOST_WITH_HOST_ROWS.json"
hsha = C.write_json(hp, host)
mi = json.loads((run7 / "MERGE_INPUT_DRY.json").read_text(encoding="utf-8"))
mi["host_index"], mi["host_index_sha256"] = str(hp), hsha
C.write_json(run7 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json", mi)
r2 = M.read(run7 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json")
C.write_json(run7 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json", r2)
r0 = json.loads((run7 / "R1_W7_READING_DRY.json").read_text(encoding="utf-8"))
res["run7_v5_practice_as_run"] = hg5_view(r0)
res["run7_v5_practice_with_host_rows"] = hg5_view(r2)
res["run7_marks_and_reported_rows_unchanged_by_the_host_rows"] = {k: (r0[k] == r2[k]) for k in ("marks", "reported", "marks_missed")}
r6 = json.loads((run6 / "R1_W7_READING_DRY.json").read_text(encoding="utf-8"))
res["practice_numbers"] = {"v5_run7": numbers(r2), "v4_run6": numbers(r6)}
diff = []


def walk(a, b, path):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            walk(a.get(k), b.get(k), path + "/" + str(k))
    elif a != b:
        diff.append({"path": path, "v5": a, "v4": b})


walk(res["practice_numbers"]["v5_run7"], res["practice_numbers"]["v4_run6"], "")
res["v5_minus_v4_practice_differences"] = diff
res["v4_practice_readings_file"] = {"path": str(v4json), "sha256": sha(v4json)}
data = (json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8")
out.write_bytes(data)
print(json.dumps({k: res[k] for k in ("run7_v5_practice_as_run", "run7_v5_practice_with_host_rows",
                                      "run7_marks_and_reported_rows_unchanged_by_the_host_rows", "v5_minus_v4_practice_differences")},
                 indent=1, sort_keys=True))
