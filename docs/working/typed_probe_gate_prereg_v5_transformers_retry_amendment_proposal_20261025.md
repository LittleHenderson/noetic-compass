# Typed-Probe v5 Transformers recovery — proposed Stage S amendment

**Owner approval status: PENDING. NOT AUTHORIZED. DO NOT LAUNCH.** This is a review copy. It does not add an `AUTHORIZED: yes` entry to the decision ledger and does not grant AWS or Claude permission.

Created: 2026-10-25 (UTC)

## Why this approval is requested

The last approved Stage S attempt in `us-west-2c` successfully created one `g5.2xlarge` instance but stopped in bootstrap because `/opt/pytorch/bin/python` lacked `transformers`. The separate system Python lacked PyTorch. The instance and its root disk are now absent from AWS. No model inference or paid Claude judge request ran. The previous one-attempt approval is consumed.

The correction candidate is `docs/working/typed_probe_v5_transformers_bootstrap_fix_20261025/`. It installs `transformers==4.57.1` into the existing PyTorch interpreter, checks PyTorch and Transformers imports, and stops before key retrieval if setup fails. The candidate has a deliberate exit-90 guard and is not deployable as-is.

## Proposed owner decision

If Wakil agrees, the following dated instruction can be entered in `docs/working/agent_exchange/decisions.md` after his reply:

> `AUTHORIZED: yes`
>
> `GO — authorize exactly one corrected Stage S launch attempt in us-west-2c under the existing US$5.00 AWS and US$10.00 Claude caps, subject to the limits and stop conditions in this amendment.`

Until Wakil provides that instruction, approval remains pending. Do not treat the quoted proposed wording as an owner decision.

## One-attempt scope if approved

- Proposed run ID: `typed-probe-v5-stage-s-transformers-retry-20261025`.
- One `g5.2xlarge` launch request in `us-west-2c`, subnet `subnet-0eb3ca4bf5ca98f24`, with the existing zero-inbound security group.
- The proposed S3 run prefix was checked and is empty. It must be checked again before use.
- Configure the EC2 client for exactly one total request attempt and create a conditional, write-once S3 launch record before `RunInstances`. No second request or alternate-zone fallback is allowed.
- Use the corrected bootstrap candidate after assigning the fresh run ID and calculating new input/source hashes. Verify `torch`, the exact Transformers pin, `AutoModelForCausalLM`, and `AutoTokenizer` before retrieving the Anthropic key. Keep the frozen models, revisions, 120-row prompt bank, rubric, sampling, judge panel, analysis, and Stage S science unchanged.
- The independent exact-run-tag watchdog must pass before launch. The previously verified watchdog allowance is **213/300 seconds**, leaving **87 seconds**. If the proof fails or exceeds **87 seconds**, stop without launching.
- If the single launch request fails, the instance fails setup, or any gate fails, stop. No retry is authorized by this proposal.

## Money and time limits

- AWS all-in cap: **US$5.00**. A read-only check of the current account and AWS Price List returned `g5.2xlarge` at **US$1.2120000000/hour**, `t3.nano` at **US$0.0052000000/hour**, and a modeled maximum scenario of **US$3.707840740740740740740740740**. This is an estimate, not an invoice. Refresh it before setup and launch; stop if it exceeds **US$5.00**.
- Claude API total cap: **US$10.00**. Frozen Stage S maximum: **US$4.249728**. Previous failed bootstrap used **US$0.00** for inference/judging. Pre-count every paid request and stop at the frozen limit.
- Combined EC2 ceiling: **10,800 seconds**. Current conservative use is **1,812 seconds**, leaving **8,988 seconds**. Stage S is capped at **5,400 seconds**; if it uses the full limit, at most **3,588 seconds** remain for any later Stage C work. Stage C remains unauthorized and requires the 30-label calibration gate plus separate owner approval.
- Keep the existing cleanup requirements. Terminate the instance, delete its root disk and temporary key/roles/schedules, and retain the S3 and CloudWatch evidence.

## Evidence checked while preparing this proposal

- AWS currently returns no record for the previous instance `i-0ad494b53d5f2ae23`; `DescribeVolumes` returns `InvalidVolume.NotFound` for its former root disk `vol-01f5504d588dbc592`.
- The proposed S3 run prefix is empty.
- The latest read-only price/account check returned the rates and estimate above.
- No launch, upload, install, model inference, or Claude judge call was performed while preparing this proposal.

## Required decision record after owner reply

Only after Wakil replies with the proposed `AUTHORIZED: yes` and `GO` (or different exact limits), add the dated, exact owner instruction to `docs/working/agent_exchange/decisions.md`. Then prepare and verify the fresh source package and run the pre-launch checks. Do not launch unless every gate passes within the approved caps.
