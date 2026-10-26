# Corrected v5 Stage S retry result — 2026-10-25

## Outcome

ATTEMPT: 🟥 FAILED / WITHDRAWN — one approved launch request was accepted for `typed-probe-v5-stage-continuation-retry1-20261025`. Instance `i-0cfc096e3a09e8d7c` launched in `us-west-2c` at `2026-10-25T09:26:25Z` and AWS accepted termination at `2026-10-25T09:31:43Z`.

SCIENCE: ⬜ NULL / INCONCLUSIVE / NOT RUN — the Stage S runner stopped while reading its frozen source. New Mistral labels: **0/640**. Claude token-count and judge requests: **0**. New Qwen replies: **0**. No panel or Stage C result exists.

CAUSE: the instance role had `s3:GetObject` but lacked `s3:GetObjectVersion` for the pinned source manifest `typed_probe_v5_20261025/typed-probe-v5-stage-s-transformers-retry-20261025/output/run_manifest_stage_s.json`. The runner failed with `AccessDenied` before labeling or paid Claude inference.

METHOD: 🔧 METHOD / PROCESS WIN — VALIDATED. AWS verified Python **3.12.10**, PyTorch **2.8.0+cu129**, Transformers **4.57.1**, and a working GPU before the runner started. The live watchdog proof passed in **48 seconds**, terminated its test instance, and deleted its disk. Watchdog use is **342/420 seconds**, leaving **78 seconds**.

TIME: G5 runtime was **318 seconds** from the RunInstances event at **09:26:25Z** to the TerminateInstances event at **09:31:43Z**. Combined EC2 use is **7,492/10,800 seconds** (prior **7,126**, proof **48**, failed Stage S **318**), leaving **3,308 seconds**. Any new proof is limited to the remaining **78 watchdog seconds**. A future **3,000-second** Stage S cap plus that full proof allowance would project **10,570/10,800 seconds**, leaving **230 seconds**.

COST: Refreshed maximum-scenario estimate was **US.708043703703703703703703704/US.00**. The invoice is not settled. Claude API actual cost is **US** for this attempt; total Claude cap remains **US.00** and Stage S upper bound **US.249728**.

CLEANUP: 🔧 METHOD / PROCESS WIN — VALIDATED. Instance terminated; run-tagged EBS volumes **0**; temporary SecureString, watchdog Lambda, instance profile, IAM roles, and schedules deleted. CloudWatch records and S3 evidence remain preserved. Cleanup receipt: `CLEANUP_PASS`.

STAGE C: NOT AUTHORIZED. The **30** owner-label / **24 of 30** panel-match gate remains open and was not run.

AUTHORIZATION: the single approved retry is consumed. No second Stage S attempt is authorized. A new attempt would need a new dated owner authorization and a scoped `s3:GetObjectVersion` permission for only the pinned manifest and Mistral label objects.

EVIDENCE: S3 prefix `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry1-20261025/`; prepared proposal `docs/working/typed_probe_v5_stage_s_continuation_retry_proposal_20261025.md`.