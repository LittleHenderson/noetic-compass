# Stage 6.6 Paired Re-Analysis

**Status:** full localized hook is gray-zone promising; rank-1 remains null.

## Why This Re-Analysis Exists

The original Stage 6.6A report compared aggregate means:

```text
noetic token match vs random-control token match
```

That is useful, but it throws away pairing. Every noetic intervention has
matched random interventions on the same sample and same prompt template.

This re-analysis keeps that pairing:

```text
delta = mean(random token-match) - noetic token-match
```

Positive delta means the noetic intervention disrupted generation more than
matched random controls.

## Full Localized Hook, Stage 6.6A

Source:

- `stage6_role_bound_generation_localized_hook_report_20260516.json`

Scope:

- full noetic subspace
- focus-token-localized hook
- 20 rows
- 3 templates
- 60 paired cases
- 3 random controls

Result:

| Level | n | Mean delta | 95% bootstrap CI | Sign-flip p |
|---|---:|---:|---:|---:|
| Case/template | 60 | +0.0361 | [-0.0146, +0.0924] | 0.1030 |
| Sample | 20 | +0.0361 | [-0.0132, +0.0889] | 0.1005 |

Template deltas:

| Template | Mean delta |
|---|---:|
| `concise_explanation` | +0.0708 |
| `focused_role_means` | +0.0333 |
| `in_other_words` | +0.0042 |

Plain-English read:

> The full localized noetic hook still points in the expected direction after
> paired analysis, and all three templates are positive. But p is about 0.10,
> so this is not a claim-bearing pass.

## Rank-1 Localized Hook, Stage 6.6C

Source:

- `stage6_role_bound_generation_localized_rank1_hook_report_20260516.json`

Scope:

- strongest noetic direction only
- focus-token-localized hook
- 20 rows
- 3 templates
- 60 paired cases
- 3 random controls

Result:

| Level | n | Mean delta | 95% bootstrap CI | Sign-flip p |
|---|---:|---:|---:|---:|
| Case/template | 60 | -0.0028 | [-0.0472, +0.0444] | 0.5513 |
| Sample | 20 | -0.0028 | [-0.0507, +0.0410] | 0.5377 |

Plain-English read:

> Rank-1 does not survive paired analysis. The "wrong dimensionality" rescue
> is not the next best path.

## Decision

This lands exactly in the gray zone:

- not strong enough to claim generated-language causality
- not weak enough to abandon the full localized hook
- strong enough to justify a confirmatory GPU run

Next run should be:

1. **Apples-to-apples 6.6B:** same 20 rows, full localized hook,
   `n_random=30`.
2. **Fresh confirmatory holdout:** deterministic seeded selection,
   exclude the old 20 rows, `per_label=4`, full localized hook,
   `n_random=30`.

The fresh holdout is the load-bearing result. The repeated 20-row run is only
for continuity with Stage 6.6/6.6A/6.6C.

## Pass Gate For The Fresh Holdout

Pass requires:

- no-hook reproducibility remains exact
- noetic token-match is lower than random controls
- paired sample-level sign-flip p <= 0.05
- mean delta >= +0.03
- at least 2 of 3 templates have positive mean delta

If it fails:

> CAS finds and causally tests a noetic readout inside Pythia, but this
> experiment does not show generated-language causality.
