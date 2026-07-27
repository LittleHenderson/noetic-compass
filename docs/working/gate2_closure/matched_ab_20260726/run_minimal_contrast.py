"""MINIMAL-CONTRAST-PILOT-v2 — prereg 75672116, locked while v1 had judged ZERO items.

Owner-specified design. 84 items, three per Foundation, ALL THREE WRITTEN FROM ONE
SHARED PLAN so the contrast is controlled:

    target                  the positive item
    same_drive_diff_world   tests World discrimination
    same_world_diff_drive   tests drive discrimination

PRIMARY endpoint is pairwise minimal-contrast accuracy (forced two-way, chance 0.50).
28-way is secondary, decomposed into world (chance 0.25) and drive (chance 0.1429),
because a judge can recover one while confusing the other.

The author NEVER sees the judge's output. Rejected items are counted and reported,
never silently regenerated.
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
sys.path.insert(0, str(HERE))
import run_matched_ab as R  # noqa: E402
import judge_parse_repair  # noqa: E402

CHOICES = R.june_judge.load_foundation_choices(R.CANONICAL_TKS)
SPEC = (HERE / "owner_scenario_spec.md").read_text(encoding="utf-8")

AUTHOR_MODEL = "models/gemini-2.5-flash-lite"
JUDGE_MODEL = "models/gemini-2.5-flash"
TEMPERATURE = 0.95
SEED = 20260727
RETRY_LIMIT = 2                      # transport errors ONLY, never quality
LENGTH_RANGE = (60, 220)             # words; outside -> rejected, NOT regenerated
WORLDS = {"a": "Spiritual", "b": "Mental", "c": "Emotional", "d": "Physical"}
DRIVES = {"1": "Desire to be and be with God", "2": "Wisdom, insight, and knowledge",
          "3": "Life, vitality, and health", "4": "Companionship, love, and friendship",
          "5": "Worldly power, influence, and control", "6": "Material food and things",
          "7": "Lust, sex, and reproduction"}
LETTERS = "abcd"


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def lmap():
    return {CHOICES[f]["legacy_tks_id"]: f for f in CHOICES}


def contrasts(legacy):
    """Deterministic contrast codes. Same drive/different world; same world/different drive."""
    d, w = legacy[0], legacy[1]
    return (f"{d}{LETTERS[(LETTERS.index(w) + 2) % 4]}",          # same drive, diff world
            f"{(int(d) % 7) + 1}{w}")                              # same world, diff drive


AUTHOR_TMPL = """{spec}

---

Build ONE shared scenario plan, then write THREE vignettes from that single plan.

TARGET            {t} = {tw} world + drive "{td}"
CONTRAST A        {ca} = {caw} world + drive "{cad}"   (same drive, different world)
CONTRAST B        {cb} = {cbw} world + drive "{cbd}"   (same world, different drive)

CRITICAL CONSTRUCTION RULE: all three vignettes come from the SAME plan. They must
share actor, setting, stakes, length, tone, number of entities, narrative complexity,
and outcome polarity. ONLY the decisive motive or world-specific method changes. Do
NOT invent three independent stories — that makes the contrast uncontrolled.

Return ONLY JSON:
{{"plan":{{"actor":"...","setting":"...","stakes":"...","tone":"...","outcome_polarity":"..."}},
  "items":[
   {{"contrast_type":"target","code":"{t}","scenario":"..."}},
   {{"contrast_type":"same_drive_diff_world","code":"{ca}","scenario":"..."}},
   {{"contrast_type":"same_world_diff_drive","code":"{cb}","scenario":"..."}}]}}

Each scenario is 80-160 words of naturalistic prose. No foundation code, no Tootra
terminology, no copied definition wording. Encode the signal behaviorally."""

JUDGE_TMPL = """You are an independent evaluator. You receive scenario text only.
For each row choose the single best Foundation, and also report the World and drive
separately.

Worlds: a=Spiritual, b=Mental, c=Emotional, d=Physical
Drives: {drives}

Foundation options:
{choices}

Return JSON only:
{{"rows":[{{"id":"...","world":"a|b|c|d","drive":"1|2|3|4|5|6|7",
  "foundation_code":"2b","top_3":["2b","2d","5b"],
  "evidence_spans":["quoted span","quoted span"],"confidence":0.0}}]}}

Rows to label:
{rows}"""

PAIR_TMPL = """You are an independent evaluator. For each row, choose which of exactly
TWO Foundations the scenario better matches. You must pick one.

{defs}

Return JSON only: {{"rows":[{{"id":"...","choice":"CODE"}}]}}

Rows:
{rows}"""


def call(model, prompt, cfg, ctx, parser):
    for attempt in range(1, RETRY_LIMIT + 2):
        try:
            resp = model.generate_content(prompt, generation_config=cfg,
                                          request_options={"timeout": 180})
            got = judge_parse_repair.robust_extract_json(resp.text, parser,
                                                        context={**ctx, "attempt": attempt})
            if got:
                return got
        except Exception as exc:  # noqa: BLE001 — transport only; quality never retried
            print(f"    {ctx} attempt {attempt}: {type(exc).__name__}", flush=True)
        if attempt <= RETRY_LIMIT:
            time.sleep(2 * attempt)
    return None


def author_all(model, path):
    items = R.read_json(path) if path.exists() else []
    done = {i["group"] for i in items}
    lm = lmap()
    for legacy in sorted(lm):
        if legacy in done:
            continue
        ca, cb = contrasts(legacy)
        prompt = AUTHOR_TMPL.format(
            spec=SPEC, t=legacy, tw=WORLDS[legacy[1]], td=DRIVES[legacy[0]],
            ca=ca, caw=WORLDS[ca[1]], cad=DRIVES[ca[0]],
            cb=cb, cbw=WORLDS[cb[1]], cbd=DRIVES[cb[0]])
        got = call(model, prompt,
                   {"temperature": TEMPERATURE, "top_p": 0.95, "max_output_tokens": 8192,
                    "response_mime_type": "application/json"},
                   {"stage": "author", "legacy": legacy}, json.loads)
        if not got or not got.get("items"):
            items.append({"group": legacy, "rejected": True,
                          "rejection_reason": "generation_failed_after_retries"})
            R.write_json(path, items)
            continue
        for it in got["items"][:3]:
            code = str(it.get("code", "")).strip()
            scen = str(it.get("scenario", "")).strip()
            reason = None
            n_words = len(scen.split())
            if not (LENGTH_RANGE[0] <= n_words <= LENGTH_RANGE[1]):
                reason = f"length_{n_words}_outside_{LENGTH_RANGE}"
            elif re.search(rf"\b{re.escape(code)}\b", scen, re.I):
                reason = "label_code_leak"
            elif re.search(r"\bTootra\b|\bFoundation\b", scen):
                reason = "terminology_leak"
            elif code not in lm:
                reason = f"unknown_code_{code}"
            items.append({
                "group": legacy, "id": f"MC_{legacy}_{it.get('contrast_type','?')}",
                "contrast_type": it.get("contrast_type"), "code": code,
                "truth": lm.get(code), "scenario": scen, "n_words": n_words,
                "plan": got.get("plan"), "rejected": bool(reason),
                "rejection_reason": reason,
            })
        R.write_json(path, items)
        print(f"  authored {legacy}  ({sum(1 for i in items if not i.get('rejected'))} kept)",
              flush=True)
    return items


def judge_28way(model, items, path):
    preds = R.read_json(path) if path.exists() else []
    seen = {p["id"] for p in preds}
    todo = [i for i in items if i["id"] not in seen]
    cj = json.dumps({f: {"world": CHOICES[f]["register"], "drive": CHOICES[f]["drive"],
                         "legacy_code": CHOICES[f]["legacy_tks_id"],
                         "meaning": CHOICES[f]["meaning"]} for f in sorted(CHOICES)}, indent=1)
    for off in range(0, len(todo), 7):
        batch = todo[off:off + 7]
        prompt = JUDGE_TMPL.format(
            drives=json.dumps(DRIVES), choices=cj,
            rows=json.dumps([{"id": i["id"], "scenario": i["scenario"]} for i in batch], indent=1))
        got = call(model, prompt, dict(R.FROZEN["judge_generation_config"]),
                   {"stage": "judge28", "offset": off}, R.june_judge.extract_json)
        if got and got.get("rows"):
            for row in got["rows"]:
                if str(row.get("id")) not in seen:
                    preds.append(row)
                    seen.add(str(row.get("id")))
            R.write_json(path, preds)
            print(f"  judged28 {len(preds)}/{len(items)}", flush=True)
    return preds


def judge_pairwise(model, pairs, path):
    preds = R.read_json(path) if path.exists() else []
    seen = {p["id"] for p in preds}
    todo = [p for p in pairs if p["id"] not in seen]
    for off in range(0, len(todo), 7):
        batch = todo[off:off + 7]
        defs = {}
        for p in batch:
            for c in (p["code_a"], p["code_b"]):
                defs[c] = CHOICES[c]["meaning"]
        prompt = PAIR_TMPL.format(
            defs="Foundation definitions:\n" + json.dumps(defs, indent=1),
            rows=json.dumps([{"id": p["id"], "scenario": p["scenario"],
                              "options": [p["code_a"], p["code_b"]]} for p in batch], indent=1))
        got = call(model, prompt, dict(R.FROZEN["judge_generation_config"]),
                   {"stage": "pairwise", "offset": off}, R.june_judge.extract_json)
        if got and got.get("rows"):
            for row in got["rows"]:
                if str(row.get("id")) not in seen:
                    preds.append(row)
                    seen.add(str(row.get("id")))
            R.write_json(path, preds)
            print(f"  pairwise {len(preds)}/{len(pairs)}", flush=True)
    return preds


def baselines(items):
    from sklearn.feature_extraction.text import TfidfVectorizer
    fs = sorted(CHOICES)
    defs = [CHOICES[f]["meaning"] for f in fs]
    scen = [i["scenario"] for i in items]
    truth = [i["truth"] for i in items]
    out = {}
    for mode, kw in (("char_3_5gram", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word_tfidf", dict(analyzer="word", ngram_range=(1, 1)))):
        v = TfidfVectorizer(**kw).fit(defs)          # fitted on DEFINITIONS only
        A, B = v.transform(scen).toarray(), v.transform(defs).toarray()
        A = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
        B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
        pick = (A @ B.T).argmax(axis=1)
        out[mode] = float(np.mean([fs[p] == t for p, t in zip(pick, truth)]))

    def w(s):
        return set(re.findall(r"[a-z]+", s.lower()))
    dw = [w(d) for d in defs]
    pick = [int(np.argmax([len(w(s) & x) / max(1, len(w(s) | x)) for x in dw])) for s in scen]
    out["label_description_overlap"] = float(np.mean([fs[p] == t for p, t in zip(pick, truth)]))
    out["random"] = round(1 / 28, 6)
    from collections import Counter
    out["majority"] = round(Counter(truth).most_common(1)[0][1] / len(truth), 6)
    return out


def main() -> int:
    import google.generativeai as genai
    from scipy import stats

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required")
    genai.configure(api_key=key)

    frozen = {
        "author_model": AUTHOR_MODEL, "judge_model": JUDGE_MODEL,
        "author_prompt_hash": sha(AUTHOR_TMPL + SPEC), "judge_prompt_hash": sha(JUDGE_TMPL),
        "pairwise_prompt_hash": sha(PAIR_TMPL),
        "definition_set_hash": sha(json.dumps(CHOICES, sort_keys=True)),
        "temperature": TEMPERATURE, "random_seed": SEED,
        "generation_retry_limit": RETRY_LIMIT, "scenario_length_range": list(LENGTH_RANGE),
        "primary_metric": "pairwise_minimal_contrast_accuracy",
        "baseline_models": ["char_3_5gram", "word_tfidf", "label_description_overlap",
                            "random", "majority"],
        "exclusion_rules": ["length outside range", "label code leak", "terminology leak",
                            "unknown code"],
        "rejection_policy": "counted and reported; NEVER silently regenerated",
    }
    print("MINIMAL-CONTRAST-PILOT-v2  (prereg 75672116)")
    for k, v in frozen.items():
        print(f"  {k}: {v}")
    print()

    raw = author_all(genai.GenerativeModel(AUTHOR_MODEL), HERE / "mc_items.json")
    items = [i for i in raw if i.get("id") and not i.get("rejected") and i.get("truth")]
    rejected = [i for i in raw if i.get("rejected")]
    from collections import Counter
    rej_reasons = dict(Counter(i.get("rejection_reason") for i in rejected))
    print(f"\n{len(items)} usable / {len(raw)} generated   rejected={len(rejected)} {rej_reasons}\n")

    p28 = judge_28way(genai.GenerativeModel(JUDGE_MODEL), items, HERE / "mc_preds_28.json")

    by_group = {}
    for i in items:
        by_group.setdefault(i["group"], {})[i["contrast_type"]] = i
    pairs = []
    for g, d in by_group.items():
        tgt = d.get("target")
        if not tgt:
            continue
        for ct in ("same_drive_diff_world", "same_world_diff_drive"):
            oth = d.get(ct)
            if not oth:
                continue
            for it, a, b in ((tgt, tgt["code"], oth["code"]), (oth, tgt["code"], oth["code"])):
                pairs.append({"id": f"P_{it['id']}_vs_{oth['code'] if it is tgt else tgt['code']}",
                              "scenario": it["scenario"], "code_a": a, "code_b": b,
                              "truth_code": it["code"], "contrast_type": ct})
    pp = judge_pairwise(genai.GenerativeModel(JUDGE_MODEL), pairs, HERE / "mc_preds_pair.json")

    # ---- scoring
    tmap = {i["id"]: i for i in items}
    got = {str(p["id"]): p for p in p28 if str(p["id"]) in tmap}
    lm = lmap()
    top1 = top3 = worldc = drivec = 0
    conf = {}
    for rid, p in got.items():
        it = tmap[rid]
        pred = str(p.get("foundation_code", "")).strip()
        top1 += pred == it["code"]
        top3 += it["code"] in [str(x).strip() for x in (p.get("top_3") or [])]
        worldc += str(p.get("world", "")).strip().lower()[:1] == it["code"][1]
        drivec += str(p.get("drive", "")).strip()[:1] == it["code"][0]
        conf[(it["code"], pred)] = conf.get((it["code"], pred), 0) + 1
    n28 = len(got)

    pt = {p["id"]: p for p in pairs}
    pg = {str(x["id"]): str(x.get("choice", "")).strip() for x in pp if str(x["id"]) in pt}
    pw_hits = np.array([1.0 if pg[i] == pt[i]["truth_code"] else 0.0 for i in pg])
    pw = float(pw_hits.mean()) if len(pw_hits) else 0.0

    base = baselines(items)
    best_lex = max(base["char_3_5gram"], base["word_tfidf"], base["label_description_overlap"])
    acc28 = top1 / n28 if n28 else 0.0

    H = {
        "H1_beats_T2_baseline": bool(acc28 > 0.0429),
        "H2_above_28way_chance": bool(n28 and stats.binomtest(top1, n28, 1 / 28, alternative="greater").pvalue < 0.01),
        "H3_pairwise_above_0.50": bool(len(pw_hits) and pw > 0.50 and stats.binomtest(int(pw_hits.sum()), len(pw_hits), 0.5, alternative="greater").pvalue < 0.05),
        "H4_beats_lexical_baselines": bool(acc28 > base["char_3_5gram"] and acc28 > base["word_tfidf"]),
        "H5_world_and_drive_recoverable": bool(n28 and worldc / n28 > 0.25 and drivec / n28 > 1 / 7),
        "H6_human_arm": None,
    }
    suspicious = bool(base["char_3_5gram"] >= acc28)

    print(f"\n  PRIMARY pairwise minimal-contrast = {pw:.4f}  ({int(pw_hits.sum())}/{len(pw_hits)})  chance 0.50")
    print(f"  28-way top1={acc28:.4f} ({top1}/{n28})  top3={top3/n28 if n28 else 0:.4f}  chance {1/28:.4f}")
    print(f"  world={worldc/n28 if n28 else 0:.4f} (chance 0.2500)   drive={drivec/n28 if n28 else 0:.4f} (chance 0.1429)")
    print(f"  baselines: {json.dumps(base)}")
    print(f"  suspicious pattern (char n-gram >= judge): {suspicious}\n")
    for k, v in H.items():
        print(f"  {k:34s} {'DEFERRED' if v is None else ('PASS' if v else 'FAIL')}")

    verdict = ("DEFERRED_HUMAN_ARM_OPEN|" +
               ("SIGNAL_RECOVERABLE" if (H["H2_above_28way_chance"] and H["H3_pairwise_above_0.50"]
                                         and H["H4_beats_lexical_baselines"])
                else "NOT_RECOVERABLE_OR_LEXICAL"))
    print("\nVERDICT:", verdict)

    R.write_json(HERE / "mc_results.json", {
        "design": "MINIMAL-CONTRAST-PILOT-v2", "prereg_commit": "75672116",
        "frozen": frozen,
        "counts": {"generated": len(raw), "usable": len(items), "rejected": len(rejected),
                   "rejection_reasons": rej_reasons, "judged28": n28, "pairs": len(pw_hits)},
        "primary": {"pairwise_minimal_contrast_accuracy": pw, "chance": 0.5},
        "secondary": {"top1_28way": acc28, "top3_28way": top3 / n28 if n28 else 0,
                      "world_accuracy": worldc / n28 if n28 else 0,
                      "drive_accuracy": drivec / n28 if n28 else 0},
        "baselines": base, "best_lexical": best_lex, "suspicious_lexical_pattern": suspicious,
        "confusion": {f"{k[0]}->{k[1]}": v for k, v in sorted(conf.items())},
        "hypotheses": H, "verdict": verdict,
        "human_arm_note": "DEFERRED — no subject pool; owner-as-author is confounded (see prereg section 8)",
    })
    print("WROTE mc_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
