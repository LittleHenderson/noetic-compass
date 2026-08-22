# RESULT v7 — register-diverse hardening — a BOUNDED result — 2026-08-21

**The fix v6 pointed to, tested. Outcome is neither a clean pass nor a clean fail — it is BOUNDED, and register-diverse training did not help.** Real `pythia-160m`, attested engine, layer 6, CPU, `$0`. Raw: `detector_validation_v7_registerdiverse_results.json` (sha256 `a52fafe8…`).

## What ran

Train the valence detector on a **register-diverse** set (explicit + implicit-A, 18 pos / 18 neg), test on **held-out implicit-B** (8 pos / 8 neg — new scenarios never seen), compare on the same held-out set to a char-ngram (n=2,3,4) surface baseline. Residuals cached (each unique sentence captured once).

## Result

| measure | value |
|---|---:|
| register-diverse activation detector (held-out implicit) | **0.750** |
| explicit-only detector, same held-out test | 0.750 |
| **improvement from adding implicit training** | **+0.000** |
| char-ngram surface baseline | 0.688 |
| shuffle null | 0.500 |
| activation beats surface | yes, by **0.062** |
| **verdict** | **NOT HARDENED** (clears 0.70, but margin over surface < 0.10) |

## Honest reading

- **There is a weak, real transferable valence signal:** the activation detector reaches `0.750` on held-out implicit scenarios and beats the surface baseline on *both* implicit sets tested (v6 set A `0.562` vs `0.438`; v7 set B `0.750` vs `0.688`). It consistently, if narrowly, outperforms surface.
- **But it does not certify HARDENED:** the margin over char-ngram is only `0.062`, well under the `0.10` bar. Much of even the implicit-valence separation is still surface-correlated.
- **Register-diverse training did NOT help (`+0.000`):** the hypothesis that mixing explicit + implicit training would produce a surface-robust direction is **not supported** on this model/scale. The detector's implicit-valence performance is what it is regardless of training register mix.
- **Set-difficulty variance is large:** explicit-only scored `0.562` on implicit-A (v6) but `0.750` on implicit-B (v7) — the two implicit sets differ in how much residual lexical valence they carry. At `n=16` these numbers are noisy; do not over-read either.

## Net across v6 + v7 (the honest state of the valence detector)

- Same-register cross-topic (v1–v3): perfect, but register-bound.
- Surface-controlled implicit: `0.56`–`0.75`, **beats surface but does not clear the hardening bar**; register-diversity does not fix it.
- **Conclusion:** the valence axis carries a genuine but weak transferable component on real activations; the harness **cannot yet certify a surface-robust valence detector at this model scale / n.** The likely levers are larger `n`, a larger model, or a **causal** test (ablate the direction and measure behavioral change) rather than a correlational probe.

## Claim states

- **Real:** all captures, both detectors, the surface baseline, the shuffle null, every number.
- **Accepted / Licensed:** none — NOT HARDENED.
- **Open:** larger n; a larger model; a causal-ablation test of the direction; the same control for Domain-4 and Operator-10.

**No pod. No GPU. `$0`. A bounded result kept exactly as strong as its evidence.**
