# Local Evidence-Chain Retention And Integrity Probe

Generated: `2026-07-26T06:41:07.408201+00:00`
Reviewer identity: `claude_opus5_local_reviewer_20260725`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Target receipt: `governance_regulatory_proof_claim__audit_retention_proof_pass`
Receipt disposition after this run: **STAYS UNSIGNED.**
Result: `PASS`
Cases passed: `26/26`  (behavioural `19`, structural `7`)
Unenforced properties found: `13`
`/verify` section status: `ran`

## What This Run Establishes

Three pieces of machinery were exercised on real files, real appends and real
HTTP calls:

1. **`cas-forex/cas_forex/evidence_store.py`** — the local hash-chained JSONL
   evidence store. Append-only ordering, unbroken back-links, cross-process
   persistence (verified in a second Python interpreter) and no-overwrite on
   duplicate identity all hold, measured. Content tamper, re-sealed tamper, tail
   truncation, mid-chain deletion, torn writes and either-file-alone deletion
   are all **detected**, measured. Every one of those positive results holds
   **only for a single writer**: concurrent appends corrupted the chain in every
   trial run (see `evstore_concurrent_writers_corrupt_chain`), which also means a
   `False` verdict from `verify_chain()` does not by itself imply tampering.
2. **`cas-forex/cas_forex/operator_audit.py`** — append and read work, and the
   advisory-phrase guard genuinely refuses an advisory summary while accepting a
   factual one. The log has **no integrity mechanism at all**.
3. **`noetic-compass-scaffold/noetic-compass/api/routes/evidence.py`** — the only
   implemented `/verify` in the repository. It genuinely detects deletion and
   tampering of *declared* artifacts.

## Out Of Scope, Deliberately

This run does **not** establish that audit records are retained. Read that
sentence as the limit on everything below it.

- **No retention window is enforced anywhere in `cas-forex`.** Not a short one,
  not a long one. A scan of `cas_forex/`, `api/` and `scripts/` for expiry,
  purge, rotation, object-lock and retention-policy constructs returns zero hits.
  The word `retention` appears in the codebase only as the receipt-key string in
  `pcba_readiness.py:141` and `cjt_readiness.py:60`. No retention window is
  stated in the book or in `cas-forex/docs/legal/` either — the privacy draft
  explicitly defers the retention schedule. The honest framing is therefore not
  "a documented window is unenforced"; it is that the book asserts *unbounded*
  retention and unsuppressible retrieval, and **no code anywhere enforces any
  retention property at all**.
- **The only retention-enforcing code in the repository is not here and is not
  a board.** `noetic-compass-scaffold/.../api/services/cas_harness_evidence_anchor.py`
  writes S3 Object Lock with `ObjectLockRetainUntilDate`. It exists on `master`
  and is **absent from this checkout** (`codex/cascompass-legal-live-source`); it
  belongs to the CAS Harness ML audit path, not to any CCB; and the enforcement
  is AWS's, not this repository's. It was not exercised: it needs boto3, live
  credentials, and a bucket with Object Lock enabled.
  `api/services/production/worm_writes.py` states in its own docstring that
  nothing in it is wired into the live app, and its stub store's `assert_ready`
  always raises. Testing it would measure a stub.
- **Chapter 25's seven-field Evidence Packet does not exist.** Nothing in the
  repository emits an object carrying TP1-TP4 `test_points`, a `decision`, a
  `ccdl_version` and a packet-level `hash`. It cannot be exercised at all — not
  partially, not in simulation — because the type does not exist. Any case
  claiming to test it would have to construct the object itself, which tests the
  test.
- **There is no decision-level `/verify`.** The implemented one verifies ML
  model-provenance artifacts (`weights`, `tokenizer`, `english_bpe`, `corpus`)
  for a CAS-Native generation trace.
- **There is no Circuit Registry.** Chapter 25:170-172's "you never overwrite or
  delete them" is untestable, as are the rollback / canary / version-pinning
  claims that depend on it.
- **"Every decision leaves a record" is untestable in the direction that
  matters.** The CSB has no runtime. You cannot show that no decision is dropped
  when no decision is ever made. Everything below tests the store's behaviour
  *given writes*, not that all decisions reach the store.
- **This receipt is external by classification.**
  `docs/working/cjt_ungating_external_gate_checklist_20260617.md:72` says the
  governance claim needs external legal/regulatory review and *audited* retention
  proof. "Audited" means a third party. No local run can supply that.
  `docs/working/pcba_owner_claim_review_20260725.md:67` already lists
  `audit_retention_proof_pass` as not signable by authorization. Nothing in this
  artifact changes that, and this artifact must not be described as proving that
  audit records are retained.

## Measurement Kinds

Every case is tagged. `behavioural` means a real run against real files or a
real HTTP client. `structural` means an absence or shape assertion over source
and models — it pins today's shape and is written to FAIL the day the
corresponding machinery is built. The two are never described as each other.
Section D is structural precisely because the machinery it asks about does not
exist to be run.

## Pass/Fail Thresholds

- Every negative control (tamper, deletion, truncation, advisory phrase) must be
  detected or refused.
- Every false-positive control (untouched store, honest entry, present artifact)
  must be accepted.
- Structural pins must hold exactly.
- The gap list below is **not** part of the pass count. Gaps are findings.
- `verify_code_commit_check_cannot_fail` is explicitly excluded from the pass
  count: it is a check that cannot fail, and counting it would be exactly the
  "engineered to pass" defect this eval exists to avoid.

## Case Corrections Made During This Run

The first execution of this script reported three failures. All three were
defects in the CASES, not findings about the code, and all three were corrected.
They are disclosed here rather than silently fixed:

1. `worm_retained_is_structurally_false` and `no_circuit_registry_implementation`
   scanned `cas-forex/scripts/` including this script itself, which quotes the
   very tokens it searches for (`worm_retained=True`, `CircuitRegistry`,
   `circuit_registry`, `ccdl_version`). The scans reported this file's own text
   as evidence. Fixed by excluding the running script from the source scan
   (`_scan_sources`). No production file matched either pattern before or after
   the fix.
2. `verify_declared_artifact_matches` declared a corpus in the system temp
   directory and got `match=false`, note `"path is outside allowed roots"`. That
   was not a verifier defect — the endpoint enforces a path allowlist restricted
   to the project and scaffold roots (`evidence.py:204`, `:233`). The fixture was
   moved inside an allowed root so the hash comparison is actually exercised, and
   the guard that caused the original failure was promoted to its own negative
   control, `verify_path_outside_allowed_roots_refused`. The eval is stronger
   after the correction, not weaker.

No case was weakened to make it pass, and no finding was reclassified.

## Section A — EvidenceStore (behavioural)

| Case | Category | Kind | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `evstore_pristine_verifies` | `false_positive_control` | `behavioural` | verify_chain=True | verify_chain=True | `true` |
| `evstore_append_keeps_chain_valid` | `false_positive_control` | `behavioural` | verify_chain=True and record_count=8 | verify_chain=True record_count=8 | `true` |
| `evstore_ordering_and_linkage` | `chain_property` | `behavioural` | contiguous seq and unbroken back-links | seq_contiguous=True backlinks_ok=True | `true` |
| `evstore_cross_process_persistence` | `durability` | `behavioural` | count=5 valid=True | count=5 valid=True | `true` |
| `evstore_no_overwrite_on_duplicate_identity` | `chain_property` | `behavioural` | 3 lines, 3 loaded, chain valid | lines=3 loaded=3 valid=True | `true` |
| `evstore_content_tamper_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |
| `evstore_resealed_tamper_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |
| `evstore_tail_truncation_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |
| `evstore_mid_chain_deletion_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |
| `evstore_jsonl_deleted_state_kept_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |
| `evstore_state_deleted_jsonl_kept_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |
| `evstore_torn_write_detected` | `negative_control_tamper` | `behavioural` | verify_chain=False (detected) | verify_chain=False | `true` |

## Section B — OperatorAuditLog (behavioural)

| Case | Category | Kind | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `opaudit_append_read_roundtrip` | `false_positive_control` | `behavioural` | total=5 recent=5 | total=5 recent=5 | `true` |
| `opaudit_advisory_phrase_rejected` | `negative_control_guard` | `behavioural` | ValueError raised and total stays 5 | raised=True total=5 | `true` |
| `opaudit_clean_summary_not_rejected` | `false_positive_control` | `behavioural` | accepted | accepted | `true` |

## Section C — the implemented `/verify` (behavioural + one scope pin)

Status: `ran`

| Case | Category | Kind | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `verify_declared_artifact_matches` | `false_positive_control` | `behavioural` | GET 200 and corpus check match=true | GET 200, overall=all_match, corpus_match=True | `true` |
| `verify_tampered_artifact_detected` | `negative_control_tamper` | `behavioural` | corpus check match=false | overall=partial_mismatch corpus_match=False | `true` |
| `verify_deleted_artifact_detected` | `negative_control_tamper` | `behavioural` | corpus check match=false | overall=partial_mismatch corpus_match=False notes=file not found locally | `true` |
| `verify_path_outside_allowed_roots_refused` | `negative_control_path` | `behavioural` | corpus check match=false with an 'outside allowed roots' note | match=False notes=path is outside allowed roots | `true` |
| `verify_scope_is_model_provenance` | `scope_pin` | `structural` | bindings == ('weights', 'tokenizer', 'english_bpe', 'corpus') | bindings == ('weights', 'tokenizer', 'english_bpe', 'corpus') | `true` |

## Section D — structural absence pins

| Case | Category | Kind | Expected | Observed | Passed |
|---|---|---|---|---|---:|
| `no_retention_construct_in_cas_forex` | `retention_absence` | `structural` | zero hits | 0 hits | `true` |
| `worm_retained_is_structurally_false` | `retention_absence` | `structural` | default False, zero True assignments | default_false=True true_assignments=0 | `true` |
| `no_circuit_registry_implementation` | `unimplemented_mechanism` | `structural` | zero hits | 0 hits | `true` |
| `ch25_seven_field_packet_unimplemented` | `unimplemented_mechanism` | `structural` | 6 of 7 fields absent (only trace_id present) | absent: ['cas_trace', 'ccdl_version', 'decision', 'hash', 'input', 'test_points'] | `true` |
| `receipt_not_self_certifiable` | `authority` | `structural` | required=true and locally-emittable=false | required=True locally_emittable=False | `true` |
| `operator_log_has_no_integrity_mechanism` | `integrity_absence` | `structural` | no integrity field and no verify method | integrity_fields_present=[] has_verify_method=False | `true` |

## Failures Observed

None. Every case listed above returned the expected result. Note that the substantive findings of this run are the unenforced properties below, not the case table.

## Unenforced Properties

These are properties the book's prose leans on that the code does not enforce.
They are recorded as findings, never as passes, and none was closed by weakening
the probe.

### `evstore_total_wipe_undetected`  (behavioural)

Delete BOTH the .jsonl and the .state sidecar, then verify. A total history erasure is the exact move Chapter 26:75 says a regulator is protected against ('a decision the vendor would rather not surface').

- Hoped: detected (verify_chain=False)
- **Observed: undetected (verify_chain=True, record_count=0)**
- **Disposition:** GAP, NOT WAIVED. Detection is impossible in principle for a purely local chain: nothing outside the two files records that a history ever existed. Closing this needs an external anchor (S3 Object Lock, a notary, or a co-signed head-hash feed). Disposition: the artifact must not claim erasure resistance, and Chapter 26's 'any decision the board ever made' must be narrowed to state that the local trail detects EDITS, not ERASURE. The product UI already says 'WORM Evidence Anchoring — UNAVAILABLE, local hash chain only' (ui/src/pages/SettingsPage.tsx:477); the book does not.

### `evstore_rewrite_shorter_undetected`  (behavioural)

Wipe a 5-record history, then write a fresh 2-record history to the same path and verify.

- Hoped: detected (verify_chain=False)
- **Observed: undetected (verify_chain=True, record_count=2)**
- **Disposition:** GAP, NOT WAIVED. Same root cause as the total wipe: no external commitment to expected length or head hash. Disposition: recorded as a limit on the audit-retention claim. The receipt stays unsigned.

### `evstore_concurrent_writers_corrupt_chain`  (behavioural)

2 threads x 25 appends against one store path, 5 trials. Measures two distinct things: whether the chain still verifies, and whether records reach disk at all.

- Hoped: chain valid in every trial and no records lost
- **Observed: chain INVALID in 5/5 trials; record loss in 0/5 trials (0/250 records, 0.0%); no exception raised in any trial**
- **Disposition:** GAP, NOT WAIVED — and the headline is CHAIN CORRUPTION, not record loss. EvidenceStore reads its head state, then appends, with no lock. Two writers interleave, read the same head, and write records that share an event_seq and a previous_record_hash. The result is a store whose own verify_chain() returns False — permanently, with no repair path — even when every record reached disk. Record loss also occurs when the interleaving is tighter, but it is intermittent; the chain corruption was reproduced in every trial. In both cases append() returns a normal receipt, so the caller believes the write succeeded. Disposition: this is the most operationally severe finding in Section A, because a single concurrent moment permanently invalidates the whole evidence chain and is indistinguishable, after the fact, from deliberate tampering. `operator_audit.py:33-36` carries an explicit single-writer warning; `evidence_store.py` carries none and must. Until it does, no claim may be made that every decision reaches the store or that a False chain verdict implies tampering. Not fixed here — this run measures, it does not patch. CALIBRATION WARNING: the LOSS rate is timing-dependent and varies substantially between runs on the same host; do not treat the percentage as a stable figure. Read the per-trial numbers in the raw JSONL, not the average.

### `packet_mutable_after_finalize`  (behavioural)

schemas/evidence.py:33 says the packet is 'Immutable after finalization'. Assign to a field after finalize() and see.

- Hoped: assignment raises
- **Observed: assignment silently accepted; verify_hash True -> False**
- **Disposition:** GAP, NOT WAIVED — but LOW severity and precisely characterised. The packet is tamper-EVIDENT, not immutable: the edit lands, and verify_hash() flips to False, so a persisted copy is caught. Disposition: the docstring overstates. It should read 'tamper-evident after finalization'. An in-memory packet edited before append is NOT caught, because EvidenceStore re-seals an unsealed packet at append time (evidence_store.py:27-28).

### `packet_sealed_at_log_time_not_decision_time`  (structural)

Chapter 25:105 states as a rule: 'hash the packet at decision time, not at log time... A seal applied after the fact seals nothing.' AST-walk every EvidenceStore.append() call site and check whether finalize() is called in the same function body.

- Hoped: 0 call sites seal at persistence time
- **Observed: 6/8 call sites call finalize() inside the persistence function, immediately before append**
- **Disposition:** GAP, NOT WAIVED. By the book's own sentence these seals seal nothing — they cover whatever reached the persistence function, not what the decision produced. Disposition: this is a BOOK finding. Chapter 25:105 states a rule that no code path in this repository obeys, and the chapter does not say so. Either the Bench Note gains an explicit 'not yet implemented in the reference codebase' line, or the call sites move finalize() to the decision site. Recorded here; not fixed by this run.

### `opaudit_in_place_edit_undetected`  (behavioural)

Edit one entry's summary and payload in place, then read it back through the public API.

- Hoped: detected by some API
- **Observed: undetected — forged row served as genuine (1 match)**
- **Disposition:** GAP, NOT WAIVED. OperatorAuditEntry has no hash, no previous-hash, no sequence number, and OperatorAuditLog exposes no verify method. The log is append-only BY CONVENTION of its own writer, with no integrity mechanism at all. Disposition: this log must never be described as tamper-evident, and it is not the evidence behind any audit claim. If an operator-action audit trail is ever offered as regulator-facing evidence it needs the EvidenceStore chain treatment.

### `opaudit_deletion_undetected`  (behavioural)

Remove one line from the operator audit log.

- Hoped: detected
- **Observed: undetected — stats total silently 5 -> 4**
- **Disposition:** GAP, NOT WAIVED. Same root cause as B4: no chain, no expected count. Disposition: recorded as a limit. The operator audit log carries no retention or integrity property and backs no audit claim.

### `opaudit_torn_write_silently_dropped`  (behavioural)

Truncate one line mid-JSON (crash during append) and read the log.

- Hoped: read APIs raise or report the loss
- **Observed: silently skipped — total 4 -> 3, no error, no dropped-record counter**
- **Disposition:** GAP, NOT WAIVED. operator_audit.py:326-331 `continue`s on JSONDecodeError by design (documented as 'tolerate corrupt lines'). Tolerance is reasonable for a cockpit feed and wrong for evidence: a lost record is indistinguishable from a record never written. Disposition: if this log is ever promoted to evidence, the read path needs a skipped-line counter surfaced in stats(). Recorded, not fixed.

### `opaudit_entry_id_collision_same_second`  (behavioural)

Append two DIFFERENT actions on the same target_id inside one second. Timestamps are second-resolution (operator_audit.py:189) and entry_id is sha256(action_kind|target_id|timestamp).

- Hoped: distinct entry_ids
- **Observed: COLLISION — both entries carry entry_id d3a9d41341522ebb**
- **Disposition:** GAP, NOT WAIVED. Both rows persist, so nothing is lost on disk. The damage is downstream: the docstring (operator_audit.py:114-117) tells callers the id exists so they can dedupe on retry, and a consumer doing that drops a real, distinct operator action. Disposition: entry_id needs microsecond resolution or a payload digest. Recorded, not fixed by this run.

### `verify_deleted_trace_indistinguishable_from_nonexistent`  (behavioural)

Create a trace, confirm it resolves, delete the trace file, then compare the responses for the deleted id and for an id that never existed. Chapter 26:75 promises a regulator can pull 'any trace ID, including one from a decision the vendor would rather not surface'.

- Hoped: distinguishable (deleted != never existed)
- **Observed: INDISTINGUISHABLE — both return 404 {"detail":"trace_id not found"}**
- **Disposition:** GAP, NOT WAIVED — the single most important finding for this receipt. There is no index, manifest, or external anchor enumerating which trace IDs ought to exist, so a vendor who deletes a record is indistinguishable from a vendor who never made it. Disposition: Chapter 26:43 and :75 must be narrowed. The unsuppressible-audit-trail claim is not backed by anything in this repository and cannot be closed by local code — it requires an external anchor.

### `verify_scope_is_self_declared`  (behavioural)

Strip the corpus declaration from the trace file and re-verify.

- Hoped: verifier still checks corpus (or reports the omission as a failure)
- **Observed: overall=all_match with checks ['code_commit'] — the corpus check simply disappears**
- **Disposition:** GAP, NOT WAIVED. Documented behaviour (evidence.py:729-730: artifacts whose expected SHA is absent are skipped entirely), so this is not a bug — but it is a real limit: an operator who controls the trace file produces a clean verdict by removing the declaration. Disposition: a verify verdict is only as strong as the declaration set, and the declaration set is not itself anchored. Any regulator-facing use needs a required-artifact list held outside the trace.

### `verify_code_commit_check_cannot_fail`  (behavioural)

Verify a trace that omits code_commit_sha. _packet_from_trace (evidence.py:622-627) fills the expected value from _git_head_sha(), and the verifier then compares it to git HEAD in the same process.

- Hoped: the check is capable of failing
- **Observed: tautology — match=True always, expected and actual both come from git HEAD**
- **Disposition:** GAP, NOT WAIVED. This is exactly the 'engineered to pass' shape this eval is forbidden to produce, so it is recorded and EXCLUDED from the pass count rather than counted. Disposition: when a trace omits its commit, the check should be omitted or reported as unverifiable, not auto-satisfied. No case in this artifact is built on it.

### `verify_packet_timestamp_not_sealed`  (behavioural)

Chapter 25:117 says /verify returns 'the decision timestamp, sealed inside the hash'. GET the same packet twice ~1.2s apart and compare.

- Hoped: identical generated_at, covered by a packet-level hash
- **Observed: regenerated on every read: 2026-07-26T06:41:17Z vs 2026-07-26T06:41:19Z; packet-level hash field present=False**
- **Disposition:** GAP, NOT WAIVED. The implemented packet's generated_at is documented as 'the timestamp the packet was assembled' (evidence.py:71) and there is no packet-level hash field at all, so no timestamp is sealed by anything. Disposition: BOOK finding — Chapter 25:117 describes a property the implemented packet does not have. Chapter 25:198's design-only clause covers the CSB packet; it does not cover a claim about what the shipped /verify returns.

## Book Findings

The following are defects in the BOOK, not in the code, and are recorded with
file and line:

- `book/CAS_PCBA_Engineer/Chapter_26_Governance.md:43` and `:75` — "They pull any
  decision the board ever made, by its trace ID" and "any trace ID, including one
  from a decision the vendor would rather not surface." Measured: a deleted trace
  and a trace that never existed return byte-identical responses. The
  unsuppressible-audit-trail claim is not backed by anything in the repository.
- `book/CAS_PCBA_Engineer/Chapter_25_Production_Deployment.md:105` — the Bench
  Note states as a rule "hash the packet at decision time, not at log time... A
  seal applied after the fact seals nothing." No code path obeys it; every
  `EvidenceStore.append` call site seals inside the persistence function.
- `book/CAS_PCBA_Engineer/Chapter_25_Production_Deployment.md:117` — "The
  decision timestamp, sealed inside the hash." Measured: `generated_at` is
  regenerated on every read and there is no packet-level hash field at all.
- `book/CAS_PCBA_Engineer/Chapter_26_Governance.md:53` and `:56` — Platinum
  requires "Every decision emits a `/verify`-able evidence packet" and "no
  evidence packets" is a Not-Certified condition. Nothing in the toolchain can
  apply either gate. Same class of defect as `csb_fuse_action_downgrade` in the
  CSB red-team report, and it should be dispositioned the same way: documented
  in-chapter as a manual check the toolchain does not perform.
- Omission, load-bearing for this receipt: the product UI already states "WORM
  Evidence Anchoring — UNAVAILABLE, local hash chain only"
  (`cas-forex/ui/src/pages/SettingsPage.tsx:477`) and `EvidenceReceipt` carries
  `worm_retained=False` / `anchor_scheme='local-jsonl-hash-chain'`. Neither
  Chapter 25 nor Chapter 26 tells the reader that the evidence trail is same-host
  storage with no durable retention. That is the single most important limit on
  the audit-retention claim, and it is currently unstated.

## Mitigations And Limits

- The allowed claim is exactly what was measured: the local evidence chain
  detects **edits**, not **erasure**.
- This evidence does not unlock live trading, does not create a broker `ACCEPT`
  path, and does not support any legal, regulatory, privacy or governance claim.
- Nothing here was fixed. This run measures. Every gap above is left standing
  with a disposition so the next phase can act on it.
- The correct outcome of this investigation is a gap report plus a narrowing of
  Chapter 26 — not a signed receipt.

## Raw Evidence

- Path: `docs\working\audit_retention_eval_raw_20260725.jsonl`
- SHA-256: `d96a15bd5ed4af1cd3dc2be5f4fd5f9c6d86e22e150f5890535e315c42419009`
- JSONL records: `39` (26 cases, 13 gap probes)
