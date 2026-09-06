# Same-state B/R construction: local implementation checks

Status: IMPLEMENTED_AND_PURE_TESTED. Native AWS construction is not yet executed.

This adds an AWS-only component check. It is separate from the completed saved-prefix diagnostic and does not train a model or change the accepted runtime, verifier, model weights, or fixed C expectation (`L2`).

The worker first attempts the ordinary A → B → C → R sequence. Every step must genuinely accept. It then closes the owned database, retains an unopened master, and restores two independent copies with the accepted `open_native` API. It compares complete recorded before-states before either copy executes C. One copy uses the previously committed B input; the other uses R. Both receive the same fresh 8192-unit allowance and one-tick limit. No outer executor is created, so no caller stack or remaining outer allowance is silently dropped. Any ordinary refusal stops the construction; there is no repair substitution.

The output separates numerical differences, decoded content, and complete-reference provenance. Even a successful component check does not establish task-conditioned input selection, whole-task correctness, learning, or generalization. A later curriculum still needs public task conditions, valid alternative choices, and unchanged whole-task verification.

## Local evidence

`checks_002/receipt.json` records **203 passed in 5.25s**, exit 0. Receipt SHA-256:

`3e784e9e82d5f297977147022109179f206243978f7a8a5c908997a26b3425bd`

Command (run from this research package):

```powershell
& 'C:/Python314/python.exe' -B tools/check_br_construction_v8.py records/child_call_v8_construction_001/checks_002
```

The capture retains the exact child command, Python identity, raw stdout/stderr, test selection, and source, protected-file, and canonical budget hashes before and after. These identities were unchanged. Model/provider imports, actual SQLite connections, and network operations were blocked in the test process. Tests use synthetic control flow and byte-only images; no real native store or tensor was opened on the laptop.

The six test files cover the construction runner, recorded-witness checker, source packager, byte-copy helper, scaffold, and prior snapshot-capture failures. Dedicated remote/parent launcher tests were absent from this capture and are not covered by its pass count.

Retained `checks_001` stopped with one collection error: the new guard blocked the harmless `sqlite3` import used by the existing pure scaffold validation. The correction allows the import but blocks actual `sqlite3.connect` operations. Source, budget, and protected files were unchanged in that failed capture. An earlier direct test invocation, before the capture directory existed, reported 41 passed and 10 fixture setup errors due to the missing parent directory. Neither result is native execution evidence.

Independent source review found and corrected two runner gaps before the passing capture: admitted-cloud setup failures now produce a construction receipt; new-source and reservation checks now run after failures as well as success. The simulated tests exercise both paths and prove that a restored-state mismatch prevents either branch from executing.

## Boundaries still open

- No AWS B/R result, measured numerical contrast, or native availability claim yet.
- No task-conditioned B/R curriculum or child-selection training result yet.
- Launcher and clean-package checks must complete before a separately recorded bounded job can run.
- No new budget reservation or provider mutation was made for this local work.
- Preserve earlier CAS held-out composition **0/72**, familiar-program **24/24**, and the completed prefix diagnostic as distinct evidence.

The authoritative campaign ledger remained at revision 12, $82 reserved and $318 unreserved. That is authorization capacity, not a spending target or an invoice total.
