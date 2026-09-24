# Q4-SDG-1 error-panel diagnostic: job limits (written before launch)

Label: `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover, 2026-09-23). Runner: the Claude coordinator.

## What it does

- **Purpose.** Directive section 3, questions 3, 4, 5 (refined) and 6. They are measured on the ORIGINAL Q4 checkpoint
  (`records/q4_authorized_20260922/run_001`, weights sha256 `d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477`).
  - Forward and backward passes only.
  - No optimizer is created, and no weight is written.
  - The checkpoint's sha256 is checked before and after.
- **Program.** `research/helm_cas_expression_lab/q4_error_panel.py` at the reviewed source commit given to
  `launch.py --source-commit`.
- **Stages on the machine:**
  - A: panel selection, with no torch. It must reproduce digest `0b98bfc9...`, or the job stops.
  - B: the builder's torch-free tests, on Linux, without the optional Rust engine. Recorded; not a stop.
  - C: the diagnostic, with its own 1,800-second limit.

## Machine, time and money

| Item | Value |
|---|---|
| Machine | one `g4dn.xlarge` (NVIDIA T4), us-west-2, $0.526 per hour; 100 GB gp3 disk, deleted on termination |
| Image | pinned `ami-07d69ce07bfe5628f` (the T4 jobs of 2026-09-23); a substitute is recorded if it is retired |
| Timers | machine: shutdown at 48 minutes plus an in-machine timer at 45 minutes; the watcher terminates it at 55 minutes |
| Worst case | $0.50 at the 55-minute client deadline (machine, public address and disk) |
| **Ceiling** | **$1.00**, as written in `Q4_SDG_TEMPORARY_OWNERSHIP_20260923.md` (`0687e20a`) before any Q4 code |
| Concurrency | refuses to launch while any GPU machine is running (account GPU quota 8 vCPU) |
| Retries | none; a failure is recorded and reported |

## Custody

- **What the bundle holds.** It is built from git objects: the lab's top-level code, the pinned compiler, the
  public Q3 v0.7 data (manifest, baselines, `visible_*.jsonl`) and the original run's records.
- **What it never holds.** Any `*_eval.jsonl` or `*sealed*` path. This is checked by name in the launcher, twice,
  and again on the machine.
- **How targets are made.** The panel recompiles targets from the visible text.

**Engine parity, measured on the laptop (2026-09-24, pure Python, no model).** Every visible Q3 v0.7 text row was
compiled with the optional Rust engine and with the pure-Python engine:
- 6,893 rows: C, G and R, train and dev;
- 2,469 non-text rows (A) skipped.

Validity and the lab-spelled tree were identical on all 6,893 rows. The machine has no Rust engine, so its targets
equal the laptop's.

## Cleanup

- **Shutdown.** The machine terminates itself on shutdown. The watcher confirms `terminated` and checks that no
  volume tagged with the job's name remains.
- **S3.** Bundle, results and progress objects stay under `q4-sdg-1/error-panel-<stamp>/` in
  `cas-harness-runpod-92754088`. Deleting them is the owner's call.
