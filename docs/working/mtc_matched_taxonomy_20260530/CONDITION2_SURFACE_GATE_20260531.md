# Condition-2 fixture + local Surface Gate (2026-05-31)

## What this is

The honest, leakage-gated specificity fixture. Real TKS Element meaning is
present (so a pretrained model recognizes the territory — the mechanism behind
the 95.625% lineage), but the canonical gloss string is NEVER used and surface
phrasing is train/test-DISJOINT, so a bag-of-words classifier cannot shortcut
to the 40-way (domain x noetic) label. Role-bound same-sentence counterfactual
pairs + Focus marker (v1 structure) keep the label tied to the focused role.

Builder: `build_mtc_condition2_meaning_instantiated.py`
Fixture: `mtc_condition2_meaning_instantiated_20260531.jsonl` (640 rows, 40
classes, 320 train / 320 test, 16/class). Noetic dynamics faithful to the
authoritative definitions (verbs preserved; visceral-^3 and associative-^8
anti-drift respected), expressed in concrete non-gloss phrasing.

## Surface Gate (local CPU, $0; text lane = CountVectorizer 1-2gram 2^14 +
LogReg C=1.0 balanced; train->test)

| Recovered from prompt text | Condition 2 | v1 (gloss embedded) | chance |
|---|---:|---:|---:|
| Full 40-element label | **6.88%** | 50.0% | 2.5% |
| Domain axis only | 28.1% | — | 25.0% |
| Noetic axis only | 25.0% | — | 10.0% |

## Reading

- **Gloss-level leakage eliminated:** full-label text drops 50.0% -> 6.9%
  (~7x). The real meaning stayed; the copyable definition string left.
- **Residual is on the noetic axis** (25% vs 10% chance). A few noetic
  dynamics are intrinsically lexical — ^2 attraction ("drawn / pull"), ^3
  aversion ("recoil / repellent"), ^5 composition ("made of / sum") — and
  partly survive the train/test vocabulary split. Domain axis is ~chance.
- A hidden-state probe must now beat **6.9%**, not 50%, to claim signal — a far
  cleaner specificity bar.

## Status / next

- Surface Gate: **near-pass.** 6.9% is ~2.7x chance, far below any plausible
  hidden recovery, and a defensible low-leakage fixture for a first capture.
- Optional tightening before GPU: expand the disjoint phrasing pools per noetic
  (esp. ^2/^3/^5) to push noetic-axis text toward 10% chance, which would pull
  full-label text toward ~2.5%.
- Meaning-Preservation Gate (still required before claim): human raters recover
  the element label from the Condition-2 prompts using the definition sheet. If
  raters recover but text baseline is ~chance, the meaning is present without
  being a surface shortcut — exactly the condition for a clean hidden-vs-text +
  matched-taxonomy specificity test on GPU.
- Do NOT spend capture dollars until BOTH gates are green locally.
