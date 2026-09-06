# Final frozen source: clean pure checks passed

Source: `42f9164754312f12850d9b8789c062fa7fb8069f`.

The unchanged full canonical validator passed from a new detached checkout:
**1908 test functions passed, 356 subtests passed, 11 skipped, 2 deselected,
1 intentional duplicate-ZIP warning, 0 failures and 0 errors**.
Pytest took 216.64 seconds; the canonical validator took 222.696 seconds; the
complete worktree/source/test audit took 245.907 seconds.

JUnit contains 2275 entries, including subtests and skips. These totals overlap;
do not add them. The cold-child, orchestration and smoke-private modules were
collected and passed. The old ablation receipt-writing case that failed in the
earlier full run also passed in this complete invocation.

All 620 distinct input/source files matched their exact Git blobs and raw
checkout bytes before and after. This includes all 603 closed launch-source
inputs and all 316 protected files. The initial Git status was empty. No tracked
source changed; retained test and audit outputs are untracked evidence only.
Checkout used `git -c core.autocrlf=false worktree add --detach`.

The retained worktree is:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/prototype-v7-audit-42f91647
```

Exact command from the active META2 package directory:

```powershell
C:/Python314/python.exe -B records/clean_source_prototype_v7_002/run.py --source 42f9164754312f12850d9b8789c062fa7fb8069f --output records/clean_source_prototype_v7_002/run_003
```

The receipt, Git command log, before/after identities, exact commands, raw
stdout/stderr, JUnit and unchanged canonical receipt are retained here.
Final audit receipt SHA256:

```text
d761a19b9db1cc469b2439e44da8fda98460064fb88e22b28a276bff929c10c3
```

This used the existing Python 3.14 environment, not a new installation. It ran
pure checks and approved old/synthetic fixtures only. It did not load models or
checkpoints, use GPU/AWS/providers, generate fresh registered tasks, run neural
training, or establish a learning result. The independent records-only stored
packet checker was outside this frozen source and is not included in this pass.

Earlier failed attempts remain separate: `../run_001/` records the corrected
audit-runner input-list mistake; `../run_002/` records the original Windows
receipt-replacement error. Its two scoped passing retries are retained in
`../diagnosis_001/`. This successful final-source run does not rewrite those
results or establish the cause of the earlier access error.
