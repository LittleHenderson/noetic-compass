# Gate 5 adversarial review v0.1

**Status:** `DRAFT / OPEN / NOT_STARTED / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

## Decision

**KEEP GATE 5 OPEN.** The Harness v2 research-control kernel, historical
recovery, and bounded live-worker repairs establish useful implementation and
negative-evidence controls. They do not establish authenticated execution,
trusted ordering, a live scientific result, independent numerical agreement,
replication, peer review, product readiness, licensing, or disclosure
authority.

The controlling charter status remains `OPEN / NOT_STARTED`. Control-kernel
engineering has begun, but none of the charter's per-module scientific closure
conditions has been satisfied by a live admitted experiment. No result in this
review creates `ACCEPT`, `LICENSED`, live-execution authority, a public route, a
product route, disclosure authority, scientific authority, or canon authority.
One CPU-only non-scientific engineering preflight canary occurred; it was not an
authorized or admitted experiment and created no GPU run, Evidence Packet, or
scientific result. Experimental execution remains `NOT_STARTED`.

## Exact review surface

This review is bounded to the following current surfaces:

- the isolated control kernel under `src/cas_harness_v2/`;
- the nominal and independent adversarial tests under `tests/cas_harness_v2/`;
- `HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md`;
- the current `live-trace-worker` model-identity and intervention-integrity
  controls;
- the successor dependency/container candidate receipt
  `GATE5_DEPENDENCY_AND_CONTAINER_CANDIDATE_RECEIPT_v0.2.json`;
- the additive raw build/security receipt
  `GATE5_RAW_BUILD_AND_SECURITY_EVIDENCE_RECEIPT_v0.1.json` and its ten retained
  payloads;
- the local runner lock `GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json`, the
  same-process pytest runner, and both deterministic builders;
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

The clean focused receipt is **119 passed tests plus 61 subtests** under Python
3.14 with startup site processing and bytecode/cache output disabled. It
contains 94 active-kernel tests, 4 historical-recovery tests, and 21 Gate 5
verifier red-team tests. The retained attacks cover hardlink/symlink aliasing,
same-byte inode replacement, a synthetic reparse attribute, duplicate or
noncanonical node IDs, raw-evidence security promotion, erasure of the
scanner/vendor conflict, duplicate normalized runner distributions, unbound
code inside a locked runner namespace, Python-root import shadowing, and
lock-byte replacement before parsing. The stable-observer regression also
confirms that metadata-only ancestor timestamp churn is not misclassified as
object substitution while structural ancestor replacement remains detected.
The receipt is limited to
`tests/cas_harness_v2`; it is not a repository-wide or production receipt.
Its same-process executed-node SHA-256 is
`8FBC5D8AE4CF3B0BBEB9A1902C6905278126B056FF6961D13EE9830E2363F362`.

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
copy-with-update. The successor candidate retains the **32/32 focused numeric**
receipt and confirms **364/364 complete worker**. Their verifier-canonical
test-ID-set
SHA-256 values are, respectively,
`12602041756f20d1afd402fa56968660839e5eb1098438ba84c69bff8de7050b`
and
`94566203b3e0ff79b3224c1c5a073698ca99d3c08bc1119a9082e42af4b178bd`.
These are not raw pytest transcript digests. One pytest process must report
identical duplicate-free collected, started, and finished sequences, exact
setup/call/teardown PASS outcomes, and separately passing subtests. The parent
normalizes path separators to `/` without Unicode normalization, sorts by
Python ordinal order, and hashes the UTF-8 serialization of each
`live-trace-worker/`-prefixed ID followed by LF, including the final ID.
Earlier hashes produced by culture-aware sorting or by omitting the final LF
are superseded and are not evidence. The independently
confirmed 290/290 receipt and the earlier 255/257 receipts remain canonical
checkpoints only for their earlier bounded bytes and test surfaces. The
successor API/launcher/fleet/state suite also passes **76/76**, with canonical
node-ID-set SHA-256
`1ed1e9e3afa2eda6881463ee5284dd4902ab94c0246b80d2937066480ac42921`.
The 364-test worker and 76-test API/launcher/fleet/state results are
`LOCAL_UNATTESTED_HOST_REGRESSION` observations. Their same-process receipts
bind executed node IDs and exact outcomes. The child starts with `-I -S -B`, a
fresh bytecode-cache prefix, disabled plugin autoload, and exact pre-admitted
repository import roots. The local lock binds three interpreter files, seven
runner distributions containing 508 exact file records, and three inventoried
`.pth` files whose startup execution is disabled. Pytest and explicit plugin
origins are checked against that per-file lock before import, and the child
hashes and parses the same stable lock bytes. The endpoint module inventory
contains only surviving `sys.modules` file origins, maps `.pyc` paths back to
source, and misses transient/unloaded/dynamic execution, unresolved or deleted
origins, native-loader dependencies, and child processes. Distribution files
absent from upstream `RECORD` also remain outside the lock. The standard
library, complete test/native/descendant closure, kernel/filesystem trust, and
independent attestation remain OPEN. None of these receipts is authenticated
execution, a GPU
model-execution receipt, or a scientific-result receipt.

GPU, autocast/mixed-precision, compiled-module hook behavior, multi-device
comparability, and production-hardware determinism also remain untested external
boundaries.

### Manifest and verifier red team

The integrated verifier red team first reproduced and retained five
fail-closed defect classes before the manifest was admitted:

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

The successor hardening then retained six more attacks:

- hardlinked and symlinked artifacts could alias admitted path bytes;
- same-byte pathname replacement could evade a digest-only postflight;
- a Windows reparse attribute could be hidden behind non-symlink semantics;
- duplicate or noncanonical node IDs could be collapsed into a plausible set;
- raw-evidence fields could be promoted into security acceptance; and
- the six-plus-one vendor disposition could be rewritten to erase the
  `dpkg` scanner/vendor conflict.

The retained repair makes the v0.1 structured carriers extra-forbid, requires
exact scalar types, derives artifact roles from canonical paths, binds the
complete Gate 5 directory and every existing pytest discovery/configuration
candidate, disables unsolicited pytest plugin and environment injection, and
observes the Gate 5, 537-file historical, and transitive Gate 4 surfaces before
and after all subprocesses. Stable reads reject symlink/reparse components and
hardlinked leaves, compare pathname and opened-handle identity, hash through
that handle, and retain ancestor identities. Bound Markdown/JSON also rejects
explicit contradictory status conclusions while preserving its exact OPEN
governance headers.

The broad active-surface LF rules in `.gitattributes` are followed by specific
`-text` exceptions for `api/services/cas_harness_pythia160m_*.py`,
`api/services/cas_harness_research_intervention_worker.py`,
`tests/test_cas_harness_pythia160m_*.py`, and
`tests/test_cas_harness_research_intervention_worker.py`. Because those
historical worker source blobs are already LF, the later exceptions deliberately
preserve their original Git bytes without checkout conversion while the
Gate 5 direct-or-transitive hash closure continues to bind them.

The postflight was also exercised by a real concurrent-write event: an
independent no-edit verifier began on one manifest while the root process added
the retained verifier regressions and rebuilt that manifest. After 126.3
seconds the independent process exited 1 with the error
`Gate 5 manifest changed during verification` and emitted no PASS. The final candidate requires a fresh
independent run on stable bytes; the failed-closed receipt is adverse evidence
that the non-atomic predecessor path is no longer silently accepted.

This is repository-local integrity and same-process regression evidence, not
authenticated or hermetic execution. The local runner lock and descriptor-based
observer close the former separate-collection ambiguity and ordinary repository
alias/replacement paths. They do not bind transient/unloaded/dynamic imports,
exact loader-executed bytecode, unresolved or deleted module origins, the
complete standard library, test/native/descendant-process closure, immutable
snapshot, privileged or metadata-preserving ABA resistance, hosted/auxiliary
model-loader aliases, kernel/filesystem trust, or external WORM ordering. Those remain `OPEN` under
`G5-ENGINEERING-002`. A verifier controlled by the same writer is not an
independent signature or reviewer.

### Exact model-file identity and successor security candidate

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

The historical v0.1 binding records the prior security hold: its Docker
dependency set pins `transformers==4.46.3`, and the canonical dependency audit
identifies that version as affected by current advisories, including
`CVE-2026-4372` / `GHSA-29pf-2h5f-8g72`, with the cited fixed line at `5.3.0`.
That record remains unchanged adverse evidence.

The time-indexed successor v0.2 receipt binds its repository source/build controls to source
commit `4bff437dbcf6d0d38046e63d2aee823e8f316711`, records a 73-distribution
hash-bound lock with `transformers==5.14.1`, and records locally observed exact
Ubuntu/Python base-image and OCI index identifiers:
`sha256:3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c`,
linux/amd64 manifest
`sha256:60bf92b327ebec84887c659313a97a6369a24fd5d8eb00a012544fcafd26ba27`,
image config, BuildKit SPDX SBOM, and SLSA provenance identifiers. At issuance,
the raw build history, SPDX payload, SLSA payload, and Scout report were not
retained or repository replayable. That historical statement remains unchanged,
and those external-tool facts are `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`. The exact five-file Pythia
artifact set was locally hashed before and after load. One CPU-only,
non-scientific engineering preflight loaded it and ran the offline
geometry/numerics canary; a 385-object native closure with only the declared
host `libcuda.so.1` seam, no-network/read-only runtime preflight, and fail-closed
no-token and no-CUDA startup probes were also locally observed. This did not
authorize or admit an experiment and created no GPU run, Evidence Packet, or
scientific result; experimental execution remains `NOT_STARTED`.

The later additive raw-evidence receipt retains ten exact payloads: the OCI
index/config/manifests, BuildKit history bundle, original SPDX and SLSA
statements, and a current direct Scout 1.21 SPDX and SARIF report. Retaining the
bytes does not replay the complete tool execution or provide an independent
trust root.

This is a materially stronger candidate, not security closure. `pip-audit`
completed for 72 lock entries with zero findings but skipped the direct-URL
Torch entry; a separate OSV query returned zero results for the exact Torch
package/version. The historical Docker Scout 1.24.0 observation has no retained
raw report. The current direct Scout 1.21 scan is retained and reports
`COMPLETED_WITH_FINDINGS` with 0 critical, 0 high, 3 medium, and 4 low findings:
`CVE-2026-27456`, `CVE-2026-13757`, `CVE-2026-2219`, `CVE-2026-27171`,
`CVE-2024-2236`, `CVE-2024-56433`, and `CVE-2026-40228`. Current vendor triage
classifies six as vulnerable or fix-deferred and one as a scanner/vendor
conflict because the exact scanned `dpkg` version is vendor-fixed. The scanner
database identity and complete process transcript are not retained. No scan
PASS, real GPU forward, independent clean build, independent provenance trust
root, or independent security receipt exists.
`G5-ENGINEERING-003` therefore remains `OPEN_SECURITY`,
`live_execution_authorized=false`, and all live or hosted Gate 5 execution
remains `HELD`.

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
outcome-access, executor/auditor, and packet protocol. The v0.2 successor now
provides a digest-bound patched container candidate, exact build controls,
and a locally observed offline preflight plus BuildKit SBOM/provenance
identifiers. The later receipt retains ten exact raw payloads and a current
direct scan, but does not replay the complete tool execution or establish an
independent trust root. The SARIF does not embed the candidate identity or its
invocation, and the linked Ubuntu vendor pages were not snapshotted. It does not
provide a scan PASS, real GPU execution, a separately controlled clean
reproduction, or an independently verified environment attestation.
The Gate 5 matrix, manifest, builder, and executable verifier now bind and
rerun the exact Gate 4 manifest/verifier while preserving Gate 4's controlling
`OPEN / RING 4 / NOT LICENSED / HELD` boundary. This closes only a structural
dependency check; a Gate 4 structural PASS cannot be reinterpreted as semantic,
scientific, product, or disclosure acceptance. Authenticated execution remains
outside this receipt. The bounded lock and runtime-isolation receipts do not
establish independent hermeticity. The local same-process receipt, runner lock,
and descriptor observer bind a stronger repository-local surface, but the
same-run JSON is ephemeral and not WORM-retained. The controls do not bind the
transient/unloaded/dynamic import history, exact loader-executed bytecode,
complete standard-library/test/native/descendant closure, immutable read-only
snapshot, privileged ABA resistance, hosted/auxiliary loader aliases, or
kernel/filesystem trust. Those remain `OPEN` under `G5-ENGINEERING-002`.

### Semantic and scientific validation

Hashes establish byte identity, not semantic correctness. The power analysis,
split sources, labels, code, outcomes, receipts, and review artifacts still need
independent semantic inspection. Byte-different semantic clones or relabeling
across packets are not resolved by the process-local registry.

One CPU-only engineering preflight canary occurred outside the admitted
experimental protocol. No authorized or admitted live exact-revision experiment
has run through v2, and no GPU run, Evidence Packet, or scientific result was
created. No module has satisfied the charter's full combination of clean nulls,
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

Accordingly, `live_execution_authorized=false`, public and product routes remain
false, scientific and canon effects remain `NONE`, the claim remains `NOT
LICENSED`, and disclosure remains `HELD`.

## Closure order

The minimum defensible order is:

1. preserve the verifier-native 32/32 focused, 364/364 complete-worker, and
   76/76 API/launcher/fleet/state receipts, the earlier 290/290 checkpoint, and
   every counterexample, including the current ephemeral same-process and
   retained raw-evidence validations;
2. preserve and independently reproduce the patched digest-bound v0.2
   dependency/container candidate, remediate or explicitly disposition the six
   vendor-confirmed vulnerable/fix-deferred records, reconcile the `dpkg`
   scanner conflict, capture complete scanner-process and vendor-source
   evidence, and revalidate the exact model and hook contract under real
   GPU/autocast/compiled-hook behavior;
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
`OPEN / NOT_STARTED / RING 4 / NOT LICENSED / HELD / NOT FROZEN`.
