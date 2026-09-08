# Diagnostic mode correction and parts-contrast data check (2026-09-08)

Scope correction from the advisor, verified against source. This is not a
software defect and changes nothing in the live teaching campaign.

## 1. The existing diagnostic is forward-only

`cas_meta2/teaching_cycle/binding_diagnostic.py` (SCHEMA
`cas-teaching-binding-diagnostic/1`) supports ONLY saved-model forward-only
inspection: it requires restored candidates with pinned model/optimizer
fingerprints, asserts `optimizer_steps_performed: 0`, and blocks optimizer
calls. It answers: "What does the current model do, and where might
information be lost?"

The advisor's **small training-fit check** is a DIFFERENT question: "Can this
learning path acquire the compact task?" — 24 balanced known binding examples,
short task-only inputs, actual optimizer updates through the real CAS/generic
binding paths, recorded before/after loss and accuracy. **No existing mode
performs optimizer updates on a small short-input set.** The training-fit
question remains OPEN. The machinery to reuse already exists in
`teaching_cycle/gpu_adapter.py` (loss.backward + optimizer.step with identity
checks) and `controller.py` (per-stage step accounting).

## 2. Parts-contrast data check (exact counts)

Counted per candidate over `data.build_dataset(seed=20260908)`:

| Split | cases | both | color_only | shape_only | neither | distinct profiles |
|---|---|---|---|---|---|---|
| train | 256 | 256 | 0 | 0 | 512 | ('B','N','N') ×256 |
| development | 64 | 64 | 0 | 0 | 128 | ('B','N','N') ×64 |
| test_fresh | 64 | 64 | 0 | 0 | 128 | ('B','N','N') ×64 |
| test_context | 64 | 64 | 0 | 0 | 128 | ('B','N','N') ×64 |
| test_names | 64 | 64 | 20 | 24 | 84 | mixed (6 profile kinds) |

Conclusion: in all permitted teaching data, every case is one both-match
candidate plus two neither-match candidates. Color-only and shape-only matches
NEVER occur, so the three parts targets are identical columns there and parts
supervision would not establish that color matching, shape matching, and their
combination were learned separately. Partial-match contrasts exist only in the
`test_names` evaluation split, which is not teaching data.

Consequences for the parts-supervised revision (see its REVISION.md addendum):
either (a) describe the lesson narrowly — parts supervision on teaching data is
redundant reinforcement, not separable part learning — or (b) propose
separately versioned, checked teaching families whose distractors share exactly
one attribute with the request (e.g., request `green triangle` with distractors
`green square` and `blue triangle`), so color-only and shape-only candidates
actually occur during teaching. Option (b) is a documented curriculum change;
it does not alter the live campaign.
