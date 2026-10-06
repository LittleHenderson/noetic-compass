# CAS-Ohm v1 source audit and candidate specification v0.1

**Status:** `OPEN / RING 4 / NOT LICENSED / HELD`

Preferred description: **profile-specific experimental response model and
calibration proposal**.

## 1. Source conflicts retained

The machine-readable evidence and locator record is
`CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json`. Relevant Guide and PCBA PDF
pages were rendered and visually inspected; the Appendix I line ranges were
read from the exact UTF-8 source; and the addendum was inspected by OOXML
paragraph/table position because both available page-rendering routes failed.
No DOCX page number is therefore asserted.

1. The Guide uses an `R` range of `0.1-10`, while PCBA Appendix I uses a
   dimensionless `0-100` constraint score. The Guide's `sat=8.5` conflicts with
   Appendix I's `0-1` region fraction and explicit mixed-scale warning.
2. The operationalization addendum maps `V` to steering alpha and `I` to an
   activation projection but retains score-derived resistance components.
   `I_pred = V/R_total` is dimensionally invalid until effective resistance has
   calibrated units `alpha_unit / activation_unit`.
3. Full-scale response has three incompatible methods: board-selected, per-path
   rail/floor, and corpus 95th percentile. They are separate profiles.
4. Fisher-Rao cause/effect gain and local Jacobian/projection gain are distinct.
   No theorem or experiment currently identifies them.
5. ASOM is a mnemonic. Dose-response region and semantic correctness are
   independent axes.
6. Series addition, reciprocal parallel aggregation, and multiplicative gain
   require compatible coordinates and validated linear active-region profiles.
7. A residual cannot identify hidden policy, bypass, or cause. At zero observed
   response it is censored/undefined; elsewhere it remains a non-identifying
   diagnostic with propagated uncertainty.

Pinpoint anchors include Guide PDF pages 6-7 and 10-18; addendum paragraphs
5-10, 14-19, and 23-35 plus operationalization/ASOM/falsification table rows;
Appendix I lines 20-59, 90-162, 171-202, 206-277, and 325-339; and the PCBA
Fisher-Rao gain definitions at PDF page 56 (book page 40) and PDF page 153
(book page 137).

## 2. Quantity model

Every numeric value is typed evidence, never a bare binary float:

```text
ObservedValue {
  quantity_kind,
  exact_decimal_value,
  unit_id,
  measurement_kind,
  method_id,
  calibration_profile_sha256,
  estimate_or_observation,
  uncertainty,
  confidence_interval,
  sample_size,
  raw_artifact_refs,
  control_refs,
  derivation_parents,
  missing_or_censored_reason
}
```

Measurement kinds include `DESIGN_VALUE`, `INSTRUMENTED`,
`BEHAVIORAL_PROXY`, `MODEL_DERIVED`, `HUMAN_SCORE`, and `LLM_SCORE`. Derived
values preserve parent lineage and do not become instrumented because one parent
was instrumented.

Canonical evidence is exact-type tagged, cycle-aware, unsafe-Unicode rejecting,
and bounded by declared depth, node, container, text, output, and 2,048-bit
integer limits. A host-runtime integer-conversion failure is normalized to the
candidate's validation error rather than leaking a platform exception.

The unit ontology separates constraint score, normalized fraction, alpha dose,
activation projection, effective resistance, and any real physical SI unit.
Physical volt/amp/ohm labels are forbidden aliases for model quantities.

## 3. Calibration profile

A profile binds exact model/config/tokenizer/weights and code identities;
runtime/dtype; test-point and direction-vector identity, norm, and sign; corpus
manifest and rights; seeds/randomization; alpha grid; I_FS method; fit and
uncertainty methods; tolerances; response-region rules; controls; drift/expiry;
review state; and a canonical digest.

Effective resistance is estimated on calibration data and must predict held-out
response. Defining `R_eff := V/I` on the same samples and then claiming `V=IR`
is rejected as circular.

## 4. Independent classifications

Dose-response region:

- cutoff;
- active;
- saturation;
- non-ohmic; or
- unstable.

Semantic outcome:

- intended;
- opposite;
- off-axis; or
- unassessed.

No region mechanically determines an outcome. No diagnosis is emitted from a
cutoff, saturated, unstable, uncalibrated, stale, or wrong-model profile.

## 5. Quantization and network capabilities

Q4 uses exact pre-rounding values and half-open bins `[0,2.5)`, `[2.5,5)`,
`[5,7.5)`, and `[7.5,10]`. Trend tags require an axis, interval, minimum effect,
and uncertainty rule.

Series, parallel, and gain-product operations are available only as
unauthenticated structural research calculations. Every result binds the exact
profile and validation evidence, capability label, authority-manifest identity,
attestation identities (which may be empty), trust mode, historical replay time,
runtime/code/dependency identities, and declared covariance limitation.
Structural-only mode has no keys or signature requirement. If the optional
integrity-configuration mode is used, its Ed25519 attestations are verified and
replayed, but they still do not establish independent reviewer, legal, product,
or Evidence Packet authority. All aggregates retain unique ordered child values,
topology, identities, and derivation evidence; duplicate or cyclic paths fail
closed. No authenticated capability path is implemented.

## 6. Research-packet completeness and Evidence Packet eligibility

At least one instrumented field is necessary but insufficient even for
structural research-packet completeness. Completeness also requires exact model
revision, valid profile digest, raw artifact bytes, relevant controls,
uncertainty, per-field lineage and status, nonstale calibration, and admissible
review state. Score-only, zero-instrumentation, missing-provenance, mixed-scale,
unknown-profile, or tampered records fail closed.

Authenticated Evidence Packet eligibility is a separate field and is false in
this candidate. It cannot become true until an independently admitted authority
manifest, protected key lifecycle and revocation policy, trusted current-time
receipt, materialized model/code/runtime dependency identities, authenticated
instrument evidence, and reviewed packet policy are all present. Deterministic
in-repository fixture keys and caller-supplied replay time never satisfy those
conditions.

## 7. TKS v8 and Noetic Topos 2 boundary

Cause/effect references and cascades remain external typed annotations until an
approved CAS semantic registry maps them. A finite deterministic cascade can be
represented structurally by `SemigroupoidPath`; continuous observations remain
outside the finite kernel. Q4 is a lossy profile-bound quantizer.

Raw observations remain Evidence Packet data or provisional sections of an
ambient measurement presheaf. A `MarkedCover` proves no measurement true, and
records do not enter resolved/sheaf semantics until restriction and gluing under
one calibration profile are defined and tested.

## 8. Closure experiments

1. Mixed-scale/unit reconciliation and golden rejection fixtures.
2. Synthetic linear, cutoff, saturation, nonlinear, parallel, confounded, and
   bypass known-fault boards; this validates software only.
3. Randomized held-out alpha sweeps with random-direction, wrong-layer,
   label-shuffled, norm-matched, and zero-intervention controls.
4. Independent constraint manipulation and inverse-slope prediction.
5. Active-region local/end-to-end gain composition.
6. Redundancy ablation against matched random-head controls.
7. Blinded residual localization on implanted faults; withdraw causal language
   if it fails.
8. Bootstrap uncertainty, cross-split direction reproducibility, checkpoint
   drift, and inter-rater reliability.

Forbidden product wording includes “physical telemetry,” “measures attention,”
“electrical law,” “causal by construction,” “cross-model comparable,” “proves
hidden resistance,” and any safety or verdict claim.
