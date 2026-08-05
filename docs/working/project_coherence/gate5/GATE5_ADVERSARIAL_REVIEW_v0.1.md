# Gate 5 adversarial review v0.1

**Status:** `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

## Decision

**KEEP GATE 5 OPEN.** The Harness v2 research-control kernel, historical
recovery, and bounded live-worker repairs establish useful implementation and
negative-evidence controls. They do not establish authenticated execution,
trusted ordering, a live scientific result, independent numerical agreement,
replication, peer review, product readiness, licensing, or disclosure
authority.

The controlling charter status remains `OPEN / NOT STARTED`. Control-kernel
engineering has begun, but none of the charter's per-module scientific closure
conditions has been satisfied by a live admitted experiment. No result in this
review creates `ACCEPT`, `LICENSED`, a public route, or a product route.

## Exact review surface

This review is bounded to the following current surfaces:

- the isolated control kernel under `src/cas_harness_v2/`;
- the nominal and independent adversarial tests under `tests/cas_harness_v2/`;
- `HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md`;
- the current `live-trace-worker` model-identity and intervention-integrity
  controls;
- the exact historical V1-V4 recovery inventory and its independent verifier;
- the Gate 5 conditions in
  `PROJECT_COHERENCE_MASTER_CHARTER_v0.1.md`; and
- the machine-readable companion matrix
  `GATE5_REVIEW_MATRIX_v0.1.json`.

The companion matrix schema is
`project_coherence.gate5_review_matrix.v0.1`. It contains **47 criteria**:

- 18 `IMPLEMENTED_AND_REGRESSION_TESTED`;
- 3 `IMPLEMENTED_AND_HASH_VERIFIED`;
- 1 `PRESERVED_NEGATIVE_EVIDENCE`;
- 10 `OPEN_ENGINEERING`;
- 1 `OPEN_SECURITY`;
- 5 `OPEN_GOVERNANCE`; and
- 9 `OPEN_EXTERNAL_VALIDATION`.

The implemented dispositions describe only their stated bounded controls. They
are not Gate 5 acceptance decisions.

## Review method

The review kept five evidence classes separate:

1. exact-byte identities and schema behavior;
2. regression-tested implementation behavior;
3. current worker structural controls;
4. preserved historical evidence, including known failures; and
5. external, scientific, security, or governance obligations that repository
   tests cannot satisfy.

A defect is called repaired only when its reproducer is retained as a regression
test. A self-hash is treated only as an integrity identity. A declared identity
is not treated as proof of a real person, affiliation, independence, or
authority. A reported metric is not treated as independently recomputed truth.

## Control-kernel adversarial chronology

The stable kernel exposes three public schema families:

| Artifact | Exact schema |
|---|---|
| Per-claim preregistration | `cas_harness_v2.preregistration.v1` |
| Preregistration amendment | `cas_harness_v2.preregistration_amendment.v1` |
| Evidence Packet | `cas_harness_v2.evidence_packet.v2` |

An internal exact-byte outcome-access carrier uses
`cas_harness_v2.outcome_access_event.v1`.

### What the kernel now enforces

The implemented kernel provides these bounded controls:

- strict, bounded, duplicate-safe UTF-8 JSON with no floating-point JSON
  numbers, key coercion, Boolean/integer substitution, unsafe surrogate, or
  unknown-field path;
- exact raw-byte binding to one current claim-ledger record and its exact claim
  text;
- a protected fixed-sample design with exact split targets, attrition maxima,
  fixed stopping, forbidden interim outcome access, exclusion and missing-data
  rules, uncertainty, falsifiers, required controls, and power-analysis
  identity;
- exact model, code, environment, dependency, weights, tokenizer, split, and
  analysis identities;
- hash-linked append-only amendments with cycle detection, skipped-link
  rejection, strict ordering, one execution window, and a 128-link total cap;
- an exact-byte outcome-access event bound to declared execution completion and
  the frozen pre-outcome chain;
- exact disjoint split accounting:
  `enrolled = analyzed + missing + excluded`;
- preservation of coherent underpowered or deviating runs as negative evidence,
  with computed scientific eligibility `INELIGIBLE`;
- fresh replay of packet and carrier bytes before assessment;
- separate structural, authentication, reported-criteria, scientific,
  numerical-audit, replication, claim-review, and governance axes; and
- invariant `RING 4 / NOT LICENSED / HELD / NONE` governance with public and
  product routes false.

### Defects found and retained as tests

Independent adversarial work reproduced and closed the following classes:

1. forged dataclass carriers that did not match fresh exact-byte loader replay;
2. mutation of retained registry bytes after snapshot construction;
3. direct base, amendment, and post-seal chain injection;
4. recursive predecessor cycles and unbounded/deep-chain denial of service;
5. skipped predecessor links and nonmonotone amendment identifiers;
6. unenforced prospective execution windows;
7. audit `match` declarations coexisting with discrepancies;
8. case-only aliases being used to satisfy declared role separation;
9. incomplete recognition of repository-known Evidence Packet v1 labels;
10. absent fixed-sample, stopping, exclusion, missing-data, and attrition rules;
11. outcome access preceding execution completion;
12. incoherent or unbounded split row accounting; and
13. bypass mutation of a valid outcome-event field followed by recomputation of
    a matching chain hash and packet.

The final event-carrier repair snapshots canonical event bytes, records their
SHA-256 and byte length, and freshly replays them against the current
pre-outcome chain before public reads. This is process-local tamper detection,
not WORM authority.

The clean focused receipt is **108 passed tests plus 50 subtests** under Python
3.14 with bytecode/cache output disabled. The receipt is limited to
`tests/cas_harness_v2`; it is not a repository-wide or production receipt.

## Live-worker adverse evidence and bounded repairs

### Intervention coordinate-space defect

The prior worker declared MLP coordinates reaching approximately 3,041 while
hooking a 768-wide post-projection tensor and silently dropping out-of-range
coordinates. A passing worker suite therefore did not prove that declared
erasures fired or changed an activation.

The bounded coordinate repair moves the intervention to
`gpt_neox.layers[{layer}].mlp.dense_4h_to_h` pre-hook `input[0]`, the 3,072-wide
post-activation MLP intermediate space. Typed structural receipts now bind
requested, valid, invalid, and applied coordinates; observed geometry; hook
firing; effective gain; exact activation change; and paired last-token-logit
change. Wrong-space, invalid, missing/nonfiring hook, nonfinite, cardinality,
zero-effect, unchanged activation/output, and demo-only paths remain typed
fail-closed observations. The canonical checkpoint records a 13-case dedicated
adversarial matrix, 76 focused worker integration tests, and 255 complete worker
tests for that earlier repair.

The intended current eraser v2 design has **no runtime causal-attestation status
or valid emission path**.
Even when the hook fires and exact comparisons observe both an activation change
and an output delta, the receipt is
`APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED` with
`structurally_valid=false`. Generation uses the paired unmodified baseline
snapshot, not the attempted-pass output, and the stream aborts after emitting
the receipt. Construction-time validation rejects a forged payload that tries
to resurrect the retired causal-success state or set `structurally_valid=true`.
Frozen public carriers and nested collections prevent assignment mutation, and
copy-with-update is replayed through validation instead of trusting unchecked
updates.

These controls establish structural execution behavior only. They do not prove
that the selected coordinates are semantically valid, that the intervention is
causally selective, or that a scientific hypothesis is true.

### Numerical and mutable-state red team

The later numeric red team extends beyond hook firing. Its retained chronology
probes:

- RNG-only output drift, which cannot support attribution;
- NaN and positive/negative infinity in activations, outputs, or controls;
- forged reference geometry, wrong hook paths, and wrong observation phases;
- dtype, rank, output-shape, and device incomparability;
- repeated target-hook invocation and other hook-cardinality mismatches;
- duplicate coordinates and atomic rejection of partially invalid write sets;
- negative, Boolean, nonfinite, uncoercible, subnormal, and oversized gains;
- caller-activation aliasing and rejected fallback output aliasing;
- hidden mutable model state, including a third-pass drift counterexample after
  two apparently stable controls;
- exact finite/stable-control requirements, RNG restoration, baseline snapshot
  fallback, and stream abort after every attempted intervention; and
- public-schema forgery of the retired causal-success state, both during
  construction and by assignment after a carrier has already validated.

The retained mutable-state reproducer established that two exact unmodified
controls cannot prove that a third-pass output delta was caused by an
intervention. The conservative repair therefore does not attempt to infer such
causality: all attempted-pass receipts remain structurally invalid, an exact
activation-plus-output delta is explicitly unattributed, generation falls back
to the baseline snapshot, and execution stops before another token can inherit
unverified mutable state.

The test
`test_validated_public_receipt_cannot_be_mutated_into_retired_attestation`
subsequently reproduced a post-validation assignment bypass. The retained
repair freezes the public receipt and its nested carriers and revalidates
copy-with-update. Independent verifier-native reruns confirm **32/32 focused
numeric** and **290/290 complete worker**. Their verifier-canonical test-ID-set
SHA-256 values are, respectively,
`12602041756f20d1afd402fa56968660839e5eb1098438ba84c69bff8de7050b`
and
`1c8db623fc6507db0b4ce218c3fd60833d514503122cd68fa79644a61db6c635`.
These are not raw pytest transcript digests. The verifier retains collection
lines containing `::`, strips whitespace, normalizes path separators to `/`,
de-duplicates them, sorts by Python ordinal order, and hashes the UTF-8
serialization of each `live-trace-worker/`-prefixed ID followed by LF,
including the final ID. Earlier hashes produced by culture-aware sorting or by
omitting the final LF are superseded and are not evidence. The earlier 255/257
receipts remain canonical checkpoints only for their earlier bounded bytes and
test surfaces. None of these receipts is a model-execution or scientific-result
receipt.

GPU, autocast/mixed-precision, compiled-module hook behavior, multi-device
comparability, and production-hardware determinism also remain untested external
boundaries.

### Manifest and verifier red team

The integrated verifier red team reproduced and retained five additional
fail-closed defects before the manifest was admitted:

- extra manifest records, unchecked artifact roles/counts, and rewritten OPEN
  boundary prose could coexist with the required records;
- review-matrix and model/security JSON could carry contradictory extra fields
  such as a second closed/licensed/execution-authorized status while all
  selected fields still passed;
- integer-valued fields could be replaced by equal JSON floating-point values;
- pytest could load an unbound ancestor `conftest.py`, caller-supplied import
  paths/options/plugins, or entry-point plugins while preserving the expected
  node-ID set; and
- files could change after their initial hash check because subprocesses ran
  before the verifier's final PASS without a postflight rehash.

The retained repair makes the v0.1 structured carriers extra-forbid, requires
exact scalar types, derives artifact roles from canonical paths, binds the
complete Gate 5 directory and every existing pytest discovery/configuration
candidate, disables unsolicited pytest plugin and environment injection, and
rehashes the Gate 5, 537-file historical, and transitive Gate 4 surfaces after
all subprocesses. Bound Markdown/JSON also rejects explicit contradictory
status conclusions while preserving its exact OPEN governance headers.

The postflight was also exercised by a real concurrent-write event: an
independent no-edit verifier began on one manifest while the root process added
the retained verifier regressions and rebuilt that manifest. After 126.3
seconds the independent process exited 1 with the error
`Gate 5 manifest changed during verification` and emitted no PASS. The final candidate requires a fresh
independent run on stable bytes; the failed-closed receipt is adverse evidence
that the non-atomic predecessor path is no longer silently accepted.

This is repository-local integrity, not authenticated or hermetic execution.
The installed interpreter and explicitly named worker pytest plugin are not
content-addressed; filesystem races cannot become trusted ordering without an
external WORM/locking authority; and a verifier controlled by the same writer
is not an independent signature or reviewer.

### Exact model-file identity and security hold

The worker's real-model predicate now requires:

- model `EleutherAI/pythia-160m`;
- exact repository commit
  `50f5173d932e8e61f858120bcb800b97af589f46`;
- exact `model.safetensors` byte count `374,998,696`;
- exact weights SHA-256
  `29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270`;
- successful fresh streaming hash verification; and
- typed status `PINNED_REVISION_AND_WEIGHTS_SHA256` with
  `execution_kind=real_model_weights`.

The canonical checkpoint records **257/257** complete worker tests and a local
cached-file match without model execution. This proves a weights-file identity,
not an in-memory tensor digest, authenticated execution, or scientific result.

The same checkpoint records a security hold: the Docker dependency set still
pins `transformers==4.46.3`, and the canonical dependency audit identifies that
version as affected by current advisories, including critical
`CVE-2026-4372` / `GHSA-29pf-2h5f-8g72`, with the cited fixed line at `5.3.0`.
All live or hosted Gate 5 execution therefore remains `HELD` until a patched
dependency/container set is digest-bound and the exact Pythia loader and hook
contract are revalidated in that environment.

## Historical V1-V4 review

The historical recovery is valuable evidence, but not a predecessor that can
be silently upgraded into v2.

The exact recovery inventory establishes:

- source revision `d9c1879762233855cd5974676b8179b1e4e75d16`;
- 537 exact files totaling 95,945,579 bytes;
- canonical inventory SHA-256
  `361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f`;
- 472 V3 raw-logit artifacts totaling 94,973,952 bytes with no per-record hash
  mismatch; and
- an independent recovery verifier passing **4/4**.

The same recovery deliberately preserves adverse evidence:

- the five-module model-free historical suite remains **43 passed, 4 failed**;
- the separately restored V1 worker suite remains **31 failed** because frozen
  fixture dependencies were outside the bounded supplement;
- V3's committed LF `result.json` and terminal CRLF expectation are distinct
  exact byte claims, classified
  `HISTORICALLY_INCONSISTENT / NOT_INDEPENDENTLY_BYTE_CLOSED / FAIL_CLOSED`;
- V3 remains
  `CONTROL_EFFECT_CEILING_FAIL:wrong_layer / NON_REUSABLE / NO RETRY`; and
- V4 retains its `ZeroNetworkGuard` versus `CompatibleZeroNetworkGuard`
  startup defect and remains
  `FAIL_CLOSED_PRE_RECEIPT / NO RECEIPT / NO NONCE / RUN_NOT_STARTED`.

These failures are preserved, not normalized into success. Evidence Packet v1
cannot be automatically upgraded because it lacks prospective v2 facts.

## Residual boundaries controlling the decision

### Trust, ordering, and authenticity

The kernel uses caller-declared UTC timestamps. It has no independently trusted
clock, durable append-only database, WORM anchor, nonce authority, one-use run
consumption, replay registry, or multi-packet selective-reporting guard. A
process-local chain can detect inconsistent mutation but cannot prove that an
earlier process did not inspect outcomes or suppress a run.

No non-caller-selected trust root authenticates an executor, auditor, reviewer,
or organization. Normalized distinct strings prevent simple aliases; they do
not prove human identity, affiliation, independence, competence, key custody,
revocation, or authorization. The packet intentionally has no `AUTHENTICATED`
path.

### Hermeticity and protocol integration

The live worker is not yet mapped into the kernel's exact preregistration,
outcome-access, executor/auditor, and packet protocol. There is no digest-bound
patched container receipt, OS/toolchain sandbox, network policy attestation,
trusted dependency closure, or independently verified environment attestation.
The Gate 5 matrix, manifest, builder, and executable verifier now bind and
rerun the exact Gate 4 manifest/verifier while preserving Gate 4's controlling
`OPEN / RING 4 / NOT LICENSED / HELD` boundary. This closes only a structural
dependency check; a Gate 4 structural PASS cannot be reinterpreted as semantic,
scientific, product, or disclosure acceptance. Installed dependency bytes,
runtime isolation, and authenticated execution remain outside this receipt.

### Semantic and scientific validation

Hashes establish byte identity, not semantic correctness. The power analysis,
split sources, labels, code, outcomes, receipts, and review artifacts still need
independent semantic inspection. Byte-different semantic clones or relabeling
across packets are not resolved by the process-local registry.

No admitted live exact-revision experiment has run through the v2 protocol. No
module has satisfied the charter's full combination of clean nulls,
matched-taxonomy and wrong-layer controls, falsifiers, independent numerical
agreement, held-out replication, and claim-language review. Causal
interpretation, generalization, utility, safety, and claim scope remain open.

### Product, licensing, and disclosure

`PacketAssessment` is evidence data, not an authority or capability token.
Downstream systems do not yet have an independently verified policy proving
that they always preserve that boundary.

Product readiness requires separate current evidence for security, operations,
accounts, billing, quotas, privacy, compliance, customer-data rights, safety,
support, and live-product behavior. Public disclosure additionally requires
explicit owner and qualified legal/patent approval of exact artifacts and exact
wording. None is supplied by this Gate 5 candidate.

## Closure order

The minimum defensible order is:

1. preserve the independently frozen verifier-native 32/32 focused and 290/290
   complete-worker receipts and every earlier counterexample;
2. patch and digest-bind the worker dependency/container set, then revalidate
   the exact model and hook contract, including GPU/autocast/compiled-hook
   behavior;
3. define and independently review the worker-to-kernel protocol;
4. materialize trusted time, nonces, one-use run consumption, durable WORM
   ordering, and selective-reporting controls;
5. preserve and independently red-team the exact Gate 4/Gate 5 manifests,
   builder, verifier, and postflight receipts without treating them as trust or
   semantic authority;
6. independently review the power analysis, data rights, labels, controls,
   analysis, and claim wording;
7. execute one separately authorized, exact-revision, hermetic private
   experiment with authenticated executor/auditor separation;
8. complete independent numerical replay, held-out replication, falsifier and
   control review, and external peer review; and
9. evaluate product and disclosure gates separately.

Until every applicable criterion is evidenced, Gate 5 remains
`OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`.
