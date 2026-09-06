# First local wrapper attempt

The plan-only launcher returned 0, verified the archive, and reported no AWS
actions. Its exact command, stdout, stderr and clean child guard report are
preserved in this directory.

The wrapper then stopped at `budget.read_ledger()` because that convenience
function tries to create a filesystem lock. The wrapper's write guard rejected
the open before a lock was created, with `PARENT_WRITE_OUTSIDE_RECORD`. No
ledger write, reservation, neural import, provider import or provider call
occurred. This was a local diagnostic wrapper error, not a campaign failure.

The second wrapper run uses the existing pure `read_locked` state/history
validator without acquiring a lock. It checks all ledger/history hashes and
absence of a lock both before and after. Its files are under `run_002/`; the
first outputs have not been overwritten.
