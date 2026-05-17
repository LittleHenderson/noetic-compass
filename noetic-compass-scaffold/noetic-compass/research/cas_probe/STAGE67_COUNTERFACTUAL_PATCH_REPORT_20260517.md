# Stage 6.7 - Counterfactual Focus-Token Patching

**Status:** counterfactual patching did not show generated-language routing.

## Plain-English Result

Stage 6.6 asked:

> If we delete the noetic signal, does Pythia's generated text change?

That failed.

Stage 6.7 asked a different question:

> If we swap in the matched counterfactual role's focus-token activation, does
> Pythia's generated text move toward that donor role?

That also failed.

The patching mechanics worked. The no-hook baseline was perfectly
reproducible. But the matched counterfactual patch did not move generation
toward the donor more than random donor patches did.

## Method

For each receiver prompt:

1. Generate the receiver baseline continuation.
2. Generate the matched donor baseline continuation from the paired A/B
   counterfactual row.
3. During receiver generation, replace the receiver focus-token hidden state at
   layer 5 with the donor focus-token activation.
4. Compare the patched continuation to both baselines.
5. Compare the true donor patch against random donor patches.

Directional score:

```text
match(patched, donor_baseline) - match(patched, receiver_baseline)
```

Higher is better. A positive score means the patched continuation looks more
like the donor than the receiver.

## Smoke Run

File:

- `stage67_focus_token_patch_smoke_20260517.json`

Scope:

| Field | Value |
|---|---:|
| Receivers | 10 |
| Cases | 30 |
| Random controls | 3 |
| Device | A6000 |
| Runtime | 20.63 sec |

Result:

| Metric | Value |
|---|---:|
| No-hook reproducibility | 1.000 |
| True patch directional score | -0.1250 |
| Random mean directional score | -0.0792 |
| True extra directional vs random | -0.0458 |
| Empirical p | 1.0000 |

Verdict:

```text
COUNTERFACTUAL_PATCH_DIRECTIONAL_EFFECT_NOT_ABOVE_RANDOM_CONTROL
```

## Fresh Confirmatory Run

File:

- `stage67_focus_token_patch_fresh_n30_20260517.json`

Scope:

| Field | Value |
|---|---:|
| Receivers | 40 |
| Cases | 120 |
| Random controls | 30 |
| Device | A6000 |
| Runtime | 493.84 sec |

Result:

| Metric | Value |
|---|---:|
| No-hook reproducibility | 1.000 |
| True patch directional score | -0.0729 |
| Random mean directional score | -0.0646 |
| True extra directional vs random | -0.0083 |
| Empirical p | 0.6774 |

Verdict:

```text
COUNTERFACTUAL_PATCH_DIRECTIONAL_EFFECT_NOT_ABOVE_RANDOM_CONTROL
```

## Interpretation

Allowed:

> Stage 6.7 tested whether matched role-bound focus-token activations route
> generation toward donor continuations. This test did not find that effect.

Not allowed:

- CAS controls Pythia's generated language.
- Pythia routes this noetic readout into continuation text through the tested
  focus-token layer-5 path.
- Stage 6.7 rescues the Stage 6.6 generated-language claim.

## Updated Stage 6 Boundary

Supported:

- CAS finds a role-bound noetic signal in Pythia hidden states.
- The activation readout beats text-only baselines.
- Removing the noetic subspace collapses the CAS readout to chance.

Not supported:

- Removing that signal reliably changes generated language.
- Patching matched counterfactual focus-token activations routes generated
  language toward the donor role.

Best current claim:

> CAS identifies and causally tests an internal noetic readout in Pythia. The
> tested generation routes did not show that this readout controls generated
> language.

## Recommendation

Stop Stage 6 generation-route experiments for now. The honest research result
is already useful:

> Pythia carries a CAS-readable, causally testable noetic readout, but this
> readout did not route into generated language under ablation or
> counterfactual patching.

Next useful work:

1. Update the Stage 6 claims matrix with the 6.7 negative.
2. Refresh the Glass House strategy memo around the bounded result.
3. Only after that, decide whether cross-model replication is worth the time.
