# RC-0.4 Backlog — remaining NONCRITICAL issues (frozen record)

Per OWNER DIRECTIVE RC-0.4 section 9: after an independent PASS, Gate 0 freezes and
the remaining noncritical issues are recorded here instead of growing more controller
machinery. **Nothing in this file blocks Gate 1A. Nothing in this file may be "fixed"
by adding new architecture during the freeze.**

Status words follow the spec-sheet legend. Date: 2026-08-30.

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
The 110 tests + 26 scenarios + 8 injections + 9 mutations run locally and via the
committed generator; there is no GitHub Actions workflow re-running them on push.
The owner noted this in the RC-0.3 audit. OPEN.

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
- Suspicion only (not reproduced): an exception escaping `run()` mid-loop would leave
  `seal_digest = None` with ledger entries unsealed; no ordinary input reached one.
- Mutation-battery coverage: `rc_canonical`, finalize-then-seal ordering, and the
  snapshot bindings beyond the consumed registry are proven by direct sensitivity
  tests, not delete-the-line mutations. OPEN (low).
- `LAW_DCR_RECEIPT_BINDING` is unreachable given the preceding effect-digest equality
  check (digest binds cause+producer). Defense-in-depth; harmless.

## 7. Engine tick guard on direct `tick()` calls
`RC01Engine.tick()` respects `halt_requested`, but a caller invoking `tick()` directly
after `run()` returned could still mutate state after the final seal (the seal would
then disagree with `runtime_snapshot()`, which is detectable — `seal()` recomputation
exposes it). `run()` is the only registered entry point; direct-tick misuse is a
harness-misuse case, detectable but not hard-blocked. OPEN (low).
