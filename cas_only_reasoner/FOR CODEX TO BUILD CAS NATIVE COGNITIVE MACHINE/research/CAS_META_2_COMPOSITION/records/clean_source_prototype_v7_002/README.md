# Clean v7 source check — prepared, not yet run

This runner is ready for a later frozen source commit. Its presence is not a
clean-checkout pass, a GPU result, or permission to start a paid job. Do not run it
until the owner supplies the exact frozen source SHA.

## Run after the source is frozen

Commit this `run.py` and this README as part of that source first. The runner
refuses to use audit-tool bytes that differ from the supplied commit. Use the
existing Python 3.14 environment; do not create or install an environment for
this check.

From the META2 package directory, replace the placeholder with the exact
40-character lowercase commit SHA and choose a new output name:

```powershell
python -B records/clean_source_prototype_v7_002/run.py --source EXACT_40_CHARACTER_FROZEN_SHA --output records/clean_source_prototype_v7_002/run_001
```

The output must be a new immediate child of this record directory. No files or
worktrees are overwritten or deleted. A retained worktree with the same short
SHA blocks this command; do not remove it or reuse its test output to make a
rerun look new.

The detached worktree is created at:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/prototype-v7-audit-<sha8>
```

The runner checks that this exact target is absent, inside `_worktrees`, and
free of links or junctions. It uses `git -c core.autocrlf=false worktree add
--detach` and records the initial clean Git status before creating test output.
It does not move the active task or change its branch.

## What the run checks

- The full closed v7 launch input list, read from the frozen profile. Its count
  is computed, not hard-coded. Each listed file must be present in Git and its
  raw checkout bytes must match the Git blob and any published hash. The source
  manifest is checked with the frozen builder's pure `make_manifest` function.
  This does not build, upload, or execute a launch archive.
- The canonical META2 source snapshot and all 316 protected baseline files.
- The exact original 256 training tasks, saved seed `926603` base dataset,
  saved `352/24/9` merged dataset, source pins, public loader, and retained
  portable-proof code. No new registered tasks are generated or inspected.
- Both cold-child helper scripts, all nine saved merged-bundle files, and all
  eight public-export files needed by the included cold-child and smoke tests.
  These dependencies must also be in the closed launch input list.
- The same Git and raw-byte identities after testing, with no tracked changes.

The runner then calls the unchanged `tools/validate_local_v3.py` from the clean
checkout. That validator starts its own fresh pure Python test process and runs
the full `tests` directory with `-m "not gpu"`, plugin auto-loading disabled,
empty CUDA visibility, and its established neural/provider import guard. Its
narrow exception-class allowance remains unchanged. The validator's own
600-second test limit is unchanged; the outer wrapper allows 660 seconds to
retain its final records.

The new cold-child, orchestration, and smoke-private test modules must appear in
JUnit and finish without failure, error, or skip. They are not run a second time
or added twice to a total. Existing tests may construct their approved old
diagnostic fixtures; none of this is fresh held-out evaluation. Cold-child tests
use real local exited processes but simulated AWS/path permissions. Orchestration
and training-entry tests use synthetic or mocked work, not models or GPUs.

## Retained evidence and limits

Each output keeps worktree creation commands and raw output, initial/final Git
status, all requested Git-blob paths and hashes, before/after file identities,
the exact validator command, raw stdout/stderr, the unmodified JUnit XML and
canonical receipt, environment identity, and an overall receipt. Partial and
failed runs are retained. The wrapper timeout covers its direct process only;
it does not claim to terminate independently detached grandchildren.

Function counts and subtest counts remain separate. JUnit totals include
subtests; the runner never adds these overlapping counts. Skips, deselections,
warnings, failures, and errors are reported from their actual records. An absent
summary or JUnit file is not converted into a successful zero-test run.

This is an existing-environment clean-source check, not a fresh installation.
It uses the original repository's Git object history where existing pure tests
check frozen historical source. It uses no untracked active-worktree inputs,
downloaded failure packet, current registered dataset, model import, checkpoint,
provider call, paid job, or neural training. A passing receipt does not claim
learning, native task correctness on new data, or production readiness.

Preparation was adapted from the retained
`records/clean_source_recovery_v6_002/run.py` workflow. Earlier failed and passed
source proofs remain separate and are not overwritten or used as the result of
this run.
