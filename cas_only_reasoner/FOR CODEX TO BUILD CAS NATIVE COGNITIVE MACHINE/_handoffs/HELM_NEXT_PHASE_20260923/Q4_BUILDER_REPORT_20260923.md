# Q4-SDG-1 builder report (2026-09-23)

**Builder:** a temporary Claude sub-agent, standing in for Codex. **Label:** `CLAUDE_BUILT_CLAUDE_CHECKED` until an
independent review. **Branch:** `claude/q4-sdg-feedback-20260923` (parent `96644503`, after the ownership record
`0687e20a`).

## In short

- I built the lesson adapter (non-neural) and its tests. They pass locally.
- I built the error-panel diagnostic (neural). It has **not** run. It is for an AWS T4 only.
- Nothing was trained. No model was run. No GPU was used. Nothing ran on AWS. No money was spent.
- No Q3 file, no pinned Q4 runtime file, and nothing in `records/q4_authorized_20260922/` was changed.

## Files added

All paths are under `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`.

| File | What it is |
|---|---|
| `research/helm_cas_expression_lab/q4_sdg_curriculum.py` | The lesson adapter: families A, B, C (a static package) and D (mistake-driven rounds), the one canonical surface, per-row compiler checks, `first_wrong_decision`, the loader, pinning, and the CLI |
| `research/helm_cas_expression_lab/test_q4_sdg_curriculum.py` | 24 pure-Python tests of the adapter |
| `research/helm_cas_expression_lab/Q4_SDG_DATA_PINS.json` | The new pin file. It is empty until the AWS build is verified and pinned |
| `research/helm_cas_expression_lab/Q4_SDG_LESSONS_SPEC_v0_1.md` | Sizes, mixture, practice budget and panels, all marked **PROPOSED** |
| `research/helm_cas_expression_lab/q4_error_panel.py` | The diagnostic for questions 3, 4, 5 (refined) and 6, on the original checkpoint. AWS T4 only |
| `research/helm_cas_expression_lab/test_q4_error_panel.py` | 9 torch-free tests of the diagnostic's non-neural parts |
| `_handoffs/HELM_NEXT_PHASE_20260923/Q4_BUILDER_REPORT_20260923.md` | This report |

## How the lesson adapter works

- **One text per tree.** A leaf is `^n^D`, then optional `_{Fk}`, then optional `|R`. A branch is always
  bracketed: `(a + b)` or `(a × b)`. A domain is always written. A register is only the tail `|R`.
  - Why: the pinned compiler reads `^8` as `^8^P`, and reads `^8|A^C` and `^8^C|A` as one tree. A test shows both.
- **Every row is checked, not trusted.**
  1. The constructor builds the intended tree.
  2. The text is rendered from that tree.
  3. The pinned compiler (LF `61ed5a45...`) compiles the text. The compile must be valid.
  4. The lab-spelled result must **equal** the intended tree. If it does not, the build stops.
  5. The codec must accept the tree. `UNSUPPORTED_OPERATION` is refused and counted, never simplified.
  6. Tokens must round-trip back to the tree.
  7. The bare shape must be allowed.
- **Stored per row, in the sealed sidecar only:** content sha256, the ordered operator-shape key, the ordered
  bare-shape key, the Q3 tree-shape key, the strict-shape key, depth, size, leaf count, the tokens, the slot kind
  and tree path of every position, the group id, the changed field, and provenance (compiler hash, engine,
  warnings, constructor).
- **The compiler engine.** It is recorded per row and in the manifest. Locally it was `rust+python`, because the
  optional Rust `cas_engine` is installed.
- **Shapes.**
  - Allowed: the single state, or one of the 16 G-train bare shapes. All are depth 3 or less.
  - Forbidden: the 9 G-dev bare shapes (including `(((L L) L) L)`, key `f5844b5735f0fe95`), and depth 4 or more.
  - The 16 and 9 keys are frozen constants. A test recomputes them from the visible train and dev files only.
- **Families.**
  - **A.** Single states, drawn so that each field's value counts stay close to equal (logged). One-field pairs
    rotate over noetic, domain, drive and register. A pair must differ in exactly one compiled token of that field.
  - **B.** Depth-1 trees with unequal leaves: left/right swap pairs, and PLUS/TIMES pairs. A pair is kept only
    when both members compile. Refusals are logged by reason.
  - **C.** Four subfamilies:
    - grouping: 3 leaves in 2 bracketings; 4 leaves in the 3 allowed bracketings;
    - operator-only pairs;
    - leaf-only pairs;
    - a mixed set that rotates evenly over all 16 allowed shapes.
  - **C exception.** A 3-leaf grouping pair with mixed operators is left out on purpose. Exactly one of its two
    bracketings can compile, because TIMES needs single-state operands. A test shows this.
  - **D.** `first_wrong_decision(pred, target)` returns the first wrong position, its slot kind (read from
    `allowed_next`), its tree path, and the mistake type. `build_d_round` turns triggers into fresh rows of that
    mistake type, plus controls.
    - Triggers may come only from the package's train rows or its feedback split.
    - A trigger from the package's dev split, from a Q3 dev row, or from an unknown row is refused.
- **Splits.** The package has three splits: `train`, `dev`, and `feedback`. Feedback is the new public panel,
  with its own seed.
  - A group gets its id before any split is made. A whole group goes to one split.
  - Each piece of content appears once in the whole package, so no text can cross splits.
- **Identity.** Schema `helm-cas-expression-lab.q4-sdg-lessons/0.1`. Seeds `20260941` (main) and `20260951`
  (feedback). Output `data/q4_sdg_v0_1/`: the build refuses a non-empty folder, and writes to `.partial`, then
  renames. Record id = first 24 hex of sha256 of `'<schema>:<seed>:<lesson>:<split>:<index>'`.

## How the error panel works (not run)

- **Stage 0.** Checks the checkpoint sha256 `d54f5715...` and the plan sha. Loads through
  `q4_checkpoint.load_checkpoint`. Replays the 16 saved dev predictions. If any differs, it writes
  `DEVICE_OR_SOURCE_MISMATCH.json` and stops.
- **Panels.**
  - `old_dev16`: the first 16 visible G dev rows.
  - `teaching16`: the first 16 rows the run consumed.
  - `public64`: 2 unconsumed train rows per G-train shape, plus 32 dev rows after the first 16, round-robin
    over the 9 dev shapes. Seed `20260971`.
  - Selection digest (measured locally): `0b98bfc94a5aed8af2d4fef72378fec7dfa9d46808b09ff30f750972387a3059`.
- **Q3.** Next-token accuracy with the correct previous tokens, per slot kind. Both plain and grammar-masked
  argmax, with the free-decoding tie-break. Shown next to free generation. Includes the choice at, before and
  after the first wrong decision. Also compares the step-by-step logits with the full teacher-forced pass.
- **Q4.** For every leaf and field, a one-field edit: the next value that compiles to exactly the edited tree.
  Measures the change in the encoder summary, and in the probability of the old and new field tokens, with the
  gold prefix fixed.
- **Q5.** Swaps the summary with a partner of the same bare shape (so the same token length). Includes a
  same-example re-encode control.
- **Q6.** Gradient norms per module group, from one backward pass of the original loss. Separate backward passes
  for the decision, field and operator positions. There is no optimizer and no step.
  - Weight change = the final weights minus a model rebuilt with seed `20260921`, in the smoke job's order.
  - The rebuild is checked against update 1 in `updates.jsonl`.
- **Fails closed** when: the device string is not `cuda:N` (before torch is imported); CUDA is missing; the GPU
  is busy (`q4_smoke_job._check_device_idle`, which runs on Linux); torch is not `2.11.0+cu128`; Python is not
  3.14; or the Q3 data folder holds any `*_eval.jsonl` or `sealed*` name.
- **Custody.** Targets are recompiled from the visible text. No sealed file is read.
- **Records.** The LF hashes of the source files are written into both `panel_manifest.json` and `result.json`.

## Tests and what each covers

**`test_q4_sdg_curriculum.py` (24 tests)**
- Exclusion: the 16/9 keys are recomputed from the visible train and dev files. Every row has an allowed shape
  and depth of 3 or less. The two held-out 4-leaf bracketings are dev shapes.
- Dev: no generated text equals any visible Q3 dev text (families G, R and C).
- Q3 frozen: the LF hashes of `q3_behaviour_records.py` (`5b3e03cd...`), `q3_load.py` (`534f486a...`) and
  `Q3_DATA_PINS.json` (`e67fb880...`) equal the values in `records/q4_authorized_20260922/plan.json`. All 12 runtime
  pins match. The Q3 v0.7 manifest is the pinned one.
- Seeds: new, and different from Q3's. A Q3 seed is refused.
- Surface: one text per tree. A missing domain, a Noetic-level register and a null register are refused.
  Unsupported output is refused, not simplified.
- Rows: every row recompiles to its stored target. Tokens round-trip. Slot kinds match `allowed_next`.
- Pairs: A one-field pairs, B swap and operator pairs, and C grouping, operator-only and leaf-only relations all
  hold. Groups never cross splits. Content is unique. A broken pair is caught.
- Identity: record ids are positional. Visible rows carry only the 4 keys. A rebuild is byte-identical. A
  non-empty output folder is refused. A tampered file or a forged visible row is refused. The pin is required.
- Leaf sampler: draws exactly like Q3's `_random_literal`.
- Feedback: `first_wrong_decision` gives the right kinds. A D round makes fresh rows of the trigger's kind plus
  controls, and those rows verify. Forbidden trigger sources are refused.

**`test_q4_error_panel.py` (9 tests)**
- The module does not import torch, and has no `torch.optim`, no `.step(`, no evaluator door, and only
  create-only writes.
- `GPU_REQUIRED` fires before torch is imported and before any file is written.
- Eval and sealed names are refused.
- The panel selection is as declared, and stable (same digest twice).
- The saved predictions' first errors match the recovery: 10 lost branch at position 2, 5 wrong Noetic at
  position 3, and 1 PLUS instead of TIMES at position 1.
- One-field edits change exactly one token.
- Partners share shape and length.
- The tie-break rule matches free decoding.
- **A wiring check:** the Stage 0, Q3, Q4 and Q5 code runs end to end on a pure-Python fake model. The fake
  model is not Q4 and not neural. It only proves the code paths run.

## What I checked locally (pure Python, no torch)

| Check | Result |
|---|---|
| Byte-compile of the 4 new `.py` files | ok |
| `pytest test_q4_sdg_curriculum.py test_q4_error_panel.py` | **33 passed** in about 7 seconds |
| Tiny builds (sizes 16, 64 and 256) | `Q4_SDG_BUILD_PASS`; `--verify --unpinned --recompile` on size 16 gave `Q4_SDG_VERIFY_PASS` |
| Size-256 depth balance (train) | depths 0/1/2/3 = 64/66/65/62 rows |
| 16 train and 9 dev keys from the visible files | equal to the frozen constants |
| Current runtime source pins | equal to run_001's `plan.json` (12 of 12) |
| `q4_error_panel.py select` | 16 + 16 + 64 rows; digest above |
| First errors of the 16 saved predictions | 10 / 5 / 1, the same as the recovery |

## What could NOT be checked without AWS

- Every torch path. Stage 0 may fail on a T4, because the original ran on an RTX 4070 Laptop GPU.
- The actual Q3 to Q6 numbers.
- Whether the GRU backward is deterministic on a T4.
- **The re-initialisation.** CUDA random initialisation can differ between GPU models. The job reports
  `REINIT_NOT_REPRODUCED_ON_THIS_DEVICE` if update 1 does not match. The weight change would then not be the true
  change.
- The full-size build (`--size 4096`): its run time, and its refusal rates at that scale.
- **Engine parity.** An AWS build without the Rust `cas_engine` might accept or refuse different TIMES trees.
- Family D inside a real training loop.
- An AWS runner/launcher. I did not write one. It is in the ownership record's order of work, but it was not in
  my task list.

## Open questions

1. Who writes the AWS launcher for the diagnostic job? Limits: $1.00 ceiling, 45-minute timer.
2. Which compiler engine should the AWS build use? `--expect-engine` can hold it fixed.
3. **Committing the built package.** This sparse worktree excludes `*sealed*`. So the package's `sealed_*` files
   cannot be committed from here without `git add --sparse`, and other sparse worktrees will not see them. Where
   should the built package live?
4. Accept, change or refuse the proposals in `Q4_SDG_LESSONS_SPEC_v0_1.md`: size 4096, mixture, 16,384 updates,
   a token-matched B arm, and the panels. The owner still needs to name a dollar ceiling for training.
5. **One-field neighbours.** Different groups are not blocked from being one-field neighbours of each other. For
   example, a dev single state usually has a train neighbour. This is disclosed, not prevented. Is that acceptable
   for the "new content, familiar structure" panel?
6. **The 4-leaf grouping sets.** A set is kept when at least 2 of its 3 bracketings compile. The dropped
   bracketings are logged. Is a partial set acceptable, or should all 3 be required?
7. **Family A drive and register balance.** Family A balances over {none, F1-F7} and {none, T, A, f, E}. This
   follows the directive. Leaves inside B and C trees instead follow Q3 G's 50/50 presence rule. So "no drive" is
   1/8 of A rows, but half of B and C leaves.

## Exposure (everything outside this worktree that I opened or used)

- **Git object store:** `git show 8eb798a5:<directive path>`, as the task told me to. No other `git show`.
- **Scratchpad** `C:/Users/wakil/AppData/Local/Temp/claude/.../scratchpad/`:
  - I wrote and read my own tiny builds there (`b1/`, `b256/`) and a temporary byte-compile folder. I deleted them.
  - I listed the folder once. It is shared with earlier sessions, so I saw other files' names. I opened none of
    them.
- **pytest temp folders** `C:/Users/wakil/AppData/Local/Temp/pytest-of-wakil/pytest-*/`: the tests' own tiny
  builds, D rounds and tamper copies.
- **Sealed files I read:** only the `sealed_*` sidecars of packages I had just generated myself (in the scratchpad
  and pytest temp folders). The loader and the pair tests have to read them.
  - I read no Q3 sealed file and no eval file.
  - This worktree does not contain them.
- **Python:** `C:/Python314/python.exe`, its standard library, and pytest 9.0.2.
  - The pinned compiler imported the optional Rust `cas_engine` from
    `C:/Users/wakil/AppData/Roaming/Python/Python314/site-packages/cas_engine/`.
  - I did not open those files myself.
- **Not touched:** D:/tksCAS-archive/, any hset1a path, any other worktree, S3/AWS, and any Claude session
  transcript.
