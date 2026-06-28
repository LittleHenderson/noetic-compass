# MTC Pre-Registration — Proposed Amendment A1 (DRAFT, pending sign-off + freeze)

**Date:** 2026-06-03
**Status:** DRAFT — proposed for founder review. NOT frozen. Must be reviewed, approved, and WORM-anchored **before** the Condition-3 20B comparator is scored (per prereg §0.2 / §10, "do not freeze until WORM-anchored").
**Amends:** `cas_harness_matched_taxonomy_control_prereg_20260530.md` (Draft v0.2)
**Scope of change:** MTC.1 **instrument fixture only.** Substrate, hypotheses, controls, scoring, and pre-registered margins are unchanged.

## A1.1 Why this amendment is needed

The original MTC.1 plan applied the NC40 (Control B) / NC28 (Control C) matched-taxonomy manifests to the existing GPT-NeoX-20B Stage 9 40E / Foundation-28 fixtures (abstract A/B TKS comparison prompts). Two facts make that path unrunnable as written:

1. **The abstract fixtures are ineligible to carry a coherent orthogonal non-CAS taxonomy.** Materializing NC40 against the Stage 9 original scenarios covered only **142 of 2,560** required train rows (most NC40 cells empty) because the abstract prompts lack ordinary topic/event content. Per **§4 rule 4**, the correct action is to **BLOCK**, not weaken — so an MTC.1 on the abstract fixtures is a BLOCKED non-result, not a verdict. (Record: `cas_harness_mtc_stage9_40e_assignment_blocked_20260530.{md,json}`.)
2. **The prior 20B MTC FALSIFY is withdrawn as a fixture artifact.** The earlier GPT-NeoX-20B run that returned FALSIFY used a dual-labeled fixture since **quarantined** (meaning-stripped / anti-drift-violating; "DO NOT USE"). Its near-chance hidden readout is a property of that broken fixture, **not** evidence about CAS specificity. It is withdrawn from the decision record and must not be cited as a CAS-specificity result.

## A1.2 The amendment

MTC.1 is run on the **Condition-3 topical-scenarios instrument**:
- **Fixture:** `docs/working/mtc_matched_taxonomy_20260530/mtc_condition3_topical_scenarios_20260531.jsonl` (1,440 rows; 40 elements balanced at 36 each; train/test 720/720).
- **Manifest / views:** `mtc_condition3_topical_scenarios_20260531_manifest.json`, `mtc_condition3_capture_view_20260531.json`, `control_c_nc28_balanced_view_20260531.json`.
- **Design intent:** real CAS meaning carried in ordinary scenarios with an **orthogonal** topic/frame scaffold, so NC40/NC28 assign from non-CAS prompt content **without reading any CAS field** (satisfies §4 rules 1–3).
- **Local readiness** (all three $0 gates GREEN per `CONDITION3_CAPTURE_READINESS_20260531.md`): Surface Gate PASS (CAS text leakage ≈ chance), Fixture-Eligibility ELIGIBLE (NC40 reconstructs from `control_semantic` only, balanced, orthogonal within the permutation null), Meaning-Preservation PASS (40/40 reader recovery — self-rated; see A1.4).

## A1.3 What is explicitly unchanged (no weakening)

- **Substrate:** GPT-NeoX-20B. MTC.1 remains the 20B decision gate; Pythia-160M and the other points remain the **conditional MTC.2** extension, gated on MTC.1.
- **Hypotheses** H-MTC-1..4; **Controls** A (scrambled) / B (NC40) / C (NC28) / D (lexical); probe family; frozen splits; flat + nested lacunarity scoring; all pre-registered margins; and the **BLOCK-don't-weaken** rule.
- Only the **instrument fixture** changes (abstract-ineligible → concrete-eligible), with the documented justification above. This **raises** comparator eligibility; it does not relax any test.

## A1.4 Integrity conditions

1. This amendment is **reviewed, approved, and frozen/WORM-anchored before** the Condition-3 20B activations are scored by `run_matched_taxonomy_control.py`. The 20B forward-pass **capture is claim-neutral data collection** and may precede the freeze; the **comparator run (the claim) occurs only after the freeze.**
2. The Condition-3 **Meaning-Preservation gate was self-rated** (40/40). An independent human rating is recommended hardening before any claim-bearing PASS is published, and is logged as an open strengthening — not a blocker for running the comparator.
3. Decision mapping unchanged: **PASS / GREY / FALSIFY / BLOCKED** per the runner's pre-registered gates. A FALSIFY or GREY on Condition-3 leaves the Stage 9 40E packet at **FLAG_FOR_HUMAN_REVIEW** (the current WORM-anchored status).

---
*Proposed by Claude (Opus 4.8) for founder review, 2026-06-03. Do not freeze without founder sign-off. The frozen + WORM-anchored version supersedes this draft.*
