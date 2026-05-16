# Stage 6.6B - Localized Generation Hook Closure

**Status:** generated-language causality not established.

## Plain-English Result

Stage 6.4 and 6.5 proved a real internal readout result:

- CAS labels can be recovered from Pythia hidden states above text baselines.
- Removing the noetic subspace collapses the CAS probe/readout to chance.

Stage 6.6B asked the harder question:

> Does removing that noetic subspace reliably change what Pythia says?

Answer:

> No. The full focus-token-localized intervention does not beat matched random
> controls when tested with 30 random controls.

That means the generated-language causal claim stays blocked.

## Runs

Both runs used:

- full 9-dimensional noetic subspace
- layer 5
- focus-token-localized hook
- `n_random=30`
- `max_new_tokens=8`
- NVIDIA RTX A6000

## Run 1: Apples-To-Apples Old Subset

Command shape:

```bash
python ablate_stage6_role_bound_generation_localized.py \
  --input stage6_role_bound_full_20260516.jsonl \
  --activations stage6_role_bound_full_activations_20260516.npz \
  --stage64-report stage6_role_bound_full_probe_report_20260516.json \
  --out-report stage6_role_bound_generation_localized_full_n30_hook_report_20260517.json \
  --per-label 2 \
  --n-random 30 \
  --max-new-tokens 8 \
  --rank-mode full
```

Result:

| Metric | Value |
|---|---:|
| Rows | 20 |
| Prompt cases | 60 |
| No-hook reproducibility | 1.000 |
| Noetic mean token match | 0.9021 |
| Random mean token match | 0.8875 |
| Extra divergence | -0.0146 |
| Aggregate empirical p | 0.7097 |
| Sample-level paired sign-flip p | 0.8006 |
| Positive templates | 1 / 3 |

Verdict:

```text
LOCALIZED_GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL
```

Plain English:

> The old 20-row subset did not replicate the 6.6A numerical signal once the
> random-control count increased from 3 to 30.

## Run 2: Fresh Confirmatory Holdout

Command shape:

```bash
python ablate_stage6_role_bound_generation_localized.py \
  --input stage6_role_bound_full_20260516.jsonl \
  --activations stage6_role_bound_full_activations_20260516.npz \
  --stage64-report stage6_role_bound_full_probe_report_20260516.json \
  --out-report stage6_role_bound_generation_localized_fresh_n30_hook_report_20260517.json \
  --per-label 4 \
  --n-random 30 \
  --max-new-tokens 8 \
  --rank-mode full \
  --selection-mode seeded \
  --selection-seed 20260517 \
  --exclude-report stage6_role_bound_generation_localized_hook_report_20260516.json
```

Result:

| Metric | Value |
|---|---:|
| Rows | 40 |
| Prompt cases | 120 |
| No-hook reproducibility | 1.000 |
| Noetic mean token match | 0.8760 |
| Random mean token match | 0.8860 |
| Extra divergence | +0.0100 |
| Aggregate empirical p | 0.2258 |
| Sample-level paired sign-flip p | 0.2932 |
| Positive templates | 2 / 3 |

Verdict:

```text
LOCALIZED_GENERATION_EFFECT_NUMERICALLY_ABOVE_RANDOM_CONTROL
```

Plain English:

> The fresh holdout points weakly in the expected direction, but the effect is
> small, below the +0.03 pass floor, and not statistically reliable.

## Gate Result

The pre-declared pass gate was:

| Gate | Old subset | Fresh holdout |
|---|---:|---:|
| No-hook reproducibility = 1.000 | Pass | Pass |
| Noetic disrupts more than random | Fail | Pass, tiny |
| Paired p <= 0.05 | Fail | Fail |
| Extra divergence >= +0.03 | Fail | Fail |
| At least 2 / 3 templates positive | Fail | Pass |

Final gate:

```text
FAIL
```

## Final Stage 6.6 Interpretation

Allowed:

> CAS can identify a role-bound noetic signal in Pythia hidden states and
> causally remove it from the CAS readout.

Not allowed:

> CAS has shown that this noetic subspace reliably changes Pythia's generated
> language.

Best current claim:

> CAS finds and tests a meaningful internal readout inside Pythia, but this
> experiment did not show generated-language causality.

## Recommendation

Do not keep tuning Stage 6.6 hook variants as a rescue path. The three tested
generation interventions now agree enough:

- all-token full-subspace hook: negative
- focus-token full-subspace hook with real controls: negative / tiny
- focus-token rank-1 hook: negative

The next useful work is either:

1. **Claims Matrix:** write the stakeholder-safe Stage 6 evidence matrix so the
   project can state exactly what is proven and what is not.
2. **Stage 6.7 counterfactual patching:** test whether copying the focus-token
   activation from role A into role B changes the continuation in the predicted
   direction. Treat this as a different causal test, not as a rescue of 6.6.
