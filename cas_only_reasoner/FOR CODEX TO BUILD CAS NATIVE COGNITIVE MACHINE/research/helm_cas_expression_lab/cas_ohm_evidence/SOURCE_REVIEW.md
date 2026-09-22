# CAS-Ohm source review — 2026-09-21

The reviewed sources support three calculations: `I=V/R`, `V=IR`, and
`R=V/I`. They do **not** supply one agreed universal scale, calibration,
measurement procedure, or neural control law. Version
`cas.ohm.declared-linear/0.1` therefore uses an explicit caller-declared
coherent ratio scale. It is a calculation convention, not a new canonical
calibration or a claim that a running model was measured.

This review read local sources and ran isolated, small arithmetic checks.
External sources were read only. Document statements about owner rulings,
adoption, or evidence status are reported as document claims, not independently
authenticated approvals. No neural model, training, controller, or cloud service
was run.

## Source identity and authority

Paths below are relative to
`C:/Users/wakil/OneDrive/Desktop/tksCAS/`. Hashes are SHA-256 of **raw
bytes**, except where an additional LF-normalized hash is expressly supplied.

| ID | Source / status | SHA-256 |
|---|---|---|
| BOOK-5 | `book/CAS_PCBA_Engineer/Chapter_05_Resistors.md`; current core book chapter | `105ef2f963bcf679ae4b96724505e4512f553a127afb63da7e95f2ba998e28b1` |
| BOOK-I | `book/CAS_PCBA_Engineer/Appendix_I_CAS_Ohm_Measurement_and_Calibration.md`; current book appendix | `5be5667eb9b37460a7b7c2f9c21ca664582445f54136c0cb0a87cec6dd98de60` |
| GUIDE | `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_Ohm_Quantification_Guide-2.pdf`; 18-page Working Draft v0.1, July 2026 | `89ae13c0a5d6208e328e9edc55f816609bb172076cc13093dccccf418145ce64` |
| ADDENDUM | Same directory as GUIDE, `CAS_Ohm_Harness_Operationalization_Addendum_v0_1.docx`; proposed Draft v0.1, July 16, 2026 | `0b62bbc66828a273e5458cc4d98eee9b341554a474ccacb6387b209b5f0be5e5` |
| GRIMOIRE | `book/cognitive-circuit-grimoire/manuscript/ch04_cas_ohms_law.md`; separate manuscript with additional design conventions | `694b25834c5b46d1c806a040b6d0b54f0229ea74c576831a19293dab5ff905f6` |
| PAPER | `docs/whitepapers/WHITEPAPER_CAS_OHM_1_0_v0.1.md`; explicitly DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD | `738680f7db4fe686d7e6fef13b4461fe01902154be305623a5592a376001125b` |
| PROTOCOL | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/spec/CAS_OHM_ATTENTION_INTEGRATION_PROTOCOL_v0.1.md`; marked adopted design direction / follow-on contract / not runtime-integrated | `5e693819466d05de3e29783ff464dd28882682a0d40eca0ee4ccdbad086ecbca` |
| AUDIT | `docs/whitepapers/monograph/cas_ohm1/chapters/ch04_conflicts.tex`; source-conflict audit, not a resolution of the conflicts | `1e43afb7c18e39fddb70cd871117a721a920ef37e2c1fabafa66cdfd48dff1d8` |

BOOK-5 LF-normalized hash:
`b670feae016f0eff43d771922ae1110ea22192fd14d93d93f9e2218e8ef6c1fd`.
BOOK-I LF-normalized hash:
`0f3d9add1ecc3c2d238739d7435908f45bf24402285bf04fef83ddd875583fcf`.
The historical AUDIT cites a different Appendix I digest; its original line
locators must not be silently reassigned to today's updated manuscript.
Guide locators below are PDF page numbers. Addendum paragraph/table indices
are zero-based structural indices from python-docx; no pagination is claimed.

## What the sources actually define

| Source location | Rule and boundary |
|---|---|
| BOOK-5:29–57 | Three algebraic rearrangements; Drive is potential, attention is flow, constraint opposes flow. The chapter's numbers are design choices. A CAS state/Drive tag supplies no numeric magnitude. |
| BOOK-5:83–93,233 | Dial is integer 3–9, with hard rejection and involution-pair difference at most 4. Resistor design range is 0–100 constraint units. Dial and resistance are distinct. |
| BOOK-I:27–31 | R: 0–100; activation/sat/cutoff: 0–1; gain unbounded, typically 0.5–5; Dial: integer 3–9; supply rails: 3.3–12 in the electrical analogy. These are different quantity families. |
| BOOK-I:44–49,95–108 | `I_Q=min(10,10*I_raw/I_FS)`; full scale is per path at rail Drive/floor constraint. The three requested operations are explicit. |
| GUIDE:2–6 | Separates inherited definitions from working extensions. Its design profile is V: 0–10, R: 0.1–10, raw I: 0–100. Never R=0. Full scale is chosen for a board; retain raw I and overload `lambda=I_raw/I_FS`. |
| BOOK-I:121–141; GUIDE:8 | `R_total=R_cap+R_policy+R_context+R_resource`; `R_cap=R_min+(R_max-R_min)*(1-P_cap/10)`. Capability inversion and D/W/P crosswalk are distinct from the core quotient. |
| BOOK-I:178–201; GUIDE:16 | `delta_I=I_obs-I_pred`, `R_hidden=V/I_obs-R_known`. Guide requires effect/operating-point checks. Its small denominator floor is for relative-error reporting, not an epsilon added to V/R or V/I. |
| BOOK-I:214–256; GUIDE:13–14 | Series resistance sums; true parallel routes combine reciprocally; stage flow stays local. Parent views retain child readings. Co-present guardrails are not automatically parallel routes. |
| GUIDE:12 | `E*=beta*I` is a working effect proxy, expressly not a canonical Ohm identity. Its sat=8.5 example uses a different scale from BOOK-I's 0–1 thresholds. |
| BOOK-I:260–364 | Fisher–Rao displacement gain and Jacobian/projection gain are distinct. No proved coordinate/metric/normalization bridge is supplied; measured gain products cannot be justified solely by the design-sizing rule. |
| BOOK-I:436–449 | Design scores, calibration values, and observed ratings are not neural voltmeter readings. The claimed relation has not been measured against a live model. |

One source inconsistency must remain visible: BOOK-I:53–55 calls a component
`R=2.0` a range error, but its own 0–100 table includes 2.0. It cannot justify
rejecting that number without a separately identified scale.

## Explicit extensions are not interchangeable

- **ADDENDUM**, paragraphs 24–35 and table 0 row 13: proposes a neural profile
  whose full scale is the 95th percentile of absolute activation projection on
  a fixed corpus. Table 0 maps Drive to steering alpha and flow to a projection.
  Paragraph 38 calls linearity a hypothesis. These quantities do not acquire
  meaning merely by changing the units on a design score.
- **GRIMOIRE:67–95,140–182,352–365**: adds V_c: 0–30, single-drive dials 3–9,
  I_max=1.00, R: 0–100/design 10–90, and domain forward drops:
  `I=(V-sum(Vf))/R`, `V=IR+sum(Vf)`, `R=(V-sum(Vf))/I`.
  Its examples use P→O drop 3.9 and C→O drop 3.2, with dropout and clipping.
  Those conventions must not silently alter the requested 12/4=3 example.
- **PAPER:73–91,146–190** preserves eight conflicts: scales/saturation,
  full-scale method, dimensional bridge, gain definition, ASOM meanings,
  network validation, residual identification, and quantization boundaries.
  Its exact half-open Q4 bins and calibrated neural response model are
  explicitly proposed extensions. Residual sign alone identifies no cause.
- **PROTOCOL:96–193,416–443,546–564,597–615** requires typed quantities,
  exact arithmetic, explicit topology/units, and positive native total
  resistance. A native rule is exact because a runtime defines it, not because
  it proves a law of thought. It separates native/neural/human substrates,
  keeps diagnostics non-identifying, and explicitly records missing runtime
  integration. Its roadmap is not evidence that those integrations exist.

## Existing software examined before choosing the boundary

1. **Historical CCB-R1 simulator.** Recovered from the main repository's Git:
   `git show f436e42476ca0127581d6085c3a22056bd509e73:scripts/ccb_r1/cjt_sim.py`.
   SHA-256:
   `073af9f068ed96fb479a18296d14ccc480b8129f15cbb23b23e80a87e6f5975e`.
   The retained read-only copy is
   `../pinned_sources/cas_ohm_references/historical_ccb_r1_cjt_sim.py.txt`.
   The path is absent from the current main filesystem and WORK base 4345aa36;
   WORK and main have different Git histories. That local absence did not mean
   the implementation never existed.
   It provides flow, series/parallel resistance, cascade gain, and region
   simulation. Small independent checks reproduced:
   `measure(valid_spec, NaN, 2)` reports ACTIVE with NaN flow; and
   `CjtSpec(..., sat=8.5, scale="unit")` bypasses the enum-identity unit range
   guard. Useful reference behavior, but unsuitable for wholesale reuse.

2. **Current quantifiers.**
   `noetic-compass-scaffold/noetic-compass/api/cas_ohm/quantifiers.py`,
   SHA-256:
   `0a486d0658ecef8b0039b15a8dc2e259637fffb98b677211c6c6fe91559ae9a4`.
   The header declares a proposed, unvalidated profile-specific instrument.
   Lines 278–296 implement a neural response quotient; this is a different
   contract from a caller-declared generic ratio.
   Isolated checks reproduced `i_pred(True,True)=1.0`,
   `i_pred(12,NaN)=NaN`, `i_pred(infinity,4)=infinity`, and
   `i_pred(-12,4)=-3.0`; import also changed Decimal precision 28→50.
   Negative intervention dose may belong to its own neural profile, but these
   behaviors do not satisfy the new nonnegative finite-input contract.
   This module was not imported into the new helper.

3. **Current Cortex control module.**
   `cas_only_reasoner/CAS_CORTEX_v0.1/cortex/ohm_control.py`, SHA-256:
   `342da4652598cc84fbf4e70a4c22d925f7e66fcd05c400e107c3a43d8055152e`.
   The source declares a native language-pipeline profile and three equations
   at lines 86–99: measure_i, design_v, and diagnose_r. These return floats
   rounded to four decimal places. Isolated checks found negative/NaN values
   propagate and a zero denominator raises raw ZeroDivisionError. The name
   measure_i still performs a quotient; that call does not itself collect a
   measurement. This related implementation exists today, but its broader
   control profile and arithmetic boundary are not the compiler contract.
   Its source snapshot is retained alongside the historical simulator.

These probes establish software behavior only. Historical passing tests and
source comments cannot establish calibration, live measurement, or correctness
outside their covered inputs.

## Why declared-coherent-linear v1 is a narrow, supportable choice

The caller supplies the complete scale descriptor and each input's reference
and origin. Constraint units are explicitly Drive-units/attention-units;
matching an ID alone is insufficient. No universal range, full-scale value,
CJT threshold, gain, domain drop, or conversion is inferred.

All three operations use exact rational arithmetic within declared budgets.
Division by zero, including 0/0, is refused without an epsilon. Required Drive
may contain a zero factor as an explicitly noted algebraic degeneracy; this
does not claim conformance to GUIDE's positive-resistance profile. Float
inputs disclose their conversion route; exact decimal inputs preserve their
literal. Outputs remain calculated, even when their parents are caller-supplied
observations. A supplied reference is not authenticated sensor evidence.

Independent numeric review reproduced and then verified fixes for ambient
Decimal-context dependence, forged direct quantity provenance, and host
integer-string limits. Connection review likewise verified fixes for large
integer lineage replay and pre-serialization JSON key/text bounds. These are
implementation checks, not validation of a physical or cognitive law.

The prepared PCBA connection calculates one explicitly selected resistor;
it infers no total or wiring. Synthetic examples separate compiler-calculated
targets from inputs and learned predictions. The RPA projection retains
declared parent/child values without fabricating aggregates or runtime records.
Measurement, calibration, automatic control, Helm learning, and semantic
correctness remain separate, unproven integrations.
