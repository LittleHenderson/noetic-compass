# GRAPH6_CURRICULUM_002 — attempt 004 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.**

## The honest ledger

| Attempt | Spent | Where it died | Defect |
| --- | --- | --- | --- |
| confirmation 001 | `$6.00` | first candidate's before-loss pass | learner-init seed passed where the dataset seed was required |
| curriculum 001 | `$7.00` | first checkpoint reload | payload embedded `TorchVersion`, refused under `weights_only=True`; `collect()` demanded artifacts from a failed worker |
| curriculum 002 | `$7.00` | first learner's before-loss pass | every learner indexed by the frozen lessons instead of its own condition's |
| curriculum 003 | `$7.00` | **after the experiment finished** | inner runner imported boto3 (absent from the training venv); the failure report then overwrote the completed result |

**`$27.00` spent, no retained measurement.** All four were defects in my new code;
none involved the frozen machinery, and cleanup completed every time.

## What attempt 003 changed — and why this is different

Attempt 003's traceback is at line 33 of the inner runner, **after**
`curriculum_experiment.launch(...)` returned: the six learners (three paired seeds
× control/varied), the 1,536 updates, the 64- and 256-update checkpoints, the
in-job reload verifications and the verdict were all produced. The experiment
cleared every defect that killed attempts 001 and 002. What remained was pure
packaging, and it has two fixes with tests behind them:

1. **Uploads moved to the OUTER worker** (system python, which has the AWS SDK).
   The inner runner only *stages* checkpoints plus a manifest under
   `results/artifacts/` and never imports boto3. Verified by executing the packed
   worker locally: its executable lines contain no boto3 reference.
2. **`result.json` is uploaded LAST** — after the manifest and every artifact — so
   the launcher's poll for it now means "everything is already in S3".
3. **A completed result can no longer be destroyed**: on any failure the outer
   worker preserves an existing result as `result_partial.json` (+ sidecar) and
   writes `failure.json` beside it instead of overwriting, and the launcher
   collects both.

Four new tests pin the staging, the upload ordering, the preservation branch and
collection tolerance. **253 graph tests pass**, including a test that executes the
rendered worker's inner runner end-to-end against stubs.

## Frozen design (unchanged)

Frozen candidate, encoder, tokenizer fitting set, CAS framing, `operation:^6`
scope; control = the existing 30 lessons, varied = the 30 new relationship lessons
(with `none` offered in 7 shared-part lessons: correct in 4, an incorrect
distractor in 3); three paired seeds `20260913/14/15` with matched initial weights
and separate optimizers; balanced schedule identical in both conditions;
checkpoints at 64 and 256; **6 learners / 1,536 updates**; the untouched final
panel (30 pairwise non-isomorphic arrangements, 90 cases, reach 10/10/10, teaching
envelope and vocabulary only — equal difficulty not claimed); real checkpoint
files reloaded and verified in-job; and the pre-registered rules with thresholds
unchanged (`VARIED_CURRICULUM_BETTER` iff ≥ 2 of 3 seeds show varied−control
≥ +0.10 with family-clustered 95 % CI low > 0 **and** ≥ 2 reach 0.50 absolute).

## Exact package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `0ecdd342218b3f54664e570667d96753c64fdd14` |
| archive_sha256 | `0f36a772103532583f9b8b88089b65c4f6ade466be40817559f259fb494d27c6` |
| archive_bytes | 410024 |
| manifest_sha256 | `d15f775e9ec29d4b12b0107c07da77614336a1f8739f90d81b9f95089c7ef30d` |
| member_count | 37 |
| package | `training_mode_001/graph6_curriculum_package_004/` |
| launch request | `training_mode_001/graph6_curriculum_launch_004/launch_request.json` (sha256 `31fbc0bc85911c4abcaab60b1d2317007f6742bf59a6734fadf830cbb760b157`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6curr-20260910113000-0ecdd342` |
| launcher | `aws/graph_training_curriculum_launch.py` at commit `0ecdd342` |

## Budget

| Item | Value |
| --- | --- |
| Instance | 1 × `g7.2xlarge` (RTX PRO 4500), no T4 fallback |
| Wall ceiling | 900 s per learner, 3,600 s worker, 7,200 s instance (2 h) |
| Reservation | one new **`$7.00`** |
| Ledger after | revision 50 → 51: `$270.00` reserved / `$130.00` unreserved (cap `$400.00`) |
| Retries | zero; original errors preserved; verified cleanup; artifacts collected first |

## What I need from you

**GO / NO-GO** for this replacement job (one new owner-signed record + one new
`$7.00` reservation). The specific, non-hopeful reason for confidence: attempt 003
proved the experiment completes end-to-end; the only remaining failure was the
upload path, which is now the outer worker's job, pinned by tests and verified by
executing the packed worker locally. If you would rather stop spending on this
job, the honest alternative is to record the four failures and return to the
design without another run.
