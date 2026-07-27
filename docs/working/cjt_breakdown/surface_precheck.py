"""C1 — MANDATORY CPU PRECHECK for CJT-BREAKDOWN-INVERSION-v1 (prereg 903136f0).

Scores each ladder's PROMPT TEXT for sentiment — no model at all — and fits the
same SMOOTH vs STEP comparison the model data will get.

WHY THIS RUNS FIRST: if the prompts' own surface sentiment already snaps at a step,
then a snap in the model measures my ladder construction, not the model. Per the
prereg that voids the run BEFORE any GPU time.

INSTRUMENT REPAIRED 2026-07-27, pre-model-data. The reason is recorded here because
adjusting a control is the riskiest move available and must never be silent. The
first version used two hand-built word sets and was broken by its own output: the
most extreme rung of the criticism ladder ("makes clear I am hopeless as a writer")
scored POSITIVE (+0.0833) because the only word it recognised was "feedback";
steps 6-10 contained no lexicon words at all; and the reported snap at breakpoint 2
was the single word "honest". A sentiment measure that rates "I am hopeless" as
positive is not measuring sentiment. Replaced with VADER — a standard published
lexicon, not tunable by me — which passes the ordering check the hand sets failed
(mild rung 0.0000, extreme rung -0.1027).
"""
import json
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from ladders import LADDERS, SHAM

_ANALYZER = SentimentIntensityAnalyzer()


def surface_valence(text):
    """VADER compound score in [-1, +1]."""
    return float(_ANALYZER.polarity_scores(str(text))["compound"])


def fit_smooth(y):
    """Monotone (linear) fit — the 'degrades gracefully' model."""
    x = np.arange(len(y), dtype=float)
    b, a = np.polyfit(x, y, 1)
    pred = a + b * x
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0


def fit_step(y):
    """Best single breakpoint: mean before, mean after — the 'it snaps' model."""
    best_r2, best_k = -1e9, None
    for k in range(2, len(y) - 1):
        pred = np.concatenate([np.full(k, y[:k].mean()), np.full(len(y) - k, y[k:].mean())])
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
        if r2 > best_r2:
            best_r2, best_k = r2, k
    return best_r2, best_k


def main():
    out = {}
    print("C1 SURFACE PRECHECK — prompts only, no model (VADER)")
    print("(if the PROMPTS snap, the run is VOID before any GPU time)\n")
    void = False
    for name, prompts in list(LADDERS.items()) + [("SHAM_control", SHAM)]:
        v = np.array([surface_valence(p) for p in prompts])
        r2s = fit_smooth(v)
        r2t, k = fit_step(v)
        d = r2t - r2s
        snap = bool(d >= 0.15)
        if name != "SHAM_control" and snap:
            void = True
        out[name] = {
            "valence": [round(float(x), 4) for x in v],
            "r2_smooth": round(r2s, 4), "r2_step": round(r2t, 4),
            "delta": round(d, 4), "breakpoint": k, "surface_snaps": snap,
        }
        print(f"  {name:16s} smooth R2={r2s:6.3f}  step R2={r2t:6.3f}  "
              f"delta={d:+6.3f}  bp={k}  {'<-- SNAPS' if snap else 'no snap'}")

    print()
    print(f"B4 surface control: "
          f"{'FAIL — VOID, prompts snap on their own' if void else 'PASS — prompts do not snap'}")
    out["_verdict"] = {
        "B4_surface_control_clean": (not void),
        "instrument": "VADER compound (published lexicon, not tuned here)",
        "action": "VOID before GPU" if void else "proceed to model measurement",
    }
    json.dump(out, open("surface_precheck_results.json", "w"), indent=2, sort_keys=True)
    print("WROTE surface_precheck_results.json")
    return 0 if not void else 1


if __name__ == "__main__":
    raise SystemExit(main())
