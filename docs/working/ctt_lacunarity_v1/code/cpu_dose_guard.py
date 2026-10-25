import json, sys
from pathlib import Path
PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1")
sys.path.insert(0, str(PKG))
from mouth_task import check
fact = set(json.load(open(PKG / "data" / "FACT_WORDS.json", encoding="utf-8")))
function = json.load(open(PKG / "data" / "FUNCTION_WORDS.json", encoding="utf-8"))
exam = [json.loads(l) for l in open(PKG / "data" / "mouth_exam.jsonl", encoding="utf-8") if l.strip()]
G = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\guard")
for tag in ("baseline", "steered", "steered_d0.05", "steered_d0.1", "steered_d0.2", "steered_d0.4"):
    p = G / f"gen_A4-s1_{tag}.jsonl"
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    g = f = 0
    for i, r in enumerate(rows):
        it = exam[i]
        ok, why = check.check(it["situation"], it["input_text"], r["text"], fact, it.get("reading"))
        g += int(ok)
        if ok and check.only_allowed_words(r["text"], set(function) | set(check.WORD_RX.findall(it["input_text"].lower()))):
            f += 1
    n = len(rows)
    print("%-16s rows %d guard %.6f fact %.6f guard_x_fact %.6f" % (tag, n, g / n, f / n, (g / n) * (f / n)))
