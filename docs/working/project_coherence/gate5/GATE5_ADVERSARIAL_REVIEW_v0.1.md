# Gate 5 adversarial review v0.1

Document status: `DRAFT / OPEN / NOT FROZEN`

Decision status: `OPEN / KEEP_OPEN`

Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`

Experimental execution status: `NOT_STARTED`

License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`

Live / product route status: `unavailable / not authorized`

## Decision

**KEEP GATE 5 OPEN.** The Harness v2 research-control kernel, historical
recovery, and bounded live-worker repairs establish useful implementation and
negative-evidence controls. They do not establish authenticated execution,
trusted ordering, a live scientific result, independent numerical agreement,
replication, peer review, product readiness, licensing, or disclosure
authority.

The decision remains `OPEN / KEEP_OPEN`, while engineering has reached
`RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED` and experimental execution remains
`NOT_STARTED`. None of the charter's per-module scientific closure conditions
has been satisfied by a live admitted experiment. No result in this review
creates `ACCEPT`, `LICENSED`, live-execution authority, a public route, a product
route, disclosure authority, scientific authority, or canon authority.
One CPU-only non-scientific engineering preflight canary occurred; it was not an
authorized or admitted experiment and created no GPU run, Evidence Packet, or
scientific result. Experimental execution remains `NOT_STARTED`.

## Exact review surface

This review is bounded to the following current surfaces:

- the isolated control kernel under `src/cas_harness_v2/`;
- the nominal and independent adversarial tests under `tests/cas_harness_v2/`;
- `HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md`;
- the research-only worker protocol candidate
  `GATE5_WORKER_PROTOCOL_BINDING_v0.1.md`, its strict carriers, dark API
  bridge, same-host prospective lifecycle registry, exact-wrapper service,
  default-dark/OpenAPI-hidden router, request-bound callback-auth projection,
  admitted packaged adapter, controller reconciliation-report path,
  active-lease validation seam, and synthetic immutable-storage seam;
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
`project_coherence.gate5_review_matrix.v0.1`. It contains **50 criteria**:

- 21 `IMPLEMENTED_AND_REGRESSION_TESTED`;
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

The bounded candidate exposes five public schema families:

| Artifact | Exact schema |
|---|---|
| Per-claim preregistration | `cas_harness_v2.preregistration.v1` |
| Preregistration amendment | `cas_harness_v2.preregistration_amendment.v1` |
| Worker authorization | `cas_harness_v2.worker_authorization.v1` |
| Worker terminal receipt | `cas_harness_v2.worker_terminal_receipt.v1` |
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

The clean focused receipt is **150 passed tests plus 99 subtests** under Python
3.14 with startup site processing and bytecode/cache output disabled. It
contains 94 active-kernel tests, 30 strict worker-protocol tests, 4
historical-recovery tests, and 22 Gate 5 verifier red-team tests. The retained
attacks cover hardlink/symlink aliasing,
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
`6BF70F5569C4BCA5B7D896382A099FC966E9C0622B3A3694BE0B330B66048756`.

## Worker-protocol adversarial chronology

The first strict carrier draft matched the current FleetJob layer range,
shard, ordered method/output, and exact model-lease fields, but an independent
adversarial pass reproduced four integration defects:

1. it placed the transport callback nonce in worker-authored terminal bytes,
   although the live client creates that nonce only when posting and an exact
   authenticated retry must use a fresh transport nonce;
2. it could parse a terminal only before outcome access, so the exact retained
   carrier could not be replayed after its own outcome-access seal;
3. it rejected every produced artifact on `FAILED`, erasing the live worker's
   possible partial-produced plus missing plus error facts; and
4. the dark API adapter accepted injected loader ports and could retain exact
   bytes, but duck typing alone could not prove that the injected functions
   were the root strict loaders.

The retained repair keeps all transport callback-nonce facts out of immutable
worker authorization and terminal carriers. After callback authentication, the
server-authored nonce receipt is bound instead to the private acceptance
wrapper and durable per-authorization index. Stable terminal bytes can
therefore be retried with a fresh HTTP-attempt nonce, while the fleet auth store
continues to reject reuse of one callback nonce. This transport control is not
the separate independently authenticated, replica/host-loss-resistant one-use
run authority required by `G5-TRUST-003`; the later same-host lifecycle
candidate does not close that requirement.

The terminal loader now supports verification from exact authorization bytes
after sealing only when the process-local OutcomeAccessEvent binds that exact
terminal artifact reference and the same execution-completion time. The public
authorization loader remains closed after outcome access. `COMPLETED` outputs
must carry `DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED`; `FAILED` outputs and
missing names must form the exact ordered expected-output partition and any
produced artifacts carry
`QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY`. A failed run therefore retains
negative evidence without minting a scientific result.

The strict worker subset passes **30 tests plus 38 subtests**, with canonical
node-ID SHA-256
`534CF4550FF56F3EA5F4235680CDB89A91784D1CEE0B7CB7ABDF9DE1C7B3E7FF`.
These are local structural regressions. Loader provenance remains an explicit
unresolved deployment trust boundary. The packaged adapter is admitted only as
a bounded local candidate; it has no provider-backed production startup,
authorized live route, or independent live-worker replay.
`G5-ENGINEERING-001` therefore remains `OPEN_ENGINEERING`.

A second read-only adversarial pass confirmed the nonce chronology and partial-
failure repairs, then caught three documentation overclaims. The specification
now distinguishes the authorization's outcome-null chain digest, the outcome
event's differently schemed sealed-pre-outcome digest, and the packet's final
post-outcome chain digest. It limits exact carrier-type enforcement to the root
loaders and keeps injected bridge provenance OPEN. The later sealed-safe replay
port repairs the former pre-outcome-only bridge defect: a retained exact
terminal can now replay after an exact seal binding the same terminal artifact
and completion time. The public authorization loader remains closed after
outcome access. The packaged HTTP adapter now uses the sealed-safe lifecycle
replay port, but no provider-backed live replay or independent authority follows
from that local repair.

### Durable prospective lifecycle P0 review

The successor adds useful local controls while keeping the release blocker
explicit:

- authorization cannot be created retroactively at terminal intake. The
  registry reserves the subject and run-nonce digest before calling the builder;
  the raw server nonce is returned only on the winning issuance, and an
  interrupted builder leaves a quarantined, reconciliation-visible reservation.
  The default factory is `secrets.token_bytes(32)`, but the constructor accepts
  an injected callable and no admitted runtime attests that factory provenance;
- callback nonce reuse is not merely credential-scoped. The v2 row binds the
  server-observed method, exact path, job/run IDs, authorization digest when
  required, and carrier digest/length for every accepted route request. That
  authentication row is not the bridge's immutable acceptance wrapper/index:
  only terminal submissions traversing the bridge create the latter. The
  admitted adapter now carries the enclosing request-bound receipt through the
  lifecycle, and the bridge revalidates its exact callback and intake binding;
- consumption uses a same-host `StateStore` compare-and-swap and a server-built
  digest-only envelope. The admitted adapter passes the raw lease capability
  process-locally to the active-lease validator, which checks the exact current
  lease generation, worker, model, token digest, and expiry before consumption;
- terminal intake reloads the prospective authorization and cannot submit a
  second authorization body at the lifecycle-service boundary. The HTTP route
  treats the body as opaque bytes, and the admitted adapter invokes the strict
  lifecycle/bridge loaders to establish terminal-only semantics.
  Retained output bodies are required to match the terminal's exact references;
  packet attachment strict-loads Packet v2, validates the full supplied
  transitive body set, rebuilds the artifact registry, and runs the structural
  verifier before its first repository write. A later storage failure can still
  leave already written dependency or Packet wrappers outside the event chain;
- the orchestration service retains wired `SUCCESS`/`FAILURE`, reserves
  outcome-access time before chain mutation, and requires a typed server-built
  nonreporting envelope for failure instead of a favorable packet. The lower
  registry and lifecycle service can record typed
  `INDETERMINATE`/`REJECTED`/`EXPIRED` dispositions, but the admitted worker
  adapter/router exposes no path for them; and
- tenant reconciliation verifies the event hash chain and event-bound wrappers.
  It does not enumerate losing/orphan wrapper writes or every output retained
  while a run remains `RUNNING`, and it cannot prove that an off-registry run
  did not occur. An entirely empty tenant view yields
  `has_registered_runs=false`, zero counts, and
  `all_runs_reporting_disposed=false`; an issue-free result over that empty view
  is not positive evidence of execution absence.

### Controller continuation adversarial review

The successor closes a narrower missing HTTP tranche without changing the gate
decision. Dedicated controller capabilities now admit exact outcome-seal,
Packet-v2 attachment, and explicit-nonreporting envelopes. Review reproduced
and retained regressions for the following failure classes:

1. a fresh HTTP request could begin with a new in-memory chain that lacked an
   already retained outcome event;
2. Packet and nonreporting callers could race without a common create-only
   disposition intent;
3. a reporting reservation did not initially bind the exact planned final
   artifact;
4. request retries could observe different process times or poison a future
   reservation with a backward declared time;
5. raw indexed events could be read without first replaying the full lifecycle;
6. continuation responses omitted fields needed to construct the next exact
   request, encouraging callers to guess or resubmit server-owned bytes;
7. duplicate security/entity headers and transfer encoding could create an
   ambiguous signed-body boundary; and
8. reconciliation returned an outer receipt ID paired with an inner report
   digest and did not retain the strict per-run replay binding;
9. nonreporting finalization could declare a reason different from the winning
   reporting reservation while still reconciling as structurally valid;
10. `RUNNING` and terminal events could move backward in declared time before
   the already-protected outcome/reporting edges; and
11. an event-first/index-second interruption was recoverable by an exact raw
   registry retry but could fail before repair through the admitted lifecycle
   service.

The repaired path reloads the retained authorization, terminal, outcome, and
dependency facts for each request; records one winning untrusted clock
observation; uses a create-only `PACKET`-versus-`NONREPORTING` reservation bound
to request, dependency plan, parent head, clock observation, and planned final
artifact; rejects competing or mismatched finalization; and verifies the full
lifecycle before event reads. Exact duplicate entity/security headers and any
transfer encoding fail before authentication-nonce consumption. Reconciliation
now returns a coherent content-addressed wrapper receipt and embeds separately
hashed strict-run and configured-scope report identities. A forged report with
a non-content-derived report ID is rejected before storage, and an evolved run
gets a new receipt while the prior immutable snapshot remains verifiable. The
winning nonreporting reason is now reservation-bound (`null` is required for a
Packet reservation), all event transitions and stored-history replay enforce
canonical nondecreasing time, and controller reads repair exactly one verified
pending successor while corrupt or divergent successors fail closed.

The route-to-real-adapter regression traverses authorization, consumption,
output, terminal, outcome, and explicit nonreporting through the FastAPI
boundary while the feature remains default-dark. This is still local software
evidence. The lower registry outcome reservation does not yet carry a separate
planned-final-artifact intent, output-retention response replay is not yet
distinguished, the three non-success/failure terminal-disposition routes remain
unwired, and provider, cross-host, host-loss, trusted-time, independent WORM,
off-registry, and scientific authority remain absent.

The route hashes `job_id` into its prospective run ID. The lifecycle hashes
`subject_id`, while the lifecycle service separately requires
`subject_id == authorization_id`. The admitted adapter now enforces the
necessary `job_id == subject_id == authorization_id` contract before lifecycle
use. This establishes the bounded software identity mapping, not an executor
identity attestation.

The SQLite tests show close/reopen persistence for one file and
compare-and-swap arbitration between two independent connections to that same
file. They do not inject a process crash, OS restart, power loss, filesystem
fault, or storage-device failure; WAL with `synchronous=NORMAL` does not turn
those untested cases into evidence.

The HTTP router itself remains default-false, absent from OpenAPI, and
fail-closed without a lifespan service. Main initializes that service to
`None`, then constructs the exact admitted adapter only when the byte-verified
packaged kernel, shared state, immutable repository, and fleet-auth ports are
available. Local import, factory, and startup-boundary tests establish
constructibility, but no provider-backed enabled startup has passed. Therefore
the route remains unavailable and not authorized as a public, product, or
live-execution route. The remaining deployment and trust seams keep
`G5-ENGINEERING-001` and `G5-TRUST-002/003/004` open.

The current bounded local receipts are **17/17** for the worker-terminal bridge
(`fa6c985cd6caa734034e006bb4baf6be9d02269d7312bee7355e9c3833759c51`),
**38/38** for the callback/Object-Lock seam
(`d3eaf533fedb5b03168200aa399ac53a6e2a6f22874ebabeaecefb227400778d`),
**97/97** for the prospective lifecycle/SQLite/default-dark route suite
(`727f58cc716f5add0bab8fb965cc1e6b68245e60db6c160a33af96ed9ec5e5f9`),
and **90/90** for packaging, snapshot, envelope, context, admitted-adapter,
and bounded-reconciliation tests
(`761038779e00511179d4fc5aa3522829d9bdefb37c231061d04fb3aad541f733`).
They are `LOCAL_UNATTESTED_HOST_REGRESSION`, not live or scientific evidence.

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
successor API/launcher/fleet/state suite also passes **78/78**, with canonical
node-ID-set SHA-256
`603debf7df9ac7b5a69543c3736f4cd38692d3330690a7559a6f9de6f0e2af77`.
The 364-test worker and 78-test API/launcher/fleet/state results are
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

The kernel uses caller-declared UTC timestamps. The successor has a same-host
SQLite compare-and-swap profile, a default `secrets.token_bytes(32)` nonce
factory that remains injectable and unattested, local one-use
consumption, event hash chain, and tenant-visible lifecycle reconciliation.
Those are not an independently trusted clock, replicated append-only database,
WORM anchor, authenticated execution authority, host-loss-resistant nonce
authority, or independently complete selective-reporting guard. A local chain
can detect inconsistent mutation but cannot prove that an earlier or external
process did not inspect outcomes, execute off-registry, or suppress a run.

No non-caller-selected trust root authenticates an executor, auditor, reviewer,
or organization. Normalized distinct strings prevent simple aliases; they do
not prove human identity, affiliation, independence, competence, key custody,
revocation, or authorization. The packet intentionally has no `AUTHENTICATED`
path.

### Hermeticity and protocol integration

Strict worker carriers, a dark bridge, a same-host lifecycle registry, and an
exact-wrapper service now map the current FleetJob shape through local
authorization, consumption, terminal, outcome-access, Packet-v2/nonreporting,
and reconciliation candidates. The admitted packaged adapter now joins exact
Fleet snapshots, joint run identity, active-lease validation, request-bound
terminal intake, controller-only outcome/Packet/nonreporting continuations,
strict lifecycle replay, and a bounded reconciliation report. Three registry
terminal states still have no admitted worker route, reconciliation does not
enumerate every orphan wrapper or off-registry run, and lower-level outcome
finalization still lacks a separately immutable planned-artifact intent. Main
refuses enabled startup without the
byte-verified root package, exact adapter profile, shared state, immutable
repository, and fleet-auth ports. This has been constructed only in local tests;
no provider-backed application startup has passed. Trusted time, live
independent Object Lock, multi-host/host-loss proof, authenticated execution,
and independent executor/auditor replay remain absent. The v0.2 successor
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

Hashes establish byte identity, not semantic correctness. The structural
verifier checks declared schemas, required language, byte identity, and local
regression outcomes; it cannot authenticate whether document/data content is
true or establish scientific validity. The power analysis, split sources,
labels, code, outcomes, receipts, and review artifacts still need independent
semantic inspection. Byte-different semantic clones or relabeling across
packets are not resolved by the same-host lifecycle registry.

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

Accordingly, `live_execution_authorized=false`; the private default-dark route
code creates no admitted public or product route; scientific and canon effects
remain `NONE`; the claim remains `NOT LICENSED`; and disclosure remains `HELD`.

## Closure order

The minimum defensible order is:

1. preserve the verifier-native 150-test/99-subtest Harness-v2,
   30-test/38-subtest worker-protocol, 17/17 dark-bridge, 38/38
   callback/Object-Lock seam, 97/97 prospective lifecycle/SQLite/dark-route,
   90/90 admitted-adapter/configured-reconciliation,
   32/32 focused numeric, 364/364 complete-worker, and 78/78
   API/launcher/fleet/state receipts, the earlier 290/290 checkpoint, and every
   counterexample, including the current ephemeral same-process and retained
   raw-evidence validations;
2. preserve and independently reproduce the patched digest-bound v0.2
   dependency/container candidate, remediate or explicitly disposition the six
   vendor-confirmed vulnerable/fix-deferred records, reconcile the `dpkg`
   scanner conflict, capture complete scanner-process and vendor-source
   evidence, and revalidate the exact model and hook contract under real
   GPU/autocast/compiled-hook behavior;
3. independently review, reproduce, and provider-start the packaged
   worker-to-kernel candidate; independently replay the admitted outcome and
   Packet/nonreporting routes, finish the remaining terminal dispositions and
   lower-level outcome-finalization intent, then replace configured-scope
   reconciliation with provider-backed cross-host completeness before any live
   authorization;
4. replace the same-host SQLite/synthetic-wrapper seams with independently
   authenticated time and run authority, replicated/host-loss-resistant one-use
   consumption, live inner-byte/WORM ordering, and independently complete
   selective-reporting controls;
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

Until every applicable criterion is evidenced, the six axes remain: document
`DRAFT / OPEN / NOT FROZEN`; decision `OPEN / KEEP_OPEN`; engineering
`RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`; experiment `NOT_STARTED`;
license/disclosure/canon `NOT LICENSED / HELD / NOT FROZEN`; and live/product
route `UNAVAILABLE / NOT AUTHORIZED`.

The `$107.00` RunPod balance is user-reported. No provider billing ledger or
balance receipt was inspected, no RunPod/GPU/paid job was launched, and known
spend for this tranche is `$0.00`.
