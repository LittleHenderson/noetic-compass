# Project Coherence Gate 5

Status: `DRAFT / OPEN / NOT STARTED / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

Gate 5 is the private research-control integration lane for CAS Harness v2. It
binds the prospective preregistration and Evidence Packet v2 kernel, the
bounded live-worker model/intervention controls, and the exact historical
V1-V4 recovery. It does not admit a scientific result, authorize an
experiment, license a claim, create a product route, or authorize disclosure.

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
  weights-file identity and the unreleased container/dependency security hold.
- `GATE5_ARTIFACT_MANIFEST_v0.1.json` is the non-self-hashing exact artifact
  and test receipt manifest.
- `scripts/build_project_coherence_gate5_manifest.py` deterministically builds
  that manifest from the closed surface.
- `scripts/verify_project_coherence_gate5.py` verifies the complete bounded
  surface and re-runs its dependencies and tests.

## Current bounded receipts

The stable Harness v2 suite contains 108 pytest node IDs and passes 108 tests
plus 50 subtests: 94 active control-kernel tests, 4 historical-recovery tests,
and 10 retained Gate 5 verifier red-team regressions. Its canonical node-ID
digest is:

`22979CE12CC23254D693E5902F2697BB3E113F835A4A3BE2FEE0680AAB5DA341`

The four-test historical subset digest is:

`B3A239A9579A0DDBADFD2231AF5454250949BFA34BF7124D9305DA0972513340`

The 94-test active research-control subset digest is:

`E170E51F83B8DEA3B43537737961580E21E08C14DE9DFE5A3809FB7B2EEA0952`

The independently confirmed post-repair worker receipt is 290/290. Its
canonical node-ID digest is:

`1C8DB623FC6507DB0B4CE218C3FD60833D514503122CD68FA79644A61DB6C635`

The nested numerical/state/schema red team passes 32/32. Its canonical node-ID
digest is:

`12602041756F20D1AFD402FA56968660839E5EB1098438BA84C69BFF8DE7050B`

Earlier 285/27, 288/30, and 289/31 green candidates were invalidated by
subsequently reproduced mutable-model-state and public-receipt mutation
bypasses. They are adverse chronology, not current receipts, and must not be
used in the manifest.

Test-ID canonicalization is exact: collect with pytest, normalize path
separators to `/`, sort unique node IDs ordinally, encode each as UTF-8 followed
by LF, and SHA-256 the concatenation. Source/test hashes remain independently
load-bearing; a node-ID digest does not replace file identity.

## Run the verifier

From the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B scripts\verify_project_coherence_gate5.py
```

The verifier also forces offline Hugging Face/Transformers mode for test
subprocesses. Pytest subprocesses additionally clear caller-provided
`PYTHONPATH`, `PYTHONHOME`, `PYTEST_ADDOPTS`, and `PYTEST_PLUGINS`; disable
entry-point plugin autoload; bind every existing ancestor `conftest.py` and
pytest configuration candidate in either admitted test path; and explicitly
load only `pytest_asyncio.plugin` for the worker because the bound parent
configuration declares `asyncio_mode`. Installed interpreter/plugin bytes are
still part of the explicitly OPEN hermetic-environment boundary.

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
- `noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/`.

It also includes all worker scenario JSON, worker shell scripts, the worker
Dockerfile and requirements, and the parent pytest configuration. Historical
recovery bytes are transitively closed by the exact 537-file history manifest;
the verifier independently rehashes that closed scope. The bound root
`.gitattributes` forces LF checkout for active Gate 5 text surfaces and disables
text conversion for the historical recovery, preserving its exact original Git
bytes and known LF/CRLF adverse evidence across clean Windows checkouts.

The exact Pythia identity is
`EleutherAI/pythia-160m@50f5173d932e8e61f858120bcb800b97af589f46`,
with `model.safetensors`, 374,998,696 bytes, SHA-256
`29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270`.
This is weights-file identity only, not an in-memory tensor digest, signature,
authenticated run, or scientific result.

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

The current worker still pins `transformers==4.46.3`. The Gate 5 security
record identifies `CVE-2026-4372` / `GHSA-29pf-2h5f-8g72`, cites 5.3.0 as the
fixed line, records that the container is not digest-bound, records that a
patched environment has not been revalidated, and fixes
`live_execution_authorized = false`.

Changing the requirement is not itself closure. A successor manifest must bind
the patched complete dependency/container artifact, SBOM and security scan,
then revalidate exact Pythia loading, weight identity, hook geometry, numerical
behavior, and full tests in that exact environment.

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
- semantic artifact/data/power-analysis/coordinate validation;
- the dependency/container security hold;
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
