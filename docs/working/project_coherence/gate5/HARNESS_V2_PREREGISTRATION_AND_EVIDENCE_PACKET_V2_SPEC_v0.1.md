# CAS Harness v2 preregistration and Evidence Packet v2 control kernel

Document status: `DRAFT / OPEN / NOT FROZEN`

Decision status: `OPEN / KEEP_OPEN`

Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`

Experimental execution status: `NOT_STARTED`

License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`

Live / product route status: `unavailable / not authorized`

This document specifies the isolated control kernel in
`src/cas_harness_v2`. It does not close Gate 5, execute an experiment, add a
live-worker route, authenticate a worker, change a product verdict, license a
claim, authorize disclosure, or establish production readiness.
It creates no live-execution, scientific, canon, product, license, or disclosure
authority.

The packaged private adapter now includes tested controller-only outcome-seal,
Packet-v2 attachment, explicit-nonreporting, and reconciliation paths as
bounded software around this isolated kernel. Exact transport envelopes remain
separate from the normative kernel carriers. The application reconstructs each
request-local chain from retained server facts, reserves one declared untrusted
outcome time, and uses a create-only Packet-versus-nonreporting intent bound to
the planned final artifact. Reconciliation binds strict per-run replay to a
separately limited configured-scope report. These controls do not change this
kernel's trust ceiling, prove provider-backed startup, create trusted time or
WORM authority, establish absence of off-registry execution, or authorize a
live route or experiment.

## 1. Normative executable schemas

The closed, versioned schemas are enforced by exact-key Python loaders. The
loaders are normative because JSON Schema alone cannot verify raw-byte hashes,
claim-ledger membership, amendment-chain continuity, evidence bytes, or
cross-document identities.

| Artifact | Exact schema value | Loader |
|---|---|---|
| Per-claim preregistration | `cas_harness_v2.preregistration.v1` | `load_preregistration` |
| Preregistration amendment | `cas_harness_v2.preregistration_amendment.v1` | `load_amendment` or `PreregistrationChain.append_amendment` |
| Evidence Packet v2 | `cas_harness_v2.evidence_packet.v2` | `load_evidence_packet` |

The JSON profile rejects duplicate object keys, UTF-8 BOMs, invalid UTF-8,
non-finite values, JSON floating-point numbers, integers above 2,048 bits,
unpaired Unicode surrogates, NUL characters, excessive size/depth/node count,
unknown fields, missing fields, Boolean-as-integer substitutions, non-string
mapping keys, key-coercion collisions, and non-normalized machine identifiers.
Decimal measurements and thresholds are finite decimal strings.

Every successfully loaded artifact snapshots its exact input bytes and records
their SHA-256 and byte length. Loaded payloads are recursively immutable.

## 2. Per-claim preregistration

A preregistration binds one exact claim-ledger record to one frozen experimental
design. The claim binding contains:

- the exact raw-byte identity of `CLAIM_LEDGER_v0.1.json`;
- one `claim_id` and its exact `claim_text`;
- the canonical hash of the selected claim record; and
- the preregistration artifact's own detached raw-byte hash and byte length.

The design requires explicit:

- primary and null hypotheses, estimand, and direction;
- measurement identifiers, units, operational definitions, and measurement
  kinds;
- confirmatory and held-out-replication splits, source hashes, allocation
  rules, grouping keys, group floors, exact target groups, exact enrolled and
  analyzed row targets, and maximum disjoint missing/excluded rows;
- a fixed-sample plan with `FIXED_SAMPLE` stopping, interim outcome access
  `FORBIDDEN`, disjoint exhaustive row-accounting semantics, explicit
  exclusion and missing-data rules, fail-closed `SCIENTIFICALLY_INELIGIBLE`
  deviation effect, and an exact power-analysis artifact identity;
- threshold identifiers, operators, decimal values, units, and decision
  effects, with threshold units equal to their registered measurement units;
- matched-taxonomy, wrong-layer, and clean-null controls, with additional
  control types available only when preregistered;
- falsifiers and their consequences;
- uncertainty method, confidence level, multiplicity rule, permutations,
  seeds, and grouping unit;
- model, exact lowercase 40-character model revision, weights, tokenizer, code
  commit, clean-worktree, source, analysis, dependency, runtime, exact lowercase
  `sha256:<64-hex>` container digest, and hardware identities; and
- exact permitted and forbidden wording with a private-research claim ceiling.

The governance block is invariant and load-bearing:

```text
admission_ring       = 4
product_claim_status = NOT LICENSED
disclosure_status    = HELD
public_release       = false
product_route        = false
license_decision     = NONE
```

Any other value is rejected. No self-hash field is accepted.

## 3. Append-only amendments and outcome access

Amendments bind the base preregistration hash and the immediately preceding
amendment hash. Identifiers and timestamps must advance monotonically. Artifact
identifiers are append-only and may not collide with earlier identities. Every
public amendment load freshly replays the exact base and every predecessor
carrier. Predecessor replay is iterative, rejects cycles and skipped links, and
is capped at 128 total amendment links. Together with the 2,000,000-byte strict
JSON document ceiling, this caps retained amendment bytes at 256,000,000 and
bounds replay work; the amendment chain is a governance log, not an execution
event stream.

Only three pre-outcome amendment classes exist:

1. `ADMINISTRATIVE_CLARIFICATION` adds a non-operative note.
2. `EXECUTION_IDENTITY_ADDITION` adds exact artifact identities without
   replacing a frozen identity.
3. `EXECUTION_WINDOW` records a prospective execution window.

There is no amendment field for hypotheses, units, splits, thresholds,
controls, falsifiers, uncertainty, wording, or governance. Unknown fields are
rejected. An amendment declaring prior outcome access is rejected. The
process-local chain seals permanently when `record_outcome_access` records an
exact receipt identity and the pre-outcome chain digest; no later amendment can
be appended or injected without invalidating the seal. An `EXECUTION_WINDOW`
is unique and packet execution must occur inside it. Outcome access records the
declared execution-completion timestamp, cannot precede it, and the packet must
carry that exact sealed completion timestamp; therefore no in-protocol interim
outcome access is permitted. The event itself is a canonical exact-byte carrier
with SHA-256 and byte length, and is freshly replayed against the current
pre-outcome chain before any public read; field-only bypass mutation cannot be
rehashed into a matching packet. Public chain-state getters replay integrity
before returning state.

This is a deterministic sequence guard, not a durable authority. A later Gate 5
integration must place the chain and outcome-access event under an independently
authenticated append-only or WORM control. Reconstructing a fresh in-memory
chain is not evidence that no one previously accessed outcomes.

## 4. Evidence Packet v2

An Evidence Packet binds the exact claim, preregistration, protected design,
sealed amendment chain, raw outcomes, execution manifest, reported metrics,
controls, falsifiers, split results, uncertainty report, result summary, and
all available audit/review artifacts.

Packet artifact identifiers must be unique and disjoint from preregistration
artifact identifiers. Distinct identifiers may not reuse one SHA-256/byte-length
identity to simulate independent artifacts. When audit, replication, or claim
review records are present, the executor, auditor, replication team, and claim
reviewer identities must be pairwise distinct after Unicode NFKC normalization,
case folding, and trimming. A reported numerical-audit match cannot coexist
with discrepancies, and a mismatch must identify at least one discrepancy.
Packet creation must follow both execution completion and recorded outcome
access. Execution must start after the last preregistration amendment and fall
inside a registered execution window when one exists. Packet carrier fields are
freshly reconstructed from exact raw bytes before verification.

Every packet reports per split: groups, enrolled rows, analyzed rows, missing
rows, and excluded rows. Missing and excluded categories are disjoint and the
loader requires exact arithmetic:

```text
enrolled_rows = analyzed_rows + missing_rows + excluded_rows
```

Incoherent arithmetic is structurally rejected. Coherent underpowered runs,
target-count deviations, and missing/excluded maxima violations remain loadable
negative evidence; the computed preregistered-criteria axis fails and scientific
eligibility is `INELIGIBLE` rather than erasing the run.

The packet deliberately carries observations and artifact identities, not
caller-selected authoritative status fields. `verify_evidence_packet` computes
separate axes:

| Axis | Current isolated-kernel meanings |
|---|---|
| Structural completeness | `COMPLETE` only when every preregistration, chain, and packet artifact reference matches snapshotted bytes; otherwise `INCOMPLETE`. |
| Authenticated execution | `UNAVAILABLE` or `PRESENT_UNAUTHENTICATED`; this kernel has no trust root and no `AUTHENTICATED` path. |
| Preregistered criteria | `REPORTED_CRITERIA_MET` or `REPORTED_CRITERIA_NOT_MET`, computed from exact decimal thresholds, controls, falsifiers, and split floors. This assesses reported values, not their truth. |
| Scientific eligibility | `INELIGIBLE` when reported frozen criteria fail; otherwise `NOT_ESTABLISHED` until authenticated execution, independent audit, replication, claim review, and external scientific review exist. Underpowered and failed runs remain loadable negative evidence rather than being erased. |
| Independent numerical audit | `UNAVAILABLE`, `REPORTED_MATCH_UNAUTHENTICATED`, or `REPORTED_MISMATCH`. |
| Replication | `UNAVAILABLE` or a reported `AGREES`/`MIXED`/`DISAGREES` state marked unauthenticated. |
| Claim-language review | `UNAVAILABLE` or a reported `APPROVED`/`REJECTED` state marked unauthenticated. Approved wording must byte-for-text match a preregistered allowed string. |
| Product, license, disclosure | Always `RING 4 / NOT LICENSED / HELD / NONE`; public and product routes are always false. |

The packet's SHA-256 is an integrity identity only. It is never a signature,
reviewer identity, authorization, license, disclosure approval, WORM receipt,
scientific conclusion, or product verdict.

Authentication, audit, replication, claim-review, and external-review blockers
are reported independently of whether the frozen numerical criteria pass or
fail; a negative result cannot hide missing provenance or review.

## 5. Evidence Packet v1 boundary

Evidence Packet v1 lacks mandatory v2 facts, including a prospective per-claim
preregistration, protected-design identity, amendment/outcome-access history,
registered splits and thresholds, separated execution authentication,
independent numerical audit, replication, claim-language review, and fixed
governance state.

`reject_automatic_v1_upgrade` and `load_evidence_packet` therefore reject all
four repository-known labels (`evidence_packet.v1`,
`cas_harness_evidence_packet_v1`, `cas_harness_evidence_packet.v1`, and
`cas_harness_stage9_40e_evidence_packet.v1`) with
`AmbiguousV1UpgradeError`. A v1 packet may be cited as a separately hashed
historical source artifact in a newly authored v2 record, but missing facts may
not be inferred or backfilled as if they were prospective.

## 6. Historical design lessons retained

The control model preserves the lessons of the historical v3/v4
preregistrations:

- a successor design never edits a frozen predecessor;
- counts or outcomes already observed must be disclosed;
- prompt, group, layer, surface, taxonomy, and null controls are distinct;
- group-aware splits and uncertainty cannot be reconstructed after unblinding;
- a failed honesty control invalidates or downgrades the instrument rather than
  being absorbed into a favorable result; and
- revised thresholds belong to a new preregistration, never an amendment to the
  result-bearing design.

## 7. Verification and remaining boundaries

Authoritative manifest build and Gate 5 verifier commands, from the repository
root:

```powershell
python -I -B scripts\build_project_coherence_gate5_manifest.py
python -I -B scripts\verify_project_coherence_gate5.py
```

The manifest build is appropriate only after an intended admitted-surface
change. A local focused regression may be run separately with
`python -E -P -B -X dev -m pytest -q -p no:cacheprovider
tests\cas_harness_v2`; it bypasses the same-process receipt control and is not
the authoritative Gate 5 verifier or a locked, attested execution environment.

The suite covers missing and extra fields, duplicate JSON keys, raw-input
mutation, frozen payload mutation, wrong claim and artifact hashes, forged
governance/status fields, threshold/control/falsifier/split failures,
non-monotone or broken amendment chains, amendments after outcome access, and
v1 upgrade ambiguity. Independent adversarial cases additionally cover forged
dataclass carriers, post-seal injection, predecessor cycles, skipped links,
the exact 128-link chain bound, execution-window evasion, fixed-sample plan
deletions and forged rules, invalid target/max values, exact power-analysis
identity, row-accounting contradictions, preserved sample deviations, interim
outcome access, exact completion binding, bypass-mutated outcome-event replay,
retained-byte registry mutation, audit contradictions, normalized cross-role
aliases, and all four repository-known v1 labels.

The last committed `b96c2c12` Harness-v2 collection has an authoritative
same-process PASS receipt. It observed collected, started, and finished sequences of 306 node
IDs, 918 ordinary setup/call/teardown reports, and 151 passing subtests, with
zero warnings, collection or internal errors, or deselections, an empty
isolated pycache, and pytest exit status 0. Its exact Python-ordinal
executed-node digest is
`49BD9090B3CF8990A213BF91CB95E154792444221CC0015F1BCA7D2E77C5D293`.
This authoritative local regression is not hermetic or independently attested
and establishes no model, detector, steering, product, licensing, or disclosure
result.

Focused green slices are diagnostic preregistration at 25 tests plus 41
subtests, digest
`0D3A5514DD15CB6F5334C5D54DF1CBF1344B488C99A18E70DB4E10CE2C90308D`;
post-terminal outcome at 29 tests, digest
`777093FE2A924455178007A326E927A18252C591A329AEF1F336E8D539E679F1`;
diagnostic Study at 46 tests, digest
`83752F3D1507673E399FEDC93D346688A5BA2F802385598E7057822A6C09C0BB`;
and portable historical negative-state verification at 2 tests, digest
`FFC9ED8632A175E576526C84B2E989FDDD39DE443D842DFCDABC3AC12C248570`.
The former 204-test/110-subtest receipt is historical pre-expansion evidence.
All of these are repository-local controls, not live execution, independent
reproduction, scientific evidence, or product authority.

The current packaged kernel has 17 byte-mirrored files and 300 unique exports.
Its packaging-provenance SHA-256 is
`C87A1AA638E89FD76E1CDA5F854832E29C6BC8491D14DE81F20E7363E5F086AC`;
12 focused mirror tests pass. Canonical/mirror `__init__.py` SHA-256 is
`115852A181C19839110E2E5E14A6814991087C0299ABFDF42CEB8EC744C0355A`,
and the packaging allowlist source SHA-256 is
`4582E2A8DDED2330CD8557608FBAFBD5FF37D6AC2E51259D862702A3562E89D4`.

The narrower Stage B joined-executor and runner-preparation suites pass 34/34
and 17/17 with same-process executed-node digests
`C2B5EF68B2491A19BD09345DED44704CA37A57AB21E07E09FFA928E25ABA4570`
and
`40FBF9298CB6DF939C5502D5B8C1E2ADBFA79011167E14E25252E663C114B8E6`.
They are source-level, engineering-only receipts with zero actual model
invocations. The frozen design authorized no separate pre-amendment model
canary. After those receipts passed, the additive runtime image was built
without a model invocation and exactly one amended local Qwen Stage B run
consumed its one-run authority. Run
`gate5-stageb-qwen-20260808T225631Z-3d71101d69ab` created Packet
`epv2-stageb-qwen-joined-001`, SHA-256
`FCF7674B14A34E3C33252B09B7A20E5E55FB6BC3751AC0F2B1C0EFB109578EAC`.
The kernel assesses that Packet as structural completeness `COMPLETE`, criteria
`REPORTED_CRITERIA_NOT_MET`, and scientific eligibility `INELIGIBLE`. Its three
mandatory controls are `INVALID / NOT PERFORMED`, and authentication,
independent audit, replication, claim-language review, and external review do
not advance. This concrete negative Packet demonstrates preservation of a
complete engineering record without promoting prompt-injection detection,
steering efficacy, scientific validity, product validation, license, or
disclosure authority.

The companion current 414-test worker and 78-test API/launcher/fleet/state
suites are `LOCAL_UNATTESTED_HOST_REGRESSION` observations. One pytest process
binds each
suite's duplicate-free collected/started/finished node IDs and exact
setup/call/teardown outcomes. The child starts with `-I -S -B`, imports only
locally locked pytest/plugin code before prepending exact repository roots, and
uses a fresh bytecode-cache prefix. The local runner lock binds three
interpreter files, 508 exact files owned by seven runner distributions, and
three disabled `.pth` files. Pytest and explicit plugin origins must match the
per-file lock before import; the lock is hashed and parsed from one stable byte
buffer. The surviving-module endpoint inventory maps cache paths to source and
does not prove exact executed bytecode or capture transient/unloaded/dynamic
imports, unresolved/deleted origins, native-loader dependencies, or child
processes. The standard library, distribution files absent from upstream
`RECORD`, complete test/native/descendant closure, kernel/filesystem trust, and
independent attestation remain outside the lock.

The time-indexed v0.2 worker/container checkpoint separately retains its
historical 364/364 issuance receipt; it is not rewritten against the current
414-test worker bytes.

The time-indexed v0.2 container receipt records BuildKit SPDX/SLSA and Docker
Scout facts as `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`; at issuance, its raw
payloads were not retained. A later additive receipt now retains ten exact OCI,
BuildKit, SPDX, SLSA, and current Scout 1.21 payloads. The current direct scan is
`COMPLETED_WITH_FINDINGS`: six records are vendor-confirmed vulnerable or
fix-deferred and one `dpkg` record remains a scanner/vendor conflict. The SARIF
does not embed the candidate invocation, scanner database/process transcripts
are absent, and linked Ubuntu vendor pages were not snapshotted. No independent
trust root or complete tool-execution replay exists. At that candidate
checkpoint, one CPU-only non-scientific preflight had loaded the exact Pythia
artifacts and run the offline canary. The pre-Stage-B Pythia GPU canary and
joined-v0.2 diagnostics later completed a six-arm mechanics canary and one joined
controller-worker model invocation on non-admitted, single-host, non-WORM
routes. Those two diagnostics created no Evidence Packet and established neither
prompt-injection detection nor steering efficacy. The later Qwen Stage B Packet
is described above and does not change that scientific boundary. Experimental
execution remains `NOT_STARTED` and
`G5-ENGINEERING-003` remains `OPEN_SECURITY`. The normative Packet-v2 schema and
admission rules in this specification are unchanged by those diagnostics.

The broad active LF rules in `.gitattributes` are followed by later `-text`
exceptions for `api/services/cas_harness_pythia160m_*.py`,
`api/services/cas_harness_research_intervention_worker.py`,
`tests/test_cas_harness_pythia160m_*.py`, and
`tests/test_cas_harness_research_intervention_worker.py`. Those specific
exceptions preserve the already-LF historical worker source blobs as original
Git bytes while Gate 5's direct-or-transitive hash closure continues to bind
them.

## Additive fixed-sample Study-v1 structural candidate

`cas_harness_v2.study_plan.v1` and
`cas_harness_v2.study_outcome_access.v1` are additive, process-local research
schemas for a fixed multi-prompt study. They do not replace or weaken the v1
preregistration chain, worker authorization, worker terminal receipt, or
Packet-v2 schemas.

The bounded source candidate is implemented in
`src/cas_harness_v2/study_protocol.py` and adversarially exercised by
`tests/cas_harness_v2/test_study_protocol.py`. Those files are an isolated
structural seam, not a live runner or authority.

The candidate binds one exact parent plan, content-addressed ordered case
packages, request bytes, case/group/variant identities, pre-outcome
preregistration-chain bytes including amendments, exact per-case counters, and
one terminal receipt per fixed case. It supports two distinct study phases:

- `DIAGNOSTIC_CALIBRATION` requires one diagnostic package with exactly 160
  groups and the exact three Stage C variants per group; it cannot masquerade
  as confirmatory or replication evidence.
- `CONFIRMATORY_EVALUATION` requires ordered confirmatory and internally
  held-out packages bound to the preregistered split artifacts, with disjoint
  exact inventories. The internal held-out role does not establish independent
  replication.

The first definite child failure terminalizes the process-local study with no
retry. Successful registration requires nonnegative, per-case exact counters
whose digests travel through authorization and receipt, and outcome access is
strictly after the chronologically latest terminal. These are structural
controls only. The implementation has no durable cross-process one-use state,
trusted time, WORM authority, provider attestation, model-consumption proof,
Packet creation, scientific conclusion, license, product permission, or
disclosure authority.

`cas_harness_v2.preregistration.v1` still requires confirmatory plus held-out
roles and cannot honestly represent C-Cal. The additive
`cas_harness_v2.diagnostic_preregistration.v1` family now closes that structural
typing gap without widening v1 or providing a conversion path. It admits only
`DIAGNOSTIC_CALIBRATION / DIAGNOSTIC_ONLY`, forbids Packet v2, evaluation and
claim promotion, binds prospective amendments and exactly one declared
execution window, exact-replays a raw aggregate outcome index, and seals its
process-local chain at outcome access. Its source SHA-256 is
`BB8876C31AEAFA6F195F1F6F35F517943BC986D62F0606ECBF2D06B35E837CC2`.
Its test source SHA-256 is
`B2A095B3009A12746BF6FFB8B0AAC6442BD22D1B89D8124115352D9C6439F57C`.

The companion `cas_harness_v2.diagnostic_study_plan.v1` source SHA-256 is
`20EFE11D953D6F6831BA3CF404292328B3A955DD3CA0DE250D18D66204D517C8`;
its test source SHA-256 is
`9DA80335E4C6A554A890C98DF296635DADCF2EDFD63BC3ED65890A8960770696`.
It freezes exactly 160 groups and 480 ordered cases, a 488-reference plan
dependency closure, and a 489-reference closure for each per-case diagnostic
Study request. The diagnostic Study request and Stage C capture request retain
different schemas, media types, bytes, and identities: the former references
the latter, and media coercion is forbidden.

These additions remain `STRUCTURE_ONLY / NON_AUTHORITY`. The newer frozen
diagnostic tranche now supplies typed authorization/terminal-v2 carriers, a
same-host one-attempt lifecycle, exact 480-row phase coordination, worker-local
archive admission, locked fitting, and one create-once freeze-or-reject
disposition. Those shapes still do not supply authenticated runtime execution,
trusted time, WORM/external anchoring, out-of-band execution/read prevention, or
HTTP/container wiring. No activated Stage C preregistration or authorization,
real-Qwen model run, provider call, outcome, or Packet exists. Stage C remains
`DESIGN ONLY / EXECUTION UNAUTHORIZED / EXPERIMENT NOT_STARTED / OPEN / RING 4 /
NOT LICENSED / HELD`.

## Additive Stage C full-vector capture structural candidate

The repaired isolated worker seam in
`live-trace-worker/app/runtime/stagec_capture.py` consumes canonical exact-byte
`cas_harness.stagec.capture_request.v1` and non-authorizing
`cas_harness.stagec.authorization_projection.v1` artifacts and emits a
canonical exact-byte `cas_harness.stagec.capture_index.v1` artifact. It obtains
the exact `model_loader.LoadedModel` singleton and postchecks that carrier after
the call. Strict replay validates the index and semantically decodes the input
IDs, attention mask, layer-0 vector, and layer-18 vector from the four bound raw
array artifacts. A process-local result seal detects later in-process mutation,
and local and global forward-hook registries must be restored exactly.

The seam reports only call counts it directly scopes: one direct capture model
call and zero direct generation API calls. Broader model-forward, generation,
intervention, and startup-canary totals remain `NOT_ATTESTED`. Its artifact
location and durability fields remain `IN_MEMORY / NOT_DURABLY_RETAINED`.
Focused regression evidence is 119/119, with node-ID digest
`E81D7234171B311720A356A36A0B6CEE06B9C564E7FF91386CAFDEA21B503144`,
source SHA-256
`4EA4C57FD412BA811993895AE37E82BEFC13B7AA220C63CAF871CB49D88500F1`
and test SHA-256
`B0DC77EEE955DE8424B11AD02CF5AD5D67C0D4F5BE5DC57A6E285A9B8AC60D30`.
The focused local-archive receipt is 32/32 with node-ID digest
`1306211016B398F44EB57FC855B87BAB2A8AFB75C32B4A4516C53FA77570395F`.
The last committed `b96c2c12` authoritative locked full-worker same-process
receipt is **PASS 576/576**
with 1,728 ordinary setup/call/teardown reports, zero subtests, warnings,
errors, or deselections, and exact Python-ordinal node-ID digest
`F454C598E8E38AF1B6C813BA124EB943E155EB3B927FACB28F4B47C758804C9F`.
The worker tree was `__pycache__`-empty after this replay.
Independent neutral QA found no P0/P1 within the declared `STRUCTURE_ONLY`
scope; that finding is not independent external replication.

The separate worker-local archive source and test SHA-256 values are
`52E444142F5C3D8FC7F0AFC983DE060EFCACCC8975C61F97B48D5BDA52226055`
and
`6D7B3440CEDD02BD6E351CCA6D1E5494F4D3FBC58D0A9470D681FEF65FBBB472`.
It create-only retains the request, authorization projection, capture index, and
four raw arrays, then publishes a reread-verified manifest. It is host-local,
nonrelocatable, same-absolute-path/file-identity bound, and covers only
manifest-listed members. Read-only permission bits, file `fsync`, and immediate
reread do not establish WORM retention, trusted time, a closed-world directory,
capture provenance, or a non-caller-selected external anchor. It retains a
separate local copy; it does not rewrite the capture-time
`IN_MEMORY / NOT_DURABLY_RETAINED` statements.

The worker-output/post-terminal source and test SHA-256 values are
`D28908786C38DCAD63B39B51A82B51FAEF888CCA9DA9552CC00BE37785777D3A`
and
`9564623A3001440AAA0E2CA51667CED9AF23127051BF57776CBD5ED289130624`.
They exact-replay the acyclic `capture archive -> worker output -> terminal
receipt -> outcome index` association for completed rows. That legacy carrier
alone does not attest execution order or retry count, coordinate failed rows, or
strictly admit the worker archive loader's exact object. The additive local
lifecycle, phase coordinator, and worker admission factory below close those
bounded structural shapes without changing this carrier into authority.

## Additive diagnostic execution, coordination, fit, and disposition candidates

The exact source/test pairs and bounded receipts are:

| Component | Source / test SHA-256 | Receipt |
|---|---|---|
| execution-v2 contract, child binding, authorization, and terminal union | `7C16F098046E533176A1FC37B1F3D303C028B9750CD4132DECE1768858E3623F` / `C4A592645136E2FAE4D215E85E0427EB52C7CCEE6DB6E800EF8D372C5FBC5199` | 47/47 PASS |
| per-attempt lifecycle | `F4FA2A4290F093A6305E7D428294D33ACBEECF8231A8E9A4B14A705170F5A8A6` / `09B20960AC9CE828D8415FB652B10F1BDB2E847298979F3C9D7ECCAC4413A64E` | 55/55 PASS, 29.86s |
| phase coordinator | `B21B857A5D94EA48CB8B78890D58039E9D8D876CBC14491F6FDE94FB6FA7AFF7` / `5A5C4BF5A34B48A2870F5412419F005D0D20F4B60C0B61FCB51B742895824BC5` | 5/5 nonheavy, 2/2 rejected-480/payload, and 1/1 clean-480/access PASS |
| exact locked calibration fit | `4E0A196F3DEF71A29C3EB1425FC777727377154BF010580570ACB2115F6B21DF` / `1418C49D72FD9893ACCFDF264F9D5D9BFB9B85D0699BA8EF6729444A26102021` | 10/10 exact locked PASS, 356.75s |
| one calibration disposition | `161EF93030FD42632D03B0ABD5CBBA3ECA084F7198B7E889C96D6FD10A6C9196` / `CDB3218AA9CA8A3796062764D45A946408C9915BFD0BB134C0A981BA3C66BF95` | 11/11 final-byte nodes PASS across two bounded split runs |
| worker-local archive admission | `169AEE6754EB44ECBBF9B636505B4EBD2D7D1C031D9736FBCA37A8044613D305` / `4D236BCC19096CF186A2CBCC67DF80B59CE7AB7D9BC29E1D261CA568F7BB110B` | 18/18 PASS; local-only |

The execution union admits exactly `COMPLETED`, `FAILED`, `INDETERMINATE`,
`REJECTED`, and `EXPIRED`. The local lifecycle and phase store permit one
attempt per exact subject, preserve all five terminal branches, reject a 481st
or late issuance, close any rejected batch without replacement, and permit one
aggregate access only after exact clean 480-row reconciliation. The worker
factory freshly reloads and semantically replays all seven archive members; its
case ordinal remains authorization-declared and requires canonical controller
replay.

The fit carrier accepts only the exact aggregate-access dataset and independently
derives the layer-18 and layer-0 models under `numpy==2.5.1`,
`scikit-learn==1.9.0`, and `scipy==1.18.0`. It fixes `StandardScaler` and
class-balanced L2 `LogisticRegression` with `lbfgs`, `C=0.25`,
`max_iter=1000`, and `random_state=42`, plus the exact binary64 threshold
candidate and higher-threshold tie rule. The same-file disposition slot permits
one `CALIBRATION_FROZEN_NONREPORTING` or
`CALIBRATION_REJECTED_NONREPORTING` result. Packet creation, evaluation
authority, reporting, claim/product/public promotion, and license grant are
forbidden.

The phase receipt timings were 50.70s, 80.32s, and 238.10s. The disposition
split timings were 210.72s for 8 passed/3 deselected and 870.18s for 3
passed/8 deselected. This is complete final-byte focused coverage across two
runs, not themselves a single-process authoritative full-suite receipt. The
last committed 306-Harness/576-worker receipts remain bound to `b96c2c12`, and
the new diagnostic tranche now has the separate authoritative full-suite
receipts below. The positive post-access `NO_ELIGIBLE_THRESHOLD` rejection
branch has not been executed.

The authoritative same-process standard Python-3.14 Harness receipt collected,
started, and finished 437 nodes. Exactly 431 had all phases pass; the six exact
named fit/disposition nodes setup-skipped because `numpy==2.3.5`,
`scipy==1.17.1`, and `scikit-learn==1.8.0` do not satisfy the frozen
2.5.1/1.18.0/1.9.0 runtime lock. Those skips are mismatch evidence, not PASS
results. The run emitted 1,305 ordinary reports and 163 passing subtests,
recorded no collection or internal errors or deselections, left the isolated
pycache empty, exited pytest 0, and bound exact node-ID digest
`85AACF5BD7909979F4EC8DB7680B279D0795D32525973BC00BE16EC0157CF5E8`.
Positive exact numerical evidence remains separate under Python 3.12: fit 10/10
and eligible disposition 3/3.

The authoritative same-process worker receipt collected, started, finished,
and passed 594/594 nodes, emitted 1,782 ordinary reports and zero subtests,
warnings, errors, or deselections, left the isolated pycache empty, exited
pytest 0, and bound exact node-ID digest
`B822D8EFC57C45712FD960BC14E2FB271FDD72C91CF29D665EBAB7ED27AE0D9B`.
Both receipts are local `STRUCTURE_ONLY / NON_AUTHORITY` evidence only.

These seams remain non-authorizing. Artifact replay has no trusted external
anchor; capture and diagnostic-chain seals are process-local; model files are
not rehashed at capture; and rendered-prompt, activation, and logits provenance
is not independently recomputable. Hook use is serialized. There is no
authorized HTTP/diagnostic Study runner, and the tests use only fake/tiny local
tensors rather than the real pinned Qwen model. Independent adversarial review
found no P0/P1 within the declared `STRUCTURE_ONLY` scope, not outside it. No
prompt-injection detector, steering result, Evidence Packet, provider, or
RunPod job exists; known spend for this tranche remains `$0.00`.

Still open outside this isolated kernel:

- a portable authorized Gate 4 external-source dependency: two registered live
  paths drifted, and the historical structural rerun now depends on local
  `tksCAS` commit `130168b3bd215e2975c8eb88776ed2be3b1c2227`, blobs
  `af187b5d85f3ebbf90a802dcfc68b81924ff57ce` and
  `fab6c93ba24ebdd13feb396a22d122def3ad3cc1`, under the exact boundary
  `RETAINED GIT BLOB / LIVE REGISTERED PATH DRIFTED / LOCAL NONPORTABLE / NO CURRENT-SOURCE EQUIVALENCE`; this provides neither current-source validation
  nor experiment authority;
- authorized HTTP/container coordinator wiring and worker-route admission;
- one real pinned-Qwen Stage C/C-Cal run plus exact capture-time model/tokenizer
  revalidation;
- positive execution of the post-access `NO_ELIGIBLE_THRESHOLD` rejection
  branch and one authoritative integrated Harness/worker replay of this tranche;
- prevention and independent discovery of out-of-band execution or outcome
  access;
- durable append-only storage and trusted outcome-access ordering;
- materialized, non-caller-selected trust roots and signature verification;
- trusted time, nonce/replay control, one-use run consumption, and protection
  against selective reporting across multiple packets;
- provider-backed live-worker execution and independent executor/auditor
  validation of the bounded protocol mapping;
- hermetic execution and environment attestation, including complete
  standard-library/test/native/descendant closure, an immutable read-only
  snapshot, privileged/metadata-preserving ABA protection, hosted/auxiliary
  loader alias hardening, and independent reproduction; the repository-local
  same-process, hardlink, reparse, descriptor, and ordinary replacement
  controls do not close `G5-ENGINEERING-002`;
- independent numerical implementation and authenticated reviewer identity;
- real person, affiliation, and organizational independence beyond normalized
  declared identity strings;
- cross-packet artifact identity and semantic/media-type equivalence when
  byte-different artifacts are relabeled or cloned;
- authorized held-out replication;
- external peer review and claim-language sign-off;
- downstream enforcement that `PacketAssessment` is evidence data and never an
  authority, authorization, or capability token;
- every C-Eval, Packet, authenticated/scientific result, product, public,
  license, and disclosure authority;
- Gate 5 control matrix, manifest, verifier, and gate decision; and
- every production, licensing, compliance, disclosure, and public-route gate.

Until those separately authorized obligations close, the six axes remain:
document `DRAFT / OPEN / NOT FROZEN`; decision `OPEN / KEEP_OPEN`; engineering
`RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`; experiment `NOT_STARTED`;
license/disclosure/canon `NOT LICENSED / HELD / NOT FROZEN`; and live/product
route `UNAVAILABLE / NOT AUTHORIZED`. No live, scientific, canon, product,
license, or disclosure authority is created.
