# WELD v3 protocol and claim boundary

## 1. What v3 fixes

WELD v2 is a useful engineered demonstration, but it cannot support a
validation claim. Its negative case changes the localizer, the actor and truth
coexist in one Python process, Python repeats Rust cutoffs, its random baseline
is not an independently verdict-bearing matched case, and the imported
`cas_engine` module is not bound to a path, hash, or version. The specification
and observed results also coexist without an immutable prior freeze.

WELD v3 replaces those mechanisms. It does not reinterpret the v2 result and
does not close Gate 5.

## 2. Two separate phases

### Phase A — actor

The actor command has no truth argument. Its frozen input directory must
contain exactly five public files: protocol, public cases, runtime binding,
model-adapter contracts, and a truth commitment. The plaintext truth file is
not permitted in that directory. The commitment is domain-separated
HMAC-SHA-256 with separately generated salt and secret key, each at least 32
bytes. It binds the key hash and the hash of a custodian receipt externally
anchored before freeze. Each case is written to the same adapter command over
standard input in a fresh empty working directory that is deleted before the
next case. The adapter runs with the same ordered pipeline and returns one
closed decision enum.

Truth custody is stronger than a naming convention: the protocol requires the
plaintext truth to be unavailable on the actor host until the actor receipt is
sealed. The subprocess receives no truth path, truth environment variable,
role, expected outcome, pair mapping, or case label. Its working directory is
a fresh empty temporary directory. A real run also requires an external
sandbox/custody receipt; the local mock tests prove channel separation, not
resistance to a malicious host administrator.

### Phase B — adjudication

Existence of `actor_receipt.json` is not enough. Before truth release, the
external custodian must anchor its exact SHA-256, byte count, invocation count,
output count, freeze identifier, fresh seal nonce, and the fact that truth was
still unreleased. Only afterward may the custodian release the plaintext truth
and HMAC key in a receipt bound to both the actor receipt and its external
seal. Adjudication rejects missing or changed custody records, non-increasing
seal/release times, a key that differs from the frozen key hash, or truth that
differs from the frozen HMAC. It then checks exact enum equality and
information matching. There is no combined actor-plus-adjudicator entry point.

The actor receipt records one successful subprocess invocation per case,
including ordered sequence, channel hashes, zero return code, and a unique
working-directory token. Zero invocations or a count/output mismatch is fatal.
These records plus the external seal make post-actor mutation detectable. They
do not let local Python prove that a malicious external custodian told the
truth; that trust boundary remains explicit. This revision has no trusted
external-anchor signature verifier and therefore rejects every
`PRODUCTION_RUST` adjudication. Only `MOCK_TEST_ONLY` can exercise the local
linkage logic. A new frozen protocol revision is required to lift that block.

## 3. Fixed pipeline

Every case, without exception, must emit this trace:

1. `INGEST_PUBLIC_CARRIER`
2. `J1_CONTRACT_GATE`
3. `COMPILE_OR_VALIDATE_ARTIFACT`
4. `DIAGNOSE`
5. `LOCALIZE`
6. `REPAIR`
7. `VERIFY`
8. `J2_CONTRACT_GATE`
9. `STAGE5_CONTRACT_GATE`
10. `EMIT_DECISION`

The controller invokes one bound executable with one command shape. Public
case envelopes contain no role or expectation. A new executable, alternate
localizer, per-case callback, or case-specific arguments require a new freeze
and a new protocol identifier.

The current contract requires `J1`, `J2`, and `STAGE5` to return `NOT_RUN`.
Their gates validate interface declarations only. Enabling them is a future,
separately preregistered protocol revision.

## 4. Decision ownership

The Rust adapter owns detection, localization, repair, and verification. Its
only admissible final decisions are:

* `REPAIR_ACCEPTED`
* `NO_REPAIR_NEEDED`
* `REPAIR_REJECTED`
* `PIPELINE_ERROR`

Python does not receive a severity cutoff, satisfaction floor, probability
cutoff, or score-to-verdict formula. It checks schema, hashes, the exact stage
trace, and enum equality against committed truth. This removes the duplicated
Python decision boundary that could drift from Rust.

## 5. Verdict-bearing matched control

Each private truth pair names one target case and one control case. Their
public `information_profile` objects must be byte-for-byte equal under
canonical JSON. The adjudicator also derives and matches carrier kind, JSON
field/array topology, exact numeric and boolean values, UTF-8/code-point string
lengths, and deterministic lexical-token length vectors, so a declared profile
cannot conceal a differently shaped or differently exposed envelope.
The control has its own committed `NO_REPAIR_NEEDED` decision; the target has
the committed `REPAIR_ACCEPTED` decision.

A pair passes only when all three conditions pass:

1. target observed decision equals target expected decision;
2. control observed decision equals control expected decision;
3. target and control information profiles match.

The overall verdict passes only when every pair passes. Thus a correct target
cannot hide a failed control. The control is an outcome-bearing case processed
by the real pipeline, not a draw-count comparison beside it.

## 6. Freeze and runtime binding

`freeze.py` refuses to overwrite a receipt and refuses a result directory that
already contains anything. Preregistration and result roots may not contain one
another. It hashes all five allowed preregistration files and records the
predeclared absolute result directory. The actor rechecks every hash and embeds
the freeze identifier in its receipt. Adjudication repeats the checks.

A `PRODUCTION_RUST` binding requires:

* one absolute executable/runtime path;
* executable byte count and SHA-256;
* exact version-probe arguments and the SHA-256 of their stdout/stderr bytes;
* Rust language, crate name, and crate version;
* absolute paths, byte counts, and SHA-256 values for `Cargo.toml`,
  `Cargo.lock`, and the scanner source;
* a parsed `Cargo.toml` package identity and matching unique `Cargo.lock`
  package identity for the bound `cas-engine` name and version;
* a scanner source that resolves within that crate's `src` tree;
* a native executable image whose bound JSON version probe reports Rust,
  crate/protocol identity, rustc/target values, and the exact three bound
  source hashes;
* an external-custody isolation contract stating that only the commitment is
  available during Phase A.

The executable and every bound source are attested at freeze time, immediately
before execution, and immediately after execution. Adjudication requires both
actor attestations to equal the freeze attestation, not merely each other.
Ambient `import cas_engine` is forbidden. `MOCK_TEST_ONLY` bindings are
accepted solely by the test protocol and force a mock-only claim ceiling.

Local validation of Cargo identities and self-reported version claims makes
ordinary substitution detectable; it is not reproducible-build proof that an
arbitrary native binary was compiled from those sources. Local timestamps and
hashes are not WORM or independent custody. A real claim still needs externally
verified build provenance, the freeze receipt anchored outside this working
tree before Phase A, and real external custody. Without those, production
adjudication remains blocked regardless of a local PASS.

## 7. Model-facing bridge

The public carrier is an artifact chain rather than a single synthetic score
vector. The frozen contracts reserve these joins:

* **J1:** `CircuitReading -> CASExpression`, followed by compiler acceptance;
* **J2:** `CorrectedExpression + CompilationArtifact -> EpsilonPrefix`;
* **Stage 5:** paired epsilon prefixes and held-out continuations -> per-item
  mean-logprob outcomes and a matched-control comparison.

The adapter contract file binds the currently observed candidate source hashes
but labels every join `NOT_RUN`. A future model-facing protocol must replace
those observations with runtime bindings, remove known continuation leakage,
define lexical-overlap checks, preregister the paired analysis, and then make
authorized provider/model calls. V3 makes that future path explicit without
pretending it happened.

## 8. Claim ceiling and open gates

Passing mock tests proves only that the protocol code enforces its schemas,
phase separation, fixed trace, receipt/custody linkages, runtime mutation
checks, per-case working directories, and matched-pair verdict logic. It proves
no CAS scientific capability.

Until a real Rust binding and build attestation, external truth/key custody,
external commitment/freeze/actor-receipt anchors, precommitted corpus, and
J1/J2/Stage-5 execution exist, the maximum status is:

`ENGINEERED / NOT_RUN / NOT_VALIDATED`

Gate 5 remains open. The scientific corpus remains outside this package.
