# Capture one actual v7 offline review

Prepared wrapper only. No current result packet or actual review was opened or run while building it.

The wrapper pins job `cas-meta2-20260906094002-39762c47`, source `42f9164754312f12850d9b8789c062fa7fb8069f`, source archive SHA256 `f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9`, preparation receipt `51d7131492406f35e45e70a73b1a4cb2e3bd62f2ab03d8213562f6cd204f6ae6`, and reviewer commit `4885b96ac0a21a03376b320be74ad2bd1d49b40c`.

The packet path and its externally supplied SHA256 are mandatory. The hash is never inferred from the packet. Only the expected current-job packet path is admitted.

## Future actual command — do not run before collection and explicit packet pin

From the META2 directory, join these lines into one command after replacing the packet-hash placeholder with the externally received exact value:

```text
C:/Python314/python.exe -B records/prototype_v7_review_execution_001/run.py
  --packet records/aws_prototype_v7_001/cloud_artifacts.zip
  --packet-sha256 EXTERNALLY_SUPPLIED_PACKET_SHA256
  --output records/prototype_v7_review_execution_001/execution_001
  --review-output records/prototype_v7_stored_review_001/run_001
  --extracted records/prototype_v7_stored_review_001/extracted_001
```

All three output directories must be absent. Capture output is a direct child of this wrapper folder. Review output and extraction are distinct direct children of the frozen reviewer directory because that reviewer requires them there. No Python file is added to that directory, so its ten-file code inventory is unchanged. Links/junctions, traversal, existing directories and outside targets are refused. Nothing is deleted or overwritten.

## What is retained

- `command.json`: exact argument list, working directory and initial time.
- `process_started.json`: real child PID and wrapper PID, written after launch.
- `stdout.txt` and `stderr.txt`: binary raw child streams.
- `process_receipt.json`: start/finish/elapsed time, exact child return code, wrapper return code, identity checks before/after, output hashes, checked review-receipt hash and errors.
- `execution_result.json`: final wrapper state and process-receipt SHA256.

The preparation receipt and all ten reviewer Python files must match both recorded hashes and raw Git blobs at the fixed reviewer commit, before and after the child. The source archive and externally pinned packet are also rehashed. The reviewer itself checks the full 603-source/316-protected closure and stored data.

A child exit of zero is not enough. The wrapper requires a matching `PROTOTYPE_V7_STORED_REVIEW_PASSED` receipt, completed true, no errors, exact job/source/archive/packet/reviewer identities, a summary, and no competing failure receipt. A nonzero child exit remains recorded even if a success file exists. Preflight, child or final-check failure returns wrapper code 1 and never becomes a pass.

The total wall time includes wrapper preflight/final checks. Child finish is separately recorded. A failed capture must be kept; a later approved retry needs new output/extraction names. Interruption only requests termination of this wrapper's own local audit child, never an AWS job.

The wrapper calls no provider, imports no model and performs no training. It invokes the existing pure offline reviewer only after all supplied identities pass. An offline evidence pass is not independent GPU arithmetic or automatic learning acceptance.

## Pure preparation tests

```text
C:/Python314/python.exe -I -S -B records/prototype_v7_review_execution_001/test_run.py
```

26 synthetic tests passed in the first isolated run (3.952 seconds). Tests mock the audit child and Git authentication and use small artificial files. They cover exact commands/PID capture, required external pins, raw stream hashes, fixed reviewer/source checks, new-path guards, nonzero exit, missing or contradictory output, changed bytes, and import-hook cleanup. This is not an actual review pass.

A bounded retained repeat is provided by:

```text
C:/Python314/python.exe -I -S -B records/prototype_v7_review_execution_001/run_checks.py
```

It writes a new `checks_001` folder once. Its receipt and raw files record the repeat's actual counts and hashes. The existing Python environment is used; no package is installed.

Files: [wrapper](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_review_execution_001/run.py>), [synthetic tests](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_review_execution_001/test_run.py>), [retained check runner](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_review_execution_001/run_checks.py>).
