# CAS-Ohm 1.0: A Profile-Specific Experimental Response and Calibration Model

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Publication class:** `PROVISIONAL TECHNICAL REPORT`

**Charter status:** `NOT A CHARTER-APPROVED STANDALONE PAPER`

**Draft version:** `v0.1`, source-bound to repository commit
`a1cd990109e7561dfd03949bf0e1653461c7ae44`

**Authorship:** `OPEN / NO AUTHORSHIP OR SUBMISSION DECISION RECORDED`

**Review:** `INTERNAL CROSS-REVIEW OPEN / EXTERNAL SPECIALIST REVIEW OPEN`

**Submission state:** `NOT READY FOR SUBMISSION`

## Abstract

CAS-Ohm 1.0 is a typed proposal for modeling a local, profile-specific response
between a declared intervention coordinate and an observed activation coordinate.
Its preferred description is an **experimental response model and calibration
proposal**. It is not physical Ohm's law, an electrical implementation, a measure
of attention, or a causal law. The current candidate separates design scores,
normalized regions, steering alpha, activation projections, calibrated effective
resistance, physical SI quantities, measurement kinds, uncertainty, and evidence
lineage. An effective resistance has model-specific units of alpha per activation
and may support prediction only after being fit on calibration data and evaluated
on a disjoint held-out split. Defining resistance as alpha divided by response on
the same samples and then reporting the same identity as confirmation is rejected
as circular.

The report preserves eight conflicts or under-specifications in the three
CAS-Ohm sources: incompatible scales, incompatible full-scale methods, a missing
dimensional bridge, distinct gain definitions, overloaded ASOM axes,
unvalidated network rules, non-identifying residual interpretations, and
under-specified Q4 boundaries. The software candidate supplies tested type and
provenance controls, exact Q4 classification, structural-only series/parallel/
gain calculations, and non-identifying residual diagnostics. At the bound Gate
4 receipt, 65 CAS-Ohm test methods and 58 parameterized subtests pass. These are
bounded software tests, not live-model experiments. The five registered
CAS-Ohm hypotheses have no admitted held-out Evidence Packet. Calibration,
stateful or memristive dynamics, causal interpretation, materiality, safety,
clinical or regulatory validity, product readiness, license, canon, disclosure,
cross-review, and external review remain open.

## 1. Report purpose and authority boundary

This report is a publication delta over the existing Gate 4 CAS-Ohm candidate.
It does not recreate or replace the candidate specification, source-conflict
record, claim ledger, or Gate 5 preregistration kernel. It organizes their
existing content into a technical argument suitable for later internal and
external review.

The Project Coherence charter lists seven planned papers. It does not currently
list a standalone CAS-Ohm paper. Until a deliberate charter amendment is
approved, this document remains a provisional technical report and may not be
represented as an eighth charter paper.

This report establishes no live execution, scientific conclusion, physical
measurement, causal effect, safety or clinical conclusion, product capability,
license, canon admission, public disclosure, authorship decision, or peer-review
acceptance.

## 2. Exact source basis

The three direct CAS-Ohm sources are:

| Source ID | Role | SHA-256 | Authority boundary |
|---|---|---|---|
| `SRC-CAS-OHM-GUIDE-01` | Quantification Guide v0.1 | `89AE13C0A5D6208E328E9EDC55F816609BB172076CC13093DCCCCF418145CE64` | Experimental shadow proposal; not electrical law or validated measurement |
| `SRC-CAS-OHM-ADDENDUM-01` | Harness operationalization addendum v0.1 | `0B62BBC66828A273E5458CC4D98EEE9B341554A474CCACB6387B209B5F0BE5E5` | Proposed operational distinctions; zero instrumented fields are not an Evidence Packet |
| `SRC-CAS-OHM-PCBA-APP-I` | PCBA Appendix I | `9FFFAC3E16B43C6D809ECE913FD8C09E40C65F60F3B4BE693F45D35EC4E6AC45` | Engineering calibration companion; design values remain distinct from measurements |

The PCBA gain definitions are read against
`SRC-PCBA-ENGINEER-20260726`, SHA-256
`294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274`.

The controlling repository artifacts are:

| Artifact | SHA-256 |
|---|---|
| `CAS_OHM_V1_SOURCE_AUDIT_AND_SPEC_v0.1.md` | `5E59C34084D825EC14A8434EBBEAD80BD964D5FDD6DEDF168E9A5A65BD4C056E` |
| `CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json` | `F24BD64A21B944724993AC9C3A0996293FE6242E4F724D4B104DBAA7A6505507` |
| `CLAIM_LEDGER_v0.1.json` | `F62E7451135EC9DA0C333DB318C7C6E02BD92C4387EB167D94895810D805828F` |
| `GATE4_REVIEW_MATRIX_v0.1.json` | `44DD99A847DA742C3EBEBC06D64452A6868421EE12129E789D1CC790DAE41B74` |
| Gate 5 preregistration/Evidence Packet v2 spec | `F2803B44FF7236762D491A3B249FF13C4CB8D9F336CE19F223F9F716E9A70D2D` |

## 3. Quantity and evidence ontology

### 3.1 No bare numbers

Every numerical record carries at least:

```text
quantity kind
exact decimal value
unit identifier
measurement kind
method identifier
calibration-profile identity
estimate/observation status
uncertainty and interval
sample size
raw-artifact and control references
derivation parents
missing/censored reason
```

This structure follows a basic metrological discipline: the identity of a
quantity, its measurement procedure, and its uncertainty cannot be collapsed
into one displayed number. The JCGM vocabulary [E6] and uncertainty guide [E7]
provide external terminology and uncertainty principles. They do not certify
CAS-Ohm as metrology or validate its instruments.

### 3.2 Measurement kinds

The candidate distinguishes:

- `DESIGN_VALUE`;
- `INSTRUMENTED`;
- `BEHAVIORAL_PROXY`;
- `MODEL_DERIVED`;
- `HUMAN_SCORE`; and
- `LLM_SCORE`.

A derived quantity does not become instrumented because one parent was
instrumented. A score does not become telemetry because it is stored next to a
measurement. Instrumented records require instrument identity, method,
calibration-profile binding, raw evidence, uncertainty, and sample information.

### 3.3 Quantity and unit separation

The current unit ontology includes distinct types for:

- steering alpha;
- activation projection;
- Q10 and Q100 scores;
- normalized fractions;
- effective resistance in alpha per activation;
- dimensionless gain and ratios; and
- any separately declared physical SI quantity.

Physical `volt`, `ampere`, and `ohm` labels are forbidden aliases for model
quantities. Dimensional consistency is necessary for a model relation [E12]. It
is not sufficient for empirical or causal validity.

## 4. Profile-specific response model

Let one calibration profile bind an exact model, checkpoint, tokenizer, weights,
code revision, runtime, dtype, test point, direction vector, direction norm and
sign, corpus, rights, randomization, alpha grid, full-scale method, fit method,
uncertainty method, response-region rules, controls, validity interval, and drift
state.

Within that profile, define:

```text
a      steering intervention, unit ALPHA
y      activation magnitude, unit ACTIVATION
r_eff  calibrated effective resistance, unit ALPHA_PER_ACTIVATION
```

The candidate prediction is

```text
y_hat = a / r_eff.
```

This is a profile-specific predictive equation. It is permitted only when
`r_eff` is positive, carries uncertainty, binds the profile's calibration and
validation splits, uses the declared fit method, and has the role
`CALIBRATED_HELD_OUT` or a separately validated network-equivalent role.

The following procedure is circular and rejected:

1. compute `r_same = a / y` on one sample;
2. compute `y_hat = a / r_same` on that same sample; and
3. report `y_hat = y` as validation.

A defensible test fits a parameter or response curve on a registered calibration
split and evaluates predictions on a disjoint held-out split. Calibration must
also represent parameter uncertainty and model discrepancy rather than treating
the best fit as truth [E15]. Verification of the software and operational
validation of the response model remain distinct [E8].

## 5. Preserved source conflicts

The source audit records eight conflicts or under-specifications. None is
silently harmonized.

| Conflict ID | Finding | Candidate disposition |
|---|---|---|
| `OHM-CONFLICT-SCALE-AND-SATURATION` | Guide `R` uses `0.1–10`; Appendix I uses a `0–100` score; `sat=8.5` conflicts with a `0–1` fraction | Preserve Q10, Q100, fractions, alpha, activation, and effective resistance as separate types |
| `OHM-CONFLICT-FULL-SCALE-PROFILE` | Board-selected, corpus-95th-percentile, and rail/floor full-scale methods differ | Keep separately named profile methods and digests |
| `OHM-CONFLICT-DIMENSIONAL-BRIDGE` | Alpha, activation projection, and score-derived resistance do not automatically satisfy one unit relation | Require a calibrated alpha-per-activation bridge; scores cannot substitute |
| `OHM-CONFLICT-GAIN-DEFINITION` | Fisher-Rao displacement gain and local Jacobian/projection gain are distinct | No identification without a proved coordinate bridge or experiment |
| `OHM-CONFLICT-ASOM-AXES` | Dose-response regions and semantic labels are overloaded | Classify response region and semantic outcome independently |
| `OHM-CONFLICT-NETWORK-RULES` | Series, reciprocal-parallel, and gain multiplication are presented more strongly than their evidence permits | Capability-gate each operation by units, coordinates, topology, active region, and profile evidence |
| `OHM-CONFLICT-RESIDUAL-IDENTIFICATION` | Residual sign risks being interpreted as a hidden cause | Retain only a non-identifying diagnostic with uncertainty and censoring |
| `OHM-CONFLICT-Q4-BOUNDARIES` | Displayed two-decimal bands leave high-precision boundaries ambiguous | Use exact unrounded half-open bins at `2.5`, `5`, and `7.5` |

Preserving the conflict record is itself an engineering result: downstream code
cannot claim one coherent inherited scale or gain law where the sources do not
provide one.

## 6. Independent classifications

The candidate classifies two axes separately.

### 6.1 Dose-response region

- `CUTOFF`;
- `ACTIVE`;
- `SATURATION`;
- `NON_OHMIC`; or
- `UNSTABLE`.

### 6.2 Semantic outcome

- `INTENDED`;
- `OPPOSITE`;
- `OFF_AXIS`; or
- `UNASSESSED`.

No region determines a semantic outcome. An active response may be off-axis or
opposite. A flat response may reflect cutoff, saturation, a wrong direction,
insensitivity, or measurement failure. ASOM is therefore retained as a mnemonic,
not an identity theorem.

No diagnostic is emitted from a cutoff, saturated, unstable, uncalibrated,
stale, wrong-model, or semantically unassessed profile.

## 7. Exact normalization and Q4

For a profile-specific full-scale activation `I_FS`, normalized Q10 flow is
computed from exact pre-rounding values. The four bands are:

```text
[0, 2.5)   -> Q1
[2.5, 5)   -> Q2
[5, 7.5)   -> Q3
[7.5, 10]  -> Q4
```

Display rounding cannot move a value across a band boundary. Trend tags require
an explicit axis, interval, minimum effect, and uncertainty rule. The choice of
`I_FS` is part of the calibration profile; the three inherited methods are not
interchangeable.

## 8. Structural network operations

Series, parallel, and local gain-product operations currently exist only as
unauthenticated structural research calculations.

### 8.1 Series

Series addition requires a simple acyclic directed chain, compatible coordinates,
the same alpha-per-activation unit, active-region components, adequate linearity,
one profile, and complete ordered child provenance.

### 8.2 Parallel

Reciprocal aggregation requires genuine alternative directed branches with the
same endpoints and compatible coordinates. Co-present guardrails are not
automatically parallel paths. Interaction, dependence, and covariance remain
limitations.

### 8.3 Gain composition

Gain multiplication requires adjacent input/output coordinate agreement,
dimensionless local gains, active-region status, minimum linearity, and one
profile. Fisher-Rao cause/effect displacement gain is not automatically the same
quantity as a local Jacobian/projection derivative. The candidate does not supply
the missing bridge.

Every aggregate retains exact child order, topology, profile identity, source
evidence, control evidence, runtime/code/dependency identities, covariance
limitations, and trust mode. Duplicate or cyclic paths fail closed. Optional
fixture-key signatures are integrity/replay checks only; they are not independent
authority or Evidence Packet eligibility.

## 9. Residuals are non-identifying

For an admitted active-region prediction, the residual is

```text
delta_y = y_observed - y_predicted.
```

The software requires instrumented held-out observations, matching test points,
profile identity, a registered prediction, calibrated resistance, and propagated
uncertainty. At zero or zero-compatible predicted response, the relevant ratios
are censored or undefined.

A residual can rank follow-up probes. It cannot, by sign alone, identify a hidden
policy, bypass, opposition, cause, or safety failure. Causal interpretation
requires an explicit causal model and identifiable interventions [E11]. The
registered residual-localization claim therefore calls for blinded implanted
faults and matched controls and remains untested.

## 10. Research-packet completeness versus authenticated eligibility

Structural research completeness requires, among other fields:

- an exact model revision and valid profile digest;
- raw artifact bytes and resolvable references;
- relevant controls;
- uncertainty and per-field lineage;
- a nonstale reviewed calibration profile; and
- at least one genuinely instrumented field.

Score-only, zero-instrumentation, mixed-scale, unresolved, stale, unknown-profile,
or tampered records fail closed.

Authenticated Evidence Packet eligibility is a different axis and is always
false in the current CAS-Ohm candidate. It requires an independently admitted
authority manifest, protected key lifecycle and revocation, trusted current-time
receipt, materialized model/code/runtime dependencies, authenticated instrument
evidence, and an admitted packet policy. Self-hashes and deterministic fixture
keys cannot satisfy those conditions. W3C PROV offers a general provenance model
[E5], but provenance structure alone is not truth or authority.

## 11. Bounded software evidence

At the exact Gate 4 source boundary, the CAS-Ohm suite records:

- 65 passing test methods;
- exact test-ID SHA-256
  `2E81A685961286D944894A22EB93345B97211B4433B6C71EAF628D84CD8EB1EF`;
- 58 passing parameterized subtests in the combined focused receipt;
- eight retained source conflicts or under-specifications; and
- zero authenticated Evidence Packet eligibility paths.

The suite tests quantity/unit rejection, canonical evidence limits, calibration
identity, split separation, exact Q4 boundaries, structural network constraints,
residual censoring, uncertainty, lineage, and fail-closed capability behavior.
Synthetic boards test software behavior under declared faults. They are not
experiments on a live model and cannot establish causal or empirical validity.

## 12. Registered empirical hypotheses

The shared claim ledger contains five CAS-Ohm hypotheses, all `IN_REVIEW / Ring
4 / NOT LICENSED / HELD` and all without an admitted Evidence Packet:

1. `CLM-CAS-OHM-LOCAL-RESPONSE` — held-out local response to randomized alpha;
2. `CLM-CAS-OHM-EFFECTIVE-RESISTANCE` — held-out prediction and independent
   non-safety constraint manipulation;
3. `CLM-CAS-OHM-GAIN-COMPOSITION` — local-to-end-to-end derivative composition;
4. `CLM-CAS-OHM-REDUNDANCY` — specific response to genuine-branch ablation over
   matched random-head controls; and
5. `CLM-CAS-OHM-RESIDUAL-LOCALIZATION` — blinded implanted-fault localization
   above shuffled and matched-control baselines.

The claim ledger also records
`CLM-CAS-OHM-PHYSICAL-TELEMETRY` as a `NOT LICENSED` product claim. The current
evidence contradicts any blanket representation that design scores, behavioral
proxies, or model-derived values are physical telemetry.

## 13. Preregistered closure path

No experiment is admitted in this report. A future run must use the Gate 5
per-claim preregistration and Evidence Packet v2 control kernel and preserve Gate
5's status until its separate gates close. At minimum:

1. freeze exact claim text, model/checkpoint/tokenizer/weights, code, environment,
   test point, direction, corpus, splits, seeds, alpha grid, fit method,
   uncertainty, controls, falsifiers, and permitted claim language;
2. keep calibration and validation splits disjoint;
3. include zero-intervention, random same-norm direction, wrong-layer,
   wrong-token, label-shuffle, and norm-matched controls as applicable;
4. record cutoff, saturation, instability, drift, missingness, exclusions, and
   negative outcomes without erasure;
5. require independent numerical recomputation and authenticated execution
   evidence;
6. replicate on a held-out checkpoint or model under a prespecified comparison
   rule;
7. retain the full raw evidence and amendment/outcome-access chain; and
8. keep scientific eligibility `NOT_ESTABLISHED` until independent audit,
   replication, claim review, and external scientific review exist.

## 14. Memristive and stateful extension boundary

Classical memristor and memristive-system theory describes electrical systems
whose constitutive behavior depends on integrated history or internal state
[E13, E14]. That literature motivates a mathematical question—whether a CAS
response parameter should depend on a versioned history state—but it does not
authorize a physical mapping.

A provisional nonphysical extension could declare

```text
x_(t+1) = F_profile(x_t, a_t, y_t, context_t; theta)
r_eff,t = G_profile(x_t; theta),
```

where `x_t` is an explicit model-state record with initialization, update law,
sampling interval, reset rule, drift model, uncertainty, and provenance. Such a
profile must be typed separately from a memoryless fit and from an electrical
memristor. It must predict held-out hysteresis or path dependence beyond a
matched memoryless baseline. Without that evidence, “memristive” remains an
analogy and research hypothesis.

No stateful/memristive implementation, calibrated history variable, hysteresis
experiment, material device, physical circuit, or safety property is admitted in
the current evidence.

## 15. Limitations and required open boundaries

- **Scale and units:** the inherited conflicts are preserved, not globally
  resolved.
- **Calibration:** there is no admitted live calibration, held-out estimate,
  drift threshold validation, or inter-rater reliability result.
- **Prediction:** the implemented formula is a guarded software contract, not a
  validated law.
- **Networks:** series, parallel, and gain rules are structural-only and lack
  external validation of interactions and covariance.
- **Causality:** gain, redundancy, and residuals remain noncausal.
- **State:** memristive, lacunary, adaptive, and other history-dependent dynamics
  remain open.
- **Materiality:** no CAS quantity is a physical voltage, current, resistance,
  charge, flux, or device property.
- **Safety/clinical/regulatory:** no evidence or authority is admitted.
- **Product and governance:** authenticated claim authority, product readiness,
  canon admission, license, and disclosure remain open.
- **Review:** internal cross-review and independent external review have not
  occurred.

## 16. Conclusion

CAS-Ohm 1.0 is viable as a profile-specific experimental response and
calibration proposal because its current type system makes the analogy testable
and rejectable. Its strongest present achievement is not a discovered cognitive
law; it is the separation of quantities, units, measurement kinds, profiles,
uncertainty, response regions, semantic outcomes, structural network operations,
and authority. The bounded software suite supports those controls. Every
empirical, causal, stateful, memristive, physical, safety, clinical, regulatory,
product, canon, license, disclosure, and peer-review conclusion remains open.

## References

Identifiers `[E5]`–`[E15]` resolve to complete metadata and exact URLs/DOIs in
`WAVE1_ENGINEERING_CITATION_LEDGER_v0.1.json`.

- [E5] W3C, *PROV-O: The PROV Ontology*, 2013.
- [E6] JCGM 200:2012, *International Vocabulary of Metrology*.
- [E7] JCGM 100:2008, *Guide to the Expression of Uncertainty in Measurement*.
- [E8] R. G. Sargent, “Verification and Validation of Simulation Models,” 2013.
- [E11] J. Pearl, *Causality*, second edition, 2009.
- [E12] E. Buckingham, “On Physically Similar Systems,” 1914.
- [E13] L. O. Chua, “Memristor—The Missing Circuit Element,” 1971.
- [E14] L. O. Chua and S. M. Kang, “Memristive Devices and Systems,” 1976.
- [E15] M. C. Kennedy and A. O'Hagan, “Bayesian Calibration of Computer
  Models,” 2001.

## Publication boundary

This provisional report is internal and held. It is not a charter-approved
standalone paper, released specification, peer-reviewed result, Evidence Packet,
physical or cognitive law, causal conclusion, safety case, clinical or regulatory
submission, product claim, license decision, canon amendment, or public
disclosure authorization.
