# v5 Stage S retry 3 result — 2026-10-25

**Status: 🟥 FAILED / WITHDRAWN.** AWS accepted the one approved launch, but startup stopped before Transformers, GPU checks, or the Stage S runner. The one-attempt approval is consumed. The failure is kept in the record; no Stage C work is authorized.

## Exact AWS receipt

- Run ID: `typed-probe-v5-stage-continuation-retry3-20261025`.
- Instance: `i-0514ed057347408e4`, `g5.2xlarge`, `us-west-2c`.
- RunInstances request ID: `fecf6f70-4073-4b6b-97f6-8704f66a3254`.
- Launch: `2026-10-25T10:32:04.196465Z`.
- Startup exit record: `exit_code=1`, finished `2026-10-25T10:33:38Z`.
- Termination event: `2026-10-25T10:33:41Z`; CloudTrail request ID `f3ed8665-b742-474e-8550-d274d1530bd0`.
- Observed launch-to-termination-request interval: **97 seconds**. This is not a settled invoice.
- AWS maximum-scenario estimate: **US$3.708043703703703703703703704**, below the **US$5.00** cap. The actual bill is not settled.
- Combined EC2 accounting: **7,575 + 97 = 7,672/10,800 seconds**, leaving **3,128 seconds**. The Stage S ceiling was **3,000 seconds**; the runner did not start.
- Claude Stage S upper bound: **US$4.249728**; total Claude cap: **US$10.00**. No Claude inference request or batch was submitted. Preparation made only a model-list availability request.

## What failed

The startup script downloaded the frozen files and stopped at the first hash test. It expected the candidate-bank SHA-256 `4a6b73ecd764fce0373cdb7ce5500b00ea0dc9a4fca6be3e2a8761857b57f32f`, but the downloaded package file was `0af5a2d083ea83a69c6851466d93c8b2186a84196d41de4c91e09b9ac69d364b`. The saved log ends after the downloads; the exit record confirms code `1`.

Independent comparison found four more stale startup pins. In each case the LF-normalized file hash equals the saved startup pin, while the frozen package had CRLF line endings:

| File | Startup pin (LF) | Frozen package hash (CRLF) | Reached by startup? |
|---|---|---|---|
| `candidate_bank_v4_120_20260610.jsonl` | `4a6b73ecd764fce0373cdb7ce5500b00ea0dc9a4fca6be3e2a8761857b57f32f` | `0af5a2d083ea83a69c6851466d93c8b2186a84196d41de4c91e09b9ac69d364b` | Yes; first failing check |
| `typed_probe_v5_judge_rubric_20261025.txt` | `e176676df7cd4d1593288daf9a793e0c75a1a81cdc9d9c40980c4d1eb02307fd` | `8634597e2bdee81ca4573458a3e4e77a52fabe4e881a9723ba9f12e272745808` | No; startup stopped earlier |
| `typed_probe_gate_prereg_v5_safe_handling_20261025.md` | `c3049fbf65565cf062fdddafd91200b96a2c7fbbd3eed7daaeb513900b5e7132` | `16621f32f7ed3a730e6e35dc084c6aca3d1102bee1c622b271709f2a7ccfc32e` | No; startup stopped earlier |
| `typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md` | `7d259447e5e5bfc8e650694bba25cb99ee0d76760e76665c3d81eea9ffcc22fe` | `5759f3a61137406af7e6c881896f80f10e245d40824d7167c6805c895f21528d` | No; startup stopped earlier |
| `run_stage_s_v5.py` | `413b309d101c132f8649e29e01d560f052611a371fee0cd1c57198166deec03e` | `d65bb1d7ef7478b800024fface56a707e3790bd837aead925f86b08919f4d0a5` | No; startup stopped earlier |

The runner pin itself matched the frozen runner: `e84aa740aba9bec3c56891878855abb58c59f57f1d07999444dded7245bfb319`. The failed asset checks occurred before the Transformers and GPU checks.

## Stage S outputs

- New Mistral labels: **0/640**.
- Claude inference requests: **0**; Claude batches submitted: **0**.
- New Qwen replies: **0**.
- Stage S result manifest: **not produced**.
- Stage C: **NOT AUTHORIZED**.

Only the bootstrap log and exit record were produced under the output prefix. The AWS evidence bucket and all run receipts were retained.

## Watchdog and pre-launch record

**🔧 METHOD / PROCESS WIN.** The pinned watchdog proof passed after the retry 3 package restored the exact watchdog source bytes used by that proof. Fresh direct and scheduled no-instance checks both logged `found: 0` and `terminated: 0`. A pre-launch manifest check also caught a path-check bug; it was corrected before launch, and a new version of the S3 manifest records the corrected setup hash. These process checks did not make Stage S run.

The startup shell was normalized to Unix line endings, and the runner pin was corrected. However, the four data/document inputs and `run_stage_s_v5.py` remained CRLF while their startup pins represented LF. The first candidate-bank check stopped the run; the later stale pins were confirmed by file comparison but were not reached.

## Cleanup

**CLEANUP_PASS.** AWS confirms the instance is `terminated`, **0** run-tagged EBS volumes remain, both schedules are absent, the temporary secure parameter and watchdog Lambda are deleted, and the instance profile and all three run-specific IAM roles are deleted. CloudWatch logs and S3 evidence are preserved.

Evidence keys:

- `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry3-20261025/provenance/stage_s_launch_attempt.json`
- `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry3-20261025/provenance/prelaunch_package_gate_correction.json`
- `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry3-20261025/output/logs/instance-bootstrap.log`
- `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry3-20261025/output/logs/instance_exit_status.txt`

## Next

A separate retry 4 package and proposal are now prepared locally: `docs/working/typed_probe_v5_stage_s_continuation_retry4_20261025/` and `docs/working/typed_probe_v5_stage_s_continuation_retry4_proposal_20261025.md` (SHA-256 `183aaf822b909b97e78c01538023b023a437e8976e6e4b2a8043020004b1876a`). Static preflight confirms **12/12** package input hashes, the runner pin, all six startup asset pins, and the LF startup script. The authorization latch is false; no retry 4 AWS setup or launch has occurred. A new one-attempt authorization is required. Stage C remains NOT AUTHORIZED.
