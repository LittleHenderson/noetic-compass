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

See STATIC_CONDITIONS_v3.yaml (frozen S0–S7 table). S6 is the identical S3
architecture with constant uniform profiles (capacity control); S7 replaces the CAS
profiles with the SCMPE matched-semantic taxonomy (meaning control). Only beating
BOTH licenses "CAS-specific".

## Gate 1B implementation bindings (frozen; no improvisation room)

- **Input construction:** one sequence per passage: the clause texts joined by a
  single space, then `"\n"`, then the question text. No chat template, no system
  prompt (raw completion-mode forward pass of the frozen model).
- **Span mapping:** clause and question character offsets are computed from the
  frozen `clauses`/`question` fields; token spans come from the tokenizer's
  `offset_mapping`; a token belongs to a clause iff its character span overlaps the
  clause's. A clause with zero tokens aborts (`SPAN_MAPPING_FAILURE`).
- **Candidate encoding:** each candidate entity is encoded as the mean of the token
  hidden states (at L*) of its FIRST occurrence in the passage text; the answer
  score for candidate e is `dot(W_o z, W_c enc(e))` with `W_c`: 896→256.
- **Capacity-matching algorithm (deterministic):** compute S3's trainable parameter
  count; for each other arm, add a widening linear pair (256→w→256, GELU) after the
  MLP and choose the smallest integer w such that the arm's count is within ±1% of
  S3's (w search ascending from 0); record w per arm in the receipt.
- **Layer convention:** decoder blocks 1-indexed; "layer L" = the hidden-state
  OUTPUT of block L; candidates {6, 12, 18, 24}.
- **Training length:** exactly 3000 updates per run; NO early stopping.
- **Code-pinning law (protected-secrecy mitigation):** the complete Gate 1B
  training/evaluation implementation must be committed and its digest recorded in
  the execution receipt BEFORE the protected-evaluation step executes; the
  independent audit verifies that ordering from git history.

## Explicit non-claims

This architecture contains no recursion, no RPM gating, no ASOM regulation, no
routing, and no adaptive compute (`I_total := 1`). It tests exactly one coupling:
`q = alphaᵀP` against matched controls. Nothing else is claimed for it.
