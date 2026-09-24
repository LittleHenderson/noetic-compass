# E1b: the sealed HSET-2 TEST readout (readout plan item 10) — job limits

Label: `CLAUDE_BUILT_CLAUDE_CHECKED`; `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT`. **Built, not launched.** Nothing in
this folder has run on AWS. No model has been read. No sealed file has been opened.

## What it does, in one paragraph

It reads the six trained `final.pt` files (three repaired, switch ON; three unchanged, switch OFF) on the sealed
HSET-2 TEST questions, once. It grades every answer with checker v2. It then prints every registered label: the one
confirmatory claim `REPAIR_IMPROVES_ANALOGY_6`, every base claim per arm, every seed-pair comparison, every cell, both
analogy distractor halves, and every no-regression gate (H1, H2, V). Only counts, p-values and labels are public.
Per-item answers go to the archive only.

## The machine and the money

| Item | Value |
|---|---|
| Machine | ONE `g4dn.2xlarge` (1 NVIDIA T4, 8 vCPU, 32 GiB), `us-west-2`, on-demand $0.752/h |
| Image | `ami-07d69ce07bfe5628f` (the T4 reference image of P1a); no substitute |
| Disk | 100 GB gp3, deleted with the machine |
| Timers | in-machine 120 min; OS power-off 123 min; client deadline 130 min (`watch.py` terminates) |
| Readout budget | `e1b_machine.py --wall-seconds 5700` (95 min) for stages 0-4 |
| Worst case | (0.752 + 0.005 address + 100 x 0.08 / 730 disk) x 130/60 = **$1.6639** |
| Cap | **$2.00 + $0.10 allowance = $2.10** in the ledger (plan item 10) |
| Expected | about 1 h with 6 worker processes: about $0.77 + $0.10 (an estimate, not measured) |
| Retries | none: one launch attempt, one zone; `launch_record.json` refuses a second |
| GPU quota | the launcher refuses if ANY GPU machine is running (`g7.*` is in its list; training uses g7.2xlarge) |

Rule before launch (plan "money"): measured spend S + $2.10 must be at most $60.00.

## Stages (each stops the job by name)

0. **Custody manifest check** (design s8, `custody_manifest.py`). Every world touched by any update, development
   evaluation, DEV reading, probe or smoke input, and every larger-question fixture, is checked against the whole
   forbidden set (TEST_NEW_6, WITHHELD_6, TEST_NEW_5, WITHHELD_5) by two isomorphism methods (the D-1 oracle's M1
   canonical form and M2 refinement plus enumeration). Any match, any disagreement between the methods, any
   undeclared kind or unreadable world-like object stops the job: `CUSTODY_STOP`, exit 3. Public: counts only.
1. **Rebuild the sealed packets** with the builder's own `build_packet`; each must equal the sealed build's recorded
   packet sha256 and record id (`PACKET_REBUILD_MISMATCH`, exit 6).
2. **Timing preflight** on PUBLIC DEV packets with a FRESH switch-ON container (no TEST packet, no trained weight).
   Projected total over the budget: `PREFLIGHT_OVER_WALL_LIMIT`, exit 5, before any TEST forward pass.
3. **Predictions**: both presentations of every claim-cell item, through the accepted route (`predict_packet` at
   `e05889ee`), graded by checker v2 (`larger_question_scope.grade`), in 6 worker processes on the one T4. Any
   exception on an item makes that run's reading INVALID (a fault is not a model difference, Codex R3-B).
4. **Scoring** (`e1b_scorer.py`): the builder's own `evaluate_cell_views` and `paired_views` (A2.2 views), the s7.2
   regression test on every V cell, the H1/H2 documents from the wave-1 reader (`../h1h2/h1h2_paired.py`), and every
   label.

## Reading rules (prereg A5.1, A5.3, A5.5; plan item 10)

- A repaired run is read only if the matched-start reading says `MATCHED_START_REPRODUCED` (A5.5). Otherwise it is
  not read at all, and nothing repaired is placed beside Helm 2.0 (H1/H2 counts are withheld too).
- A repaired run's analogy items are predicted only if the ITEM2 reading (probe v0.3) says mechanism gate `CLEARED`,
  `ITEM2_PASS`, bound to these three `final.pt` files (A5.1). Otherwise: `NOT_READ_MECHANISM_GATE_OPEN`, and the
  confirmatory claim reads `MECHANISM_GATE_OPEN` (Q-J default: only the non-analogy H1/H2 view, exploratory).
- A historical Helm 2.0 control (seeds 20260918, 20260919) is read only if the U17 reproduction reading says
  `STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED` (option C). The launcher refuses anything else: the plan says stop and
  ask the owner.
- TEST is read once per registered run. A run that is not read stays unread.
- `INFERENCE_ASSUMPTIONS_UNSUPPORTED` is printed until a committed ruling record (`claude.e1b-inference-ruling/0.1`,
  `ruling: SUPPORTED`) exists (Q-D default).

## Labels and status words

- `REPAIR_IMPROVES_ANALOGY_6`: `PASS` (with the A2.3 caption, word for word) or `FAIL`, unless a status word applies,
  in this fixed order: `NOT_TESTABLE`, `MECHANISM_GATE_OPEN`, `COMPARISON_INCOMPLETE`,
  `INFERENCE_ASSUMPTIONS_UNSUPPORTED`. Every word that applies is listed with every reason. The inferential p is the
  largest degree-group or component p over every required comparison (never 0.01 ** 3).
- Base claims, `REPAIR_BEATS_UNCHANGED_<cell>`, `CELL_RESULT`, `ANALOGY_6_DISTRACTOR_HALF`:
  `EXPLORATORY_NOMINAL_PASS`, `EXPLORATORY_NO_NOMINAL_PASS`, `NOT_TESTABLE`, `COMPARISON_INCOMPLETE`,
  `NOT_READ_MECHANISM_GATE_OPEN`.
- `NO_REGRESSION_CHECK` (H1, H2, V:<cell>, per seed pair): `NO_REGRESSION_DETECTED` (caption "no regression detected by
  the listed paired tests"), `REGRESSION_DETECTED`, `LEFT_OUT_CANNOT_CARRY_A_CLAIM`, `NOT_READ_MECHANISM_GATE_OPEN`,
  `COMPARISON_INCOMPLETE`. Never "no ability lost", "preserved performance" or "noninferior".

## Custody

- The sealed P2 tarball never enters git or the bundle. The coordinator gives its private-bucket key and sha256 at
  launch; the machine fetches it by its own time-limited link, checks the sha256, extracts one file, and deletes the
  input from its disk before uploading anything.
- Public output (`results/`): counts, p-values, accuracies, labels, and digests of code and public input records only.
  Never an item id, record id, cluster id, class key, answer, per-item flag, or the digest of any sealed file.
- Sealed output (per-item answers and correctness, per-cluster tables, stage-0 matches, error messages, the readout's
  stderr) goes to `D:/tksCAS-archive/e1b_sealed_<date>/run_<stamp>/` only. `watch.py` refuses a git work tree and
  refuses to overwrite.
- The launch record keeps the sealed input's S3 key; its sha256 is written to the archive run folder only.

## What must exist before a launch (all committed; one file `E1B_INPUTS.json`, schema `claude.e1b-inputs/0.1`)

Each input is named as `{"commit": ..., "path": <package-relative path>, "sha256": <raw sha256>}`:

```json
{"schema": "claude.e1b-inputs/0.1",
 "hset2_build_commit": "<the commit P2 ran>",
 "build_summary": {...}, "public_cells": {...},
 "runs": [{"run_id": "R17", "arm": "repaired", "seed": 20260917, "provenance": "fresh_repaired", "switch": true,
           "commit": "...", "path": ".../final.pt", "sha256": "..."}, ... six rows: R17 R18 R19 U17 H18 H19 ...],
 "item2_reading": {...}, "matched_start": {...}, "reproduction_reading": {...}, "inference_ruling": {...} or null,
 "h1h2": {"20260917": {...}, "20260918": {...}, "20260919": {...}},
 "touched": {"updates": [{...}], "development_evaluation": [{...}], "dev_reading": "NONE:<reason>",
             "probe": [{...}], "smoke": [{...}], "fixture": [{...}]}}
```

It is written after training, E1a, P2, the U17 verdict and the H1/H2 readings. Until then a dry run refuses with
`INPUTS_NOT_YET_WRITTEN` (no AWS call).

    python -B launch.py --dry-run                                              # builds the bundle; no AWS call
    python -B launch.py --sealed-s3-key KEY --sealed-sha256 HEX                # the coordinator only
    python -B watch.py                                                         # the coordinator only

## What was checked, and how (laptop, no torch, 2026-09-24)

`test_e1b.py`, 14 tests, one process (one test starts a two-worker pure-Python pool); 14 passed in 14.73 s
(`TEST_RUN_20260924.txt`). The acceptance check: an
end-to-end run on a THROWAWAY public salt with tiny packets and stand-in predictions, in five scenarios (all clear;
gate open with no ruling; controls not admitted; matched start failed; a planted regression), prints every
registered label every time, covers every status word across the scenarios, and publishes no digest covering an
answer (every hex string in the public file and the log must be a digest of a known non-answer input, and no item
id, answer, class key or sealed-file digest may appear). `job.sh.template` passes `bash -n`, raw and rendered with
five 2,048-byte links under the 16,000-byte user-data limit. The real route engine (`RouteEngine`, torch) and the
launcher's AWS path have NOT run anywhere; their first run is on AWS.

## Known limits (recorded, not blocking)

- The preflight's parallel speed-up (0.75 per extra process) is an assumption; the real per-packet time on a
  trained container with 6 processes is not measured. If the preflight refuses, the plan's fallback is to split E1b
  by cell (a later build).
- Only claim-cell clusters are predicted (reach: PRIMARY clusters). Parts, edge-account and reach tie strata are not
  read here.
- H1/H2 counts come from documents computed beforehand by `h1h2_paired.py` (registered view only after ITEM2_PASS
  and the matched start); this job does not re-derive them.
