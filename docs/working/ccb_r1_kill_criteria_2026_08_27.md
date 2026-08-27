# CCB-R1 Kill Criteria - Full Pre-Registration (F0-F5, K0, K1-K3)

**Date:** 2026-08-27
**Status:** pre-registration. Locks on merge. Every rule names a condition, a
disposition, and a recording artifact; a kill rule without an artifact is prose.
The margin numbers and the P1-P5 definitions are ruled in
`ccb_r1_kill_criteria_margins_2026_08_27.md` and travel with this document.

---

## Meta-rule (the one-liner)

> **No stage may be declared passing unless its failure conditions were actually
> attempted and the mandatory failures failed.** A suite that never sees its
> expected failures is vacuous, not green.

---

## F0 - Structural conformance (Stage 0)

- **F0.1** Audited section-11 fixture must be REJECTED by stage0_lint.py on every
  run. If it passes: halt; lint regression. Artifact: CI failure + changelog entry.
- **F0.2** Conformant rebuild fixture must PASS on every run. If it fails: halt;
  spec or lint drifted. Artifact: CI failure + changelog entry.
- **F0.3** Placeholder values (ellipsis, NaN, untyped numerics) rejected at
  parse/validation, never coerced. Artifact: regression test.

## F1 - Simulator and golden traces (Stage 1)

- **F1.1** Simulator-vs-source-trace mismatch: halt. Only two exits: fix the
  simulator (source number authoritative) or record a spec-ambiguity ledger
  entry (ACCEPT/DEFER/REJECT). Adjusting traces to match code is banned.
- **F1.2** Zero ambiguities at first contact requires an explicit vacuous-run
  statement in the ledger.
- **F1.3** Non-termination (unbounded descent, cycle, rumination past bounds) =
  build failure, never a warning. NONTERMINATING is a reportable terminal.

## F2 - Fault injection (Stage 2)

- **F2.1** Injected fault missing its named axis -> fail.
- **F2.2** Unfaulted control tripping -> fail (false positive).
- **F2.3** Off-diagonal confusion-matrix entry -> fail that commit. Metrics must
  remain 1.0 / 1.0 / 0.0 or the reason is a specification defect.

## F3 - Truth-firewall sweep (Stage 3)

- **F3.1** Arm A: bias-port sensitivity above epsilon at beta=1 -> firewall FAIL
  -> Stage 5 blocked (epsilon default 0.05). Artifact: sweep report + GREY row.
- **F3.2** Arm B: direction-correctness at or below chance on 3 consecutive seeds
  -> stop, log, withdraw causal language. Artifact: GREY row.
- **F3.3** Controls must keep failing in the same run: rigid fails 3A-sens and
  leaky fails 3A-inv. If controls stop failing, the harness broke.
- **F3.4** Abstention: hallucination rate > 0 on unanswerable OR usefulness below
  floor (default 0.9) on answerable -> fail.

## F5 - Baselines (B0-B2)

- **F5.1** If B0 (association-only) passes a transitive task, the task set no
  longer tests deduction -> invalidate the tasks.
- **F5.2** If B2 random-bias rate >= structured conclude rate, the board design
  fails (topology earns nothing).
- **F5.3** B1 must refuse construction (no bias-free CJT) forever.

## K0 - Idea-level death conditions (Stage 5; pre-registered give-up)

All margins and pinning definitions as ruled in the margins document; summary:

- **K0.1 Honesty (M1 = 20 pp):** abstention margin over the B3 baseline below
  M1 -> the flagship advantage does not exist -> idea dead. Artifact: WITHDRAWN row.
- **K0.2 Firewall (M2 = 5% ceiling, 0 category flips):** movement above the
  ceiling or any flip (P3) -> the exclusion claim is false -> idea dead.
  Artifact: WITHDRAWN row.
- **K0.3 Deduction (M3 = 10 pp, 40-70% calibrated task set):** margin below M3
  -> the reasoning middle is decoration -> idea dead. Artifact: WITHDRAWN row.
- **K0.4 Localization:** fault scorecard degrades (any off-diagonal or false
  positive) -> the diagnostic claim is dead; causal language withdrawn per the
  research paper. Artifact: claim-ledger withdrawal.
- **Sample rule:** n >= 100 paired items per condition, pre-registered;
  threshold judged on the CI lower bound of the paired per-item difference (P4).

## K - Program-level kill criteria

- **K1 (budget):** 3 consecutive failed attempts at the same stage without a
  written rule revision -> stop and escalate. Silent widening banned. The M3
  rebuild loop inherits this budget (P5).
- **K2 (no-progress):** no metric improvement across two consecutive stages ->
  halt and reassess the approach.
- **K3 (external):** Stage 5 starts only after F3.1-F3.3 pass on the real board
  (not toy reasoners); live-model runs require the research paper's Gate-5
  pre-registration with falsifiers fixed before data exists.

## Revision rule

Any change to a threshold, disposition, or the rule set is a dated revision
with a changelog row, applied before the next data-collection run - never after.

## Adoption

Locks as the pre-registration upon merge. Until then it is a draft and may be
edited freely.