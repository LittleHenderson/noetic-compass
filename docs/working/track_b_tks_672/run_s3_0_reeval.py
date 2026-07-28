"""S3-0 — apparatus-only re-evaluation. NO generation. Prereg: PREREG_S3_LOCK.md.

Re-scores the frozen confirmatory items (same 192 texts, same splits) with only
the apparatus corrected:
  - judge key = FULL canonical 28-Foundation definitions (was: register names +
    one-line wants)
  - surface gate = family-grouped CV primary (ungrouped kept as secondary)
  - P12/P63/P74 pairwise boundary baselines measured on the CURRENT items

Cannot authorize v3. Its output is causal diagnosis: how much of the R2/R3/R4
failure was the instrument rather than the items?
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANON = REPO / "docs/working/gate2_closure/matched_ab_20260726/tootra_28_full_definitions.json"
JUNE = REPO / "docs" / "working" / "mtc_f28_goemotions_20260615"
sys.path.insert(0, str(JUNE))

JUDGE_MODEL = "models/gemini-2.5-flash"
PAIRS = {"P12": ("1", "2"), "P63": ("6", "3"), "P74": ("7", "4")}

JUDGE_TMPL = """You are an independent evaluator. You receive scenario text only.
For each row, choose the single best-fitting cell from the 28 canonical definitions
below. Codes are drive digit (1-7) + world letter (a-d).

{defs}

Return JSON only: {{"rows":[{{"id":"...","code":"2b"}}]}}

Rows:
{rows}"""

PAIR_TMPL = """You are an independent evaluator. For each row, decide which of exactly
TWO definitions the scenario's TERMINAL motive better matches. You must pick one.

{defs}

Return JSON only: {{"rows":[{{"id":"...","choice":"<code>"}}]}}

Rows:
{rows}"""


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def log_call(fh_path, model, prompt, raw):
    with open(fh_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"model": model, "prompt_sha256": sha(prompt), "prompt": prompt,
                             "response_raw": raw, "response_sha256": sha(raw)},
                            ensure_ascii=False) + "\n")


def batched_judge(model, tmpl_fill, todo, preds, path, log_path, tag):
    for off in range(0, len(todo), 6):
        batch = todo[off:off + 6]
        prompt = tmpl_fill(batch)
        raw = ""
        for attempt in range(1, 4):
            try:
                resp = model.generate_content(
                    prompt, generation_config={"temperature": 0.0, "max_output_tokens": 8192,
                                               "response_mime_type": "application/json"},
                    request_options={"timeout": 180})
                raw = resp.text
                for row in json.loads(raw).get("rows", []):
                    preds[str(row.get("id"))] = str(row.get("code") or row.get("choice") or "").strip()
                break
            except Exception:  # noqa: BLE001
                time.sleep(2 * attempt)
        log_call(log_path, JUDGE_MODEL, prompt, raw)
        path.write_text(json.dumps(preds, indent=1), encoding="utf-8")
        print(f"  {tag} {min(off + 6, len(todo))}/{len(todo)}", flush=True)


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

    rows = [r for r in json.loads((HERE / "confirm_A0_records.json").read_text(encoding="utf-8"))
            if r.get("candidate_index") and r.get("selected")]
    for r in rows:
        r["item_id"] = f"C_{r['code']}_{r['plan_idx']}_{r['candidate_index']}"
    train = [r for r in rows if not r["heldout"]]
    held = [r for r in rows if r["heldout"]]
    print(f"S3-0 re-eval: {len(rows)} frozen items ({len(train)} train / {len(held)} heldout)")

    # ---- R2_GROUPED_BASELINE (primary) + historical ungrouped (secondary)
    texts = june.strip_texts([r["text"] for r in rows])
    groups = np.array([f"{r['code']}_{r['plan_idx']}" for r in rows])

    def cv(labels, grouped, analyzer, ngr):
        y = np.array(labels)
        hits = []
        if grouped:
            splits = GroupKFold(n_splits=5).split(texts, y, groups)
        else:
            from sklearn.model_selection import KFold
            splits = KFold(n_splits=5, shuffle=True, random_state=0).split(texts)
        for tr, te in splits:
            v = TfidfVectorizer(analyzer=analyzer, ngram_range=ngr).fit([texts[i] for i in tr])
            clf = LogisticRegression(max_iter=3000).fit(v.transform([texts[i] for i in tr]), y[tr])
            hits += list(clf.predict(v.transform([texts[i] for i in te])) == y[te])
        return float(np.mean(hits))

    r2g = {}
    for ax, lab in (("world", [r["world"] for r in rows]),
                    ("drive", [r["drive"] for r in rows]),
                    ("foundation16", [r["code"] for r in rows])):
        r2g[ax] = {"grouped_char": cv(lab, True, "char_wb", (3, 5)),
                   "grouped_word": cv(lab, True, "word", (1, 1)),
                   "ungrouped_word_secondary": cv(lab, False, "word", (1, 1))}
        m = max(r2g[ax]["grouped_char"], r2g[ax]["grouped_word"])
        print(f"  R2-G {ax:13s} grouped max {m:.4f}   (ungrouped secondary "
              f"{r2g[ax]['ungrouped_word_secondary']:.4f})")

    # ---- R3/R4 with FULL canonical definitions
    model = genai.GenerativeModel(JUDGE_MODEL)
    p_path = HERE / "s3_0_judge_preds.json"
    preds = json.loads(p_path.read_text(encoding="utf-8")) if p_path.exists() else {}
    todo = [r for r in rows if r["item_id"] not in preds]
    batched_judge(model,
                  lambda b: JUDGE_TMPL.format(defs=defs_block, rows=json.dumps(
                      [{"id": r["item_id"], "scenario": r["text"]} for r in b])),
                  todo, preds, p_path, HERE / "calls_s3_0.jsonl", "judge28")

    def score(sub):
        w = float(np.mean([preds.get(r["item_id"], "")[1:2] == r["world"] for r in sub]))
        d = float(np.mean([preds.get(r["item_id"], "")[:1] == r["drive"] for r in sub]))
        j = float(np.mean([preds.get(r["item_id"], "") == r["code"] and True for r in sub]))
        j = float(np.mean([(preds.get(r["item_id"], "")[:1] == r["drive"] and
                            preds.get(r["item_id"], "")[1:2] == r["world"]) for r in sub]))
        return w, d, j

    tw, td, tj = score(train)
    hw, hd, hj = score(held)
    print(f"\n  R3 full-canon train:   WORLD={tw:.4f}  DRIVE={td:.4f}  JOINT={tj:.4f}")
    print(f"  R4 full-canon heldout: WORLD={hw:.4f}  DRIVE={hd:.4f}  JOINT={hj:.4f}  "
          f"gap={tj-hj:+.4f}")
    print(f"  (thin-key run was:     train J=0.2222, heldout J=0.3542)")

    # ---- R5 with full-canon judge
    ytr = [r["world"] for r in train]
    yte = [r["world"] for r in held]
    lex = {}
    for name, kw in (("char_3_5gram", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word_tfidf", dict(analyzer="word", ngram_range=(1, 1)))):
        v = TfidfVectorizer(**kw).fit([r["text"] for r in train])
        clf = LogisticRegression(max_iter=3000).fit(v.transform([r["text"] for r in train]), ytr)
        lex[name] = float(np.mean(clf.predict(v.transform([r["text"] for r in held])) == np.array(yte)))
    print(f"  R5 full-canon heldout World: judge={hw:.4f}  char={lex['char_3_5gram']:.4f}  "
          f"tfidf={lex['word_tfidf']:.4f}")

    # ---- P12 / P63 / P74 baselines on current items
    pw_results = {}
    for tag, (da, db) in PAIRS.items():
        sub = [r for r in rows if r["drive"] in (da, db)]
        pp_path = HERE / f"s3_0_pair_{tag}.json"
        pp = json.loads(pp_path.read_text(encoding="utf-8")) if pp_path.exists() else {}
        todo = [r for r in sub if r["item_id"] not in pp]

        def fill(b, da=da, db=db):
            d2 = "\n".join(f"{c}: {defs[c]}" for r in b
                           for c in (da + r["world"], db + r["world"]))
            return PAIR_TMPL.format(defs=d2, rows=json.dumps(
                [{"id": r["item_id"], "scenario": r["text"],
                  "options": [da + r["world"], db + r["world"]]} for r in b]))
        batched_judge(model, fill, todo, pp, pp_path, HERE / "calls_s3_0.jsonl", tag)
        acc = float(np.mean([pp.get(r["item_id"], "")[:1] == r["drive"] for r in sub]))
        pw_results[tag] = {"n_items": len(sub),
                           "n_families": len({(r['code'], r['plan_idx']) for r in sub}),
                           "accuracy": acc, "chance": 0.5}
        print(f"  {tag}: {acc:.4f}  (n={len(sub)} items, chance 0.50)")

    json.dump({"phase": "S3-0", "r2_grouped": r2g,
               "r3_full_canon": {"train": {"world": tw, "drive": td, "joint": tj},
                                 "heldout": {"world": hw, "drive": hd, "joint": hj}},
               "thin_key_reference": {"train_joint": 0.2222, "heldout_joint": 0.3542},
               "r5_full_canon": {"judge_heldout_world": hw, **lex},
               "pairwise_baselines": pw_results,
               "note": "apparatus-only diagnosis; CANNOT authorize v3"},
              open(HERE / "s3_0_results.json", "w"), indent=2, sort_keys=True)
    print("WROTE s3_0_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
