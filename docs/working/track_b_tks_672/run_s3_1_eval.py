"""S3-1 EVAL — full-canon judge, grouped gate, pairwise boundaries, 13-row table.

Bars (frozen in PREREG_S3_LOCK.md and s3_1_frozen_config.json):
  R1 <= 0.05 overall, no cell > 0.15     R1B <= 0.10
  R2-G grouped max <= 0.60 all axes      R3-J >= 0.70 (train)
  R4 heldout >= 0.55 AND gap <= 0.20     R5 judge - each lexical >= 0.10 (heldout World)
  P12 > 0.6833   P63 > 0.7333   P74 > 0.5833   (must IMPROVE on S3-0 baselines)
R6A/R6B rows are PENDING for the motive-repaired instrument — they ran under the
confirmatory prompt, not this one. If every other row is green they must be
re-run before any authorization; the mechanical table cannot go all-green
without them, and no prose override applies.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANON = REPO / "docs/working/gate2_closure/matched_ab_20260726/tootra_28_full_definitions.json"
JUNE = REPO / "docs" / "working" / "mtc_f28_goemotions_20260615"
sys.path.insert(0, str(JUNE))
sys.path.insert(0, str(HERE))
from run_s3_0_reeval import JUDGE_TMPL, PAIR_TMPL, PAIRS, batched_judge  # noqa: E402

JUDGE_MODEL = "models/gemini-2.5-flash"
BASELINES = {"P12": 0.6833, "P63": 0.7333, "P74": 0.5833}


def main() -> int:
    import google.generativeai as genai
    import surface_gate_f28_goemotions as june
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY required")
    genai.configure(api_key=key)
    defs = json.loads(CANON.read_text(encoding="utf-8"))["definitions"]
    defs_block = "\n".join(f"{c}: {defs[c]}" for c in sorted(defs))

    allrows = [r for r in json.loads((HERE / "s3_1_records.json").read_text(encoding="utf-8"))
               if r.get("candidate_index")]
    rows = [r for r in allrows if r.get("selected")]
    for r in rows:
        r["item_id"] = f"S31_{r['code']}_{r['plan_idx']}_{r['candidate_index']}"
    train = [r for r in rows if not r["heldout"]]
    held = [r for r in rows if r["heldout"]]
    print(f"S3-1 eval: {len(rows)} selected ({len(train)} train / {len(held)} heldout)")

    # ---- R1 / R1B from generation records
    by = defaultdict(lambda: [0, 0])
    for r in allrows:
        by[r["code"]][1] += 1
        by[r["code"]][0] += r["leaked_primary"]
    r1_overall = sum(v[0] for v in by.values()) / sum(v[1] for v in by.values())
    r1_worst = max(v[0] / v[1] for v in by.values())
    r1b = sum(r["r1b"] for r in allrows) / len(allrows)
    r1_pass = r1_overall <= 0.05 and r1_worst <= 0.15
    r1b_pass = r1b <= 0.10

    # ---- R2-G grouped surface gate
    texts = june.strip_texts([r["text"] for r in rows])
    groups = np.array([f"{r['code']}_{r['plan_idx']}" for r in rows])

    def gcv(labels, analyzer, ngr):
        y = np.array(labels)
        hits = []
        for tr, te in GroupKFold(n_splits=5).split(texts, y, groups):
            v = TfidfVectorizer(analyzer=analyzer, ngram_range=ngr).fit([texts[i] for i in tr])
            clf = LogisticRegression(max_iter=3000).fit(v.transform([texts[i] for i in tr]), y[tr])
            hits += list(clf.predict(v.transform([texts[i] for i in te])) == y[te])
        return float(np.mean(hits))

    r2g = {}
    for ax, lab in (("world", [r["world"] for r in rows]),
                    ("drive", [r["drive"] for r in rows]),
                    ("foundation16", [r["code"] for r in rows])):
        r2g[ax] = max(gcv(lab, "char_wb", (3, 5)), gcv(lab, "word", (1, 1)))
        print(f"  R2-G {ax:13s} grouped max {r2g[ax]:.4f}")
    r2_pass = all(v <= 0.60 for v in r2g.values())

    # ---- R3/R4 full-canon judge
    model = genai.GenerativeModel(JUDGE_MODEL)
    p_path = HERE / "s3_1_judge_preds.json"
    preds = json.loads(p_path.read_text(encoding="utf-8")) if p_path.exists() else {}
    todo = [r for r in rows if r["item_id"] not in preds]
    batched_judge(model,
                  lambda b: JUDGE_TMPL.format(defs=defs_block, rows=json.dumps(
                      [{"id": r["item_id"], "scenario": r["text"]} for r in b])),
                  todo, preds, p_path, HERE / "calls_s3_1_eval.jsonl", "judge28")

    def score(sub):
        w = float(np.mean([preds.get(r["item_id"], "")[1:2] == r["world"] for r in sub]))
        d = float(np.mean([preds.get(r["item_id"], "")[:1] == r["drive"] for r in sub]))
        j = float(np.mean([(preds.get(r["item_id"], "")[:1] == r["drive"] and
                            preds.get(r["item_id"], "")[1:2] == r["world"]) for r in sub]))
        return w, d, j

    tw, td, tj = score(train)
    hw, hd, hj = score(held)
    r3_pass = tj >= 0.70
    r4_pass = hj >= 0.55 and (tj - hj) <= 0.20
    print(f"\n  R3 train:   W={tw:.4f} D={td:.4f} J={tj:.4f}   (S3-0 old items: J=0.6181)")
    print(f"  R4 heldout: W={hw:.4f} D={hd:.4f} J={hj:.4f}  gap={tj-hj:+.4f}")

    # ---- R5
    ytr, yte = [r["world"] for r in train], [r["world"] for r in held]
    lex = {}
    for name, kw in (("char_3_5gram", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word_tfidf", dict(analyzer="word", ngram_range=(1, 1)))):
        v = TfidfVectorizer(**kw).fit([r["text"] for r in train])
        clf = LogisticRegression(max_iter=3000).fit(v.transform([r["text"] for r in train]), ytr)
        lex[name] = float(np.mean(clf.predict(v.transform([r["text"] for r in held])) == np.array(yte)))
    r5_pass = all(hw - v >= 0.10 for v in lex.values())
    print(f"  R5 heldout World: judge={hw:.4f} char={lex['char_3_5gram']:.4f} "
          f"tfidf={lex['word_tfidf']:.4f}")

    # ---- Pairwise boundaries vs S3-0 baselines
    pw = {}
    for tag, (da, db) in PAIRS.items():
        sub = [r for r in rows if r["drive"] in (da, db)]
        pp_path = HERE / f"s3_1_pair_{tag}.json"
        pp = json.loads(pp_path.read_text(encoding="utf-8")) if pp_path.exists() else {}
        todo = [r for r in sub if r["item_id"] not in pp]

        def fill(b, da=da, db=db):
            d2 = "\n".join(f"{c}: {defs[c]}" for r in b
                           for c in (da + r["world"], db + r["world"]))
            return PAIR_TMPL.format(defs=d2, rows=json.dumps(
                [{"id": r["item_id"], "scenario": r["text"],
                  "options": [da + r["world"], db + r["world"]]} for r in b]))
        batched_judge(model, fill, todo, pp, pp_path, HERE / "calls_s3_1_eval.jsonl", tag)
        acc = float(np.mean([pp.get(r["item_id"], "")[:1] == r["drive"] for r in sub]))
        pw[tag] = {"accuracy": acc, "baseline": BASELINES[tag],
                   "improved": bool(acc > BASELINES[tag]), "n_items": len(sub)}
        print(f"  {tag}: {acc:.4f}  vs S3-0 baseline {BASELINES[tag]}  "
              f"{'IMPROVED' if acc > BASELINES[tag] else 'NOT IMPROVED'}")

    table = {
        "R1": {"pass": bool(r1_pass), "value": f"{r1_overall:.4f} overall, worst {r1_worst:.4f}"},
        "R1B": {"pass": bool(r1b_pass), "value": f"{r1b:.4f}"},
        "R2-G": {"pass": bool(r2_pass), "value": json.dumps({k: round(v, 4) for k, v in r2g.items()})},
        "R3-W": {"pass": None, "value": f"train {tw:.4f}"},
        "R3-D": {"pass": None, "value": f"train {td:.4f}"},
        "R3-J": {"pass": bool(r3_pass), "value": f"train {tj:.4f} (bar 0.70)"},
        "R4": {"pass": bool(r4_pass), "value": f"heldout {hj:.4f}, gap {tj-hj:+.4f}"},
        "R5": {"pass": bool(r5_pass), "value": f"judge {hw:.4f} vs {lex['char_3_5gram']:.4f}/{lex['word_tfidf']:.4f}"},
        "R6A": {"pass": None, "value": "PENDING — confirmatory arms used the pre-repair prompt"},
        "R6B": {"pass": None, "value": "PENDING — confirmatory arms used the pre-repair prompt"},
        "P12": {"pass": pw["P12"]["improved"], "value": f"{pw['P12']['accuracy']:.4f} vs {BASELINES['P12']}"},
        "P63": {"pass": pw["P63"]["improved"], "value": f"{pw['P63']['accuracy']:.4f} vs {BASELINES['P63']}"},
        "P74": {"pass": pw["P74"]["improved"], "value": f"{pw['P74']['accuracy']:.4f} vs {BASELINES['P74']}"},
    }
    required = ["R1", "R1B", "R2-G", "R3-J", "R4", "R5", "R6A", "R6B", "P12", "P63", "P74"]
    greens = all(table[k]["pass"] for k in required if table[k]["pass"] is not None)
    pending = [k for k in required if table[k]["pass"] is None]
    print()
    for k, v in table.items():
        s = "PASS" if v["pass"] else ("PEND" if v["pass"] is None else "FAIL")
        print(f"  {k:6s} {s:5s} {v['value']}")
    verdict = ("ALL_NON_PENDING_PASS_R6_RERUN_REQUIRED" if greens and pending
               else "PASS" if greens else "NOT_AUTHORIZED")
    print(f"\nS3-1 TABLE VERDICT: {verdict}")
    json.dump({"phase": "S3-1-eval", "table": table, "pending": pending,
               "verdict": verdict, "pairwise": pw,
               "r3": {"train": [tw, td, tj], "heldout": [hw, hd, hj]}},
              open(HERE / "s3_1_eval_results.json", "w"), indent=2, sort_keys=True)
    print("WROTE s3_1_eval_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
