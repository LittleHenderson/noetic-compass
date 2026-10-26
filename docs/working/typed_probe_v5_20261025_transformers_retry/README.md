# Typed-Probe v5 Transformers recovery attempt

This folder contains the fresh, single-attempt Stage S package authorized on 2026-10-25. It corrects the prior AWS bootstrap failure by installing the pinned `transformers==4.57.1` package into `/opt/pytorch/bin/python`, then checking PyTorch, Transformers, `AutoModelForCausalLM`, and `AutoTokenizer` before the runner can retrieve the Claude key.

## Fixed run limits

- Run ID: `typed-probe-v5-stage-s-transformers-retry-20261025`.
- Region and zone: `us-west-2`, `us-west-2c`.
- Instance: one `g5.2xlarge` launch request only.
- AWS maximum modeled estimate: no more than US$5.00; the estimate must be refreshed before setup and launch.
- Claude total cap: US$10.00; frozen Stage S upper bound: US$4.249728.
- Stage S runtime cap: 5,400 EC2 seconds.
- The live watchdog proof must pass using no more than 87 sentinel EC2 seconds. Failure or a limit overrun means no Stage S launch.
- No local model execution, alternate zone, retry, or Stage C work is authorized.

## Package contents

- `cloud_setup_stage_s.py`: lightweight AWS checks, preparation, and the single launch command.
- `cleanup_v5_aws_resources.py`: run-scoped cleanup that preserves S3 results and CloudWatch logs.
- `watchdog_e2e_proof_transformers_retry.py`: live, exact-run-tag watchdog proof with a write-once attempt record.
- `cloud_watchdog.py`: watchdog Lambda source.
- `user_data_stage_s.sh`: fail-closed instance bootstrap with the Transformers correction.
- `run_stage_s_v5.py`: frozen Stage S runner.
- `candidate_bank_v4_120_20260610.jsonl`: frozen 120-row candidate bank.

The package is staged only after the refreshed account, price, source, AWS identity, key, S3, IAM, and cleanup checks pass. Stage C remains unauthorized.

## Final outcome — 2026-10-25

- 🔧 METHOD / PROCESS WIN — VALIDATED: AWS ran the Stage S program with Python 3.12.10, PyTorch 2.8.0+cu129, `transformers==4.57.1`, and an NVIDIA A10G GPU. This confirms the AWS environment correction worked.
- 🔧 METHOD / PROCESS WIN — VALIDATED: the pre-launch watchdog proof passed in 53 seconds. Total watchdog sentinel use is 266/300 seconds.
- 🟨 PARTIAL — REAL: the run saved all 1,920 replies from 120 prompts (16 each). Mistral labeled 1,280/1,920 replies, then the watchdog stopped the instance at 2026-10-25T08:10:30Z.
- ⬜ NULL / INCONCLUSIVE / NOT RUN: labeling and the behavioral screen did not finish. There is no complete panel result or quality conclusion. Stage C remains unauthorized.
- 🔧 METHOD / PROCESS WIN — VALIDATED: AWS confirms the instance is terminated and the run-tagged disk, secure key, schedules, Lambda, instance profile, and three temporary roles are gone. The evidence remains in S3. The CloudWatch watchdog log group exists and reports 0 stored bytes.

The Stage S elapsed time from the launch receipt to the watchdog termination request was 5,135.397787 seconds. The conservative whole-second cap tally is 5,136/5,400 Stage S seconds. The combined conservative EC2 tally is 7,001/10,800 seconds. AWS's maximum-scenario estimate was US$3.707840740740740740740740740 under the US$5.00 cap; it is not a settled invoice. The run manifest records `api_actual_cost_usd` as `"0"`; the Claude cap remains US$10.00.

See [`evidence_summary.json`](evidence_summary.json) for hashes, S3 versions, counts, and cleanup checks. The one approved Stage S launch is consumed; this run folder does not grant another launch or Stage C authority.
