# Project Coherence Phase 0 changelog

All dates use the repository's working timezone. This changelog records control-package changes, not product releases.

## 2026-08-12 - Offline synthetic Evidence-Coverage Dispersion Stage 1 candidate

### Added

- A corrected v0.2 ECD specification and separate canonical/package-mirrored
  Stage 1 module for exact required-cell support counts, gaps, reduced-rational
  coverage/HHI/population-CV2 summaries, and deterministic advisory next-test
  ordering.
- Four additive schemas, four media types, 27 public exports, exact resource
  ceilings, frozen synthetic fixtures, arithmetic invariants, adversarial
  strict-input tests, package provenance/export integration, and a separate
  Gate 5 review receipt and `OPEN_ENGINEERING` criterion.
- Explicit rejection of all Unicode general-category `Cc` controls; explicit
  identity-only treatment for externally admitted `ArtifactRef` values; and an
  explicit pure-Python reflection boundary that invalidates all in-process
  seal claims after verifier-state mutation.

### Verification state

- The canonical focused suite is `118 / 118 PASS`; the package mirror suite is
  `13 / 13 PASS`; canonical and packaged sources are byte-identical. Independent
  frozen-byte source/package review reports P0/P1 `0 / 0`.
- Current run `ecd-stage1-suite-receipts-20260812T182522-d7b2ef6d` passed the
  `1,570`-node Harness inventory at node-ID SHA-256
  `8887298311BBFAFFF45421F43FEEC4E68160FF84D360EF108743E9EF90858510`;
  its six exact setup skips remain mismatch evidence rather than pass. The
  `99`-node adapter also passed at node-ID SHA-256
  `B84EB29C59563DD0270C3BD8B230D604D59A2E45D38B9E375C7FA697468D656B`.
  The complete 12-suite map is `2,790` configured nodes. The published
  Phase 0 `1,452`-node Harness receipt predates ECD and is preserved unchanged;
  it covers none of the new `118` nodes.
- The archived Harness receipt is `295,566` bytes /
  `A7AF4C73517DF93B1FFE04979D8D3688E61DBE730638FCAE7963E9D8BC5471A5`;
  the adapter receipt is `16,663` bytes /
  `7AFCE687047363D2B27E53D7978E220B6B4F36C85DFA6FA6DEA3B5FDA5AE9FBB`.
  Both bind issuance verifier `BFB3DE9B...7CF3`, manifest `9D94072D...0473`,
  and runner `EB7D2D66...60B13`; independent receipt audit reports P0/P1
  `0 / 0`.
- First integrated attempt `first-20260813T023503Z-f3de22ee` completed suite
  execution but retained a stale Phase 0 worker loaded-code comparator. It
  emitted no exact PASS line and remains `FAILED / STALE PHASE0 WORKER RECEIPT
  COMPARATOR / EXIT 0 WITHOUT EXACT PASS LINE / STRUCTURE_ONLY /
  NON_AUTHORITY`. Its result is `3,202` bytes /
  `F6CC658B34C5BEDDD84DD7FF501BD36575942D6675EDDF8D9CBF3C9DEF0AB303`;
  stderr is `500` bytes /
  `1A50674944CFADFB705D584EDFC70F192E23109A22918F6A97E38A0C67C773D7`;
  stdout is empty.
- Separate ECD-only worker run
  `ecd-stage1-worker-receipt-20260812T202101-c1cb7da6` passed `732 / 732`.
  The receipt is `98,968` bytes /
  `60EA620DA91F29E0D1F059ECCFF1BDC4DD206EC68BB17AD92D4C566401380342`;
  pre-test/complete loaded-code digests are `5859DC61...94B7A1` /
  `47C816D2...0BFAB`. It is promoted only on ECD Stage 1 surfaces; published
  Phase 0 worker current and historical receipts remain unchanged.
- The current manifest is `712` artifacts / `478` Python artifacts, with
  `2,314` executable-shadow paths and `1,284` integrated postflight identities.
- Audited intermediate integrated run `retry-20260813T033443Z-64762d21`
  exited `0` with the exact PASS line once across `12 / 12` suites and `2,790`
  configured nodes, `53` criteria / all `22` required OPEN boundaries. Result,
  start, stdout, and stderr are respectively `3,200` B /
  `163E7D60111978CD40C191680DD49DF33B562E7C4C842A915544C281E52936F8`,
  `2,597` B /
  `6FFA96A6C7B8EC3E2CC5A9482A5AA46452544D701A552D8501DBD0314D1F000F`,
  `12,118` B /
  `61D027192FF7E8B89BB85854F72D834AE2C97768915C387F6745D5DFF9424EDD`,
  and `0` B /
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
  Before/after verifier, manifest, and runner were exact at `976,022` B /
  `9ECEEE47D33855135A9A7A2749CD0239EDEBC51AA0EF008B433C15C0837B31B1`,
  `205,702` B /
  `C6C50718BEB5D9EC4FDD2772B92483747C113CF00EB8A6BEAE38995D811CC859`,
  and `121,525` B /
  `EB7D2D661BFE262C1E3BB4657E418EADE8339F35D1089C7AE6A87EFC6A360B13`.
- Mandatory correction: the supervisor start field
  `8605BCA3935F14370900963A6D48E4C236C69A8A9D3792F3E776AFE677546355` is stale
  pre-worker-promotion state and is explicitly rejected as a binding for the
  run. The actual launch tree was independently reconstructed post hoc as
  `2,228` bytes / `15` paths /
  `20E463B9A88D016E7C2E27991E282EDA44DC65A2D7762C532015A7B129C10F70`;
  the correction artifact is `1,436` B /
  `5854A202FB06A59ABC1BF37225A0712AC8141E2B9D36762AD0F3A38D5AD28FC8`.
  The reconstruction is not trusted time or
  WORM and adds no authority.
- All 12 exact suite identities are bound. Harness `1,570`, worker `732`, and
  adapter `99` use node/loaded-code pairs
  `8887298311BBFAFFF45421F43FEEC4E68160FF84D360EF108743E9EF90858510` /
  `973AD5E7905130A17D29798C94593D5BA3BFFE807AC2C82F0AF2AB89A4FE77A5`,
  `F53562BAECCC4982B402A9A747F8CADC29468B5F14D8B4A8C17CFC2A8E89B568` /
  `47C816D2873400775F353F6832DD6656CFB0B19471BD596B3829D530ACE0BFAB`,
  and `B84EB29C59563DD0270C3BD8B230D604D59A2E45D38B9E375C7FA697468D656B` /
  `6EDFF27912DC8C73FF508C11D850F18E6A6146C6B93238FA431E00D49B12299F`.
- Current ECD status is `CURRENT HARNESS, WORKER, AND ADAPTER SAME-PROCESS
  RECEIPTS PASS / AUDITED INTERMEDIATE INTEGRATED 12-SUITE REPLAY PASS / FINAL
  UNCHANGED-TREE REPLAY PENDING / STRUCTURE_ONLY / NON_AUTHORITY`. Manifest
  rebuild after receipt promotion, independent promotion audit, and the final
  unchanged-tree integrated replay remain open.

### Boundaries

Stage 1 is `R&D / OFFLINE SYNTHETIC / ADVISORY_ONLY / NON_AUTHORITY`. It adds no
adjacency, rates, uncertainty, Evidence Packet, production, provider, model,
Stage C, decision, licensing, disclosure, or canon authority. CV2 remains
`EXPERIMENTAL / NOT PROMOTED`; Stage 2 is blocked until a separate
preregistration defines a genuinely non-equivalent CV2 action rule and complete
policy-independent common-horizon outcomes against all frozen simple baselines
and the CV2-removed ablation.

## 2026-08-07 - Gate 5 retained-evidence reconciliation

### Added

- `gate5/GATE5_ENGINEERING_EXECUTION_RECONCILIATION_v0.1.json` canonically
  binds the retained local engineering chronology: GPU canary v0.1
  fail-closed startup, GPU canary v0.2 six-arm mechanical pass, joined v0.1
  pre-model fail-closed run, and joined v0.2 one-invocation
  `SUCCESS_NO_PACKET_RECORDED` run. It records zero provider calls, `$0.00`
  known spend, and the explicit absence of detector, steering, Packet-v2,
  authenticated-science, replication, product, and disclosure claims.
- `gate5/history/HISTORICAL_CAPABILITY_EVIDENCE_RECONCILIATION_v0.1.json`
  binds the recovered deterministic instruction-integrity shadow scanner
  (development fixture 15/15, held-out fixture 12/12, `mode=shadow`,
  positive disposition `FLAG_FOR_HUMAN_REVIEW` only) and the retained
  Qwen V6 prompt-injection and Pythia-160M steering negative studies to
  exact Git commits and blob OIDs. Promotion and rerun inference are
  prohibited; the negatives remain controls against outcome shopping.

### Corrected

- Refreshed stale suite receipts to the already-committed test surface:
  Harness v2 `155` tests + `106` subtests, strict worker-protocol `35` + `45`,
  complete worker `391/391`, prospective lifecycle `134/134`, admitted
  adapter/reconciliation `98/98`, and the retained-evidence suite `27/27`.
  No test was added or relaxed; the historical v0.2 OCI candidate keeps its
  own `364/364` issuance receipt unrewritten.
- The Gate 5 verifier now redirects the integrated Gate 4 `compileall`
  bytecode into a verifier-owned temporary directory so a dependency check
  cannot leave `__pycache__` mutations inside the postflight-hashed surface,
  and verifies the historical container receipt against its exact
  source-commit blobs instead of current worker bytes.
- The raw-text status guard accepts the phrase `Gate 5 closed` only inside
  the explicit forbidden-wording list and continues to reject it everywhere
  else.

### Boundaries

Gate 5 remains `OPEN / KEEP_OPEN`; engineering remains `RING 4`; the
scientific experiment remains `NOT_STARTED`; license/disclosure/canon remain
`NOT LICENSED / HELD / NOT FROZEN`. This tranche reconciles retained evidence
only; it creates no new execution, claim, or authority.

## 2026-08-06 - Gate 5 explicit controller-continuation successor

### Added

- Exact controller-only outcome-seal, Evidence-Packet-v2 attachment, and
  explicit-nonreporting request envelopes, capabilities, private routes, and
  continuation DTOs. The feature remains default-dark and excluded from
  OpenAPI.
- Fresh request-local outcome reconstruction from retained authorization,
  terminal, lifecycle, and outcome facts. The create-only outcome reservation
  preserves one winning declared time and its explicit untrusted provenance.
- A mandatory create-only `PACKET`-versus-`NONREPORTING` reservation that binds
  operation, request, dependency plan, parent head, clock observation, and the
  exact planned final artifact before any final reporting transition.
- A reconciliation storage-wrapper v2 whose returned ID and digest identify
  the same retained bytes. It binds a hashed strict per-run lifecycle/artifact
  snapshot to the separately limited configured-scope report.
- One real FastAPI-to-admitted-adapter regression traversing authorization,
  consumption, output retention, terminal acceptance, outcome sealing, and
  explicit nonreporting without enabling a live provider lane.

### Corrected through adversarial review

- Made the planned reporting artifact part of both ordinary and concurrent
  reservation equality. Packet/nonreporting lifecycle finalization can no
  longer bypass the reservation, and direct lifecycle-service calls derive a
  deterministic request identity rather than taking an unreserved legacy path.
- Rejected a duplicate claim-ledger artifact source in authorization envelopes,
  including both byte-identical and conflicting duplicates.
- Rejected ambiguous duplicate security/entity headers and every transfer-
  encoding request before callback-nonce consumption. Corrected fresh-chain
  replay, backward-clock poisoning, claim-ledger identity selection,
  continuation bindings, and reporting dependency replay.
- Distinguished direct caller-declared time from process/injected-clock
  provenance without promoting either to trusted time.
- Rejected forged non-content-derived reconciliation report IDs and preserved
  immutable prior receipts when a strict run head evolves.
- Bound the closed nonreporting reason into the create-only reporting
  reservation, rejected backward lifecycle event time at every transition and
  during full replay, and made controller reads repair exactly one verified
  event-first/index-second pending successor while rejecting corrupt or
  divergent pending histories.
- Required exact Packet/nonreporting event-detail shapes, full indexed-history
  verification before every replay, append, repair winner, and fresh-success
  return, and exact verification of a concurrent repair winner before it can be
  exposed as lifecycle state.
- Extended full replay to verify every indexed event envelope plus lifecycle,
  subject, nonce, finalization, registry, reservation, builder, and backend
  profile cross-bindings. Canonical event identities can no longer be hidden by
  a forged payload run ID. A bounded fingerprint-refresh loop now converges on
  valid later state after stale reads, post-CAS acknowledgement races,
  simultaneous exact retries, and concurrent pending-successor repair.
- Moved outcome/reporting reservation replay and state checks behind the same
  repair/full-verification loop, closing corrupt-history and interrupted-write
  recovery gaps. Event-record verification now also binds tenant and event kind.

### Verified bounded receipts

- Prospective lifecycle/SQLite/default-dark route: 130/130, node-ID digest
  `0CA9217040958125285BFA0F6A7C6D517808B4AC4F4078C152620190767B6BB0`.
- Packaging/snapshot/envelope/context/admitted-adapter/reconciliation: 90/90,
  node-ID digest
  `761038779E00511179D4FC5AA3522829D9BDEFB37C231061D04FB3AAD541F733`.
- A focused development run across the changed route, lifecycle, service,
  adapter, authentication, and bridge surfaces passed 187/187. These are local,
  unattested software regressions, not live execution or scientific evidence.

### Preserved open boundaries

- Gate 5 remains `OPEN / KEEP_OPEN`; engineering remains `RING 4 / BOUNDED
  SOFTWARE CANDIDATE TESTED`; experiment status remains `NOT_STARTED`; and
  license/disclosure/canon remain `NOT LICENSED / HELD / NOT FROZEN`.
- The lower outcome reservation still lacks a separately immutable planned-
  final-artifact intent; output-retention responses do not yet identify exact
  replay; `INDETERMINATE`/`REJECTED`/`EXPIRED` HTTP dispositions, complete
  partial-write/orphan inventory, provider-backed enabled startup, trusted
  time, independent inner-byte WORM retention, cross-host/host-loss authority,
  authenticated execution, independent replay, and every experimental,
  scientific, product, license, canon, and disclosure conclusion remain open.
- The user-reported RunPod balance remains `$107.00`; no RunPod/GPU/paid job was
  launched, known spend for this tranche remains `$0.00`, and no provider
  billing ledger or balance receipt was inspected.

## 2026-08-06 - Gate 5 admitted adapter and bounded reconciliation successor

### Added

- A byte-for-byte application-local mirror of the isolated Harness-v2 kernel,
  an exact provenance record, and a startup verifier that rejects file,
  inventory, authority-boundary, and provenance drift before kernel import.
- An exact default-dark admitted adapter binding controller issuance, worker
  consumption/output/terminal calls, immutable pre-nonce context, joint
  `job_id == subject_id == authorization_id` identity, server-derived Fleet
  configuration, active lease generation, one-time raw authorization release,
  request-bound intake receipt transitivity, and exact redacted route DTOs.
- Server-built `INDETERMINATE`/`REJECTED`/`EXPIRED` dispositions and a
  terminal-safe current-snapshot loader so exact replay remains possible after
  legacy Fleet completion without reopening authorization issuance.
- A fail-closed configured-scope reconciliation service and controller route.
  It joins only injected Fleet configuration, immutable contexts, tenant
  lifecycle rows, artifact indices, and optional bridge indices; marks source
  enumeration failure `UNAVAILABLE`; reports missing/orphan/pending states;
  re-verifies but excludes prior reconciliation wrappers from recursive state;
  and retains canonical exact report bytes without claiming global or
  off-registry execution absence.

### Corrected through adversarial review

- Preserved terminal replay after legacy Fleet state advances to
  `COMPLETE`/`FAILED` by separating issuance-only snapshots from exact current
  configuration snapshots.
- Classified bridge persistence failures as unavailable/retryable authority
  failures rather than caller conflicts; kept bridge binding and immutable
  conflicts distinct.
- Mapped invalid internal DTOs and corrupted retained context to service
  unavailability, while preserving request-originated closed-envelope errors as
  conflicts. Retained authorization digests now require canonical uppercase;
  the lifecycle kernel's canonical lowercase artifact binding uses an explicit
  one-way HTTP translation rather than permissive case normalization.
- Required terminal callbacks to carry and reverify the exact bound intake
  receipt through bridge persistence. Raw lease and credential capabilities
  remain process-local and are never stored or returned.

### Verified bounded receipts

- Worker-terminal bridge: 17/17, node-ID digest
  `FA6C985CD6CAA734034E006BB4BAF6BE9D02269D7312BEE7355E9C3833759C51`.
- Fleet callback/Object-Lock seams: 38/38, node-ID digest
  `D3EAF533FEDB5B03168200AA399AC53A6E2A6F22874EBABEAECEFB227400778D`.
- Prospective lifecycle/SQLite/default-dark route: 76/76, node-ID digest
  `5F1197D70B7AFAD39D01BEBEB4E7397C3E075D74A5BFFA5305C62A0EDB3C7D84`.
- Packaging/snapshot/envelope/context/admitted-adapter/reconciliation: 80/80,
  node-ID digest
  `2E45FCD920E0B52916A7341D2FF766FDC9F7911EC2CB11C27BC3FF8FEC3815FB`.
- These remain `LOCAL_UNATTESTED_HOST_REGRESSION`; they do not establish a
  provider-backed enabled startup, live execution, trusted time, host-loss
  durability, independent reproduction, or science.

### Preserved open boundaries

- Gate 5 decision remains `OPEN / KEEP_OPEN`; engineering is
  `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`; experimental execution remains
  `NOT_STARTED`; license/disclosure/canon remain `NOT LICENSED / HELD / NOT
  FROZEN`; the live/product route remains unavailable and not authorized.
- `G5-ENGINEERING-001` and `G5-TRUST-001/002/003/004/005` remain open. Missing
  HTTP Packet-v2, explicit nonreporting, and outcome-seal dependency envelopes,
  provider-backed WORM/trusted-time/multi-host authority, authenticated
  execution, off-registry completeness, independent replay, and every live,
  scientific, product, license, canon, and disclosure decision remain absent.
- The user-reported RunPod balance remains `$107.00`; no RunPod/GPU/paid job was
  launched, known spend for this tranche remains `$0.00`, and no provider
  billing ledger or balance receipt was inspected.

## 2026-08-06 - Gate 5 dark prospective run-lifecycle successor

### Added

- A backend-qualified prospective lifecycle registry that reserves a run subject
  and run-nonce digest before authorization construction, releases the raw nonce
  only once, uses same-host `StateStore` compare-and-swap for one-use
  consumption, hash-links terminal/outcome/packet-or-nonreporting transitions,
  and reconciles tenant-visible lifecycle records. Its default nonce factory is
  `secrets.token_bytes(32)`, but the factory is injectable and current runtime
  provenance is unattested. Its SQLite evidence is close/reopen persistence and
  two-connection same-file arbitration only, with no process-crash, OS-restart,
  power-loss, host-loss, replication, or independent-attestation claim.
- A dark orchestration service for exact authorization, server-built
  consumption, retained output bodies, `SUCCESS`/`FAILURE` terminalization,
  reserved outcome sealing, strict Evidence Packet v2 attachment or typed
  nonreporting, and event-bound wrapper replay. Synthetic Object-Lock receipts
  bind the canonical outer wrapper, not independent retention of the inner exact
  carrier.
- A private, default-false, OpenAPI-hidden exact-body router. Callback nonce rows
  now bind the server-observed method, exact path, job/run identity,
  authorization digest where applicable, and body digest/length for every
  accepted route request. These authentication rows are distinct from the
  terminal-only bridge acceptance wrapper/index. The terminal route body remains
  opaque until the missing strict adapter validates it, and customer-JWT
  fallback is forbidden.
- A standalone exact active-lease-generation validator and a sealed-safe bridge
  authorization replay port.

### Corrected through P0 adversarial review

- Prevented retroactive/terminal-first authorization by reserving the subject
  and nonce digest before invoking the builder; interrupted builders remain
  quarantined and reconciliation-visible and cannot reissue the raw nonce.
- Required Packet v2 to match retained terminal outputs and transitive artifact
  bodies; failed runs use a server-built nonreporting envelope instead of a
  fabricated favorable packet. Packet and supplied dependency bytes are
  structurally prevalidated before the first write, but a later storage failure
  can leave already written wrappers outside the lifecycle event chain.
- Preserved the missing integration boundaries: lifecycle consumption currently
  trusts passed lease facts rather than calling the standalone active-lease
  validator; the bridge does not receive the enclosing request-bound intake
  receipt; service/route paths do not record registry-level
  `INDETERMINATE`/`REJECTED`/`EXPIRED`; and reconciliation does not enumerate
  orphan/losing wrappers or every pending output.
- Preserved the missing run-identity adapter: the route hashes `job_id`, the
  lifecycle hashes `subject_id`, and the service requires
  `subject_id == authorization_id`, but no admitted adapter enforces
  `job_id == subject_id == authorization_id`.
- Recorded empty-tenant semantics explicitly: an empty configured tenant view
  has zero counts, `has_registered_runs=false`, and
  `all_runs_reporting_disposed=false`; an issue-free structural result does not
  prove that no off-registry execution occurred.

### Verified bounded receipts

- Harness v2 kernel/history/verifier: 150 tests and 99 subtests. The strict
  worker-protocol subset passes 30 tests and 38 subtests with canonical node-ID
  digest
  `534CF4550FF56F3EA5F4235680CDB89A91784D1CEE0B7CB7ABDF9DE1C7B3E7FF`.
- The API/launcher/fleet/state suite passes 78/78; the dark bridge passes 8/8;
  and the callback-auth/fake-Object-Lock seam suite passes 35/35. Their
  canonical node-ID digests are, respectively,
  `603DEBF7DF9AC7B5A69543C3736F4CD38692D3330690A7559A6F9DE6F0E2AF77`,
  `6B0B52C30FA70C52E0EA5AC3B15221F4E5B8BC8337AA53B04972B3E543177969`,
  and `A340034084006FC437AB1F9724FB45D3AE09555F5D302FC36CCD6CF53EC28F57`.
- The prospective lifecycle/SQLite/default-dark-route suite passes 48/48 with
  canonical node-ID digest
  `B7B87D52351B21039A83E4B526BCAEDE0E8F3E11F79E162480FB007375421F44`.
  All are local same-process engineering receipts, not independent, live, or
  scientific evidence. The historical 364/364 worker receipt remains unchanged.

### Preserved open boundaries

- Router code now exists, but it is not an admitted or enabled route. Main sets
  the service port to `None`, excludes the router from OpenAPI, and refuses
  startup when the flag is enabled without both the isolated root package and a
  packaged lifespan adapter. No such adapter or explicit HTTP outcome-seal path
  is wired.
- `G5-ENGINEERING-001` and `G5-TRUST-002/003/004` remain `OPEN_ENGINEERING`.
  Trusted time, independent inner-byte/WORM authority, multi-host and host-loss
  proof, authenticated execution, complete anti-selective-reporting coverage,
  independent replay, live experiment, science, product, license, canon, and
  disclosure authority remain absent.
- The structural verifier binds declared schemas, wording, bytes, and local
  regression outcomes; it cannot authenticate substantive content truth or
  establish scientific validity.
- The user-reported RunPod balance is `$107.00`; no RunPod/GPU/paid job was
  launched, known spend for this tranche is `$0.00`, and no provider billing
  ledger or balance receipt was inspected.

## 2026-08-06 - Gate 5 initial strict worker-protocol candidate

This is the predecessor checkpoint. The lifecycle-successor entry above is the
current semantic boundary; the facts below are retained as chronology.

### Added

- Strict exact-byte `cas_harness_v2.worker_authorization.v1` and
  `cas_harness_v2.worker_terminal_receipt.v1` carriers binding the current
  FleetJob layer range, shard, ordered method/output assignments, exact lease
  model identity, preregistered controls/falsifiers, structural run nonce, and
  fixed `Ring 4 / NOT LICENSED / HELD` authority limits.
- An initial pre-outcome-only dark research adapter that requires injected worker
  loaders and a current server FleetJob snapshot, then stores one retry-stable
  terminal wrapper/index
  plus a separate server-authored acceptance wrapper/index for each consumed
  transport callback nonce through the existing immutable repository seam.
- An additive durable fleet-callback nonce receipt projection that can be
  re-read after SQLite restart while retaining the distinction between
  transport replay protection and still-open authenticated one-use run
  authorization.

### Corrected through adversarial review

- Removed the transport callback nonce from worker-authored immutable terminal
  bytes because the live client creates it only at HTTP-post time and an exact
  retry must use a fresh callback nonce.
- Added exact terminal replay from stored authorization bytes after outcome
  sealing, permitted only when the seal binds the same terminal artifact and
  execution-completion time; public post-outcome authorization loading remains
  rejected.
- Preserved partial failures as an ordered produced/missing partition with
  typed errors and mandatory
  `QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY`; completed outputs remain
  `DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED`.
- Made injected strict-loader provenance an explicit unresolved deployment
  trust boundary instead of treating byte-retaining duck types as attestation.

### Verified bounded receipts

- Harness v2 kernel/history/verifier: 146 tests and 96 subtests. The strict
  worker-protocol subset passes 27 tests and 35 subtests with canonical node-ID
  digest
  `1F18A5854B5AF20FE87D9C281AAE0CC0B1F1DC8CB81748A47DC49CB7BC4A549A`.
- The dark bridge passes 7/7; the callback-auth and fake Object-Lock seam suite
  passes 34/34; their combined local replay passes 41/41. These are
  `LOCAL_UNATTESTED_HOST_REGRESSION` receipts, not live provider or scientific
  evidence.

### Preserved open boundaries

- `G5-ENGINEERING-001`, `G5-TRUST-002`, `G5-TRUST-003`, and `G5-TRUST-004`
  remain `OPEN_ENGINEERING`. No production route, attested loader provenance,
  authenticated one-use run nonce, trusted time, complete run registry, live
  S3/Object-Lock receipt, full outcome-access/Evidence-Packet sequence,
  independent executor-auditor replay, GPU experiment, science, license,
  product, canon, or disclosure authority was created.
- Gate 5 remains `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT
  FROZEN`. No RunPod job was launched.

## 2026-08-05 - Gate 5 retained evidence and same-run verifier hardening

### Added

- An additive raw build/security receipt and ten exact retained payloads: the
  original OCI index, platform/config/attestation records, BuildKit history,
  SPDX and SLSA statements, plus a current direct Scout 1.21 SPDX and SARIF
  report. The historical v0.2 issuance-time receipt remains byte-unchanged and
  continues to record that those raw payloads were unavailable at issuance.
- A local Windows runner lock over three interpreter files, 508 exact files
  owned by seven pytest-support distributions, and three `.pth` files disabled
  at startup by `-I -S`. Pytest and explicit-plugin origins are checked against
  the exact file lock before import. The child hashes and parses the same
  identity-checked lock byte buffer.
- Same-process collection/start/finish and exact setup/call/teardown/subtest
  receipts for each admitted suite, with ephemeral digests for executed node
  IDs, outcomes, locked import origins, pre-test module endpoints, and final
  module endpoints.
- Descriptor-bound repository observations that reject symlink/reparse path
  components and hardlinked leaves, compare pathname/open-handle/ancestor
  identities, separately preserve the non-self-hashed manifest identity, and
  recheck the integrated Gate 5/Gate 4/history surface after child execution.
  Ancestor checks bind stable structural identity (device, inode, type, link,
  and reparse state) while intentionally excluding directory size/timestamps,
  which can change when unrelated Codex work occurs outside the worktree.

### Verified bounded receipts

- The intended manifest surface contains 340 hash-bound artifacts, including
  298 syntax-checked Python files, while retaining the exact 537-file historical
  recovery and transitive Gate 4 dependency.
- Harness v2 kernel/history/verifier: 119 tests and 61 subtests, comprising 94
  active kernel tests, 4 historical-recovery tests, and 21 Gate 5 verifier
  red-team tests. Live worker: 364/364; API/launcher/fleet/state: 76/76; focused
  numeric red team: 32/32. These are local same-process engineering receipts,
  not scientific or independently attested execution.
- The direct Scout payload reports 0 critical, 0 high, 3 medium, and 4 low
  findings. Current Ubuntu-source triage leaves six records vulnerable or
  fix-deferred and identifies one scanner/vendor conflict because the exact
  scanned `dpkg` version is vendor-fixed.

### Preserved open boundaries

- Gate 5 remains `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT
  FROZEN`; `G5-ENGINEERING-002` remains `OPEN_ENGINEERING` and
  `G5-ENGINEERING-003` remains `OPEN_SECURITY`.
- The endpoint module inventory contains only surviving `sys.modules` file
  origins and maps cache paths to source. It does not capture
  transient/unloaded/dynamic execution, exact loader-executed bytecode,
  unresolved/deleted origins, native-loader dependencies, descendant
  processes, or files absent from upstream distribution `RECORD` inventories.
- Complete standard-library/test/native/process closure, an immutable and
  independently attested snapshot, trusted time/WORM ordering, privileged ABA
  resistance, independent reproduction, real GPU execution, worker-to-kernel
  integration, scientific validation, licensing, product authority, and
  disclosure authority all remain open.

## 2026-08-05 - Gate 5 successor dependency/container candidate hardening

### Added

- A successor v0.2 dependency/container candidate receipt binding the repository
  build controls, 73-distribution lock, exact worker application tree, recorded
  OCI identities, exact five-file Pythia identity, offline CPU engineering
  canary, native dependency preflight, and fail-closed runtime probes.
- Complete Gate 5 direct-or-transitive closure over 325 artifacts, including
  every regular file in the admitted kernel/worker roots, the complete API
  source/resource tree used by the launcher/fleet/state receipt, pytest
  discovery controls, and the unchanged 537-file historical recovery.
- Repository-local rejection of `__pycache__`, bytecode, native-extension, and
  archive shadows before child tests, plus retained red-team checks for forged
  scan status, authority promotion, OCI/source/lock drift, missing controls,
  external-evidence replayability, and post-test rehash ordering.

### Verified bounded receipts

- Harness v2 kernel/history/verifier: 113 tests and 61 subtests, with 94 active
  kernel tests, 4 historical-recovery tests, and 15 verifier red-team tests.
- Live worker: 364/364; API/launcher/fleet/state: 76/76; focused numeric red
  team: 32/32. The worker and API receipts are
  `LOCAL_UNATTESTED_HOST_REGRESSION`: node-ID hashes come from separate
  collect-only subprocesses and do not receipt the actual executed-node set.
- The integrated static replay binds the unchanged historical v0.1
  model/dependency record and composes the still-OPEN Gate 4 dependency.

### Preserved open boundaries

- Gate 5 remains `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`.
  `G5-ENGINEERING-003` remains `OPEN_SECURITY`.
- BuildKit SPDX/SLSA and Docker Scout facts are
  `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`: raw payloads were not retained, are
  not repository replayable, and have no independent trust root.
- The recorded package scan has 0 critical, 0 high, 3 medium, and 4 low unfixed
  findings; the direct filesystem scan is `INCOMPLETE / PENDING`.
- Mutable host/user-site runner integrity, same-run executed-node identity,
  authenticated read-only snapshots, hardlink/reparse/ABA resistance,
  independent reproduction, real GPU execution, worker-to-kernel integration,
  scientific validation, licensing, product authority, and disclosure authority
  remain open. The CPU canary was engineering preflight only and did not create
  an admitted experiment, Evidence Packet, or scientific result.

## 2026-08-04 - Gate 4 bounded software candidates and adversarial review

### Added

- Isolated CAS Core v8, CAS PCBA v8, and CAS-Ohm v1 research packages with 208
  focused tests in the integrated unittest receipt: Core 61, PCBA 82, and Ohm
  65. Focused pytest runs additionally exercised 19, 195, and 58 parameterized
  subcases respectively.
- A 53-criterion cross-domain Gate 4 review matrix with 20 explicitly open
  criteria, a human-readable adversarial review, exact candidate specifications,
  and a fail-closed integrated verifier that binds every source/test/control
  artifact plus the exact passing test-ID sets.
- A machine-readable five-board PCBA construct-coverage audit: four direct EBNF
  counterexamples and one bounded listing for which no direct counterexample was
  established. The defensible conclusion is corpus-level noncoverage.
- A machine-readable CAS-Ohm source audit preserving eight conflicts or
  under-specifications with exact source locators and conservative candidate
  rules.
- The integrated Gate 4 verifier passes against 54 hash-bound artifacts, all
  208 exact unittest IDs, the 11-record Ring-4 claim boundary, 53 review
  criteria with 20 open, the five-board PCBA audit, the eight-record Ohm source
  audit, and the integrated Gate 1 dependency chain. This is not a gate-close
  or release/admission claim.

### Corrected

- CAS Core now uses complete semantic identities, bounded type-injective
  canonicalization, exact-byte-backed registries, fresh isolated compiler replay,
  exact-type/primitive boundary comparisons, and structural decisions that can
  never grant authorization. Its v0.2 execution profile also serializes
  cooperating worker processes without retry, binds the finite lock policy and
  sanitized Windows architecture inputs, samples runtime identity before
  compiler execution without WMI or subprocess probing, and emits bounded
  hash/path-only transport and profile-difference diagnostics on failure.
- CAS PCBA now uses fixed versioned decimal arithmetic, exact tagged finite
  values, complete projector/simulation/DRC identities, sounder fuse and
  per-cycle feedback checks, provenance-validated result graphs, fixed research
  boundaries, and a hash-bound TKS adapter certificate.
- CAS-Ohm now binds complete profile/source/evidence identities, derives and
  replays network and operating assessments, enforces exact Q4 and role-aware
  resistance/residual rules, and separates structural research-packet
  completeness from authenticated Evidence Packet eligibility. Authenticated
  eligibility remains false without external authority and trusted time. Its
  canonical form also has an explicit 2,048-bit integer bound and normalizes
  host-runtime integer-conversion failures.
- Renamed the claim-ledger completeness header from the inaccurate
  `INITIAL_LOAD_BEARING_NONCLAIMS_ONLY` to
  `INITIAL_LOAD_BEARING_CLAIM_BOUNDARY_RECORDS`; the ledger contains empirical
  and product claim-boundary records and remains entirely Ring 4 / `NOT LICENSED`.

### Preserved open boundaries

- Gate 4 remains `OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`.
- No test establishes canon acceptance, full semantic migration, hermetic
  toolchain closure, Python/Rust equivalence, complete CCDL/stateful semantics,
  live calibration, empirical validity, safety, peer review, product readiness,
  claim licensing, or public-disclosure authorization.
- The monolithic repository pytest collector still has older package-shadowing
  collisions; the integrated verifier uses exact isolated subprocess suites and
  binds their full test-ID sets.

## 2026-08-04 - Gate 0 identity correction and Gate 1 prototypes

### Corrected

- Reclassified the apparent active-compiler hash drift as a CRLF/LF serialization difference. Reproducible normalization of the current 248,859-byte CRLF checkout yields the exact 243,046-byte registry-bound LF Git blob and SHA-256 `8169188A...`; no substantive compiler drift was found.
- Updated the source-authority and migration records so raw-hash inequality is no longer a false Gate 0 blocker. Both raw and canonical content hashes remain required provenance.
- Corrected the census's pre-review ASOM expansion to the source-defined Starved, Aligned, Oversaturated, and Misaligned labels.
- Recorded five newly audited source conflicts rather than silently selecting semantics: CAS-Ohm scale/units, gain/network profiles, ASOM axes, PCBA grammar coverage, and the CSB safety-reference contradiction.

### Added

- Gate 0 candidate closure, baseline-freeze, standing-authority, and compiler-normalization receipts with a fail-closed verifier.
- Gate 0 bounded load-bearing term census covering 49 groups and 712 members across 22 hash-pinned sources while preserving 19 conflicts and every competing profile.
- Gate 1 v7.4 declaration-surface inventory and bounded corrigendum with 29 adjudicated correction records; every unlisted declaration remains OPEN by default.
- Gate 1 typed TKS v8 finite-function reference kernel, corrected deterministic-lift fixtures, fixed-order denotational shortlex prototype, ordered-input guards, bounded resource controls, and standard-basis lift functor tests.
- A pinned Lean 4.32.1 proof seed with exact source hashes, no project-specific axioms or `sorry`, a hardcoded `propext` allowlist, and explicit OPEN boundaries for all unformalized universal claims.
- Gate 1 Noetic Topos 2.0 transverse marked-context construction, finite witness presheaves, strict canonical cover provenance, a two-parent ACBE/RPM join derivation, schema-valid theorem/obligation ledgers, source verification, and executable model checks.
- A finite-context proof candidate and exhaustive 298-sieve certificate showing `M_A M_R ~= M_atom ~= M_R M_A` naturally on `PSh(L,Set)`; the product-site lift remains OPEN.
- A 23-entry integrated Gate 1 hash chain and verifier that composes the Phase 0, Gate 0, v7.4, typed TKS, Noetic, modality, and Lean receipts.
- Seven Ring 4 / `NOT LICENSED` Gate 4 claim records covering held-out CAS-Ohm response, effective resistance, gain composition, redundancy, residual localization, PCBA compiler conformance, and CSB safety-effectiveness boundaries.

### Clarified

- The Noetic successor's underlying topos is the ambient presheaf topos equipped with modalities; the broader `NoeSystem_2` tuple is a structured package, not itself a topos.
- The fully resolved finite context factor is only four independent legacy channels. It is a separation/provenance reference model, not yet a rich final Noetic Topos 2.0 semantics.
- The context-factor mark schema currently covers ACBE, RPM, and their joint refinement. Typed observational/product-site provenance remains OPEN.
- The Lean constant-lift module proves the exact vector expansion and noncontractivity counterexample. Its literal matrix/Gram values are not yet bridged to generic matrix, trace, or rank definitions.
- Derived Noetic cover JSON is accepted as evidence only after its complete parent derivation DAG resolves, rehashes, and recomputes successfully.

These are private research candidates. Gate 0 remains open, all successor research remains Ring 4, and no product claim or public disclosure is licensed.

## 2026-08-04 - v0.1 draft

### Added

- Draft Project Coherence Master Charter with four admission rings, seven research cells, six release gates, and a first-year execution sequence.
- Byte-identified source-authority matrix anchored to the owner-signed semantic registry and its approval receipt.
- Initial load-bearing symbol and terminology registry preserving the ten verbatim Noetic definitions and the World/Domain/Register, Foundation/Drive, and RPM type separations.
- Initial migration matrix with no inherited entries.
- Machine-readable theorem and claim record schemas.
- Initial theorem ledger and fail-closed empirical/product claim ledger.
- Chapter-by-chapter quarantine for *Ten Advances in Mathematics and Theoretical Computer Science*.
- Mathematical red-team report with explicit finite counterexamples and correction obligations.
- Primary-source literature and transfer audit with exact theorem/model conditions and citation labels.
- Draft open-vs-held disclosure boundary.
- Standard-library Phase 0 verification command.

### Corrected from the precursor analyses

- The primary Ten Advances manuscript is now `present`, not `unavailable`; its results remain manuscript claims pending independent review.
- The owner-supplied TKS v7.4 FULL_BEAUTIFUL PDF is a verified rendering of the registered FULL_BEAUTIFUL text, while the repository FULL_CORRECTED PDF is materially different and remains unregistered context.
- The owner-supplied Noetic Topos PDF is byte-identical to the registered eight-page rendering and is not a new version.
- CAS Harness v1.6 is historical and superseded, not the current product-readiness authority.
- The current PCBA baseline already uses mixed simplex addresses and explicitly warns against pure one-hot geometry; projector profiles are a proposed extension, not a correction of an absent representation.
- The proposed projector-capacity transfer omitted a load-bearing isometry/intertwining hypothesis and is recorded as a proof gap.
- ACBE and RPM cover clauses in the conservative Noetic Topos do not add coverage beyond jointly-surjective families; separate-topology triviality remains under final independent review.
- The inherited deterministic-lift norm bound, occupation trace/projector cluster, and several spectral/MVR claims fail explicit finite counterexamples and are blocked for corrigendum.
- Current axioms do not imply subcanonicity; a finite injection-category counterexample blocks bare representables as marked sheaf objects.

### Open blockers

- Charter owner review and explicit freeze decision.
- Final mathematical red-team report and theorem-by-theorem v7.4 audit.
- Independent verification of each Ten Advances proof and novelty claim.
- Twelve unresolved conflicts retained by the owner-signed semantic registry.
- Term-census, compatibility-profile, and remaining semantic-conflict closure work; the earlier compiler-drift item is resolved as a line-ending serialization identity.
- PCBA internal version-label ambiguity.
- Human and qualified-counsel review of the open-vs-held boundary.

No successor release, production-readiness claim, empirical license, public-disclosure decision, or theorem admission is made by this draft.
