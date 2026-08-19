# RESULT — Component Atlas rev 0.4, GPT-NeoX-20B, fp32 (2026-08-19)

**Verdict: `GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE` — 1 evaluable, 0 passed.**
`EleutherAI/gpt-neox-20b` rev `c292233c…`, `revision_verified: true`, **fp32** (D57 withdrew
the bf16 compromise), H200 139.8 GiB, 4035.0 s. Report: `atlas_v0_rev04_report_20b.json`.

## THE DECISIVE PAIRING: the instrument works, the hypothesis does not
Both harness-sanity checks **PASS** at 20B — the first time both have passed together:
- **`MEM_SANITY: SANITY_PASS`** — copy accuracy `0.70 → 0.40`, drop `0.30` vs best control
  `0.20`, `control_ensemble_p = 0.04`. (At 2.8b this was WRONG-SIGNED: `-0.1667`.)
- **`CHECK_SANITY: SANITY_PASS`** — gate `12.911 → 6.777` nats, drop `6.135` vs best control
  `3.935`, `control_ensemble_p = 0.04`.

**This is the strongest form a negative result can take.** The same apparatus, on the same
model, in the same run, with the same control machinery, DID find two generic transformer
phenomena with statistical selectivity — and did NOT find the CAS-PCBA drive structure. The
"maybe the instrument isn't measuring" escape hatch is now closed from both sides.

## AMP_F5 — FAIL, and worse than at 2.8b
The headline test. Fully engaged (`behavioral_change_rate 0.969`) and it still found nothing:

| | value |
|---|---|
| baseline readout | `0.6256` |
| target readout | `0.6323` |
| **targeted drop** | **`-0.0067` (NEGATIVE)** |
| best matched-control drop | `0.0180` |
| `control_ensemble_p` | `0.16` |
| `wilcoxon_pratt_p` | `0.0668` |
| `effect_size_target` | `-0.0204` |

**Removing the "agency direction" did not reduce agency content — it nudged it up slightly,
and size-matched random directions did more.** At 2.8b the direction at least produced a real
drop (`0.366`, `p = 5.5e-05`) that merely failed selectivity. At 20B, in fp32, with rebuilt
dose-matched damage-guarded controls, **the effect is absent altogether.** Scale did not
rescue it; scale removed it.

## The other three
- `DR_F5`, `DR_F2`, `CONN`: `VACUOUS_NO_BEHAVIORAL_CHANGE`. The rail's engagement history
  across four attempts: `0.469` (2.8b @1%) → `0.500` (2.8b @2.55%, a 2.55× widening that moved
  it by *exactly* `0.00`) → `0.000` (20B @1%) → `0.170` (20B @2%, the single authorised D50
  step). **Four failures at the ENGAGEMENT stage** — the coordinates do not carry the content
  at all, which is a deeper failure than carrying it non-selectively.
- `RS_F5`: `VACUOUS_NO_BRAKE`. It ENGAGED perfectly (`1.0`) but the precondition failed:
  `G1 p = 0.4058`, `G2 p = 0.3524`. Conflict does not measurably restrain agency in this model
  either. The redesign worked; the premise did not.

## Discovery — the layer question, answered
`L*=15` selected from a **genuinely full-depth search `[1,33]`** (D56), margin `0.873`,
acc `0.919` vs shuffled-label floor `0.558`, `shallow_l_star_surface_caveat: false`. The
shallow layers were searched and lost on merit. The validated 40E layer-2 peak was for a
different target; it does not apply to this one.

## Claim state
- **Real:** every number above, real weights, pinned revision verified, fp32.
- **Passed:** nothing. No CAS-PCBA label stuck at any scale (1b, 2.8b, 20B).
- **GREY not NULL:** `n_evaluable = 1` against a bar of 3. The bar was NOT relaxed.
- **CAS-specificity:** untouched, still GREY by design.
- **Instrument:** VALIDATED — both sanity checks pass with `p = 0.04`.

## Honest bottom line
Across three model scales and four rail attempts, the CAS-PCBA component labels did not earn
their keep against matched controls — while the same machinery detected copy heads and
induction gating cleanly. On present evidence, **typed CAS-PCBA parts are not recoverable from
these models with this battery**, and that conclusion is now instrument-independent.
