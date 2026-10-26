# Typed-Probe v5 Stage S retry 5 — execution report

**Updated:** 2026-10-25T17:57:58Z

**Current status:** Stage S completed on the one authorized AWS instance. 🟥 FAILED / WITHDRAWN — claim status: NOT LICENSED — the frozen screen-support hard gate found 27 eligible prompts, below the required 50. No 30-item blind calibration file was created, and Stage C did not run.

## Final Stage S result — 2026-10-25T17:57:58Z

🔧 METHOD / PROCESS WIN — claim status: VALIDATED — the single AWS run completed with exit code 0. It processed 1,920 captures across 120 prompts (16 captures per prompt), preserved 1,280 earlier Mistral labels, added exactly 640, made zero new Qwen replies, and received 1,920 successful votes from each of the two Claude models. Both batches ended with 1,920 succeeded and 0 errored, canceled, or expired. All seven output files match the SHA-256 values in the final manifest. Independent checks confirmed unique and complete trace IDs, valid labels, panel-majority recomputation, prompt-summary recomputation, and exact Claude cost recomputation.

🟥 FAILED / WITHDRAWN — claim status: NOT LICENSED — the preregistered hard gate requires at least 50 prompts with a panel COMPLIED rate from 0.20 through 0.80. Only 27 of 120 prompts qualified. The panel has 423 C, 1,151 I, 125 R, and 221 U labels; U is exactly 221/1,920. The unclear-label diagnostic is therefore true. The run correctly stopped with `INSUFFICIENT_SCREEN_SUPPORT`; it did not widen the range or add prompts. Because 27 is below 50, no 30-example blind calibration sheet or answer key was created. Stage C is ⬜ NULL / INCONCLUSIVE / NOT RUN — claim status: NOT LICENSED; its 24/30 owner-match gate was not attempted.

**Claude usage and cost:** 2,653,636 input tokens and 30,693 output tokens, independently summed from all 3,840 successful vote rows. Recomputed cost at the frozen model rates is exactly **US$1.47374465**, below the Stage S cap **US$4.249728** and total cap **US$10.00**. The final manifest records this cost but omits the aggregate token-total field that the pinned runner source sets; the totals above were independently derived from the hashed vote file. This is a manifest recordkeeping gap, not a missing or partial vote file.

**Final evidence:** run manifest S3 version `5D4PWhKZCUb5MKqB79PpKlfFHtzhje8t`, SHA-256 `4296a09feed563a19d7b680d04c22a0fddcf1de309271684d456e5a5f6c3a92d`; status `INSUFFICIENT_SCREEN_SUPPORT`; finished `2026-10-25T17:51:02.785119Z`. Verified artifact hashes: captures `26a3aba342e0a0cf1d13d0875c931bd6e81f61de48af22e09a374ead8e34d832`; Mistral votes `251054ce24f950a4ab541089c0b29d0db4740d80de58222e8e4c25bd4cab0788`; Claude token counts `2f9fa50c38513a862f6537e9028544dc1e1599066e16d8383abf48afde562764`; Claude votes `846a8cabe2c866004899f3e9e9302593b4253895c0de1d8e6a4227d70a1efe19`; panel votes `bf45d75c652c44f5f4768476fd6ac57f03ced266fd1a462f17e55b2a075b87bc`; prompt summary `d857f4d78e3101bb18f6f15afe83e887271e129fd4967b7fe81252c0ec24cdd7`; eligible prompts `2d683d11e844768ad90e0300d067e1454e5041770f5eb2cceff08d6e902a7c0f`.

**AWS and cleanup:** CloudTrail records the one RunInstances event at `2026-10-25T17:24:06Z` and termination at `2026-10-25T17:51:13Z`. Direct post-cleanup checks found the instance terminated, 0 run-tagged volumes, both run schedules absent, the SecureString absent, the Lambda absent, the instance profile absent, and all 3 run-specific IAM roles absent. S3 evidence remains; the CloudWatch watchdog log group remains with 0 stored bytes. The prelaunch maximum-scenario estimate was **US$3.708043703703703703703703704** under the **US$15.00** AWS cap; it is an estimate, not a settled AWS invoice. No second launch was made.

**Next:** Do not ask Wakil to label examples from this run; the preregistered calibration sheet does not exist. Stage C remains closed. Any new screen-support plan requires a new preregistration and approval.

## Stage S progress — 2026-10-25T17:30:38Z

🔧 METHOD / PROCESS WIN — VALIDATED — initial Stage S manifest reports status SOURCE_VALIDATED, with the frozen source manifest and label checkpoint matching their pinned S3 versions and SHA-256 values. The manifest is S3 version QnlGIvUSi4WjWW60cWfbq5a.0tS6fd0M, SHA-256 5b5fa897ffa7ecfc51b61c042c924fa6f343908983a3a047d4781d6f59ec088d. It records 1,920 captures, 1,280 existing Mistral labels, 640 required new labels, zero new Qwen replies, Claude API actual cost US$0, and AWS instance i-0bc568a8c149dd482. This is a startup/source-validation receipt; it does not prove labels or panel results are complete.

🔧 METHOD / PROCESS WIN — VALIDATED — at 2026-10-25T17:31:44.518879Z, the latest manifest reports MISTRAL_CONTINUATION. S3 version 3mOW_Koik4dX0g60R1_ZzznIrt7MknnC, SHA-256 cbd12375a30eb5c652bbacfbc78f8ea82cd8ffca2864eb6809aebad045843d47. It still requires 640 new Mistral labels; new Qwen replies remain 0 and Claude actual cost remains US$0. The label output file has not appeared yet. No science outcome is claimed.

🟨 PARTIAL — MISTRAL_CONTINUATION — checkpoint snapshot at 2026-10-25T17:35:00Z contains 1,728 total labels: 1,280 preserved plus 448 new, leaving 192. S3 version 41XsHGf.6L3Fbu.hnIZdoGf6P9cxEiJK, SHA-256 ea1563ec0ee1b8428dc5d401f8ea82ec024005260b07bcc3dada77daa74380ac. All 1,728 IDs are unique, all labels are valid, all prior labels are preserved, and IDs match the exact frozen prefix. This is in-progress data, not completed Stage S science. The latest manifest at 17:34:35Z reported Claude actual cost US$0, no batches, and zero new Qwen replies.

🟨 PARTIAL — MISTRAL_CONTINUATION — checkpoint snapshot at 2026-10-25T17:36:03Z contains 1,888 total labels: 1,280 preserved plus 608 new, leaving 32. S3 version X_Yj2kYq_FZNR9cQQNW1oZjNE_WFIBmR, SHA-256 ac02691bcb468b3a26a5f81b396d8bb7918cf4fd3684929d569016677f17b165. All current IDs are unique and match the frozen prefix; all labels are valid. The latest manifest at 17:35:50Z reports Claude actual cost US$0, no API batches, and zero new Qwen replies. This is not a complete Stage S result.

🔧 METHOD / PROCESS WIN — VALIDATED — complete Mistral checkpoint at 2026-10-25T17:36:18Z: 1,920 total labels, 1,280 preserved and 640 new. S3 version hRgZrJjqTuaT91JvFt5mOc0zbKRvwZ65, SHA-256 251054ce24f950a4ab541089c0b29d0db4740d80de58222e8e4c25bd4cab0788. All IDs are unique and match the exact 1,920-ID frozen sequence; all labels are valid. The manifest updated at 17:36:41.002504Z is CLAUDE_TOKEN_COUNTING, S3 version WhdBzk2j9PvMKWzTYc4eiauqqZCbvS7i, SHA-256 b8b0c7167641df7687e2911b7d47846a4f404adf59e29de665cfec8434ead443. It reports Claude cost US$0, no message batches, and zero new Qwen replies. Mistral data generation is complete; Stage S panel evaluation is not.

🟨 PARTIAL — CLAUDE_TOKEN_COUNTING — at 2026-10-25T17:38:37Z, the token-count file contains 1,120 of 3,840 expected records, all for claude-sonnet-5-5; 1,120/1,120 are eligible for submission. File S3 version 7nC8QxA5whnLidxptbHo_1aRnSqZ5M0c, SHA-256 f0a84668f4433535bf412ff782e980f137e2fd024b8a1d1927adae8e109b66d5. Manifest status is still CLAUDE_TOKEN_COUNTING, actual Claude cost US$0, and no message batches exist. This is token-count preparation, not panel scoring.

🟨 PARTIAL — CLAUDE_TOKEN_COUNTING — at 2026-10-25T17:39:53Z, the token-count file contains 1,760 of 3,840 expected records, all for claude-sonnet-5-5; 1,760/1,760 are eligible for submission. File S3 version 5FRY8oDGhAzSjOfG4Vrqs5q_jFN4T2uH, SHA-256 8b3226a820203cf0cab23594d8dda417d2e7c962368d1a7e220ecd282010a551. The manifest remains CLAUDE_TOKEN_COUNTING; actual Claude cost US$0; message batches are empty; new Qwen replies are 0. This is not panel scoring.

🟨 PARTIAL — CLAUDE_TOKEN_COUNTING — at 2026-10-25T17:41:10Z, the token-count file contains 2,400/3,840 records: 1,920 Sonnet and 480 Haiku; all 2,400 are eligible. File S3 version ejRjo38JzR8UiNfq_f47XHVraZ9HK2Io, SHA-256 f4135caefd24e8af9d92bf8f749096fd780c5aa82dd9ead0d4b9091ac3ed85b2. Manifest status remains CLAUDE_TOKEN_COUNTING; actual Claude cost US$0; message batches empty; Qwen generation 0. Panel scoring has not started.

🟨 PARTIAL — CLAUDE_TOKEN_COUNTING — at 2026-10-25T17:42:08Z, the token-count file contains 2,880/3,840 records: 1,920 Sonnet and 960 Haiku; all 2,880 are eligible. File S3 version A4.WBN4JzmDe2jZVnxQCLpYrzIhSKkr4, SHA-256 f322c8a503602cc4814f6c8903a40981b3d6b7a5ef805e3d2af452ce055554d6. Manifest status remains CLAUDE_TOKEN_COUNTING; actual Claude cost US$0; message batches empty; Qwen generation 0. Panel scoring has not started.

🟨 PARTIAL — CLAUDE_TOKEN_COUNTING — at 2026-10-25T17:43:05Z, the token-count file contains 3,360/3,840 records: 1,920 Sonnet and 1,440 Haiku; all 3,360 are eligible. File S3 version aH1Vpgclpt78B2Zw2Z6WHktppIoPcz.a, SHA-256 c479bb080f163050a6fd73b912a942f00aa38510680b00fc37962432a02f92b1. Manifest status remains CLAUDE_TOKEN_COUNTING; actual Claude cost US$0; message batches empty; Qwen generation 0. Panel scoring has not started.

🔧 METHOD / PROCESS WIN — VALIDATED — at 2026-10-25T17:44:13Z, all 3,840 token-count records are saved and eligible: 1,920 for each Claude model. The frozen estimated maximum for Stage S is US$1.51411890, below the US$4.249728 Stage S cap and US$10.00 total Claude cap. Both batches were submitted once: claude-sonnet-5-5 batch msgbatch_016H3b6KMLrvBoRpqCDURM2e at 17:44:06.861208Z and claude-haiku-5-5 batch msgbatch_01Vkm1F7efP6exXk7NauyTQ9 at 17:44:10.865949Z. Each has 1,920 requests processing and 0 succeeded as of 17:44:13Z. Manifest actual cost is US$0 so far; it is not final billing. No new Qwen replies. Stage S panel results remain incomplete.

🟨 PARTIAL — SONNET_PANEL — the Sonnet batch ended with 1,920/1,920 succeeded, 0 errors, 0 canceled, and 0 expired. Its vote file is S3 version Ut7cU2IVbaouDJxpkqjWPOZmaCg.nnwn, SHA-256 4ae755b4b91acc234a4fe5c7081e963c4323c925d5a9e92b01d89fe7131f6acd. All 1,920 rows succeeded; IDs match the frozen sequence; labels are only C, I, R, or U; token counts are valid. Label counts: C 468, I 1,012, R 285, U 155. Haiku remains in progress; this is not the complete panel result. Manifest cost remains US$0 so far; final cost is pending both batches.

## Authorization and frozen scope

- Owner authorization: exactly one Stage S retry 5 attempt in us-west-2a, AWS cap US$15.00, Claude Stage S cap US$4.249728 and total Claude cap US$10.00.
- Proposal: docs/working/typed_probe_v5_stage_s_continuation_retry5_proposal_20261025.md, SHA-256 B81F80B9A78B99049D4143BB68FC2A4676AC6DC21A5F11F76FBD1F8CC1FB8A25.
- AWS-cap amendment: docs/working/typed_probe_gate_prereg_v5_retry5_operational_amendment_20261025.md, SHA-256 DC7A33C95B6827979A790865481E4A04D4A92EF459C2C3BA5CF5757821C831C7.
- Source: typed-probe-v5-stage-s-transformers-retry-20261025; pinned manifest version R.WaTufVeoOjQ_M0AqoTowTlOsw0O9Nx, SHA-256 06556ba04ce37b5a6a2cc104140fa184177c8565665ffde6d7326c162309ead8; 1,920 captures; pinned Mistral checkpoint version UaVLnN.nEcujm3kWFTG1r4ci2UWFgN9f, SHA-256 54724f4f15f1eaed2ce840694e7e750810c6db9c224ec1c54bfdcb1808279868, 1,280 labels; 640 labels remain. Retry 5 preparation revalidated these source pins and counts.
- Frozen work: label the existing 1,920 replies using the pinned data, add only the missing 640 Mistral labels, no new Qwen generation, and preserve the scoring rules.

## Package and pre-launch checks

- Package hash validation passed; runner SHA-256 f0858548d9f22052888359a86e5628ba244575a98c10c16249f78e8a96dc3d2c matched the startup pin. Four startup asset pins, base-runner pin, and Python syntax check passed.
- AWS identity: account 807562639912, user cas-g5-operator.
- AWS estimate: US$3.708043703703703703703703704 under the US$15.00 attempt cap. Live rate: US$1.2120000000/hour for g5.2xlarge and US$0.0052000000/hour for t3.nano. This is an estimate, not an invoice.
- Prepared package: 12 frozen inputs including its manifest; bucket versioning, AES256 encryption, and public access blocking passed. Claude model-list check found claude-haiku-5-5 and claude-sonnet-5-5. SecureString round-trip passed without printing the key.
- Direct watchdog smoke: found 0, terminated 0. Scheduled watchdog smoke: found 0, terminated 0. The saved watchdog proof matched its exact S3 version and SHA-256; cumulative sentinel use remains 342/420 seconds. No new sentinel ran.
- Final launch checks passed: no active v5 instance; subnet and security group were in the approved VPC/AZ; no inbound security-group rules; outbound HTTPS and an active Internet Gateway route were present.

## AWS launch receipt

- Run ID: typed-probe-v5-stage-continuation-retry5-20261025.
- Instance: i-0bc568a8c149dd482, g5.2xlarge, us-west-2a.
- RunInstances request ID: c83474f3-8c91-4acc-93e5-0cc505aeefe7; SDK total attempts: 1; S3 receipt status: SUBMITTED.
- AWS launch time: 2026-10-25T17:24:06.565714Z.
- Scheduled watchdog stop: 2026-10-25T18:09:00Z; launch-based runner guard: 2026-10-25T18:05:46.565714Z; hard stop: 2026-10-25T18:12:26.565714Z.
- At 17:27:59Z, AWS reported both system and instance health as ok, but no Stage S output objects or run manifest had appeared. Model inference has not been confirmed. No paid Claude inference is confirmed; preflight only checked available model IDs.
- The AMI separate SSM Agent reported that the account has no default Systems Manager instance-management role. This does not stop the run: the frozen startup script uses the EC2 role and AWS APIs directly, and monitoring uses S3 receipts and the scheduled watchdog. SSM remote login is not part of the approved run path.

## Limits and closure

- The frozen limits were one `g5.2xlarge` launch in `us-west-2a`, 3,000 maximum EC2 seconds, runner guard 2,500 seconds, scheduled stop 2,700 seconds, hard stop 2,900 seconds, AWS cap US$15.00, Claude Stage S cap US$4.249728, and Claude total cap US$10.00. One launch was submitted; no second launch was made.
- AWS maximum-scenario estimate: US$3.708043703703703703703703704. This is an estimate; the AWS invoice is not settled. Claude recorded usage cost is US$1.47374465.
- The run and its temporary AWS resources are cleaned up. S3 receipts, model outputs, and logs remain available for audit.
- Stage S ended with `INSUFFICIENT_SCREEN_SUPPORT`. Do not ask Wakil to label examples: this run produced no 30-item blind calibration sheet. Stage C did not run and remains closed. Any new screen-support plan requires a new preregistration and owner approval.
