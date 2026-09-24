# Q4-SDG-1 error-panel diagnostic: run log

Label: `CLAUDE_BUILT_CLAUDE_CHECKED`. Runner: the Claude coordinator (temporary takeover). Owner go-ahead for the
next Q4 run: 2026-09-24 (`OWNER_DIRECTION_20260924.md`, research branch `e782898f`).

## Run 1 (2026-09-24): done

**Where and what ran:**
- Machine `i-0bb026161de743f23`, g4dn.xlarge, Tesla T4, us-west-2a.
- Source `28acfa06`: builder revision 1; review `APPROVE_FOR_DIAGNOSTIC_JOB` at `a3567eb0`.
- Bundle 76 files, sha256 prefix `0f2696a4a9b8c0a2`.

**Time and money:**
- Launched 01:16:05Z; watch ended 01:23:31Z, 7.4 minutes.
- The diagnostic itself took 26.7 s.
- Upper bound $0.0673, against a $1.00 ceiling.
- Termination confirmed. No volume left.

**Exit codes:** stage A 0; stage B tests 1; stage C panel 0. The job's status: `done`.

**Checkpoint:** weights sha256 `d54f5715...` before and after the run. No optimizer was created.

**Archive:** `D:/tksCAS-archive/q4_sdg_1_error_panel_20260924/`, with sha256 list
`D:/tksCAS-archive/q4_sdg_1_error_panel_20260924.sha256`, checked three times.

**Stage B note: my bundling gap, not a code fault.**
- 37 passed and 1 failed. `test_q3_files_are_unchanged` reads `records/q4_authorized_20260922/plan.json`, and the
  launcher packed only `run_001/`.
- The panel's own plan check uses `run_001/plan.json`, and it passed.
- The same test passed on the laptop (review `a3567eb0`: 38 passed).

## Measured (program output, `results/panel/`)

**Stage 0: `REPRODUCED_16_OF_16`.** The T4 replays the 16 saved RTX 4070 predictions exactly. The rebuilt starting
weights reproduce update 1 exactly (`REINIT_REPRODUCES_UPDATE_1`): loss 3.5241360664367676, gradient norm
0.7250789210081344 against 0.7250789403915405 saved.

### Question 3: free generation versus the correct previous tokens (96 rows: old_dev16, teaching16, public64)

**Free generation:**
- 1 distinct output for all 96 inputs; 0 of 96 exact.
- First wrong decisions: LOST_BRANCH 64, WRONG_NOETIC 25, PLUS_FOR_TIMES 5, WRONG_DOMAIN 2.

**With the correct previous tokens (grammar-masked; plain argmax in brackets where it differs):**

| Slot | Correct | Of | Note |
|---|---|---|---|
| noetic | 36 | 453 | about 1 in 13; 10 choices, so chance is about 1 in 10 |
| domain | 118 | 453 | about 1 in 4; 4 choices |
| drive | 227 | 453 | about 1 in 2 |
| register | 214 | 453 | about 1 in 2 |
| op (PLUS or TIMES) | 254 | 357 | |
| expr (state or branch) | 549 (481) | 810 | |
| end of sequence | 96 (33) | 96 | |

### Question 4: one-field edits of the input, with the correct previous tokens held fixed

- 1,812 edits.
- The largest change in the probability of the edited field's new token, over all rows: noetic
  3.6378330280362192e-06, domain 3.5484508671690396e-06, drive 2.6277583939915417e-06, register
  2.324467688163967e-06.
- Every median is 0.0.

### Question 5 (refined): swapping in a partner's input summary, same bare shape and length (95 rows)

- The summary's cosine to its partner: min 0.9965840794023093, median 0.9997842858774879.
- Grammar-masked choices changed by the swap: 0 of 3,027 positions.
- Largest change in the correct token's probability: 0.006323997268072423.
- Same-example control: 0.0.

### Question 6: gradient size by model part, original loss, no step (mean over 96 rows)

| Part | Gradient norm |
|---|---|
| output head | 0.935616 |
| decoder | 0.403756 |
| output embedding | 0.032826 |
| encoder | 0.009038 |
| input embedding | 0.000567 |

**Weight change from the rebuilt start to the final checkpoint (relative):** output head 0.6385, decoder 0.5635,
encoder 0.3806, output embedding 0.0347, input embedding 0.0067.

## Reading (coordinator's words; not a program verdict)

- **The saved Q4 model does not use its input.**
  - Given the correct previous tokens, its field choices sit at chance or at the most common value.
  - Changing one field of the input moves the right token's probability by less than 0.000004.
  - Its summary of the input is almost the same for every input.
- **The learning signal barely reaches the input side.** The encoder's gradient is about 1/45 of the decoder's, and
  the input embedding's is about 1/700.
- **This supports the owner-pasted point** (`OWNER_PASTED_INTEGRATION_GUIDANCE_20260924.md`): information that never
  reaches the decision cannot be recovered by a larger penalty.
- **What this does NOT show.** The run had only 128 single-example updates. These numbers cannot tell apart two
  cases:
  - an input path that cannot carry the information;
  - an input path that has not yet learned to.
  A longer run, or an arm whose lessons force input use (families A to C), is what separates them. The choice of
  next arm, and whether an architecture change is justified, belongs to the owner.
