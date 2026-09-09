# Graph-first ^6 — competence run 001: STAGE-1 GATE STOPPED THE JOB (as designed; gate defect fixed)

Status: **AWS_COMPETENCE_FAILED / STAGE1_CHECK_FAILED.** The in-job gate
did exactly what the owner specified — it stopped before any training when
the relationship check failed — and in doing so exposed a defect in MY gate
implementation, now fixed. Ledger 40 → 41 (`$210.00 → $214.00` reserved,
`$190.00 → $186.00` unreserved); the reservation stands — no refund, no
automatic retry. Cleanup complete; instance `i-0236ca5c706659fed` confirmed
terminated; collected result sha `86d9b738…` verified.

## What the run measured

The worker reached stage 1 on the GPU and the gate refused:
`RELATIONSHIP_PRESERVATION_CHECK_FAILED` on record `7f5bae88…`. The gate
compared MODULE OUTPUT differences (rewire vs reorder) with a 10×
tolerance; the module's output crushed the input distinction (its fixed
bias/tanh operating point dominates the tiny Hadamard-bound inputs), so the
ratio failed. The stage-1 numbers themselves were NOT preserved in the
result — my gate raised a bare exception before writing them.

## The two gate defects, fixed (test-locked; 129 graph tests pass)

1. **Wrong quantity gated.** The owner's requirement table asks for
   distinguishable module INPUTS beyond the reorder baseline; outputs are to
   be REPORTED, not gated (a changed argmax/response is not required on
   every contrast). The gate now uses the INPUT difference (rewire >
   10× reorder input baseline); output differences are reported alongside.
2. **Failure did not preserve the numbers.** A stage-1 failure now returns a
   complete result with `outcome: "STAGE1_CHECK_FAILED"` and the preserved
   `stage1` measurements — never a bare exception.

## What this does NOT change

- No training ran; no capability claim follows; the two-arm comparison
  stays postponed.
- The replacement runs the SAME fixed sequence with the corrected gate and
  needs a NEW owner GO and one new `$4.00` reservation (ledger 41 → 42:
  `$218.00` / `$182.00`).
