# Graph→^6 adapter spec: input, prediction, scoring, update (exact)

This document answers, concretely, what the review demanded: exactly what
information enters the neural module, what it predicts, how each graph
operation is scored, and which parameters receive updates.

## 1. What enters the module

For each whole-part exercise, `adapter.build_task(record, arm)` builds one
module input:

1. `adapter.encode_graph(record["graph"])` renders the graph record into a
   deterministic token sequence: for every node its label, kind, and contents
   (`node <label> kind=<kind> <field>=<value> ...`), then for every connector
   its source, kind, target, and carried commonality
   (`rel <source> <kind> <target> common=<content>`). Nothing in this sequence
   carries the answer.
2. The structured request tokens follow (`question`, the op and its
   arguments), then the option tokens.
3. The real encoder (`real_framework.build_encoder`) maps tokens to ids with
   the campaign's frozen public tokenizer fitted on the lesson prompts
   (train + practice, both framings) and embeds ids with a FIXED seeded
   projection (frozen; never trained).
4. The module input is the mean embedding of the question tokens; each option
   gets its own mean embedding. Both are computed identically for the cas and
   generic conditions — the conditions differ only in the prompt framing, and
   the module input tokens are the same structural encoding.

   **Amendment 2026-09-09 (representation follow-up 001, owner-authorized):**
   the OPTION embeddings are now SUM-pooled instead of mean-pooled (module
   input stays mean-pooled, exactly as attempt 010). Reason: attempt 002's
   neural diagnostic MEASURED that mean-pooling collapsed every option vector
   onto one direction (pairwise cosines ≈ 1.0 to within 4e-8), so the three
   scores were float32 noise and the loss was exactly ln 3. Sum-pooling keeps
   each option's distinct tokens and their count; a common additive part is
   softmax-shift-invariant, so it cannot hurt the decision. See
   `REPRESENTATION_FOLLOW_UP_001.md`.

   **Amendment 2026-09-09 (representation correction 002, owner-directed,
   PREPARED not launched):** the pure inspection measured that sum-pooled
   differences are dominated by token count (LIST_PARTS length spread median
   10 tokens vs 0.5 unique-to-one tokens per option). The prepared change
   sums ONLY the tokens NOT shared by all three options, per occurrence
   (count-respecting). Per the owner's mathematical review: removing an
   IDENTICAL vector from every option only shifts every score equally
   (softmax-invariant), so the removal changes decisions only through count
   differences; any finite-precision benefit is a hypothesis to be measured.
   Fail-closed: `OPTION_CONTENT_REQUIRED`. See
   `REPRESENTATION_CORRECTION_002.md`.

## 2. What the module is and what it predicts

- The module is a CANDIDATE copy of the registered decompose transform
  (`cas_cjt.neural.RegisteredOperationBank(config).modules_by_operation[DECOMPOSE]`
  — two learned tanh views concatenated and merged into one d_model channel).
  The accepted model is never touched.
- The module maps the input vector to one d_model output vector.
- A FROZEN readout scores each option by dot product against the option's
  embedding; the prediction is the argmax option
  (`adapter.predict`). There is no learned head outside the module, so any
  learning signal can only change the module's own parameters.
- The checker is consulted only for the training correction; it never
  computes the answer during inference.

## 3. How each operation is scored

| Operation | Target | Scored by |
|---|---|---|
| `LIST_PARTS` | sorted direct constituents | option index over part-list options |
| `FIND_SHARED_PART` | shared direct constituent or `none` | option index over part/none options |
| `REACHED_VIA` | `direct` / `via:<constituent>` / `absent` | option index over reach options |

Loss = cross-entropy over option logits against the checker-derived correct
index (`adapter.score` pure formula; torch version in `GraphLearner.step`).

## 4. Which parameters receive updates

- Contract: `cas.cjt.operation.^6.decompose/0.2`, built by
  `cas_cjt.state.make_operation_contract("^6")`. Its admitted plasticity
  roles are `("operation:^6", "bias_update_head")`.
- This run uses ONLY `operation:^6` — every named parameter of the candidate
  decompose module (left, right, merge views). `bias_update_head` is not
  present in the standalone candidate module and stays frozen in any future
  accepted-model promotion.
- The trainer freezes everything else (`scope_parameters`), digest-snapshots
  all parameters before and after (`parameter_snapshot`), and reports
  containment: any digest change outside the allowlist is named
  (`containment_report`).
- The optimizer is AdamW over the module parameters only (`GraphLearner`).
- The accepted model and the governed write-back controller are OUT OF SCOPE
  for this candidate run; promotion into the accepted model, if it ever
  happens, requires the governed proposal path.

## 5. Lesson exposure, conditions, and the seal

- The trainer reports per-operation exposure: how many records and how many
  updates each operation received (`lesson_exposure`), with the explicit
  boundary that an optimizer step is not a complete teaching cycle.
- The two conditions are labeled `prompt_framing_only`: same graphs, same
  options, same reference answers; only the prompt framing differs. This is
  NOT the CASformer-versus-generic-network comparison.
- Budget resolution: 64 optimizer steps / 600 s PER CONDITION; both conditions
  run sequentially in one worker → totals 128 steps / 1200 s in ONE job with
  ONE `$4.00` reservation.
- `evaluate_sealed` records predictions BEFORE consulting answers; each sealed
  prediction record is answer-free, and the training path never reads the
  validation/test splits.

## 6. Fail-closed behavior

- `ENCODER_HOOK_NOT_BUILT` if the encoder is absent; `CAS_CJT_IMPORT_UNRESOLVED`
  if the real cas_cjt import fails; `CUDA_REQUIRED_NO_CPU_FALLBACK` /
  `EXACTLY_ONE_VISIBLE_GPU_REQUIRED` from the teaching gpu_adapter. There is
  no silent fallback anywhere.
