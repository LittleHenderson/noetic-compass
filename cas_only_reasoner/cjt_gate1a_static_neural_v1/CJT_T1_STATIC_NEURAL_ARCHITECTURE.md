# CJT-T1 — Static Dual-Stream CJT Coupler (FROZEN architecture)

## Base model (frozen)

- **Checkpoint:** `Qwen/Qwen2.5-0.5B-Instruct` (24 transformer layers, d_model=896).
- **Base weights FROZEN.** Only the matched heads/adapters below are trainable.
- **Pinning law:** the exact HuggingFace revision SHA and the SHA-256 of every
  weight file are recorded into the Gate 1B execution receipt AT CONTAINER BUILD,
  BEFORE any training; the owner-signed approval binds to those recorded digests,
  and every job refuses to start if the resolved revision differs. (The weights are
  not downloaded in Gate 1A — no model load is permitted here.)
- Rationale: chosen because it makes the first falsifiable comparison affordable and
  reproducible — not because it is the smartest available model.

## Unit of processing: the Idea (clause)

Each passage contains **3–6 separately represented Ideas** (clauses). Every clause
realizes exactly one formal construction-gold operation, and the task answer is
computable from the formal trace that existed BEFORE the natural-language surface
was generated (see CONSTRUCTION_GOLD_DATASET_SPEC.md).

## Streams

For a passage with Ideas i = 1..N (N in 3..6):

- **Semantic stream `h_i`** (d=896): mean-pool of the frozen model's hidden states
  at the frozen layer L* (see LAYER_SELECTION_AND_CACHING_SPEC.md) over Idea i's
  token span. Extracted ONCE per passage on AWS GPU, cached, reused by every arm
  and seed.
- **CAS stream `p_i`** (d=4): the construction-gold process profile of Idea i over
  the restricted slice `(^2, ^3, ^6, ^8)` — one-hot from the gold operation class
  in S2/S3; permuted, randomized, uniform, or replaced per the arm definition in
  STATIC_CONDITIONS_v3.yaml.
- **Question embedding `g`** (d=896): mean-pool of hidden states at L* over the
  question's token span.

## Coupler (the trainable candidate, arm S3)

```
alpha = softmax_i( (W_q g)ᵀ (W_k h_i) / sqrt(64) )     # attention over Ideas
q     = alphaᵀ P                                        # P = [p_1; ...; p_N]  (N x 4)
c     = alphaᵀ H                                        # H = [h_1; ...; h_N]  (N x 896)
z     = MLP( [c ; W_p q ; g] )                          # W_p: 4 -> 64 profile lift
answer_logits = W_o z                                   # over the closed candidate set
```

- `W_q, W_k`: 896->64. `W_p`: 4->64. `MLP`: (896+64+896) -> 256 -> 256 (GELU).
- `W_o`: 256 -> answer-candidate scoring (dot with candidate Idea/entity encodings;
  candidates = the closed entity set of the passage).
- Loss: cross-entropy over the passage's closed candidate set. Metric: exact match.

## Matched-capacity law

Every arm's TRAINABLE parameter count must be within **±1%** of S3's. Arms lacking
a component (e.g. S0 has no coupler) receive a capacity-matching MLP widening on
their head, computed and recorded in the execution receipt. The base model is frozen
in every arm; nothing else varies except the registered arm difference.

## What each arm isolates

See STATIC_CONDITIONS_v3.yaml (frozen S0–S7 table, v3.1). S6 is the identical S3
architecture with constant uniform profiles (capacity control); S7 replaces the
CAS profiles with ONE alternative surface-verb taxonomy
(ALTERNATIVE_TAXONOMY_MANIFEST_CANDIDATE.json — owner PATH A: not SCMPE-v1, not
an equal task-aligned control). The license law is THRESHOLDS_AND_STATUS_LAW.yaml
v3: the auxiliary-value claim requires beating ALL SEVEN controls; the words
"CAS-specific" are prohibited on this dataset regardless of result.

## Gate 1B implementation bindings (frozen; no improvisation room)

- **Input construction:** one sequence per passage: the clause texts joined by a
  single space, then `"\n"`, then the question text. No chat template, no system
  prompt (raw completion-mode forward pass of the frozen model).
- **Span mapping:** clause and question character offsets are computed from the
  frozen `clauses`/`question` fields; token spans come from the tokenizer's
  `offset_mapping`; a token belongs to a clause iff its character span overlaps the
  clause's. A clause with zero tokens aborts (`SPAN_MAPPING_FAILURE`).
- **Candidate encoding (amended A5 — owner audit section 7):** each candidate
  entity is encoded CONTEXT-FREE: `enc(e)` = the mean of the frozen model's
  INPUT-EMBEDDING rows for e's tokens, tokenized standalone with no special
  tokens (`exec/candidate_encoding.py`); the answer score for candidate e is
  `dot(W_o z, W_c enc(e))` with `W_c`: 896→256. The former rule (mean contextual
  hidden states at the FIRST occurrence) encoded 17.4% of train and 17.9% of val
  answers (regenerated corpus; `CANDIDATE_OCCURRENCE_AUDIT.json`) from a clause
  other than the target — an avoidable architecture interaction, withdrawn. One
  rule, identical for every arm.
- **Capacity-matching algorithm (deterministic):** compute S3's trainable parameter
  count; for each other arm, add a widening linear pair (256→w→256, GELU) after the
  MLP and choose the smallest integer w such that the arm's count is within ±1% of
  S3's (w search ascending from 0); record w per arm in the receipt.
- **Layer convention:** decoder blocks 1-indexed; "layer L" = the hidden-state
  OUTPUT of block L; candidates {6, 12, 18, 24}.
- **Training length:** exactly 3000 updates per run; NO early stopping.
- **Code-pinning law (STRENGTHENED at Gate 1A.1 — owner audit section 2):** the
  complete Gate 1B implementation is COMMITTED NOW in `exec/` (arms, capacity
  matcher, labels, assembly, spans, candidate encoding, activation extraction +
  cache I/O, training loop, layer selection, protected evaluator, B0/B1
  baselines, launcher, receipts), hashed in `GATE1B_CODE_MANIFEST.json`, and
  bound by the owner-signed approval BEFORE any signature exists — not merely
  before the protected step. CPU shape proofs: `tools/test_exec_shapes.py`
  (declared shapes; ±1% capacity; S4–S7 structurally identical to S3; corrupted
  arms cannot read gold at runtime; candidate masks; protected-path refusal;
  GPU_REQUIRED fires first at every guarded entry).

## Explicit non-claims

This architecture contains no recursion, no RPM gating, no ASOM regulation, no
routing, and no adaptive compute (`I_total := 1`). It tests exactly one coupling:
`q = alphaᵀP` against matched controls. Nothing else is claimed for it.
