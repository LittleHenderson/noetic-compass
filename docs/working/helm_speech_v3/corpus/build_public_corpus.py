"""Build a public conversational corpus from human-written sources.

Research use only (owner decision 2026-10-26: HELM is a research project). Rules applied here:
- human-written only: OASST1 rows flagged `synthetic` are dropped, so no foreign model output is used as a target;
- English only, short everyday turns, no links, no code, no assistant boilerplate;
- deduplicated by (user, reply);
- provenance and licence recorded on every row.

    python build_public_corpus.py [--max-pairs 60000]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "public_corpus" / "raw"
OUT = HERE / "data" / "public_corpus"
OASST1_READY = "2023-04-12_oasst_ready.messages.jsonl.gz"
OASST1_URL = "https://huggingface.co/datasets/OpenAssistant/oasst1/resolve/main/" + OASST1_READY

URL_RX = re.compile(r"https?://|www\.", re.I)
CODE_RX = re.compile(r"[{}<>`#*|]{1,}|;\s*$")
BOILERPLATE = ("as an ai", "language model", "i cannot", "i'm sorry, but as", "openai", "chatgpt")


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def clean(text: str) -> str:
    t = " ".join((text or "").split())
    return t


def good_turn(text: str) -> bool:
    t = clean(text)
    w = len(t.split())
    if w < 3 or w > 60:
        return False
    low = t.lower()
    if any(b in low for b in BOILERPLATE):
        return False
    if URL_RX.search(t) or CODE_RX.search(t):
        return False
    if sum(c.isdigit() for c in t) > 12:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pairs", type=int, default=60000)
    a = ap.parse_args()
    path = download(OASST1_URL, RAW / OASST1_READY)

    messages = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except Exception:
                continue
            messages[m["message_id"]] = m

    rows, seen = [], set()
    for mid, m in messages.items():
        if m.get("role") != "assistant" or m.get("lang") != "en" or m.get("deleted"):
            continue
        if m.get("synthetic"):
            continue
        reply = clean(m.get("text"))
        parent = messages.get(m.get("parent_id") or "")
        if not parent or parent.get("role") != "prompter" or parent.get("lang") != "en":
            continue
        user = clean(parent.get("text"))
        if not good_turn(reply) or not good_turn(user):
            continue
        ctx = []
        cur = parent
        for _ in range(2):
            gp = messages.get(cur.get("parent_id") or "")
            if not gp:
                break
            ctx.append(f"{gp.get('role')}: {clean(gp.get('text'))[:200]}")
            cur = gp
        ctx.reverse()
        key = hashlib.sha256((user + "\x00" + reply).encode("utf-8")).hexdigest()[:20]
        if key in seen:
            continue
        seen.add(key)
        rows.append({"source": "oasst1", "licence": "Apache-2.0", "synthetic": False,
                     "user": user, "reply": reply, "context": ctx,
                     "rank": m.get("rank"), "message_id": mid})
        if len(rows) >= a.max_pairs:
            break

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "oasst1_turns.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    users = {r["user"] for r in rows}
    stats = {"source": "oasst1", "licence": "Apache-2.0", "pairs": len(rows), "distinct_user_turns": len(users),
             "mean_user_words": round(sum(len(r["user"].split()) for r in rows) / max(1, len(rows)), 2),
             "mean_reply_words": round(sum(len(r["reply"].split()) for r in rows) / max(1, len(rows)), 2),
             "with_context": sum(1 for r in rows if r["context"]), "file": str(out)}
    (OUT / "oasst1_stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    for r in rows[:8]:
        print("USER:", r["user"][:90])
        print("HELM:", r["reply"][:90])
    return 0


if __name__ == "__main__":
    sys.exit(main())
