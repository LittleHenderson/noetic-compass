# GRAPH6_CONFIRMATION_001 — attempt 002 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Replacement for attempt 001, which failed in
the first candidate's before-loss pass after 549.2 s with `KeyError: '26da6b16…'`.
Cleanup was verified complete and independently confirmed; the error and root
cause are preserved in `ATTEMPT_GRAPH6_CONFIRMATION_001_FAILURE.md`.

## What went wrong, in one line

`trainer.launch(seed=…)` selects the **teaching dataset**, and the new
confirmation code passed the candidate's **learner-init seed**, so the trainer
generated a different dataset than the learner's index — a bug in my new
confirmation code, not in the frozen candidate or the module.

## What changed (and what did not)

Changed:
* the trainer now always receives the frozen dataset seed `20260909`;
* a fail-closed guard (`TRAINING_DATASET_SEED_CHANGED`) rejects any other dataset
  seed instead of dying later with a `KeyError`;
* the candidate record now reports `training_dataset_seed` next to `learner_seed`
  and `encoder_seed`;
* two regression tests pin all of the above (34 confirmation tests pass).

Unchanged: the frozen candidate, the encoder and tokenizer fitting set, the
teaching records and order, the allowance (64 updates / 600 s / lr `0.003` per
candidate), the three learner seeds, the fresh 90-case panel (same content
digest `d1076de3…`), the pre-registered fit and transfer rules, the uncertainty
method, baseline row mode A, and the total budget.

## Exact package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `a387d882250b526301d580face0bd11361f37941` |
| archive_sha256 | `b0f013fa052625e24ec2098fa41f6264b59527725203378cd117b2e7e46d0ee6` |
| archive_bytes | 385710 |
| manifest_sha256 | `773875ae7c39fc9ed2cf425758c0a949946f1274a20fc0c05fd29b1a65810a63` |
| member_count | 34 |
| package | `training_mode_001/graph6_confirmation_package_002/` |
| launch request | `training_mode_001/graph6_confirmation_launch_002/launch_request.json` (sha256 `9894741f9e7cf1ee39ae9753bbbc8ec2ce7badb087945579333c7eff982c7410`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6conf-20260910023000-a387d882` |
| launcher | `aws/graph_training_graph6_confirmation_launch.py` at commit `a387d882` |
| preregistration | `GRAPH6_CONFIRMATION_001.md` (unchanged) |

The packaged worker is byte-checked against `render_worker()`; the manifest
carries `launch_enabled: false`, learner seeds `[20260913, 20260914, 20260915]`,
panel seed `20260920`, `baseline_mode none`, `total_optimizer_steps 192`.

## The one-job request

ONE job, three independently initialized candidates, 64 updates each (192 total),
one pre-registered fresh 90-case panel measured before and after training with
answers sealed until the predictions are recorded, one new `$6.00` reservation
created exactly once, zero automatic retries, verified cleanup, original errors
preserved. Ledger today: revision 46, `$236.00` reserved / `$164.00` unreserved;
after this job's reservation: revision 47, `$242.00` / `$158.00` (cap `$400.00`).

Verdict rule (unchanged, pre-registered): fit = `mean(after_loss) <
mean(before_loss) − 0.02`; a candidate passes fresh transfer iff paired margin
≥ +0.10 **and** family-clustered 95 % bootstrap lower bound > 0 **and** absolute
fresh accuracy ≥ 0.50 **and** no operation regresses with ≥ 2 operations gaining
≥ +0.10; `FRESH_TRANSFER_CONFIRMED` iff ≥ 2 of 3 candidates pass. All three
candidates are reported either way.

## What I need from you

**GO / NO-GO** for this replacement job (one new owner-signed record + one new
`$6.00` reservation). The two earlier defaults hold unless you say otherwise:
baseline row **A** (report the missing run-005 checkpoint as `UNAVAILABLE`) and
the pre-registered transfer rule as written. On GO I mint the owner record
binding these exact identities, register, and execute — nothing before.
