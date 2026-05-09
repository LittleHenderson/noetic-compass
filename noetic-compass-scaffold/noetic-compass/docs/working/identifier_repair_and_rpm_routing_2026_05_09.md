# Identifier Repair + rpm_chain Routing Diagnosis — 2026-05-09

## Context

After the cas_prefix_mask architectural fix landed (commit `2530d1b`),
the v1 PREFIX128 5-epoch retrain hit the user's content-correctness
gate (5/8 strong-partial, vs 0/8 in the no-prefix baseline). Two
residual issues remained:

1. **Exact Ω-name / coefficient recovery flatlined** even as semantic
   binding (operators, registers, domains) sharpened.
2. **`rpm_chain` task routing failed in 1/8 records** — model emitted
   `invalid_to_explanation` language for a valid `rpm_chain` prompt,
   even with K=128 (full prompt visibility) and 5 epochs.

This doc records the durable findings from investigating both.

## Finding 1: Ω-names and coefficients are a copy-mechanism problem,
not a learning problem.

Direct evidence: with `cas-native/inference/identifier_repair.py`
applied as a post-generation step, the v1 PREFIX128 5ep checkpoint
recovers identifier content fidelity to:

| Class | Pre-repair | Post-repair | Ceiling |
|---|---:|---:|---|
| Ω-name | 33% | **100%** | hit |
| Coefficient | 33% | **67%** | gen-completeness, not pattern |
| Variable | 0% | 0% | gen rarely produces var slots in this checkpoint |

Coefficient post-repair is below 100% because the model **emitted only
2 of 3 coefficient slots** for the recipe — it dropped the side-product
mention entirely (`+ 0.1*Λ·Ω_engagement_side`). Repair was specified
as positional fill of *existing* slots, not invention of missing ones.
Coverage rises as gen completeness improves with more training.

**Implication:** the model knows where the slot is; it just can't
fill it with the right specific identifier under continuous learning.
Long-tail unique strings (1000+ Ω names across the corpus, each seen
~35 times during 5-epoch training) cannot be memorized against the
rest of parameter capacity. A copy mechanism — whether post-gen
substitution or in-decoder pointer attention — is the right fix.

This iteration ships the post-gen substitution path. A pointer head
in the decoder is the cleaner long-term answer when we eventually
revisit architecture.

### Coefficient surface-form patterns observed

The CAS-Native model emits coefficients with several qualifier
suffixes. The repair module's slot detector covers all observed
forms:
- `1 of something`
- `1 unit of something` / `1 units of something`
- `1.5 times something` / `0.7 times`
- `1 part of` / `1 parts of`
- `0.7 contribution from` / `0.7 contribution of`

Numbers WITHOUT a qualifier (e.g., bare `0.5` between commas) are
deliberately not matched. Empirically the model rarely emits
unqualified numerics; matching them broadly would risk over-repair
on serial numbers inside Ω names like `_60`.

## Finding 2: `rpm_chain` misrouting is structural, not prompt-text.

### Hypothesis tested

Valid `rpm_chain` prompts and invalid `rpm` prompts share the same
CAS body shape (`let X = ...; X -> Y`). At inference, valid prompts
are wrapped by `"Describe the following CAS expression in plain
English:"` and invalid prompts by `"Explain in plain English why
the following CAS expression is invalid: ..."`. Hypothesis: the
model loses the wrapper distinction and routes by CAS body shape.

### Evidence — wrapper text is ignored at inference

Five wrapper variants were tested on the same valid `rpm_chain` CAS
body under greedy decoding:

| Wrapper variant | Routing |
|---|---|
| baseline ("Describe...") | invalid-style |
| `[TASK:cas_to_english/rpm_chain]` prefix | invalid-style |
| `Paraphrase the following valid CAS...` | invalid-style |
| `This is a valid let-binding CAS expression.` | invalid-style |
| `VALID. Describe...` | invalid-style |

**All 5 produced byte-identical output.** The encoder/bottleneck-z
path is not differentiating wrapper text when the CAS body
dominates conditioning. The wrapper signal is effectively dead at
this checkpoint.

### Evidence — valid trajectory has zero probability mass

Under high-entropy sampling (`top_p=0.95, temperature=1.0`) over
20 random samples on the same `rpm_chain` prompt:

- valid-style routing: **0/20**
- invalid-style routing: **20/20**

The model has not just *preferred* the invalid trajectory; it has
*memorized* it as the only output for this CAS body shape.

### Evidence — variable name prefix `stageA0` is shared

Variable-name prefix distribution in training:

| Prefix | Valid `rpm_chain` count | Invalid `rpm` count |
|---|---:|---:|
| `stageA0` | 323 (every record) | 207 |
| `stageA` (no `0`) | 0 | 111 |
| `stageB` | 0 | 111 |
| `stageD3`, `stageW3`, `stageP3`, … | ~50 each | 0 |

`stageA0` is the canonical RPM-chain start variable in valid records
AND a heavily-used let-binding head in invalid records. Combined
with the shared CAS body shape, the cas_prefix carries an ambiguous
routing signal that the model resolves toward the more-abundant
invalid family (425 invalid vs 323 valid for similar shapes).

### Architectural side-effect of the cas_prefix_mask fix

The `cas_prefix_mask` fix made the discrete CAS prefix path dominate
decoder conditioning. That's a feature for source-binding (Ω-names
are now copyable). It's a regression for task discrimination when
two task families share CAS body shape: the encoder's bottleneck-z
loses influence relative to the cas_prefix tokens, and any wrapper
signal that lived in the encoder pass becomes inaccessible at
generation time.

### Why this won't be fixed by training-side adjustments alone

- More epochs: 0/20 sampled trajectories reach the valid silhouette,
  so the cross-entropy gradient on a valid `rpm_chain` example would
  fight against a near-saturated invalid-routing prior.
- Wrapper-text engineering: encoder bottleneck-z is empirically
  insensitive to wrapper differences for this CAS body.
- Sampling tweaks: valid trajectory has effectively zero probability
  mass. No temperature recovers it.

### What WILL fix it

Three options, ranked by effort:

| Option | Effort | Effect |
|---|---|---|
| **A. Compilability gate at inference** | Low (~50 LOC; reuse compiler) | Routes valid CAS to `cas_to_english`, invalid to `invalid_to_explanation`. Bypasses model task discrimination entirely. **No retraining required.** |
| **B. Explicit task tokens in cas_prefix** | Medium (corpus regen + retrain) | `[VALID]` / `[INVALID]` tokens in the discrete prefix give the head an unambiguous routing signal. Architecturally clean for new training runs. |
| **C. Variable renaming + corpus rebalance** | High | Valid uses `stageA0`, invalid uses task-distinct prefixes. Plus oversample the under-represented family. |

**Decision (2026-05-09):** Option A — compilability gate at
inference. Routing valid-vs-invalid is a structural property of the
expression, not a learned semantic one; the compiler is the right
authority. Option B is the right answer for the next training run
when we revisit corpus shape.

## Headline numbers (durable record)

```
v1 NO-PREFIX baseline (2 epoch K=64):
  task routing       4/8
  N/D/F/R binding    minimal
  Ω-name recovery    0%
  coefficient        0%
  hard/jargon leaks  0
  content gate       0/8 strict, 0/8 strong-partial

v1 PREFIX 2ep K=64:
  task routing       7/8
  N/D/F/R binding    partial
  Ω-name recovery    0% (prefix preserved sometimes, not exact)
  coefficient        0%
  hard/jargon leaks  0
  content gate       1/8 strict, 1/8 strong-partial

v1 PREFIX128 5ep:
  task routing       7/8 (rpm_chain still broken)
  N/D/F/R binding    strong (3-4/4 axes per record)
  Ω-name recovery    0% (model still hallucinates)
  coefficient        33%
  hard/jargon leaks  0
  content gate       1/8 strict, 4/8 strong-partial = 5/8 combined

v1 PREFIX128 5ep + identifier_repair postprocessor:
  Ω-name recovery    100% (when slot exists in gen)
  coefficient        67% (gen-completeness ceiling)
  variable           0% (gen rarely emits var slots)
  hard/jargon leaks  0 (unchanged)
  rpm_chain routing  still broken — repair can't fix routing
```

## Files of record

- `cas-native/inference/identifier_repair.py` — the repair module
- `cas-native/tests/inference/test_identifier_repair.py` — 26 tests
- `cas-native/training/runs/v1_path_d_PREFIX128_5ep_20260509T035024Z/diverse_eval_with_repair_v3.log` — eval log on pod

## Open work after this commit

1. Step 3: chat-integration with compilability gate + gated repair
   postprocessor (this commit does NOT integrate either into chat.py;
   the repair module is library-shaped, not wired in).
2. Future training run: add explicit task tokens to cas_prefix to
   eliminate the structural ambiguity at training time (Option B).
3. Pointer/copy head in the decoder for in-architecture identifier
   binding (long-term clean answer).
