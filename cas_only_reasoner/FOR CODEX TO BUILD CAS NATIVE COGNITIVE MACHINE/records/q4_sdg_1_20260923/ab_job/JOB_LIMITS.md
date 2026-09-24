# Q4-SDG-1 A-versus-B training job: job limits (written before launch)

Label: `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover). Runner: the Claude coordinator. Not launched.
Rules: `research/helm_cas_expression_lab/q4_ab_rules.py`; spec `Q4_SDG_AB_SPEC_v0_2.md` (must say FROZEN_BEFORE_LAUNCH).

## What it does

- **Purpose.** The owner's decided next step (OWNER_AUTHORITY_AND_DECISIONS_20260924.md): keep Q4's architecture;
  compare A (family-G teaching) with B (CAS SDG lessons, families A-C); 3 seeds per arm; measure input use at fixed
  checkpoints; a frozen rule decides whether an architecture change is justified.
- **Stages on the machine:**
  - A (no torch): `q4_ab_prep.py measure` must reproduce every frozen panel digest, with the Python engine. Stop otherwise.
  - B (no torch): `pytest test_q4_ab.py`. Recorded; not a stop.
  - C: `q4_ab_train.py run` with its own limit of 11,400 s (190 min): pin check, GPU gates, Stage 0 (the diagnostic's
    16 decodes and update 1 must reproduce here first), the B rebuild (must equal the pin), `prep.json`, the smoke stage
    and time projection, then A1 B1 A2 B2 A3 B3 with a fresh-process reload check after each run.
  - D (no torch): `read_q4_ab_results.py` on the machine. The coordinator re-runs it on the downloaded files; that
    local reading is the one reported.

## Pre-launch refusals (launch.py, at the source commit)

- The spec does not say `FROZEN_BEFORE_LAUNCH`; any frozen digest is not filled in; the runner's wall limit differs.
- `Q4_SDG_DATA_PINS.json` has no pin for the frozen package (engine `python`, size 4096, seeds 20260941 and 20260951).
- `data_build_job/watch_record.json` is missing, or its measured cost plus this job's worst case exceeds $5.00.
- A GPU machine is running; this folder already has a `launch_record.json`; the run_001 weights differ from `d54f5715`.

## Machine, time and money

| Item | Value |
|---|---|
| Machine | one `g4dn.xlarge` (NVIDIA T4), us-west-2, $0.526 per hour; 100 GB gp3 disk, deleted on termination |
| Image | pinned `ami-07d69ce07bfe5628f` (the T4 jobs of 2026-09-23/24); a substitute is recorded if it is retired |
| Timers | runner 190 min; in-machine timer 225 min; shutdown at 228 min; the watcher terminates it at 240 min |
| Per run | `RUN_WALL_SECONDS` 3,000 s; the smoke projection (x 1.25) must fit both the run and the job limit |
| **Worst case** | (0.526 + 0.005 public address + 100 x 0.08 / 730 disk) x 240 / 60 = **$2.1678** |
| **Ceiling** | **$5.00 for the whole A-versus-B job**, the data build included |
| Ceiling arithmetic | measured data-build cost bound (from its watch record; worst case $0.0813) + $2.1678 <= $5.00. Worst total $2.2491 |
| Concurrency | refuses while any GPU machine is running (account GPU quota 8 vCPU; one GPU job at a time) |
| Retries | none; a failure is recorded, uploaded and reported |

**Runtime estimate** (from the measured diagnostic, 26.7 s on a T4 for about 14,200 decoder calls, 2,000 encoder calls
and 385 backward passes, so at most about 1.6 ms per decoder call; the training-update cost is an ASSUMPTION of about
5 ms until the smoke stage measures it):

| Part | Typical | Upper (before the projection stop) |
|---|---|---|
| Setup (uv, Python, torch) | 7 min | 10 min |
| Panels, Stage 0, B rebuild, prep | 4 min | 8 min |
| Smoke (3 x 64 updates, thinned panels) | 2 min | 4 min |
| Evaluation per checkpoint (832 decodes, 832 teacher-forced passes, 773 edits) | 41 s | 90 s |
| Training per run (32,768 updates) | 2.7 min | 8.2 min (15 ms per update) |
| Per run (7 checkpoints + reload check) | 8 min | 20 min |
| Six runs | 48 min | 120 min |
| **Total machine time** | **about 61 min, about $0.55** | **about 142 min, about $1.28** |

## Custody

- Bundle from git objects: the lab's top-level `.py`/`.json`, the spec, the pinned compiler, the public Q3 v0.7 data
  (manifest, baselines, `visible_*.jsonl`), and `records/q4_authorized_20260922/run_001/`.
- Never bundled: `*_eval.jsonl`, names containing `sealed`, `hset1a`, `hset1b`. Checked twice in the launcher, on the
  machine after unpacking, and on the way out (no such name leaves the machine).
- The runner opens no eval or sealed file. Every target is recompiled from visible text. The B rebuild writes its own
  sidecars on the machine; the runner never reads them.
- The protected examination (Q3 G eval, depths 4-5) is not in the bundle and is in no loop.

## Download (watch.py)

- Nested result folders (`out/ab/runs/<run>/checkpoint/model_state.pt`) are unpacked file by file: regular files only,
  under `out/`, at most 6 simple-name parts, no `..`, no absolute path, no link, no eval/sealed/hset name, 100 MB per
  file and 1 GB in total; every target path is checked to stay inside `results/`. Never `extractall`.
- The watch record adds this machine's cost bound to the data build's: `whole_ab_job_cost_upper_bound_usd`.

## Cleanup

- The machine terminates itself on shutdown. The watcher confirms `terminated` and that no volume of this job remains.
- S3: bundle, results and progress stay under `q4-sdg-1/ab-<stamp>/` in `cas-harness-runpod-92754088`. Deleting them
  is the owner's call.
