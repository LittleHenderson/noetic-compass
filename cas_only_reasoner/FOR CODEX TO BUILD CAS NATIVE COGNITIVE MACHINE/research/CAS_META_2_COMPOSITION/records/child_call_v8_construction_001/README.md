# Same-state B/R construction: local implementation checks

Current status: `BR_COMPONENT_EXECUTED`; the separate AWS result and cleanup are recorded in `records/aws_br_construction_v8_001/README.md`. The implementation-stage account below is retained as historical evidence from before that launch.

The new run used the exact source ZIP documented here. Its B/R outputs differ numerically but both decode `L2`; it proves no new learning or task-conditioned correct choice. Campaign ledger revision 13 retains a separate $4 reservation, bringing the campaign to $86 reserved and $314 unreserved. The older revision-12 figures below describe the completed local-only preparation stage.

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
- The live provider preflight and a separately recorded bounded construction job remain unexecuted; local launcher and clean-package checks are completed below.
- No new budget reservation or provider mutation was made for this local work.
- Preserve earlier CAS held-out composition **0/72**, familiar-program **24/24**, and the completed prefix diagnostic as distinct evidence.

The authoritative campaign ledger remained at revision 12, $82 reserved and $318 unreserved. That is authorization capacity, not a spending target or an invoice total.

## Completed launch and clean-package checks

The dedicated parent and remote runner are now implemented. `checks_003` passed **312 tests in 8.05s**, adding the 51 remote and 58 parent tests. Independent review also corrected S3 deletion reporting: an HTTP-success response with per-object deletion errors can no longer be reported as successful removal.

The final combined local capture, `checks_004`, passed **327 tests in 14.89s**, adding 15 clean-package verifier tests. Its receipt SHA-256 is `eaa5740cc7554305a46739fa77a1dea2f7a38dc115c8492524c1009e67ff9028`. Source, protected files and the canonical ledger remained unchanged. This is simulated/pure evidence, not a live provider launch.

Worker source is frozen at `d047540a635ecccdd2cfd4d96ee3b43da59f7ce7`. `source_001/source.zip` preserves all 616 base members and adds 13 committed source/test files plus its separate root manifest: **630 members, 8,043,470 bytes**.

- Archive SHA-256: `1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a`.
- Root manifest SHA-256: `7d5fdf331e74638b5cd1ecf9fca2c4a5ae3610aa562014decc5c03e4ca29944f`.
- The accepted baseline remains `0917267b1354e5d036263eaa6ba9a7197eafb776`, with all 316 protected files checked. Published wheels and the dependency lock are included and hashed.

`br_clean/checks_002` independently extracted that exact archive and ran its six shipped pure test files in a fresh isolated Python process: **203 passed in 5.11s**, exit 0. All 630 files were verified before and after. The child receipt lists 15 loaded `cas_meta2`/`aws` modules or namespaces and verifies that each comes from the extracted copy. No original-worktree source was used for the test imports. Receipt SHA-256: `4cf76f96e7519fa8ac2d3ecdbb6a389ccd5899f4d8001803eabd941c710c828c`.

The retained first clean attempt verified all 630 files but stopped before pytest: the wrapper requested a nonexistent `pytest.ini` instead of the shipped `pyproject.toml`. Only the wrapper and its synthetic tests changed; the source archive and worker bytes did not. Both attempts retain receipts and raw outputs.

Clean reproduction command:

```powershell
& 'C:/Python314/python.exe' -B tools/verify_br_clean_package_v8.py --archive records/child_call_v8_construction_001/source_001/source.zip --archive-sha256 1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a --source-sha d047540a635ecccdd2cfd4d96ee3b43da59f7ce7 --manifest-sha256 7d5fdf331e74638b5cd1ecf9fca2c4a5ae3610aa562014decc5c03e4ca29944f --output records/child_call_v8_construction_001/br_clean/checks_003
```

Use a new `checks_*` output name for each rerun. The command does not install or run a model. The separate live construction scope remains one `g7.2xlarge`, one GPU, a 600-second worker and at most one hour of instance lifetime, within a $4 reservation from existing campaign authority. No retries or later training are included. Actual AWS preflight, reservation, component result and cleanup still require their own receipts.
