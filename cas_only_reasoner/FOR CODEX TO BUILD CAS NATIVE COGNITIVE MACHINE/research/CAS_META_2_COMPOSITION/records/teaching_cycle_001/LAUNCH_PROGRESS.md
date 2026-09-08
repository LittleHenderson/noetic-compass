# Teaching launch progress

Recorded 2026-09-08 05:33 UTC. This is a progress record, not a learning result.

## Frozen source and checks

- `874ad687bc77a86c5e9885fbf6b515ec84104a71`: new teaching transport and independent result reader.
- `d158201c6cc8dfc7da6bc933bd56bf25ded8ae37`: exact AWS price-format correction.
- `f0befae3956086eaf8d7115919f2d05349ec4b97`: bounded IAM settling before the single launch.
- Frozen worker remains `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e`.

The full corrected transport suite passed **229 tests in 127.68 seconds**.
`transport_checks_003/receipt.json` records exit 0, unchanged before/after bytes,
the exact command, Python identity, raw stdout/stderr hashes and input hashes.
Receipt SHA256:
`bdb7fc61160113de13357ed918bf748f9981e6b11b1aa68c85b69ee8d79d77b2`.
These are fake-client/process tests, with network, neural, NumPy and SQLite
execution prohibited. They are not GPU training results or a clean-clone claim.

The earlier 188- and 208-test captures remain in `transport_checks_001` and
`transport_checks_002`. Targeted 83- and 89-test correction runs were reported
in the task transcript only; no filesystem receipt for those runs is claimed.

## Attempts

`job_001`: real preflight passed, then a strict money parser rejected AWS's
`2.5200000000` string before reservation or resource creation. The raw response
and finding are preserved under that directory. The price value was not over
budget. The provider correction removes only insignificant zeros, never rounds
prices into acceptance, and leaves the raw quote and budget rules unchanged.

`job_002`: one $8 reservation, then EC2 rejected the new IAM profile ARN before
creating any instance. The same ARN had been returned by IAM roughly two
seconds earlier. Temporary cloud inputs and setup resources were removed;
local source copies and all receipts were retained. No GPU bill is inferred
from the reservation and no reservation refund is claimed. See its `FINDING.md`.

`job_003`: job `cas-meta2-teaching-20260908052915-8b5df59c`, source `f0befae3`.
The provider waited 120.88080620000255 seconds and repeated the IAM identity
check, then AWS returned instance **i-0272a6d80f3b5ad75** (`g7.2xlarge`).
The exact-instance shutdown schedule was read back before its worker permit
was released. The absolute deadline is Unix `1788852565`; no timer reset or
workload retry is authorized. A separate live EC2 read observed it `running`,
with the expected profile and job tag, request ID
`03cb2337-fdaa-4d34-972f-7838ae8a0517`.

This launch success is observed. Cross-service delay remains the inferred cause
of the previous ARN refusal; the delay itself did not prove propagation.
AWS describes IAM visibility delays at:
https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot.html#troubleshoot_general_eventual-consistency

No first CUDA-update receipt, training completion, held-out prediction or
learning result had been observed at the time of this progress record.
The launch supervisor remains active; its durable records are in `job_003/launch`.

## Budget and learning boundaries

Canonical ledger revision 19: $118 reserved, $282 unreserved, $400 inclusive
campaign cap. The current job's individual bound is $8. Reservation totals
are not AWS invoices. Ledger SHA256:
`09ab0dcc314cd12f2e317fd6184f2007e2f759cd38eb8b9d90ad019a6589f755`.

The unchanged material has 256 training tasks, 64 development tasks and three
64-task final splits. Each of four candidate arms receives up to 896 optimizer
updates across 16 passes. Final public tasks are released only after the
training process exits and its saved allocation/checkpoint checks pass.

Accepted model weights and native executors are unchanged. This pilot trains
binding selection, not unfamiliar nested programs. The familiar 24/24 and
earlier held-out CAS 0/72 remain separate evidence. Native execution, retention
after intervening learning, mastery, CAS advantage and complete CNCM remain
unproven by this progress record.
