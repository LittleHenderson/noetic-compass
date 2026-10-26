# Typed-Probe v5 Stage S continuation — authorized scope

**Date:** 2026-10-25 (UTC)

**Status: AUTHORIZED FOR ONE STAGE S CONTINUATION; PRE-LAUNCH GATES OPEN.** The owner supplied AUTHORIZED: yes and GO on 2026-10-25; see the dated entry in docs/working/agent_exchange/decisions.md. No AWS resource or launch request has been created for this continuation.

## Recommended action

Authorize exactly one bounded Stage S continuation using the outputs already saved by run `typed-probe-v5-stage-s-transformers-retry-20261025`. This avoids generating a second set of 1,920 replies. The continuation would use the same frozen 120 prompts, same 16 saved replies per prompt, same models, revisions, rubric, labels, and Stage S calculations.

The current `run_stage_s_v5.py` always starts a new Qwen generation and overwrites its local captures; it has no resume support. Therefore, before any AWS setup, prepare and hash-check a separate continuation runner that:

1. Reads the existing 120 capture files and the 1,280-row Mistral checkpoint from the prior S3 prefix; verifies their hashes and trace IDs; and never writes over that prefix.
2. Labels only the missing 640 replies with the frozen Mistral version and settings.
3. Runs the frozen 3,840 Claude token-count checks, submits the two frozen 1,920-request judge batches, and writes the same Stage S panel, prompt-rate, eligible-prompt, and calibration artifacts into a new S3 prefix.
4. Stops within the limits below, preserves each checkpoint, and deletes its instance, disk, temporary key, schedules, Lambda, profile, and roles. It does not start Stage C.

If the continuation runner cannot pass the source, input, budget, and cleanup checks without changing the frozen protocol, do not launch. No Qwen generation, local model execution, second launch, alternate-zone fallback, or Stage C work is included.

## Current evidence and limits

- AWS confirms no active v5 instance and no run-tagged disk remain.
- Existing S3 source prefix: `typed_probe_v5_20261025/typed-probe-v5-stage-s-transformers-retry-20261025/`.
- The prior run saved **1,920/1,920** replies from **120** prompts. Its Mistral checkpoint contains **1,280/1,920** unique trace IDs. Capture-body SHA-256: `26a3aba342e0a0cf1d13d0875c931bd6e81f61de48af22e09a374ead8e34d832`. Checkpoint SHA-256: `54724f4f15f1eaed2ce840694e7e750810c6db9c224ec1c54bfdcb1808279868`.
- The saved run manifest records Python **3.12.10**, PyTorch **2.8.0+cu129**, Transformers **4.57.1**, and NVIDIA A10G. Claude `api_actual_cost_usd` is recorded as `"0"`; no token-count result or judge batch was recorded.
- The existing conservative combined EC2 tally is **7,001/10,800 seconds**, leaving **3,799 seconds**. Watchdog sentinel use is **266 seconds**.
- The AWS Price List API was queried on 2026-10-25. It returned On-Demand Linux rates of **US$1.2120000000/hour** for `g5.2xlarge` and **US$0.0052000000/hour** for `t3.nano` in US West (Oregon). AWS documents On-Demand compute as billed by hour or second ([AWS EC2 On-Demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/)).
- Cost Explorer's v5 project-tag query currently returns **US$0** with `Estimated=true` and no groups. This is not a settled invoice or proof of the final charge.

## Requested one-run authorization

- **Purpose:** finish the saved Stage S screen from the frozen existing replies.
- **Run ID:** `typed-probe-v5-stage-s-continuation-20261025`; use a fresh S3 output prefix and a write-once launch record.
- **Instance:** one On-Demand `g5.2xlarge` in `us-west-2c`; exactly one `RunInstances` request. No retry or second-zone fallback.
- **GPU instance maximum:** **3,500 EC2 seconds from launch**, including setup. The stop schedule must enforce this wall-clock maximum; the runner must stop earlier if its own guard expires.
- **Watchdog:** extend the total sentinel allowance from **300 to 420 seconds**. **266 seconds** are already used, so this proof may use at most **120 seconds**, ending at no more than **386/420 seconds**. If the proof takes longer than 120 seconds or any check fails, do not launch.
- **Combined EC2 ceiling:** after the maximum continuation and proof, conservative use is **10,621/10,800 seconds** (**7,001 + 3,500 + 120**), leaving **179 seconds**.
- **AWS cap:** maximum all-in estimate **US$3.708043703703703703703703704**, below the existing **US$5.00** cap. This intentionally conservative model charges the full 10,800 G5 seconds plus the full 420 watchdog seconds, 100 GiB main disk, 8 GiB sentinel disk, 1 GiB-month S3 allowance, and three hours of public IPv4. Refresh the Price List estimate immediately before setup and launch; if it exceeds **US$5.00**, stop.
- **Claude cap:** keep the existing **US$10.00** total cap and **US$4.249728** Stage S upper bound. Recount each paid request before submission and stop at either cap. No paid judge request is permitted before the new dated authorization.
- **Cleanup and evidence:** terminate compute and remove all run-scoped temporary resources; keep the old run evidence and new S3 receipts. Do not claim Stage S complete unless all frozen outputs are present and the manifest says the frozen completion status.
- **Stage C:** NOT AUTHORIZED. Wakil's 30-example calibration and at least **24/30** exact panel matches are still required, followed by separate authorization.

## Owner response received

The owner approved this scope on 2026-10-25 with: “AUTHORIZED: yes; GO — approve one Stage S continuation under the proposal.” The dated record is in docs/working/agent_exchange/decisions.md. This approval covers only the scope and limits above. The runner, input hashes, refreshed AWS estimate, watchdog proof, one-request launch control, and cleanup gates must pass before launch. Stage C remains unauthorized.
