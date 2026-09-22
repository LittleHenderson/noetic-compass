# Q4 representation code: bounded inputs and decoding, no neural run

This adds the T14 interfaces and R0 control. It does **not** complete T14 or
Q4. No neural model was initialized, trained, or evaluated. No new Helm model
version, operation result, or benefit claim follows from these checks.

## Interfaces

- `learner_q4_representation.from_visible_record(row)` accepts a Q3 R/G visible
  record and produces ordered UTF-8 byte IDs. The caller must first use
  `q3_load.load_visible` to read the pinned visible data. IDs, family, mode,
  provenance, and targets are absent from the encoding. The adapter rejects
  extra fields and operation-family packets. Input length is 1–2,048 bytes.
- `R0NearestNeighbor(training_examples)` sums fixed one-hot byte rows and
  retrieves the nearest **training** label. Memory is at most 2,048 examples;
  squared Euclidean distance and first-training-row tie breaking are fixed.
  Every tied row position is reported. This is the required order-blind
  diagnostic control, not a learned symbolic operation.
- `learner_q4_decoder.free_decode(bottleneck, next_logits, limits)` predicts
  tokens from only a finite numeric vector and its own generated history.
  Grammar masks use that history and public size limits, never input/target
  ASTs. Invalid numeric outputs and exhausted budgets have no repaired answer.
- `learner_q4_neural.build_model(config, device="cuda:0")` prepares an R1 GRU
  encoder and autoregressive GRU decoder, width 64 or 128. `generate(input)`
  passes only the encoded vector to decoding; no cross-attention or source
  pointer exists. `teacher_forced_logits` is a separate training-only method.
  CUDA is required at creation and at execution, with no CPU fallback.
  This factory and all its neural methods remain **unexecuted**.

## Versioned output subset

`helm-cas-expression-lab.q4-ast-prefix/0.1` serializes the Q3 G grammar:
`StateLiteral`, and ordered `BinaryExpr` with `PLUS`/`TIMES`. It preserves
left/right order, grouping, domain, drive, and the distinction between a missing
register, a null register, and a present register. It does not evaluate an
expression or decide any book/compiler semantic disagreement.

All Unicode CAS text is retained by the input encoding. The first output codec
has explicit limits: at most 127 nodes, depth 16 (root depth 0), and 1,024 output
tokens including EOS. Unsupported nodes/operators/fields are refused; they are
never dropped or approximated. R-family recipes, relations, sets, functions,
nesting, the canonical 28 Foundations, and PCBA remain in the overall project
scope and need additional versioned output productions. This is not a claim
that CAS itself is limited to the first codec's grammar.

## Run the deterministic checks

From this lab folder:

```powershell
python -m pytest -q test_learner_q4.py
python learner_q4_demo.py
```

The demo prints all four statuses and labels its decoder as
`SCRIPTED_FIXTURE_NOT_A_LEARNED_RESULT`. Its same-bag pair produces an R0
collision with both training positions reported. The ordered byte sequences
and the two AST serializations remain distinct. A structural compatibility
check round-trips all 2,048 existing Q3 v0.4 G **training** ASTs through this
codec. That is codec verification, not model reconstruction accuracy.

The tests deny compiler/reference/torch imports in a fresh deterministic-demo
process and inspect the neural code for forbidden imports and teacher-target
calls from prediction methods. This is not a hostile-process sandbox. A Python
callback can be malicious, and a fixed-width float vector can hide information;
runtime custody controls and Q5 interventions remain necessary.

## Acceptance still open

| Criterion | Current evidence | Still required |
|---|---|---|
| V25 order-preserving representation | Ordered input and AST codec distinguish a same-bag pair; R0 collides | Run the actual learned encoder and report its distinction |
| V26 free-running reconstruction | Free-running loop tested with scripted fixtures; training AST codec compatibility checked | Authorized neural run; held-out length/depth scores; syntax, exact AST, bindings, refusal, and execution scores separately; invalid outputs count as errors |
| V27 no hidden bottleneck side channel | Decoder API has only numeric vector/history; no source, AST, target cache or solver import in prediction modules | Instrument the real neural path, isolate evaluator files, test checkpoint reload and interventions; audit any added bypass |
| R2 structured memory | Not implemented | Explicit node/role memory and learned vectors; label as structured computation, not strict vector compression |
| Q4 exit / T15 | Not implemented here | Typed learned operations, invalid-case behavior, supervised loss/training harness, executable end-to-end experiment |

No private held-out target was inspected for this implementation. No learning
score was computed. Resource authorization is supplied by the owner/session,
not inferred from constructing these interfaces. Parent integration owns the
shared changelog, lineage note, task ledger, and any later run approval.
