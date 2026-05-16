# Stage 6.6C - Rank-1 Focus-Token-Localized Generation Hook

**Status:** rank-1 localized hook did not beat random controls.

## Plain-English Result

Stage 6.6A removed the full 9-dimensional noetic subspace only at the
role-bound `Focus: A/B` token. It showed a small numerical signal, but only
with three random controls.

Stage 6.6C tests a narrower rescue hypothesis:

> Maybe the full 9-dimensional cut damages too much side-information, while
> the single strongest noetic direction is the cleaner generated-language
> control.

Result:

> The top-1 noetic direction changed generation about the same as random
> rank-1 directions. It did not produce a stronger generated-language effect.

This keeps the Stage 6 generated-language claim blocked. Stage 6.4 and 6.5
still stand as discriminative/readout evidence.

## Command

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\ablate_stage6_role_bound_generation_localized.py --input stage6_role_bound_full_20260516.jsonl --activations stage6_role_bound_full_activations_20260516.npz --stage64-report stage6_role_bound_full_probe_report_20260516.json --out-report stage6_role_bound_generation_localized_rank1_hook_report_20260516.json --per-label 2 --n-random 3 --max-new-tokens 8 --rank-mode top1
```

## Scope

| Field | Value |
|---|---:|
| Device | CPU |
| Rows | 20 |
| Rows per noetic | 2 |
| Prompt templates | 3 |
| Noetic cases | 60 |
| Random controls | 3 |
| Rank mode | top1 |
| Removed rank | 1 |
| Full noetic subspace rank | 9 |
| Max new tokens | 8 |
| Runtime | 441.51 seconds |

## No-Hook Reproducibility

Greedy generation was deterministic:

| Metric | Value |
|---|---:|
| Cases | 60 |
| Exact match rate | 1.000 |
| First-step top-1 match rate | 1.000 |
| Mean token match rate | 1.000 |

## Rank-1 Localized Hook

| Metric | Value |
|---|---:|
| Exact continuation match rate | 0.7500 |
| First-step top-1 match rate | 0.9667 |
| Mean token match rate | 0.8854 |
| Mean first-step KL | 0.0086 |

Random rank-1 localized hooks:

| Control | Mean token match | Mean first-step KL |
|---|---:|---:|
| Random 0 | 0.9042 | 0.0059 |
| Random 1 | 0.8854 | 0.0083 |
| Random 2 | 0.8583 | 0.0072 |

Aggregate:

| Metric | Value |
|---|---:|
| Random mean token match | 0.8826 |
| Random mean first-step KL | 0.0071 |
| Noetic extra divergence vs random mean | -0.0028 |
| Noetic extra KL vs random mean | 0.0015 |
| Empirical p, random token match <= noetic | 0.7500 |

Verdict:

```text
LOCALIZED_GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL
```

## Interpretation

Allowed claim:

> Removing only the strongest noetic direction at the focus token does not
> produce a stronger generated-language effect than sampled random rank-1
> removals on this 20-row subset.

Not allowed:

- Rank-1 noetic intervention steers Pythia generation.
- Stage 6 has established generated-language causality.
- The top noetic direction is the hidden generator-side control.

## What This Means

Claude's proposed "wrong dimensionality" rescue does not work in this smoke.
The full localized cut from Stage 6.6A remains the better-looking generation
test, but it still needs a higher-N random-control run before any upgrade.

The current Stage 6 evidence stack is:

- Stage 6.4: CAS labels are recoverable from Pythia hidden states above text
  baselines.
- Stage 6.5: the layer-5 noetic subspace is causal for the probe/readout.
- Stage 6.6/6.6A/6.6C: generated-language causality is not yet established.

## Next Step

Run Stage 6.6B on GPU:

- same focus-token-localized full-subspace hook as Stage 6.6A
- `--rank-mode full`
- `--n-random 30`
- same 20-row subset and prompt templates

That is the direct closure test for the only remaining positive generation
signal. If Stage 6.6B fails, the responsible claim is:

> CAS finds and tests a behaviorally meaningful readout inside Pythia, but we
> have not shown that cutting that readout changes generated language in a
> CAS-specific way.
