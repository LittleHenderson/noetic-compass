"""SPEC-AUTHORED-SCENARIOS-v1 — prereg committed BEFORE any scenario was generated.

Does the owner's 27-section authoring specification account for the missing signal?

Baseline, already published: the SAME author model (gemini-2.5-flash-lite) under a
thin prompt produced scenarios scoring 12/280 = 0.0429 against chance 0.0357,
one-sided binomial p = 0.3011 — indistinguishable from guessing.

Author model is PINNED to that same weaker model so a positive result is
attributable to the protocol and not to a better writer.
"""
from __future__ import annotations

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

june_judge = R.june_judge
CHOICES = june_judge.load_foundation_choices(R.CANONICAL_TKS)
SPEC_PATH = HERE / "owner_scenario_spec.md"
AUTHOR_MODEL = "models/gemini-2.5-flash-lite"      # PINNED to the baseline's author
JUDGE_MODEL = "models/gemini-2.5-flash"            # the T0 = 28/28 configuration
BASELINE = 0.0429
CHANCE = 1.0 / 28.0
N_PER = 3
BOOT = 10_000
SEED = 20260727

WORLDS = {"a": "Spiritual", "b": "Mental", "c": "Emotional", "d": "Physical"}
DRIVES = {
    "1": "Desire to be and be with God", "2": "Wisdom, insight, and knowledge",
    "3": "Life, vitality, and health", "4": "Companionship, love, and friendship",
    "5": "Worldly power, influence, and control", "6": "Material food and things",
    "7": "Lust, sex, and reproduction",
}


def legacy_map():
    """legacy TKS id (e.g. '2b') -> F-code (e.g. 'F2A'). One convention throughout."""
    return {CHOICES[f]["legacy_tks_id"]: f for f in CHOICES}


def words(s):
    return set(re.findall(r"[a-z]+", str(s).lower()))


def jaccard(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, len(wa | wb))


def author_all(model, spec, lmap, out_path):
    items = []
    if out_path.exists():
        items = R.read_json(out_path)
    done = {i["target_legacy"] for i in items}
    for legacy in sorted(lmap):
        if legacy in done:
            continue
        f = lmap[legacy]
        prompt = (
            f"{spec}\n\n---\n\nTARGET FOUNDATION: {legacy}\n"
            f"World: {WORLDS[legacy[1]]}\nDrive: {DRIVES[legacy[0]]}\n\n"
            f"Produce exactly {N_PER} scenarios for this target: two at difficulty S1 and "
            f"one at S2. Return ONLY a JSON object:\n"
            '{"items":[{"difficulty":"S1","scenario":"...","blind_prediction":"...",'
            '"author_confidence":0.0,"rubric_total":0}]}\n'
            "The scenario field must be 80-160 words of naturalistic prose with no Tootra "
            "terminology, no foundation code, and no copied definition wording."
        )
        got = None
        for attempt in range(1, 4):
            try:
                resp = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.95, "top_p": 0.95,
                                       "max_output_tokens": 8192,
                                       "response_mime_type": "application/json"},
                    request_options={"timeout": 180},
                )
                got = judge_parse_repair.robust_extract_json(
                    resp.text, lambda t: json.loads(t),
                    context={"legacy": legacy, "attempt": attempt})
                if isinstance(got, dict) and got.get("items"):
                    break
                got = None
            except Exception as exc:  # noqa: BLE001
                print(f"    author {legacy} attempt {attempt}: {type(exc).__name__}", flush=True)
            if attempt < 3:
                time.sleep(2 * attempt)
        if not got:
            print(f"    author {legacy}: FAILED after 3 attempts — skipped", flush=True)
            continue
        for j, it in enumerate(got["items"][:N_PER]):
            items.append({
                "id": f"SP_{legacy}_{j}", "target_legacy": legacy, "truth": f,
                "difficulty": it.get("difficulty", "?"),
                "scenario": str(it.get("scenario", "")).strip(),
                "author_blind_prediction": it.get("blind_prediction"),
                "author_confidence": it.get("author_confidence"),
                "author_rubric_total": it.get("rubric_total"),
            })
        R.write_json(out_path, items)
        print(f"  authored {legacy} -> {len(items)} items", flush=True)
    return items


def judge_items(model, items, out_path):
    preds = R.read_json(out_path) if out_path.exists() else []
    seen = {str(p["id"]) for p in preds}
    todo = [i for i in items if i["id"] not in seen]
    for off in range(0, len(todo), 10):
        batch = [{"id": i["id"], "prompt": i["scenario"]} for i in todo[off:off + 10]]
        prompt = R.neutralize_judge_prompt(june_judge.judge_prompt(batch, CHOICES))
        for attempt in range(1, 4):
            try:
                resp = model.generate_content(
                    prompt, generation_config=dict(R.FROZEN["judge_generation_config"]),
                    request_options={"timeout": 180})
                payload = judge_parse_repair.robust_extract_json(
                    resp.text, june_judge.extract_json,
                    context={"stage": "judge", "offset": off, "attempt": attempt})
                if not june_judge.validate_preds(batch, payload, CHOICES):
                    for row in payload["rows"]:
                        if str(row.get("id")) not in seen:
                            preds.append(row)
                            seen.add(str(row.get("id")))
                    R.write_json(out_path, preds)
                    print(f"  judged {len(preds)}/{len(items)}", flush=True)
                    break
            except Exception as exc:  # noqa: BLE001
                print(f"    judge off {off} attempt {attempt}: {type(exc).__name__}", flush=True)
            if attempt < 3:
                time.sleep(2 * attempt)
    return preds


def surface_top1(items):
    from sklearn.feature_extraction.text import TfidfVectorizer
    fs = sorted(CHOICES)
    defs = [CHOICES[f]["meaning"] for f in fs]
    scen = [i["scenario"] for i in items]
    out = {}
    for mode, kw in (("char", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word", dict(analyzer="word", ngram_range=(1, 1)))):
        v = TfidfVectorizer(**kw).fit(defs + scen)
        A, B = v.transform(scen).toarray(), v.transform(defs).toarray()
        A = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
        B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
        pick = (A @ B.T).argmax(axis=1)
        out[mode] = float(np.mean([fs[p] == i["truth"] for p, i in zip(pick, items)]))
    return out


def main() -> int:
    import google.generativeai as genai
    from scipy import stats

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required")
    if not SPEC_PATH.exists():
        raise SystemExit(f"owner spec not found at {SPEC_PATH}")
    genai.configure(api_key=key)
    spec = SPEC_PATH.read_text(encoding="utf-8")
    lmap = legacy_map()

    print("SPEC-AUTHORED-SCENARIOS-v1")
    print(f"author={AUTHOR_MODEL} (PINNED to baseline)  judge={JUDGE_MODEL}")
    print(f"baseline={BASELINE}  chance={CHANCE:.4f}\n")

    items = author_all(genai.GenerativeModel(AUTHOR_MODEL), spec, lmap,
                       HERE / "spec_authored_items.json")
    items = [i for i in items if len(i["scenario"].split()) >= 40]
    print(f"\n{len(items)} items with usable prose\n")

    preds = judge_items(genai.GenerativeModel(JUDGE_MODEL), items,
                        HERE / "spec_authored_preds.json")

    truth = {i["id"]: i["truth"] for i in items}
    got = {str(p["id"]): str(p.get("foundation")) for p in preds if str(p["id"]) in truth}
    hits = np.array([1.0 if got[i] == truth[i] else 0.0 for i in got])
    acc = float(hits.mean()) if len(hits) else 0.0
    n = len(hits)

    surf = surface_top1(items)
    best_surface = max(surf.values())
    leak = float(np.mean([jaccard(i["scenario"], CHOICES[i["truth"]]["meaning"]) for i in items]))
    counts = {}
    for f in got.values():
        counts[f] = counts.get(f, 0) + 1
    share = max(counts.values()) / len(got) if got else 1.0

    rng = np.random.default_rng(SEED)
    diffs = np.sort(np.array([hits[rng.integers(0, n, n)].mean() - BASELINE for _ in range(BOOT)]))
    lo, hi = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
    p = float(stats.binomtest(int(hits.sum()), n, CHANCE, alternative="greater").pvalue)

    crit = {
        "P1_beats_baseline": bool((acc - BASELINE) >= 0.15 and lo > 0),
        "P2_above_chance": bool(p < 0.01),
        "P3_beats_surface": bool((acc - best_surface) >= 0.10),
        "P4_no_collapse": bool(share <= 0.30),
        "P5_not_lexical": bool(leak <= 0.15),
    }
    if not crit["P4_no_collapse"]:
        verdict = "VOID_DEGENERATE"
    elif crit["P2_above_chance"] and not crit["P5_not_lexical"]:
        verdict = "VOID_LEAKAGE"
    elif not crit["P2_above_chance"]:
        verdict = "SPEC_INSUFFICIENT"
    elif not crit["P3_beats_surface"]:
        verdict = "NOT_LICENSED_LEXICAL"
    elif crit["P1_beats_baseline"]:
        verdict = "LICENSED"
    else:
        verdict = "NOT_LICENSED"

    print(f"\n  accuracy = {acc:.4f}  ({int(hits.sum())}/{n})   baseline {BASELINE}   chance {CHANCE:.4f}")
    print(f"  surface: char={surf['char']:.4f} word={surf['word']:.4f}  best={best_surface:.4f}")
    print(f"  vs baseline: {acc-BASELINE:+.4f}   bootstrap 95% CI [{lo:+.4f}, {hi:+.4f}]")
    print(f"  binomial p = {p:.6f}   leakage Jaccard = {leak:.4f}   top-share = {share:.3f}\n")
    for k, v in crit.items():
        print(f"  {k:22s} {'PASS' if v else 'FAIL'}")
    print("\nVERDICT:", verdict)

    R.write_json(HERE / "spec_authored_results.json", {
        "design": "SPEC-AUTHORED-SCENARIOS-v1",
        "author_model": AUTHOR_MODEL, "judge_model": JUDGE_MODEL,
        "n_items": n, "accuracy": acc, "baseline": BASELINE, "chance": round(CHANCE, 6),
        "surface": surf, "best_surface": best_surface,
        "delta_vs_baseline": acc - BASELINE, "bootstrap_ci": [lo, hi],
        "binomial_p": p, "leakage_jaccard": leak, "max_single_foundation_share": share,
        "criteria": crit, "verdict": verdict,
    })
    print("WROTE spec_authored_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
