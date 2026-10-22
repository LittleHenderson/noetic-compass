"""The custodian's program for TEACH-2 (laptop, 0 USD; TEACH-1's custody_t1.py adapted). A separate session from the
builder runs it, from a fresh extract of the sealed zip, with the owner's recorded line `CUBE EXAM at 1 USD` (typed by
the owner on 2026-10-21, OPEN_QUESTIONS Q8; A-TEACH2-1 item 8; the owner writes nothing else, A-TEACH2-17). Three steps:

  1. approve   writes APPROVAL_RECORD_TEACH2.json from a one-line file holding the owner's exact words (refuses any
               line not in OWNER_LINES, surrounding whitespace, or a newline); binds the zip and freeze sha256.
  2. draw      derives the four seeds (seed_rule_t2), builds the 16 keyed worlds, the 32-slot plans with TRAP lines,
               the quizzes and the planted damage, and writes one WRITER PACKET per world (facts, plan slots, anchor
               words, TRAP decoys) for the AI model writers (contract/WRITER_BRIEF_TEACH2.md). Prints counts and hashes only.
  3. finish    takes the keyed turn file (contract/KEY_FORMAT_TEACH2.md), checks it (floors, anchors, forbidden
               phrases, split, writer families, two keys, HELM's own routing), and writes the exam folder the host
               units read (exam_t2.build_exam with the sealed turns) plus EXAM_CHECK / ROUTE_CHECK. Refuses on any
               problem and names it; a refused turn goes back to its writer (brief rule 9).

    python -X utf8 -B -I <pkg>/teach2/custody_t2.py approve --line-file L.txt --zip Z.zip --source "<where>" --out-dir D
    python -X utf8 -B -I <pkg>/teach2/custody_t2.py draw --approval D/APPROVAL_RECORD_TEACH2.json --zip Z.zip --out-dir D
    python -X utf8 -B -I <pkg>/teach2/custody_t2.py finish --custody D --turns KEYED_TURNS_TEACH2.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from teach2 import common_t2 as C          # noqa: E402
from teach2 import exam_t2 as E            # noqa: E402
from teach2 import seed_rule_t2 as SR      # noqa: E402
from teach2 import worlds_t2 as W          # noqa: E402


def cmd_approve(a) -> int:
    raw = Path(a.line_file).read_bytes()
    line = raw.decode("utf-8")
    if line != line.strip() or "\n" in line or "\r" in line:
        raise SystemExit("REFUSED: the line file must hold one line with no surrounding whitespace or newline")
    if line not in C.OWNER_LINES:
        raise SystemExit(f"REFUSED: not a TEACH-2 line; expected one of {sorted(C.OWNER_LINES)}")
    if not (a.source or "").strip():
        raise SystemExit("REFUSED: name where the owner's words are recorded (--source)")
    freeze = C.read_json(PKG / "PACKAGE_FREEZE.json")
    zsha = C.sha256_file(a.zip)
    rec = {"schema": "helm.teach2.approval/1", "label": C.LABEL, "owner_line_verbatim": line,
           "owner_line_utf8_bytes": len(raw), "owner_line_sha256": hashlib.sha256(raw).hexdigest(),
           "owner_line_source": a.source.strip(), "package_zip": Path(a.zip).name, "package_zip_sha256": zsha,
           "package_freeze_sha256": C.sha256_file(PKG / "PACKAGE_FREEZE.json"), "package_version": freeze.get("package_version"),
           "cap_usd": C.OWNER_LINES[line]["cap_usd"], "host": C.OWNER_LINES[line]["host"],
           "seed_source_rule": "sha256(UTF-8 of the typed line + ':' + the full zip sha256), no trailing newline",
           "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    sha = C.write_json(Path(a.out_dir) / "APPROVAL_RECORD_TEACH2.json", rec)
    print(json.dumps({"approval_sha256": sha, "zip_sha256": zsha, "line_sha256": rec["owner_line_sha256"]}))
    return 0


def cmd_draw(a) -> int:
    apr = C.read_json(a.approval)
    zsha = C.sha256_file(a.zip)
    if zsha != apr["package_zip_sha256"]:
        raise SystemExit("REFUSED: this zip is not the one the approval record binds")
    der = SR.derive(apr["owner_line_verbatim"], zsha)
    out = Path(a.out_dir)
    if der["overlap_check"] != "PASS":
        C.write_json(out / "TEACH2_BLOCKED_SEED.json", der)
        raise SystemExit("STOP: the seed rule found no free slot (TEACH2_BLOCKED_SEED.json)")
    C.write_json(out / "exam" / "SEED_DERIVATION_TEACH2.json", der)
    worlds = W.build_all(der["WORLD"])
    packets = []
    for w in worlds:
        plan = W.teaching_plan(w, der["WORLD"], der["TRAP"])
        packets.append({"world_id": w["world_id"], "template": w["template"], "unit_word": w["unit_word"],
                        "slots": [{"turn_index": s["turn_index"], "kind": s["kind"], "fact_id": s["fact_id"],
                                   "canonical": s["text"], "value": s.get("value"), "not_value": s.get("not_value"),
                                   "trap_role": s.get("trap_role"), "trap": s.get("trap"),
                                   "anchor_words": next((f["anchor_words"] for f in w["facts"] if f["id"] == s["fact_id"]), [])}
                                  for s in plan]})
    pins = {"WRITER_PACKETS_TEACH2.json": C.write_json(out / "exam" / "WRITER_PACKETS_TEACH2.json",
                                                       {"schema": "helm.teach2.writer-packets/1", "packets": packets})}
    print(json.dumps({"worlds": len(worlds), "templates": sorted({w["template"] for w in worlds}),
                      "derivation_sha256": C.sha256_file(out / "exam" / "SEED_DERIVATION_TEACH2.json"), "pins": pins}))
    return 0


def cmd_finish(a) -> int:
    d = Path(a.custody)
    der = C.read_json(d / "exam" / "SEED_DERIVATION_TEACH2.json")
    keyed = C.read_json(a.turns)
    turns = {wid: [{k: t.get(k) for k in ("turn_index", "kind", "fact_id", "text", "value", "not_value", "trap_role", "label",
                                         "writer", "key1", "key2", "keyed")} for t in rows] for wid, rows in keyed["turns"].items()}
    tmp = d / "exam" / "TURNS_SEALED_INPUT.json"
    C.write_json(tmp, turns)
    exam_dir = d / "exam" / "exam_folder"
    E.build_exam(der, exam_dir, practice=False, turns_file=str(tmp))
    rc = subprocess.run([sys.executable, "-X", "utf8", "-B", "-I", str(PKG / "teach2" / "run_t2.py"), "routecheck",
                         "--exam", str(exam_dir), "--out", str(d / "exam")], capture_output=True, text=True)
    chk = C.read_json(d / "exam" / "EXAM_CHECK_TEACH2.json")
    bad = {w: {"problems": r["problems"], "bad_turns": r["bad_turns"]} for w, r in chk["reports"].items() if not r["ok"]}
    print(json.dumps({"route_exit": rc.returncode, "exam_check_all_ok": chk["all_ok"], "worlds_with_problems": sorted(bad)}))
    if bad:
        C.write_json(d / "exam" / "TURN_PROBLEMS_TEACH2.json", bad)
        raise SystemExit("REFUSED: turns need rewriting (TURN_PROBLEMS_TEACH2.json); send each back to its writer")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("approve")
    p.add_argument("--line-file", required=True)
    p.add_argument("--zip", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--out-dir", required=True)
    q = sub.add_parser("draw")
    q.add_argument("--approval", required=True)
    q.add_argument("--zip", required=True)
    q.add_argument("--out-dir", required=True)
    r = sub.add_parser("finish")
    r.add_argument("--custody", required=True)
    r.add_argument("--turns", required=True)
    a = ap.parse_args(argv)
    return {"approve": cmd_approve, "draw": cmd_draw, "finish": cmd_finish}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
