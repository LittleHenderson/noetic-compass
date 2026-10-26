# CAS-LAB-014 — Phase 3 valve acceptance on the full exam: preregistration (2026-10-25)

Status: **preregistered before the AWS run.** Closes the gap recorded in `CAS_LAB_013`: the accepted result covered
the first 300 of 1,517 exam rows and explicitly said the other 1,217 were not tested.

## 1. Question

Does the Phase 3 `G-ABSENT` valve hold its accepted property across the **entire** 1,517-row exam, for two different
reply populations, with the same fixture oracle and the same controller?

## 2. Design (frozen)

- Controller: `tks_meta_valve_controller.py` at the committed revision, default aperture 0.75.
- Oracle: `test_phase3_valve_ctt_acceptance._expected_failure`, unchanged.
- Conditions: (a) A4-s1 step-1,000 generations, (b) A4-s1 final (step-6,000) generations. Both 1,517 rows, already
  produced under the frozen generation path.
- Rows: all 1,517 exam rows, in file order. No sampling, no exclusions.
- Host: AWS `t3.small` in us-west-2 (CPU only; the valve is pure Python/Decimal), one instance, ≤600 s, ≤US$0.50.

## 3. Predeclared acceptance bar

The run **passes** only if **all** hold for **both** conditions:

1. fixture-rule violations admitted = **0**;
2. fixture-compliant items refused = **0**;
3. receipts recomputed = 1,517 and unique full receipts = **1,517**;
4. oracle/controller mismatches = **0**.

Any single failure is reported as FAIL for that condition. The run is not allowed to drop rows to meet the bar.

## 4. What it licenses

Only: "on this fixed 1,517-row exam and these two reply populations, the valve admitted no reply that the lexical
fixture oracle flags and refused no reply it does not flag, with a recomputable receipt per row."

It does **not** license general zero-hallucination, semantic correctness, or any claim about model change.

## 5. What would change a decision

A failure on any condition would falsify the extension of CAS-LAB_013 to the full exam and would put the v0.4
"0-leak RPM interlock" roadmap status back to a 300-row-only claim.
