"""Builder tool (NOT sealed): read the v6 practice run again with the SEALED v6 reader, supplying the two host rows the laptop
dry-run tool does not write (the host runner writes them on AWS): the sandbox start/end hash of the wave-1 brain folder and
the helm_cut instrument row. Units untouched. Writes PRACTICE_READINGS_V6.json with every mark and reported row of the v6
practice (run8) beside v5's practice numbers (run7's reading).

    python -X utf8 -B -I reread_v6.py <sealed v6 extract pkg dir> <run8 dir> <run7 dir> <v5 practice readings json> <deps dir> <out json>
"""
import hashlib
import json
import sys
from pathlib import Path

pkg, run8, run7, v5json, deps, out = [Path(a).resolve() for a in sys.argv[1:7]]
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


res = {"schema": "helm.r1w7.v6-rereads/1", "reader_package": str(pkg), "reader_string": M.READER}
host = json.loads((run8 / "R1_W7_HOST.json").read_text(encoding="utf-8"))
w1 = deps / C.NEIGHBOURS["w1"]["dir"]
fz = json.loads((w1 / "PACKAGE_FREEZE.json").read_text(encoding="utf-8"))
bad = [r for r, p in fz["members"].items() if not (w1 / r).is_file() or sha(w1 / r) != p["sha256"]]
extra = sorted(q.relative_to(w1).as_posix() for q in w1.rglob("*") if q.is_file() and "__pycache__" not in q.parts
               and q.relative_to(w1).as_posix() not in fz["members"] and q.name != "PACKAGE_FREEZE.json")
now = tree_sha(w1)
res["wave1_folder_after_run8"] = {"members": len(fz["members"]), "members_not_equal_to_freeze": bad, "extra_files": extra,
                                  "equals_its_sealed_freeze": not bad and not extra, "tree_sha_now": now}
host["sandbox"] = {"start": now if (not bad and not extra) else "FREEZE_MISMATCH", "end": now,
                   "note": "laptop reread: start is the sealed state (the folder equals its freeze after the run), end is the folder now"}
host["instruments"] = dict(host.get("instruments") or {}, helm_cut=C.check_helm_cut())
host["index_note"] = "R1_W7_HOST.json of run8 + the two host rows the dry-run tool omits (reread_v6.py); units untouched"
hp = run8 / "R1_W7_HOST_WITH_HOST_ROWS.json"
hsha = C.write_json(hp, host)
mi = json.loads((run8 / "MERGE_INPUT_DRY.json").read_text(encoding="utf-8"))
mi["host_index"], mi["host_index_sha256"] = str(hp), hsha
C.write_json(run8 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json", mi)
r2 = M.read(run8 / "MERGE_INPUT_DRY_WITH_HOST_ROWS.json")
C.write_json(run8 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json", r2)
r0 = json.loads((run8 / "R1_W7_READING_DRY.json").read_text(encoding="utf-8"))
res["run8_v6_practice_as_run"] = hg5_view(r0)
res["run8_v6_practice_with_host_rows"] = hg5_view(r2)
res["run8_marks_and_reported_rows_unchanged_by_the_host_rows"] = {k: (r0[k] == r2[k]) for k in ("marks", "reported", "marks_missed")}
r7 = json.loads((run7 / "R1_W7_READING_DRY_WITH_HOST_ROWS.json").read_text(encoding="utf-8"))
res["practice_numbers"] = {"v6_run8": numbers(r2), "v5_run7": numbers(r7)}
diff = []


def walk(a, b, path):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            walk(a.get(k), b.get(k), path + "/" + str(k))
    elif a != b:
        diff.append({"path": path, "v6": a, "v5": b})


walk(res["practice_numbers"]["v6_run8"], res["practice_numbers"]["v5_run7"], "")
res["v6_minus_v5_practice_differences"] = diff
res["v5_practice_readings_file"] = {"path": str(v5json), "sha256": sha(v5json)}
data = (json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8")
out.write_bytes(data)
print(json.dumps({k: res[k] for k in ("run8_v6_practice_as_run", "run8_v6_practice_with_host_rows",
                                      "run8_marks_and_reported_rows_unchanged_by_the_host_rows", "v6_minus_v5_practice_differences")},
                 indent=1, sort_keys=True))
