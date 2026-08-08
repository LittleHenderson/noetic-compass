# CAS-Ohm 1.0: A Profile-Specific Experimental Response and Calibration Model

**White paper, version 0.1 — 2026-08-07**

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Preferred description:** profile-specific experimental response model and
calibration proposal.

**Source basis:**
- `CAS_OHM_V1_SOURCE_AUDIT_AND_SPEC_v0.1.md` (SHA-256
  `5E59C34084D825EC14A8434EBBEAD80BD964D5FDD6DEDF168E9A5A65BD4C056E`)
- `CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json` (SHA-256
  `F24BD64A21B944724993AC9C3A0996293FE6242E4F724D4B104DBAA7A6505507`)
- Direct sources: Quantification Guide v0.1 (`SRC-CAS-OHM-GUIDE-01`), Harness
  operationalization addendum v0.1 (`SRC-CAS-OHM-ADDENDUM-01`), PCBA Appendix I
  (`SRC-CAS-OHM-PCBA-APP-I`)
- Publication delta: `CAS_OHM_1_PROVISIONAL_TECHNICAL_REPORT_v0.1.md`
  (base commit `a1cd990109e7561dfd03949bf0e1653461c7ae44`)
- Implementation: `src/cas_ohm_v1/` (model, calibration, evidence, records,
  networks, diagnostics, synthetic, canonical)

**Authorship / review:** `OPEN / NOT A CHARTER-APPROVED STANDALONE PAPER /
INTERNAL CROSS-REVIEW OPEN / EXTERNAL REVIEW OPEN`

---

## Abstract

CAS-Ohm 1.0 is a typed proposal for modeling a local, profile-specific
response between a declared intervention coordinate (steering alpha) and an
observed activation coordinate (activation projection) in a neural system
under audit. It is *not* physical Ohm's law, an electrical implementation, a
measure of attention, or a causal law. Its candidate prediction,
`y_hat = a / r_eff`, is admissible only when the effective resistance `r_eff`
carries model-specific units of alpha per activation, was fit on a registered
calibration split, carries uncertainty, and is evaluated on a disjoint
held-out split; defining resistance as alpha over response on the same samples
and reporting the identity as confirmation is rejected as circular.

The contribution is threefold. First, a quantity-and-evidence ontology in
which every numeric value is typed evidence — quantity kind, exact decimal,
unit, measurement kind, method, calibration-profile digest, uncertainty,
lineage, and censoring status — and physical volt/amp/ohm labels are forbidden
aliases for model quantities. Second, a source audit that preserves eight
conflicts or under-specifications across the three CAS-Ohm sources
(incompatible scales, incompatible full-scale methods, a missing dimensional
bridge, distinct gain definitions, overloaded ASOM axes, unvalidated network
rules, non-identifying residuals, under-specified quantization boundaries)
rather than harmonizing them silently. Third, a fail-closed software candidate
implementing exact Q4 classification, structural-only series/parallel/gain
network calculations, non-identifying residual diagnostics, and a strict
separation between structural research-packet completeness and authenticated
Evidence Packet eligibility — the latter always false in this candidate. At
the bound Gate 4 receipt, 65 CAS-Ohm test methods and 58 parameterized
subtests pass; these are bounded software tests, not live-model experiments.
Five registered empirical hypotheses await preregistered closure through the
Gate 5 control kernel.

---

## 1. Scope and authority boundary

CAS-Ohm borrows the *shape* of Ohm's law — a dose coordinate, a response
coordinate, and a fitted proportionality parameter — as an experimental
hypothesis about local linear response regions in steered model activations.
The borrowed shape licenses nothing by itself: dimensional consistency is
necessary for a model relation [E12] but not sufficient for empirical or
causal validity. This report establishes no live execution, scientific
conclusion, physical measurement, causal effect, safety or clinical
conclusion, product capability, license, canon admission, or disclosure.

## 2. Preserved source conflicts

The audit records eight conflicts across the Guide, the operationalization
addendum, and PCBA Appendix I; none is silently harmonized.

| Conflict | Finding | Disposition |
|---|---|---|
| Scale and saturation | Guide `R` range `0.1–10` vs Appendix I dimensionless `0–100` score; `sat=8.5` vs a `0–1` region fraction | Q10, Q100, fractions, alpha, activation, and effective resistance kept as separate types |
| Full-scale profile | Board-selected, per-path rail/floor, and corpus 95th-percentile methods differ | Separate named profile methods with digests |
| Dimensional bridge | `I_pred = V/R_total` invalid until resistance has calibrated `alpha_unit / activation_unit` | Require a calibrated bridge; scores cannot substitute |
| Gain definition | Fisher-Rao cause/effect gain vs local Jacobian/projection gain | No identification without a proved coordinate bridge or experiment |
| ASOM axes | Dose-response region and semantic correctness overloaded | Classified independently (§4) |
| Network rules | Series/parallel/gain presented more strongly than evidence permits | Capability-gated structural calculations only (§6) |
| Residual identification | Residual sign read as hidden policy/bypass/cause | Non-identifying diagnostic with uncertainty and censoring (§7) |
| Q4 boundaries | Two-decimal display bands ambiguous at high precision | Exact half-open bins at 2.5, 5, 7.5 (§5) |

Preserving this record is itself an engineering result: downstream code cannot
claim one coherent inherited scale or gain law where the sources do not
provide one.

## 3. Quantity and evidence ontology

Every numeric value is typed evidence, never a bare binary float:

```text
ObservedValue {
  quantity_kind, exact_decimal_value, unit_id,
  measurement_kind, method_id, calibration_profile_sha256,
  estimate_or_observation, uncertainty, confidence_interval,
  sample_size, raw_artifact_refs, control_refs,
  derivation_parents, missing_or_censored_reason
}
```

Measurement kinds — `DESIGN_VALUE`, `INSTRUMENTED`, `BEHAVIORAL_PROXY`,
`MODEL_DERIVED`, `HUMAN_SCORE`, `LLM_SCORE` — are not fungible: a derived
value does not become instrumented because one parent was, and a score does
not become telemetry because it is stored next to a measurement. The unit
ontology separates constraint score, normalized fraction, alpha dose,
activation projection, effective resistance, and real physical SI units;
physical volt/amp/ohm labels are forbidden aliases. This follows basic
metrological discipline (JCGM vocabulary [E6]; uncertainty guide [E7]) without
claiming that CAS-Ohm *is* metrology.

Canonical evidence is exact-type tagged, cycle-aware, unsafe-Unicode
rejecting, and bounded by declared depth, node, container, text, output, and
2,048-bit integer limits; host-runtime conversion failures normalize to the
candidate's validation error rather than leaking platform exceptions.

## 4. Calibration and independent classifications

A calibration profile binds exact model/config/tokenizer/weights and code
identities; runtime and dtype; test-point and direction-vector identity, norm,
and sign; corpus manifest and rights; seeds; alpha grid; full-scale method;
fit and uncertainty methods; tolerances; response-region rules; controls;
drift/expiry; review state; and a canonical digest. Effective resistance is
estimated on calibration data and must predict held-out response; calibration
must represent parameter uncertainty and model discrepancy rather than
treating the best fit as truth [E15]. Verification of the software and
operational validation of the response model remain distinct activities [E8].

Two axes are classified independently:

- **Dose-response region:** `CUTOFF`, `ACTIVE`, `SATURATION`, `NON_OHMIC`, or
  `UNSTABLE`.
- **Semantic outcome:** `INTENDED`, `OPPOSITE`, `OFF_AXIS`, or `UNASSESSED`.

No region mechanically determines an outcome — an active response may be
off-axis or opposite; a flat response may be cutoff, saturation, a wrong
direction, insensitivity, or measurement failure. ASOM is retained as a
mnemonic, not an identity theorem. No diagnosis is emitted from a cutoff,
saturated, unstable, uncalibrated, stale, or wrong-model profile.

## 5. Exact normalization and Q4 quantization

For profile-specific full-scale activation `I_FS`, the classifier computes the
exact pre-clipping value `exact_q10 = 10 · raw / I_FS`, retains
`overload_ratio = raw / I_FS` separately, and clips only the displayed `q10`.
Exact-input bands use half-open bins:

```text
[0, 2.5) -> Q1     [2.5, 5) -> Q2     [5, 7.5) -> Q3     [7.5, ∞) -> Q4
```

Display rounding cannot move a value across a band boundary. Trend tags
require an explicit axis, interval, minimum effect, and uncertainty rule. The
choice of `I_FS` is part of the calibration profile; the three inherited
full-scale methods are not interchangeable.

## 6. Structural network operations

Series addition, reciprocal parallel aggregation, and gain-product composition
exist only as unauthenticated structural research calculations, each
capability-gated: series requires a simple acyclic chain, compatible
coordinates, one unit, active-region components, adequate linearity, one
profile, and complete ordered child provenance; parallel requires genuine
alternative directed branches with shared endpoints (co-present guardrails are
not automatically parallel paths); gain composition requires adjacent
coordinate agreement, dimensionless local gains, and active-region status —
and Fisher-Rao displacement gain is not automatically the local
Jacobian/projection derivative. Every aggregate binds exact child order,
topology, profile identity, evidence, runtime/code/dependency identities,
covariance limitations, and trust mode; duplicate or cyclic paths fail closed.
Optional Ed25519 fixture-key attestations are integrity/replay checks only —
never independent reviewer, legal, product, or Evidence Packet authority.

## 7. Residuals are non-identifying

For an admitted active-region prediction, `delta_y = y_observed −
y_predicted` requires instrumented held-out observations, matching test
points, profile identity, a registered prediction, calibrated resistance, and
propagated uncertainty; at zero or zero-compatible predicted response the
relevant ratios are censored or undefined. A residual can rank follow-up
probes. It cannot, by sign alone, identify a hidden policy, bypass,
opposition, cause, or safety failure — causal interpretation requires an
explicit causal model and identifiable interventions [E11]. The registered
residual-localization claim therefore calls for blinded implanted faults with
matched controls and remains untested.

## 8. Research-packet completeness versus authenticated eligibility

Structural research-packet completeness requires an exact model revision,
valid profile digest, raw artifact bytes, relevant controls, uncertainty,
per-field lineage, a nonstale reviewed calibration profile, and at least one
genuinely instrumented field; score-only, zero-instrumentation, mixed-scale,
unknown-profile, or tampered records fail closed. Authenticated Evidence
Packet eligibility is a separate axis and is *always false* in this candidate:
it requires an independently admitted authority manifest, protected key
lifecycle and revocation, trusted current-time receipt, materialized
model/code/runtime dependency identities, authenticated instrument evidence,
and a reviewed packet policy. Deterministic in-repository fixture keys and
caller-supplied replay time never satisfy those conditions.

## 9. Bounded software evidence and registered hypotheses

At the bound Gate 4 receipt the CAS-Ohm suite records 65 passing test methods
(test-ID SHA-256
`2E81A685961286D944894A22EB93345B97211B4433B6C71EAF628D84CD8EB1EF`), 58
passing parameterized subtests, eight retained source conflicts, and zero
authenticated Evidence Packet eligibility paths. The suite exercises
quantity/unit rejection, canonical evidence limits, calibration identity,
split separation, exact Q4 boundaries, structural network constraints,
residual censoring, uncertainty, lineage, and fail-closed capability behavior.
Synthetic known-fault boards (linear, cutoff, saturation, nonlinear, parallel,
confounded, bypass) validate software behavior only.

Five registered hypotheses, all `IN_REVIEW / Ring 4 / NOT LICENSED / HELD`
with no admitted Evidence Packet:

1. `CLM-CAS-OHM-LOCAL-RESPONSE` — held-out local response to randomized alpha;
2. `CLM-CAS-OHM-EFFECTIVE-RESISTANCE` — held-out prediction plus independent
   constraint manipulation;
3. `CLM-CAS-OHM-GAIN-COMPOSITION` — local-to-end-to-end derivative
   composition;
4. `CLM-CAS-OHM-REDUNDANCY` — genuine-branch ablation over matched random-head
   controls;
5. `CLM-CAS-OHM-RESIDUAL-LOCALIZATION` — blinded implanted-fault localization
   above shuffled and matched-control baselines.

`CLM-CAS-OHM-PHYSICAL-TELEMETRY` is recorded as a `NOT LICENSED` product
claim; current evidence contradicts any representation of design scores,
behavioral proxies, or model-derived values as physical telemetry.

## 10. Preregistered closure path

A future run must use the Gate 5 per-claim preregistration and Evidence Packet
v2 control kernel: freeze exact claim text, model/checkpoint/tokenizer/weights,
code, environment, test point, direction, corpus, splits, seeds, alpha grid,
fit and uncertainty methods, controls, falsifiers, and permitted claim
language; keep calibration and validation splits disjoint; include
zero-intervention, random same-norm direction, wrong-layer, wrong-token,
label-shuffle, and norm-matched controls; record cutoff, saturation,
instability, drift, missingness, exclusions, and negative outcomes without
erasure; require independent numerical recomputation and authenticated
execution evidence; replicate on a held-out checkpoint or model under a
prespecified comparison rule; and keep scientific eligibility
`NOT_ESTABLISHED` until independent audit, replication, claim review, and
external scientific review exist.

## 11. Memristive extension boundary

Classical memristive-system theory [E13, E14] motivates a mathematical
question — whether a CAS response parameter should depend on a versioned
history state — without authorizing a physical mapping. A provisional
nonphysical extension would declare

```text
x_(t+1) = F_profile(x_t, a_t, y_t, context_t; θ)
r_eff,t = G_profile(x_t; θ)
```

with `x_t` an explicit model-state record (initialization, update law,
sampling interval, reset rule, drift model, uncertainty, provenance), typed
separately from both a memoryless fit and an electrical memristor, and
required to predict held-out hysteresis beyond a matched memoryless baseline.
Absent that evidence, "memristive" remains an analogy and research hypothesis.
No stateful implementation, calibrated history variable, hysteresis
experiment, material device, or safety property is admitted.

## 12. Limitations

Inherited scale conflicts are preserved, not resolved. There is no admitted
live calibration, held-out estimate, drift-threshold validation, or
inter-rater reliability result. The implemented prediction is a guarded
software contract, not a validated law. Network rules are structural-only.
Gain, redundancy, and residuals remain noncausal. History-dependent dynamics
remain open. No CAS quantity is a physical electrical quantity. No safety,
clinical, regulatory, product, canon, license, or disclosure authority exists.
Internal cross-review and independent external review have not occurred.

## 13. Conclusion

CAS-Ohm 1.0 is viable as a profile-specific experimental response and
calibration proposal precisely because its type system makes the Ohm analogy
*testable and rejectable*. Its strongest present achievement is not a
discovered cognitive law but the enforced separation of quantities, units,
measurement kinds, profiles, uncertainty, response regions, semantic outcomes,
network structure, and authority — a design in which the circular validation,
the unit pun, and the residual-as-cause inference are each unrepresentable or
fail closed. Whether the model predicts anything is a question the five
registered hypotheses leave to preregistered, controlled, independently
audited experiments.

## References

Identifiers `[E5]`–`[E15]` resolve to complete metadata in
`WAVE1_ENGINEERING_CITATION_LEDGER_v0.1.json`.

- [E5] W3C, *PROV-O: The PROV Ontology*, 2013.
- [E6] JCGM 200:2012, *International Vocabulary of Metrology*.
- [E7] JCGM 100:2008, *Guide to the Expression of Uncertainty in Measurement*.
- [E8] R. G. Sargent, "Verification and Validation of Simulation Models," 2013.
- [E11] J. Pearl, *Causality*, 2nd ed., 2009.
- [E12] E. Buckingham, "On Physically Similar Systems," 1914.
- [E13] L. O. Chua, "Memristor — The Missing Circuit Element," 1971.
- [E14] L. O. Chua and S. M. Kang, "Memristive Devices and Systems," 1976.
- [E15] M. C. Kennedy and A. O'Hagan, "Bayesian Calibration of Computer
  Models," 2001.

---

**Publication boundary.** This white paper is an internal research artifact,
not a charter-approved standalone paper, released specification, peer-reviewed
result, Evidence Packet, physical or cognitive law, causal conclusion, safety
case, clinical or regulatory submission, product claim, license decision,
canon amendment, or public disclosure authorization. New matter relative to
USPTO provisional 64/037,173 requires its own filing or inclusion in the
utility conversion.
