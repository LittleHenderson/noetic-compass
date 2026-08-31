# RC-0.4 Backlog — remaining NONCRITICAL issues (frozen record)

Per OWNER DIRECTIVE RC-0.4 section 9: after an independent PASS, Gate 0 freezes and
the remaining noncritical issues are recorded here instead of growing more controller
machinery. **Nothing in this file blocks Gate 1A. Nothing in this file may be "fixed"
by adding new architecture during the freeze.**

Status words follow the spec-sheet legend. Date: 2026-08-30.
Updated same day under OWNER DIRECTIVE RC-0.4A: items resolved by the RC-0.4A patch
are marked FIXED below; the stale "110 tests" figure is corrected (the RC-0.4 commit
recorded 17+28+23+14+30 = 112 internal tests; RC-0.4A adds test_rc04a (22) and, after
its internal pre-commit adversarial audit, test_rc04b (16) → 150 internal tests —
internal results, NOT an independent reproduction).

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
- The 9-mutation frozen battery does not delete-line-cover the RC-0.4B laws (gate,
  non-finite rejection, result-tamper); those are proven by direct sensitivity tests in
  test_rc04b. Extending the frozen inventory stays OPEN (low) to keep the pinned
  manifest digest stable.

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
The internal tests (134 as of RC-0.4A) + 26 scenarios + 8 injections + 9 mutations
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
