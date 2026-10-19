# SCORE_SCRIBE_L4_SEALED_98, job c41 (2026-10-19 Pacific): SCORED — 0 of 98 exact, 77 refusals, 21 confident wrong answers that pass the round trip

Status: REAL run, one scored attempt, 0 plumbing retries. The counts below come from the plan's own script
(`score_scribe_l4.py`, sha256 `969c845e…`) run on AWS and written to `SCRIBE_L4_SEALED_98_RECEIPT.json`
(sha256 `f283d38304846ebd62482ae3fbf92739635aa6c24181b2261832127b6cf9d38c`). The plan defines no status word; its
written-before-the-run predictions are checked below. Claim ceiling stays **`ENGINEERED-NOT-VALIDATED`** (plan §6).

**Said plainly first.** We took the old small English model (Scribe L4) and showed it the 98 sealed English
sentences, once. Each sentence describes a recipe. The model can only answer with one short clause, so it can never
match a recipe. It matched 0 of 98, as the plan said before the run. It refused ("please clarify") on 77 of 98. On the
other 21 it answered with confidence, every one of those 21 answers passed the real round-trip check, and every one
of them was wrong. So the round-trip check alone let 21 of 98 wrong answers through. 🟥 That is the danger number.

## What was scored

- **Model:** Scribe L4, commit `84812689b6fb6de4250dc9bf2e400df88a95944c`. Sealed package
  `HELM_DISTRIBUTION_PACKAGE/scribe_l4_aws_gpu_training/SCRIBE_L4_AWS_GPU_PACKAGE.zip` sha256
  `7179250cbb17a800280d1b6459f2bb3ee4a23048d6b5a2382020296e8cceb58b` = its `PACKAGE_FREEZE.json` (checked before
  shipping; the package was not edited). `scribe_model.py` and `cce_shim.py` taken from that zip (byte-equal to the
  commit). Weights `e36cf3cb50fe8ae168b2986a97000a47e7632b058b34b44629f4f17f99af9dc1`, vocabulary
  `6746e5dbd77dc6ddaa7bd7270b21ca2558c4da2e439522a2fbcffc66ce4dbc1a` (both re-checked by the script on the host).
- **Exam:** the sealed held-out set `cas-synthetic/data/l4_split/real_heldout_unparseables_98.jsonl`, sha256
  `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe` before and after (`sealed_unchanged: true`).
  Not training data. The operator never opened or printed a row; the receipt holds counts only.
- **Plan:** `docs/working/scribe_l4_eval/SCORE_SCRIBE_L4_PLAN.md` sha256 `18e350f5…` (commit `9453853a`), followed as
  written: real `language_v3/cce.py` round trip through the declared adapter, gold from `scoring.content_from_parse`.
- **Laptop check before the run (stdlib, no torch, no sealed row):** `test_score_scribe_l4_adapter.py` 6/6 OK.

## Counts (exact, from the receipt)

| Count | Value | Plainly |
|---|---|---|
| rows | 98 | all sealed rows read |
| exact_match_gold | **0** | 0 of 98 match the recipe gold |
| exact_match_gold_and_cce_round_trip | 0 | |
| clarify | **77** | refused 77 of 98 (78.57%) |
| answer | 21 | answered 21 of 98 |
| cce_round_trip_ok (real CCE) | 21 | all 21 answers survive `parse(render(Ĉ)) == Ĉ` |
| answered_round_trip_ok_but_not_gold | **21** | 🟥 confident, round-trip-clean, wrong: 21 of 98 (21.43%) |
| shim_round_trip_ok (its own shim, comparison only) | 16 | 16 of 21 |
| NO_CCE_FRAME failures | 0 (key absent) | so all 21 answers had subject `Mind` |
| truncated_over_30_words | 97 | 97 of 98 inputs were cut at 32 tokens |
| input words / known to its 108-word vocabulary | 4,899 / 1,571 | 32.07% of input words readable |

## The plan's predictions vs the result

| Written before the run (plan §6) | Result | Mark |
|---|---|---|
| exact match 0 of 98 (structural) | 0 of 98 | ✅ as predicted |
| real-CCE round trip passes only on ANSWER rows with subject `Mind` | 21 of 21 answers passed; 0 `NO_CCE_FRAME` | 🟩 consistent |
| CLARIFY rate unknown; high = good | 77 of 98 | 🟨 mostly refuses unreadable English |
| high `answered_round_trip_ok_but_not_gold` = bad | 21 of 98 (every answer it gave) | 🟥 the interlock alone does not catch them |

Reading in one line: a round-trip check proves an answer is well-formed, not that it is right. This model's every
non-refusal was well-formed and wrong. No real-English reading claim follows; the ceiling stays
`ENGINEERED-NOT-VALIDATED`, and `NOT LICENSED` stays on "the Scribe reads real English".

## Job, machine, money

| Job | Instance | Launch / terminate (UTC) | Host s | Charge |
|---|---|---|---|---|
| `helm-claude-scribe-l4-score-20261019-c41` | `i-085092855ef75f1b8` t3.medium, us-west-2b, `ami-0803a33fd43db1fbf` (al2023-ami-2023.12.20261016.0), 16 GB gp3 | 23:39:36 / 23:41:34 (cleanup record 23:42:06) | 149.6 | 0.01 |

- **Pacific time:** launched 4:39 PM, terminated 4:41 PM, 2026-10-19.
- **Source:** payload `c41-payload.zip` sha256 `5a4f6981028745dac31bfb3c0c45d022eccc7e2a77ba22dcda419ef345957d03`
  (manifest `ff8eb33f…`, 178 members re-hashed on the host, 0 bad): the plan script, weights, vocabulary, the two
  Scribe code files, `language_v3/`, `bridge_root/` (`sdg_bridge_v2` and the `sdg_bridge` it imports), `lacunarity_machine_v1/`,
  the sealed file, the approval record. Built by `build_payload_c41.py`.
- **Purpose:** SCORE_SCRIBE_L4_SEALED_98 per the plan. **Limits:** cap 0.10 USD; 30 minutes (force cutoff 28 min by the
  controller and a separate watchdog; OS shutdown at +30 min with terminate-on-shutdown); one attempt + one plumbing retry.
- **Host:** Python 3.12.14, `torch==2.14.1+cpu` (CPU-only wheel); scoring took 0.168 s; SSM command `Success`
  23:39:59 → 23:41:28. No GPU.
- **Charge:** **0.01 USD** actual (list price from host time: t3.medium 0.0416 USD/h + root disk + public IPv4 =
  0.002010 USD, rounded up to the cent; bill not posted). Cautious (adds worst-case t3 CPU-credit surplus): **0.01 USD**.
  Both far under the 0.10 cap. Good.
- **Ledger:** before 111.29. Hold 0.10 placed: 111.29 → 111.39 (`BUDGET_RESERVATION_SCRIBE_L4_C41.json` `e5a446cc…`).
  Closed 111.39 → **111.30** of 200.00 (unreserved 88.70). Addendum
  `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_SCRIBE_L4_C41_20261019T234231Z.json` (`93316024…`); ledger after `4169f4de…`.
- **Cleanup VERIFIED, three ways:**
  - controller: terminated, volume `vol-09ed9ed5cfe971512` deleted, shared prefix purged (4 keys) and verified empty,
    0 multipart uploads (`aws-c41-a1-cleanup.json` `7660f8c8…`);
  - independent read-only check: `VERIFIED` 23:42:17 UTC (`aws-c41-a1-independent-cleanup.json` `e6d6cf07…`);
  - direct read-only look 23:42:19 UTC: instance terminated ("User initiated (2026-10-19 23:41:34 GMT)"), no live
    project instance, no job volume, no prefix version or delete marker, no multipart upload (`e783c582…`).
  Proof `CLEANUP_PROOF_SCRIBE_L4_C41.json` (`1eec80c6…`). No role, profile or bucket created. Watchdog saw `TERMINATED`.
- Benign control note (as at c40): one `InvalidInstanceID.NotFound` 0.1 s after launch while AWS registered the instance.
- Two harmless host warnings in `score.stderr.log`: numpy not installed (not used) and the nested-tensor prototype notice.

## Governance

- Owner's words, verbatim: "SCORE L4" (`OWNER_APPROVALS_20261018.md`, 2026-10-19 block). The plan needs the line
  `APPROVE SCORE_SCRIBE_L4_SEALED_98`; the coordinator mapped the owner's words to it and to the plan hash in
  `OWNER_APPROVAL_SCORE_SCRIBE_L4.md` (sha256 `5a35f3ba…`). The owner was not asked to re-paste.
- Small deviation (recorded): the bridge folder also carries `sdg_bridge` (v1), because `sdg_bridge_v2/bridge.py`
  imports it; this matches the PYTHONPATH the plan's laptop check used. No sealed or scored file was changed.

## Files

- Controller: `C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation\controller_claude_scribe_l4_c41\`
  (`aws_control_c41.py` `1e390751…`, `worker_c41.sh` `5bfee2f9…`, `independent_cleanup_c41.py`, `direct_check_c41.py`, all receipts).
- Deliverable: `aws-c41-a1-deliverable.zip` sha256 `8618feb41f881bc0048484ce7879ae4b8fa30ade60191040c2e86246c60e1cdc`
  (unpacked in `deliverable_unpacked\c41_out\`, SHA256SUMS all OK).
