# Ordered ingestion teaching/reload smoke

Status: PURE_REPAIRS_PASSED / REVISED_PACKAGE_AND_CUDA_PENDING.

The versioned smoke/reload extension and worker binding passed 169 focused tests,
with zero failures, errors, skips or prohibited imports. Declared test inputs
remained unchanged. A scoped committed-source package fix then passed 53 targeted
launcher tests. The 211-member archive at source 4296fdaa5ce5c9d12850242c3e20042b4e319156
was built, but its startup rehearsal rejected an overly broad timeout check:
the upload thread's join timeout was counted alongside the actual 1200-second
training subprocess deadline. That failed rehearsal is retained in
package_rehearsal_001. The corrected helper passed 14 regression checks and the
exact 211-member archive rehearsal. A new archive will bind the subsequent fixes
before actual CUDA execution. No learning gain is established.

Independent pre-launch review also found that the inherited two-hour instance
limit depends on the local supervisor. A new-provider guest shutdown safeguard
now runs on a responsive guest before downloads. The extension also requires a
real positive price quote and reports pending termination or an uncertain launch
identity as incomplete cleanup. These safeguards passed 74 targeted tests in
provider_guard_003; 638 declared inputs were unchanged during that run. Shared
historical sources remain unchanged. Guest or host failure remains outside the
guest timer's protection. Reservations are not invoiced charges.

An actual-fixture probe caught a separate preparation bug: the three training
questions have distinct legacy_input_id values, so their complete source_binding
objects must differ. The fix compares the nine common source fields and preserves
ordered request, prepared and legacy input identities in checkpoint metadata.
All 94 focused smoke/worker tests passed in material_fix_001. The original failed
probe is retained. The accepted ingestion adapter and cycle remain unchanged.

Launch preparation now rejects staged and unstaged tracked changes; seven real
local Git checks passed in prepare_fix_001. None of these checks ran a neural
model, created a reservation or launched provider compute.

Focused receipt SHA-256: cae54a57313414b2a7bde8de3fa5b435a661e0f5e9247abe50c5facbb42b099d

All 607 accepted source files, nine prior evidence receipts and five runtime
profiles remain unchanged. The current read-only provider audit is recorded in
provider_audit_001/REPORT.md. Existing campaign rules permit one bounded $7 job
from the canonical ledger; preparation has not reserved funds or launched it.

Previous goal turn: PROGRESS (accepted ingestion, 308 tests/306 source checks,
694-file exact GitHub readback). The full goal remains active; the earlier
three-seed recurrence result remains NOT_MET, 0/3 positive.
