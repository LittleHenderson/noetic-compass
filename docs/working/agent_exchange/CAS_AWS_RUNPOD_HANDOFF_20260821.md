# CAS AWS and RunPod handoff — 2026-08-21

## Current status

- Real A40/Pythia experiment: **NOT RUN**. It has neither passed nor failed.
- AWS guardian stack `cas-runpod-guardian-v1`: `UPDATE_COMPLETE`, `ActivationMode=INERT`.
- Guardian ledger: `0` items. No Step Functions/provider execution is authorized.
- AWS GPU standby stack `cas-aws-gpu-standby-v1`: `CREATE_COMPLETE`; no EC2 instance exists and GPU compute cost is zero.
- RunPod: no new Pod was created during AWS deployment. Preserve the stopped evidence Pods and volume listed below.
- Gate 5: `OPEN / KEEP_OPEN`. Stage C: `DESIGN_ONLY / NOT_STARTED`. Corpus: `0 / 960`.

## Repository truth

- Root: `C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820`
- Branch: `codex/cas-interpretability-successor-v2`
- HEAD and upstream before this handoff commit: `f91d45aa93ae27a4499ec7fa7329b9dc0107312f`
- Preserve unrelated untracked directory `infra/runpod_precreate_guardian_aws/`; do not stage, edit, or delete it without a separate review.
- The canary execution freeze is not current after the C13/C14 source changes. Do not launch from the old preregistration/source manifest. Re-pin and re-audit only after the final source set is frozen.

## AWS work completed

- Active operator is non-root IAM user `cas-g5-operator` in `us-west-2`; MFA is attached and the owner attested MFA login. CloudTrail still has no published matching `ConsoleLogin` event, so independent `MFAUsed=Yes` evidence remains open.
- Guardian runtime ZIP SHA-256: `326F483639B8B48EC8718DDF166663A721710E353968CDE59D601BC22858BAF9`, S3 version `0SMfNuuIf0gst0QOe_Oa8O1BOzRYjTFr`.
- All nine guardian Lambdas report AWS `CodeSha256` `Mm9INjm4tI7IcY3fFmZjpyFxDjU5aM3lnWAbwihYuvk=`.
- INERT starter probe fails closed with `ACTIVATIONERROR`; recovery EventBridge is disabled.
- Live substrate checks pass: DynamoDB two-client conditional race had exactly one winner, strong read matched, cleanup returned ledger to zero; KMS P-256 DIGEST sign/verify was `True`; unsigned API POST returned `403`.
- PITR drill restored an empty disposable table, verified exact schema and zero rows, then deleted it successfully.
- AWS GPU launch template `lt-0521aede1946e3bd7` version `1` pins `g6e.xlarge` (one NVIDIA L40S, 45,776 MiB reported GPU memory) and AMI `ami-039f004668b2adc12`. It requires IMDSv2, encrypted 100-GB gp3, termination protection, shutdown-to-stop, no ingress, HTTPS-only egress, and a minimal SSM role. First boot writes `STANDBY_ONLY_NO_MODEL` and stops.
- Current On-Demand price from AWS Pricing API: `$1.861/hour`. No Capacity Reservation was created because it would bill continuously.

## Open external blockers

1. Lambda regional concurrency remains `10`. Request `20b451c3ad714eeea66ea5fdd11e56a6qTqBf9h7` for `1001` is `CASE_OPENED`. LIVE guardian reserved capacity cannot be enabled before approval.
2. On-Demand G/VT quota remains `0`. Request `dd221af97df443bfbd06b70b7d5648a7iSTWwQLf` for `8` vCPUs is `CASE_OPENED`. Do not substitute an unreliable Spot launch.
3. Empirical AWS timing/fault evidence, final versioned deployment-binding and timing documents, remote material attestation, CloudTrail/WORM export, and the independent MFA event remain open.
4. The AWS L40S fallback is not the frozen RunPod A40 experiment. It needs its own reviewed hardware/source execution binding before model work.

## Protected resources and launch limits

- Never delete or mutate protected Pod `q2oqlooejhin7s`.
- Keep stopped evidence Pod `vernmyfb3ck9po` stopped; do not restart, update, or delete it.
- Never mutate or delete network volume `hfelwlp1va`.
- Standing authority covers exactly one new bounded replacement RunPod Pod only after every live gate passes: Secure-Cloud A40, on-demand/noninterruptible, rate at or below `$0.50/hour`, exact pinned image, encrypted positive Pod volume, no network volume, only `22/tcp`, dedicated key, and a 30-minute hard bound.
- No model load or forward may occur until the production guardian, GitHub supervisor, local watchdog, exact target GET, and no-model image/GPU preflight all pass and their canonical receipts are bound.

## Next agent sequence

1. Read the canonical tracker at `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md` and recheck both quota request statuses, both CloudFormation stacks, ledger count, and CloudTrail MFA evidence.
2. While quotas are open, finish only non-provider evidence: empirical AWS recovery/STOP timing and fault tests, WORM/CloudTrail export, and immutable binding/timing artifacts. Keep the stack `INERT`.
3. After Lambda quota approval, verify reserved concurrency and exact remote artifact/ARN/hash bindings, then review the complete `LIVE` change set before execution. Do not weaken any gate to make it pass.
4. Freeze the final repository source, repair the canary source manifest/preregistration to the exact commit/image/hardware/receipt set, and rerun the full runtime, canary, guardian, and hostile negative suites.
5. Immediately before the one allowed RunPod creation, perform a fresh account inventory plus A40 stock/rate check. Use the one-send production launcher and guardian. Any mismatch or arm failure must STOP only the exact new ID and must not run the model.

## Primary files

- AWS guardian runbook: `infra/runpod_guardian_live_candidate/RUNBOOK.md`
- AWS guardian template: `infra/runpod_guardian_live_candidate/template.yaml`
- Production guardian core: `tools/runpod_open_weight_canary_v2/aws_production_guardian_core.py`
- Provider launcher: `tools/runpod_open_weight_canary_v2/create_provider_launch_receipt.py`
- RunPod canary preregistration: `docs/working/OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json`
- AWS GPU standby template: `infra/aws_gpu_standby/template.yaml`

Do not expose the RunPod API key, AWS secret values, MFA data, or receipt signing material in logs, commits, or chat.
