# v5 Stage S retry 4 — verified startup asset hashes

**Date:** 2026-10-25  
**Status: AUTHORIZED FOR ONE ATTEMPT; PRE-LAUNCH GATES OPEN.** Approval is recorded below. No retry 4 AWS setup, launch, or model inference has been performed.

## Why a new package is needed

Retry 3 is 🟥 FAILED / WITHDRAWN. AWS accepted one `g5.2xlarge` launch, but the shell stopped at its first file hash test before Transformers, GPU checks, or Stage S. The package stored five text inputs with CRLF line endings while the startup pins represented LF bytes. The first candidate-bank test failed; four further stale hash checks were found by comparison. Retry 3's full receipt is in `docs/working/typed_probe_v5_stage_s_continuation_retry3_result_20261025.md`. Its one-attempt authorization is consumed.

## Retry 4 corrections

This is a separate package and run ID. Its startup pins now match the exact bytes in the staged files:

| Frozen file | Retry 4 startup SHA-256 |
|---|---|
| `candidate_bank_v4_120_20260610.jsonl` | `4a6b73ecd764fce0373cdb7ce5500b00ea0dc9a4fca6be3e2a8761857b57f32f` |
| `typed_probe_v5_judge_rubric_20261025.txt` | `e176676df7cd4d1593288daf9a793e0c75a1a81cdc9d9c40980c4d1eb02307fd` |
| `typed_probe_gate_prereg_v5_safe_handling_20261025.md` | `c3049fbf65565cf062fdddafd91200b96a2c7fbbd3eed7daaeb513900b5e7132` |
| `typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md` | `7d259447e5e5bfc8e650694bba25cb99ee0d76760e76665c3d81eea9ffcc22fe` |
| `run_stage_s_v5.py` | `413b309d101c132f8649e29e01d560f052611a371fee0cd1c57198166deec03e` |
| `stage_s_continuation.py` | `2182ab33e8e5b5a456d26402074f6dba85542476da6be59f6ef2258a5ee93f0f` |

The setup script will compare every startup pin above with its frozen package file in both `prepare` and `launch`, before any AWS calls. It also checks the shell is LF-formatted, the retry 4 proposal hash, the runner pin, and the prepared manifest's special `provenance/user_data_stage_s.sh` location. The watchdog source is byte-identical to the source used by the passed immutable proof. Fresh direct and scheduled no-target checks remain required.

## One proposed attempt

- **Run ID:** `typed-probe-v5-stage-continuation-retry4-20261025`.
- **Compute:** exactly one On-Demand `g5.2xlarge` in `us-west-2c`; one `RunInstances` request, no automatic retry, no alternate zone.
- **Saved inputs:** recheck the pinned 1,920 replies and 1,280 existing Mistral labels; add only the missing 640 labels. Generate no Qwen replies.
- **Time limits:** Stage S maximum **3,000 EC2 seconds**; runner guard **2,500 seconds**; scheduled stop at **2,700 seconds**; hard stop at **2,900 seconds**.
- **Combined EC2 limit:** recorded use before retry 4 is **7,672/10,800 seconds**. A 3,000-second attempt projects **10,672/10,800 seconds**, leaving **128 seconds**.
- **Watchdog:** reuse the passed immutable watchdog proof pinned by exact S3 version and SHA-256; new watchdog proof EC2 time is **0 seconds**. Cumulative watchdog use is **342/420 seconds**, leaving **78 seconds**. Fresh direct and scheduled no-target checks for retry 4 must pass before launch.
- **AWS cap:** **US$5.00** all-in. The latest maximum-scenario estimate is **US$3.708043703703703703703703704**; refresh after approval and before setup and again before launch. Do not launch above US$5.00. This is an estimate, not an invoice.
- **Claude cap:** Stage S upper bound **US$4.249728**; project total cap **US$10.00**. Count and reserve each request before submission; do not retry an unconfirmed batch.
- **Stage C:** **NOT AUTHORIZED.** It still requires 30 human labels and at least 24/30 panel matches, followed by its own authorization.
- **Cleanup:** terminate the instance and remove only retry 4's disk, schedules, secure parameter, Lambda, profile, and IAM roles. Preserve S3 evidence.

## Launch gates

Before setup and again immediately before launch: verify AWS account `807562639912`, refreshed price, exact source object versions and counts, empty retry 4 prefix, input hashes, API key type and run tag, reused watchdog proof, direct and scheduled no-target checks, permissions, subnet and security group, capacity in `us-west-2c`, and no retry 4 resources or active instance. Stop on any failed gate. Launch only once if every gate passes.

## Owner approval required

No AWS setup or launch is authorized by this draft. To authorize exactly one retry 4 attempt under the limits above, reply:

`AUTHORIZED: yes; GO — approve one Stage S retry 4 with verified startup asset hash pins under docs/working/typed_probe_v5_stage_s_continuation_retry4_proposal_20261025.md.`


## Owner approval received — 2026-10-25T14:25:05Z

RATIFIED-BY: owner message in this thread (verbatim): `AUTHORIZED: yes; GO — approve one Stage S retry 4 with verified startup asset hash pins under docs/working/typed_probe_v5_stage_s_continuation_retry4_proposal_20261025.md.`
SCOPE: Exactly one Stage S retry 4 attempt under this proposal. AWS setup and launch remain gated on all listed checks passing. Stage C remains NOT AUTHORIZED.
