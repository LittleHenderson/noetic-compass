# Stage 6.6A - Focus-Token-Localized Generation Hook

**Status:** numerical signal above random controls, not a reliable pass.

## Plain-English Result

Stage 6.6 used a broad hook that removed the noetic subspace from every token
position. That was probably too blunt because the Stage 6 readout was measured
at one place: the terminal `Focus: A/B` token.

Stage 6.6A fixed that design issue. It removed the same layer-5 noetic subspace
only at the original focus-token position during generation. It also added a
no-hook reproducibility control.

Result:

> The localized noetic hook changed generated text slightly more than localized
> random hooks, but the effect is small and not statistically reliable with
> only three random controls.

This is better than Stage 6.6, but it is not enough to upgrade the claim.

## Command

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\ablate_stage6_role_bound_generation_localized.py --input stage6_role_bound_full_20260516.jsonl --activations stage6_role_bound_full_activations_20260516.npz --stage64-report stage6_role_bound_full_probe_report_20260516.json --out-report stage6_role_bound_generation_localized_hook_report_20260516.json --per-label 2 --n-random 3 --max-new-tokens 8
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
| Max new tokens | 8 |
| Runtime | 435.13 seconds |

## No-Hook Reproducibility

Greedy generation was deterministic:

| Metric | Value |
|---|---:|
| Cases | 60 |
| Exact match rate | 1.000 |
| First-step top-1 match rate | 1.000 |
| Mean token match rate | 1.000 |

This matters because it proves the observed differences come from the hooks,
not from nondeterministic generation.

## Localized Noetic Hook

| Metric | Value |
|---|---:|
| Exact continuation match rate | 0.6500 |
| First-step top-1 match rate | 0.9833 |
| Mean token match rate | 0.8313 |
| Mean first-step KL | 0.0092 |

Random localized hooks:

| Control | Mean token match | Mean first-step KL |
|---|---:|---:|
| Random 0 | 0.8771 | 0.0083 |
| Random 1 | 0.8438 | 0.0084 |
| Random 2 | 0.8813 | 0.0064 |

Aggregate:

| Metric | Value |
|---|---:|
| Random mean token match | 0.8674 |
| Random mean first-step KL | 0.0077 |
| Noetic extra divergence vs random mean | 0.0361 |
| Noetic extra KL vs random mean | 0.0014 |
| Empirical p, random token match <= noetic | 0.2500 |

Verdict:

```text
LOCALIZED_GENERATION_EFFECT_NUMERICALLY_ABOVE_RANDOM_CONTROL
```

## Interpretation

Allowed claim:

> When the intervention is localized to the focus token, noetic-subspace
> removal perturbs generation slightly more than the sampled random controls
> on this 20-row subset.

Not allowed:

- The effect is statistically established.
- CAS can steer Pythia's generated language through this subspace.
- Stage 6 has solved generated-language causality.

The p-value cannot pass with only three random controls; the smallest possible
empirical p with this setup is `0.25`. So the current result should be treated
as a design signal, not a scientific conclusion.

## Why This Matters

Stage 6.6 was negative because random all-token removals were more disruptive
than noetic all-token removal. Stage 6.6A shows that a more precise,
focus-token-localized intervention moves in the expected direction.

That suggests the previous all-token hook was probably too broad. But it does
not yet prove the localized effect is robust.

## Next Step

Stage 6.6B should rerun this localized hook with more random controls, ideally
on GPU:

- same 20-row subset
- `n_random >= 30`
- same prompt templates
- same max-new-token setting

If the noetic token-match rate remains lower than the random-control
distribution with a real empirical p-value, then we can upgrade from
"numerical signal" to "localized generation effect above random control."

If not, the generated-language claim remains blocked while Stage 6.4 and 6.5
remain valid.
