# Case 45: committed work, unfinished execution

The separate stored check verified 37 committed native runs and 37 traces for `generic_trained` in case 45. Their compute plans reserve 2,664 policy units. This is a lower bound on recorded work, not GPU operations, elapsed time or invoice cost.

The sealed selected program schedules 39 native runs. The next scheduled run is node 37, CJT `B`, reading node 0. This identifies the next uncommitted step in the saved program, not the worker's instruction pointer or the reason for the delay.

No completed answer or verifier receipt exists for this arm. The next tick's work, final output, full-task correctness and remaining compute are unknown. The full experiment failed. This review does not prove a deadlock or determine the timeout's underlying cause.

## Original evidence preserved

The original `native.db`, `native.db-wal` and `native.db-shm` were individually matched to the externally pinned extraction receipt, copied into `copy_001`, then rehashed at the end. The originals were never opened through SQLite.

SQLite opened only the copied database with `mode=ro` and `PRAGMA query_only=ON`. `immutable=1` was deliberately not used there, because SQLite must read the copied WAL. A SQLite backup then produced a separate closed `derived_committed.db`. Both views passed `integrity_check`; the semantic check opens only the closed derived backup read-only and immutable.

The copied SHM can change when SQLite reads the copied WAL. This does not change the authenticated original SHM. The original triplet hashes remained unchanged. "Committed" here means present in the collected SQLite transaction view, not a new power-loss durability test.

## What was checked

The check bound the exact source ZIP and 603 source files/316 protected files; the complete 72-row sealed prediction mapping; the selected public observations and action; the fixed executor model's raw artifact hash without loading it; the published trace schema; all 37 trace/commit/state/effect/cause/verifier chains and their referenced artifact bytes; and the exact 37-run prefix of the selected 39-run program. It used no private answer as an execution substitute.

It did not call the old `partial.audit_prefix`, fabricate a `failure.json` or `RuntimeContractError`, load a neural model/tensor, run a native executor, contact a provider, retry the experiment, or change frozen source. The generic trained policy's selected action and the unchanged executor model are different objects; this prefix check does not measure the candidate policy's training improvement.

## Records

- `copy_receipt.json`: `9e1708bba0701ae79e9fea2dd12044250db3c999c74de97eecb49031cf3940cd`.
- `timeout_prefix_receipt.json`: `fc444ba90f71cca2d1b539884da56f5ddc32d41b3e841c3dbf4c94867fd17fbe`.
- `copy_001/derived_committed.db`: `b46b9772631c7553991a2990350e658fc33f2159876572fd776c2dfc389e25aa`.
- Upstream extraction receipt: `9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98`.

Exact commands, from the META2 package directory:

```text
python -B records/prototype_v7_timeout_prefix_001/copy_view.py
python -B records/prototype_v7_timeout_prefix_001/audit.py
python -B records/prototype_v7_timeout_prefix_001/test_prefix.py
```

The first two commands create fixed new paths and must not overwrite their saved output. Tests use disposable new copies. They check WAL inclusion, original-byte preservation, refusal of corrupt/existing copies, the actual authenticated prefix, and rejection of wrong binding/public/model identity, missing commit rows and altered trace hashes. Initial corruption-fixture writes were themselves rejected by SQLite's immutability triggers; the final tests first assert that rejection, then remove only the applicable trigger on the disposable corruption copy to exercise the independent checker. Original and derived evidence remain unchanged.
