"""JUDGE-POSITIVE-CONTROL-v1 — prereg 8ab16b2d + amendment 1, both committed BEFORE this ran.

The check sixteen instruments never performed: can this judge apparatus recover a
signal that is certainly present?

Three tiers, SAME judge / SAME choice set / SAME prompt builder / SAME parse path as
the scaled matched A/B. Only the item text varies.

  T0  item = the choice-key definition VERBATIM      -> C1 harness integrity (bar 0.90)
  T1  item = deterministic meaning-preserving rewrite -> C2 sensitivity      (bar 0.50)
  T2  item = real committed scenarios, seeded sample  -> C3 localization     (T1-T2 >= 0.20)

If C1 fails, the judge cannot identify a definition handed to it verbatim, and every
NOT_LICENSED verdict in the ledger becomes uninterpretable pending repair.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_matched_ab as R  # noqa: E402 — reuse the EXACT apparatus under test
import judge_parse_repair  # noqa: E402

june_judge = R.june_judge
CHOICES = june_judge.load_foundation_choices(R.CANONICAL_TKS)
BATCH = 10
CHANCE = 1.0 / 28.0

# Frozen BEFORE execution (prereg §"Why this cannot manufacture a favourable result").
# Meaning-preserving only: no term that names a drive or register is touched.
SYNONYMS = {
    "quest": "pursuit", "comprehend": "understand", "evolving": "developing",
    "capacity": "ability", "toward": "towards", "beyond": "past",
    "seeking": "searching for", "maintaining": "keeping", "creating": "making",
    "recognizing": "acknowledging", "expressing": "conveying",
}


def rewrite_variants(text: str, limit: int = 10) -> list[str]:
    """Deterministic, meaning-preserving rewrites. No LLM, no randomness."""
    clauses = [c.strip() for c in re.split(r"[;,]\s*", text.strip().rstrip(".")) if c.strip()]
    out: list[str] = []
    for rot in range(max(1, len(clauses))):
        rotated = clauses[rot:] + clauses[:rot]
        base = "; ".join(rotated) + "."
        for use_syn in (False, True):
            v = base
            if use_syn:
                for a, b in SYNONYMS.items():
                    v = re.sub(rf"\b{re.escape(a)}\b", b, v)
            if v not in out:
                out.append(v)
            if len(out) >= limit:
                return out
    return out


def build_tiers() -> dict[str, list[dict]]:
    t0, t1 = [], []
    for f in sorted(CHOICES):
        meaning = CHOICES[f]["meaning"]
        t0.append({"id": f"T0_{f}", "prompt": meaning, "truth": f})
        for j, v in enumerate(rewrite_variants(meaning)):
            t1.append({"id": f"T1_{f}_{j}", "prompt": v, "truth": f})

    pool = R.read_json(HERE / "blind_pool.json")
    key = R.read_json(HERE / "blind_key.json")
    rng = random.Random(20260727)
    picks = rng.sample(pool, 280)
    t2 = [{"id": f"T2_{p['id']}", "prompt": p["prompt"], "truth": key[p["id"]]["foundation"]}
          for p in picks]

    seen: set[str] = set()
    t1d = []
    for r in t1:                       # amendment 1: dedup T1, report actual count
        if r["prompt"] in seen:
            continue
        seen.add(r["prompt"])
        t1d.append(r)
    return {"T0": t0, "T1": t1d, "T2": t2}


def judge_tier(model, tier: str, rows: list[dict], out_path: Path) -> list[dict]:
    preds: list[dict] = []
    if out_path.exists():
        preds = R.read_json(out_path)
    seen = {r["id"] for r in preds}
    todo = [r for r in rows if r["id"] not in seen]
    for off in range(0, len(todo), BATCH):
        batch = [{"id": r["id"], "prompt": r["prompt"]} for r in todo[off:off + BATCH]]
        prompt = R.neutralize_judge_prompt(june_judge.judge_prompt(batch, CHOICES))
        last = ""
        for attempt in range(1, 4):
            try:
                resp = model.generate_content(
                    prompt, generation_config=dict(R.FROZEN["judge_generation_config"]),
                    request_options={"timeout": 180},
                )
                payload = judge_parse_repair.robust_extract_json(
                    resp.text, june_judge.extract_json,
                    context={"tier": tier, "offset": off, "attempt": attempt})
                errs = june_judge.validate_preds(batch, payload, CHOICES)
                if not errs:
                    for row in payload["rows"]:
                        if str(row.get("id")) not in seen:
                            preds.append(row)
                            seen.add(str(row.get("id")))
                    R.write_json(out_path, preds)
                    print(f"  {tier}: {len(preds)}/{len(rows)}", flush=True)
                    break
                last = "; ".join(errs[:3])
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {exc}"
            if attempt < 3:
                time.sleep(2 * attempt)
        else:
            print(f"  {tier}: batch at offset {off} FAILED — {last[:160]}", flush=True)
    return preds


def score(rows: list[dict], preds: list[dict]) -> dict:
    truth = {r["id"]: r["truth"] for r in rows}
    got = {str(p["id"]): str(p.get("foundation")) for p in preds if str(p["id"]) in truth}
    correct = sum(1 for i, f in got.items() if f == truth[i])
    counts: dict[str, int] = {}
    for f in got.values():
        counts[f] = counts.get(f, 0) + 1
    top = max(counts.values()) / len(got) if got else 1.0
    return {
        "n_rows": len(rows), "n_scored": len(got), "n_correct": correct,
        "accuracy": round(correct / len(got), 6) if got else None,
        "chance": round(CHANCE, 6),
        "max_single_foundation_share": round(top, 4),
        "effective_n_equals_rows": len({r["prompt"] for r in rows}) == len(rows),
    }


def main() -> int:
    import google.generativeai as genai

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(R.FROZEN["judge_model"])

    tiers = build_tiers()
    print("JUDGE-POSITIVE-CONTROL-v1  (prereg 8ab16b2d + amendment 1)")
    print(f"judge={R.FROZEN['judge_model']}  chance={CHANCE:.4f}")
    for t, rows in tiers.items():
        print(f"  {t}: {len(rows)} distinct rows")
    print()

    out = {}
    for t, rows in tiers.items():
        preds = judge_tier(model, t, rows, HERE / f"posctl_preds_{t}.json")
        out[t] = score(rows, preds)

    a0 = out["T0"]["accuracy"]
    a1 = out["T1"]["accuracy"]
    a2 = out["T2"]["accuracy"]
    crit = {
        "C1_harness_integrity": bool(a0 is not None and a0 >= 0.90),
        "C2_instrument_sensitivity": bool(a1 is not None and a1 >= 0.50),
        "C3_difficulty_localized": bool(a1 is not None and a2 is not None and (a1 - a2) >= 0.20),
        "C4_no_degenerate_collapse": bool(
            all(v["max_single_foundation_share"] <= 0.30 for v in out.values())),
    }
    if not crit["C1_harness_integrity"]:
        verdict = "HARNESS_DEFECT"
    elif not crit["C2_instrument_sensitivity"]:
        verdict = "TASK_INTRACTABLE"
    elif not crit["C4_no_degenerate_collapse"]:
        verdict = "VOID_DEGENERATE"
    elif crit["C3_difficulty_localized"]:
        verdict = "JUDGE_FUNCTIONAL"
    else:
        verdict = "UNLOCALIZED"

    print()
    for t in ("T0", "T1", "T2"):
        v = out[t]
        print(f"  {t}  acc={v['accuracy']}  ({v['n_correct']}/{v['n_scored']})  "
              f"top-share={v['max_single_foundation_share']}")
    print(f"\n  T1 - T2 = {round((a1 or 0) - (a2 or 0), 4)}")
    print()
    for k, v in crit.items():
        print(f"  {k:28s} {'PASS' if v else 'FAIL'}")
    print("\nVERDICT:", verdict)

    R.write_json(HERE / "posctl_results.json", {
        "design": "JUDGE-POSITIVE-CONTROL-v1",
        "prereg_commit": "8ab16b2d", "amendment": "AMENDMENT 1 (T0 n=28, T1 deduplicated)",
        "judge_model": R.FROZEN["judge_model"], "chance": round(CHANCE, 6),
        "tiers": out, "criteria": crit, "verdict": verdict,
    })
    print("WROTE posctl_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
