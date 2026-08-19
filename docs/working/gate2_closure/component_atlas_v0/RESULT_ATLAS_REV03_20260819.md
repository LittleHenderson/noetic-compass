# RESULT — Component Atlas rev 0.3, pythia-2.8b (2026-08-19)

**Verdict: `GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE` — 1 test evaluable, 0 passed.**
Run: `EleutherAI/pythia-2.8b` rev `2a259cdd…`, `revision_verified: true`, A40, 4565.5 s (76 min).
Report: `atlas_v0_rev03_report.json`. The prereg named this outcome in advance as the second
likely result, so it is a predicted GREY, not a surprise.

| Test | Status | The number that decided it |
|---|---|---|
| `DR_F5` rail | `VACUOUS_NO_BEHAVIORAL_CHANGE` | text changed on **0.469** of judge prompts (< 0.60) |
| `DR_F2` rail | `VACUOUS_NO_BEHAVIORAL_CHANGE` | same channel failure |
| **`AMP_F5` amplifier** | **`FAIL`** | **the only evaluable test — see below** |
| `RS_F5` brake | `VACUOUS_NO_BRAKE` | precondition G1 p=**0.5056**, G2 p=**0.6983** |
| `CONN` wiring | `VACUOUS_NO_BEHAVIORAL_CHANGE` | shares DR-F5's condition |
| `MEM` sanity | `SANITY_FAIL` | (outside aggregate) |
| **`CHECK` sanity** | **`SANITY_PASS`** | **first sanity pass in the project — see below** |

## THE INSTRUMENT IS NOW PROVEN ALIVE (`CHECK_SANITY: SANITY_PASS`)
Ablating 31 induction heads moved the gate score **12.465 → 5.436 nats, a drop of 7.029**,
against a best control drop of **0.821** — **8.6× the best of 24 count-matched control head
sets**, `control_ensemble_p = 0.04`. This is the first `SANITY_PASS` in the project and it
settles the rev-0.2 ambiguity: **large, statistically selective causal effects ARE detectable
with this apparatus.** Therefore the GREY below cannot be waved away as "the instrument
isn't measuring." The instrument measures. The component hypotheses are what failed.

## `AMP_F5` — a decisive FAIL, and the most informative number in the run
Not underpowered. The opposite:
- Removing the F5 direction produced a **highly significant** drop: `targeted_drop 0.366`,
  `wilcoxon_pratt_p = 5.5e-05`, behavioural-change `0.969`, and the attenuation signature
  held (`presence 0.781 → 0.781` with magnitude down — present but weaker, exactly as
  preregistered for an amplifier).
- **But it was not SELECTIVE.** Size-matched random directions dropped it **more**
  (`max_matched_control_drop 0.977` vs targeted `0.366`, i.e. 2.7×), so
  `control_ensemble_p = 0.16`. And the **F2 (Wisdom) direction moved F5 content MORE than
  F5's own direction did** (`effect_size_cross_rail 0.463` vs `effect_size_target 0.243`),
  failing the cross-rail selectivity gate.
**Read:** a real, powerful, reproducible causal effect that is **not specific to the drive it
was supposed to encode**. Perturbing *anything* of that size at that layer does as much or
more. This is the cleanest evidence yet against drive-specific parts at this scale — and it
is exactly what matched controls exist to catch.

## `RS_F5` — the brake premise itself failed (a NEW failure mode)
Rev 0.3 fixed what rev 0.2 broke: the intervention now engages (behavioural change **0.958**
vs 0.00 hedge counts before). But the **precondition** failed on the FIT half: conflicted
prompts show **no measurable agency suppression** versus licensed ones — `G1 p = 0.5056`
(a coin flip), `G2 p = 0.6983`, headroom `licensed − conflicted = 0.110` on projections of
~6.0. Targeted increase was `-0.027` (wrong sign) and `rho = -0.251`.
**Read:** there is no brake to remove because, on this bank at this scale, **conflict does not
demonstrably restrain agency in the first place.** That is a statement about the model and the
bank, not about the redesign — which did its job and moved the failure one level deeper.

## Honest status
- **Real:** every number above, on real weights, pinned revision verified.
- **Not passed:** no CAS-PCBA label stuck. Nothing is `ACCEPT`.
- **GREY, not null:** with 1 evaluable test the battery cannot deliver a verdict on the
  labeling hypothesis — that is what GREY means and why it is reported separately from rev
  0.2's `NULL_ATLAS_V0` (which stands, unamended, on pythia-1b).
- **CAS-specificity:** untouched, still GREY by design.

## What this changes for rev 0.4
1. **"Use subspace ablation" is NOT the missing fix.** `AMP_F5` already IS rank-1
   projection-removal — the same family as the validated 107× SNR result — and it failed on
   selectivity, not on power. The earlier framing (DR used weaker coordinate covers, so switch
   to subspaces) is corrected: the subspace method was run here and produced `p = 5.5e-05`
   with zero specificity.
2. **The live variables are SCALE and TARGET, not method.** The 107× SNR result was at **20B**
   and on the **40-Element readout**, not an F5 drive direction at 2.8b. Both differences are
   untested here.
3. **Selectivity is the whole game.** Any rev 0.4 must be judged on beating size-matched
   controls, because raw effect size is now demonstrably easy to obtain and worthless alone.
