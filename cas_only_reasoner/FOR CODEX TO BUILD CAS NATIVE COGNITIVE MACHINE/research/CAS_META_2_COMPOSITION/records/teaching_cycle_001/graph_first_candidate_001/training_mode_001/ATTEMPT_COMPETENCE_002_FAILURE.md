# Graph-first ^6 — competence run 002: STAGE-1 GATE STOPPED AGAIN — and this time the preserved numbers prove why

Status: **AWS_COMPETENCE_FINISHED / STAGE1_CHECK_FAILED.** The fixed gate
stopped the job BEFORE any training and — unlike run 001 — RETURNED the
preserved stage-1 measurements. Ledger 41 → 42 (`$214.00 → $218.00`
reserved, `$182.00` unreserved); the reservation stands — no refund, no
automatic retry. Cleanup complete (instance `i-06d15fca213df9fcc` confirmed
terminated; collected result sha `99d45ea9…`; receipt
`receipt_cas-meta2-competence-20260909195309-68ac4845/`).

## What the preserved numbers show (the real reason the gate refused)

| Check | Value |
|---|---|
| forward/backward sanity | PASSED (losses 1.089–1.104 finite; gradients 0.14–0.24 on all three matrices) |
| rewire input difference (record 1) | `0.0` (reorder `0.0`) |
| rewire input difference (record 2) | `1.9048e-4` (reorder `1.9048e-4`) |

The rewire produced NO distinguishable module input beyond the reorder —
not because the binding rule is wrong (the pure vector-level test passes),
but because of SCALE: the raw Hadamard products over ~7–13 token rows are
~8 orders of magnitude smaller than the mean-pooled framing/request text
added on top. In float32, the relationship distinctions sit below the noise
floor of the summed vector — the module literally cannot receive them. The
gate measured this numerical drowning exactly as designed.

## The fix (documented change to the encoding rule, test-locked)

Each bound line is now UNIT-NORMALIZED after the Hadamard product (fixed
computation, no learned parameters): every structural line contributes at
O(1) scale, so the structure dominates the input instead of drowning in it.
The rule amendment is recorded in `RELATIONSHIP_ENCODER_001.md` and the
adapter spec. The structural test now verifies the rewire-vs-reorder
contrast on balanced fake rows (large rewire difference, ~zero reorder
difference). 129 graph tests pass.

## What this does NOT change

- No training ran; no capability claim; the two-arm comparison stays
  postponed; the module, option path, learning scope, and allowance are
  unchanged.
- The replacement runs the SAME fixed sequence with the normalized encoder
  and needs a NEW owner GO and one new `$4.00` reservation (ledger 42 → 43:
  `$222.00` / `$178.00`).
