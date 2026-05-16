# Stage 6.5 - Layer-5 Role-Bound Subspace Ablation

**Status:** PASS for representation/readout causality. Not yet a language
generation causality result.

## Plain-English Result

Stage 6.4 showed that Pythia-160M's focus-token layer-5 hidden state can
recover the intended noetic role much better than plain text baselines.

Stage 6.5 asks a sharper question:

> If we remove the exact hidden-state direction that the successful probe
> reads, does the CAS readout collapse?

Answer: yes.

The locked-test readout went from `73.9%` accuracy to `10.0%` accuracy after
the noetic probe subspace was removed. `10.0%` is chance for ten noetic
classes.

Thirty same-rank random removals from the orthogonal complement produced
`0.0` mean disruption and `0.0` max disruption. That means the collapse is not
caused by simply deleting any nine-dimensional slice of the hidden state. It
is specific to the probe-readable noetic subspace.

## Command

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\ablate_stage6_role_bound_layer5.py --input stage6_role_bound_full_20260516.jsonl --activations stage6_role_bound_full_activations_20260516.npz --stage64-report stage6_role_bound_full_probe_report_20260516.json --out-report stage6_role_bound_layer5_ablation_report_20260516.json --n-random 30
```

## Inputs

Dataset SHA-256:

```text
450086d137396cd9906f8458ab37ead041ead1842fbfa866d47326befd155710
```

Activation SHA-256:

```text
6641e28519eefeadc66d053c4996075d640401f6f650ef14b80435ccd57206f2
```

Stage 6.4 report:

```text
stage6_role_bound_full_probe_report_20260516.json
```

## Design

The script retrains the Stage 6.4 headline probe:

- readout: `focus_token`
- layer: `5`
- split: locked Stage 6.2 train/val/test

Then it constructs the probe-readable raw activation subspace:

1. Take the logistic regression coefficients from standardized space.
2. Convert them back to raw hidden-state directions using the scaler.
3. Build an orthonormal basis with SVD.
4. Remove that subspace from locked-test activations.
5. Re-run the same trained probe without retraining it.

Random controls:

- 30 random same-rank subspaces
- sampled from the noetic subspace's orthogonal complement
- same ablation method
- same locked-test rows

## Results

| Measurement | Value |
|---|---:|
| Subspace rank | 9 |
| Baseline test accuracy | 0.7393 |
| Noetic-subspace-ablated test accuracy | 0.1000 |
| Noetic disruption | 0.6393 |
| Changed prediction rate | 0.9007 |
| Random mean disruption | 0.0000 |
| Random max disruption | 0.0000 |
| Empirical p, random >= noetic | 0.0323 |

After ablation, the probe collapses to a single fallback class:

```text
pred_distribution: {"6": 1400}
```

That is not a good model result; it is exactly the expected collapse pattern
when the readout signal has been removed and the classifier falls back to its
intercept/remaining bias.

Paired comparison against the unablated readout:

| Case | Count |
|---|---:|
| Both correct | 119 |
| Noetic-ablated only correct | 21 |
| Unablated only correct | 916 |
| Both wrong | 344 |
| Discordant total | 937 |

Random controls were orthogonal to the noetic basis with max absolute cosine:

```text
1.3530843112619095e-16
```

## Verdict

```text
ROLE_BOUND_SUBSPACE_CAUSAL_FOR_PROBE_READOUT
```

Allowed claim:

> The Stage 6.4 readout depends on a specific focus-token layer-5 subspace.
> Removing that subspace collapses the noetic readout to chance, while
> same-rank random orthogonal removals do not.

## Boundary

This does **not** yet prove:

- Pythia's generated language changes when this subspace is removed.
- The subspace causes Pythia's next answer.
- CAS has fully solved the black box problem.
- Glass House AI is product-ready.

This is causal evidence at the representation/readout level. It is stronger
than Stage 6.4 because it does not merely read the signal; it removes the
signal and watches the readout collapse.

The next stage must test live model behavior.

## Next Step

Stage 6.6 should run a generation-hook test:

1. Hook Pythia block 4 output, corresponding to hidden-state layer 5.
2. Remove the same role-bound noetic subspace during generation.
3. Compare baseline vs ablated continuations.
4. Compare against same-rank random orthogonal hooks.
5. Measure whether output text changes in the predicted role-bound direction.

That is the step that can move the claim from:

> CAS can read and causally remove the internal readout signal.

to:

> CAS can read and test a signal that appears to affect what the model says.
