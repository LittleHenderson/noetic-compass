# Stage 14 Weight Geometry / Alignment Gates

Date: 2026-05-19

## Purpose

Inspect whether the Stage 14 Pythia-2.8B CAS Foundation probe subspace is unusually aligned with the host model's static token-weight geometry.

This is not an activation-firing test. Weights do not fire. Weights are static matrices. This diagnostic compares a trained CAS readout subspace against:

- output embedding / unembedding geometry
- input embedding geometry
- random same-rank subspace controls
- logit-lens energy on locked test activations

## Inputs

- Fixture: `stage7_foundation_pilot_20260517.jsonl`
- Activations: `stage14_pythia28b_activations_20260518.npz`
- Model: `EleutherAI/pythia-2.8b`
- Selected Stage 14 layer: validation-selected layer `14`

## Diagnostic Gate

This is a diagnostic, not a pass/fail product claim.

Report:

1. Probe rank and selected-layer readout accuracy.
2. Output-weight energy fraction of CAS subspace vs random same-rank controls.
3. Input-weight energy fraction of CAS subspace vs random same-rank controls.
4. Logit-lens energy fraction on locked test activations vs random same-rank controls.
5. Top decoded tokens for each class probe direction as an interpretability aid.

## Allowed Claim

> CAS Harness can inspect whether a learned CAS readout subspace is geometrically aligned with static model weight matrices.

## Not Allowed

- Weights fired.
- Exact neurons caused the answer.
- Weight alignment proves generation control.
- Top decoded tokens are definitive semantic explanations.
