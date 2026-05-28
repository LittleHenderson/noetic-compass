# CAS Harness Correct Baseline Methodology - Global Note

Date: 2026-05-27

Read this before running or summarizing any CAS Harness probe/readout result.

## The Rule

A hidden-state probe number is not enough. Every claim-bearing readout must report:

1. hidden-state readout accuracy,
2. majority/chance baseline,
3. shuffled-label hidden-state control,
4. exact-fixture text-only baseline,
5. split and group-overlap proof.

If text-only is at or above the pre-registered ceiling, the run can still show internal signal, but it cannot claim CAS beats surface text.

## What Went Wrong

The compact-gloss TKS40 v0 library reached `100.00%` text-only accuracy. That means the wording carried the answer strongly enough for a classifier that never touched the model. That library is diagnostic-only for CAS-beats-text purposes.

This does not make canonical TKS language invalid. The issue is not "colloquialisms are leakage by default." The issue is simpler: if the exact fixture lets text-only win too easily, it cannot support the specific comparison claim.

## Correct 40E Method

- Canonical label: `S9-40E-ORIGINAL-BASELINE-READOUT`
- Plain-English name: **Stage 9 40-Element Original-Fixture Balanced Readout**
- Fixture: original Stage 9 role-bound/counterfactual scenario library
- Axis: 40 Elements = 10 Noetics x 4 Domains
- Readout: `StandardScaler + LogisticRegression(C=0.1, class_weight="balanced")`
- Split: fixed historical Stage 9 train/test split
- Grouping: zero train/test group overlap

## GPT-NeoX-20B Result

| Measure | Result |
| --- | ---: |
| Model | `EleutherAI/gpt-neox-20b` |
| Rows | `8,320` |
| Classes | `40` |
| Samples per class | `208` |
| Train / test | `3,840 / 4,480` |
| Train/test group overlap | `0` |
| Best layer | `2` |
| Hidden readout accuracy | `95.625%` |
| Hidden macro-F1 | `95.617%` |
| Confirmed CountVectorizer text baseline | `49.241071%` |
| Evaluator text-hash baseline | `50.000%` |
| Majority baseline | `2.500%` |
| Shuffled-label mean | `2.619%` |
| Shuffled-label max | `3.304%` |

Plain English: on the original Stage 9 40-Element task, GPT-NeoX-20B's hidden states carry the TKS40/CAS structure far more strongly than surface text alone.

## Claim Boundary

This is a readout-tier replication. It is not yet:

- causal ablation,
- eta-to-epsilon bridge,
- Evidence Packet verifier merge,
- ACCEPT/SUPPRESS production verdict.

## Anti-Drift Checklist

- Do not use compact-gloss TKS40 v0 for CAS-beats-text claims.
- Do not report hidden readout without its exact text-only baseline.
- Do not call source-derived TKS language "leakage" by default.
- Do block the comparison claim if text-only is too high.
- Do preserve split, grouping, hashes, and scenario provenance in the Evidence Packet.
