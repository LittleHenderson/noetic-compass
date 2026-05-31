# Did the high-recoverability lineage use the REAL TKS definitions? — $0 local cut (2026-05-31)

## The question

User challenge: "the real TKS definitions of the 40 Elements / 28 Foundations
are what got the high accuracy rates — did you use those?" The MTC FALSIFY
result (2026-05-31) came from the dual_labeled marker-balanced fixture, which
recovered nothing (40E hidden 5.5% vs 2.5% chance; text 1.5%). The worry: that
null is an artifact of a fixture that STRIPPED the real meaning, not evidence
against CAS.

## What I checked (no GPU, local CPU only)

The 95.625%-hidden lineage is the **Stage-9 v1 fixture**
(`docs/working/lsa_artifacts_20260530/stage9_elements_pilot_20260517.v1.jsonl`,
generator `build_stage9_elements_fixture.v1.py`). Its prompts embed
`_ELEMENT_GLOSSES` — faithful paraphrases of the real TKS 40-Element
definitions (A1 = "ultimate source-awareness, unseen purpose, and the soul's
contact with what guides all causes" — derived from the real TKS A1 "Spiritual
Mind"). So this fixture **does** carry real TKS meaning.

I ran the same text lane the official MTC runner uses
(`CountVectorizer(1-2gram, 2^14) + LogisticRegression(C=1.0, balanced, lbfgs)`),
train on `split=train`, test on `split=test` (group-disjoint by lexical
bundle). Script:
`docs/working/mtc_matched_taxonomy_20260530/local_text_baseline_stage9_real_defs.py`.

## Result (40 classes, chance = 2.5%, 2560 train / 4480 test)

| text field probed | acc | macro-F1 |
|---|---:|---:|
| `english` (full prompt, gloss embedded) | **50.0%** | 47.7% |
| `element_gloss` (the gloss string alone) | 100.0% | 100.0% |

Reference points:
- dual_labeled marker-balanced **null**: text = **1.5%** (its own 40E run).
- v1 lineage **hidden** readout: **95.625%**.

## What this establishes

1. **The user is right that the real definitions carry the signal.** The
   real-definition fixture's prompt text is ~50% recoverable by bag-of-words;
   the over-stripped dual_labeled null was 1.5%. The difference is the real TKS
   meaning. The MTC FALSIFY is a property of the stripped fixture, NOT a global
   CAS null — confirmed from the text side, for $0.

2. **But the v1 fixture is also ~50% text-leaky**, because the gloss is
   embedded near-verbatim (`element_gloss` alone → 100%, i.e. it is a literal
   label→string lookup). So the 95.625% hidden number sits on top of ~50%
   surface leakage. The honest hidden-over-text lift on v1 is **+46pp**
   (95.6% − 49–50%), which is real signal beyond bag-of-words — but it is NOT
   a clean leakage-free specificity claim, because half the label is already
   in the visible text.

## The decisive next experiment (cheap-first, then GPU)

Two conditions, both grounded in the REAL TKS definitions (not stripped, not
verbatim-embedded):

- **Condition 1 (definition-faithful, named):** = the v1 fixture. Text ≈ 50%,
  hidden ≈ 95.6%. Use only as the leakage-anchored upper reference. Already done.
- **Condition 2 (meaning instantiated in concrete scenarios, definition NOT
  named):** write plain scenarios where the target element's real meaning is
  required to pick the label, but the gloss string is absent. **Surface Gate:**
  local text baseline must fall to near-chance. **Then** capture 20B hidden +
  run the matched-taxonomy comparator. If hidden recovers, text ≈ chance, and
  CAS beats the matched control → real specificity, leakage-free.

Gate Condition 2 LOCALLY (text baseline ≤ near-chance) before spending any
capture dollars. Do not re-cite the v1 95.6% as clean specificity — cite it as
the meaning-present, leakage-anchored reference, with the +46pp lift as the
honest signal-beyond-text quantity.
