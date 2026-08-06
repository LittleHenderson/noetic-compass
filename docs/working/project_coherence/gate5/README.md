# Project Coherence Gate 5

Document status: `DRAFT / OPEN / NOT FROZEN`

Decision status: `OPEN / KEEP_OPEN`

Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`

Experimental execution status: `NOT_STARTED`

License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`

Live / product route status: `unavailable / not authorized`

Gate 5 is the private research-control integration lane for CAS Harness v2. It
binds the prospective preregistration and Evidence Packet v2 kernel, the
bounded live-worker model/intervention controls, and the exact historical
V1-V4 recovery. It does not admit a scientific result, authorize an
experiment, license a claim, create a product route, or authorize disclosure.
It creates no live-execution, canon, product, license, disclosure, or scientific
authority.

## Control artifacts

- `HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md` defines the
  isolated executable control-kernel boundary.
- `GATE5_WORKER_PROTOCOL_BINDING_v0.1.md` defines the research-only exact
  worker-authorization, prospective lifecycle, terminal, outcome-access,
  packet/nonreporting, and reconciliation mapping. It distinguishes local
  same-host compare-and-swap controls from still-OPEN authenticated execution,
  trusted time, independent WORM ordering, and host-loss authority.
- `history/HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json` binds the exact
  537-file historical recovery and its adverse evidence.
- `history/HISTORICAL_HARNESS_V1_V4_RECOVERY_INVENTORY.md` explains the
  recovery scope and preserved failures.
- `GATE5_REVIEW_MATRIX_v0.1.json` records implemented, preserved-negative, and
  OPEN criteria without converting repository tests into acceptance.
- `GATE5_ADVERSARIAL_REVIEW_v0.1.md` records reproduced defects, repairs, and
  residual boundaries.
- `GATE5_MODEL_AND_DEPENDENCY_BINDING_v0.1.json` records the exact Pythia
  weights-file identity and the historical `transformers==4.46.3`
  container/dependency security hold. It remains unchanged adverse evidence.
- `GATE5_DEPENDENCY_AND_CONTAINER_CANDIDATE_RECEIPT_v0.2.json` records the
  successor patched dependency lock, repository source controls, locally
  observed OCI identities, BuildKit SPDX/SLSA identifiers, offline model/native
  preflight, fail-closed runtime probes, bounded audits, and every remaining
  `OPEN_SECURITY` item. Its external-tool evidence effect is
  `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`.
- `GATE5_RAW_BUILD_AND_SECURITY_EVIDENCE_RECEIPT_v0.1.json` is the later,
  additive receipt for ten repository-retained OCI, BuildKit, SPDX, SLSA, and
  Scout payloads. It makes those exact bytes locally replayable without making
  the original tool execution, scanner database, or trust chain replayable.
- `GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json` records the local Python and
  pytest content lock. Its exact scope is `LOCAL_CONTENT_LOCK /
  SELF-OBSERVED / NOT HERMETIC / NOT INDEPENDENTLY ATTESTED`.
- `GATE5_ARTIFACT_MANIFEST_v0.1.json` is the non-self-hashing exact artifact
  and test receipt manifest.
- `scripts/build_project_coherence_gate5_manifest.py` deterministically builds
  that manifest from the closed surface.
- `scripts/build_project_coherence_gate5_runner_lock.py` deterministically
  drafts the local runner lock and fails drift within its exact
  distribution-`RECORD` surface. Files absent from those upstream inventories
  and transient execution remain part of the explicit OPEN boundary.
- `scripts/run_project_coherence_gate5_pytest.py` runs one suite and emits its
  same-process collection, execution, and outcome receipt.
- `scripts/verify_project_coherence_gate5.py` verifies the complete bounded
  surface and re-runs its dependencies and tests.

## Current dark prospective lifecycle successor

The successor now joins bounded local controls without promoting any of them to
live or independent authority:

1. `cas_harness_v2_run_lifecycle.py` reserves a run subject and nonce digest
   before authorization construction, returns the raw nonce only once, records
   one-use consumption, retains terminal states including
   failure/indeterminate/rejected/expired, and hash-links outcome-access,
   packet, or explicit nonreporting transitions. The default nonce factory is
   `secrets.token_bytes(32)`, but the constructor accepts an injected callable
   and no admitted runtime attests which factory was used. Reconciliation is
   limited to record kinds visible in that tenant's configured `StateStore`.
   The lifecycle service can record typed indeterminate/rejected/expired server
   dispositions, but the admitted worker adapter/router does not expose those
   paths. An entirely empty
   tenant view returns `has_registered_runs=false`, zero counts, and
   `all_runs_reporting_disposed=false`; its issue-free structural result is not
   evidence that no execution occurred.
2. The tested SQLite profile provides close/reopen persistence and
   compare-and-swap arbitration between two independent connections to one
   database file on one host. It does not test process-crash, OS-restart,
   power-loss, filesystem, or storage-device durability. It explicitly reports
   multi-host support, host-loss survival, and independent attestation as
   unavailable or not established. This is not a WORM authority and cannot
   prove that an unregistered execution never occurred.
3. `cas_harness_v2_lifecycle_service.py` retains exact inner carrier bytes in
   typed repository wrappers; server-builds consumption and nonreporting
   envelopes; verifies retained output bodies and transitive packet references;
   reserves outcome-access time before mutating the chain; and reconciles the
   event-bound authorization, consumption, terminal, outcome, and
   packet/nonreporting wrappers plus packet-referenced bodies. Packet attachment
   validates all supplied dependency bytes and the structural Packet result
   before its first repository write. A later dependency or Packet storage
   failure can nevertheless leave already written wrappers outside the event
   chain; current reconciliation does not enumerate those losing/orphan writes
   or every output retained while a run remains `RUNNING`. Repository receipts
   attest the synthetic outer wrapper in current tests, not the inner carrier
   directly or a live independent Object-Lock provider.
4. `cas_harness_v2_worker_protocol.py` defines private exact-body HTTP handlers
   for authorization, output retention, consumption, terminal, packet,
   nonreporting, and reconciliation. Every accepted route request creates a
   durable authentication nonce row binding the observed method, exact path,
   job/run identity, authorization digest when applicable, and carrier
   digest/length. That row is distinct from the bridge's immutable
   callback-acceptance wrapper/index, which exists only for terminal submissions.
   The admitted packaged adapter passes the exact terminal carrier through the
   strict lifecycle/bridge loaders and preserves the request-bound intake
   receipt through terminal acceptance. Customer JWT fallback is forbidden.
   These are bounded software bindings, not live-worker authentication.

The admitted adapter now hands the raw lease token only to the lifecycle's
exact active-lease validator, which checks the current process-local
job/worker/model/token/expiry generation before consumption and retains only a
digest fence. The terminal route's request-bound receipt is preserved and
revalidated across route, adapter, lifecycle, and bridge. These controls do not
establish multi-host lease authority, trusted time, or authenticated execution.

The route derives `run_id` from `job_id`, while the lifecycle derives it from
`subject_id` and the service separately requires
`subject_id == authorization_id`. The admitted adapter now enforces the joint
identity contract `job_id == subject_id == authorization_id` before lifecycle
use. That bounded identity check is not an executor identity attestation.

That HTTP router is **default-dark**, excluded from OpenAPI, and returns a dark
or unavailable response unless an admitted lifespan service is injected. The
main application initializes that service to `None`, then constructs the exact
admitted adapter only when the feature is enabled and shared state, immutable
repository, and fleet-auth ports are present. The API image now contains a
byte-verified packaged `cas_harness_v2` mirror and startup rejects any other
adapter type or admission profile. Local import, factory, and startup-boundary
tests establish constructibility only. No positive provider-backed application
startup, enabled deployment, public/product route, or live execution has been
authorized or observed. Explicit HTTP outcome sealing, live Fleet execution,
trusted time, and independently controlled storage remain unfinished.

## Current bounded receipts

The stable Harness v2 suite contains 150 pytest node IDs and passes 150 tests
plus 99 subtests: 94 active control-kernel tests, 30 strict worker-protocol
tests, 4 historical-recovery tests, and 22 retained Gate 5 verifier red-team
regressions. Its canonical node-ID
digest is:

`6BF70F5569C4BCA5B7D896382A099FC966E9C0622B3A3694BE0B330B66048756`

The four-test historical subset digest is:

`B3A239A9579A0DDBADFD2231AF5454250949BFA34BF7124D9305DA0972513340`

The 94-test active research-control subset digest is:

`E170E51F83B8DEA3B43537737961580E21E08C14DE9DFE5A3809FB7B2EEA0952`

The 30-test strict worker-protocol subset passes 38 subtests. Its canonical
node-ID digest is:

`534CF4550FF56F3EA5F4235680CDB89A91784D1CEE0B7CB7ABDF9DE1C7B3E7FF`

That kernel keeps the transport callback nonce outside immutable worker bytes,
preserves retry-stable terminal identity, allows exact post-seal replay only
when the outcome-access event binds the same terminal receipt and completion
time, and quarantines partial failure artifacts as negative evidence. These
are structural controls, not authenticated execution or a scientific result.

The current successor-candidate worker receipt is 364/364. Its
canonical node-ID digest is:

`94566203B3E0FF79B3224C1C5A073698CA99D3C08BC1119A9082E42AF4B178BD`

The companion API/launcher/fleet/state suite passes 78/78. Its canonical
node-ID digest is:

`603DEBF7DF9AC7B5A69543C3736F4CD38692D3330690A7559A6F9DE6F0E2AF77`

The dark worker-terminal bridge suite passes 17/17. Its canonical node-ID digest
is:

`FA6C985CD6CAA734034E006BB4BAF6BE9D02269D7312BEE7355E9C3833759C51`

The separate durable fleet-callback and fake Object-Lock seam suite passes
38/38. Its canonical node-ID digest is:

`D3EAF533FEDB5B03168200AA399AC53A6E2A6F22874EBABEAECEFB227400778D`

The prospective lifecycle, SQLite, and default-dark route suite passes 76/76
with no subtests. Its canonical node-ID digest is:

`5F1197D70B7AFAD39D01BEBEB4E7397C3E075D74A5BFFA5305C62A0EDB3C7D84`

The packaging, snapshot, envelope, context, admitted-adapter, and bounded-
reconciliation suite passes 80/80 with no subtests. Its canonical node-ID
digest is:

`2E45FCD920E0B52916A7341D2FF766FDC9F7911EC2CB11C27BC3FF8FEC3815FB`

The bridge stores one retry-stable terminal wrapper/index and binds each
server-authored *terminal* callback-attempt receipt in a separate
post-authentication acceptance wrapper/index rather than the worker terminal
carrier. Nonterminal route nonce rows do not receive this bridge wrapper. It now uses
the sealed-safe authorization replay port, so exact terminal replay can remain
available after an outcome seal when the same receipt and completion time are
bound. The surrounding lifecycle successor adds local prospective authorization,
same-host one-use consumption, output retention, outcome-access reservation,
Packet-v2/nonreporting attachment, and event-bound reconciliation. These paths
remain dark and locally bounded: the packaged service adapter and
reconciliation report path now exist and are locally tested, while
strict-loader provenance is not independently attested, the tested Object-Lock
backend is synthetic, repository receipts bind wrappers rather than
independently retained inner bytes, no provider-backed startup has passed, and
no live experiment or claim authority is created.

The 364-test worker, 78-test API/launcher/fleet/state, 30-test worker-protocol,
17-test bridge, 38-test durable-seam, 76-test prospective-lifecycle, and 80-test
admitted-adapter/reconciliation results are
`LOCAL_UNATTESTED_HOST_REGRESSION` observations. Each suite now binds its
collected, started, and finished node-ID sequences plus exact
setup/call/teardown and subtest outcomes inside one pytest process. The child
starts with `-I -S -B`, uses a fresh bytecode-cache prefix, disables plugin
autoload, and admits only the locked pytest site root and exact suite-specific
repository import roots. The local lock binds Python 3.14.0, pytest 9.0.2,
pytest-asyncio 1.3.0, three interpreter files, 508 exact files owned by seven
runner distributions, and three `.pth` files whose startup execution is
disabled. Before importing pytest or an explicit plugin, the child requires its
resolved origin and package search root to match those exact file records; the
parent rechecks the origin records and the surviving loaded-module inventory.
The inventory is an endpoint snapshot of surviving `sys.modules` entries. It
maps cache paths back to source and therefore does not prove the exact bytecode
executed, and it cannot see transient/unloaded/dynamic execution, unresolved or
deleted origins, native-loader dependencies, or descendant processes. The
standard library, complete test/native/descendant-process closure, Windows
kernel, filesystem, and independent trust root remain `OPEN`. Each detailed
JSON receipt is ephemeral inside the verifier; the verifier prints its
executed-node, outcome, locked-origin, and loaded-code digests, but no trusted
time, WORM retention, or independently replayable receipt is created.

The nested numerical/state/schema red team passes 32/32. Its canonical node-ID
digest is:

`12602041756F20D1AFD402FA56968660839E5EB1098438BA84C69BFF8DE7050B`

The independently confirmed 290/290 worker receipt and the earlier 285/27,
288/30, and 289/31 green candidates remain exact earlier checkpoints. The
earlier green candidates were invalidated by
subsequently reproduced mutable-model-state and public-receipt mutation
bypasses. They are adverse chronology, not current receipts, and must not be
used in the manifest.

Same-process test-ID canonicalization is exact: require duplicate-free
collected, started, and finished sequences to agree, normalize path separators
to `/` without Unicode normalization, sort node IDs ordinally, encode each as
UTF-8 followed by LF, and SHA-256 the concatenation. Source/test hashes and the
exact outcome ledger remain independently load-bearing; a node-ID digest alone
does not replace file identity or prove hermetic execution.

## Build and run the verifier

From the repository root:

```powershell
python -I -B scripts\build_project_coherence_gate5_manifest.py
python -I -B scripts\verify_project_coherence_gate5.py
```

The manifest build is appropriate only after an intended change to the admitted
surface. Both authoritative scripts require Python isolated mode and disabled
bytecode writes. Child suites run through the locally content-locked
same-process runner; they remain sanitized local regressions, not hermetic or
independently attested execution.

The verifier also forces offline Hugging Face/Transformers mode for test
subprocesses. Pytest subprocesses additionally clear caller-provided
`PYTHONPATH`, `PYTHONHOME`, `PYTEST_ADDOPTS`, and `PYTEST_PLUGINS`; disable
entry-point plugin autoload; bind every existing ancestor `conftest.py` and
pytest configuration candidate in either admitted test path; and explicitly
load only `pytest_asyncio.plugin` for the worker because the bound parent
configuration declares `asyncio_mode`. The local lock is checked before and
after all suites. The lock file is read once through one identity-checked
descriptor, and those same bytes are hashed and parsed. Installed
standard-library/test/native/descendant code, distribution files absent from
upstream `RECORD`, transient imports, exact loader-executed bytecode, and other
runtime activity outside its declared scope remain part of the explicitly OPEN
hermeticity boundary.

For repository artifacts, the verifier rejects symlink or reparse path
components and hardlinked leaf files, compares pathname and opened-handle
identity, hashes through that same handle, checks stable structural ancestor
identity before and after each read, and compares the integrated Gate 5, Gate
4, and history identity map after tests. Structural ancestry binds device,
inode, type, link count, and reparse state; volatile directory byte counts and
timestamps are excluded because unrelated child activity can change them
without replacing the observed path. Full leaf identity and exact bytes remain
bound. These controls catch ordinary aliasing and same-byte replacement. They
do not establish an immutable read-only snapshot, privileged or
metadata-preserving ABA resistance, hosted/auxiliary model-loader alias
protection, kernel/filesystem trust, or independent reproduction. Those remain
`OPEN` under `G5-ENGINEERING-002`.

The verifier rejects a missing or extra artifact, byte/hash/role drift,
absolute or traversing paths, case-folded duplicate paths, symlink/reparse
components, hardlinked artifacts, opened-handle or ancestor-identity drift,
a manifest self-hash, an unbound Gate 5/Python/script/data/pytest-environment
file, stale test counts or node IDs, a red test result, a removed security hold,
a missing historical defect, a missing or rewritten OPEN boundary, a malformed
or extended structured carrier, an explicit contradictory status promotion, or
non-integer numeric-count substitution. After every subprocess it rehashes the
complete Gate 5 surface, all 537 historical files, and all transitively bound
Gate 4 artifacts before printing PASS.

A verifier `PASS` remains bounded by the six prose axes: document
`DRAFT / OPEN / NOT FROZEN`; decision `OPEN / KEEP_OPEN`; engineering
`RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`; experiment `NOT_STARTED`;
license/disclosure/canon `NOT LICENSED / HELD / NOT FROZEN`; and live/product
route `UNAVAILABLE / NOT AUTHORIZED`. A structural PASS changes none of them.

## Manifest contract

The manifest schema is
`project_coherence.gate5_artifact_manifest.v0.1`. Its governance fields are
fixed:

- `document_status = DRAFT / OPEN / NOT FROZEN`;
- `gate5_status = OPEN`;
- `gate_decision = KEEP_OPEN`;
- `experimental_execution_status = NOT_STARTED`;
- `admission_ring = 4`;
- `license_status = NOT LICENSED`;
- `disclosure_status = HELD`;
- `public_disclosure_authorized = false`;
- `canon_effect = NONE`;
- `product_claim_effect = NONE`; and
- `manifest_self_hash = null`.

Every `artifacts[]` record uses a canonical repository-relative POSIX path,
uppercase SHA-256, exact byte count, and nonblank role. The manifest does not
hash itself. It directly binds the claim ledger and Gate 4 manifest, and the
verifier requires both gates to agree on the exact claim-ledger bytes. The
integrated Gate 4 verifier must pass while retaining Gate 4 as OPEN.

The exact active closure includes all Python under:

- `src/cas_harness_v2/`;
- `tests/cas_harness_v2/`;
- `noetic-compass-scaffold/noetic-compass/live-trace-worker/app/`;
- `noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/`; and
- `noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/`; and
- the admitted complete source/resource tree under
  `noetic-compass-scaffold/noetic-compass/api/`.

It also includes all worker scenario JSON, worker shell scripts, the worker
Dockerfile, `.dockerignore`, `requirements.in`, `requirements.txt`, the selected
launcher/fleet/state tests used by the successor identity flow, and the complete
pytest discovery/configuration inputs for those admitted test paths. Historical
recovery bytes are transitively closed by the exact 537-file history manifest;
the verifier independently rehashes that closed scope. The bound root
`.gitattributes` forces LF checkout for active Gate 5 text surfaces and disables
text conversion for the historical recovery, preserving its exact original Git
bytes and known LF/CRLF adverse evidence across clean Windows checkouts. Its
later `-text` exceptions for
`api/services/cas_harness_pythia160m_*.py`,
`api/services/cas_harness_research_intervention_worker.py`,
`tests/test_cas_harness_pythia160m_*.py`, and
`tests/test_cas_harness_research_intervention_worker.py` intentionally override
the earlier broad API/test LF rules. Those exceptions preserve already-LF
historical worker source blobs without checkout conversion; they do not remove
the blobs from Gate 5's direct-or-transitive exact hash closure.

The exact Pythia identity is
`EleutherAI/pythia-160m@50f5173d932e8e61f858120bcb800b97af589f46`,
with `model.safetensors`, 374,998,696 bytes, SHA-256
`29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270`.
The successor loader and image preflight bind and hash the exact five-file
model/config/tokenizer set both before and after load. This is artifact-set and
bounded runtime-canary evidence only. One CPU-only, non-scientific engineering
preflight loaded those artifacts and ran the offline canary; it was not an
authorized or admitted experiment and created no GPU run, Evidence Packet, or
scientific result. Experimental execution remains `NOT_STARTED`. This is not an
in-memory tensor digest, independent signature, or authenticated GPU run.

## Preserved negative evidence

The verifier requires, rather than hides, the following historical evidence:

- 537 recovered files, 95,945,579 bytes, inventory digest
  `361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f`;
- the V3 committed-LF versus terminal-CRLF result identity inconsistency;
- the V4 `ZeroNetworkGuard` versus `CompatibleZeroNetworkGuard` startup
  defect;
- the historical model-free receipt of 43 passed and 4 failed; and
- the separately restored V1 worker receipt of 31 failed due to absent frozen
  fixture dependencies.

The adversarial review must also retain every newly reproduced kernel and
worker defect alongside its regression. In particular, it must record carrier
forgery, outcome-event rehash forgery, fixed-sample bypass attempts, normalized
identity aliases, coordinate/hook mismatch, nonfinite/dtype/shape comparison,
RNG-only output drift, fallback alias/RNG state, mutable model-state baseline
instability, and abort-on-rejection behavior. A repaired defect may become a
regression-tested control; its adverse observation must not disappear.

## Dependency-security hold

The historical v0.1 binding still records `transformers==4.46.3` and
`CVE-2026-4372` / `GHSA-29pf-2h5f-8g72`. It is preserved unchanged as adverse
evidence; it is not the current build input.

The successor v0.2 candidate pins `transformers==5.14.1` in a 73-distribution
hash-bound lock, binds its repository source/build controls to source commit
`4bff437dbcf6d0d38046e63d2aee823e8f316711`, and records locally observed OCI
index
`sha256:3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c`
and linux/amd64 manifest
`sha256:60bf92b327ebec84887c659313a97a6369a24fd5d8eb00a012544fcafd26ba27`.
The time-indexed v0.2 receipt records locally observed BuildKit SPDX SBOM and
SLSA provenance identifiers. At issuance, the raw build history, SPDX payload,
SLSA payload, and Scout report were not retained or repository replayable; that
historical statement remains unchanged and its claim effect is
`SELF_REPORTED_LOCAL_OBSERVATION_ONLY`. Exact
offline Pythia loading, one CPU-only engineering geometry/numerics canary,
385-object native closure with only the declared host `libcuda.so.1` seam, a
no-network/read-only runtime preflight, and fail-closed startup without token or
CUDA were locally observed.

The later additive raw-evidence receipt retains ten exact payloads, including
the original OCI index/config/manifests, BuildKit history, SPDX statement, and
SLSA statement. It also retains a current direct Scout 1.21 image SPDX report
and SARIF scan. The current direct scan is `COMPLETED_WITH_FINDINGS`: 0
critical, 0 high, 3 medium, and 4 low across seven records. Vendor triage
currently classifies six as vulnerable or fix-deferred and one as a
scanner/vendor conflict because the exact scanned `dpkg` version is
vendor-fixed. The SARIF does not embed the candidate identity or retained
invocation, and the linked Ubuntu vendor pages were not snapshotted. The
original Scout 1.24 raw report, scanner database identity, complete process
transcript, independent trust root, and independent reproduction remain
unavailable.

These receipts materially advance the candidate but do not close
`G5-ENGINEERING-003`. `pip-audit` examined 72 lock entries with zero findings
and skipped the direct-URL Torch entry; a separate OSV package/version query
returned zero Torch findings. No scan PASS, real GPU forward, admitted
experiment, or independent security receipt exists. The disposition therefore remains
`OPEN_SECURITY`; `live_execution_authorized = false`, Gate 5 remains `HELD`,
and the candidate is not accepted.

## Required OPEN boundaries

The manifest, matrix, and adversarial review must preserve these closure
classes:

- upstream Gate 4 remains OPEN;
- independently trusted time and a non-caller-selected trust root;
- durable append-only/WORM ordering;
- independently authenticated run issuance, replay rejection and atomic
  one-use consumption beyond one same-host SQLite file, plus a registry proven
  complete against external executions and selective reporting;
- authenticated execution and real identity/affiliation/independence;
- provider-backed startup and independent reproduction of the bounded
  worker-to-kernel mapping, plus hermetic environment attestation;
- an independently attested hermetic runner, complete standard-library,
  test/native/descendant-process closure, immutable read-only snapshot,
  privileged/metadata-preserving ABA resistance, hosted and auxiliary loader
  alias hardening, and independent reproduction under `G5-ENGINEERING-002`;
- semantic artifact/data/power-analysis/coordinate validation;
- the remaining dependency/container `OPEN_SECURITY` hold, including
  remediation or disposition of six vendor-confirmed vulnerable/fix-deferred
  records, reconciliation of the `dpkg` conflict, complete scanner-process
  evidence, and independent reproduction;
- one separately authorized live exact-revision experiment;
- GPU/autocast/compiled-hook numerical determinism;
- matched controls and falsifiers;
- independent numerical audit and held-out replication;
- external specialist peer review and exact claim-language review;
- downstream proof that packet assessments cannot mint authority;
- current product readiness under its separate authority; and
- explicit owner and qualified legal/patent/privacy disclosure authorization.

Repository tests can close bounded implementation defects. They cannot close
the external, scientific, governance, product, or disclosure items above.

## Interpretation boundary

The SHA-256 values in this lane are integrity identities only. They are not
signatures, reviewer identities, trusted timestamps, WORM receipts, semantic
validations, licenses, or capability tokens. The structural verifier can check
declared schemas, required wording, byte identity, and local regressions; it
cannot authenticate that a document's substantive claims are true or establish
scientific validity. `PacketAssessment` remains data, not authority. No Gate 5
artifact may be routed into a customer verdict or public claim until the
applicable independent authorities explicitly close their own gates.

The reported RunPod balance is user-supplied `$107.00`. No provider billing
ledger or balance receipt was inspected, no RunPod/GPU/paid job was launched,
and known spend for this tranche is `$0.00`.

Nothing in this lane creates live-execution authority, a scientific result,
canon authority, a licensed claim, a product route, or disclosure authority.
