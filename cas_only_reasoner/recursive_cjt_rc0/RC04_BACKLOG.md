# RC-0.4 Backlog — remaining NONCRITICAL issues (frozen record)

Per OWNER DIRECTIVE RC-0.4 section 9: after an independent PASS, Gate 0 freezes and
the remaining noncritical issues are recorded here instead of growing more controller
machinery. **Nothing in this file blocks Gate 1A. Nothing in this file may be "fixed"
by adding new architecture during the freeze.**

Status words follow the spec-sheet legend. Date: 2026-08-30.
Updated same day under OWNER DIRECTIVE RC-0.4A: items resolved by the RC-0.4A patch
are marked FIXED below; the stale "110 tests" figure is corrected (the RC-0.4 commit
recorded 17+28+23+14+30 = 112 internal tests; RC-0.4A adds test_rc04a (22) and, after
its internal pre-commit adversarial audit, test_rc04b (16) → 150; RC-0.4C adds
test_rc04c (25 after its own internal-audit round 2) → 175; RC-0.4D adds test_rc04d
(30 after its internal round) → 205; RC-0.4E adds test_rc04e (41 after its internal
round) → 246 internal tests. The RC-0.4D battery (205/26/8/15 + replay + manifest)
was INDEPENDENTLY REPRODUCED by a third-party AI agent in a fresh environment
(2026-08-31, owner-relayed) — an independent cross-model software audit, NOT external
scientific replication; RC-0.4E's additions are internal results pending the same.)

## RC-0.4E closures (2026-08-31, owner independent audit of ad46418f + third-party AI audit)
The owner's audit (merged with the third-party agent's independent reproduction of the
full battery and its F-01 finding) ordered the lifecycle-authority patch. Closed:
- **Run owns the lifecycle**: typed phases NEW→RUNNING→FINALIZING→FINALIZED|FAULTED;
  tick() requires run()'s private scheduler capability; result() exists only in a
  terminal phase; run() refuses non-pristine engines.
- **Promotion is an authority operation**: one-time-claimable lifecycle authority +
  one-use `FinalizationPermit` bound to the exact provisional sets; voiding needs the
  authority token. The owner's verbatim `tick → promote → result` bypass refuses at
  all three doors.
- **Finalization is ONE guarded transaction** (third-party F-01 exact): planned final
  snapshot → permit → atomic promotion → planned==installed digest equality; ANY
  exception (RuntimeError, MemoryError, mid-promotion) yields a typed, voided,
  FAULTED terminal state — nothing stranded provisional.
- **Split caging** (unit = child branch): total/active/governance ceilings checked
  before budget; **global cause-id registry** with deterministic collision handling
  (ID_COLLISION event), seal-bound; **honest cutoff**: CUTOFF_CAUSE_UNRESOLVED, no
  relabel self-clear, no repairs_completed, Desire emitted once, no same-tick retry.
- Mutation inventory frozen as v4 (22 laws; v1–v3 preserved on disk).

### RC-0.4E internal adversarial round (same commit, 3 lenses)
Found 1 CRITICAL + 2 MAJOR + hardenings; all fixed and test-locked (test_rc04e → 41):
- **CRITICAL:** both split paths silently dropped the registered publication-law
  consequences — a verifier-confirmed `opposite` combined Effect (or committed child
  verdict) kept its producer unquarantined. FIXED: consequences fire on resume and
  child-collection exactly as on the direct path.
- **MAJOR:** the execution internals carried only the finalization latch — pre-run
  direct calls executed/committed/provisionally-published and a later run() sealed
  the injected work. FIXED: the lifecycle guard (phase RUNNING/FINALIZING) on every
  execution internal + a pristine-state check at run() entry.
- **MAJOR:** dropped causes had no terminal disposition. FIXED: typed CAUSE_DROPPED
  events (cause id + why) and a `dropped_causes` metric on every drop path.
- Hardenings: terminal phase without a computed seal refuses (ControllerTampered);
  the finalization boundary has NO exception carve-outs; splits are registered only
  for experts with a combined op (fail-closed `split_no_combined_op`); suspended
  frames are swept into the failed-frame refusal at FINALIZE; the failed-frame
  refusal appears in BOTH evidence surfaces; the governance split cage counts the
  chosen expert's OWN open children.
- Residuals recorded, not fixed: the finalization-permit registry is deliberately NOT
  seal-bound (circular: the permit contains the planned snapshot digest — documented
  in the snapshot docstring); `_compute_final_seal` still swallows all exceptions by
  design (it must never throw).

## RC-0.4D closures (2026-08-31, owner independent audit of 38635986)
The owner's audit ended the enumerated-patch era: verifier fixes CLOSED, but the
CONTROLLER configuration was not preflighted, an unsealed run could still hold
`published == 1`, and the ASOM cutoff/breakdown actions were decorative. Closed by
OWNER DIRECTIVE RC-0.4D (correction-only, no new architecture):
- **One input schema** (`_validated_constructor_config` + `CONSTRUCTOR_SCHEMA_PARAMS`):
  every constructor parameter validated, COPIED into owned state, and covered by an
  import-time signature law; the engine is not returned unless its entire initial
  state seals to a real 64-hex digest. The owner's `commit_verdicts=object()` and
  `[valid_cause, object()]` attacks are rejected at construction.
- **Publication atomicity**: publication is `PROVISIONAL_PUBLICATION` until the
  final-seal barrier's prospective probe passes; only then is it promoted to
  `PUBLISHED` and counted. THE INVARIANT — marker ⇒ `published == 0` and no ledger
  row `PUBLISHED` — holds; failed/faulted runs terminally VOID their provisionals
  (receipts stay consumed: a terminal void, never a release).
- **ASOM dispatch load-bearing**: at zero total score, breakdown quarantines
  (`asom_region:breakdown`, excluded from routing) and cutoff repairs the ACTUAL
  blocker (real RPM prereq / Desire-law deprioritization / committed region
  re-assessment), bounded by the per-cause RepairFrame; hard-masked experts are never
  mutated; RPM blocks remain a separate axis.
- **Whole-object detachment**: `runtime_snapshot()` returns one `copy.deepcopy` of the
  complete snapshot (the fault record included); taus/repair_requires and every other
  mutable constructor input are owned copies.
- **Frozen inventory v3** = the eleven v2 laws verbatim + 4 new (constructor schema,
  final-publication barrier, ASOM dispatch, whole-object detach); v1 and v2 preserved
  on disk; new pinned digest.

### RC-0.4D internal adversarial round (same commit, 3 lenses)
Found 2 MAJOR + 1 MINOR + 3 SUSPICIONs; fixed or recorded:
- **MAJOR (fixed):** one Cause naming K ready cutoff experts was requeued K times and
  PUBLISHED K times — the dispatch now requeues AT MOST ONCE per call (test-locked);
  this also closes the split-child double-publication corollary (suspicion).
- **MAJOR (fixed):** a SUBSET `states` dict was accepted and deferred failure to a raw
  mid-run KeyError — past budget, commits, and a provisional publication. A provided
  states dict must now cover EXACTLY the registered expert set (also resolves the
  `states={}` vs `states=None` ambiguity — `{}` fails coverage; test-locked).
- Fixed: `episode_id` must be non-empty; the prospective probe catches only the
  encoder's own (TypeError, ValueError) so an environmental error becomes a typed
  FAULT instead of silently voiding a sealable run's publications.
- Residual recorded, not fixed: `_compute_final_seal` still catches all Exception (it
  must never throw); a non-deterministic environmental error striking BETWEEN a
  passed probe and the final seal could in principle yield the marker after
  promotion — outside the deterministic model, no runnable trigger exists.

## RC-0.4C closures (2026-08-30, owner independent audit of 80d2f70e)
The owner's independent audit found TWO Gate-0 blockers that the internal 5-lens
workflow had UNDER-TRIAGED (its finalization probe actually listed
`verifier.verify -> coord.register_verifier_receipt` among the unguarded paths, and I
wrongly treated registration-refusal as sufficient — recorded here as an honest
internal-audit miss). Both FIXED and test-locked (tests/test_rc04c.py, 18 tests):
- **Verifier finalization gate (finding 1).** `SealedVerifier.verify()` could still
  issue receipts and mutate its seal-bound issuance registry after finalization —
  "the receipt press kept running in the sealed room." FIXED: the shared `SealGate`
  is passed into the verifier; `verify()` refuses with `FinalizedControllerError`
  BEFORE issuing anything. The rc04b test that had itself exercised the hole is
  repaired. Frozen mutation `verifier_finalization_gate_removed` added.
- **Configuration preflight (finding 2).** The verifier accepted arbitrary dicts, so
  an unused unsealable poison entry let the engine work — and publish — before a
  delayed final-seal failure. FIXED: `_preflight()` validates the frozen schemas
  (2-tuple str keys naming registered experts; verdict vocabulary; exact-str
  payloads) and PRECOMPUTES both configuration digests at construction; no deferred
  first-time canonicalization at sealing. Frozen mutation
  `verifier_configuration_preflight_removed` added.
- **Fault-only hash retired (finding 3).** A final-seal failure now yields the marker
  `UNSEALED_TERMINAL_FAULT` — plainly not a digest, never presented as a trace seal;
  nothing is appended to evidence after the failure; the underlying exception is
  preserved separately in the fault record; publication eligibility is prohibited
  (gate tripped). Reachable only by out-of-API injection now that preflight +
  construction validation close every public path.
- Mutation inventory frozen as `RC04_REQUIRED_MUTATIONS_v2.json` (11 laws — the nine
  v1 entries verbatim plus the two above; v1 preserved on disk unchanged; new pinned
  digest in the generator).

### RC-0.4C internal adversarial round 2 (same commit)
A second 3-lens internal workflow attacked the patched tree before commit and found
1 CRITICAL + 3 MAJOR + residuals; all fixed and test-locked (test_rc04c grew to 25):
- **CRITICAL:** non-finite/non-numeric `max_total_branches`/`max_active_branches` were
  accepted and reproduced the owner's publish-then-unsealable attack through a
  different constructor argument. FIXED: `require_nonneg_int` on both; plus
  `require_str(episode_id)`, str-keyed states (coordinator), and registered-expert
  states keys (engine) — every constructor argument that reaches the seal is now
  validated at construction.
- **MAJOR:** an unsealed terminal run with a PUBLISHING cause still emitted
  `published=1` and a PUBLISHED ledger through `result()`. FIXED: `result()` raises
  the typed `ControllerFault` for an `UNSEALED_TERMINAL_FAULT` run — an unsealed run
  has no result; forensic state stays on the engine object. The scenario runner now
  rejects the marker as a seal (`_is_real_seal`: 64-hex only) and two markers never
  read as an identical replay.
- **MAJOR:** `_finalize_failed_frame` was the one split helper without the
  finalization guard (mutate-then-refuse). FIXED: guarded first-line like its
  siblings.
- Hardenings: `runtime_snapshot()` returns detached copies of every live collection;
  the tamper tripwire keys on `seal_digest` alone, so flipping `finalized` is no
  longer a silent kill-switch.
- Residual recorded, not fixed: raw attribute rewrites (e.g. `e.seal_digest = ...`)
  remain outside the same-process API capability boundary, per the recorded trust
  boundary.

## RC-0.4A internal pre-commit adversarial audit (2026-08-30) — CLOSURES
A 5-lens adversarial workflow (internal review, NO authority) attacked the RC-0.4A
tree before commit and found two CRITICALs that were exactly the owner's recurring
pattern ("a field was added without proving it governs authority"). Both FIXED in the
same commit, test-locked (tests/test_rc04b.py, 16 tests):
- **CRITICAL — finalization did not govern the write paths.** The `finalized` latch
  guarded only 5 engine methods; the sub-objects (coordinator, publication
  coordinator, budget) and internal helpers still mutated sealed evidence, and
  `e.seal_digest = e.seal()` could re-sync a forged seal. FIXED: a shared one-way
  `SealGate` (rc01_types) is tripped at finalization; `coord.commit`,
  `register_verifier_receipt`, `pubcoord.commit_publication/refuse/abstain`, and
  `budget.spend` all refuse with `FinalizedControllerError`; the internal mutators
  (`_quarantine`/`_reopen`/`_seal_and_halt`/`_record_publication`/`_execute_verify_commit`/
  `_handle_no_ready`/`_collect_child`/`_resume_parent`/`_settle_cancelled_child`) refuse
  too; and `result()` is self-verifying — for a finalized engine it recomputes the live
  seal and raises `ControllerTampered` rather than emit evidence under a stale seal.
- **CRITICAL — storable-but-unsealable value.** A non-finite float was legal to store
  (`_deeply_immutable`) but illegal to seal (`rc_canonical`), so `seal()` threw inside
  the fault handler and a bare `ValueError` escaped unsealed (after an Effect had
  published). FIXED at the root: `_deeply_immutable` and `require_deeply_immutable`
  reject NaN/inf; `taus` finiteness validated at construction; and belt-and-suspenders
  `_compute_final_seal()` never lets a bare encoder exception escape — it records a
  typed SEAL_FAILED fault and raises `ControllerFault`.
Also fixed from the same audit: `result()` self-verification (MAJOR 2); `frame_full`
now binds parent-cause evidence (snapshot-types suspicion); `invalidations_consumed`
anti-stringification test lock added (directive-completeness MAJOR); three manifest-law
robustness fixes (duplicate-entry/malformed-name/`emit_status` independent soundness).
Residuals recorded, not fixed:
- KeyboardInterrupt/SystemExit are not caught by `except Exception` in `run()` (they are
  BaseException). Async interrupts are OUT OF SCOPE for the sealing guarantee by design
  (catching SystemExit to seal-and-swallow is itself undesirable). Recorded.
- `run()` re-entrancy TOCTOU: the entry guard and the finalized latch are not atomic;
  the deterministic controller is single-threaded and no overlapping double-execution
  was reproducible. Recorded (low).
- The frozen battery (11 laws as of RC-0.4C's manifest v2) delete-line-covers the two
  RC-0.4C laws but still not the RC-0.4B laws (coordinator/pubcoord/budget gates,
  non-finite rejection, result-tamper); those are proven by direct sensitivity tests
  in test_rc04b. Extending further stays OPEN (low).

## 1. Per-Cause operation contract (owner scorecard: "Partial")
The verifier's op_kind check is PRODUCER-level (`EXPECTED_OPS[producer]`), not a
per-Cause contract. A producer with two registered operations could apply the wrong
one of its own operations to a Cause and pass the op check (the payload oracle would
still catch a wrong payload). OPEN. Fix, if ever needed, belongs to a future
verifier-table extension, not to Gate 0.

## 2. Same-process trust boundary (recorded, out of scope by owner order)
The issuance registry and all private registries are same-process API capability
discipline. Python name-mangling and closures do not stop hostile code in the same
interpreter (introspection). The PERMITTED claim: ordinary API callers cannot
manufacture an accepted receipt without the verifier issuance path. The PROHIBITED
claim: receipt forgery is structurally impossible against hostile same-process code.
Owner order: do NOT build process separation or cryptography in this phase. RECORDED
in the receipt's `trust_boundary` field.

## 3. Scenario-matrix display artifact still uses `default=str`
`RC01_SCENARIO_MATRIX.json` is written with `json.dumps(..., default=str)` as a
HUMAN-READABLE report. It carries no state, intent, receipt, or trace authority (the
authority-bearing digests all go through `rc_canonical`). If a set-typed value ever
lands in a scenario row, its bytes could vary across processes; the matrix digest is
recorded per-generation, not replay-compared. OPEN (cosmetic).

## 4. No CI runner
The internal tests (246 as of RC-0.4E) + 26 scenarios + 8 injections + 22 mutations
run locally and via the committed generator; there is no GitHub Actions workflow
re-running them on push. The owner noted this in the RC-0.3 and RC-0.4 audits, and
ruled that CI is recommended but does not by itself decide Gate 0. OPEN.

## 5. RC-0.4 commit SHA unbound at commit time (self-reference law)
`RC02_ATTESTATION.json` now binds the RC-0.3 evidence commit (846f323f…) but the
RC-0.4 commit cannot bind its own SHA. A follow-up binding record — or simply the
owner's audit of the pushed history — covers it. This is the registered law, not a
defect.

## 6. Internal adversarial audit residuals (2026-08-30)
An internal fresh-context adversarial agent audited the RC-0.4 tree before commit
(internal review, NO authority — per the owner's standing calibration). It reproduced
8 refused publication attacks, 10 fail-closed mutation-law cases, and found 1 MAJOR +
2 MINOR issues. The MAJOR (canonical enum/record tags used the bare class `__name__`
and dropped the enum member value — cross-class name collisions) and the first MINOR
(`episode_id` not directly seal-bound on zero-commit runs) were FIXED and test-locked
in the RC-0.4 commit itself. Remaining residuals, recorded not fixed:
- `_latent_ok` (per-tick scratch) is not seal-bound; it feeds only the
  `forced_publications` metric, which IS bound. Informational.
- The DCR's semantic RegionRecord CONTENT (region posterior, stability) is
  caller-arbitrary; eligibility binds `semantic_outcome == receipt.verdict` and the
  cause-bound receipt, not the diagnosis payload itself. By design; recorded.
- ~~Suspicion: an exception escaping `run()` mid-loop unsealed~~ — the owner's
  RC-0.4A audit CONFIRMED this reachable through an unknown theta mode. **FIXED in
  RC-0.4A**: mode validated before budget spend; `run()` has a fault boundary that
  records a typed FAULT, finalizes, seals, and re-raises `ControllerFault` carrying
  the seal (test-locked, 6 tests).
- Mutation-battery coverage: `rc_canonical`, finalize-then-seal ordering, and the
  snapshot bindings beyond the consumed registry are proven by direct sensitivity
  tests, not delete-the-line mutations. The required INVENTORY itself is now frozen
  (RC04_REQUIRED_MUTATIONS_v1.json, RC-0.4A section 4); extending the battery to
  these three families stays OPEN (low).
- `LAW_DCR_RECEIPT_BINDING` is unreachable given the preceding effect-digest equality
  check (digest binds cause+producer). Defense-in-depth; harmless.

## 7. ~~Engine tick guard on direct `tick()` calls~~ — FIXED in RC-0.4A
The prior classification ("harness misuse, detectable but not hard-blocked") was
REJECTED by the owner's RC-0.4A audit: a sealed controller may not rely on callers
politely not calling public methods. **FIXED**: `finalized` is a real latched state;
`run()`, `tick()`, `_repair()`, `_do_split()`, and `_publish_or_refuse()` raise the
typed `FinalizedControllerError` after finalization without mutating anything;
`result()` returns a detached deep copy; the latch itself is seal-bound. Test-locked
by the six section-1 tests in `tests/test_rc04a.py`.
