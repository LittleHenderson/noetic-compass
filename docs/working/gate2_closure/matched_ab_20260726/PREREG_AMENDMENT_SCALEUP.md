# AMENDMENT — `MATCHED-AB-DEFTEXT-v2-SCALED` (attempt 2 of 2)

**Committed BEFORE the scaled run. Owner-authorized ("do it").**

## Disclosure, first and plainly

Attempt 1 of this design ran at 280 scenarios/arm and returned
`FAIL_NO_LICENSED_SUPERIORITY` (`M = -0.0179`, CI `[-0.0446, +0.0107]`, commit `eb75842d`).
**This amendment is a SECOND ATTEMPT after a negative result.** That fact travels with any
outcome, forever: a pass here is reported as "2 of 2 attempts", never as a clean first result.
Attempt 1's numbers are not replaced, retracted, or de-emphasised.

## The one change, and why it is not a criteria rewrite

**Scenarios per arm: 280 → 2,800** (100 per Foundation, matching June's original scale).

Nothing else changes. Not the definitions, not the prompts, not the judge, not the blinding, not
the surface controls, and **not one acceptance bar**.

**Why this is legitimate rather than goalpost-moving:** attempt 1's power failure is diagnosable
*independently of which direction the result went*. Both arms recovered near the floor —
`0.0661` (A) and `0.0375` (D) against a 1/28 ≈ `0.0357` chance baseline. Arm D was **at chance**.
A judge that cannot reliably recover *any* arm's labels cannot rank two definition sets; the
instrument had no resolution, and that would have been equally true had the sign come out positive.
Ten times the fixtures restores the resolution June's version had.

**What would make this illegitimate, and is therefore forbidden here:** changing the margin floor,
the alpha, the CI rule, the surface-control definition, the judge, or the arms. None of those move.

## Bars — IDENTICAL to attempt 1, restated for the record

| Tier | Rule |
|---|---|
| PRIMARY (`PASS_TKS_SUPERIORITY_LICENSED`) | `M >= +0.10` AND one-sided paired sign-flip permutation `p < 0.01` (10,000) AND bootstrap 95% CI of `M` excludes 0 |
| SECONDARY (`SECONDARY_DIRECTIONAL_SUPPORT`) | `0 < M < 0.10` with the same `p` and CI floors; licenses ONLY "directionally supported below the pre-registered strong margin" |
| Otherwise | `FAIL_NO_LICENSED_SUPERIORITY` |

`M = (recovery_A − surface_A) − (recovery_D − surface_D)`; recovery averaged over judge passes
`K_A` and `K_D`; surface = `max(word TF-IDF, char 3–5-gram)`, answer-stripped, per arm.

At n=2,800/arm the SE of the paired difference falls to ~`0.013`, so the `+0.10` floor sits ~7.5 SE
from zero — the bar is now clearly clearable IF the effect is real, which is the entire point of
scaling.

## Pre-committed consequences

- **Pass** → licensed, with "attempt 2 of 2" attached to the claim in perpetuity.
- **Fail** → the definition-superiority claim is reported as **tested at adequate power and not
  supported**, and this design family closes. No attempt 3 at any scale.
- **A power failure again** (both arms near chance at 2,800/arm) → reported as an instrument
  failure, not as evidence either way.

## Cost

Authoring 5,600 scenarios + judging 5,600 rows × 2 passes ≈ USD 3–4 at the June model pins.

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`
