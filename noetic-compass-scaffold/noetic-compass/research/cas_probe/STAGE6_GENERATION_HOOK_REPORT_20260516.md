# Stage 6.6 - Live Generation Hook Subset

**Status:** negative against random controls. No language-causality upgrade.

## Plain-English Result

Stage 6.5 showed that the role-bound noetic subspace is causal for the CAS
readout: remove it, and the probe collapses to chance.

Stage 6.6 asked a harder question:

> If we remove that same subspace inside Pythia while it generates text, does
> the generated text change more than it changes under random same-size
> removals?

On the first locked subset, the answer is no.

The noetic removal changed generated continuations, but random same-rank
orthogonal removals changed them more. So this subset does **not** support the
claim that the role-bound noetic subspace has a specific causal effect on
Pythia's generated language.

## Command

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\ablate_stage6_role_bound_generation.py --input stage6_role_bound_full_20260516.jsonl --activations stage6_role_bound_full_activations_20260516.npz --stage64-report stage6_role_bound_full_probe_report_20260516.json --out-report stage6_role_bound_generation_hook_report_20260516.json --per-label 2 --n-random 3 --max-new-tokens 8
```

## Scope

This was intentionally a subset test because local CUDA is unavailable and
generation hooks are expensive on CPU.

| Field | Value |
|---|---:|
| Device | CPU |
| Rows | 20 |
| Rows per noetic | 2 |
| Prompt templates | 3 |
| Noetic cases | 60 |
| Random controls | 3 |
| Max new tokens | 8 |
| Runtime | 450.97 seconds |

Prompt templates:

- `In other words,`
- `The focused role means`
- `A concise explanation is`

## Result

Noetic-subspace removal:

| Metric | Value |
|---|---:|
| Cases | 60 |
| First-step top-1 match rate | 0.9167 |
| Exact continuation match rate | 0.4000 |
| Mean token match rate | 0.6667 |
| Mean first-step KL | 0.0255 |

Random controls:

| Control | Mean token match | Mean first-step KL |
|---|---:|---:|
| Random 0 | 0.6021 | 0.0496 |
| Random 1 | 0.6188 | 0.0336 |
| Random 2 | 0.5396 | 0.0889 |

Aggregate comparison:

| Metric | Value |
|---|---:|
| Random mean token match | 0.5868 |
| Random mean first-step KL | 0.0574 |
| Noetic extra divergence vs random mean | -0.0799 |
| Noetic extra KL vs random mean | -0.0319 |
| Empirical p, random token match <= noetic | 1.0000 |

Verdict:

```text
GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL
```

## Interpretation

Allowed claim:

> In a 20-row locked subset, removing the Stage 6 role-bound noetic subspace
> during generation changed continuations, but not more than random same-rank
> removals.

Not allowed:

- The noetic subspace controls Pythia's generated language.
- CAS can steer this host model's output through that subspace.
- The Stage 6.5 readout-causal result automatically implies
  generation-causal behavior.

This is a useful negative result. It separates two claims:

1. **Supported:** CAS can read and remove the internal signal used by the
   Stage 6 probe.
2. **Not yet supported:** removing that signal specifically changes what
   Pythia says more than random internal removals do.

## Why This May Be Negative

Three plausible explanations need audit:

1. The subspace is real for the readout but not load-bearing for generation.
2. The hook removes the subspace at every sequence position, while the Stage 6
   readout was specifically about the terminal focus token.
3. Same-rank random removals are too strong as a generation control on a small
   CPU subset, because any arbitrary nine-dimensional removal can disturb
   greedy continuation.

The current evidence does not choose between those explanations.

## Next Step

Do not scale to the full 1,400-row generation run yet.

Recommended Stage 6.6A audit/fix:

1. Audit whether the hook should be focus-token-localized instead of applied
   to every token position.
2. Add a smaller-rank control, e.g. one-dimensional top singular direction,
   to test whether rank-9 random removals are too disruptive.
3. Add a no-hook rerun reproducibility control to ensure greedy baseline is
   stable.
4. Only after that, rerun a larger generation subset.

The Stage 6.4 and 6.5 results still stand. Stage 6.6 simply blocks the next
stronger claim about generated language.
