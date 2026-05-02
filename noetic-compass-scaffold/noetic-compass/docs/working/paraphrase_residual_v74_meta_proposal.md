# Paraphrase Residual Proposal: v74_baseline + meta_logic

**Date:** 2026-05-02
**Run:** `structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`
**Checkpoint:** d99810a (clean-eval rescore)

---

## The Numbers That Need Explaining

| Bucket | Canonical | Paraphrase | Gap |
|---|---:|---:|---:|
| v77_omega | 99.3% | 87.3% | 12.0 pp |
| v76_production | 94.4% | 75.6% | 18.8 pp |
| v77_rule_four | 71.2% | 59.9% | 11.3 pp |
| **v74_baseline** | **99.5%** | **18.7%** | **80.8 pp** |
| **meta_logic** | **78.4%** | **17.0%** | **61.4 pp** |

The v74_baseline gap (80.8 pp) and meta_logic gap (61.4 pp) dwarf every other bucket. The lexicon + K=3 augmentation lever that drove v77_omega to 87.3% paraphrase accuracy did not move the needle on these two.

---

## Diagnosis: Template-Prefix Memorization

### The smoking-gun breakdown

The clean-eval paraphrase set uses 3 eval templates per canonical (indices 0, 1, 2 — all disjoint from the 8 training templates by construction). Per-template accuracy for the two failing buckets:

| Template | v74_baseline | meta_logic |
|---|---:|---:|
| 0 — "Map this recoverable CAS slot reading into notation, then explain it briefly: {slots}." | 73/200 = **36.5%** | 32/102 = **31.4%** |
| 1 — "Please reconstruct the exact CAS expression from these stated slots: {slots}." | 5/200 = **2.5%** | 13/102 = **12.7%** |
| 2 — "As a CAS notation check, translate this slot list into the formal expression: {slots}." | 34/200 = **17.0%** | 7/102 = **6.9%** |

**Every paraphrase variant contains exactly the same slot block.** The only difference between a canonical record and its three paraphrase siblings is the prefix string. Yet accuracy drops from 99.5% to 2.5% — a 97 percentage-point swing on identical slot content.

This is not an OOV problem. The Session 44 lexicon-coverage diagnostic already established that OOV explains at most −0.98 pp of the paraphrase gap. Formal Level 3 recoverable slot blocks ("families: state expression; states: Noetic ^8; domain C (cognitive); drive F6") contain no natural-language triggers — only CAS notation tokens (`^8`, `F6`) and structured slot-label words ("domain", "drive", "Noetic"). The lexicon expansion has nothing to bite.

The model has memorized the association between training-distribution prefix strings and content-head values. When a novel prefix appears, those associations break and content heads collapse to distributional priors.

### Why the canonical prompt format memorizes well

The Level 3 recoverable generator produces prompts in two canonical surface forms:

```
"As a notation exercise, map this structure into CAS: families: state expression; states: Noetic ^8; ..."
"I am learning CAS. The target structure is families: state expression; states: Noetic ^8; ... What is the precise notation?"
```

With K=3 training augmentation, each canonical record also trains on training templates [0], [1], [2]:

```
[0] "Convert these CAS slots into formal notation: families: ..."
[1] "From the slot reading families: ..., write the CAS expression."
[2] "What is the CAS notation for: families: ...?"
```

The model trains on 5 surface forms total (2 canonical + 3 training templates). None of the 3 eval templates ("Map this recoverable CAS slot reading...", "Please reconstruct...", "As a CAS notation check, translate...") appears in training. When the model sees an eval-template prefix, it enters an out-of-distribution state and the content-head predictions fall back on priors.

### Evidence from the head failures

**v74_baseline failure signature** (361 total failures across para1+para2, 127 failures on para0):
- `registers` wrong: 255/361 (71%)
- `noetic` wrong: 247/361 (68%)
- `drive` wrong: 195/361 (54%)
- `domain` wrong: 192/361 (53%)

v74_baseline records have `registers: []` (no register — they predate v7.5). Under eval-template prefixes, the model predicts `['E']` (157 occurrences) or `['A']` (136 occurrences). The slot block has zero register tokens. The model is hallucinating registers that cannot be derived from slot content — they can only come from prefix-conditioned priors.

The noetic confusion is non-random: predicted 5 or 0 appear in every off-diagonal cell in the confusion matrix. Noetic 5 and 0 are the model's fallback predictions when the structured-token features from the slot block are not strong enough to override the prefix-conditioned signal.

**meta_logic failure signature** (184 total failures across all 3 templates):
- `noetic` wrong: 128/184 (70%)
- `meta_relations` wrong: 86/184 (47%)
- `registers` wrong: 52/184 (28%)
- `domain` wrong: 47/184 (26%)
- `drive` wrong: 46/184 (25%)

meta_logic prompts contain a "typed cluster" slot family with multi-state membership specifications. The `meta_relations` head (which should be `['membership']` or `['pullback']`) is lost under eval-template prefixes — the model predicts `[]`. This is another prior-collapse marker: `meta_relations=[]` is the default for most other buckets, and the model is defaulting to it.

### Why v77_omega is immune

The v77_omega slot block contains highly distinctive CAS_NOTATION tokens: compound expressions like `(^3^P_{F3}|A × ^2^C_{F2}|f) = ^2^C_{F2}|Ω_unity`. Each `×`, `Ω_*`, `^N^D_{Fk}|R` token is recognized by the CAS notation tokenizer and appears in the 25-dim CAS signature features of the structured token embedding. These features are present regardless of which prefix wraps the slot block. The model has learned to use them as unambiguous content signals. The prefix is noise; the omega tokens dominate.

For v74_baseline, the slot block contains `^8`, `F6`, and bare domain letter `C`. These CAS notation tokens are sparser and individually less distinctive. `^8` alone, without supporting omega or compound context, does not provide the same override signal as `Ω_unity`. The model can, and does, ignore it in favor of prefix-conditioned priors under OOD framing.

### Summary

| Failure mode | Explanation | Supported by evidence |
|---|---|---|
| Lexicon OOV | Slot tokens are CAS notation, not NL | Session 44 OOV delta = −0.98 pp; lexicon entries are NL not slot labels |
| Class imbalance | ~3200 v74_baseline training records; canonical 99.5% proves it's learnable | ✓ |
| Template-prefix memorization | Prefix-conditioned content-head predictions collapse under OOD prefixes | Per-template accuracy 36.5% / 2.5% / 17.0%; register hallucination under eval framing |
| Weak slot-content CAS signal | Sparse CAS notation in v74/meta slots can't override prefix features | v77_omega (rich `Ω_*`/`×` tokens) immune; v74 (sparse `^N`, `Fk`) not |

The failure is **template-prefix memorization amplified by sparse CAS signal in the slot blocks**. This is not what the K=3 augmentation was designed to break — K=3 exposes the model to 3 of 8 training templates, all of which are OOD relative to the eval templates too. The model has learned to use any familiar prefix as a cue. It needs to learn that prefix is irrelevant and slot content alone determines the content-head answers.

---

## Proposed Experiment

### Add a bare-slot training template and raise K to 9

**The core idea:** The only training configuration that forces the model to predict content heads from slot content alone — with zero prefix signal — is training on bare slot blocks: `{slots}` with no wrapper. If the model has seen "families: state expression; states: Noetic ^8; domain C (cognitive); drive F6" as the entire input (no prefix), it cannot learn any prefix-content association. The slot tokens are the only available signal.

Combined with raising K so that all 9 training templates (8 existing + 1 bare) are covered per canonical record, this breaks the prefix-memorization pathway for all buckets and specifically targets the v74_baseline and meta_logic gap.

### Exact changes

**File 1: `cas-native/training/paraphrase_templates.py`**

Add one entry to `TRAINING_PARAPHRASE_TEMPLATES`:

```python
TRAINING_PARAPHRASE_TEMPLATES: tuple[str, ...] = (
    "Convert these CAS slots into formal notation: {slots}",
    "From the slot reading {slots}, write the CAS expression.",
    "What is the CAS notation for: {slots}?",
    "Render this as CAS notation: {slots}.",
    "Translate the following slot description to CAS notation: {slots}",
    "Given {slots}, what does the CAS expression look like?",
    "Output the CAS expression that matches: {slots}",
    "Encode the following into CAS form: {slots}.",
    "{slots}",   # bare slot: forces content-head prediction with no prefix signal
)
```

The `"{slots}"` template must pass the existing disjointness test against `EVAL_PARAPHRASE_TEMPLATES` (all 4 eval templates are non-empty prefix strings; the bare template is trivially disjoint).

**CLI: `--paraphrase-augment-train 9`** (replacing 3)

With 9 templates and K=9, every training record gets all 9 variants via `paraphrase_index % 9` modulo cycling. Template 8 (bare) appears once per canonical.

**No other changes.** Same corpus, same eval set, same epochs/lr/batch/seed.

### Token cost

| Configuration | Canonical records | Paraphrase records | Total |
|---|---:|---:|---:|
| Current (K=3) | 16,570 | 49,710 | 66,280 |
| Proposed (K=9) | 16,570 | 149,130 | 165,700 |

~2.5× total training records. Wall-clock roughly proportional; same A6000 hardware. No architecture changes; cost is purely data volume.

### Expected lift and why

The bare-slot template variant trains the model on a signal that is IDENTICAL across all paraphrase surface forms — because the bare-slot record IS the slot block. The model that has seen "families: state expression; states: Noetic ^8; domain C (cognitive); drive F6" as a standalone input, and learned to predict noetic=8, domain=C, drive=F6, registers=[], should carry that slot-reading capability into any other surface form that preserves the slot block.

The K=9 coverage ensures that every v74_baseline and meta_logic record — not just a sample — trains on this bare-slot variant. The 8 prefixed templates plus 1 bare-slot template force diverse prefix handling and at least one template that has no prefix to memorize.

Expected outcomes:
- **v74_baseline paraphrase:** 18.7% → 45–65% (rough estimate; depends on how cleanly the bare-slot learning transfers). The register hallucination should largely disappear — bare-slot training on records with `registers: []` makes `[]` the unambiguous zero-prefix prediction for v74_baseline records.
- **meta_logic paraphrase:** 17.0% → 35–55%. The `meta_relations` head should recover because the bare-slot input for meta_logic records contains `meta_relations` slot labels explicitly.
- **v77_omega/v76_production:** Hold or modest improvement. These are already robust; the bare-slot template adds redundant but harmless signal.

### What this experiment rules in or out

- If v74_baseline and meta_logic lift substantially → template-prefix memorization confirmed as the primary failure mode; bare-slot training is the right structural fix.
- If v74_baseline and meta_logic don't lift despite K=9 → the model is not reading the CAS notation tokens in the slot block at all, even with a bare-slot input; the failure is in the CAS_NOTATION tokenizer coverage for domain letters and slot-label words (next hypothesis: add multi-word lexicon entries for "domain C", "domain P", "domain E", "domain O", "drive F1"–"drive F7" as structured-token signals).
- If lift appears but plateaus below 60% → slot content has intrinsic ambiguity that the content-head architecture can't resolve without additional structural cues (e.g., domain-disambiguation from the `(cognitive)` vs `(principled)` parenthetical in the slot text).

### What to watch for in the run

- **Registers head on v74_baseline paraphrase:** should drop from 71% failure rate to near zero. If it doesn't, the model isn't learning bare-slot as a prior anchor.
- **Noetic head consistency:** the current per-template spread (template 0: 36.5%, template 1: 2.5%, template 2: 17.0%) should narrow; the bare-slot template is the equalizing anchor.
- **Canonical accuracy:** should hold at 99.3%+. The bare-slot template doesn't touch the canonical eval set. If canonical drops, the bare-slot template is harming the training distribution (unlikely but worth checking).

---

## What This Proposal Does NOT Include

- **CAS-CLM-as-prompt-encoder:** ruled out, documented in Session 37/38.
- **Eval template merging:** TRAIN/EVAL template disjointness is a load-bearing invariant. No eval templates are added to training.
- **Architecture changes:** same `StructuredTokenEmbedding + StructuredPredictionHead`, same hparams.
- **Per-bucket K:** technically more token-efficient (only v74 and meta_logic get K=9; others stay K=3), but requires augmentation-code changes and the global K=9 already has a straightforward one-flag change. If the global run is too expensive, per-bucket K is the follow-on refinement.

---

## Files Changed in This Experiment

| File | Change |
|---|---|
| `cas-native/training/paraphrase_templates.py` | Add `"{slots}"` as 9th entry in `TRAINING_PARAPHRASE_TEMPLATES` |
| CLI invocation | `--paraphrase-augment-train 9` (was 3) |

All other files (corpus, eval set, model, tokenizer, lexicon) unchanged.

---

*Author: diagnostic agent, Session 49 (2026-05-02)*
