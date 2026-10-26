"""Add DailyDialog and EmpatheticDialogues to the public corpus, then combine with OASST1.

Research use only (owner decision 2026-10-26). Licences:
- DailyDialog: CC BY-NC-SA 4.0 (non-commercial, share-alike) — used here for research; weights trained on it must not
  be shipped commercially.
- EmpatheticDialogues: CC BY-NC 4.0 (verify on its card) — same restriction.
- OASST1: Apache-2.0.

    python build_warm_corpus.py
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "public_corpus" / "raw"
OUT = HERE / "data" / "public_corpus"
URL_RX = re.compile(r"https?://|www\.", re.I)
CODE_RX = re.compile(r"[{}<>`#*|]{1,}")
BAD = ("as an ai", "language model", "chatgpt", "openai")


def clean(t: str) -> str:
    return " ".join((t or "").split())


def ok(t: str, lo: int = 2, hi: int = 60) -> bool:
    t = clean(t)
    w = len(t.split())
    if w < lo or w > hi:
        return False
    low = t.lower()
    if any(b in low for b in BAD) or URL_RX.search(t) or CODE_RX.search(t):
        return False
    return True


def daily_dialog():
    import zipfile
    path = RAW / "dd" / "train" / "dialogues_train.txt"
    rows = []
    if not path.exists():
        z = RAW / "dd_train.zip"
        if not z.exists():
            return rows
        with zipfile.ZipFile(z) as zf:
            name = next((n for n in zf.namelist() if n.endswith("dialogues_train.txt")), None)
            if not name:
                return rows
            lines = zf.read(name).decode("utf-8", errors="replace").splitlines()
    else:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        utts = [clean(u) for u in line.split("__eou__") if clean(u)]
        for a, b in zip(utts, utts[1:]):
            if ok(a) and ok(b):
                rows.append({"source": "dailydialog", "licence": "CC BY-NC-SA 4.0",
                             "user": a, "reply": b, "context": [], "synthetic": False})
    return rows


def empathetic():
    path = RAW / "ed_train.csv"
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                hist = ast.literal_eval(r.get("chat_history") or "[]")
            except Exception:
                hist = []
            user = clean(r.get("situation") or (hist[0] if hist else ""))
            reply = clean(r.get("sys_response") or "")
            ctx = []
            for h in hist[-2:]:
                if isinstance(h, str) and clean(h):
                    ctx.append("user: " + clean(h)[:200])
            if ok(user, 3, 80) and ok(reply):
                rows.append({"source": "empathetic_dialogues", "licence": "CC BY-NC 4.0",
                             "user": user, "reply": reply, "context": ctx,
                             "emotion": r.get("emotion"), "synthetic": False})
    return rows


def main() -> int:
    oasst = [json.loads(l) for l in open(OUT / "oasst1_turns.jsonl", encoding="utf-8")] if (OUT / "oasst1_turns.jsonl").exists() else []
    dd = daily_dialog()
    ed = empathetic()
    all_rows, seen = [], set()
    for r in oasst + dd + ed:
        key = hashlib.sha256((r["user"] + "\x00" + r["reply"]).encode("utf-8")).hexdigest()[:20]
        if key in seen:
            continue
        seen.add(key)
        all_rows.append(r)
    out = OUT / "public_turns.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_rows), encoding="utf-8")
    by = {}
    for r in all_rows:
        by.setdefault(r["source"], 0)
        by[r["source"]] += 1
    stats = {"total_pairs": len(all_rows), "by_source": by,
             "licences": {"oasst1": "Apache-2.0", "dailydialog": "CC BY-NC-SA 4.0",
                          "empathetic_dialogues": "CC BY-NC 4.0"},
             "mean_words_reply": round(sum(len(r["reply"].split()) for r in all_rows) / max(1, len(all_rows)), 2),
             "file": str(out)}
    (OUT / "public_corpus_stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    for src in by:
        print("\n---", src)
        for r in [x for x in all_rows if x["source"] == src][:4]:
            print("  U:", r["user"][:80])
            print("  R:", r["reply"][:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
