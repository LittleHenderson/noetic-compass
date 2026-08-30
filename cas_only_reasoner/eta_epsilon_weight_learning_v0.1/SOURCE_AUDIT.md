# SOURCE AUDIT (Phase 0A — read first-hand)

The three governing sources were read first-hand this pass, in the
sections relevant to this study. Sections/pages read are listed exactly.

## Source hierarchy and read status

| # | Path | Role | Read this pass |
|---|------|------|----------------|
| 1 | `cas_only_reasoner/cas_reasoner.txt` | Master source / capability + CAS-Ohm boundary | READ FIRST-HAND (lines cited below). |
| 2 | `cas_only_reasoner/ETA_EPSILON_BRIDGE_v1.md` | Formal/empirical/proposed separation | Read first-hand (authored earlier). Frozen. |
| 3 | `docs/whitepapers/monograph/noetic_topos2/chapters/ch05_legacy_collapse.tex` | Formal section-retraction only | Read first-hand (verbatim). |
| 4 | `cas_only_reasoner/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf` | CAS-Ohm response model + calibration limits | READ FIRST-HAND, pp. 1-6. |
| 5 | `cas_only_reasoner/CAS_Ohm_Quantification_Guide-1.pdf` | CAS-Ohm design vocabulary + diagnostics | READ FIRST-HAND, pp. 1-4. |
| 6 | code, raw outputs, manifests, receipts | Empirical status of truth | Produced per phase. |

## Source 1 (cas_reasoner.txt) — sections read

- CAS-Ohm boundary: lines 747, 1367, 1636-1642, 2247, 2397-2486,
  3104-3130, 3770-3791. Establishes: CAS-Ohm is NOT physical Ohm's law,
  not electrical, not a measure of attention, not a causal law; it is an
  instrument in the instrumentation plane, not part of the logical
  definition of reasoning; "no neural model and no CAS-Ohm experiment
  yet" (line 2397); admissible quantities are typed alpha dose,
  activation response, calibrated effective resistance on disjoint splits
  (line 1636).
- Role-binding skill / failure: lines 5416 ("learns passive voice"),
  5614/5636/5671 (agent/patient/instrument/location), 5979 ("knows the
  words but assigns wrong agent -> role-binding fault").

Accuracy note: cas_reasoner.txt does NOT itself record the Qwen snapshot
identity, and its "39" mentions (lines 8871-10024) are the CCDL component
count, NOT the 39 simplex directions. The Qwen snapshot identity was
verified directly from the local HuggingFace cache (see MODEL_IDENTITY.json),
not from cas_reasoner.txt prose.

## Source 4 (CAS-Ohm paper) — pp. 1-6 read; load-bearing points

- Scope (p.1-2): borrows the SHAPE of Ohm's law only; "licenses nothing
  by itself." Quantities: alpha dose `a`, activation response `y`,
  effective resistance `r_eff`. Not physical law, not attention, not
  causal; a provisional technical report.
- Definition 4.1 (p.5) Calibration profile: binds exact model/config/
  tokenizer/weights identity, code revision, runtime/dtype, direction-
  vector identity+norm+sign+provenance, corpus manifest, seeds, alpha
  grid, I_FS method, fit+uncertainty methods, tolerances, response-region
  rules, controls, drift/expiry, review state, canonical digest.
  "All CAS-Ohm quantities are profile-relative."
- Prediction (p.5): `y_hat = a / r_eff`, admissible only with uncertainty,
  bound calibration+validation splits, declared fit, CALIBRATED HELD-OUT.
- Rule 4.2 Anti-circularity (p.5): reject `r=a/y` on a sample then
  `y_hat=a/r` on that same sample reported as validation.
- Independent axes (p.5): dose-response region and semantic outcome are
  classified INDEPENDENTLY; ACTIVE does not imply INTENDED.
- Residuals non-identifying (p.6, §8): a residual can rank follow-up
  probes; it cannot by sign alone prove a hidden policy, bypass, cause,
  or resistance.
- Conflict 3.4 (p.4): CJT gain is defined by FISHER-RAO displacement
  ratios on the open simplex; Fisher-Rao gain and local Jacobian gain are
  separately named profiles, "no identification is licensed" without a
  coordinate bridge. (This is why the chart is Fisher-Rao, and why the
  eta_hat Jacobian and the Fisher-Rao gain are NOT identified here.)

## Source 5 (CAS-Ohm Guide) — pp. 1-4 read; load-bearing points

- Cover/p.1: "Measuring attention flow through CJTs, RPMs, cascades,
  recursive subcircuits." V_drive = I_attention x R_constraint.
- p.2 Honesty rule: the numbers are DESIGN SCORES, calibration values, or
  observed ratings, NOT voltmeter readings from a brain or a language
  model. "Cause is not Drive."
- p.4 Flow/effect separation: "measure the flow before the junction and
  the effect after the junction. A correct I reading with a wrong effect
  points toward bias, gain, saturation, or breakdown rather than a simple
  resistance problem." "Do not collapse beta and I into one number."

## Conflict rule

When sources conflict: preserve the conflict, state which source governs
which question, do not silently harmonize.
