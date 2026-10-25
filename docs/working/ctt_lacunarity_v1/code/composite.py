"""Composite score per model: guard x fact exactness x round-trip, failures counted.

    python composite.py --scored <rt-scored jsonl> ...
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG))
from mouth_task import check

FACT = ("ANSWER", "SAYBACK", "ASK")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", nargs="+", required=True)
    a = ap.parse_args()
    function = json.load(open(PKG / "data" / "FUNCTION_WORDS.json", encoding="utf-8"))
    out = {}
    for path in a.scored:
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        n = len(rows)
        guard = sum(1 for r in rows if r["guard_ok"]) / n
        fact = [r for r in rows if r["situation"] in FACT]
        exact = sum(1 for r in fact if r["guard_ok"] and check.only_allowed_words(
            r["text"], set(function) | set(check.WORD_RX.findall(r["input_text"].lower())))) / max(1, len(fact))
        rt = sum(1 for r in fact if r.get("round_trip") is True) / max(1, len(fact))
        name = Path(path).stem.replace("gen_", "").replace("_scored", "")
        out[name] = {"rows": n, "fact_rows": len(fact), "guard": round(guard, 6),
                     "fact_exact": round(exact, 6), "round_trip": round(rt, 6),
                     "composite": round(guard * exact * rt, 6)}
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
