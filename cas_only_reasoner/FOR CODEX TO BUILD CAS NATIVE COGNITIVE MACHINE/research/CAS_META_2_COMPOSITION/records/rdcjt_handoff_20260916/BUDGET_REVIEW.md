# Budget review — 2026-09-16

Independent automated code review of commit `a93d8ce404a3ea3dbb3d6ea31ccd62cf1c797774` and the current ledger. This is not human review or authorization for another paid run. No provider calls, paid reservations, neural work, canonical ledger edits, commits, or pin updates were performed.

## Fixed: reject an unmatched head before reserving

`aws/budget.py::read_locked` previously allowed the ledger head to differ from the newest history entry in authorization and metadata fields. `reserve_budget` nevertheless hashed the complete head for the next history link. A valid-looking head-only cap amendment therefore passed the initial read, persisted a new reservation, and then failed with `BROKEN_BUDGET_HISTORY_CHAIN`. Every later read also failed. An `updated_utc`-only change produced the same defect.

The smallest repair restores complete decoded-object equality between the head and newest history entry. Such discrepancies now fail with `LEDGER_HISTORY_MISMATCH` before any reservation or history write. Historical states still validate against their own recorded cap. The owner cap, reservation rules, amendment binding, and legacy launcher pins are unchanged.

Two regression tests demonstrate both cases. Both fail against the original `a93d8ce4` module loaded in memory, then pass with the repair. The tests also require the temporary ledger and all history bytes to remain unchanged after refusal. Evidence: `budget_regressions_before_fix.txt`, `budget_scoped_tests.txt`, and `budget_test_receipt.json`.

## Current canonical evidence

- Current head and all 73 history records pass `read_locked` after the repair; before/after hashes are identical. See `budget_canonical_read_receipt.json`.
- Revision: `72`; reservations: `74`; cap: `$5000.00`; reserved: `$417.00`; remaining unreserved: `$4583.00`. These are internal reservation bounds, not an AWS invoice or current billing verification.
- Canonical ledger SHA-256: `e2c9cc87793a40c10361dbd5c2602d4e4ec8d1127b68ee4a6e1ad6b7624fba79`.
- Amendment SHA-256: `d714bea5a89d275c78fbc64460bbd851925b3957752bb35640a72edd3ceb7a76`.
- History revision 69 differs from `PRESERVED_history_00000069_pre_cap_raise.json` only in `owner_task_cap_usd`, `remaining_unreserved_usd`, and `amendment`. Its reservation list is identical. The two preserved pre-raise files decode to identical objects. This is a documented historical rewrite, not an append-only amendment event.
- Current budget source SHA-256: `cb3c78a0dfed166857109710cb8eac79dd337d837c839d558565982084b5a22f`.
- Current budget tests SHA-256: `169246bd7091d3eb4591428681e863cde97abacbbd672bd3155a751782753f3d`.

## Verification and remaining blockers

The five offline suites passed: **142 tests, 24 subtests** in 57.40 seconds using `C:\Python314\python.exe`. Suites: budget, graph training curriculum launch, graph training candidate launch, owner record bounds, and recurrent CJT launch. Provider clients are fakes; no training or cloud execution was performed. Exact command, runtime, and source/output hashes are in `budget_test_receipt.json`.

Seven legacy modules still fail collection with `PINNED_SHARED_BUDGET_CHANGED_BEFORE_IMPORT`: `test_bundle_v3`, `test_launch_ablation_v4`, `test_launch_contrast_v6`, `test_launch_fit_v5`, `test_launch_recovery_v6`, `test_launch_v3`, and `test_prototype_v7_launcher`. See `legacy_budget_collection.txt`. Their launcher imports pin the shared module to SHA-256 `77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0`. Before this review, the committed module already had SHA-256 `7ad29c6ab6187c9434561d5f36d1459a30274d8050b998c2d86665a8b6a233fd`; the failure predates this small repair. Deriving `budget.CAP` alone cannot repair an import-time digest mismatch.

Do not remove the pins or update them blindly. Any revival of those historical launchers needs review of the shared budget change, an intentional pin/manifest update, and their full offline launch-contract tests. Multiple other launchers still require `$400.00`; their compatibility with the amended cap is unproven. This review makes no full-suite success claim.

The ledger schema still equates one revision with one added reservation. A future cap change needs an explicit amendment event or migration design that preserves the historical record and its hash chain. This fix deliberately refuses unsupported head-only changes before they consume a reservation. The historical cap raise and money-path changes still require the human review named in the handoff.
