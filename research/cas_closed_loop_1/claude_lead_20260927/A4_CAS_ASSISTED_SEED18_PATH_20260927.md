# A4 — Later CAS-assisted seed-18 path (preparation, 2026-09-27)

Status: **PREPARED, GATED, NOT RUN.** Nothing here is authorized to execute. The gate is the joint acceptance of
the CAS engineering checks in the admitted venue (`A5_ACCEPTANCE_PACKAGE_20260927.md`, 142 declared cases at CAS
`7bbf1e0f…` + SI `d7808d59…`, currently `NOT_RUN`). Until that passes, this path stays a document.

## 1. Plain statement of what exists today, and what does not

- The CAS closed loop (`research/cas_closed_loop_1/`) repairs a **symbolic equation fixture**: the pinned Ohm
  calculation (`predicted_flow(Design(drive, constraint))`, cases `test_exact_pinned_ohm_calculation[12-4-3, 12-6-2]`)
  on the native runtime `8182ad52…`. Its witness (`output 3`, 12 host entries, 18 native events) is a **native
  symbolic** execution. It is **not** a HELM neural invocation and must never be presented as one.
- The SI lane (`research/helm_self_improvement/` at `d7808d59…`) admits and journals episodes of the same native
  runtime ("deterministic native execution; injected configuration failure"). It contains **no** call into the HELM
  learned component either; `test_no_model_fixture_refuses_every_non_null_checkpoint` refuses any non-null checkpoint
  by design.
- The HELM learned component is `pointer_learner.py` at `c45f775f…` (Codex's scientific source, outside this lane),
  whose checkpoints are the `.pt` files in the seed-18 receipt. No code path in either lane loads one.

So: before any "learned-component result" is claimed, the model must actually be called through a real bridge that
does not exist yet. Building that bridge is not in Claude's acknowledged scope; its requirements are.

## 2. Design for the comparison, fixed now

Three controller conditions over **one frozen learned checkpoint**, on the same items, same order, same scoring:

| Condition | Controller | What is counted |
|---|---|---|
| C0 fixed | no adaptation; the frozen checkpoint's prediction is the answer | prediction calls only |
| C1 ordinary-adaptive | the existing non-CAS adaptive control in the HELM lane (Codex names the exact one; if none exists, C1 is `NOT_AVAILABLE` and the CAS claim ceiling drops accordingly) | prediction calls + its own repair/verification work |
| C2 CAS closed loop | the real adapter (`native_step_adapter.py`: `grant_for`, `execute_grant`, host-entry meter, `runtime_location` with `return_identity` and `atlas_binding`) driving repair on the native runtime | prediction calls + every granted native call (`I_allocated`, `I_executed`), `actual_primitive_work`, charged native policy units, verification and controller work |

Rules:
- The learned checkpoint is frozen across C0, C1 and C2: same file, same sha256, no training step in any condition.
  Candidate: the seed-18 pass-20 main-course state (identity open, see the seed-18 preregistration) or the Arm A
  pass-30 state once it exists; chosen once, before results.
- **Each original neural prediction is preserved** verbatim (inputs digest, raw output, checkpoint sha256, device,
  torch version) before any repair touches it. The checked system result after repair is reported **separately**,
  never in place of the raw prediction.
- All repair, verification and controller work is counted in the same units for every condition and reported
  alongside the outcome; a condition that spends more work is never compared on outcome alone.
- A CAS-specific advantage may only be stated if C0 and C1 were run under the same budget and the C2 difference
  survives both; otherwise the ceiling is "C2 differs from C0 by k with work w".
- The Q4 experiment and its negative result stay in the record unchanged and are cited, not replaced.

## 3. Bridge requirements (for Codex's scope; Claude supplies the CAS side)

- Real forward call: `restore_checkpoint` of the frozen `.pt` with its `expected_sha256` and run identity, on the
  reference device class (`g7.2xlarge`, torch `2.11.0+cu128`, CUDA `12.8`), then the learner's prediction entry point
  for each item. No CPU inference; `GPU_REQUIRED` fails closed.
- Every prediction record carries: item id, inputs digest, checkpoint sha256, `model_state_identity`, raw output,
  wall time, and the venue. The record is written before the CAS adapter is invoked.
- The CAS adapter is invoked exactly as in the closed loop today: a grant per native step, meter intact, receipts
  with `I_executed <= I_allocated <= 1`, `runtime_location` detached, atlas addresses read-only. The neural output
  enters as an **input** to the native repair (an Idea brought to Mind), not as a native event.
- Evidence bundle, replay and fresh-process reload follow the existing protocol (`run_closed_loop.py replay
  --expected-bundle-digest`), extended with the prediction records' digests so that a replay rejects a changed
  prediction file the same way it rejects a changed journal.
- Disabled-actuator, wrong-method, insufficient-budget and incorrect-result controls run against the bridged path
  with the same test identities as the symbolic path (items 4a-4d in the acceptance package), plus one new negative
  control: a **substituted checkpoint** (different sha256) must be refused before any prediction.

## 4. Sequence and gates

1. Joint acceptance passes in the admitted venue (Codex runner, owner authorization).
2. Codex names the bridge's file scope and the existing ordinary-adaptive controller (or records `NOT_AVAILABLE`).
3. Claude writes the CAS-side bridge contract and its test identities in the lane; Codex builds the neural side.
4. A CPU-only dry admission that proves refusal paths without loading a model.
5. One bounded GPU job per condition, sequential, after the seed-19 continuation and the seed-18 arms; owner-signed.
6. Report: raw predictions, checked results, work counts, per condition; claim ceiling as in section 2.

## 5. Not authorized by this document

Any model load or call; any GPU job; any change to `c45f775f…`; presenting the Ohm fixture as a neural result;
combining this with the growth or schedule comparisons (a combined version comes later, with attribution).
