"""Run ONE Unity Eye self-scan (the U3-T1 scanner) on a built test copy of HELM's state and print it as JSON.

Called by helm_ui/server.py in its own process, because the U3 package loads its own pinned copies of HELM modules.
Read-only: the U3 package is imported, never edited. The world is a dev-seed copy (salt "dev", the U3 tests' own
convention), never a scored world. Arm OWNER_INITIATED/REPORT_ONLY: the owner asked, the Eye reports, no whisper.
The Eye writes nothing to the brain; the counts below come from the run itself.

    python -I helm_ui/eye_runner.py --codex-day C:\\Users\\wakil\\Documents\\Codex\\2026-10-19 --world clean|fault
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys

WORLDS = {"clean": ("C003", "a clean copy"), "fault": ("P4-04", "a copy with one planted fault")}
ARM = "OWNER_INITIATED/REPORT_ONLY"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codex-day", required=True)
    ap.add_argument("--world", choices=sorted(WORLDS), default="clean")
    a = ap.parse_args()
    sys.path.insert(0, a.codex_day)
    wid, label = WORLDS[a.world]
    with contextlib.redirect_stdout(io.StringIO()):
        from u3_t1 import world as W, arms as A  # noqa: E402
        spec = W.make_spec(wid, salt="dev")
        r = A.Runner(spec, ARM, match_units=200, keep_reports=True)
        res = r.run()
    done = [x for x in r.reports if x["status"] == "COMPLETE"]
    if not done:
        print(json.dumps({"ok": False, "wired": True, "reason": "no complete scan in this run"}))
        return 0
    plain = next((x for x in done if x["report"]["register"] == "f"), done[0])
    full = next((x for x in reversed(done) if x["report"]["register"] == "A"), done[-1])

    def sentences(rep):
        return [{"kind": s["kind"], "text": s["text"], "cites": s.get("cites", [])}
                for s in rep["report"]["sentences"] if s["kind"] != "TECHNICAL"]

    tech = next((s["text"] for s in full["report"]["sentences"] if s["kind"] == "TECHNICAL"), None)
    findings = [{"check": f.get("check"), "code": f.get("code"), "object": f.get("object"),
                 "plain": f.get("plain_label"), "evidence": f.get("evidence")} for f in full.get("findings", [])]
    out = {
        "ok": True, "wired": True,
        "what": f"Self-check on {label} of HELM's state (synthetic test world {wid}, dev seed). "
                "It does not read this chat session.",
        "world": a.world, "world_id": wid, "salt": "dev", "arm": ARM,
        "plain": sentences(plain), "itemized": sentences(full), "technical": tech, "findings": findings,
        "dropped_sentences": len(full["report"].get("dropped", [])),
        "eye_writes_to_brain": res.get("eye_writes_to_brain"), "whisper_writes": res.get("whisper_writes"),
        "reads_total": res.get("reads_total"), "scans_complete": len(done),
        "scan_digest": full.get("digest"), "log_read_back_ok": full.get("read_back_ok"),
        "self_notice_cas": full.get("self_notice_cas"), "body_scan_cas": full.get("body_scan_cas"),
        "source": "Documents/Codex/2026-10-19/u3_t1 (U3-T1 scanner, imported read-only)",
    }
    print(json.dumps(out, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
