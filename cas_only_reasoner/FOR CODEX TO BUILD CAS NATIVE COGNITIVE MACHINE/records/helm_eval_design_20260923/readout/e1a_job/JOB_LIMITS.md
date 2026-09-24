# AWS job E1a: checks before any results (readout plan item 9)

**Status: BUILT and dry-run on the laptop only. NOT launched. NOT reviewed.**
Labels: `CLAUDE_BUILT_CLAUDE_CHECKED`; `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT`.

## What it answers

E1a unlocks, or keeps locked, every repaired-arm number. It reads no TEST data and prints no analogy number.

1. **Route receipt.** Can the trained models be read through the accepted larger-question route (`e05889ee`)?
   It loads 7 checkpoints: the switch-ON smoke `final.pt`, the three repaired finals (switch ON), U17's final and
   Helm 2.0's finals for seeds 20260918 and 20260919 (switch OFF). The switch is read back and asserted. The 37
   public gradable fixtures must go read → forward → decode → grade with no error. The 4 refusal fixtures must refuse
   before any forward pass. No right/wrong, answer digest or check digest is written.
2. **Probe v0.3 validation** on the real harness (prereg v0.3 section 6: a fresh container, seed 20260917, switch
   OFF).
3. **The 18 probe reads and ITEM2.** 3 repaired seeds × `pass_01`, `main_checkpoint_0294/0588/0882/1176`, `final`.
   They start **only** if stage 2 re-derives as `VALIDATION_PASS` from its raw tables with the frozen metric.
   Otherwise the job writes `READS_NOT_STARTED.json` and the reads never start. The checkpoint hashes and update
   counts in `ITEM2_INPUTS.json` come from each receipt's inventory, through the roster checker. They never come from
   the harness.
4. **Matched start (A5.5).** First the real-file self-test. The reading runs only after `MATCHED_START_SELF_TEST:PASS`.
5. **Checkpoint roster** on each repaired receipt.

Stages 1, 2 and 4+5 run side by side. Stage 3 waits for all of them.

## Authority (recorded, not invented)

- The owner's standing project approval, extended to Claude as runner (2026-09-24,
  `_handoffs/HELM_NEXT_PHASE_20260923/OWNER_STANDING_AUTHORIZATION_CLAUDE_20260924.md`, commit `ca68690b`).
- The owner's AWS order of 2026-09-23 ("use aws as there is only 354 mb of 16 gbs locally").
- Readout plan item 9: E1a on a T4, cap $2.00 + $0.10, after U17.
- **Execution admission: NOT_READY.** The builder does not launch. The coordinator launches only after the one Codex
  check, with a committed probe v0.3 acceptance record. The money rule is: measured spend S + $2.10 <= $60.00.

## Limits

| Limit | Value |
|---|---|
| Machine | ONE `g4dn.2xlarge`: NVIDIA T4, 8 vCPU, 32 GiB, us-west-2, on-demand, $0.752/hour |
| Image | pinned `ami-07d69ce07bfe5628f` (the P1a and analogy-T4 image). No substitute: a real launch refuses if it is gone |
| One GPU machine at a time | refuses if any `g4dn.*`, `g4ad.*`, `g5.*`, `g5g.*`, `g6.*`, `g6e.*`, `g6f.*`, `gr6.*`, `g7.*`, `g7e.*`, `p3.*`, `p3dn.*`, `p4d.*`, `p4de.*`, `p5.*`, `p5e.*` or `p5en.*` machine is pending, running or stopping |
| Instance line | the machine reads its own id through IMDSv2 and writes `instance_id=<id>` into `env.txt`; it stops if it cannot. The launch asks for IMDSv2 only (`HttpTokens: required`) |
| Software | uv 0.12.17, Python 3.14.7, torch 2.11.0 from the cu128 index (must report `2.11.0+cu128`), numpy 2.5.2, both wheels from the bundle with `--no-deps` |
| Environment | `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, `CAS_META2_RUN_TEACHING_CYCLE=1`, `PYTHONDONTWRITEBYTECODE=1` |
| Timing preflight | after setup, it times real probe calls and fixture calls. It projects the whole job against a 110-minute budget, with a 1.15 margin and 2 of 3 processes assumed to run at full speed. It also checks that no harness process would pass its own 3,600 s wall. If not: `PREFLIGHT_OVER_WALL_LIMIT`, and nothing else runs |
| Wall limits | in-machine timer 120 minutes; OS power-off 123 minutes; client deadline 130 minutes (`watch.py` terminates the machine). Each probe process keeps its own 3,600 s wall and its 80 C stop |
| Worst case | (0.752 + 0.005 public address + 100 GB × 0.08 / 730 disk) = 0.767959 USD/hour × 130/60 hours = **$1.6639** |
| Cap | **$2.00 + $0.10 allowance**. The launcher refuses if the worst case is over $2.00 |
| Expected | readout plan estimate, NOT measured: 60-75 minutes, about $0.77-$0.96 |
| Retries | none. One launch attempt, one zone. `launch_record.json` refuses a second |
| Credentials on the machine | none. Time-limited links only: one download (the bundle) and two uploads (results, progress log) |
| Work | forward passes only, under `no_grad`. No optimizer step, no checkpoint written |
| Cleanup evidence | `watch.py` confirms "terminated" and lists any volume still tagged with the job's name |

## Custody

- The bundle is built from **git objects only** and streamed to a new folder outside every git tree.
- Every data file, checkpoint and readout program is checked against a pin. Every receipt file is bound to its
  receipt's `collected_inventory.json` (sha256 and bytes).
- Allowlist: the e05889ee source (`cncm/*.py`, `cas_meta2/**/*.py`, the route's `eval_paths` files and fixtures),
  the public course, tokenizer, development file, both wheels, Helm 2.0's three `initial.pt` and two finals, the
  smoke final, the six readout programs, and from each study receipt the checkpoints, sidecars, update rows,
  `worker_report.json`, the inventory and `reduced_schedule.json`.
- A second line refuses any bundle name with `sealed`, `_eval.jsonl`, `salt`, `private_target`, `protected`,
  `transcript`, `hset`, `tkscas-archive`, `test_new`, `_scoring.json` or `_predictions.json`. It also refuses any file
  of the evaluation-design tree other than the six pinned readout programs.
- `worker_report.json` travels because the roster reads its update totals. It holds score fields. No program on the
  machine reads or prints them.
- **Reading order (A5.1/A5.3/A5.5).** The returned score tables hold raw analogy-slot logits. Do not compute any
  accuracy from them. They exist so ITEM2 can be re-derived on the laptop (`item2_reader.py`, pure Python).

## Refusals before any spend

- A real launch refuses **before building anything** without all four study receipts: the three repaired receipts
  named by the frozen repaired study (`c0d65ce8`) at `--repaired-commit`, and U17's receipt named by the frozen
  unchanged study (`60140ae0`) at `--unchanged-commit` (`STUDY_RECEIPTS_MISSING`). A dry run builds what exists, runs
  the custody filters, prints the plan and then refuses the same way (exit 2).
- A real launch also refuses without a committed probe v0.3 acceptance record whose three hashes equal the pinned
  harness, metric and prereg (`ACCEPTANCE_RECORD_REQUIRED` / `ACCEPTANCE_RECORD_INVALID`).
- It also refuses when: a pin or inventory differs; a receipt file is missing from its inventory; the job files are
  not committed; a pinned commit is not on its pushed branch; the image is gone; a GPU machine is running; the
  default security group allows inbound traffic; the machine script is over 16,000 bytes; `launch_record.json`
  exists.

## Commands

    python -B launch.py --dry-run --repaired-commit SHA --unchanged-commit SHA      # laptop; no AWS call
    python -B launch.py --repaired-commit SHA --unchanged-commit SHA --acceptance-record PATH   # the coordinator
    python -B watch.py                                                               # the coordinator
    python -B read_results.py                                                        # laptop; JSON only

## Not in this job

- No analogy accuracy of either arm, no H1/H2 comparison, no HSET-2 or sealed material. Those belong to E1b.
- It does not decide `REPAIR_IMPROVES_ANALOGY_6`. It can only keep the mechanism gate open or let it close.
