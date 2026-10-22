"""t3_score_v73.py -- DESIGN_V73_A11.md section 4, T3, built as the design says (fix round 2026-10-21, reviewer G-1/G-2):
"end to end through the package's own unit runner and scorer", three scratch copies side by side, the design's 13 items,
both arms, and the section 6 step 3 STOP rule computed by program. Design sha256
57fcc5143d97431f4831b9c231d02c44efc88260da357febfc0b6add17be890a. Laptop only (the design's light-run rule: at least 500 MB
free, checked at the start and before every unit), 0 USD, no network, scratch copies only; never edits the sealed v9 tree;
runs no git command that changes state (read-only `git show` / `git rev-parse` only).

    python -X utf8 -B -I t3_score_v73.py [--out <json>] [--scratch-root <dir>]                 # the T3 run (frozen items)
    python -X utf8 -B -I t3_score_v73.py --probe-items <json> --out <json> [--scratch-root ...] # a labelled probe, not T3

Steps (each refuses and stops on a failed check; there is no silent fallback):
  0. memory floor; the design file's sha256; the v9 zip's sha256; the T3 item list's sha256 (FROZEN_ITEMS_SHA256: the list
     was frozen before any T3 run, so a revised item cannot enter T3 without changing this file, which is a deviation)
  1. three FRESH extracts of the sealed v9 zip under <scratch-root>/t3_<utc>_<pid>/:
       pkg_v72  = helm_now as sealed (reader v7.2)
       pkg_v73r = helm_now with ONLY helm_wide_turn.py, test_helm_reader_gap.py and test_helm_cas_address.py (the pin
                  moved, design 2.6) from the worktree
       pkg_v73  = helm_now with EVERY cut file whose worktree bytes differ from v9 (the v7.3 files and F12's memory
                  files): the cut a v10 reseal would carry
     In each copy the swapped files' sha256 and size are rewritten in contract/HELM_CUT_R1W7.json and the byte-equal
     helm_now/SOURCE_CUT.json (commit field unchanged: scratch plumbing, never sealed).
  2. A-R1W7-11 applied to every copy (docs/working/r1_wave7/a_r1w7_11/apply_amendment_11.py)
  3. the items -> X7_REAL inputs by the frozen rbw1t.exam_rbw1t.turns_for, keys by the frozen rbw1t.keys_rbw1t.key_item +
     A-R1W7-7's multi_qty_w7.apply, raw lines by id; built in every copy (must be byte-equal); in a T3 run checked
     against the copies kept in t3/ (written there on the first T3 run, refused if they ever differ)
  4. the package's own unit runner per copy: r1w7/units_w7.py chat --exam X7_REAL --arm CHAT_ON and loop --arm LOOP_ON
  5. the copy's real r1w7/score_w7.score_real(ns, HV, keys, items, doc, plain, raw_by_id=...) (it calls the frozen
     r1w6.score_w6.score_real), per unit; per-lesson detail by the frozen real_record_view + score_lessons
  6. one JSON: per item, per copy, per arm (verdicts, HELM's statuses and sentences, A-R1W7-11 rows), totals, the design's
     pass condition and STOP rule (T3 only), each design-table row checked (reported only), and the deviations.

Claim status: a scratch test of an unsealed reader and an unsealed instrument amendment; at most ENGINEERED-NOT-VALIDATED;
the chat stays NOT LICENSED. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent                      # .../docs/working/r1_wave7/v73_a11
T3DIR = HERE / "t3"
WORKTREE = HERE.parents[3]
DESIGN = HERE / "DESIGN_V73_A11.md"
DESIGN_SHA256 = "57fcc5143d97431f4831b9c231d02c44efc88260da357febfc0b6add17be890a"
A11_DIR = HERE.parent / "a_r1w7_11"
ITEMS = T3DIR / "T3_ITEMS_V73.json"
FROZEN_ITEMS_SHA256 = "6d0d9990d8ae91295f02cdee966b19f8a2e728423134f1570d6d38c351f8dcad"
ZIP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\build_v9\HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip")
ZIP_SHA256 = "ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c"
PKG_TOP = "HELM_R1_W7_20261020"
DEPS = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\x7v9_custody\pkg\deps")
NEIGHBOUR_ENV = {"R1W7_W1_DIR": "HELM_R1_W1_20261015", "R1W7_W3_DIR": "HELM_R1_W3_20261019",
                 "R1W7_W3B_DIR": "HELM_R1_W3B_20261019", "R1W7_W6_DIR": "HELM_R1_W6_20261019",
                 "R1W7_RBW1T_DIR": "HELM_RBW1T_20261019"}
SCRATCH_ROOT = Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
                    r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch\t3")
KEPT = {"inputs": "INPUTS_REAL_AUTHOR.json", "keys": "AUTHOR_KEYS.json", "raw": "RAW_LINES_AUTHOR.json"}
OUT_DEFAULT = T3DIR / "T3_V73.json"
SWAP_R = ("helm_wide_turn.py", "test_helm_reader_gap.py", "test_helm_cas_address.py")
COPIES = (("v7.2", "pkg_v72"), ("v7.3r", "pkg_v73r"), ("v7.3", "pkg_v73"))
V73 = ("v7.3r", "v7.3")
UNITS = (("chat", "CHAT_ON"), ("loop", "LOOP_ON"))
MEMORY_FLOOR_MIB = 500
MEMORY_WAIT_SECONDS = 300
PY = [sys.executable, "-X", "utf8", "-B", "-I"]
SCHEMA = "helm.r1w7.v73-t3/1"
EXEMPT_WANT = ["AUTHOR:M1", "AUTHOR:P1"]
PHANTOMS = ("AUTHOR:C1", "AUTHOR:C2", "AUTHOR:C3")
FAULT_ITEMS = ("AUTHOR:D1", "AUTHOR:D3", "AUTHOR:A1", "AUTHOR:X2")
#: deviations from the design's T3 text, recorded by this driver (never by editing the design)
DEVIATIONS = [
    "helm files: the design says 'branch head'; the v7.3 files are UNCOMMITTED changes in the worktree on branch "
    "claude/helm-reader-v73-a11-20261021 (no git state may change in this round), so every swapped file is read from the "
    "worktree; F12's memory files are equal to the branch HEAD blobs; each swapped file's worktree sha256 and whether it "
    "equals the HEAD blob are recorded per copy",
    "nouns: the design names the 13 items' raw lines, not their dish nouns; the nouns are the design's T1/T2 nouns (sauce, "
    "cake, batter, stew, pilaf); C4's 'soup' is the item file's own",
    "pkg_v73 does not carry helm_memory_compact.py (not a cut file); helm_memory.py imports it only behind "
    "HELM_MEMORY_COMPACT, which this driver's child environment never sets (every HELM_* variable is removed)",
    "the design's 'expected' table is checked cell by cell and REPORTED only (the design: 'the chat may differ and is "
    "reported as found, never tuned'); the pass condition and the STOP rule are computed exactly as section 4 and "
    "section 6 step 3 state them",
]


# ============================================================================================ helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    return sha256_bytes(Path(p).read_bytes())


def json_bytes(obj, indent=1) -> bytes:
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
    return None


def memory_gate(where: str, log: List[Dict[str, Any]]):
    t0 = time.time()
    first = f = free_mib()
    while f is not None and f < MEMORY_FLOOR_MIB and time.time() - t0 < MEMORY_WAIT_SECONDS:
        time.sleep(5)
        f = free_mib()
    log.append({"where": where, "free_mib": f, "free_mib_first_check": first, "waited_seconds": round(time.time() - t0, 1)})
    if f is None or f < MEMORY_FLOOR_MIB:
        stop(f"free physical memory {f} MiB < {MEMORY_FLOOR_MIB} MiB at {where} (owner's AWS order: no local fallback)")


def child_env() -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("HELM_")}
    for k, d in NEIGHBOUR_ENV.items():
        env[k] = str(DEPS / d)
    return env


def git_ro(args: List[str]) -> Optional[bytes]:
    try:
        r = subprocess.run(["git", "-C", str(WORKTREE)] + args, capture_output=True, timeout=60,
                           env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


# ============================================================================================ step 1: copies
def extract(run_dir: Path, label: str) -> Path:
    dest = run_dir / label
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(ZIP) as zf:
        bad = [n for n in zf.namelist() if n.startswith("/") or ".." in Path(n).parts or not n.startswith(PKG_TOP + "/")]
        if bad:
            stop(f"zip member outside {PKG_TOP}/: {bad[:3]}")
        zf.extractall(dest)
    return dest / PKG_TOP


def swap_files(root: Path, rels: List[str]) -> Dict[str, Any]:
    """helm_now/<rel> := the worktree's bytes for every rel; pins rewritten in the contract and SOURCE_CUT.json."""
    contract = root / "contract" / "HELM_CUT_R1W7.json"
    source_cut = root / "helm_now" / "SOURCE_CUT.json"
    orig = contract.read_bytes()
    if source_cut.read_bytes() != orig:
        stop("SOURCE_CUT.json is not byte-equal to contract/HELM_CUT_R1W7.json in the fresh extract")
    obj = json.loads(orig)
    rows = []
    reserialises = json_bytes(obj) == orig
    text = orig.decode("utf-8")
    for rel in rels:
        if rel not in obj["files"]:
            stop(f"{rel} is not a cut file")
        new_bytes = (WORKTREE / rel).read_bytes()
        old = dict(obj["files"][rel])
        new_pin = {"bytes": len(new_bytes), "sha256": sha256_bytes(new_bytes)}
        if set(old) != set(new_pin):
            stop(f"cut pin of {rel} has fields {sorted(old)}")
        (root / "helm_now" / rel).write_bytes(new_bytes)
        obj["files"][rel] = new_pin
        if not reserialises:
            if text.count(old["sha256"]) != 1:
                stop(f"cut pin sha256 of {rel} not found exactly once")
            text = text.replace(old["sha256"], new_pin["sha256"])
            pat = re.compile(r'("%s":\s*\{\s*"bytes":\s*)%d' % (re.escape(rel), old["bytes"]))
            text, n = pat.subn(lambda m: m.group(1) + str(new_pin["bytes"]), text)
            if n != 1:
                stop(f"cut pin bytes of {rel} not found exactly once")
        head = git_ro(["show", "HEAD:" + rel])
        rows.append({"file": rel, "old": old, "new": new_pin,
                     "worktree_equals_branch_head_blob": (head == new_bytes) if head is not None else None})
    data = json_bytes(obj) if reserialises else text.encode("utf-8")
    contract.write_bytes(data)
    source_cut.write_bytes(data)
    after = json.loads(data)
    if any(after["files"][r["file"]] != r["new"] for r in rows) or after.get("commit") != json.loads(orig).get("commit"):
        stop("cut rewrite check failed")
    return {"swapped": rows, "how": "reserialised" if reserialises else "targeted replacement",
            "commit_field": after.get("commit"), "commit_field_unchanged": True,
            "contract_sha256": sha256_bytes(data), "source_cut_equals_contract": source_cut.read_bytes() == data}


def differing_cut_files(root: Path) -> List[str]:
    cut = read_json(root / "contract" / "HELM_CUT_R1W7.json")
    out = []
    for rel in sorted(cut["files"]):
        wt = WORKTREE / rel
        if not wt.is_file():
            stop(f"cut file {rel} missing in the worktree")
        if wt.read_bytes() != (root / "helm_now" / rel).read_bytes():
            out.append(rel)
    return out


def apply_a11(root: Path) -> Dict[str, Any]:
    tool = A11_DIR / "apply_amendment_11.py"
    r = subprocess.run(PY + [str(tool), str(root)], capture_output=True, text=True, timeout=300, cwd=str(root.parent))
    if r.returncode != 0:
        stop("apply_amendment_11.py refused: " + (r.stdout + r.stderr)[-1500:])
    return {"applied": True, "tool_sha256": sha256_file(tool), "stdout": r.stdout.strip().splitlines(),
            "honest_ask_in_copy_sha256": sha256_file(root / "r1w7" / "honest_ask_w7.py"),
            "score_w7_sha256": sha256_file(root / "r1w7" / "score_w7.py"),
            "merge_r1w7_sha256": sha256_file(root / "r1w7" / "merge_r1w7.py")}


# ============================================================================================ step 3: build (in a copy)
def cmd_build(a) -> int:
    pkg = Path(a.pkg).resolve()
    sys.path.insert(0, str(pkg))
    from r1w7 import common_w7 as C            # noqa: E402
    from r1w7 import multi_qty_w7 as MQ        # noqa: E402
    ns = C.setup(helm=False)
    X, K, G = ns.rb.exam_rbw1t, ns.rb.keys_rbw1t, ns.XG
    doc = read_json(a.items)
    ids = [r["id"] for r in doc["items"]]
    if len(set(ids)) != len(ids):
        raise SystemExit("REFUSED: duplicate ids")
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
        rows.append({"id": r["id"], "heads": [p["head"] for p in parsed], "pantry_lines": t["pantry_lines"],
                     "lesson_names": t["lesson_names"], "key_answer": key["answer"],
                     "why_not": key["representable"]["why_not"], "turns": t["turns"]})
    if K.floats_in(keys):
        raise SystemExit("REFUSED: a float in the keys")
    out = Path(a.out_dir)
    h = {"inputs": write_json(out / KEPT["inputs"], {"schema": C.INPUT_SCHEMAS["X7_REAL"], "items": inputs}),
         "keys": write_json(out / KEPT["keys"], {"schema": "helm.r1w7.real-keys/1", "keys": keys, "authored_fixture": True,
                                                  "built_by": "rbw1t.keys_rbw1t.key_item + r1w7.multi_qty_w7.apply (A-R1W7-7)"}),
         "raw": write_json(out / KEPT["raw"], {"schema": "helm.r1w7.v73-t3.raw-lines/1", "raw_by_id": raw_by_id,
                                                "authored_fixture": True})}
    write_json(out / "BUILD_REPORT.json", {"files_sha256": h, "rows": rows, "pkg": str(pkg)})
    print(json.dumps({"built": len(inputs), "files_sha256": h}, sort_keys=True))
    return 0


# ============================================================================================ step 5: score (in a copy)
def sentences(rec: Dict[str, Any]) -> List[Optional[str]]:
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
    if "raw_by_id" not in inspect.signature(SC.score_real).parameters:
        raise SystemExit("REFUSED: the copy's score_w7.score_real does not carry A-R1W7-11")
    out = SC.score_real(ns, HV, keys, inputs, doc, plain, raw_by_id=raw)
    K = ns.rb.keys_rbw1t
    by_id = {r["id"]: r for r in doc.get("records") or []}
    n_by = {it["id"]: it["n_lessons"] for it in inputs}
    per_q = {p["id"]: p for p in out["per_item"]}
    a11 = {r["id"]: r for r in out.get("a11_checks") or []}
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
            "lesson_ingredients": [x.get("ingredient") for x in v["lessons"]],
            "lesson_learned_in_taught_unit": [x.get("learned_in_taught_unit") for x in v["lessons"]],
            "key_q": [x.get("q") for x in key["lessons"]], "key_heads": [x.get("head") for x in key["lessons"]],
            "key_answer": key["answer"].get("key"), "key_yield": key["answer"].get("yield"),
            "why_not": key["representable"]["why_not"], "stock_status": v["stock_status"],
            "question_status": q.get("status"), "question_value": q.get("value"), "question_limiting": q.get("limiting"),
            "unexplained_ask_strict": bool(K.unexplained_ask(key, ls, v["stock_status"], qs)),
            "a11_exempt": per_q[key["id"]].get("a11_exempt"), "a11_row": a11.get(key["id"]),
            "lesson_sentences": sent[:n_by[key["id"]]], "stock_sentence": (sent[n_by[key["id"]]:] or [None])[0],
            "question_sentence": sent[-1] if sent else None, "scored_reply": rec.get("scored_reply"),
            "crashed": bool(rec.get("crashed")), "error": rec.get("error"), "log_len": len(rec.get("log") or []),
            "log_last_path": ((rec.get("log") or [{}])[-1] or {}).get("path"), "wide_audit": rec.get("wide_audit")}
    res = {"arm": a.arm, "pkg": str(pkg), "unit_sha256": a.unit_sha256, "totals": out["totals"],
           "a11_exempted_ids": out.get("a11_exempted_ids"), "a11_checks": out.get("a11_checks"),
           "per_item_score_real": out["per_item"], "items": items,
           "score_w7_sha256": sha256_file(pkg / "r1w7" / "score_w7.py"),
           "honest_ask_w7_sha256": sha256_file(pkg / "r1w7" / "honest_ask_w7.py"),
           "score_w6_file": ns.SC6.__file__, "keys_rbw1t_file": K.__file__}
    sha = write_json(Path(a.out), res)
    print(json.dumps({"scored": len(items), "sha256": sha, "totals": out["totals"]}, sort_keys=True, default=str))
    return 0


# ============================================================================================ step 6: the reading
NL, L = "NOT_LEARNED", "LEARNED"


def design_rows(iid: str, copy: str, x: Dict[str, Any]) -> Optional[bool]:
    """The design's expected table (section 4), one cell; REPORTED only."""
    v72 = copy == "v7.2"
    ls, q, st = x["lessons"], x["q"], x["lesson_statuses"]
    n = iid.split(":")[1]
    if n in ("D1", "D3"):
        return ls[0] == "WRONG" if v72 else (ls == [NL] * 3 and all(s == "CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE" for s in st))
    if n in ("D2", "D4"):
        return q == "RIGHT" if v72 else (q == "ASKS" and ls == [NL] * 3 and not x["unexplained_ask_strict"])
    if n in ("A1", "X2"):
        return ls[0] == "WRONG" if v72 else ls == [NL, NL, L] if n == "X2" else ls == [NL, L, L]
    if n == "X1":
        return ls == [NL, NL, L] if v72 else ls == [NL] * 3
    if n in ("C1", "C2", "C3"):
        return q == "ASKS" and x["unexplained_ask_strict"] is True and x["a11_exempt"] is False
    if n == "C4":
        return ls[2] == NL and x["unexplained_ask_strict"] is False
    if n in ("M1", "P1"):
        return q == "ASKS" and x["unexplained_ask_strict"] is True and x["a11_exempt"] is True
    return None


def reading_t3(table, totals, a11, arms) -> Dict[str, Any]:
    v73_wrong = {c: {arm: {"lessons_WRONG": totals[c][arm]["lessons_WRONG"], "WRONG": totals[c][arm]["WRONG"]}
                     for arm in arms} for c in V73}
    no_wrong_v73 = all(v["lessons_WRONG"] == 0 and v["WRONG"] == 0 for c in V73 for v in v73_wrong[c].values())
    exempted = {c: {arm: a11[c][arm]["a11_exempted_ids"] for arm in arms} for c, _l in COPIES}
    exact = all(exempted[c][arm] == EXEMPT_WANT for c, _l in COPIES for arm in arms)
    phantom_exempt = {c: {arm: sorted(set(exempted[c][arm] or []) & set(PHANTOMS)) for arm in arms} for c, _l in COPIES}
    no_phantom = all(not phantom_exempt[c][arm] for c, _l in COPIES for arm in arms)
    m1p1_v73 = all(set(EXEMPT_WANT) <= set(exempted[c][arm] or []) for c in V73 for arm in arms)
    fault = {arm: sorted(i for i in FAULT_ITEMS if "WRONG" in table[i]["v7.2"][arm]["lessons"]) for arm in arms}
    exercises = all(fault[arm] for arm in arms)
    cells = {i: {c: {arm: design_rows(i, c, table[i][c][arm]) for arm in arms} for c, _l in COPIES} for i in table
             if isinstance(table[i], dict) and "v7.2" in table[i]}
    mism = [{"item": i, "copy": c, "arm": arm} for i in cells for c in cells[i] for arm in arms if cells[i][c][arm] is False]
    tot_rows = {c: {arm: {"unexplained_asks_strict": totals[c][arm].get("unexplained_asks_strict"),
                          "unexplained_asks_strict_after_a11": totals[c][arm].get("unexplained_asks_strict_after_a11"),
                          "design_strict_5_after_3": totals[c][arm].get("unexplained_asks_strict") == 5
                          and totals[c][arm].get("unexplained_asks_strict_after_a11") == 3}
                    for arm in arms} for c, _l in COPIES}
    return {
        "pass_condition": {
            "v73_lessons_WRONG_and_WRONG_zero_both_arms": no_wrong_v73, "by_copy_arm": v73_wrong,
            "exempted_exactly_M1_P1_every_copy_and_arm": exact, "exempted": exempted,
            "C1_C2_C3_never_exempted": no_phantom, "phantom_exempted": phantom_exempt,
            "v72_shows_a_WRONG_lesson_among_D1_D3_A1_X2_each_arm": exercises, "v72_wrong_lesson_items": fault,
            "holds": no_wrong_v73 and exact and no_phantom and exercises},
        "stop_rule_section_6_step_3": {
            "wrong_lesson_or_answer_under_v73": not no_wrong_v73, "C1_C2_C3_exempted": not no_phantom,
            "M1_or_P1_not_exempted_under_v73": not m1p1_v73,
            "STOP": (not no_wrong_v73) or (not no_phantom) or (not m1p1_v73)},
        "design_table_cells_reported_only": cells, "design_table_mismatches_reported_only": mism,
        "design_totals_reported_only": tot_rows}


def run_unit(root: Path, cmd: str, arm: str, inputs: Path, inputs_sha: str, run_dir: Path, label: str) -> Dict[str, Any]:
    scratch = run_dir / "units" / f"{label}_{arm}_scratch"
    out = run_dir / "units" / f"{label}_{arm}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    argv = PY + [str(root / "r1w7" / "units_w7.py"), cmd, "--exam", "X7_REAL", "--arm", arm, "--items", str(inputs),
                 "--items-sha256", inputs_sha, "--scratch", str(scratch), "--out", str(out)]
    t0 = time.time()
    r = subprocess.run(argv, capture_output=True, text=True, timeout=1200, env=child_env(), cwd=str(run_dir))
    if r.returncode != 0 or not out.is_file():
        stop(f"unit {label} {arm} exit {r.returncode}: " + (r.stdout + r.stderr)[-2000:])
    d = read_json(out)
    return {"label": label, "cmd": cmd, "arm": arm, "out": str(out), "sha256": sha256_file(out),
            "seconds_wall": round(time.time() - t0, 3), "summary": json.loads(r.stdout.strip().splitlines()[-1]),
            "crashed": d.get("crashed"), "items": d.get("items"), "helm_now_files_changed": d.get("helm_now_files_changed"),
            "helm_outside": d.get("helm_outside"), "netguard": d.get("netguard"),
            "helm_cut_commit_field": d.get("helm_cut_commit")}


def orchestrate(a) -> int:
    t0 = time.time()
    mem: List[Dict[str, Any]] = []
    memory_gate("start", mem)
    if sha256_file(DESIGN) != DESIGN_SHA256:
        stop("the design file does not hash to its frozen sha256")
    if sha256_file(ZIP) != ZIP_SHA256:
        stop("the v9 zip does not hash to ad3fb98c...")
    probe = a.probe_items is not None
    items_path = Path(a.probe_items).resolve() if probe else ITEMS
    items_sha = sha256_file(items_path)
    if not probe and items_sha != FROZEN_ITEMS_SHA256:
        stop("T3_ITEMS_V73.json is not the frozen item list (a revised item is a deviation; see the docstring)")
    if probe and items_sha == FROZEN_ITEMS_SHA256:
        stop("--probe-items given the frozen T3 list; run without --probe-items")
    run_dir = Path(a.scratch_root) / ("%s_%s_%d" % ("probe" if probe else "t3", time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                                                    os.getpid()))
    run_dir.mkdir(parents=True, exist_ok=False)
    print("run dir:", run_dir, flush=True)
    roots, copies = {}, {}
    for c, label in COPIES:
        roots[c] = extract(run_dir, label)
        copies[c] = {"label": label, "root": str(roots[c])}
    diff = differing_cut_files(roots["v7.2"])
    for rel in SWAP_R:
        if rel not in diff:
            stop(f"{rel} does not differ from v9 in the worktree; nothing to swap")
    copies["v7.2"]["swap"] = {"swapped": []}
    copies["v7.3r"]["swap"] = swap_files(roots["v7.3r"], list(SWAP_R))
    copies["v7.3"]["swap"] = swap_files(roots["v7.3"], diff)
    for c, _l in COPIES:
        rd = (roots[c] / "helm_now" / "helm_wide_turn.py").read_bytes()
        copies[c]["reader_version"] = (re.search(rb'READER_VERSION = "([^"]+)"', rd) or [b"", b"?"])[1].decode()
        copies[c]["reader_sha256"] = sha256_bytes(rd)
        copies[c]["cut_files_still_differing_from_worktree"] = differing_cut_files(roots[c])
        copies[c]["a_r1w7_11"] = apply_a11(roots[c])
    if copies["v7.2"]["reader_version"] == copies["v7.3r"]["reader_version"]:
        stop("v7.2 and v7.3r carry the same READER_VERSION")
    if copies["v7.3"]["cut_files_still_differing_from_worktree"]:
        stop("pkg_v73 still differs from the worktree in a cut file")
    built = {}
    for c, label in COPIES:
        od = run_dir / ("inputs_" + label)
        r = subprocess.run(PY + [str(Path(__file__).resolve()), "build", "--pkg", str(roots[c]), "--items", str(items_path),
                                 "--out-dir", str(od)], capture_output=True, text=True, timeout=600, env=child_env(),
                           cwd=str(run_dir))
        if r.returncode != 0:
            stop(f"build in {label}: " + (r.stdout + r.stderr)[-2000:])
        built[c] = {k: od / v for k, v in KEPT.items()}
    for k in KEPT:
        if len({built[c][k].read_bytes() for c, _l in COPIES}) != 1:
            stop(f"the {KEPT[k]} built in the copies differ")
    kept = {}
    if not probe:
        for k, name in KEPT.items():
            mine = built["v7.2"][k].read_bytes()
            here = T3DIR / name
            if here.is_file():
                if here.read_bytes() != mine:
                    stop(f"{name} in t3/ differs from the one rebuilt now")
                kept[name] = {"sha256": sha256_bytes(mine), "written_now": False}
            else:
                here.write_bytes(mine)
                kept[name] = {"sha256": sha256_bytes(mine), "written_now": True}
    inputs, keys_p, raw_p = built["v7.2"]["inputs"], built["v7.2"]["keys"], built["v7.2"]["raw"]
    inputs_sha = sha256_file(inputs)
    units, scores = [], {}
    for c, label in COPIES:
        for cmd, arm in UNITS:
            memory_gate(f"unit {label} {arm}", mem)
            u = run_unit(roots[c], cmd, arm, inputs, inputs_sha, run_dir, label)
            u["copy"] = c
            units.append(u)
            so = run_dir / "scores" / f"{label}_{arm}.json"
            r = subprocess.run(PY + [str(Path(__file__).resolve()), "score", "--pkg", str(roots[c]), "--arm", arm,
                                     "--unit", u["out"], "--unit-sha256", u["sha256"], "--inputs", str(inputs),
                                     "--keys", str(keys_p), "--raw", str(raw_p), "--out", str(so)],
                               capture_output=True, text=True, timeout=600, env=child_env(), cwd=str(run_dir))
            if r.returncode != 0:
                stop(f"score {label} {arm}: " + (r.stdout + r.stderr)[-2000:])
            scores[(c, arm)] = read_json(so)
            scores[(c, arm)]["_file_sha256"] = sha256_file(so)
    arms = [arm for _c, arm in UNITS]
    doc = read_json(items_path)
    table: Dict[str, Any] = {}
    for it in doc["items"]:
        table[it["id"]] = {k: it.get(k) for k in ("noun", "raw_lines", "multipliers", "design_v72", "design_v73", "why")}
        for c, _l in COPIES:
            table[it["id"]][c] = {arm: scores[(c, arm)]["items"][it["id"]] for arm in arms}
    totals = {c: {arm: scores[(c, arm)]["totals"] for arm in arms} for c, _l in COPIES}
    a11 = {c: {arm: {"a11_exempted_ids": scores[(c, arm)]["a11_exempted_ids"], "a11_checks": scores[(c, arm)]["a11_checks"]}
               for arm in arms} for c, _l in COPIES}
    head = (git_ro(["rev-parse", "HEAD"]) or b"").decode().strip() or None
    reading = {
        "schema": SCHEMA, "kind": "PROBE (not T3; no T3 claim)" if probe else "T3",
        "design": {"file": "docs/working/r1_wave7/v73_a11/DESIGN_V73_A11.md", "sha256": DESIGN_SHA256, "section": "4 T3"},
        "claim_status": "scratch test only; reader v7.3 and A-R1W7-11 at most ENGINEERED-NOT-VALIDATED; the chat stays NOT LICENSED",
        "scratch_only": True, "cut_commit_field_is_plumbing": True,
        "helm_files_from": "branch head %s of %s, with the worktree's uncommitted v7.3 files (see deviations)" % (head, WORKTREE),
        "items": {"file": str(items_path), "sha256": items_sha, "frozen_t3_list": not probe, "count": len(doc["items"])},
        "zip": {"path": str(ZIP), "sha256": ZIP_SHA256}, "deps": str(DEPS), "run_dir": str(run_dir), "copies": copies,
        "kept": kept, "units": units,
        "score_files": {f"{c}|{arm}": {"sha256": scores[(c, arm)]["_file_sha256"],
                                       "score_w7_sha256": scores[(c, arm)]["score_w7_sha256"],
                                       "honest_ask_w7_sha256": scores[(c, arm)]["honest_ask_w7_sha256"],
                                       "score_w6_file": scores[(c, arm)]["score_w6_file"]} for (c, arm) in scores},
        "per_item": table, "totals": totals, "a_r1w7_11": a11, "deviations": DEVIATIONS,
        "memory_checks": mem, "script_sha256": sha256_file(Path(__file__).resolve()), "python": sys.version.split()[0],
        "seconds_total": None}
    if not probe:
        reading.update(reading_t3(table, totals, a11, arms))
    reading["seconds_total"] = round(time.time() - t0, 3)
    sha = write_json(Path(a.out), reading)
    summary = {"out": a.out, "sha256": sha, "kind": reading["kind"], "seconds": reading["seconds_total"]}
    if not probe:
        summary.update(pass_condition=reading["pass_condition"]["holds"],
                       STOP=reading["stop_rule_section_6_step_3"]["STOP"],
                       design_table_mismatches=len(reading["design_table_mismatches_reported_only"]))
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="t3_score_v73")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--pkg", required=True)
    b.add_argument("--items", required=True)
    b.add_argument("--out-dir", required=True)
    s = sub.add_parser("score")
    for k in ("--pkg", "--arm", "--unit", "--unit-sha256", "--inputs", "--keys", "--raw", "--out"):
        s.add_argument(k, required=True)
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--scratch-root", default=str(SCRATCH_ROOT))
    ap.add_argument("--probe-items", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return cmd_build(a)
    if a.cmd == "score":
        return cmd_score(a)
    return orchestrate(a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as exc:
        sys.exit(exc.code)
