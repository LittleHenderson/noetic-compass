# VOID — `SMALL-MODEL-SEMANTIC-MATCH-v1`

**Pre-registration:** `5df9d66b` (committed before model load)
**Date:** 2026-07-27
**Verdict:** `VOID_PREMISE_DEFECT` — and, independently, would have failed its own `S3` gate.

---

## 1. The premise defect

The design assumed the TKS canon text and the compact composition are **two independently-worded
descriptions of the same cell**. That assumption is false, and it is false *by design*.

`docs/reference/tks_28_foundations_translation_key.md` states the mapping is a
**"position-by-position translation"** whose explicit purpose is to let TKS material serve as
source *"without admitting the metaphysical commitments TKS carries."* The CAS drive names are
therefore **positional relabelings that deliberately change the semantics**, not paraphrases.

Side by side, at the Analytical register:

| Code | TKS canon (legacy name) | CAS compact | Same concept? |
|---|---|---|---|
| `F1A` | *Mental Unity* — "quest to comprehend the infinite, mental models of the divine" | "integrating separate parts into one coherent whole" | **partial** |
| `F2A` | *Mental Wisdom* — "discernment via analysis and intuition" | "discerning what fits, what matters, what should guide action" | yes |
| `F3A` | *Mental Life* — "cognitive resilience, neuroplasticity, mindfulness" | "maintaining energy, liveliness, repair" | yes |
| `F4A` | *Mental Love* — "intellectual compatibility, cognitive empathy" | "forming, preserving, repairing bonds" | yes |
| `F5A` | *Mental **Power*** — "strategic thinking, persuasive communication" | "**choosing, initiating, directing** action" | **NO** — power-over vs self-direction |
| `F6A` | *Mental **Resources*** — "frameworks as resources, intellectual property, **consuming** information" | "**ordering, constraining, arranging**, stabilizing a system" | **NO** |
| `F7A` | *Mental **Creation*** — "spreading ideas, **replicating one's mentality** in others" | "**orienting action toward an aim**, meaning, duty, end" | **NO** |

The owner's own authoring specification confirms the TKS side independently: Foundation `5` is
*"Worldly power, influence, and control"*, `6` is *"Material food and things"*, `7` is *"Lust,
sex, and reproduction"*.

**Consequence:** for at least four of seven drives, matching compact text to TKS text for the same
code is not a semantic task at all. It requires knowing an arbitrary positional convention that
cannot be inferred from meaning. A model that understood both texts perfectly would still be
wrong on those cells.

## 2. My error, named

I measured word overlap at mean Jaccard `0.0209` and read it as *"different words, same
meaning"* — the ideal semantic tier. Part of that low overlap was actually **different words,
different meaning**. Low lexical overlap is consistent with both, and I did not check which.

**The check I skipped:** confirm semantic equivalence, not just lexical distance, before treating
a pair as a paraphrase. A tier-validity gate must test *both*.

## 3. Independent corroboration — the pre-registered gate agreed

The run was killed before `small_model_semantic_results.json` was written, so no verdict was ever
computed. **Partial per-arm numbers had, however, already been printed to the log, and they are
reported here in full rather than discarded:**

```
surface char 3-5-gram    top1 = 0.1607
surface word TF-IDF      top1 = 0.0714
pythia-160m  layer 6     top1 = 0.0536   drive 0.1429   register 0.3571
pythia-160m  layer 0     top1 = 0.1607   drive 0.2321   register 0.7321
```

Two things follow, both pre-registered before any of this was visible:

- **`S3` (tier validity, `best_surface <= 0.15`) FAILS.** Best surface is `0.1607`. The run was
  already headed for `VOID_TIER_CONTAMINATED` on its own terms.
- **`S1` (beats surface) FAILS badly.** The model at layer 6 scored `0.0536` against a surface
  control at `0.1607` — the model was *worse* than character n-grams.

The premise defect and the pre-registered gate point to the same verdict from different
directions. That is the outcome a control is supposed to produce.

**Note on layer 0 vs layer 6:** token embeddings (`0.1607`) beat the middle layer (`0.0536`), and
register accuracy at layer 0 reached `0.7321` against chance `0.25`. That is a surface effect —
layer 0 is close to a bag of tokens, and the compact text literally contains register-definition
vocabulary. It is not evidence of depth-based understanding, and `S5` was non-gating for exactly
this kind of ambiguity.

## 4. What is NOT concluded

- **Nothing about whether small models can recover CAS structure.** This design never posed that
  question properly. It remains open.
- **Nothing about TKS versus CAS quality.** The positional mapping is a documented, intentional
  design decision, not a defect in either framework.
- **Nothing about the 28-cell grid.** The separately licensed result
  (`SCRAMBLE-NULL-COMPLETION-v1`, `0/200` scrambles) is untouched by this.

## 5. What a valid successor needs

1. **A semantic-equivalence gate**, not just a lexical-distance gate. Two texts qualify as a
   paraphrase pair only if an independent check confirms they denote the same concept.
2. **One convention per run.** Items authored against TKS semantics must be judged against the
   TKS key; items authored against CAS semantics against the CAS key. Mixing them tests the
   positional convention, not meaning.
3. **The surface controls stay** — they did their job here, flagging contamination before any
   headline number existed.

Gate 2 remains OPEN at `0.38`. Nothing licensed.
