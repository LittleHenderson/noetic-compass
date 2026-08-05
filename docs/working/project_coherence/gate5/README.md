# Project Coherence Gate 5

Document status: `DRAFT / OPEN / NOT FROZEN`

Gate 5 status: `OPEN / NOT_STARTED / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

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
- `GATE5_ARTIFACT_MANIFEST_v0.1.json` is the non-self-hashing exact artifact
  and test receipt manifest.
- `scripts/build_project_coherence_gate5_manifest.py` deterministically builds
  that manifest from the closed surface.
- `scripts/verify_project_coherence_gate5.py` verifies the complete bounded
  surface and re-runs its dependencies and tests.

## Current bounded receipts

The stable Harness v2 suite contains 113 pytest node IDs and passes 113 tests
plus 61 subtests: 94 active control-kernel tests, 4 historical-recovery tests,
and 15 retained Gate 5 verifier red-team regressions. Its canonical node-ID
digest is:

`FD31E05BDFE62A44B4FC7D1556A2CA498115FF8E0A65C3F16160FA4D0C2FA294`

The four-test historical subset digest is:

`B3A239A9579A0DDBADFD2231AF5454250949BFA34BF7124D9305DA0972513340`

The 94-test active research-control subset digest is:

`E170E51F83B8DEA3B43537737961580E21E08C14DE9DFE5A3809FB7B2EEA0952`

The current successor-candidate worker receipt is 364/364. Its
canonical node-ID digest is:

`94566203B3E0FF79B3224C1C5A073698CA99D3C08BC1119A9082E42AF4B178BD`

The companion API/launcher/fleet/state suite passes 76/76. Its canonical
node-ID digest is:

`1ED1E9E3AFA2EDA6881463EE5284DD4902AB94C0246B80D2937066480AC42921`

The 364-test worker and 76-test API/launcher/fleet/state results are
`LOCAL_UNATTESTED_HOST_REGRESSION` observations. Their node-ID digests were
computed from collect-only subprocesses; pass/fail summaries came from separate
execution subprocesses. They do not receipt the node IDs that actually executed
in the passing runs. The runner uses mutable user-site Python 3.14.0, pytest
9.0.2, pytest-asyncio 1.3.0, and startup-hook state that is not content-bound by
these receipts.

The nested numerical/state/schema red team passes 32/32. Its canonical node-ID
digest is:

`12602041756F20D1AFD402FA56968660839E5EB1098438BA84C69BFF8DE7050B`

The independently confirmed 290/290 worker receipt and the earlier 285/27,
288/30, and 289/31 green candidates remain exact earlier checkpoints. The
earlier green candidates were invalidated by
subsequently reproduced mutable-model-state and public-receipt mutation
bypasses. They are adverse chronology, not current receipts, and must not be
used in the manifest.

Collect-only test-ID canonicalization is exact: collect with pytest, normalize
path separators to `/`, sort unique node IDs ordinally, encode each as UTF-8
followed by LF, and SHA-256 the concatenation. Source/test hashes remain
independently load-bearing; a collect-only node-ID digest does not replace file
identity or prove the actual executed-node set.

## Build and run the verifier

From the repository root:

```powershell
python -I -B scripts\build_project_coherence_gate5_manifest.py
python -I -B scripts\verify_project_coherence_gate5.py
```

The manifest build is appropriate only after an intended change to the admitted
surface. Both authoritative scripts require Python isolated mode and disabled
bytecode writes. Their child test runs are sanitized local regressions, not a
locked or independently attested runner.

The verifier also forces offline Hugging Face/Transformers mode for test
subprocesses. Pytest subprocesses additionally clear caller-provided
`PYTHONPATH`, `PYTHONHOME`, `PYTEST_ADDOPTS`, and `PYTEST_PLUGINS`; disable
entry-point plugin autoload; bind every existing ancestor `conftest.py` and
pytest configuration candidate in either admitted test path; and explicitly
load only `pytest_asyncio.plugin` for the worker because the bound parent
configuration declares `asyncio_mode`. Installed interpreter/plugin bytes are
still part of the explicitly OPEN hermetic-environment boundary. The static
verifier rejects executable shadows inside the admitted repository roots;
host-runner integrity, hardlink/reparse-point aliasing, read-only snapshot and
before/after ABA resistance, cache/bytecode and native-extension shadows outside
that admitted snapshot, same-run executed-node receipts, and raw
external-evidence retention remain `OPEN` under `G5-ENGINEERING-002`.

The verifier rejects a missing or extra artifact, byte/hash/role drift,
absolute or traversing paths, case-folded duplicate paths, symlinked artifacts,
a manifest self-hash, an unbound Gate 5/Python/script/data/pytest-environment
file, stale test counts or node IDs, a red test result, a removed security hold,
a missing historical defect, a missing or rewritten OPEN boundary, a malformed
or extended structured carrier, an explicit contradictory status promotion, or
non-integer numeric-count substitution. After every subprocess it rehashes the
complete Gate 5 surface, all 537 historical files, and all transitively bound
Gate 4 artifacts before printing PASS.

A verifier `PASS` must still print:

`OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`

and `experimental execution: NOT_STARTED`.

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
The receipt records locally observed BuildKit SPDX SBOM and SLSA provenance
identifiers, but the raw build history, SPDX payload, SLSA payload, and Scout
report were not retained, are not repository replayable, and have no independent
trust root. Their claim effect is `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`. Exact
offline Pythia loading, one CPU-only engineering geometry/numerics canary,
385-object native closure with only the declared host `libcuda.so.1` seam, a
no-network/read-only runtime preflight, and fail-closed startup without token or
CUDA were locally observed.

Those receipts materially advance the candidate but do not close
`G5-ENGINEERING-003`. `pip-audit` examined 72 lock entries with zero findings
and skipped the direct-URL Torch entry; a separate OSV package/version query
returned zero Torch findings. A local Docker Scout 1.24.0 run against the
observed SPDX identifier covered 190 packages and reported
`COMPLETED_WITH_FINDINGS`: 0 critical, 0 high, 3 medium, and 4 low across seven
unfixed vulnerabilities. A separate direct local image/filesystem scan did not
complete and remains `INCOMPLETE / PENDING`. No scan PASS, real GPU forward, or
independent clean reproduction exists, and the raw scan report is not retained
or repository replayable. The disposition therefore remains
`OPEN_SECURITY`; `live_execution_authorized = false`, Gate 5 remains `HELD`,
and the candidate is not accepted.

## Required OPEN boundaries

The manifest, matrix, and adversarial review must preserve these closure
classes:

- upstream Gate 4 remains OPEN;
- independently trusted time and a non-caller-selected trust root;
- durable append-only/WORM ordering;
- authenticated nonces, replay rejection, atomic one-use consumption, and a
  complete anti-selective-reporting run/packet registry;
- authenticated execution and real identity/affiliation/independence;
- exact worker-to-kernel protocol mapping and hermetic environment attestation;
- a locked and independently attested host runner, same-run executed-node
  receipt, read-only snapshot, hardlink/reparse/ABA resistance, cache/native
  shadow exclusion beyond the repository-local check, and retained raw
  build/security evidence under
  `G5-ENGINEERING-002`;
- semantic artifact/data/power-analysis/coordinate validation;
- the remaining dependency/container `OPEN_SECURITY` hold, including a
  disposition for every current scan finding, direct-filesystem coverage, and
  independent reproduction;
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
validations, licenses, or capability tokens. `PacketAssessment` remains data,
not authority. No Gate 5 artifact may be routed into a customer verdict or
public claim until the applicable independent authorities explicitly close
their own gates.

Nothing in this lane creates live-execution authority, a scientific result,
canon authority, a licensed claim, a product route, or disclosure authority.
