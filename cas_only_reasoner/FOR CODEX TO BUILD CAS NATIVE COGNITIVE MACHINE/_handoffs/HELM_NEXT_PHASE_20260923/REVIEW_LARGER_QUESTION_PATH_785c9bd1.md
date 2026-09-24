# Review: larger-question path v0.1 (HELM-LARGER-QUESTION-PATH-1), code 785c9bd1, report a2bab9f2

- **Label: CLAUDE_BUILT_CLAUDE_CHECKED.** Written by a fresh, adversarial Claude reviewer during the temporary
  takeover. Codex is away until 2026-09-28. Custody is not independent: Claude also built the path.
- Branch: `claude/helm-builder-continuation-20260923`. Reviewed files: the 8 files of `785c9bd1` under
  `research/CAS_META_2_COMPOSITION/eval_paths/`, and `BUILDER_REPORT_LARGER_QUESTION_PATH.md` of `a2bab9f2`.
- All 8 files on disk equal the sha256 values in the report. They have not changed since `785c9bd1`.

## Verdict: CHANGES_REQUIRED

In plain words:

- **The path itself is sound.** Items 1 to 6 of the brief pass. The router, the refusals, the subclass copy, the
  inventory boundary, the kind table and the 41 fixtures all hold up. I found no way around a refusal.
- **The AWS T4 script is not ready to launch.** Its planned work very likely does not fit its own 3,600 s limit.
  A committed T4 measurement puts the run at about 3,600 s in the best case and about 5,000 s in the worst.
  The check that matters most (d, the subclass against the original learner) runs last, so it is the one that
  gets cut. When the limit is hit, the half-finished check's results are thrown away. A paid run would most
  likely end with `WALL_LIMIT_REACHED` and no verdict.
- **The fix is small and stays inside `t4_larger_question_checks.py`** (plus report wording). Nothing in the
  router, the learner half or the fixtures needs to change. The minimum change set is listed below.

## What I did

| Step | Result |
|---|---|
| Read all 8 new files, the builder report, and the protected code they call (`pointer_learner.py` `_graph`, `_build_container`, `_degree_features`, `GraphForward`; `slots.py`, `slots_v2.py`, `answers.py`, `answers_v2.py`, `checker.py`, `checker_v2.py`, `source.py`, `course.py`, the four contract files, `gpu_adapter.py`, `cncm/typed_matched_worker.py`) | done |
| Ran the builder's torch-free tests once: `python -B -m pytest -q -p no:cacheprovider eval_paths/tests/test_larger_question_path_static.py` | **26 passed in 23.16 s** |
| Re-derived every fixture answer with my own code (own isomorphism search, own two reach rules, own parts/edges/definition/context), not the builder's | **41 of 41 agree; 0 problems** |
| Read the pinned public course from git objects (`public_course.json`, sha256 `cf7a7181...0987`) | bank digest `0f563762...e79c388`, 64 worlds, largest world 4 nodes, largest degree 3, 564 registry rows, every focus inside the bank |
| Checked each link of the inventory chain at the cited lines | all correct |
| Timed the torch-free steps that the T4 checks repeat per question (laptop, course-shaped 64-world packet) | cached compile 0.008 s; decisions 0.008 s; answer assembly 0.040-0.043 s; packet validation 0.046-0.048 s |
| Read the committed T4 run log of the Helm 2.0 preservation digests | see finding F1 |

Nothing ran with torch. No AWS call was made.

## Item by item

### 1. Questions with 4 nodes or fewer take the untouched original path: PASS

- **The subclass.** On the old route, `LargerQuestionPointerLearner._graph` calls `super()._graph(packet)`
  unchanged (`larger_question_learner.py:93-100`). The router only reads the packet. It never changes it.
- **The container path.** On the old route, `predict_packet` uses the frozen `slots` module itself
  (`slot_module(ORIGINAL)` returns `slots`), then the same `read_packet`, `GraphForward`, `_scalar_scores`,
  `_logit_rows`, `score_decisions` and `assemble_answer` as `_graph` (`pointer_learner.py:1918-1951`), in the same
  order. The builder's syntax-tree test checks the order.
- **All 564 course questions take the old route.** I checked this on the real pinned course, not only on a
  rebuilt bank: every registry packet carries exactly the course bank (`course.py:86-87`, `:285-292`), and that
  bank's largest world has 4 nodes. The builder's test checked one synthetic packet; this closes the gap.
- Two harmless differences, recorded only: the subclass wrapper calls the router before the parent's budget
  check, and it adds a `route` key to the internal result dictionary. Neither reaches the prediction bytes.
  Check d on the T4 is what proves the prediction bytes are equal.

### 2. The copied `_graph` differs only in the slot module: PASS

- By eye and by the syntax-tree test: with the docstrings removed, the two bodies have the same statements.
  Exactly one differs: `from . import slots` became `slots = scope.slot_module(scope.LARGER)`.
- Every free name the copy reads is imported from `pointer_learner` itself (tested), so it resolves to the same
  object the original uses.
- The copy cannot drift silently. `pointer_learner.py` is pinned, and the learner half refuses with
  `LARGER_PATH_REFUSED:SOURCE_DRIFT` at import if the pin moves.

### 3. Refusals fire before any forward pass and cannot be bypassed: PASS

- All four entry points ask the router first: `predict_packet` (after the GPU and eval-mode checks, before any
  compile), the subclass `_graph`, and the pure `compile_plan`, `decode`, `grade` and `target`.
- **I tried to find a bypass and found none.** The router returns "old route" without counting only when it cannot
  read the packet. But the frozen validator rebuilds every world from scratch (`source.py:232-255`): nodes are
  unique, edges are closed `{ref, source, target}` rows with text endpoints, no duplicates, no self-loops, no
  cycles. So every packet the old path would accept is one the router can count exactly. A malformed packet goes
  to the old validators and is refused there, as before.
- The degree the router counts is the degree Helm's reader sees: both come from the same `contains` edges
  (`pointer_learner.py:1043-1046`, `:1016-1017`).
- The training calls are refused on the subclass. The default `PointerCourseLearner` still answers 7- to 10-node
  parts, reach and edge questions without warning. That is by design (no protected file edited), and disclosed.

### 4. The new folder is outside the training launcher's input inventory: PASS

Every cited line is right:

| Link | Line | What it says |
|---|---|---|
| `aws/typed_pointer_launch.py` | 39 | `from cas_meta2.typed_teaching import pointer_contract as contract` |
| `aws/typed_pointer_launch.py` | 321 | `rows = contract.input_inventory(PROJECT if root is None else root)` |
| `pointer_contract.py` | 429 | `rows = [*practice.input_inventory(root), *_checkpoint_rows(root)]` |
| `practice_contract.py` | 74 | `input_inventory, material_inputs = matched.input_inventory, matched.material_inputs` |
| `matched_contract.py` | 174 | `rows = baseline.input_inventory(root)` (`baseline` is `worker_contract`, line 16) |
| `worker_contract.py` | 138-139 | `*.py` under `cncm` and `research/CAS_META_2_COMPOSITION/cas_meta2` only |

- `eval_paths/` is a sibling of `cas_meta2/`, so neither prefix covers it.
- The switch-ON runner (`run_on_study.py`) launches through the same `typed_pointer_launch.py`.
- No `.py` file under `cncm/`, `cas_meta2/` or `aws/` mentions `eval_paths` or `larger_question` (searched).
- The learner's identity list (`pointer_learner.py:469-478`) is a fixed list of 10 files.

### 5. The kind-by-kind scope table: PASS, with one open decision

- `diff checker.py checker_v2.py` shows only the docstring, `PROFILE_SCHEMA` and `MAX_ISOMORPHISM_NODES` (4 to 6).
  The bound is read only by `_bounded_graphs`, which only the isomorphism paths call. So for role, definition,
  context, parts, edge account and reach, checker v2 runs the frozen checker's code. The table is right.
- `slots_v2.compile_slots` hands every non-correspondence packet, and every correspondence packet of 4 nodes or
  fewer, to the frozen compiler. The table's "COMPILES / REFUSES" words are right, and tested on the fixtures.
- Answer-slot sizes are right (for example 25 and 36 edge slots; 121 and 721 correspondence candidates).
- The D-1 column matches `D1_ACCEPTANCE_RESULT.md`: A3 covered analogy and correspondence at 5 nodes and
  correspondence at 6; A5 and A6 covered bank rules and timing. **D-1 licensed checker v2 only for analogy and
  correspondence at 5 or 6 nodes.** See F6.

### 6. The fixtures: PASS

- My own code agrees with every `expected_values` entry and with checker v2 on all 37 answerable fixtures.
- Counts: role 2, definition 3, context 3, analogy 5, correspondence 8, parts 4, edge account 2, reach 10, plus 4
  refusals. Every kind appears with a 5-node and with a 6-node focus. Both reach rules appear.
- **Genuine no-match.** F07 and F20: the target has the same degree list, is not isomorphic, and has the same node
  count (121 and 721 candidates). F05: no isomorphic world at all, and 2 same-degree decoys. F18: the only
  isomorphic twin shares the focus's domain (so the rule says no match), plus 2 decoys.
- **Genuine no-path.** F12 and F25: the part is in the world and is reachable from the other root, but not from the
  whole.
- **Same-degree pairs.** S5A/S5B and S6A/S6B: same degree lists, not isomorphic, told apart by colour refinement.
- F19 has exactly 2 valid maps. F11's two rules name different nodes. H02's bank has no world above 4 nodes, and
  its focus sits outside the bank.
- Refusals: R01 (7-node focus) and R02 (7-node bank world) refuse by node count; R03 and R04 refuse by degree 5.
- The self-map counts of the committed shapes (at most 2 for the allowed ones) are far below the 64-answer cap.

### 7. The T4 script: FAILS on the time limit; the rest mostly passes

| Requirement | Result |
|---|---|
| Checks old-question preservation, 564 questions x 6 Helm 2.0 checkpoints | runs, but compares two copies of the same steps (F2) |
| Runs the fixtures through the listed containers (3 trained finals OFF, fresh OFF, fresh ON) | yes, 37 x 5 = 185 |
| Refusals with zero forward passes | yes: counts `GraphForward` in the learner half (check c) and counters (check d) |
| Learner versus subclass identity | yes, check d, on fresh switch-ON learners (F8) |
| Fails closed without CUDA | yes: exit 2 before any setup; no CPU fallback |
| Writes no right/wrong flags | no explicit flag, but correctness can be recomputed (F4) |
| Stays inside its 3,600 s limit | **no, very likely not (F1)** |
| Names exactly the files it needs | **no (F3)** |

Things I checked that do hold: the checkpoint loading matches `preservation_digest.py` (strict `load_state_dict`
from `torch.load(..., weights_only=True)["model_state"]`); the per-question and overall digest formats match it
exactly; the check d learner is built as `cncm/typed_pointer_worker.py:869-884` builds it; the learner's T4 ban
(`T4_NOT_ADMITTED`) lives only in `gpu_adapter._cuda`, which this script never calls; `validate_answer` has no
permutation bound, so the frozen `answers` module can validate 5- and 6-node answers.

## Findings

| Id | Severity | Finding |
|---|---|---|
| F1 | **MAJOR** | The T4 work very likely does not fit the 3,600 s limit, and check d runs last |
| F2 | MINOR | Check a compares two copies of the same code; it does not compare with the recorded Helm 2.0 digests |
| F3 | MINOR | The script does not name its input files; the report's list is loose and misses the two wheels |
| F4 | MINOR | Right/wrong is recoverable from `answer_sha256` and `check_digest`; the "only graded and receipt digest" wording is wrong |
| F5 | MINOR | The pure half never checks the pins, so a torch-free grader could use a drifted checker v2 |
| F6 | NOTE (decision) | Checker v2 is not D-1 licensed for parts, edge account or reach at 6 nodes |
| F7 | NOTE | Two raw inputs go past the trained range at 5 and 6 nodes; not disclosed |
| F8 | NOTE | Check d tests the subclass with the switch ON only |
| F9 | NOTE | Builder exposure: repo-wide `git grep` and three files under an `hset1a` path |
| F10 | NOTE | Small wording items in the report |

### F1 (MAJOR): the planned T4 work does not fit its own time limit

- **The planned work.** 8,122 forward passes: check a 6,768 (6 models x 564 questions x 2 paths), b 185, c 4,
  d 1,165.
- **The measured rate.** `records/helm_eval_design_20260923/analogy_wiring_probe/RUN_LOG.md`, "Attempt 5", on a
  `g4dn.2xlarge` (Tesla T4): each preservation job took 810 to 811 s for 3 models x 564 questions = 1,692 forward
  passes. That job compiles each plan and reads each packet only ONCE. So a forward pass costs at most
  0.479 s, and about 0.39 s if start-up took 150 s of each job.
- **Forward passes alone:** 8,122 x 0.39 to 0.479 s = about 3,170 to 3,890 s.
- **Extra work this script adds.** Check a re-reads the packet, re-decodes and re-assembles the answer on every
  call, for both paths. Answer assembly re-validates the whole 64- or 65-world source. My laptop timing of the
  torch-free part alone is about 0.06 s per call, before `read_packet`. That adds at least about 400 s in check a,
  and up to about 1,000 s. Checks b and d add grading and 16 container builds.
- **Projection: about 3,600 s at best, about 5,000 s at worst, against a limit of 3,600 s.** The builder gave no
  time estimate.
- **Why this matters.** The checks run in the order a, b, c, d. Check d is the only check of the subclass against
  the original learner, and it runs last. On `WallLimit` the running check's rows are discarded
  (`main`, lines 423-427): only `WALL_LIMIT_REACHED` is written. So the likely outcome is exit 3, a partial record,
  and a second paid launch.
- **Minimum fix (any one of the first three, plus the fourth):**
  1. Run the checks in the order d, c, b, a, so the subclass check cannot be the one that is cut.
  2. Shrink check a. For example, keep the paired old-versus-new comparison on 1 or 2 checkpoints, not 6. On the
     other checkpoints, run `predict_packet` once per question and compare its overall digest with a recorded T4
     reference (see F2).
  3. Or raise `WALL_SECONDS` on a measured basis, and add a preflight that times about 20 forward passes and
     refuses before the main work if the projected total exceeds the limit.
  4. Write each finished model's (or fixture's) rows as they complete, so a stop at the limit keeps what ran.
- The report should then state the expected wall time and where the number comes from.

### F2 (MINOR): check a does not test against history

- On the old route, `original_steps` (in the script) and `predict_packet` call the very same `slots`,
  `read_packet` and `GraphForward`. Their agreement shows the route choice and GPU repeatability. It cannot show
  that Helm 2.0's recorded answers are reproduced.
- Recorded references exist. `preservation_reference_20208c92_seed20260919.json` holds overall digests for fresh,
  initial and final of seed 20260919, and `RUN_LOG.md` lists digests for seeds 20260917 and 20260918. Those came
  from an 8 GB laptop GPU, not a T4, so their bits may differ on a T4. The T4 "Attempt 5" outputs are the right
  reference if they are committed (I did not open them: they are in a `results/` folder).
- Suggested: compare `predict_packet`'s per-model overall digest with the T4 reference for the same checkpoint.
  That is a true history check, and it halves check a's cost (helps F1).

### F3 (MINOR): the script does not name its inputs

- The script has no input list. The report says "the pinned course, tokenizer and development files; `cncm/`;
  `cas_meta2/`". That is not exact, and it misses the two wheels that `real_framework.py:63-66` imports
  (`casformer`, `cas_cjt`).
- The exact list, all present as git objects (checked by `git cat-file -s`):
  - `cncm/**/*.py` and `research/CAS_META_2_COMPOSITION/cas_meta2/**/*.py`;
  - `research/CAS_META_2_COMPOSITION/eval_paths/*.py` and `eval_paths/fixtures/larger_question_fixtures_v0_1.json`
    (the script hashes every `.py` at the top of `eval_paths/`, so the set shipped changes its record);
  - `records/typed_course_001/checks_002/public_course.json` (4,165,195 bytes, sha256 `cf7a7181...0987`);
  - `records/typed_interface_001/checks_002/training_tokenizer.json` (447,140 bytes, sha256 `bee9ab50...533c`);
  - `records/typed_matched_001/development_001/compact_development.json` (685,549 bytes, sha256
    `5780ffac...00b4`);
  - `records/typed_pointer_001/receipt_{20260917,20260918,20260919}/checkpoints/{initial,final}.pt` (pinned in the
    script);
  - installed wheels `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/casformer_reference-0.1.0-py3-none-any.whl`
    and `cas_neural_cjt-0.2.0-py3-none-any.whl` (sha256 in `worker_contract.WHEELS`);
  - torch with CUDA (the T4 preservation run used `2.11.0+cu128`).
- Suggested: put this list in the script as a constant, add a torch-free `--list-inputs` mode for the bundler, and
  check existence and sha256 of every data file before `Context` starts. Today the checkpoints are only checked
  inside check a, and a missing wheel shows up only as a crashed check.
- Cost if left: small. Missing files fail within minutes. But this is the same class of failure as the recorded
  T4 probe that died on a missing side file.

### F4 (MINOR): right/wrong can be recomputed from the record

- Check b writes `answer_sha256`, the sha256 of the canonical answer. The fixture file is public and holds each
  question's `query_id` and correct values. Anyone can hash the correct answers and compare.
- `check_digest` is a digest over a body that contains `"correct"` (`checker_v2.py:292-299`), so it can be
  recomputed the same way.
- The literal rule holds: no correct/incorrect field is written. But the script docstring ("Only 'graded, no
  error' and the checker's receipt digest are written") and the report say less than is written: `answer_sha256`,
  `logit_bits` and `admissible_answer_count` are written too.
- The coordinator has ruled that the 7 fixture shapes match 0 sealed TEST shapes and will be excluded, so this is
  not a leak. Fix the wording, or drop `answer_sha256` and `check_digest` if a stricter rule is wanted.

### F5 (MINOR): the pure half does not check the pins

- `verify_source_pins()` runs when the learner half is imported and at the start of the T4 script. The pure half
  (`route`, `decode`, `grade`, `target`) never calls it.
- A later torch-free scorer that imports only `larger_question_scope` would grade with whatever `checker_v2.py` is
  on disk, even if it no longer equals the D-1 anchor.
- Suggested: check at least the three D-1 anchors inside `grade()`, or at import of the scope module.

### F6 (NOTE, needs a decision): checker v2's licence at 6 nodes

- D-1 licensed checker v2 "for analogy and correspondence at 5 or 6 nodes" and not beyond the tested scope.
- The coordinator ruled definition, context and role not claim-bearing. There is no ruling yet on **parts, edge
  account and reach at 6 nodes** (D-1's extra check X covered 3 to 5 nodes).
- The code for those kinds is the frozen checker's, byte for byte, so the risk is low. But if HSET-2 has 6-node
  parts, edge or reach questions, someone must say whether they are claim-bearing.

### F7 (NOTE): inputs past the trained range

- `_query_vector` feeds the `whole` and `part` node positions as raw numbers (`pointer_learner.py:1102-1103`).
  The course never goes above 3; a 6-node world reaches 5.
- If `node_rank_feature` is on, each node's raw rank goes up to 5 as well (`:1056`).
- This is not a defect of the path. It belongs next to the report's section on what Helm's input can tell apart,
  because it will shape any later result.

### F8 (NOTE): check d uses the switch-ON learner only

- `_build_container` defaults to `analogy_focus_comparison=True`, and `PointerCourseLearner` does not pass it. So
  check d compares the original and the subclass with the switch ON.
- The switch-OFF Helm 2.0 checkpoints go through `predict_packet` only. The report should say this.

### F9 (NOTE): builder exposure, for the coordinator to confirm

- The builder report discloses a repo-wide `git grep -l` for the training bank digest, and a second long `git grep`
  whose output the tool saved to a file. A repo-wide `git grep` reads the contents of every tracked file,
  including any `*sealed*`, `*_eval.jsonl` or `hset1a` path, unless pathspecs exclude them. The report does not say
  they were excluded. Only file names came back.
- The builder also read three files under `records/helm_eval_design_20260923/hset1a/` and listed file names that
  include `hset1a_aws_job/results_attempt1/`. It declared these allowed.
- Please check both against the builder's brief. If they were not allowed, record them as exposure items.

### F10 (NOTE): small wording items

- "The old learner answered 7- to 10-node questions silently" was tested on the laptop only at the slot compiler
  and checker (R01). Check c's informational part will measure it through the forward pass.
- The kind table's claim that no allowed world can exceed 64 valid maps is also true for worlds with isolated nodes.
  By hand count, the most is 24 (for example one edge plus 4 isolated nodes). The report's caveat can be closed.
- The stale comment at `pointer_learner.py:54-57` and `:207-210` (degree list as a complete fingerprint) is
  correctly flagged by the builder and correctly left unedited.

## Required before the T4 launch

1. F1: reorder the checks (d first), keep partial rows on a wall stop, and either shrink check a or raise the limit
   with a measured projection and a timing preflight.
2. F3: add the input list and a pre-`Context` existence and sha256 check.
3. F4: correct the "what is written" wording in the script docstring and the report.

F2 and F5 are strongly recommended. F6 needs a coordinator decision before any 6-node parts, edge or reach result
is treated as claim-bearing. A short delta review of the revised script is enough; the rest of the path does not
need to be reviewed again.

## Claim status

- **REAL (measured by this reviewer):** 26 of 26 builder tests pass; 41 of 41 fixture answers re-derived; the pinned
  course bank's largest world is 4 nodes, largest degree 3; the inventory chain lines; the file hashes.
- **Estimated, not measured:** the T4 wall time (from a committed T4 run of a similar job, plus laptop timing of the
  torch-free steps).
- **NOT RUN:** all four T4 checks. Nothing here was run with torch or on a GPU.
- **NOT LICENSED:** any statement about Helm's accuracy on larger questions.

## EXPOSURE: every file outside my working copy that I opened

My working copy is `D:/tksCAS-worktrees/helm-builder`.

**Loaded by the tool before I started (not opened by me).** The owner's global `CLAUDE.md`, the project
`CLAUDE.md` at `C:/Users/wakil/OneDrive/Desktop/tksCAS/CLAUDE.md`, and the auto-memory index `MEMORY.md`. The index
names the sealed-test archive folder and states sealed-build totals. It holds no TEST world, record id, shape or
answer.

**Read through git objects of `origin/research/helm-integration-20260923`** (`git show`), not working files:
- `records/helm_eval_design_20260923/analogy_wiring_probe/preservation_digest.py` (whole file);
- `.../analogy_wiring_probe/preservation_reference_20208c92_seed20260919.json` (only its top-level keys, GPU
  admission fields, wall and load seconds, and each model's label, checkpoint, checkpoint sha256 and overall
  digest, printed through a Python filter);
- `.../analogy_wiring_probe/RUN_LOG.md` (a `grep` for timing words, then lines 21-80). Those lines name
  `D:/tksCAS-archive/helm_wiring_probe_aws_20260923` and `../aws_probe_job/results/`. I opened neither;
- `records/helm_eval_design_20260923/d1_acceptance/D1_ACCEPTANCE_RESULT.md` (a `grep` for headings, anchors and
  "node", then lines 44-93 with every line containing "sealed", "hset1a" or "test_new" filtered out). It reports
  counts only;
- file names only (`git ls-tree`) of `records/helm_eval_design_20260923/analogy_wiring_probe/`, and the local branch
  names matching "integration".

**Read through git objects of this branch, outside the sparse checkout:** the pinned public training course
`records/typed_course_001/checks_002/public_course.json` (bank shape and registry size only, through a Python
filter); and `git cat-file -s` sizes of the tokenizer, the development file, two wheels and two Helm 2.0
checkpoints (sizes only, contents not read).

**Written by me outside the working copy:** two small scripts in the session scratchpad
(`indep_fixture_check.py`, `time_cpu_steps.py`), run with `python -B`.

**Saved by the tool, not opened by me:** my first `cat` of the builder report was long, so the tool saved its output
to a file under `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not open it; I re-read the report from the
working copy.

**Local machine, not project data:** `python` 3.14.0 and pytest 9.0.2.

**Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` or `*sealed*` file, any `*_eval.jsonl`, any path containing
`hset1a` or `hset1b`, any `results/` folder, S3 or AWS, the meta1 ledger, other worktrees' files, and Claude
transcripts.
