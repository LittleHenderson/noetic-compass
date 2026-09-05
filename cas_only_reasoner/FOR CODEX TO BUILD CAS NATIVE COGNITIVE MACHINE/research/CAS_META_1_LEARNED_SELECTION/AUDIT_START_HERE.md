# CAS-META-1 audit entry point

Status: verified learned-selection pilot; AWS cleanup is closed. CASformer
improved from 8/72 to 66/72 correct held-out tasks. Trained generic scored 61/72;
the rule selector scored 72/72. See `RESULTS.md` for the full measured boundary.

`records/FINAL_VALIDATION_RECEIPT.json` binds the result, original checkpoints,
source archive, 195 final local tests, four GPU integration tests, complete
stored-result verification and provider cleanup. `records/AUDIT_FILE_ADDRESSES.json`
provides absolute addresses for the main source, checkpoints, traces and receipts
on this machine. Archive manifests enumerate all individual source/evidence files.

## Source identities

- Accepted executor baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.
- Original GPU training source: `a4dc9f2fc6f6d4f3d5e0b31100ac131327e02109`.
- Blackwell recovery source: `cfd22ab96c479703d09e0792a139901f2931f5bd`.
- Training job: `cas-meta1-20260905103339-cd06685e`.
- Recovery job: `cas-meta1-20260905115219-33ee1c8f`.

The recovery repeats every original prediction. It does not train or select a
new checkpoint after opening test labels. See `RECOVERY_PLAN.md` for the rules
fixed before the second launch. Post-freeze audit helpers are separate from the
code that ran on AWS and record their own hashes.

## Portable evidence

The source archive `runs/cas-meta1-cfd22ab9.zip` contains the runnable pilot,
all three accepted dependency packages, both frozen dependency wheels, the
original training packet, and a complete source/member-hash manifest.

Its SHA-256 is
`17688c68c1f35c06ea3c9fc6571c5b60af62201a69549cef3a4223a7dcb32b1f`.

Original training evidence is `records/aws_run_001/cloud_artifacts.zip`, SHA-256
`76fbb522a97e3018e946857ce71599fbdea8bb6daffd29bd15fb7cf2d091f7a0`.
It preserves the timeout, all six checkpoints, all 360 sealed predictions, and
the incomplete first evaluation. It must not be reported as a completed pilot.
The original launch receipt's cleanup warning is historical; the separate
`records/aws_run_001/cleanup_closure/` receipt closes it without rewriting it.

Job 002's launch receipt is `records/aws_run_002/launch_receipt.json`.
Its completed evidence is `records/aws_run_002/cloud_artifacts.zip`, SHA-256
`b42598370145843182515afe202a2b340e14d9a248517b4e35d62bc4daaa541e`.
The original job 002 launch receipt retains its temporary cleanup warning.
`records/aws_run_002_provider_state_closed/provider_state_receipt.json` confirms
termination, automatic disk deletion, removal of job-owned supporting resources,
and seven-day S3 retention. The separate cleanup closure records all requests.
`records/aws_run_002_semantic_audit/audit_receipt.json` confirms all 72 references
and all 360 saved outcomes were rechecked with no model or tensor execution.
Local source checks before launch are in `records/local_recovery_launch_gate/`:
187 tests passed, four GPU tests deliberately excluded; 316 baseline files and
the two installed frozen wheels were byte-checked.

## Saved candidate checkpoints

The six immutable files live in the original packet at
`cloud_job/training/{cas,generic}_{initial,best,last}.pt`.
Their hashes and selected epochs are in `cloud_job/training/checkpoints.json`.
Both models completed 60 epochs and 840 optimizer steps. CAS selected epoch 28;
the parameter-matched generic model selected epoch 55 using validation only.
Training took 57.839461555 and 13.099626616 seconds respectively on AWS.

Do not load checkpoints merely to inspect them. The byte-only inspector verifies
all six raw files without deserializing them. Neural reruns must use AWS GPU,
not the laptop. A new paid run is not part of a read-only third-party audit.

## Read-only checks and stored-result verification

From the pilot directory, with Python and the pinned dependencies installed:

```text
python -B tools/inspect_cloud_packet.py --run-dir records/aws_run_002 --predecessor-run-dir records/aws_run_001
python -B tools/audit_recovery_semantics.py --run-dir records/aws_run_002 --extracted records/aws_run_002_extracted --predecessor records/aws_run_001 --output records/third_party_semantic_audit
```

If the extracted directory is not already present, add
`--extract-to records/aws_run_002_extracted` to the first command. Extraction
requires a new directory. The second command requires a new output directory.
It uses JSON, raw bytes, schema checks and read-only SQLite. Guards prohibit
model construction/calls, tensor operations and checkpoint loading. This is
stored-result verification, not a new neural run.

The paid recovery command, environment, source archive, package-install reports,
GPU test output, profiles, individual traces and result hashes are retained in
the packets and launch receipt. `aws/README.md` describes the bounded launcher.
Keep one canonical budget ledger; copying the project does not create another
$100 allowance. There is no automatic cloud retry or T4 fallback.

## Limits on the conclusion

This pilot measures one seed, three authored procedures, 72 held-out synthetic
tasks, and five selectors using the same accepted executor. Repair is an authored
prerequisite workflow. It does not prove arbitrary program composition, complete
Noetic-fractal reasoning, general reasoning, language capability, CAS-specific
advantage, or production readiness.
