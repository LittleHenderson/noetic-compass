# Separate AWS launch path for the decoder comparison

The new files are `aws/launch_ablation_v4.py`,
`tools/build_launch_bundle_ablation_v4.py`,
`tools/experiment_profiles_ablation_v4.py`, and `EXPERIMENT_ABLATION_V4.json`.
The old training launcher, builder, experiment profile and specification are
unchanged. The first cloud attempt stopped before prediction because its
decoder-test command inherited the local "not gpu" marker. The corrected
candidate explicitly selects the GPU tests; the required two-test gate remains.
The failed source and packet are preserved under
`records/aws_ablation_v4_source_001` and `records/aws_ablation_v4_001`.
No successful decoder comparison has yet been demonstrated.

## What stays fixed

The launcher retains the existing $400 total budget ledger and owner-approval
checks. The current registered resource plan is one `g7.2xlarge` Blackwell GPU,
at most two hours, a $7 reservation, no automatic job retries, encrypted scratch
storage, HTTPS-only outbound access, and seven-day evidence expiry. It is not a
T4 or H100 launch. H100 requires a separately validated plan and sufficient
provider quota; the last observed H100 quota was zero.

The new launcher shares the v3 execution-lock path and checks for active CAS jobs
before reserving or creating another instance. Read-only live account, instance,
AMI, quota and pricing checks precede the budget reservation. The AWS scheduler
deadline must be confirmed before installation or neural work is permitted.
Guest shutdown, local observation, tagged-resource ownership checks, bounded
artifact collection, download verification and cleanup behavior are retained.

The pure tests compare the ASTs of those unchanged infrastructure helpers with
the frozen v3 launcher. This checks implementation continuity; it does not prove
that a future provider operation or cleanup will succeed.

## What changes

Only `decoder_ablation_v4` is an accepted experiment profile. The exact spec
forbids training, fresh-held-out claims and source-release acceptance. The old
training and smoke profiles cannot dispatch through this launcher. The package
explicitly includes only the pinned checkpoint-input ZIP and five reconstructed
dataset fixture files from historical records; other historical records/runs
remain excluded. All six exceptions are checked against fixed original hashes.

The remote command invokes `cas_meta2.ablation_campaign_v4` with the exact job,
preserved input archive and remaining time budget. Existing native and neural
contract tests remain required. These may exercise synthetic gradients, but
cannot retrain or update the four saved candidate checkpoints. The comparison
itself performs inference only.

Success requires both modes' prediction seals, native results, grouped results,
the prediction-exit gate and strict payload index. The receipt must match the
launched experiment and job, report 72 cases / 360 arm verdicts per mode, and
retain the no-training/no-fresh-held-out/no-release-acceptance boundaries.

## Before a paid run

Commit and test the complete source, then build the bundle from committed Git
bytes. Independently validate the generated archive and launcher identity. Check
the current provider state and remaining ledger, then execute with the existing
approved cap. The launcher must reserve before provider mutations; never bypass
an existing live job, lock, uncertain launch, missing quota or changed-price
refusal. Preserve failure evidence and verify shutdown instead of blindly retrying.

A successful cloud exit is still not a CAS-specific advantage or a newly learned
skill. Inspect and audit the complete packet and actual task outcomes afterward.
