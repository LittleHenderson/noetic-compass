# One-child curriculum and native qualification

The curriculum is saved in `dataset_001` and its source package passed the clean-extraction check. Its AWS native qualification **failed**: the R_CR candidate raised `NATIVE_RESULT_NOT_RETURNABLE` in the first development panel. See `records/aws_child_qualification_v8_001/README.md` for the preserved negative result. The curriculum is not qualified for training, and no model has been trained by this package.

## Declared lesson

The public problem supplies an ordinary A → B → C → R prelude, two child definitions, a requested observation, a requested second/fourth committed input, and a requested existing authored L2/L1 label. The candidate must choose the observation, child and input. The parent returns the child result. Labels keep their existing fixture meanings; this is not a new arithmetic or Noetic interpretation.

| Partition | Tasks | Independent contexts | Graph combinations |
| --- | ---: | ---: | --- |
| Training | 192 | 64 | 64 each B_C, B_CR, R_C |
| Validation | 72 | 24 | 24 each B_C, B_CR, R_C |
| Final test | 48 | 24 | 8 each familiar combination, 24 R_CR |

All tasks have depth 2 and exactly one child CALL. Contrast variants share a context and remain in one partition. The 112 contexts contain 336 distinct float32 observation payloads. Wording templates are separate by partition. R_CR is absent from training and validation, but is known to the builder and appears in development qualification. Final results must separate the 24 fresh familiar-graph tasks from the 24 unseen-combination tasks. Marginal choice frequencies differ between training and final evaluation, so report each combination and matched controls rather than relying on a pooled score.

`prepare_curriculum.py` creates a new `dataset_NNN` directory with training, validation, final-public, final-private, manifest, and four development-qualification tasks. Its receipt binds the actual saved counts, source hashes, command, Python identity and unchanged budget. Pure generation does not establish native acceptance for every new observation or binding.

## Native prerequisite

The four separate development tasks share fresh observations and use binding 0. Each target is checked against a public-only parser before execution. All 16 candidate actions are sealed before the first private reference executes.

For each public request, the plan is one private reference plus all four B/R × C/C→R candidates: 20 complete fresh executions, 110 planned native ticks. The accepted `native.reference_task`, `native.execute_task`, `native.verify_task` and stored-record audit remain unchanged. Candidate calls must carry real CALL/SUSPEND/RETURN/RESUME evidence. This does not restore an active caller from a database copy.

The gate requires all alternatives to execute legally; identical prelude audit rows within each public request; the correct candidate to pass the unchanged whole-task verifier; and every wrong candidate to fail task verification and have different final output bytes. A provenance difference or valid trace alone is insufficient. The four public requests need not have identical cross-request cause records.

The AWS-only worker has a 1800-second limit, one g7.2xlarge/RTX PRO 4500 GPU, no automatic retry, and no training. The parent reserves at most $4 from the existing $400 campaign ledger and enforces instance shutdown and evidence limits. A reservation is not an invoice. Failed qualification must remain a failure; it must not be repaired by changing the accepted verifier or silently substituting a different fixture.

## Source and evidence boundaries

The worker package preserves the exact 616-member accepted prefix archive and 13 B/R additions, adds nine explicitly listed files and a new root manifest: 639 members total. The accepted baseline remains `0917267b1354e5d036263eaa6ba9a7197eafb776`, with 316 protected files. Parent and remote launch code are separately committed and pinned.

`checks_001` records 178 passing guarded local tests. It predates the final parent/remote/clean-package test integration and is not a native result. Later captures must use fresh directories and keep raw failures rather than overwrite them. Local checks block neural/provider imports, actual SQLite connections and network operations.

`checks_002` records **362 passed in 59.83s**, exit 0, including the dedicated parent, remote runner and clean-archive verifier contracts. The capture confirmed unchanged source, protected prefix files and canonical budget. Its receipt SHA-256 is `7de1ebddc59955f70ba5cc767281f591bcef6f780fac5f8a9357cc62ebb97bad`. This is still pure/synthetic evidence, not actual native qualification.

The exact source freeze is `b61b011c3d53ae49a1f7f988397df632e95e82a6`. `source_001/source.zip` contains 639 members and 8,086,367 bytes; SHA-256 `d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3`. The root manifest SHA-256 is `a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d`.

`clean/checks_001` records **179 passed in 19.27s**, with every source member checked before and after. Its five mandatory files ran from the actual archive extraction, with no original-worktree import fallback. Receipt SHA-256: `ab68267aa2dad69302475525fabafb62b108c7189cc691a7e80654ddcfd62f72`. Only receipts and raw logs are versioned; the extracted source is reproduced from the ZIP.

`dataset_001/receipt.json`, SHA-256 `d77357ff9b2c67617548c404385917374ca01cb1e3ac90639793499c8677b947`, binds the saved 192/72/48 tasks and four separate development tasks to this source freeze. No native outcomes have been inferred from saving those files.

Reproduction commands from this research package root (choose fresh output names):

```powershell
& 'C:/Python314/python.exe' -B tools/verify_child_qualification_clean_v8.py --archive records/child_qualification_v8_001/source_001/source.zip --archive-sha256 d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3 --source-sha b61b011c3d53ae49a1f7f988397df632e95e82a6 --manifest-sha256 a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d --output records/child_qualification_v8_001/clean/checks_002
& 'C:/Python314/python.exe' -B records/child_qualification_v8_001/prepare_curriculum.py dataset_002
```

These commands are pure and unpaid. The separately generated `records/aws_child_qualification_v8_001/registration_001/capture_parent.py` is a paid execution entrypoint for one registered job, not a reproduction command to repeat. Its request and standing-authority registration bind the existing $400 campaign authorization and proposed $4 maximum; registration itself did not reserve money or create AWS resources.

Earlier familiar-program **24/24**, held-out CAS composition **0/72**, saved-prefix diagnostic, and completed B/R numerical contrast are separate evidence. None becomes a one-child learning result through this package. Accepted core, META-0 and META-1 audits are not reopened.
