#!/usr/bin/env python3
"""Pull real HELM chat exchanges from the SPENT c53 exam into helm_hub/chat_samples_c53.json.

The hub's "Talking to HELM" page is built from that JSON, so the hub builds on any machine without the
unit files. Run this script only to refresh the JSON (laptop, 0 USD):

    python -X utf8 -I helm_hub/make_chat_samples.py

Reads the five unit files of job c53 (package v5, exam X7v5). That exam is spent: its item ids are on the
exclusion list of every later draw, so showing its lines tunes nothing. The live exam (c54) is never read.
Set HELM_HUB_UNITS to point at another units folder. Standard library only.

Selection is deterministic (file order), so re-running on the same files gives the same JSON byte for byte
except the generation stamp.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HUB = Path(__file__).resolve().parent
OUT = HUB / "chat_samples_c53.json"
UNITS = Path(os.environ.get(
    "HELM_HUB_UNITS",
    r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\run_c53_r1w7v5_20261020\deliverable_unpacked_a1"
    r"\results\r1w7_host_run\out\r1w7_out\units"))
FILES = {
    "real_on": "W7_X7_REAL_CHAT_ON.json",
    "real_off": "W7_X7_REAL_CHAT_OFF.json",
    "conv_on": "W7_X7_CONV_CHAT_ON.json",
    "noise_on": "W7_X7_NOISE_CHAT_ON.json",
    "loop_on": "W7_X7_REAL_LOOP_ON.json",
}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")
# The known-gap families named in the record (spec sheet 7.104 and 7.106 "Negatives kept").
GAP_FAMILIES = ("S1_WISDOM_STATED", "S2_POWER_STATED", "S7_NOT_A_FACE", "S6_TWO_FACES", "R4_WITNESS_IN_ENGLISH")


def clean(s: str | None) -> str:
    if s is None:
        return ""
    return EMOJI_RE.sub("", EMAIL_RE.sub("[e-mail removed]", str(s)))


def load(key: str) -> tuple[list[dict], str]:
    p = UNITS / FILES[key]
    data = p.read_bytes()
    return json.loads(data.decode("utf-8"))["records"], hashlib.sha256(data).hexdigest()


def turn_status(t: dict) -> str | None:
    return (t.get("loop") or {}).get("status")


def scored_status(rec: dict) -> str | None:
    s = rec.get("scored_turn")
    if isinstance(s, int) and 0 <= s < len(rec["turns"]):
        return turn_status(rec["turns"][s])
    if isinstance(s, dict):
        return s.get("status")
    return turn_status(rec["turns"][-1]) if rec.get("turns") else None


def answered(rec: dict) -> bool:
    return scored_status(rec) == "SUCCESS_EVALUATED"


def transcript(rec: dict, arm: str, note: str = "") -> dict:
    turns = []
    for t in rec["turns"]:
        reply = t.get("reply") or t.get("stdout") or ""
        turns.append({
            "kind": t.get("kind") or "turn",
            "you": clean(t.get("text")),
            "helm": clean(reply).strip() or "(no reply recorded for this turn)",
            "status": turn_status(t) or "none",
        })
    return {
        "id": rec["id"], "family": rec.get("family") or "REAL", "arm": arm,
        "scored_status": scored_status(rec) or "none", "note": note, "turns": turns,
    }


def main() -> int:
    real, h_real = load("real_on")
    real_off, h_off = load("real_off")
    conv, h_conv = load("conv_on")
    noise, h_noise = load("noise_on")
    _loop, h_loop = load("loop_on")
    off_by_id = {r["id"]: r for r in real_off}

    rights = [r for r in real if answered(r)]
    asks = [r for r in real if not answered(r)]

    # 1. three real recipes answered
    real_right = [transcript(r, "CHAT_ON") for r in rights[:3]]
    # 2. the same first recipe with the wide brain OFF
    off = off_by_id.get(rights[0]["id"]) if rights else None
    real_off_same = [transcript(off, "CHAT_OFF", "Same item as the first answered recipe above, with the wide brain switched off.")] if off else []
    # 3. two asks with distinct reasons
    real_ask, seen = [], set()
    for r in asks:
        st = scored_status(r)
        if st in seen:
            continue
        seen.add(st)
        real_ask.append(transcript(r, "CHAT_ON"))
        if len(real_ask) == 2:
            break
    # 4. three dialogues answered, distinct families
    conv_right, fams = [], set()
    for r in conv:
        if answered(r) and r.get("family") not in fams:
            fams.add(r.get("family"))
            conv_right.append(transcript(r, "CHAT_ON"))
        if len(conv_right) == 3:
            break
    # 5. three dialogues HELM could not settle, from the known-gap families, distinct families
    conv_open, fams = [], set()
    for fam in GAP_FAMILIES:
        for r in conv:
            if r.get("family") == fam and not answered(r):
                conv_open.append(transcript(r, "CHAT_ON"))
                break
        if len(conv_open) == 3:
            break
    # 6. two dialogues with small talk, answered
    noise_right = [transcript(r, "NOISE_CHAT_ON") for r in [r for r in noise if answered(r)][:2]]

    conv_by_family = Counter(r.get("family") for r in conv)
    conv_open_by_family = Counter(r.get("family") for r in conv if not answered(r))
    status_counts = Counter(turn_status(t) or "none" for r in real + conv + noise for t in r["turns"])
    out = {
        "job": "c53", "package": "v5", "exam": "X7v5 (spent; ids on the exclusion list)",
        "units_dir": str(UNITS),
        "unit_files": {FILES[k]: h for k, h in (("real_on", h_real), ("real_off", h_off), ("conv_on", h_conv), ("noise_on", h_noise), ("loop_on", h_loop))},
        "counts": {
            "real_items": len(real), "real_answered_by_status": len(rights), "real_asked_by_status": len(asks),
            "real_off_answered_by_status": sum(1 for r in real_off if answered(r)),
            "conv_items": len(conv), "conv_answered_by_status": sum(1 for r in conv if answered(r)),
            "noise_items": len(noise), "noise_answered_by_status": sum(1 for r in noise if answered(r)),
            "noise_turns": sum(1 for r in noise for t in r["turns"] if t.get("kind") == "noise"),
            "conv_by_family": dict(sorted(conv_by_family.items())),
            "conv_not_answered_by_family": dict(sorted(conv_open_by_family.items())),
            "turn_status_counts": dict(sorted(status_counts.items())),
        },
        "samples": {
            "real_right": real_right, "real_off_same": real_off_same, "real_ask": real_ask,
            "conv_right": conv_right, "conv_open": conv_open, "noise_right": noise_right,
        },
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    n = sum(len(v) for v in out["samples"].values())
    print(f"wrote {OUT} ({n} transcripts) from {UNITS}")
    for k, v in out["samples"].items():
        print(f"  {k:<14} {len(v)}  " + ", ".join(x["id"] for x in v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
