# Self-Reference Invariance Lever — Proposal

**Branch**: `proposal/self-reference-lever`  
**Date**: 2026-05-03  
**Author**: Claude Code (Session 49)  
**Status**: Proposal — awaiting reviewer decision before retrain

---

## TL;DR

The model has the right content-axis answers in canonical form and loses them under paraphrase. A 95-98% canonical-wins asymmetry across all four content heads (noetic, domain, drive, registers) means this is a pure invariance failure, not a knowledge gap. The proposed lever conditions the paraphrase forward pass on the model's own canonical prediction: give the model its canonical answer as a `[PRIOR]` block prepended to the paraphrase prompt, and train it to be consistent with that prior. The model needs to learn one low-capacity rule — "trust the `[PRIOR]` block for content axes when present" — rather than learning surface-form generalization from scratch.

This is a third lever, composable with PR #2 (bare-slot K=9 augmentation) and PR #3 (KL-on-content-heads regularizer). It is not a replacement for either.

---

## Diagnosis

### Per-head paraphrase consistency on `d99810a` checkpoint (clean eval, n=1000)

| Head | Rate |
|---|---:|
| turn_type | 100.0% |
| authority | 100.0% |
| has_omega | 99.5% |
| has_meta_logic | 99.0% |
| register_mode | 98.4% |
| transition_kind | 98.2% |
| meta_relations | 97.0% |
| expression_family | 96.0% |
| drive | 79.4% |
| registers | 79.1% |
| domain | 77.4% |
| noetic | 71.5% |

The 8 boolean/categorical heads are essentially invariant. The 4 content heads — noetic, domain, drive, registers — collapse under paraphrase. Noetic is the worst at 71.5%.

### Canonical-wins asymmetry (commit `3232f05`, sampled disagreements)

When canonical and paraphrase predictions disagree on a content head, canonical is right 95-98% of the time:

| Head | Disagreements | Canon right | Para right | Asymmetry |
|---|---:|---:|---:|---:|
| noetic | 854 | 822 | 11 | 96.3% |
| domain | 677 | 667 | 4 | 98.5% |
| drive | 618 | 600 | 9 | 97.1% |
| registers | 627 | 599 | 8 | 95.5% |

The model has the right answer in canonical form and loses it under surface change. This is not a knowledge gap.

---

## Architectural finding

The structured-token tokenizer already understands CAS notation tokens with provenance (`cas:` / `lex:` / `learned:` / `surf:` prefixes). Appending a serialized canonical CAS prediction to a paraphrase prompt produces a string the tokenizer parses with full CAS-axis awareness. No new modality is required; the existing input path handles it.

The delimiter format is:

```
[PRIOR] {canonical_cas_expression}
[QUERY] {paraphrase_prompt_text}
```

The `[PRIOR]` and `[QUERY]` surface tokens are new to the vocabulary but learn trivially with exposure during training. The CAS tokens in the prior block are already in-vocabulary from the existing training data.

---

## Loss/data finding

Today, paraphrase records are added to the training set as **independent records** — each paraphrase is paired with its canonical ONLY at the loss level (same CAS target labels), never at the input level. Specifically:

1. **No paired input**: paraphrase records have `prior_cas_state = None` (absent); the model never sees the canonical CAS expression as part of the paraphrase input.
2. **No self-conditioning training signal**: the model has no opportunity to learn "trust the [PRIOR] block for content axes when a prior is present."

The PR #2 (K=9) and PR #3 (KL regularizer) levers both operate on the OUTPUT side or the AUGMENTATION side without providing the model the canonical answer as input. This lever provides a direct input-side signal.

---

## Proposed lever

### Core mechanism

1. Records gain an optional `prior_cas_state` field (a serialized CAS expression string, `None` absent).
2. When `prior_cas_state` is present, the ingest path prepends it to `user_prompt` before tokenization:  
   `f"[PRIOR] {prior_cas_state}\n[QUERY] {user_prompt}"`
3. A new augmentation function `expand_with_self_conditioning_pairs(records, *, variants_per_record)` generates self-conditioning pairs: each paraphrase variant carries the canonical's `cas_expression` in `prior_cas_state`.
4. A new eval harness measures canonical-vs-paraphrase-with-oracle-prior consistency, giving a ceiling on what self-conditioning can achieve.

### Why near-oracle hint is cheap to learn

The 95-98% asymmetry means attaching the model's own correct canonical answer is a near-oracle hint for the disagreement cases. The model only needs to learn: "when `[PRIOR]` is present, let it anchor the content axes." This is a low-capacity pattern (one positional rule) vs surface-form generalization (requires understanding that `{slots}` in 8+ surface templates are equivalent).

### Training data signal path

```
canonical record
  cas_expression = "^2^P_{F4}|f"
  user_prompt = "families: ^2^P_{F4}|f. What notation should I use?"

↓ expand_with_self_conditioning_pairs(K=3)

self-conditioning paraphrase record (index 0)
  cas_expression = "^2^P_{F4}|f"           ← same (inherited, deepcopy)
  prior_cas_state = "^2^P_{F4}|f"          ← set explicitly
  user_prompt = "Convert these CAS slots into formal notation: families: ^2^P_{F4}|f"
                                            ← template-wrapped paraphrase

↓ get_effective_prompt(record) at tokenization time

tokenized input = "[PRIOR] ^2^P_{F4}|f\n[QUERY] Convert these CAS slots..."
```

---

## Implementation diff

### New files

- `cas-native/training/self_conditioning_serialization.py` — `serialize_prior_cas_state(record) -> str`
- `cas-native/training/self_conditioning_augmentation.py` — `expand_with_self_conditioning_pairs(records, *, variants_per_record)`
- `cas-native/training/evaluate_self_conditioning_invariance.py` — eval harness
- `cas-native/tests/test_self_conditioning_augmentation.py` — ≥5 tests

### Modified files

- `cas-native/training/structured_prediction_ingest.py` — adds `get_effective_prompt(record)` helper
- `cas-native/training/train_structured_prediction.py` — uses `get_effective_prompt`, adds `--self-conditioning-pairs K` flag

### Size estimate

~350 lines new code, ~25 lines modified, ~150 lines tests. No model-architecture changes. No new primitives.

---

## A/B test plan

Three runs in sequence after PR merge (not included in this PR; retrain decision is the user's):

**Run A (baseline)**: current `d99810a` checkpoint, no modification.  
- Canonical: 93.2%, paraphrase: 46.9%.

**Run B (K=9 paraphrase only, PR #2)**: `--paraphrase-augment-train 9`. In flight on `feature/paraphrase-augment-9-templates`. DO NOT INTERFERE.

**Run C (self-conditioning, this PR)**: `--paraphrase-augment-train 3 --self-conditioning-pairs 3`.  
- 3 standard paraphrase variants per canonical (without prior) + 3 self-conditioning variants (with prior).
- Prediction: paraphrase consistency on content heads rises from 71-79% toward 85-90%.

**Run D (combined)**: `--paraphrase-augment-train 9 --self-conditioning-pairs 3` + PR #3 KL regularizer (if merged).  
- Measures composability.

Eval harness: `evaluate_self_conditioning_invariance.py` measures oracle-prior consistency before and after Run C, isolating the lever's contribution.

---

## Why this lever vs PR #3 alternatives

| Axis | PR #3 (KL regularizer) | This PR (self-reference) |
|---|---|---|
| Side of intervention | Output logit space | Input feature space |
| What model learns | Make logits invariant | Trust the [PRIOR] block |
| Signal source | Both canonical and para logits | Canonical CAS expression as prior |
| Risk of degradation | Canonical accuracy may drop if KL weight too high | Minimal — prior is only present on self-conditioning records |
| Additive to PR #3 | Yes | Yes |

PR #3 pushes canonical and paraphrase logits together by regularizing their KL divergence. This PR pulls the paraphrase prediction toward the canonical answer by providing it as an explicit input. They are mechanistically independent and composable.

---

## Risks

1. **Vocabulary OOV**: `[PRIOR]` and `[QUERY]` delimiter tokens are new. Mitigated: they appear frequently in self-conditioning training records; the vocabulary builds from training data so these tokens are in-vocabulary if `--self-conditioning-pairs K > 0`.

2. **Prior leakage to non-self-conditioning eval**: when `prior_cas_state` is absent (standard canonical or standard paraphrase eval), the `get_effective_prompt` path is identity and the tokenizer sees only `user_prompt`. No leakage.

3. **Canonical accuracy regression**: if self-conditioning records are too numerous relative to standard canonical records, the model may over-rely on the `[PRIOR]` block and underperform without it. Mitigated: start with K=3 self-conditioning pairs alongside K=3 standard paraphrases. Monitor canonical accuracy on standard eval (no prior) in the eval harness.

4. **Template overlap with standard paraphrases**: `expand_with_self_conditioning_pairs` uses `TRAINING_PARAPHRASE_TEMPLATES` for the query surface form. The standard `expand_with_paraphrases` uses the same template set. If both are applied (K_para + K_self), the same template may appear in both conditioned and unconditioned forms. This is intentional and beneficial — the model sees the same surface form with and without a prior.

5. **Eval oracle vs model-prediction gap**: the eval harness uses the ground-truth `cas_expression` as oracle prior (upper bound). In deployment, the prior would be the model's own canonical prediction (~93.2% correct). The oracle-prior eval overstates the real improvement for incorrectly-predicted canonicals, but correctly measures the ceiling.

---

## Composability with PR #2 and PR #3

**PR #2 (bare-slot K=9)** adds 9 training paraphrase variants per canonical WITHOUT a prior. This PR adds K self-conditioning variants WITH a prior. Both expand the training set; neither interferes with the other. In a combined run, the model learns both: surface-form generalization (from PR #2 records) and prior-anchored prediction (from this PR's records).

**PR #3 (KL invariance loss)** regularizes logit-level consistency. This PR adds prior-anchored input records. In a combined run, the KL loss pushes canonical and paraphrase logits closer, while the self-conditioning records teach the model to use the prior. Both converge on the same goal (paraphrase consistency on content heads) via independent mechanisms.

---

## Open questions for reviewer

1. **K value for self-conditioning pairs**: K=3 is proposed. Should it match the paraphrase augmentation K (currently 3, in-flight run at 9)?

2. **Prior content scope**: this PR uses the full `cas_expression` string as the prior. Would a simplified prior (e.g., just noetic + domain + drive fields as a short token sequence) work better? The full expression is the highest-fidelity prior but also longer.

3. **Backward compatibility in deployment**: in inference, the `[PRIOR]` path is activated only when `prior_cas_state` is set. Should we always run canonical first and always attach the prior for the paraphrase? Or is this a capability the caller opts into?

4. **PR #3 interaction order**: if PR #3 raises canonical accuracy before we retrain with this PR, should we retrain on the PR #3 checkpoint? Yes — each lever should be evaluated from the best available checkpoint.

5. **Eval harness oracle vs model-prediction**: should the eval harness also support `--use-model-prediction-as-prior` mode (where the prior is the model's actual predicted CAS rather than the ground truth)? This would require a lightweight CAS expression renderer from structured-prediction head outputs, which is non-trivial.
