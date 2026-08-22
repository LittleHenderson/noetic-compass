# V13 — Construct-correct + giveaway-free `^8`/`^9`: was the NOISE a wrong-construct artifact?

**Date:** 2026-08-21 · **Model:** `pythia-160m` (reserialized `d5861d32…`), attested engine, CPU, **$0**.
**Results file (co-located):** `detector_validation_v13_cause_effect_constructcorrect_results.json`, sha256 `689cd7dafa88b71d…`
**Prompted by:** owner — "maybe the wording of the definitions is the reason it's not passing… use examples that wouldn't contain giveaway verbiage."

## The two fixes tested at once
1. **Construct fix.** Canonical `^8` Above/Cause = **associative TRIGGERING** (an Idea that triggers a *different* Idea to come to Mind), `^9` = the **ARRIVAL** of that Idea. The prior cause-effect tests (v3/v6/v10) used **physical/logical causation** (rain→flood, "because/so") — a *drifted* construct per CLAUDE.md's own anti-drift rule ("`^8` is associative triggering, not analytical reasoning"). v13 uses the canonical triggering-vs-arrival construct.
2. **Giveaway fix.** TRAIN on the v5 canonical colloquial exemplars; TEST on FRESH phrasings with the giveaways stripped (no reminds/triggered/brought-to-mind/popped/came-to-me/clicked/because/so). 2-class, 6 train + 6 test per class, chance `0.50`.

## Result (exact)
- **activation `0.667` (8/12, L2)** — `^8` 4/6, `^9` 4/6.
- **char-ngram surface `0.833` (10/12)** — `^8` 6/6, `^9` 4/6.
- **activation − surface = `−0.167` → the word-counter WINS.** label-shuffle (single draw) `0.333`.

## Verdict — NOT_SEPARABLE_GIVEAWAYFREE (surface-confounding is robust)
The construct fix **helped** — `^8`/`^9` is no longer the pure noise of v10 (where 0.750 at n=12 best-of-32 was ~91% under the null). But two things remain true:
1. **Activation still loses to surface** (`0.667` < `0.833`). The char-ngram baseline separates `^8`/`^9` *better* than the activation detector — whatever signal exists is more accessible to character n-grams than to the hidden state.
2. **Activation isn't clearly above chance under selection.** `8/12` at best-of-12-layers has P≈`0.93` under the coin-flip null — so `0.667` is consistent with layer-selection noise.

**Conclusion:** fixing the construct and stripping the giveaways did **not** rescue `^8`/`^9`. The surface-confounding first seen at v6/v10 is **robust**, not an artifact of wrong wording or physical-vs-associative construct. My "fresh" stimuli still carry an `^8`-vs-`^9` surface signature (sensory-cue scene-setting vs arrival/presence language) that char-ngrams exploit — which is itself the point: the distinction the model represents here is surface-shaped.

## Claim state
- **Real:** all numbers, real pythia-160m via attested engine. **Accepted:** none.
- **Verdict:** load-bearing NEGATIVE — `^8`/`^9` does not beat a char-ngram control even construct-correct and giveaway-free at this scale/n.
- **Open:** a truly *surface-matched* `^8`/`^9` pair set (same words, different dynamic — hard to author); the 6.9b version; larger n.
- **Caveat:** activation best-of-12-layers on the 12-item test set; n=6 per class; `^8`/`^9` may be two halves of one dynamic and intrinsically hard to split on isolated sentences.

## Cross-reference — Domain (the other axis owner flagged)
The giveaway-free Domain test is **v11** (framing-matched Domain-4): activation `0.625` vs surface `0.438`, verdict **PARTIAL** — `O` surface-carried, `P` collapses when modals stripped, only `C`/`E` a thin real edge. Same pattern: better stimulus design refines but does not flip these axes to clean passes.
