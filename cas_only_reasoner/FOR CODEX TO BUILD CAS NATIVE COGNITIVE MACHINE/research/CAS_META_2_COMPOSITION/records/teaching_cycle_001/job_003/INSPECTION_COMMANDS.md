# Local inspection commands for collected teaching job 003

Both commands below were executed with Python 3.12.10 and exited 0. They block
neural, NumPy, SQLite and cloud imports. Neither trains or loads a checkpoint
tensor. Output paths must not already exist; use different fresh destinations
when rerunning, and point the second command at the first command's extraction.

Working directory:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION
```

These are command transcripts, not a separate raw stdout capture. Generated
receipts retain their own full results. The original ZIP and all input receipts
are preserved. No final private targets were opened by either command.

## Verify and extract

```powershell
& 'C:/Users/wakil/AppData/Local/Programs/Python/Python312/python.exe' -I -B tools/evaluate_teaching_launch.py --parent-result records/teaching_cycle_001/job_003/launch/result.json --parent-sha256 c12347f65d38dc883221b9f9ddb48099574c851acc858d6d6444a0eaa2295b76 --archive records/teaching_cycle_001/job_003/launch/partial_collected/artifacts.zip --archive-sha256 73a1e22bdf011380527d78fd72f2a343bfffa1d302eedffc57b0f5417aa361e9 --complete-marker records/teaching_cycle_001/job_003/launch/partial_collected/complete.json --complete-sha256 72e855be29eef920df8cf4089b6f81347a9b709a952e7f6d9aff44208e7d97a7 --material-root records/teaching_cycle_001/material_001 --output records/teaching_cycle_001/job_003/evaluation_001
```

Result: `PARTIAL_EXPOSURE_ONLY`, exit 0. Generated `evaluation.json` is 88123
bytes, SHA256 `0574d29371108ef8ef0a08c8af79216e638deabeffd3b6f5a323e6c57d953f18`.

## Verify existing checkpoint journals and pure resume checks

```powershell
& 'C:/Users/wakil/AppData/Local/Programs/Python/Python312/python.exe' -I -B tools/inspect_teaching_continuation.py --parent-result records/teaching_cycle_001/job_003/launch/result.json --parent-sha256 c12347f65d38dc883221b9f9ddb48099574c851acc858d6d6444a0eaa2295b76 --archive records/teaching_cycle_001/job_003/launch/partial_collected/artifacts.zip --archive-sha256 73a1e22bdf011380527d78fd72f2a343bfffa1d302eedffc57b0f5417aa361e9 --complete-marker records/teaching_cycle_001/job_003/launch/partial_collected/complete.json --complete-sha256 72e855be29eef920df8cf4089b6f81347a9b709a952e7f6d9aff44208e7d97a7 --extracted-root records/teaching_cycle_001/job_003/evaluation_001/extracted --output records/teaching_cycle_001/job_003/continuation_inspection_001.json
```

Result: `STRUCTURALLY_RESUMABLE_GPU_RESTORE_UNTESTED`, exit 0. Generated receipt
SHA256 `a47ced1ca072041306f8e4a47f2efb03ec97d5690659b14ab19cd0e19141ef6d`.

The retained latest checkpoint file hashes and committed counts are in that
receipt. The actual GPU restore, optimizer restore, tokenizer/tensor geometry
check and continuation launch are explicitly unexecuted.

## One-shot supplemental AWS cleanup (already executed; do not rerun)

Unlike the two pure inspection commands above, this command used the existing
SDK-capable Python 3.14.0 environment, boto3/botocore 1.43.87, and live AWS.
The tool was committed at `6c993db1bdc459dc58ee7629a51e3ba7470200b0` before
execution. It only closes this already-terminated job's temporary resources.
Its fixed output path deliberately refuses a second execution.

```powershell
& 'C:/Python314/python.exe' -B tools/recover_teaching_job003_cleanup.py --output records/teaching_cycle_001/job_003/cleanup_recovery_001 --profile default
```

Result: `CLEANUP_CLOSED_RESULTS_RETAINED`, exit 0. Supplemental result SHA256
`9a1516b871820125bc914bef3c8fef899b532b49e56b80e641067f880a895500`.
Tool SHA256 `0da31256f5ebe5cf3577c26c1f010c942d578f2e042647cbeb043054d5a19a25`.
The original failed cleanup receipt was not overwritten. No workload was
launched or retried; no model, ledger or S3 result object was changed.
