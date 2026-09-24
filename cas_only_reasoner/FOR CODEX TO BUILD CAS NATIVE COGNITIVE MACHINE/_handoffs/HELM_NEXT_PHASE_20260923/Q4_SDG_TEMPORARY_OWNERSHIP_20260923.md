# Q4-SDG-1: temporary ownership record (2026-09-23), written before any Q4 code

## Authority

- **The owner's attached directive.** `Q4_SDG_AND_TARGETED_FEEDBACK_DIRECTIVE_20260923.md`, sha256
  `b2092d01ad0a6cbde6a5e3005345c691af5fcfeffac96ff7f7ad324daa8c4056`. A byte copy is on
  `research/helm-integration-20260923` at `8eb798a5`. The owner-pasted rationale is at `e1728a59`.
- **The directive's words on roles** (section 10): "Claude may continue the selected Q4 implementation while Codex is
  unavailable, after recording temporary ownership and checking current branch activity."
- **This file is that record.**

## Identity and separation

| Item | Value |
|---|---|
| Experiment id | **Q4-SDG-1**. Separate from Q4-RECON-2 (Codex's registered Q4 line), from Helm and from the late-reach experiment. Never pooled with any of them |
| Branch and working copy | `claude/q4-sdg-feedback-20260923` in `D:/tksCAS-worktrees/q4-sdg`, parent `96644503` (Codex's newest; the Q4 model, training and data code is byte-identical to the executed source `d4c3fc76`) |
| Runner | the Claude coordinator (this session) |
| Builder | a separate Claude sub-agent working only in the Q4 working copy |
| Reviewer | a fresh Claude sub-agent |
| On return | Codex reviews the bounded change set. It is not merged automatically |
| Label | every result is `CLAUDE_BUILT_CLAUDE_CHECKED` until an independent review |

## What is preserved, untouched

- The Q3 v0.7 data and adapter: `q3_behaviour_records.py`, `q3_load.py`, `Q3_DATA_PINS.json` and the manifest. The
  historical plan pins them, and any edit is `PLAN_DRIFT`.
- The 12 pinned Q4 runtime files, including `q4_smoke_job.py`, `learner_q4_neural.py` and `learner_q4_decoder.py`.
- Codex's `q4_panel_evaluation.py`.
- The original run `records/q4_authorized_20260922/run_001`:
  - executed source `d4c3fc76`;
  - plan sha256 `9dacc836...`;
  - checkpoint `model_state.pt`, sha256 `d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477`, git blob
    `f28cf18c`.
- New work goes in new files with new identities. The proposed names are `q4_sdg_curriculum.py`,
  `test_q4_sdg_curriculum.py`, a new error-panel module and a new runner.

## Protected examination (custody)

- **What is protected.** Q3 v0.7 family-G evaluation, depths 4 and 5: `data/q3_v0_7/visible_G_eval.jsonl` and
  `sealed_G_eval.jsonl`.
- **How it is kept out.** The Q4 working copy excludes every `*_eval.jsonl` and every `*sealed*` file: checked
  0 and 0 present. The builder and reviewer are told not to read them through git either.
- **How it may be used.** Only once, for an arm registered in advance, and only with the owner's approval. Never in
  any feedback loop.
- **Development only.** The old 16 dev rows, inspected many times, are development diagnostics.
- **Generated training.** It uses only depth-3-or-less bare shapes from the 16 G-train keys, plus the single state.
  It never uses the 9 G-dev keys, and never depth 4 or more. That rules out every eval shape without opening the eval
  files.

## Evidence reused, not recomputed

Section 3 of the directive asks six first-step questions. Their status from recovery:

| # | Question | Status |
|---|---|---|
| 1 | input, target, output and first wrong decision | **answered from retained files, $0** |
| 2 | kind of first error | **answered, $0.** 10/16 leaf-versus-branch at position 2 (chose STATE where BINARY belonged); 5/16 wrong Noetic at position 3; 1/16 PLUS instead of TIMES at position 1. Caveat: the output is one fixed tree, so this split mostly describes how the targets differ from that tree |
| 5 | summary swap | **answered in substance, for the original checkpoint.** The final input summary is nearly constant: minimum cosine 0.9911303112245342 over 272 inputs. Swapping summaries changes the probed choices by at most 0.013814, and changes 0 of 16 decodes |
| 3 | teacher-forced versus free-generation accuracy | **needs a new run** (forward only) |
| 4 | the effect of a one-field input change | **needs a new run** |
| 6 | gradients and weight change per module | **needs a new run** (backward, no optimizer step) |

The why-review diagnostics RT1, RT2 and RT7 (`26f1b465`, `records/helm_why_review_20260922/`) are reused and not
re-run.

## Compute and money

- **AWS GPU only.** The Q4 model code fails closed without CUDA, and the rule "Never CPU for model inference" has
  no "local" qualifier. The laptop runs nothing neural.
- **This supersedes one earlier line.** The AWS order of 2026-09-23 replaces `EVALUATION_DESIGN.md:27`
  ("no GPU/cloud/API") for Q4-SDG-1 jobs.
- **The diagnostic job** (questions 3, 4 and 6, with no optimizer step):
  - one g4dn.xlarge T4;
  - a timer of 45 minutes on the machine and a 55-minute client deadline;
  - **ceiling $1.00**, a test or validation job of precedent size under the standing authorization;
  - it runs only when no other GPU machine is running (the account's GPU quota is 8 vCPU).
- **The A-versus-B training comparison is not approved yet.** The owner has named no amount for Q4 training. It
  needs one short owner answer on a dollar ceiling before launch.

## Order of work

1. This record.
2. Builder:
   - the Q4 lesson adapter (families A to D), its tests, its data identity and its exclusion proofs, all
     non-neural;
   - a Linux AWS runner for the diagnostic and for the later A/B jobs.
3. Fresh review.
4. The diagnostic job.
5. The owner's answer on a training ceiling, then the A-versus-B job with a declared practice budget, frozen before
   launch.
6. B versus C only if the error report supports it.
