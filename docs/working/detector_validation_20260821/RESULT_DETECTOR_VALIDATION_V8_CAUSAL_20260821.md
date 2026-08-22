# RESULT v8 — causal sufficiency of the valence direction — CAUSALLY LOAD-BEARING — 2026-08-21

**Completes the arc, and reconciles the correlational negative with a causal positive.** Real `pythia-160m`, attested engine, layer 6, CPU, `$0`. Raw: `detector_validation_v8_causal_results.json` (sha256 `…` in file). Script: `detector_validation_v8_causal.py`.

## The different question this asked

v6/v7 asked *can a probe READ valence from activations* — answer: weakly, surface-confounded, NOT HARDENED (correlational). v8 asks the **stronger, orthogonal** question: does **injecting** the validated probe direction into the residual stream during generation **causally steer** the model's valence output, more than a norm-matched random direction? A direction can be a real causal lever even when a readout struggles — so this can add information the probes could not.

## Method

Direction `w` = mean(explicit-pos residuals) − mean(explicit-neg residuals) at layer 6 (the exact v1 detector direction), scaled to norm 6.0. Through the attested engine's `InterventionSpec(mode="additive")`, inject `+w` and `−w` at layer 6 on 4 neutral prompts; the per-prompt **swing** = `M(+w) − M(−w)` on the valence margin. Permutation null: `K=16` random norm-matched directions, same protocol.

## Result — CAUSALLY LOAD-BEARING

| measure | value |
|---|---:|
| probe-direction swing `S_w` (mean over 4 neutral prompts) | **+5.656** |
| per-prompt swings | +5.375, +5.500, +4.875, +6.875 |
| `+w` raised valence on **every** prompt | **yes** |
| random-direction null: mean / std / max\|·\| | 0.176 / 0.588 / **1.188** |
| probe swing vs largest random swing | **4.76×** |
| probe swing above null mean | **≈ 9.3 σ** |
| p-value (two-sided magnitude, K=16) | **0.0588** (floor: beat all 16 nulls) |
| **verdict** | **`CAUSALLY_LOAD_BEARING`** |

The probe direction moved valence far more than any of 16 random directions, consistently and in the predicted direction. The `p = 0.0588` is the **K-limited floor** (1/17 — it exceeded every null), not a weak effect; the honest strength measure is the effect size, ≈ 9.3 σ above the null mean and 4.76× the largest random swing. More null directions would push p arbitrarily low; the effect is not in doubt.

## The reconciliation — this is the important part

- **Correlational (v6/v7): the direction reads implicit valence only weakly (`~0.56–0.75`), surface-confounded, NOT HARDENED.**
- **Causal (v8): the SAME direction is a strong, real valence lever (`CAUSALLY_LOAD_BEARING`).**

These are not contradictory — they are two different properties, now both measured honestly. The direction **is** a genuine valence axis in the model's geometry (you can steer with it), but a nearest-centroid **readout** of it cannot cleanly classify implicit-valence sentences because the readout is confounded by other surface variance. **Causal sufficiency ≠ correlational-readout robustness.** The harness now has evidence on both, separated — which is exactly the kind of distinction a real interpretability harness should surface.

## Honest scope

- This is causal **sufficiency** (injecting steers output), not causal **necessity** (ablating removes valence) — the attested engine has no runtime directional-projection mode, so necessity was not tested. Scope stated, not overstated.
- `n=4` neutral prompts; the effect is large and consistent but the prompt set is small.
- `p` is K-limited (K=16); reported as a floor with the σ effect size as the primary measure.
- Partially strengthens the earlier CAV steering run (8.69× targeting) by using the **validated probe direction** (not a single contrast pair) and adding a permutation null with an effect size.

## Claim states

- **Real:** all interventions on real weights through the attested engine; the probe direction; the 16-direction null; every number.
- **Accepted / Licensed:** none — research-grade.
- **Open:** causal **necessity** (needs a projection/ablation mode); larger prompt set; tighter p (more nulls); the same causal test for `^8`/`^9`, Domain, Operator directions.
- **Not licensed:** any product sentence citing these numbers.

**No pod. No GPU. `$0`.** The valence axis: same-register readable (v1–v3), surface-confounded as an implicit readout (v6/v7 BOUNDED/NEGATIVE), and **causally load-bearing as a steering direction (v8)** — three honest, separated properties on real weights.
