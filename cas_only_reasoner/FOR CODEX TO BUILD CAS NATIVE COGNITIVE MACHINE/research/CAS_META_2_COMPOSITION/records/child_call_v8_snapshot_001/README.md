# B/R byte-copy preparation

The standalone file-copy helper and its guarded local tests are complete.
**68 tests passed in 3.26 seconds**, exit 0, with empty stderr. This is not a
native restoration result, a B/R numerical comparison, a learning result, or
permission to launch a GPU job.

## Implemented

`cas_meta2/br_snapshot_v8.py:copy_closed_snapshot` copies an explicitly pinned,
caller-declared closed/self-contained SQLite image into a new retained master
and two independent B/R arm files. It never opens a SQLite connection.

The helper requires a bounded regular file with the SQLite header, rejects
observed WAL/SHM/journal sidecars and links/hard links, confines new outputs to
the supplied owned directory, and refuses existing destinations. It hashes and
checks file identities before/after copying. If a later step fails, created
files remain and a failure receipt is attempted without overwriting evidence.

A successful return proves **byte-equivalent independent files only**. The
caller declaration does not prove all processes are closed. No writer lock is
taken. File hashes and sidecar observations do not prove native validity,
absence of suspended callers or equal outer allowances.

The tests use fabricated header-plus-filler bytes, not a valid native database.
Link/junction refusal includes portable metadata simulations. The hard-link
test uses real separate directory entries. No model, tensor or actual native
database is executed.

## Required native state is now clearer

The database does not hold the entire outer program. META-0 has a separate
executor checkpoint; the current META-2 composition executor has no
checkpoint/restore method. A database copy must not be described as resuming a
paused META-2 caller.

The next component check must finish its prelude before copying and preserve
the actual caller-ownership evidence and equal fresh arm limits. The complete
requirements and exact inspected source identities are in
`BEFORE_STATE_REQUIREMENTS.md`. This does not reopen the accepted META-0
restart audit or add general executor persistence.

The AWS restoration adapter, actual ordinary prelude, both native arm outcomes,
same-state witness, numerical/semantic discrimination and a public curriculum
with varying correct inputs remain **unexecuted or unbuilt**. They are separate
from the pending saved-model prefix diagnostic.

## Test evidence and correction history

- `checks_001`: **11 failed, 55 passed**, exit 1. Raw output and receipt are
  retained. The new helper compared all Path.stat fields directly with os.fstat
  fields and rejected several synthetic copies.
- `windows_stat_probe_001.json`: read-only observation of one retained failing
  test file. The two views agreed on file ID, device, link count, size and
  modification time, but reported different `ctime_ns` values.
- The fix compares shared file-identity fields across the two views while
  retaining full, ctime-inclusive before/after checks within each view.
  Tests cover both a stable cross-view difference and a real within-view change.
- `checks_002`: **68 passed**, exit 0, zero reported skips. This comprises
  41 copy tests, 25 scaffold regression tests and 2 capture-failure tests.
- The test wrapper also preserves a failed postcheck receipt if frozen-source,
  budget or launch-request checks cannot be completed. A successful synthetic
  child process is not promoted to a successful overall check in that case.

Both captures recorded unchanged frozen source, canonical ledger and prefix
launch request. The separate prefix request still has SHA-256
`745b45d437e0b17adacc71f6f945a47f8cf6767c1209f637cbadc9a2380a8cbf`.
No new approval, reservation, AWS request or paid execution occurred here.
The ledger remains revision 11: $400 cap, $78 reserved, $322 unreserved.

## Rerun

Run from:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

Use a new capture directory; the tool refuses an existing one.

```powershell
python -B tools/check_br_snapshot_v8.py records/child_call_v8_snapshot_001/NEW_CHECK
```

The command blocks neural/native/provider imports and runs only the local
byte-copy, scaffold and simulated capture-failure tests. It also checks the
frozen source and the exact prefix-request source files. These source fixtures
must be present as documented in the earlier preparation package.

`FINAL_RECEIPT.json` binds the committed preparation source and the raw
records. Temporary synthetic test files are retained locally but are not
staged into Git. The two existing source/approval commits remain unchanged.
