# CAS Harness Evidence-Coverage Dispersion R&D Handoff v0.2

Status: **CORRECTED SPECIFICATION CANDIDATE / OFFLINE R&D ONLY / NON_AUTHORITY**  
Supersedes: `CAS_HARNESS_LACUNARITY_RND_HANDOFF_v0.1.md` for all new work  
Implementation state: **NOT STARTED**  
Scientific promotion state: **NOT ESTABLISHED**  
Evidence Packet status: **NO SCHEMA CHANGE AUTHORIZED**

## 1. Decision and sequencing

Adopt the evidence-gap-map concept, but do not yet adopt “lacunarity” as a permanent Harness capability.

The required order is:

1. finish and publish the current Gate 5 Phase 0 tranche;
2. freeze and independently audit this corrected v0.2 specification;
3. implement a separate offline Stage 1 using synthetic fixtures only;
4. require exact arithmetic invariants, adversarial tests, package mirroring, and an independent P0/P1 audit;
5. run a decision-neutral retrospective Stage 2 against simpler baselines; and
6. promote a dispersion-based method only if it demonstrates preregistered incremental value.

Phase 0 publication was completed before this specification was drafted. That completion does not close Gate 5, authorize Stage C, admit a Stage C corpus, or change any experimental, licensing, disclosure, or product decision.

## 2. Corrections from v0.1

This version makes the following normative corrections:

- The primary metric is named **evidence-coverage dispersion**. “One-scale categorical lacunarity” is permitted only as a research alias.
- The proposed coefficient is explicitly identified as a one-scale categorical concentration statistic, not classical spatial or multiscale lacunarity.
- The exact identity is stated: for cell proportions `p_i`, `CV2 = n * HHI - 1`, where `HHI = sum(p_i^2)`.
- The counting unit, joint-cell semantics, scope binding, comparison identity, and input contracts are frozen.
- Joint and marginal analyses are separate profiles. They may not be silently mixed.
- Unequal-exposure or rate dispersion is unavailable in Stage 1. Counts may not be relabeled as rates.
- All rational examples use reduced terms.
- Every `ArtifactRef.byte_length` is at least 1.
- `ArtifactRef` is treated as a constructible identity descriptor. Trust comes from exact byte verification, semantic re-derivation, and any artifact-specific factory seal—not from pretending its constructor is secret.
- Explicit document, cell, item, identifier, depth, node, and integer bounds are added.
- Retrospective Stage 2 is decision-neutral and must compare against zero-cell-first, minimum-support, uncertainty-first, random, and the frozen current risk-ranking method.
- CV2 has no promotion presumption. Failure to beat every preregistered baseline leaves it experimental.

## 3. Scope and authority boundary

### 3.1 Stage 1 is allowed to do only this

Given a frozen required-cell universe and frozen synthetic observations, Stage 1 may:

- derive exact per-cell counts;
- identify zero-count cells;
- compute reduced gap and coverage fractions;
- compute exact count dispersion when total support is nonzero;
- derive deterministic, explicitly non-authoritative test recommendations; and
- build and replay canonical JSON artifacts entirely offline.

### 3.2 Stage 1 is not allowed to do this

Stage 1 may not:

- call a model, provider, network, subprocess, shell, registry, database, clock, or filesystem path API;
- read or write production evidence;
- admit, reject, promote, freeze, license, disclose, start, stop, or spend;
- modify prior audit decisions or Evidence Packets;
- infer a causal, mechanistic, cognitive, safety, product, or Noetic claim;
- treat missing evidence as evidence of model failure;
- compare non-comparable scopes; or
- use floating-point or tensor arithmetic.

All Stage 1 outputs must carry these exact semantic boundaries:

- `authority: NON_AUTHORITY`
- `recommendation_authority: ADVISORY_ONLY`
- `decision_effect: NONE`
- `execution_authority: NOT_GRANTED`
- `scientific_status: STRUCTURE_ONLY`
- `classification: SYNTHETIC_ONLY`

## 4. Terminology

**Required universe**: the complete, frozen set of audit cells that the profile requires.

**Dimension**: a named axis used to define a cell, such as domain, carrier, condition, or round.

**Joint required cell**: one complete ordered tuple containing exactly one value for every dimension in `dimension_order`.

**Eligible required cell**: a roster cell whose frozen state is `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT`. Only these cells enter counts, metrics, and recommendations.

**Evidence item**: one admitted synthetic observation assigned to exactly one joint required cell.

**Support count**: the number of distinct evidence items assigned to a cell.

**Gap**: an eligible required cell with support count zero. Unavailable, pending-eligibility, or ineligible cells are not gaps. A gap is an observation about coverage, not a finding about model behavior.

**Evidence-coverage dispersion**: the exact population coefficient of variation squared over the cell support counts.

**Research alias**: `ONE_SCALE_CATEGORICAL_LACUNARITY_ALIAS_ONLY`. This alias does not assert spatial, geometric, scale-dependent, fractal, or classical lacunarity.

**Scope binding**: a canonical artifact that identifies the subject/model and exact revision where applicable, corpus or synthetic fixture, audit protocol, taxonomy, counting rule, and decision epoch.

## 5. Canonical names

The proposed Stage 1 module is separate from production and Noetic numeric code:

- canonical module: `cas_harness_v2.diagnostic_evidence_coverage_dispersion`
- canonical test module: `tests.cas_harness_v2.test_diagnostic_evidence_coverage_dispersion`
- no import of Torch, NumPy, model workers, Noetic floating-point code, or provider clients

Proposed schema names:

- `cas_harness_v2.evidence_coverage_required_universe.v1`
- `cas_harness_v2.evidence_coverage_observation.v1`
- `cas_harness_v2.evidence_coverage_metric_policy.v1`
- `cas_harness_v2.evidence_coverage_dispersion.v1`

Proposed media types:

- `application/vnd.cas-harness.evidence-coverage-required-universe+json`
- `application/vnd.cas-harness.evidence-coverage-observation+json`
- `application/vnd.cas-harness.evidence-coverage-metric-policy+json`
- `application/vnd.cas-harness.evidence-coverage-dispersion+json`

Version is expressed in the schema value, not by an added media-type parameter.

## 6. Common exact-value rules

All artifacts use UTF-8 canonical JSON with the existing Harness canonicalizer and strict loader. Unless a field is explicitly optional in this document:

- objects have an exact closed key set;
- arrays preserve declared order;
- booleans are never accepted as integers;
- integers are exact JSON integers, not decimal strings or floats;
- floating-point JSON numbers are forbidden;
- machine identifiers match the current Harness grammar `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}` exactly;
- dimension values are nonempty NFC strings, at most 128 UTF-8 bytes, with no NUL, no Unicode general-category `Cc` control character (including C0, DEL, and C1 controls), no unpaired surrogate, and no leading or trailing whitespace;
- enumeration values are exact and case-sensitive;
- SHA-256 values are exactly 64 uppercase hexadecimal characters, matching the current `ArtifactRef` contract;
- duplicate object keys are rejected;
- unknown keys are rejected;
- a supplied snapshot must equal the canonical bytes re-rendered from the semantically re-derived value; and
- all returned values are deeply immutable and detached from caller-owned objects.

An `ArtifactRef` is a normal constructible identity descriptor with the exact scalar fields required by the current Harness. Its `byte_length` must be an exact integer of at least 1. The `2,000,000`-byte ceiling in Section 16 applies to each canonical JSON document directly parsed by Stage 1; it is not a maximum for the byte length named by an embedded identity descriptor. Embedded `ArtifactRef.byte_length` values retain the current Harness contract and the strict JSON integer-bit ceiling, with no Stage 1-specific upper bound. A descriptor is not evidence of artifact validity. For an artifact directly consumed by Stage 1, validity requires exact digest and length verification over the supplied bytes, exact media type, strict parsing, and full semantic replay. An embedded reference to an external scope artifact remains identity-only in Stage 1; its external admission must be established before this API and is never inferred from the descriptor alone.

For each directly consumed input, the derived input reference uses the payload identifier (`universe_id`, `observation_id`, or `policy_id`) as `artifact_id`, the exact media type from Section 5, and the exact canonical input byte length and SHA-256. A replay-supplied reference must equal that derivation field for field.

## 7. Required-universe contract

The required-universe object has exactly these keys:

```text
schema_version
universe_id
scope_binding_ref
eligibility_snapshot_id
counting_unit
cell_semantics
dimension_order
cell_roster
classification
```

Required exact values:

- `schema_version = cas_harness_v2.evidence_coverage_required_universe.v1`
- `counting_unit = ADMITTED_SYNTHETIC_EVIDENCE_ITEM`
- `cell_semantics = JOINT_REQUIRED_CELL`
- `classification = SYNTHETIC_ONLY`

`dimension_order` is a nonempty array of distinct dimension identifiers.

`eligibility_snapshot_id` is a machine identifier bound to the point-in-time eligibility determination.

`cell_roster` is a nonempty array sorted by `cell_ordinal`. Each cell has exactly:

```text
cell_ordinal
cell_id
dimension_values
eligibility_status
```

Rules:

- `cell_ordinal` is the exact contiguous sequence `0..n-1`.
- `cell_id` is unique.
- `dimension_values` is an array with exactly `len(dimension_order)` values.
- `eligibility_status` is exactly one of `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT`, `UNAVAILABLE_AT_SNAPSHOT`, `PENDING_ELIGIBILITY_AT_SNAPSHOT`, or `INELIGIBLE_AT_SNAPSHOT`.
- A cell is identified by the pair `(dimension_order, dimension_values)`.
- No two cells may have equal `dimension_values`.
- At least one cell must be `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT`.
- Only `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT` cells are required cells and enter the denominator, counts, dispersion, cell-count output, or recommendation roster.
- Cells in the other three states remain explicitly preserved in the universe but are never interpreted as zero-support gaps.
- The universe is explicit; the implementation must not silently form a Cartesian product.
- Every scope-binding reference is byte-verified by the caller before it enters this API. Stage 1 checks only exact reference equality because it has no authority to reconstruct an external scope artifact.

Exact equality of opaque `scope_binding_ref` values establishes only syntactic identity for this profile. It does not prove that the external scope artifact is complete, semantically correct, admitted, or authoritative.

### 7.1 Joint versus marginal profiles

One universe is one joint-cell profile. A marginal analysis over one dimension or a different grouping requires a separate required-universe artifact, a distinct `universe_id`, and a separate result. Counts from a joint profile may not be presented as marginal counts, summed across an unrecorded crosswalk, or compared with another profile as if the cells were identical. Changing an eligibility state requires a new universe identity and eligibility snapshot.

## 8. Observation contract

The observation object has exactly these keys:

```text
schema_version
observation_id
universe_ref
scope_binding_ref
counting_unit
observation_protocol_id
evidence_items
classification
```

Required exact values:

- `schema_version = cas_harness_v2.evidence_coverage_observation.v1`
- `counting_unit = ADMITTED_SYNTHETIC_EVIDENCE_ITEM`
- `classification = SYNTHETIC_ONLY`

Each `evidence_items` member has exactly:

```text
item_ordinal
evidence_ref
cell_id
```

Rules:

- `item_ordinal` is the exact contiguous sequence `0..m-1`.
- Each `evidence_ref` is a structurally exact `ArtifactRef`, is unique in the observation, and has `byte_length >= 1`. The referenced synthetic evidence bytes are external to Stage 1; their admission and byte verification must be established before this API and are not inferred by this module.
- One evidence reference contributes exactly one count. Weights, repetitions, and multiplicity fields do not exist.
- Duplicate exact evidence references reject.
- Reuse of one `artifact_id` with any conflicting SHA-256, length, or media type rejects.
- Equal `(sha256, byte_length)` content identity under different artifact IDs rejects.
- Each item maps to exactly one `cell_id` whose state is `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT` in the referenced universe. Mapping an item to an unavailable, pending, or ineligible cell rejects.
- Counts are derived from the item roster; callers may not supply counts.
- An empty item roster is valid and produces the all-zero status.
- Evidence content is not interpreted by Stage 1.
- The observation’s universe and scope references must exactly equal the loaded universe references.

## 9. Metric-policy contract

The metric-policy object has exactly these keys:

```text
schema_version
policy_id
counting_mode
dispersion_mode
rate_mode
recommendation_order
tie_break_order
classification
```

Required exact values:

- `schema_version = cas_harness_v2.evidence_coverage_metric_policy.v1`
- `counting_mode = EXACT_ITEM_COUNT`
- `dispersion_mode = POPULATION_CV2_EXACT_RATIONAL`
- `rate_mode = UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1`
- `recommendation_order = [ZERO_SUPPORT_FIRST, MINIMUM_SUPPORT_NEXT]`
- `tie_break_order = [CELL_ORDINAL_ASCENDING]`
- `classification = SYNTHETIC_ONLY`

The Stage 1 policy is frozen. Callers may not supply weights, thresholds, alternative formulas, floating-point tolerances, random seeds, or an elevated resource ceiling.

## 10. Adjacency deferred

Adjacency, graph components, connected voids, geometry, distance, and scale are excluded from Stage 1 v1. There is no adjacency schema, media type, input parameter, result field, edge ceiling, or graph-derived quantity in the Stage 1 contract. Any such key or argument rejects.

A later adjacency experiment requires a separate specification, new versioned schemas, synthetic counterexamples, resource bounds, and independent audit. It may not be backfilled into the v1 carrier.

## 11. Exact arithmetic

Let `n` be the number of cells whose frozen state is `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT`. Let `x_i` be the exact nonnegative support count for eligible required cell `i`. Let:

```text
S = sum(x_i)
Z = count(i where x_i = 0)
Q = sum(x_i * x_i)
```

### 11.1 Gap and coverage fractions

The gap fraction is `Z / n`. The coverage fraction is `(n - Z) / n`. Both are reduced using the greatest common divisor. Zero is represented as `0/1`.

### 11.2 Evidence-coverage dispersion

When `S > 0`:

```text
CV2 numerator   = n * Q - S * S
CV2 denominator = S * S
CV2             = numerator / denominator, reduced by gcd
```

The numerator is nonnegative for exact nonnegative counts. Uniform positive counts produce `0/1`.

For `S > 0`, the exact bounds are `0 <= CV2 <= n - 1`. The upper bound is reached when all support is concentrated in one cell. Multiplying every count by the same positive integer leaves CV2 unchanged.

For `p_i = x_i / S`:

```text
HHI = sum(p_i * p_i)
CV2 = n * HHI - 1
```

This identity is normative. It is also why the metric must not be marketed as a newly discovered spatial statistic.

When `S = 0`:

- `dispersion_status = UNAVAILABLE_ALL_CELLS_ZERO`
- the result has no dispersion rational; and
- no divide-by-zero fallback, infinity, NaN, sentinel number, or invented `0/1` is allowed.

### 11.3 Rates and unequal exposures

Stage 1 does not accept exposure denominators and does not calculate rate dispersion. If audit cells have unequal opportunities or durations, a count-based result may still describe admitted item counts, but it may not be interpreted as a rate comparison. A future rate specification requires a separate schema, estimand, uncertainty method, and independent audit.

## 12. Deterministic recommendations

Recommendations are test-design suggestions, not findings or decisions.

For every eligible required cell, derive its support count. Sort recommended cells using exactly:

1. zero support before nonzero support;
2. lower support count before higher support count; and
3. lower `cell_ordinal` before higher `cell_ordinal`.

The recommendation reason is exactly one of:

- `ZERO_SUPPORT_REQUIRED_CELL`
- `MINIMUM_SUPPORT_REQUIRED_CELL`

The reason assignment is exact: support count `0` maps to `ZERO_SUPPORT_REQUIRED_CELL`; every support count greater than `0` maps to `MINIMUM_SUPPORT_REQUIRED_CELL`.

All eligible required cells are included in the deterministic ranking. Stage 1 v1 uses no truncation: result recommendation count equals eligible-required-cell count.

CV2 does not alter this ordering in Stage 1. It is a profile summary whose incremental decision value remains unproved.

## 13. Result contract

The result object has exactly these top-level keys:

```text
schema_version
profile_id
input_bindings
metric_identity
coverage_summary
dispersion_summary
cell_counts
recommendations
classification
authority_boundary
```

Required exact values:

- `schema_version = cas_harness_v2.evidence_coverage_dispersion.v1`
- `metric_identity.canonical_name = EVIDENCE_COVERAGE_DISPERSION_POPULATION_CV2`
- `metric_identity.research_alias = ONE_SCALE_CATEGORICAL_LACUNARITY_ALIAS_ONLY`
- `metric_identity.spatial_claim = NONE`
- `metric_identity.multiscale_claim = NONE`
- `classification = SYNTHETIC_ONLY`

`profile_id` is deterministic: `ecd-` followed by the lowercase SHA-256 of the UTF-8 canonical JSON bytes of `input_bindings`.

`input_bindings` has exactly `required_universe_ref`, `observation_ref`, and `metric_policy_ref`. All three are exact artifact-ref objects.

`metric_identity` has exactly `canonical_name`, `research_alias`, `spatial_claim`, and `multiscale_claim`, with the exact values frozen above.

`coverage_summary` has exactly `roster_cell_count`, `eligible_required_cell_count`, `unavailable_cell_count`, `pending_eligibility_cell_count`, `ineligible_cell_count`, `observed_nonzero_cell_count`, `zero_cell_count`, `evidence_item_count`, `gap_fraction`, and `coverage_fraction`. The first five counts must exactly partition the frozen cell roster: eligible plus unavailable plus pending plus ineligible equals roster count. Gap and coverage denominators are `eligible_required_cell_count` only. Each fraction is a reduced rational object with exactly `numerator` and `denominator`, a positive denominator, a nonnegative numerator, and gcd equal to 1.

`dispersion_summary` has one of two closed forms:

Available form:

```text
status = AVAILABLE_EXACT_COUNT_DISPERSION
total_support
sum_squared_support
cv2 = {numerator, denominator}
hhi_relationship = CV2_EQUALS_N_TIMES_HHI_MINUS_ONE
rate_status = UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1
```

Unavailable form:

```text
status = UNAVAILABLE_ALL_CELLS_ZERO
total_support = 0
sum_squared_support = 0
cv2 = ABSENT
hhi_relationship = UNAVAILABLE_ALL_CELLS_ZERO
rate_status = UNAVAILABLE_RATE_MODE_NOT_IN_STAGE1
```

`cell_counts` has one row per eligible required cell, in original roster-ordinal order. Each row has exactly `cell_ordinal`, `cell_id`, `eligibility_status`, and `support_count`; `eligibility_status` is always `ELIGIBLE_OBSERVABLE_AT_SNAPSHOT`.

`recommendations` has one row per eligible required cell in the exact ordering from Section 12. Each row has exactly `recommendation_ordinal`, `cell_ordinal`, `cell_id`, `support_count`, and `reason`. Recommendation ordinals are the contiguous sequence `0..n-1`.

`authority_boundary` has exactly:

```text
authority = NON_AUTHORITY
recommendation_authority = ADVISORY_ONLY
decision_effect = NONE
execution_authority = NOT_GRANTED
scientific_status = STRUCTURE_ONLY
evidence_packet_effect = NONE
```

The returned artifact reference uses `profile_id` as `artifact_id`, the exact result media type from Section 5, and the exact canonical result byte length and SHA-256.

## 14. Worked arithmetic example

Consider ten eligible required cells with support counts:

```text
[0, 0, 1, 1, 1, 1, 1, 1, 1, 3]
```

Then:

```text
n = 10
S = 10
Z = 2
Q = 16
gap fraction = 2/10 = 1/5
coverage fraction = 8/10 = 4/5
CV2 = (10*16 - 10*10) / (10*10)
    = 60/100
    = 3/5
```

The example is one-scale count dispersion. It makes no spatial, behavioral, causal, or product claim.

An illustrative valid-shape reference uses a positive length:

```json
{
  "artifact_id": "synthetic-universe-example",
  "byte_length": 128,
  "media_type": "application/vnd.cas-harness.evidence-coverage-required-universe+json",
  "sha256": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
}
```

This shape does not claim that the referenced bytes exist. An implementation test must use actual canonical bytes whose length and digest verify exactly.

## 15. Comparability rules

Two results are directly comparable only when all of the following are exactly equal:

- required-universe reference;
- scope-binding reference;
- metric-policy reference;
- counting unit;
- cell semantics;
- eligibility snapshot and complete cell roster;
- dimension order and eligibility states; and
- observation protocol identifier.

A model, weights, tokenizer, corpus, protocol, taxonomy, decision epoch, or universe change creates a different scope. Such results are not directly comparable unless a separately frozen crosswalk and paired-comparison protocol explicitly authorizes the comparison. Stage 1 does not create such a crosswalk.

## 16. Resource ceilings

The implementation must reject inputs before unbounded allocation or arithmetic.

Global strict-JSON ceilings inherited from the current Harness:

- maximum canonical document bytes: `2,000,000`
- maximum JSON depth: `40`
- maximum JSON nodes: `50,000`
- maximum integer bits: `2,048`

Stage 1 tighter ceilings:

- dimensions: `1..16`
- total roster cells: `1..2,048`
- eligible required cells: `1..2,048`
- evidence items: `0..2,048`
- identifier UTF-8 bytes: `1..128`
- recommendations: exactly the number of eligible required cells, at most `2,048`

The lowest applicable ceiling wins. A policy document or caller cannot raise a ceiling. Complexity must remain bounded by the admitted roster cells and items; no implicit Cartesian-product expansion is allowed.

## 17. Minimum public API

The candidate public surface is pure and byte-oriented:

```text
build_evidence_coverage_dispersion(
    *,
    required_universe_bytes: bytes,
    observation_bytes: bytes,
    metric_policy_bytes: bytes,
) -> EvidenceCoverageDispersionArtifact

load_evidence_coverage_dispersion(
    snapshot_bytes: bytes,
    *,
    required_universe_bytes: bytes,
    observation_bytes: bytes,
    metric_policy_bytes: bytes,
) -> EvidenceCoverageDispersionArtifact

replay_evidence_coverage_dispersion(
    artifact: EvidenceCoverageDispersionArtifact,
) -> EvidenceCoverageDispersionArtifact
```

All public byte parameters require exact built-in `bytes`; subclasses and byte-like aliases reject. Build and load retain detached immutable copies of the exact canonical input bytes inside the returned factory-issued artifact. Replay accepts no replacement context: it uses those retained snapshots, re-derives a fresh artifact, and requires exact raw-byte, payload, scalar, and artifact-reference equality. A result snapshot alone is insufficient; loading it always requires the three explicit original input parameters.

Every load or artifact-reference access must:

1. verify exact bytes, digest, length, media type, and schema;
2. strict-parse with type-aware boolean/integer distinction;
3. reload and validate all original inputs;
4. re-derive every count, fraction, metric, ordering, and boundary value;
5. require byte-for-byte equality with the canonical re-rendering; and
6. return detached immutable state.

The result type is factory-only and cannot be directly initialized. Its JSON view is tuple-backed and recursively immutable, with no reachable mutable dict, list, set, bytearray, or caller-owned backing. It retains private built-in `bytes` snapshots of its three inputs and result. Every `.artifact_ref` access validates the process seal and performs the same fresh input/result replay before returning a reconstructed reference. If a bounded process-seal registry is used, eviction fails closed.

A process-local factory seal rejects ordinary direct-construction and slot-population forgeries in an unmodified interpreter, but it is only defense in depth. Module-namespace rebinding of canonicalizers, renderers, factories, validators, or seal helpers after import must not change build/load/replay behavior; the public closures capture their audited dependencies.

Arbitrary same-interpreter reflection is outside the process-seal provenance boundary. Mutation through `cell.cell_contents`, function `__defaults__` or `__kwdefaults__`, code-object replacement, `ctypes`, a tracing or debugging hook, or an equivalent mechanism invalidates **all** in-process seal and result claims. Pure Python cannot make a provenance seal tamper-proof against an actor that can rewrite the verifier's own executable state. Under such deliberately mutated state, injecting an exact semantic clone may reproduce only the same identity descriptor; that descriptor is not proof of factory issuance. No claim may be made from that interpreter after the mutation.

Durable validity comes from strict verification and complete semantic re-derivation from the exact frozen source plus exact input and result bytes in a pristine or independent execution. Even a successful independent replay remains `SYNTHETIC_ONLY / NON_AUTHORITY / ADVISORY_ONLY`. In an unmodified interpreter, changing any semantic, classification, authority, count, ordering, or input-binding value must still fail fresh replay.

## 18. Stage 1 implementation acceptance

Stage 1 is acceptable for an offline synthetic-only merge only if all of the following pass:

- exact canonical build/load/replay equality;
- byte-for-byte fresh replay equality;
- reduced-rational invariants for every output fraction;
- `CV2 >= 0` and exact `CV2 = n*HHI - 1` property tests;
- exact `CV2 <= n-1` and positive-integer scale-invariance property tests;
- uniform-count `0/1` property;
- all-zero unavailable status with no numeric substitute;
- exact recommendation ordering;
- bool/int alias rejection at every integer field;
- duplicate-key, unknown-key, Unicode (including C1 `Cc` controls), size, depth, node, integer-bit, and resource-bound attacks;
- embedded external `ArtifactRef.byte_length` values greater than `2,000,000` that remain valid identity descriptors while each directly parsed canonical document stays within its own byte ceiling;
- duplicate item, unknown cell, noncontiguous ordinal, scope mismatch, universe mismatch, and protocol mismatch attacks;
- evidence assignment to unavailable, pending, or ineligible cells and eligibility-state substitution attacks;
- attempts to omit non-eligible roster cells and relabel them as zero support;
- adjacency argument, key, schema, or graph-result injection rejection;
- joint/marginal substitution rejection;
- ordinary direct-construction, module-global-rebinding, mutable-backing, subclass, exposed-registrar, helper-forgery, GC/identity-reuse, and bounded-eviction attacks in an unmodified interpreter;
- an explicit reflection-boundary test showing that deliberate registry-cell injection can reproduce only an exact semantic clone and the same identity descriptor, while any semantic or authority change fails fresh replay unless verifier state itself is mutated, in which case every in-process claim is classified invalidated;
- static and runtime evidence of no filesystem, clock, network, process, provider, model, Torch, NumPy, or callback capability;
- exact canonical/package mirror parity and provenance;
- no Evidence Packet schema change;
- focused tests plus the proportionate current Harness/package verification surface; and
- an independent audit reporting P0 = 0 and P1 = 0 for the frozen Stage 1 bytes.

Synthetic fixtures must include at least:

- all zero;
- exactly one nonzero cell;
- uniform positive support;
- multiple zero cells;
- highly concentrated support;
- maximum admitted roster-cell and evidence-item bounds;
- mixed eligible, unavailable, pending, and ineligible rosters proving that only eligible cells enter gap denominators and recommendations;
- reordered-but-semantically-equal inputs that must reject when order is canonical;
- different joint universes with deceptively equal marginals; and
- unequal-exposure metadata attempts that must reject rather than create a rate result.

## 19. Decision-neutral Stage 2 retrospective

Stage 2 asks whether a dispersion-assisted policy improves **future test selection**. It does not revisit or change prior audit outcomes.

### 19.1 Frozen study unit

Before evaluation, freeze:

- eligible historical audit instances;
- exact subject/model, corpus, protocol, taxonomy, and decision identities;
- inclusion and exclusion rules;
- group-preserving train, tuning, and final-holdout partitions;
- candidate cells available at each simulated decision point;
- fixed recommendation budgets `K`;
- outcome adjudication completed without access to evaluated rankings;
- the current production risk-ranking implementation and bytes; and
- all baseline implementations, random seed rosters, tie breakers, and missing-data rules.

Each simulated decision point must additionally bind an exact `as_of_ordinal`, an exact pre-decision evidence-snapshot reference, and an exact candidate-cell roster. Every policy must be reconstructed from that same snapshot and may use only fields that existed by the `as_of_ordinal`. Post-decision evidence, outcome labels, adjudications, later support counts, later risk features, and later uncertainty inputs are forbidden ranking inputs.

Each instance must also freeze one exact `outcome_horizon_end_ordinal` after its `as_of_ordinal` and one policy-independent ascertainment protocol applied uniformly to every cell in the frozen candidate roster. A complete blinded label must exist for every candidate cell at that same horizon. The candidate roster may not be reduced using post-`as_of` availability. If even one candidate lacks complete common-horizon ascertainment, the entire instance is excluded under the pre-frozen completeness rule; individual missing cells may not be deleted, imputed as zero, or made “unavailable to all policies.”

Historical test-selection logs alone do not establish complete potential outcomes for unselected cells. An instance is admissible only when a standardized later audit, replay, or complete archive supplies policy-independent common-support labels for the entire candidate roster. A proposed off-policy alternative requires a separate frozen and independently audited design with known assignment propensities, positivity over every candidate action, and explicit censoring adjustment. v0.2 authorizes no such off-policy shortcut.

All observations sharing a subject/model/corpus/protocol lineage belong to one partition and one inference cluster. They may not be split across train, tuning, and final holdout. Fitting and tuning occur only on train and tuning partitions. Final-holdout outcomes remain inaccessible until the endpoint, implementations, exact hashes, effect thresholds, seed roster, tie rules, and analysis code are frozen.

No instance used to choose a metric, effect threshold, weight, baseline, endpoint, or analysis method may enter the final holdout.

### 19.2 Policies to compare

The comparison must include at least:

1. `ZERO_CELL_FIRST`: zero-support candidates by cell ordinal, followed by all remaining candidates by cell ordinal
2. `MINIMUM_SUPPORT_FIRST`: all candidates by ascending support count, then cell ordinal
3. `UNCERTAINTY_FIRST` using a separately frozen estimand and exact interval method, ranked by descending interval width and then cell ordinal
4. `RANDOM` using a frozen seed roster and exact aggregation rule
5. `CURRENT_RISK_RANKING` bound to the current method’s exact bytes
6. `CV2_ASSISTED`, currently `UNSPECIFIED_BLOCKED_ANALYTIC_FUTILITY`
7. `CV2_ASSISTED_WITH_CV2_REMOVED`, identical to an eventual policy 6 except that every CV2-derived term is replaced by exact `0/1`

CV2 alone is a profile summary and does not rank cells. The superficially natural score `CV2(x) - CV2(x + e_i)` is forbidden as an incremental-CV2 policy because it is analytically identical to `MINIMUM_SUPPORT_FIRST`. For `S > 0`, every term in `CV2(x + e_i)` is constant across candidate cells except `2*n*x_i/(S+1)^2`; therefore maximizing the reduction ranks exactly by ascending `x_i`. For `S = 0`, every candidate ties and both policies use the same ordinal tie break. Their rankings and fixed-budget utilities are identical for every input, so a required positive improvement is impossible.

No alternative CV2-assisted ranking is specified or authorized in v0.2. Before Stage 2 may start, a separate preregistered amendment must define a scientifically motivated, exact action rule whose ranking is demonstrably non-equivalent to zero-cell-first, minimum-support, uncertainty-first, random, and current-risk ranking on frozen synthetic counterexamples. It must identify the CV2 contribution rather than bundle unrelated features. Any eligibility rule or non-CV2 feature must be identical in the CV2-removed ablation. Property tests must prove at least one admissible profile on which the CV2-assisted and CV2-removed rankings differ before final-holdout access. Failure to identify such a rule means `NO STAGE2 CV2 EVALUATION / NO PROMOTION`.

The uncertainty baseline must bind its estimand, confidence level, interval construction, and available pre-decision inputs. The current-risk baseline must bind both executable bytes and its exact pre-decision input projection. A baseline that cannot run from the common `as_of` snapshot is unavailable and blocks promotion; it may not receive later information. Random utility is the arithmetic mean across every frozen seed, with no best-seed selection.

### 19.3 Outcome and analysis

The primary outcome is one binary cell label:

```text
PROTOCOL_VALID_NEW_EVIDENCE_DEFICIENCY_REQUIRING_PREREGISTERED_FOLLOW_UP
```

For decision point `j` and candidate cell `c`, `L_jc = 1` only when independent reviewers, blinded to every evaluated ranking, establish that label under the common ascertainment protocol using evidence in the exact interval `(as_of_ordinal, outcome_horizon_end_ordinal]`; otherwise `L_jc = 0`. The adjudication rubric and reviewer resolution rule must be frozen before rankings are generated. This label is an evidence-planning outcome. It explicitly excludes model-failure labels, ACCEPT/FLAG/HFR dispositions, causal conclusions, product decisions, and coverage status known at the decision point.

For policy `p` at fixed budget `K`, define exact per-instance utility:

```text
Y_pj(K) = sum(L_jc for the first K distinct cells ranked by policy p)
```

If fewer than `K` candidates exist, the instance is ineligible unless that rule was frozen before partitioning. If test costs vary, count utility remains primary and a separately frozen cost-normalized utility is secondary; costs may not be inferred after rankings are seen.

For every comparator `b`, the paired cluster-level contrast is `D_bj(K) = Y_CV2,j(K) - Y_bj(K)`. Multiple decision points in one lineage are aggregated by a pre-frozen equal-lineage rule before inference so that one lineage is one independent analysis unit.

The preregistration must define:

- one primary budget `K` and any secondary `K` values;
- equal-lineage aggregation and the paired cluster unit;
- exclusion or retention of zero-positive instances, frozen without ranking access;
- exact cost accounting;
- an exact blocked sign-flip test over the lineage-level paired contrasts;
- a two-sided simultaneous confidence set obtained by inversion of that same sign-flip test;
- familywise `alpha = 0.05` with Holm adjustment across every required comparator and every confirmatory `K`;
- missing-data treatment;
- a positive rational minimal practically important improvement `delta_b` for each comparator;
- stability endpoint; and
- false-prioritization or harm endpoint.

The sign-flip analysis requires the lineage-level paired contrasts to be exchangeable under sign inversion under the tested null; that assumption and its diagnostic must be frozen before outcome access. The implementation must enumerate the exact sign-flip distribution. If the cluster count makes exact enumeration exceed a frozen resource ceiling, or if sign exchangeability is not defensible, confirmatory inference is unavailable until a separate distribution-free method is specified and independently audited. Approximate or post-selected substitution is forbidden.

Instances with no positive label are retained by default and contribute zero utility to every policy. Missing outcome labels are not zero and make the whole instance ineligible under the complete-ascertainment rule. Random results must be derived from the full frozen finite seed roster. Reporting only the best random seed is forbidden.

### 19.4 Promotion criterion

CV2-assisted ranking is promoted only if, on the untouched final holdout:

- it beats **each** named baseline on the preregistered primary endpoint;
- for every required comparator `b`, the multiplicity-adjusted lower confidence bound for the mean lineage-level `D_b` is strictly greater than its frozen positive `delta_b`;
- it is not worse than any baseline on preregistered cost, stability, and false-prioritization safety margins;
- results remain valid under the preregistered sensitivity analyses; and
- an independent auditor reproduces the evaluation from frozen bytes.

A tie, mixed result, endpoint change, leakage, missing comparator, failed exchangeability requirement, unavailable confirmatory interval, or failure against any required baseline—including the CV2-removed ablation—means **NO PROMOTION**. The evidence-gap map may remain useful even if CV2 is rejected.

Stage 2 output remains `RETROSPECTIVE / DECISION_NEUTRAL / NON_AUTHORITY`. It cannot amend the historical decisions used as data.

## 20. Later research layers

Behavioral-deficit, internal-localization, causal-intervention, independent-replication, and optional Noetic-interpretation layers remain future research. They require separate schemas, preregistrations, authority decisions, and evidence. Stage 1 or Stage 2 success does not promote any later layer.

In particular:

- coverage gaps are not behavioral deficits;
- behavioral associations are not internal localization;
- internal correlates are not causal effects;
- one-team causal effects are not independent replication; and
- replicated effects do not automatically validate a Noetic construct.

## 21. Integration and publication boundary

No current repository module, package manifest, verifier manifest, review matrix, Evidence Packet schema, production API, UI, worker, or RunPod configuration is changed by this specification.

After this document passes independent audit, the smallest permitted Stage 1 tranche is:

- one new canonical source module;
- one new focused test module;
- its exact package mirror and provenance integration;
- collision-aware package export integration;
- exact manifest/verifier bindings;
- existing-node red-team coverage where practical;
- tracker and existing-document status updates; and
- no provider, model, GPU, corpus, or product action.

The implementation must remain separately reviewable and must not be folded into Noetic numeric code.

## 22. Final acceptance statement

The concept is accepted for controlled R&D after Phase 0 because an exact required-cell evidence-gap map can improve audit completeness and test planning.

The CV2 component is not accepted as a permanent Harness capability. It is a mathematically valid one-scale concentration summary equivalent to `n*HHI - 1`, but it must demonstrate incremental decision value against simpler methods under a frozen, decision-neutral retrospective protocol.

Until those gates pass, the correct status is:

**EVIDENCE-GAP MAP: ADOPT FOR OFFLINE SYNTHETIC R&D**  
**CV2 / “LACUNARITY”: EXPERIMENTAL / NOT PROMOTED**  
**HARNESS AUTHORITY EFFECT: NONE**
