"""run_scorer_path_v73.py -- DESIGN_V73_A11.md section 4, T3 ("end to end through the package's own unit runner and
scorer"), the scorer-path test of reader v7.3 (design sha256 57fcc5143d97431f4831b9c231d02c44efc88260da357febfc0b6add17be890a).
Laptop only, 0 USD, no network, scratch copies only; never edits the sealed v9 tree; runs no git command that changes state.

    python -X utf8 -B -I run_scorer_path_v73.py [--out <json>] [--scratch-root <dir>]

What it does, in this order (each step refuses and stops on a failed check; there is no silent fallback):
  0. free physical memory at least 500 MB (the design's light-run rule, section 6; else STOP, the owner's AWS order stands);
     the design file hashes to its frozen sha256; the v9 zip hashes to ad3fb98c...
  1. two FRESH extracts of the sealed v9 zip under <scratch-root>/run_<utc>_<pid>/:
       pkg_v72   = helm_now as sealed (reader v7.2)
       pkg_v73r  = helm_now with ONLY helm_wide_turn.py replaced by the worktree's (reader v7.3); its sha256 and size are
                   rewritten in contract/HELM_CUT_R1W7.json and the byte-equal helm_now/SOURCE_CUT.json (commit field
                   unchanged: scratch plumbing, never sealed)
     then every other cut file of each copy is compared with the worktree's file at the same path (differences listed,
     and, read-only, whether the worktree file equals the branch HEAD blob)
  2. A-R1W7-11 applied to BOTH copies by docs/working/r1_wave7/a_r1w7_11/apply_amendment_11.py (only if that builder's
     honest_ask_w7.py is present), so score_w7.score_real takes raw_by_id and runs the K4 recount
  3. the authored recipes (AUTHORED_RECIPES_V73.json, the author's own lines) -> X7_REAL inputs by the frozen
     rbw1t.exam_rbw1t.turns_for (host fields = custody_w7.real_inputs_doc's), keys by the frozen rbw1t.keys_rbw1t.key_item +
     A-R1W7-7's multi_qty_w7.apply, the raw lines by id; built in each copy (must be byte-equal) and checked against the
     copies kept beside this script (written there on the first run, refused if they ever differ)
  4. the package's own unit runner, one process per unit: r1w7/units_w7.py chat --exam X7_REAL --arm CHAT_ON and
     r1w7/units_w7.py loop --exam X7_REAL --arm LOOP_ON, on both copies (neighbours by R1W7_*_DIR from the custody deps)
  5. the package's real r1w7/score_w7.score_real (it calls the frozen r1w6.score_w6.score_real), per unit, in its own
     copy; per-lesson detail by the frozen score_w6.real_record_view + rbw1t.keys_rbw1t.score_lessons
  6. SCORER_PATH_V73.json: per item, per reader, per arm, the question verdict and the lesson verdicts (with HELM's own
     status words and sentences), the totals, A-R1W7-11's fields, and the four facts the test asserts.

Claim status: a scratch test of an unsealed reader; reader v7.3 at most ENGINEERED-NOT-VALIDATED; the chat stays NOT LICENSED.
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[4]                                  # .../docs/working/r1_wave7/v73_a11/scorer_path -> worktree root
DESIGN = HERE.parent / "DESIGN_V73_A11.md"
DESIGN_SHA256 = "57fcc5143d97431f4831b9c231d02c44efc88260da357febfc0b6add17be890a"
A11_DIR = HERE.parents[1] / "a_r1w7_11"
ZIP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\build_v9\HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip")
ZIP_SHA256 = "ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c"
PKG_TOP = "HELM_R1_W7_20261020"
DEPS = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\x7v9_custody\pkg\deps")
NEIGHBOUR_ENV = {"R1W7_W1_DIR": "HELM_R1_W1_20261015", "R1W7_W3_DIR": "HELM_R1_W3_20261019",
                 "R1W7_W3B_DIR": "HELM_R1_W3B_20261019", "R1W7_W6_DIR": "HELM_R1_W6_20261019",
                 "R1W7_RBW1T_DIR": "HELM_RBW1T_20261019"}
SCRATCH_ROOT = Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
                    r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch\scorer_path")
RECIPES = HERE / "AUTHORED_RECIPES_V73.json"
KEPT = {"inputs": "INPUTS_REAL_AUTHOR_V73.json", "keys": "AUTHOR_KEYS_V73.json", "raw": "RAW_LINES_AUTHOR_V73.json"}
OUT_DEFAULT = HERE / "SCORER_PATH_V73.json"
READERS = (("v7.2", "pkg_v72"), ("v7.3", "pkg_v73r"))
UNITS = (("chat", "CHAT_ON"), ("loop", "LOOP_ON"))
MEMORY_FLOOR_MIB = 500
PY = [sys.executable, "-X", "utf8", "-B", "-I"]
REFUSED_RAN_OUT = "TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH"
SCHEMA = "helm.r1w7.v73-scorer-path/1"


# ============================================================================================ small helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_bytes(obj, indent=1) -> bytes:
    """Sorted keys, LF, ASCII: the package's own write_json bytes."""
    return (json.dumps(obj, sort_keys=True, indent=indent, default=str, ensure_ascii=True) + "\n").encode("ascii")


def write_json(p, obj, indent=1) -> str:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json_bytes(obj, indent)
    part = p.with_name(p.name + ".partial")
    part.write_bytes(data)
    os.replace(part, p)
    return sha256_bytes(data)


def read_json(p) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


class Stop(SystemExit):
    pass


def stop(msg: str):
    print("STOP: " + msg, flush=True)
    raise Stop(3)


def free_mib() -> Optional[float]:
    """Free physical memory in MiB (Windows GlobalMemoryStatusEx, else /proc/meminfo), or None if unknown."""
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        ms = MS()
        ms.dwLength = ctypes.sizeof(MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            return round(ms.ullAvailPhys / (1024 * 1024), 1)
    except Exception:
        pass
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return round(int(line.split()[1]) / 1024, 1)
    except Exception:
        pass
    return None


MEMORY_WAIT_SECONDS = 300


def memory_gate(where: str, log: List[Dict[str, Any]]):
    """The design's light-run rule (section 6: at least 500 MB free), checked at the start AND before every unit (stricter
    than the design's 'at the start'). Below the floor it waits up to MEMORY_WAIT_SECONDS for other programs to free
    memory (rechecking every 5 s; nothing runs meanwhile), then STOPs: never a local run below the floor."""
    t0 = time.time()
    first = f = free_mib()
    while f is not None and f < MEMORY_FLOOR_MIB and time.time() - t0 < MEMORY_WAIT_SECONDS:
        time.sleep(5)
        f = free_mib()
    log.append({"where": where, "free_mib": f, "free_mib_first_check": first, "waited_seconds": round(time.time() - t0, 1)})
    if f is None:
        stop(f"free memory unknown at {where}; the light-run rule cannot be checked")
    if f < MEMORY_FLOOR_MIB:
        stop(f"free physical memory {f} MiB < {MEMORY_FLOOR_MIB} MiB at {where} after waiting {MEMORY_WAIT_SECONDS} s "
             f"(owner's AWS order: no local fallback)")


def child_env() -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("HELM_")}
    for k, d in NEIGHBOUR_ENV.items():
        env[k] = str(DEPS / d)
    return env


def popped_helm_env() -> List[str]:
    return sorted(k for k in os.environ if k.upper().startswith("HELM_"))


def git_head_blob(rel: str) -> Optional[bytes]:
    """Read-only: the branch HEAD blob of a worktree path (git show), or None."""
    try:
        r = subprocess.run(["git", "-C", str(WORKTREE), "show", "HEAD:" + rel], capture_output=True, timeout=60,
                           env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def git_head_sha() -> Optional[str]:
    try:
        r = subprocess.run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


# ============================================================================================ step 1: the copies
def extract(run_dir: Path, label: str) -> Path:
    dest = run_dir / label
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(ZIP) as zf:
        names = zf.namelist()
        bad = [n for n in names if n.startswith("/") or ".." in Path(n).parts or not n.startswith(PKG_TOP + "/")]
        if bad:
            stop(f"zip member outside {PKG_TOP}/: {bad[:3]}")
        zf.extractall(dest)
    return dest / PKG_TOP


def rewrite_cut(root: Path, rel: str, new_bytes: bytes) -> Dict[str, Any]:
    """helm_now/<rel> := new_bytes; its sha256 and size rewritten in contract/HELM_CUT_R1W7.json and the byte-equal
    helm_now/SOURCE_CUT.json (commit field unchanged)."""
    contract = root / "contract" / "HELM_CUT_R1W7.json"
    source_cut = root / "helm_now" / "SOURCE_CUT.json"
    orig = contract.read_bytes()
    if source_cut.read_bytes() != orig:
        stop("SOURCE_CUT.json is not byte-equal to contract/HELM_CUT_R1W7.json in the fresh extract")
    obj = json.loads(orig)
    old = dict(obj["files"][rel])
    (root / "helm_now" / rel).write_bytes(new_bytes)
    new_pin = {"bytes": len(new_bytes), "sha256": sha256_bytes(new_bytes)}
    if set(old) != set(new_pin):
        stop(f"cut pin of {rel} has fields {sorted(old)}, expected bytes and sha256")
    if json_bytes(obj) == orig:                      # the contract re-serialises byte for byte: rewrite the whole file
        obj["files"][rel] = new_pin
        data = json_bytes(obj)
        how = "reserialised (sorted, indent 1, LF; the original re-serialised byte for byte)"
    else:                                            # else: targeted replacement of the two values only
        text = orig.decode("utf-8")
        if text.count(old["sha256"]) != 1:
            stop(f"cut pin sha256 of {rel} not found exactly once")
        text = text.replace(old["sha256"], new_pin["sha256"])
        pat = re.compile(r'("%s":\s*\{\s*"bytes":\s*)%d' % (re.escape(rel), old["bytes"]))
        text, n = pat.subn(lambda m: m.group(1) + str(new_pin["bytes"]), text)
        if n != 1:
            stop(f"cut pin bytes of {rel} not found exactly once")
        data = text.encode("utf-8")
        how = "targeted replacement of sha256 and bytes"
    contract.write_bytes(data)
    source_cut.write_bytes(data)
    after = json.loads(data)
    if after["files"][rel] != new_pin or after.get("commit") != obj.get("commit"):
        stop("cut rewrite check failed")
    return {"file": rel, "old": old, "new": new_pin, "how": how, "commit_field": after.get("commit"),
            "commit_field_unchanged": True, "contract_sha256": sha256_bytes(data),
            "source_cut_equals_contract": source_cut.read_bytes() == contract.read_bytes()}


def compare_cut_with_worktree(root: Path) -> Dict[str, Any]:
    cut = read_json(root / "contract" / "HELM_CUT_R1W7.json")
    differ, missing, equal = [], [], 0
    for rel in sorted(cut["files"]):
        mine = (root / "helm_now" / rel).read_bytes()
        wt = WORKTREE / rel
        if not wt.is_file():
            missing.append(rel)
            continue
        wb = wt.read_bytes()
        if wb == mine:
            equal += 1
            continue
        head = git_head_blob(rel)
        differ.append({"file": rel, "copy_sha256": sha256_bytes(mine), "worktree_sha256": sha256_bytes(wb),
                       "worktree_equals_branch_head": (head == wb) if head is not None else None,
                       "copy_equals_branch_head": (head == mine) if head is not None else None})
    return {"cut_files": len(cut["files"]), "equal_to_worktree": equal, "differ_from_worktree": differ,
            "missing_in_worktree": missing}


def apply_a11(root: Path) -> Dict[str, Any]:
    tool, mod = A11_DIR / "apply_amendment_11.py", A11_DIR / "honest_ask_w7.py"
    if not (tool.is_file() and mod.is_file()):
        return {"applied": False, "why": "the A-R1W7-11 builder's module is not present"}
    r = subprocess.run(PY + [str(tool), str(root)], capture_output=True, text=True, timeout=300, cwd=str(root.parent))
    if r.returncode != 0:
        stop("apply_amendment_11.py refused: " + (r.stdout + r.stderr)[-1500:])
    return {"applied": True, "tool_sha256": sha256_file(tool), "honest_ask_w7_sha256": sha256_file(mod),
            "stdout": r.stdout.strip().splitlines(),
            "score_w7_sha256": sha256_file(root / "r1w7" / "score_w7.py"),
            "honest_ask_in_copy_sha256": sha256_file(root / "r1w7" / "honest_ask_w7.py")}


# ============================================================================================ step 3: build (in a copy)
def cmd_build(a) -> int:
    pkg = Path(a.pkg).resolve()
    sys.path.insert(0, str(pkg))
    from r1w7 import common_w7 as C            # noqa: E402
    from r1w7 import multi_qty_w7 as MQ        # noqa: E402
    ns = C.setup(helm=False)
    X, K, G = ns.rb.exam_rbw1t, ns.rb.keys_rbw1t, ns.XG
    doc = read_json(a.recipes)
    ids = [r["id"] for r in doc["items"]]
    if len(set(ids)) != len(ids):
        raise SystemExit("REFUSED: duplicate authored ids")
    inputs, keys, raw_by_id, rows = [], [], {}, []
    for r in doc["items"]:
        raw = [x.strip() for x in r["raw_lines"]]
        parsed = [G.parse_line(x) for x in raw]
        if not all(parsed):
            raise SystemExit("REFUSED: a line the frozen grammar does not parse in " + r["id"])
        mults = [Fraction(m) for m in r["multipliers"]]
        if len(mults) != len(raw):
            raise SystemExit("REFUSED: one multiplier per line needed in " + r["id"])
        frame = {"id": r["id"], "noun": r["noun"], "all_parsed": True,
                 "lines": [{"raw": x, "parsed": p} for x, p in zip(raw, parsed)]}
        t = X.turns_for(frame, mults)
        full = {"id": r["id"], "cell": X.cell_of(frame) or "OUTSIDE_FRAME", "n_lines": len(raw), "noun": r["noun"],
                "turns": t["turns"], "n_lessons": t["n_lessons"], "raw_lines": raw, "pantry_lines": t["pantry_lines"],
                "multipliers": [C.ftext(m) for m in mults]}
        if not X.skeleton_ok(full):
            raise SystemExit("REFUSED: the turns do not re-derive from the raw lines in " + r["id"])
        key = MQ.apply(K.key_item(full), raw, G)
        inputs.append(X.host_view(full))
        keys.append(key)
        raw_by_id[r["id"]] = raw
        rows.append({"id": r["id"], "cell": full["cell"], "heads": [p["head"] for p in parsed],
                     "modifiers": [list(p["modifiers"]) for p in parsed], "pantry_lines": t["pantry_lines"],
                     "lesson_names": t["lesson_names"], "key_answer": key["answer"],
                     "why_not": key["representable"]["why_not"]})
    if K.floats_in(keys):
        raise SystemExit("REFUSED: a float in the keys")
    out = Path(a.out_dir)
    h = {"inputs": write_json(out / KEPT["inputs"], {"schema": C.INPUT_SCHEMAS["X7_REAL"], "items": inputs}),  # = custody_w7.real_inputs_doc's shape
         "keys": write_json(out / KEPT["keys"], {"schema": "helm.r1w7.real-keys/1", "keys": keys, "authored_fixture": True,
                                                  "built_by": "rbw1t.keys_rbw1t.key_item + r1w7.multi_qty_w7.apply (A-R1W7-7)"}),
         "raw": write_json(out / KEPT["raw"], {"schema": "helm.r1w7.v73-scorer-path.raw-lines/1", "raw_by_id": raw_by_id,
                                                "authored_fixture": True})}
    write_json(out / "BUILD_REPORT.json", {"files_sha256": h, "rows": rows, "pkg": str(pkg)})
    print(json.dumps({"built": len(inputs), "files_sha256": h}, sort_keys=True))
    return 0


# ============================================================================================ step 5: score (in a copy)
def sentences(rec: Dict[str, Any]) -> List[Optional[str]]:
    """HELM's own loop sentence per played item turn (CHAT: loop.loop_sentence of kind 'turn'; LOOP_ON: reply_adapter)."""
    turns = rec.get("turns") or []
    chat = [t for t in turns if isinstance(t, dict) and t.get("kind") == "turn"]
    if chat:
        return [(t.get("loop") or {}).get("loop_sentence") for t in chat]
    return [t.get("reply_adapter") for t in turns if isinstance(t, dict)]


def cmd_score(a) -> int:
    pkg = Path(a.pkg).resolve()
    sys.path.insert(0, str(pkg))
    from r1w7 import common_w7 as C            # noqa: E402
    from r1w7 import score_w7 as SC            # noqa: E402
    ns = C.setup(helm=False)
    HV = C.load_helm_voice()
    keys = read_json(a.keys)["keys"]
    inputs = read_json(a.inputs)["items"]
    raw = read_json(a.raw)["raw_by_id"]
    doc = C.load_doc(a.unit, a.unit_sha256)
    plain = a.arm in ("CHAT_ON", "CHAT_OFF", "CHAT_ON_REPLAY")       # as merge_r1w7.Run.arm_summary
    amended = "raw_by_id" in inspect.signature(SC.score_real).parameters
    out = (SC.score_real(ns, HV, keys, inputs, doc, plain, raw_by_id=raw) if amended
           else SC.score_real(ns, HV, keys, inputs, doc, plain))
    K = ns.rb.keys_rbw1t
    by_id = {r["id"]: r for r in doc.get("records") or []}
    n_by = {it["id"]: it["n_lessons"] for it in inputs}
    per_q = {p["id"]: p for p in out["per_item"]}
    items = {}
    for key in keys:
        rec = by_id.get(key["id"])
        if rec is None:
            items[key["id"]] = {"missing": True}
            continue
        v = ns.SC6.real_record_view(rec, n_by[key["id"]])
        ls = K.score_lessons(key, v["lessons"])
        q = v["question"]
        qs = K.score_question(key, q.get("status"), q.get("value"), q.get("limiting"), v["lessons"])
        sent = sentences(rec)
        items[key["id"]] = {
            "q": per_q[key["id"]]["q"], "q_recomputed": qs, "lessons": ls,
            "lesson_statuses": [x.get("status") for x in v["lessons"]],
            "lesson_paths": [x.get("path") for x in v["lessons"]],
            "lesson_ingredients": [x.get("ingredient") for x in v["lessons"]],
            "lesson_learned_in_taught_unit": [x.get("learned_in_taught_unit") for x in v["lessons"]],
            "key_q": [x.get("q") for x in key["lessons"]], "key_answer": key["answer"].get("key"),
            "key_yield": key["answer"].get("yield"), "why_not": key["representable"]["why_not"],
            "stock_status": v["stock_status"], "question_status": q.get("status"), "question_value": q.get("value"),
            "question_limiting": q.get("limiting"),
            "unexplained_ask_strict": bool(K.unexplained_ask(key, ls, v["stock_status"], qs)),
            "a11_exempt": per_q[key["id"]].get("a11_exempt"),
            "lesson_sentences": sent[:n_by[key["id"]]], "stock_sentence": (sent[n_by[key["id"]]:] or [None])[0],
            "question_sentence": sent[-1] if sent else None, "scored_reply": rec.get("scored_reply"),
            "crashed": bool(rec.get("crashed")), "error": rec.get("error"),
            "log_len": len(rec.get("log") or []), "wide_audit": rec.get("wide_audit")}
    res = {"arm": a.arm, "pkg": str(pkg), "amended_score_real": amended, "unit_sha256": a.unit_sha256,
           "totals": out["totals"], "a11_exempted_ids": out.get("a11_exempted_ids"), "a11_checks": out.get("a11_checks"),
           "plainness_scored": out.get("plainness_scored"), "per_item_score_real": out["per_item"], "items": items,
           "score_w7_sha256": sha256_file(pkg / "r1w7" / "score_w7.py"),
           "score_w6_file": ns.SC6.__file__, "keys_rbw1t_file": K.__file__}
    sha = write_json(Path(a.out), res)
    print(json.dumps({"scored": len(items), "sha256": sha, "totals": out["totals"]}, sort_keys=True, default=str))
    return 0


# ============================================================================================ step 6: facts
def lessons_of(table, iid, reader, arm) -> List[str]:
    return list(table[iid][reader][arm]["lessons"])


def facts(table: Dict[str, Any], arms: List[str]) -> Dict[str, Any]:
    f: Dict[str, Any] = {}
    d = "AUTHOR73:OR_DANGLING"
    rows = {arm: {"v7.2_lessons": lessons_of(table, d, "v7.2", arm), "v7.3_lessons": lessons_of(table, d, "v7.3", arm),
                  "v7.2_has_wrong_lesson": "WRONG" in lessons_of(table, d, "v7.2", arm),
                  "v7.3_has_wrong_lesson": "WRONG" in lessons_of(table, d, "v7.3", arm)} for arm in arms}
    f["dangling_or_wrong_under_v72_not_under_v73"] = {
        "item": d, "by_arm": rows,
        "holds": all(r["v7.2_has_wrong_lesson"] and not r["v7.3_has_wrong_lesson"] for r in rows.values())}
    a = "AUTHOR73:RANOUT_AMBIG"
    rows = {}
    for arm in arms:
        x = table[a]["v7.3"][arm]
        rows[arm] = {"v7.3_q": x["q"], "v7.3_lessons": x["lessons"], "v7.3_ran_out_lesson_status": x["lesson_statuses"][0],
                     "v7.3_ran_out_lesson_verdict": x["lessons"][0],
                     "v7.2_lessons": lessons_of(table, a, "v7.2", arm),
                     "never_wrong": "WRONG" not in x["lessons"] and x["q"] != "WRONG",
                     "ran_out_lesson_refused_not_learned": x["lessons"][0] == "NOT_LEARNED"
                     and x["lesson_statuses"][0] == REFUSED_RAN_OUT}
    f["ambiguous_ran_out_never_wrong_under_v73"] = {
        "item": a, "ran_out_lesson_index": 0, "refused_status_expected": REFUSED_RAN_OUT, "by_arm": rows,
        "holds": all(r["never_wrong"] and r["ran_out_lesson_refused_not_learned"] for r in rows.values())}
    for name, iid in (("sugar_brown_sugar_same_under_both", "AUTHOR73:SUGAR_PAIR"),
                      ("one_line_or_same_under_both", "AUTHOR73:OR_ONE_LINE")):
        rows = {}
        for arm in arms:
            p, q = table[iid]["v7.2"][arm], table[iid]["v7.3"][arm]
            rows[arm] = {"v7.2": {"q": p["q"], "lessons": p["lessons"]}, "v7.3": {"q": q["q"], "lessons": q["lessons"]},
                         "same_verdicts": p["q"] == q["q"] and p["lessons"] == q["lessons"],
                         "same_statuses_and_values": (p["lesson_statuses"], p["stock_status"], p["question_status"],
                                                      p["question_value"], p["lesson_learned_in_taught_unit"]) ==
                                                     (q["lesson_statuses"], q["stock_status"], q["question_status"],
                                                      q["question_value"], q["lesson_learned_in_taught_unit"])}
        f[name] = {"item": iid, "by_arm": rows, "holds": all(r["same_verdicts"] for r in rows.values())}
    f["all_four_hold"] = all(f[k]["holds"] for k in ("dangling_or_wrong_under_v72_not_under_v73",
                                                     "ambiguous_ran_out_never_wrong_under_v73",
                                                     "sugar_brown_sugar_same_under_both", "one_line_or_same_under_both"))
    return f


# ============================================================================================ main
def run_unit(root: Path, cmd: str, arm: str, inputs: Path, inputs_sha: str, run_dir: Path, label: str) -> Dict[str, Any]:
    scratch = run_dir / "units" / f"{label}_{arm}_scratch"
    out = run_dir / "units" / f"{label}_{arm}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    argv = PY + [str(root / "r1w7" / "units_w7.py"), cmd, "--exam", "X7_REAL", "--arm", arm, "--items", str(inputs),
                 "--items-sha256", inputs_sha, "--scratch", str(scratch), "--out", str(out)]
    t0 = time.time()
    r = subprocess.run(argv, capture_output=True, text=True, timeout=1200, env=child_env(), cwd=str(run_dir))
    secs = round(time.time() - t0, 3)
    if r.returncode != 0 or not out.is_file():
        stop(f"unit {label} {arm} exit {r.returncode}: " + (r.stdout + r.stderr)[-2000:])
    summary = json.loads(r.stdout.strip().splitlines()[-1])
    d = read_json(out)
    return {"label": label, "cmd": cmd, "arm": arm, "out": str(out), "sha256": sha256_file(out), "seconds_wall": secs,
            "summary": summary, "crashed": d.get("crashed"), "items": d.get("items"),
            "helm_now_files_changed": d.get("helm_now_files_changed"), "helm_outside": d.get("helm_outside"),
            "wide_modules_imported": d.get("wide_modules_imported"), "netguard": d.get("netguard"),
            "helm_cut_commit_field": d.get("helm_cut_commit"), "unit_id": d.get("unit_id")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run_scorer_path_v73")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--pkg", required=True)
    b.add_argument("--recipes", required=True)
    b.add_argument("--out-dir", required=True)
    s = sub.add_parser("score")
    for k in ("--pkg", "--arm", "--unit", "--unit-sha256", "--inputs", "--keys", "--raw", "--out"):
        s.add_argument(k, required=True)
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--scratch-root", default=str(SCRATCH_ROOT))
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return cmd_build(a)
    if a.cmd == "score":
        return cmd_score(a)
    return orchestrate(a)


def orchestrate(a) -> int:
    t0 = time.time()
    mem: List[Dict[str, Any]] = []
    memory_gate("start", mem)
    if sha256_file(DESIGN) != DESIGN_SHA256:
        stop("the design file does not hash to its frozen sha256")
    if sha256_file(ZIP) != ZIP_SHA256:
        stop("the v9 zip does not hash to ad3fb98c...")
    wt_reader = WORKTREE / "helm_wide_turn.py"
    if not wt_reader.is_file():
        stop("no helm_wide_turn.py in the worktree " + str(WORKTREE))
    wt_bytes = wt_reader.read_bytes()
    m = re.search(rb'READER_VERSION = "([^"]+)"', wt_bytes)
    run_dir = Path(a.scratch_root) / ("run_%s_%d" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), os.getpid()))
    run_dir.mkdir(parents=True, exist_ok=False)
    print("run dir:", run_dir, flush=True)

    # 1. the copies
    roots, copies = {}, {}
    for reader, label in READERS:
        root = extract(run_dir, label)
        roots[reader] = root
        rd = (root / "helm_now" / "helm_wide_turn.py").read_bytes()
        copies[reader] = {"label": label, "root": str(root),
                          "sealed_reader_sha256": sha256_bytes(rd),
                          "sealed_reader_version": (re.search(rb'READER_VERSION = "([^"]+)"', rd) or [b"", b"?"])[1].decode()}
    swap = rewrite_cut(roots["v7.3"], "helm_wide_turn.py", wt_bytes)
    copies["v7.3"]["swapped"] = swap
    for reader, _label in READERS:
        rd = (roots[reader] / "helm_now" / "helm_wide_turn.py").read_bytes()
        copies[reader]["reader_sha256"] = sha256_bytes(rd)
        copies[reader]["reader_version"] = (re.search(rb'READER_VERSION = "([^"]+)"', rd) or [b"", b"?"])[1].decode()
        copies[reader]["cut_vs_worktree"] = compare_cut_with_worktree(roots[reader])
    if copies["v7.2"]["reader_version"] == copies["v7.3"]["reader_version"]:
        stop("the two copies carry the same READER_VERSION")
    # 2. A-R1W7-11 on the scorer side of each copy
    for reader, _label in READERS:
        copies[reader]["a_r1w7_11"] = apply_a11(roots[reader])
    # 3. inputs, keys, raw lines (built in each copy; byte-equal; checked against the kept copies)
    built = {}
    for reader, label in READERS:
        od = run_dir / ("inputs_" + label)
        r = subprocess.run(PY + [str(Path(__file__).resolve()), "build", "--pkg", str(roots[reader]), "--recipes",
                                 str(RECIPES), "--out-dir", str(od)], capture_output=True, text=True, timeout=600,
                           env=child_env(), cwd=str(run_dir))
        if r.returncode != 0:
            stop(f"build in {label}: " + (r.stdout + r.stderr)[-2000:])
        built[reader] = {k: (od / v) for k, v in KEPT.items()}
    for k in KEPT:
        if built["v7.2"][k].read_bytes() != built["v7.3"][k].read_bytes():
            stop(f"the {KEPT[k]} built in the two copies differ")
    kept = {}
    for k, name in KEPT.items():
        mine = built["v7.2"][k].read_bytes()
        here = HERE / name
        if here.is_file():
            if here.read_bytes() != mine:
                stop(f"{name} beside the script differs from the one rebuilt now (authored inputs changed?)")
            kept[name] = {"sha256": sha256_bytes(mine), "written_now": False}
        else:
            here.write_bytes(mine)
            kept[name] = {"sha256": sha256_bytes(mine), "written_now": True}
    inputs, keys_p, raw_p = built["v7.2"]["inputs"], built["v7.2"]["keys"], built["v7.2"]["raw"]
    inputs_sha = sha256_file(inputs)
    # 4. the package's own unit runner; 5. the package's real scorer
    units, scores = [], {}
    for reader, label in READERS:
        for cmd, arm in UNITS:
            memory_gate(f"unit {label} {arm}", mem)
            u = run_unit(roots[reader], cmd, arm, inputs, inputs_sha, run_dir, label)
            u["reader"] = reader
            units.append(u)
            so = run_dir / "scores" / f"{label}_{arm}.json"
            r = subprocess.run(PY + [str(Path(__file__).resolve()), "score", "--pkg", str(roots[reader]), "--arm", arm,
                                     "--unit", u["out"], "--unit-sha256", u["sha256"], "--inputs", str(inputs),
                                     "--keys", str(keys_p), "--raw", str(raw_p), "--out", str(so)],
                               capture_output=True, text=True, timeout=600, env=child_env(), cwd=str(run_dir))
            if r.returncode != 0:
                stop(f"score {label} {arm}: " + (r.stdout + r.stderr)[-2000:])
            scores[(reader, arm)] = read_json(so)
            scores[(reader, arm)]["_file_sha256"] = sha256_file(so)
    # 6. the reading
    arms = [arm for _c, arm in UNITS]
    recipes = read_json(RECIPES)
    table: Dict[str, Any] = {}
    for it in recipes["items"]:
        table[it["id"]] = {"role": it["role"], "required": it["required"], "raw_lines": it["raw_lines"],
                           "multipliers": it["multipliers"], "noun": it["noun"]}
        for reader, _label in READERS:
            table[it["id"]][reader] = {arm: scores[(reader, arm)]["items"][it["id"]] for arm in arms}
    totals = {reader: {arm: scores[(reader, arm)]["totals"] for arm in arms} for reader, _l in READERS}
    a11 = {reader: {arm: {"amended_score_real": scores[(reader, arm)]["amended_score_real"],
                          "a11_exempted_ids": scores[(reader, arm)]["a11_exempted_ids"],
                          "a11_checks": scores[(reader, arm)]["a11_checks"]} for arm in arms} for reader, _l in READERS}
    fx = facts(table, arms)
    v73_wrong = {arm: {"lessons_WRONG": totals["v7.3"][arm]["lessons_WRONG"], "WRONG": totals["v7.3"][arm]["WRONG"]}
                 for arm in arms}
    reading = {
        "schema": SCHEMA, "design": {"file": "docs/working/r1_wave7/v73_a11/DESIGN_V73_A11.md", "sha256": DESIGN_SHA256,
                                     "section": "4 T3"},
        "claim_status": "scratch test only; reader v7.3 at most ENGINEERED-NOT-VALIDATED; the chat stays NOT LICENSED",
        "scratch_only": True, "cut_commit_field_is_plumbing": True,
        "helm_files_from": "v7.2: the sealed v9 helm_now (cut 55cda1e2); v7.3: the v9 helm_now with ONLY helm_wide_turn.py "
                           "taken from the worktree %s (branch HEAD %s; the file is an uncommitted change there)"
                           % (WORKTREE, git_head_sha()),
        "worktree_reader": {"path": str(wt_reader), "sha256": sha256_bytes(wt_bytes),
                            "reader_version": m.group(1).decode() if m else None,
                            "equals_branch_head_blob": (git_head_blob("helm_wide_turn.py") == wt_bytes)},
        "zip": {"path": str(ZIP), "sha256": ZIP_SHA256}, "deps": str(DEPS), "run_dir": str(run_dir),
        "copies": copies, "authored": {"recipes": str(RECIPES), "recipes_sha256": sha256_file(RECIPES), "kept": kept,
                                       "items": len(recipes["items"])},
        "units": units, "score_files": {f"{r}|{arm}": {"sha256": scores[(r, arm)]["_file_sha256"],
                                                        "score_w7_sha256": scores[(r, arm)]["score_w7_sha256"],
                                                        "score_w6_file": scores[(r, arm)]["score_w6_file"]}
                                         for (r, arm) in scores},
        "per_item": table, "totals": totals, "a_r1w7_11": a11, "facts": fx,
        "design_stop_rule_v73": {"by_arm": v73_wrong,
                                 "no_wrong_under_v73": all(v["lessons_WRONG"] == 0 and v["WRONG"] == 0
                                                           for v in v73_wrong.values())},
        "env_popped_helm_vars": popped_helm_env(), "memory_checks": mem,
        "script_sha256": sha256_file(Path(__file__).resolve()), "python": sys.version.split()[0],
        "seconds_total": round(time.time() - t0, 3)}
    sha = write_json(Path(a.out), reading)
    print(json.dumps({"out": a.out, "sha256": sha, "all_four_hold": fx["all_four_hold"],
                      "design_stop_rule_no_wrong_under_v73": reading["design_stop_rule_v73"]["no_wrong_under_v73"],
                      "seconds": reading["seconds_total"]}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as exc:
        sys.exit(exc.code)
