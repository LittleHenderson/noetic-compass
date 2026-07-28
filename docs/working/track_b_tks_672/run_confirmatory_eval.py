"""CONFIRMATORY-PILOT-R1-R6 — evaluation stage: R2, R3, R4, R5.

Runs ONLY on the frozen A0 selected corpus (192 items, 64 complete families).
Judge calls are logged with the same replayability standard as generation.

  R2  June surface gate (frozen functions, hash-bound, threshold 0.60)
  R3  blind judge world/drive recovery on TRAIN-family items; gate R3-JOINT >= 0.70
  R4  held-out family transfer: heldout joint >= 0.55 AND (train - heldout) <= 0.20
  R5  lexical resistance: judge beats char 3-5gram AND word TF-IDF on held-out
      World by >= 0.10 (baselines trained on train-family items only)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
JUNE = REPO / "docs" / "working" / "mtc_f28_goemotions_20260615"
sys.path.insert(0, str(JUNE))
sys.path.insert(0, str(HERE))

WORLD_NAMES = {"a": "Spiritual", "b": "Mental", "c": "Emotional", "d": "Physical"}
DRIVES = {"1": "desire to be and be with God", "2": "wisdom, insight, and knowledge",
          "3": "life, vitality, and health", "4": "companionship, love, and friendship",
          "5": "worldly power, influence, and control", "6": "material food and things",
          "7": "lust, sex, and reproduction"}

JUDGE_MODEL = "models/gemini-2.5-flash"
JUDGE_TMPL = """You are an independent evaluator. You receive scenario text only.
For each row, identify which interpretive register the DECISIVE success condition
occupies, and which fundamental want drives the actor.

Registers: a={a}, b={b}, c={c}, d={d}
Wants: {drives}

Return JSON only: {{"rows":[{{"id":"...","world":"a|b|c|d","drive":"1|2|3|4|5|6|7"}}]}}

Rows:
{rows}"""


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    import google.generativeai as genai
    import surface_gate_f28_goemotions as june

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY required")
    genai.configure(api_key=key)
    if june.THRESHOLD != 0.60:
        raise SystemExit("June threshold drift")

    rows = [r for r in json.loads((HERE / "confirm_A0_records.json").read_text(encoding="utf-8"))
            if r.get("candidate_index") and r.get("selected")]
    for i, r in enumerate(rows):
        r["item_id"] = f"C_{r['code']}_{r['plan_idx']}_{r['candidate_index']}"
    train = [r for r in rows if not r["heldout"]]
    held = [r for r in rows if r["heldout"]]
    print(f"selected corpus: {len(rows)} items ({len(train)} train-family, {len(held)} held-out)")

    # ---- R2: June surface gate, frozen functions
    stripped = june.strip_texts([r["text"] for r in rows])
    r2 = {"foundation_16cell": june.cv_accuracy(stripped, [r["code"] for r in rows]),
          "world": june.cv_accuracy(stripped, [r["world"] for r in rows]),
          "drive": june.cv_accuracy(stripped, [r["drive"] for r in rows])}
    r2_pass = all(v <= june.THRESHOLD for v in r2.values())
    print(f"\nR2 June gate (threshold {june.THRESHOLD}):")
    for k, v in r2.items():
        print(f"   {k:20s} {v:.4f}  {'OK' if v <= june.THRESHOLD else 'OVER'}")

    # ---- R3/R4: blind judge, logged
    model = genai.GenerativeModel(JUDGE_MODEL)
    preds_path = HERE / "confirm_judge_preds.json"
    preds = json.loads(preds_path.read_text(encoding="utf-8")) if preds_path.exists() else {}
    todo = [r for r in rows if r["item_id"] not in preds]
    for off in range(0, len(todo), 7):
        batch = todo[off:off + 7]
        prompt = JUDGE_TMPL.format(
            a=WORLD_NAMES["a"], b=WORLD_NAMES["b"], c=WORLD_NAMES["c"], d=WORLD_NAMES["d"],
            drives=json.dumps(DRIVES),
            rows=json.dumps([{"id": r["item_id"], "scenario": r["text"]} for r in batch]))
        raw = ""
        for attempt in range(1, 4):
            try:
                resp = model.generate_content(
                    prompt, generation_config={"temperature": 0.0, "max_output_tokens": 4096,
                                               "response_mime_type": "application/json"},
                    request_options={"timeout": 180})
                raw = resp.text
                got = json.loads(raw)
                for row in got.get("rows", []):
                    preds[str(row.get("id"))] = {"world": str(row.get("world", "")).strip().lower()[:1],
                                                 "drive": str(row.get("drive", "")).strip()[:1]}
                break
            except Exception as exc:  # noqa: BLE001
                time.sleep(2 * attempt)
        with open(HERE / "calls_judge.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"model": JUDGE_MODEL, "prompt_sha256": sha(prompt),
                                 "prompt": prompt, "response_raw": raw,
                                 "response_sha256": sha(raw)}, ensure_ascii=False) + "\n")
        preds_path.write_text(json.dumps(preds, indent=1), encoding="utf-8")
        print(f"  judged {len(preds)}/{len(rows)}", flush=True)

    def score(subset):
        w = np.mean([preds.get(r["item_id"], {}).get("world") == r["world"] for r in subset])
        d = np.mean([preds.get(r["item_id"], {}).get("drive") == r["drive"] for r in subset])
        j = np.mean([preds.get(r["item_id"], {}).get("world") == r["world"] and
                     preds.get(r["item_id"], {}).get("drive") == r["drive"] for r in subset])
        return float(w), float(d), float(j)

    tw, td, tj = score(train)
    hw, hd, hj = score(held)
    r3_pass = tj >= 0.70
    r4_pass = hj >= 0.55 and (tj - hj) <= 0.20
    print(f"\nR3 (train families): WORLD={tw:.4f}  DRIVE={td:.4f}  JOINT={tj:.4f}  bar 0.70")
    print(f"R4 (held-out):       WORLD={hw:.4f}  DRIVE={hd:.4f}  JOINT={hj:.4f}  "
          f"bars: joint>=0.55, gap<=0.20 (gap={tj-hj:+.4f})")

    # ---- R5: lexical resistance on held-out World
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    Xtr_t = [r["text"] for r in train]
    ytr = [r["world"] for r in train]
    Xte_t = [r["text"] for r in held]
    yte = [r["world"] for r in held]
    lex = {}
    for name, kw in (("char_3_5gram", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word_tfidf", dict(analyzer="word", ngram_range=(1, 1)))):
        v = TfidfVectorizer(**kw).fit(Xtr_t)
        clf = LogisticRegression(max_iter=3000).fit(v.transform(Xtr_t), ytr)
        lex[name] = float(np.mean(clf.predict(v.transform(Xte_t)) == np.array(yte)))
    r5_pass = all(hw - v >= 0.10 for v in lex.values())
    print(f"\nR5 held-out World: judge={hw:.4f}  char={lex['char_3_5gram']:.4f}  "
          f"tfidf={lex['word_tfidf']:.4f}  bar: judge - each >= 0.10")

    verdicts = {"R2_june_gate": bool(r2_pass), "R3_joint_train": bool(r3_pass),
                "R4_heldout_transfer": bool(r4_pass), "R5_lexical_resistance": bool(r5_pass)}
    print()
    for k, v in verdicts.items():
        print(f"  {k:24s} {'PASS' if v else 'FAIL'}")
    overall = all(verdicts.values())
    print(f"\nEVAL VERDICT: {'R2-R5 ALL PASS' if overall else 'NOT ALL PASS — v3 NOT authorized'}")

    json.dump({"n_items": len(rows), "r2": r2, "r2_threshold": june.THRESHOLD,
               "r3": {"world": tw, "drive": td, "joint": tj},
               "r4": {"world": hw, "drive": hd, "joint": hj, "gap": tj - hj},
               "r5": {"judge_heldout_world": hw, **lex},
               "verdicts": verdicts, "all_pass": overall},
              open(HERE / "confirm_eval_results.json", "w"), indent=2, sort_keys=True)
    print("WROTE confirm_eval_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
