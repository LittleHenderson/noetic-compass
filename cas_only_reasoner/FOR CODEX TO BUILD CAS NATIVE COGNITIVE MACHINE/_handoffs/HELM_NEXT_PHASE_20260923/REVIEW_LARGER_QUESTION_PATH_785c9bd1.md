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

---

# Verification of e21472a85acf561daf0703cb0808cb92476db8f3

- **Label: CLAUDE_BUILT_CLAUDE_CHECKED.** Written by a fresh Claude verifier during the temporary takeover. Custody
  is not independent: Claude also built, reviewed and revised this path.
- Commit verified: `e21472a8` (Revision 1 of the larger-question path). Parent: `cc68d8b3` (this review).
- It changes 4 files only: `t4_larger_question_checks.py`, `larger_question_scope.py`, the torch-free test file and
  `BUILDER_REPORT_LARGER_QUESTION_PATH.md`. No protected file changed. The file sizes and sha256 values on disk equal
  the report's table (Revision 1, section 11). All four files use LF only.
- The "Q4" part of the verifier brief (fakes for `ARCHITECTURE_CHANGE_JUSTIFIED`) does not apply here. This path has
  no such reader.

## Verdict: APPROVE_FOR_T4_CHECKS

In plain words:

- **The MAJOR finding (F1) is fixed.** Check d now runs first. Every finished row is on disk at once. A timing
  preflight refuses the run by name before the main work if the projected total is over 3,600 s. Check a is half its
  old size. The planned work fell from 8,122 to 4,917 forward calls.
- **Every MINOR finding and every coordinator decision is applied**, and applied as worded.
- **The new check a compares the same quantity as the recorded T4 history.** I re-read the six committed T4 files
  and the reference tool myself. I then replayed the recorded per-question digests through the real `check_a` code.
  It passes on the true history and fails on every change I tried.
- **Nothing else changed behaviour** beyond what the decisions asked for. The changes to checks b, c and d are
  stricter, not looser.
- **Five NOTES remain** (V1-V5 below). None blocks the T4 launch. V1 is a one-line hardening the coordinator may
  want before any torch-free scorer is used on its own.

## Decision by decision

| Item | Result | What I checked |
|---|---|---|
| F1 / decision 1: order d, c, b, a | **APPLIED** | `CHECK_ORDER = ("d", "c", "b", "a")`; `requested` is built from `CHECK_ORDER`, so a typed order cannot change it. I ran the real `main()` with a fake torch and fake checks: typed `a,b,c,d` still ran `d, c, b, a` |
| F1 / decision 1: rows written as each unit completes, create-only, flushed | **APPLIED** | `RowWriter` opens with `"x"`, then write, flush, fsync per row. In my fake run, the rows file already held each row when the check returned. A wall stop in check c kept d's rows and c's first row, marked c `NOT_COMPLETE`, b and a `NOT_RUN`, exit 3. A second run with the same `--out` refused (exit 4). No `.partial` was left behind. The unit is one model (a), one fixture (b, d), one refusal (c, d) or one learner pair's course sweep (d) |
| F1 / decision 3: preflight of about 20 forward passes, named refusal | **APPLIED** | 2 warm-up calls, then 16 timed course calls and 4 timed fixture calls (20), plus 1 warm-up and 3 timed learner calls. Refusal: `PREFLIGHT_OVER_WALL_LIMIT`, exit 5, summary written. Checked by a fake-clock run of the real `preflight` (below) |
| F1 / decision 3: expected wall time in the report | **APPLIED** | Report section 3: about 2,300 to 2,800 s, labelled an ESTIMATE. See V2 on how it was derived |
| F2 / decision 2: compare with the T4 item-1 digests | **APPLIED** | Compared field named: `results[].overall_digest`. Why it is the same quantity: stated point by point in the script and the report. I confirmed each point (below). The paired comparison was dropped, as the decision allows when the quantity is the same |
| F3 / decision 4: `REQUIRED_INPUTS`, `--list-inputs`, checks before torch | **APPLIED** | 12 files with bytes and sha256: course, tokenizer, development file, both wheels, 6 checkpoints, fixture file. `--list-inputs` printed 12 rows and exit 0 (the test also runs it with torch blocked). `verify_inputs` runs before `import torch`. I traced every data read of the run; the list is complete (below) |
| F4 / decision 5: digest wording | **APPLIED** | Script docstring, `BOUNDARY`, check b's note and the report now say right/wrong is recomputable from `answer_sha256` and `check_digest`, acceptable for public fixtures, never for sealed items. The old v0.1 sentence is marked wrong in place |
| F5 / decision 6: D-1 anchors inside `grade()` | **APPLIED** | `verify_grader_pins` checks `checker_v2.py`, `answers_v2.py`, `slots_v2.py` on the new route (and `checker.py` on the old route) on every `grade()` and `target()` call. See V1 for what it does not cover |
| F6 / decision 7: scope ruling in the table | **APPLIED** | `KIND_SCOPE` rows: reach at 6 nodes `CLAIM_BEARING_IN_HSET2_REACH_GOLD_CROSS_CHECKED_BY_INDEPENDENT_RULES`; parts and edge account at 6 nodes `DIAGNOSTIC_ONLY`; role, definition, context `OUT_OF_SCOPE`. The builder marks 5-node parts, edge and reach `NOT_RULED` and asks the coordinator (open question 1). That is honest, not a builder decision |
| F7 / decision 8: raw inputs past the trained range | **APPLIED** | Report section 8 discloses it. Check b records `query_whole`, `query_part` and `past_trained_query_range` per fixture. I confirmed the builder's correction to this review: `pointer_contract.DESIGN["node_rank_feature"]` is `False` (`pointer_contract.py:896`), so node rank is not a raw input in these containers |
| F8 / decision 8: switch-OFF in check d | **APPLIED** | A switch-OFF learner pair on every 8th course packet (71 of 564), all 37 fixtures, the 4 refusals, F20 and both training calls. The substitute of `_build_container` is scoped to the two constructor calls and restored in `finally`. `PointerCourseLearner.__init__` calls `_build_container(torch, framework, self.device)` by module-global name (`pointer_learner.py:1777`), so the substitute takes effect; if it did not, the read-back of `module.analogy_focus_comparison` raises `D_SWITCH_STATE`. Nothing in the learner's constructor requires the analogy head |
| F9, F10 | **RECORDED** | The builder records the v0.1 exposure items for the coordinator, and answers the wording items |
| Nothing else changed behaviour | **HOLDS** | Hunk by hunk: the scope module only adds the pin check, one return key and two table columns. Checks b, c and d keep their v0.1 pass rules; c also fails now if a refusal row is missing; d must pass on both pairs. The summary is now written once and create-only, as ordered |

## How I tried to break it

1. **Torch-free tests, run once.** `python -B -m pytest -q -p no:cacheprovider eval_paths/tests/test_larger_question_path_static.py`
   from `research/CAS_META_2_COMPOSITION`: **36 passed in 45.46 s.** The working tree was clean before and after.
2. **The T4 reference, re-read by my own script** from git objects of `41071a3f` (I fetched
   `origin/research/helm-integration-20260923` explicitly; `41071a3f` is an ancestor of its head `59d86443`):
   - all six file sha256 values equal `T4_REFERENCE["files_sha256"]`; every file is `complete`, torch
     `2.11.0+cu128`, course digest `272c26e1...6dbb`, tool LF sha256 `21bf01e5...292e`;
   - in the three OFF files, the five source pins equal `T4_REFERENCE_SOURCE_LF_SHA256`. In the three control files
     only `pointer_learner.py` differs, as expected for the unchanged `20208c92` source;
   - every checkpoint row: `init_seed` equals the receipt seed, `checkpoint` equals `_checkpoint_path(seed, phase)`,
     `checkpoint_sha256` equals the pin, 564 records, and `overall_digest` recomputes from its own `per_record`;
   - the six overall digests equal `T4_REFERENCE_OVERALL_DIGEST`, and the OFF and control per-question maps are
     equal on all six checkpoints.
3. **Same quantity, point by point.** I read the reference tool `preservation_digest.py` at `41071a3f` (whole file)
   and `job.sh.template` (the preservation lines):
   - per question: both write `"%08x" % (v & 0xFFFFFFFF)` of the float32 logits viewed as int32, as sorted-key compact
     JSON, then sha256 (tool lines 98-100; `larger_question_learner.logit_bits_digest`);
   - overall: both hash the newline-joined `"record_id digest"` lines over the sorted ids (tool line 101;
     `_overall_digest`);
   - same logits: `GraphForward(torch, model, reading, device).head_logits(plan, indicators)` with the frozen
     `slots.compile_slots` plan, `pointer_inputs.read_packet` and the same tagger rule. `predict_packet` then calls
     `_scalar_scores`, which reads the tensors and does not change them, so the digested `rows` are the head logits;
   - same container: the job's OFF runs pass `--container-kwargs '{"analogy_focus_comparison": false}'` and
     `--model h2_<phase>_<seed>:<seed>:records/typed_pointer_001/receipt_<seed>/checkpoints/<phase>.pt`; the
     framework seed is the checkpoint's own seed in both; strict `load_state_dict`, then eval mode;
   - same determinism: `CUBLAS_WORKSPACE_CONFIG=:4096:8`, deterministic algorithms (`warn_only=True`), cuDNN
     deterministic, no benchmark, in both.
4. **Replay through the real `check_a`.** With fakes that return the recorded per-question digests of the control
   files, the real `check_a` gives **PASS on all 6 models**, 6 rows, 564 digests each. It gives **FAIL** when
   initial and final are swapped (6 of 6 unequal), when one question's digest changes (only that model unequal),
   when one question takes the new route (`non_original_route_count` 1), and when one question is missing.
5. **The real `main()` with a fake torch and fake checks**, 9 cases: all pass (exit 0); typed order `a,b,c,d` (ran
   `d,c,b,a`); wall stop in c (exit 3, rows kept); crash in d (d `FAIL`, c, b, a still run, exit 1); preflight over
   the limit (exit 5, no check run); wrong torch with check a (exit 4, `T4_REFERENCE_ENVIRONMENT_DIFFERS`, before
   `Context`); wrong torch with `--checks d,c,b` (runs; `INTEGRATION_CHECKS_INCOMPLETE`, exit 1); no CUDA (exit 2);
   missing input (exit 4, before torch). Every case wrote the summary once; a second run refused.
6. **Preflight arithmetic.** `planned_work` for the real sizes (564 questions, 37 fixtures, 4 refusals): a 3,384
   course calls; b 185 and c 4 fixture calls; d 1,270 learner course calls (564 x 2 + 71 x 2) and 74 learner
   fixture calls; 14 container builds; 4 learner builds. Total 4,917, as the report says. A fake-clock run of the
   real `preflight` made 22 container calls (2 warm-up, 16 + 4 timed) and 4 learner calls (1 warm-up, 3 timed). With
   300 s of setup and 0.2 s of grading per fixture:

   | Seconds per course call (learner call) | Projected (with the 1.15 margin) | Fits? | Total at those speeds, no margin |
   |---|---|---|---|
   | 0.39 (0.44) | 2,705 s | yes | 2,394 s |
   | 0.49 (0.54) | 3,273 s | yes | 2,888 s |
   | 0.56 (0.61) | 3,671 s | **no, refuses** | 3,234 s |

   This matches the report's break-even (about 0.56 s per call, real total about 3,160 s). The margin makes the run
   refuse early rather than be cut late.
7. **Input completeness.** Every data file the run reads comes through `pointer_contract.load_material`
   (= `matched_contract.load_material`: course, tokenizer, development file), the fixture loader, the checkpoint
   loader and the two wheels (imported by `real_framework`). `load_material` is called three times: at the import of
   `pointer_contract` (`_import_time_stratified_digests`, line 672), in `Context`, and by the role tagger's cache
   (`pointer_inputs._build_cache`, line 260). The 18 practice checkpoints in `pointer_contract.MATERIAL` are read
   only by `input_inventory` (the training launcher), not by this run. The learner's identity files and
   `face_corpus.py` are `.py` files inside the shipped `cas_meta2` tree. So `REQUIRED_INPUTS` plus the two source
   trees plus the five `eval_paths` files is complete.

## Remaining findings (all NOTE; none blocks the T4 launch)

| Id | Severity | Finding |
|---|---|---|
| V1 | NOTE | `grade()` pins the three D-1 anchors, but checker v2 also runs code from four other files that `grade()` does not pin |
| V2 | NOTE | The wall-time estimate counts two of the reference tool's three course loads as forward-pass time |
| V3 | NOTE | The reference job also set `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2`; this script does not |
| V4 | NOTE | Open decisions stay open: 5-node parts, edge and reach; and the new claim words are local labels |
| V5 | NOTE | Check a needs torch `2.11.0+cu128` on a T4, and no launcher exists yet |

- **V1.** `checker_v2.py` imports `answers`, `focal` and `source` and calls `answers.validate_answer`,
  `answers.make_answer`, `answers.validate_query`, `focal.derive_roles` and `source.validate_public`; `grade()` also
  calls `course.validate_model_packet`. These four files are pinned only by `verify_source_pins`, which the pure half
  never calls. So a torch-free scorer could still grade with a drifted `answers.py`, `focal.py`, `source.py` or
  `course.py`. Decision 6 ("check the D-1 source anchors inside `grade()`") is met as worded. The scope docstring's
  "cannot grade with a drifted checker" is true of the checker file only. Cheap hardening: have
  `verify_grader_pins` also check those four pins (they are already in `PROTECTED_SOURCE_LF_SHA256`). Not needed for
  the T4 run, which calls `verify_source_pins` in `Context`.
- **V2.** The report takes the reference job's wall time minus ONE course load and divides by 1,692 calls. But the
  reference tool loads the course three times (import, explicit load, tagger), and prepares all 564 plans once. So
  the per-call figure (0.384-0.389 s) is too high, and this script's setup (also three loads, about 230 s assumed) is
  probably too low. The two errors partly cancel. The preflight measures both for real, so there is no launch risk.
  Treat the 2,300-2,800 s band as rough.
- **V3.** Thread settings only matter if CPU arithmetic feeds the logits. I found none on this path (inputs become
  device tensors; checkpoint copies are exact). If it ever mattered, check a would FAIL, not falsely PASS.
- **V4.** 5-node parts, edge account and reach are `NOT_RULED` (builder's open question 1). The words in the new
  `claim_status_*` columns (`OUT_OF_SCOPE`, `DIAGNOSTIC_ONLY`, `CHECKER_V2_D1_ACCEPTED`, ...) are not the spec sheet's
  status words. Map them to the legend before any of them enters `docs/CAS_HARNESS_SPEC_SHEET.md`.
- **V5.** If the T4 image is not torch `2.11.0+cu128`, a run that includes check a refuses before any GPU work
  (by design; builder's open question 2). The launcher must install that torch and both wheels with `--no-deps`, or
  run `--checks d,c,b`. The launcher is not written or reviewed yet; it needs its own check (bundle side files, the
  environment variable, Linux).

## Claim status of this verification

- **REAL (measured by me, torch-free):** 36 of 36 tests pass; the six T4 reference files and digests re-read and
  matched; the real `check_a`, `main()` and `preflight` driven with fakes as described; the input trace.
- **NOT RUN:** all four T4 checks and the real preflight. Nothing ran with torch or on a GPU. No AWS call was made.
- **ESTIMATED, not measured:** any T4 wall time.
- **NOT LICENSED:** any statement about Helm's accuracy on larger questions.

## EXPOSURE (verification): every file outside my working copy that I opened, and what else I saw

My working copy is `D:/tksCAS-worktrees/helm-builder`.

**Loaded by the tool before I started (not opened by me).** The owner's global `CLAUDE.md`, the project `CLAUDE.md`
at `C:/Users/wakil/OneDrive/Desktop/tksCAS/CLAUDE.md`, and the auto-memory index `MEMORY.md`. The index names the
sealed-test archive folder and states sealed-build totals. It holds no TEST world, record id, shape or answer.

**Read through git objects of commit `41071a3f`** (after `git fetch origin research/helm-integration-20260923`;
`FETCH_HEAD` was `59d86443`), not working files:
- the six files `records/helm_eval_design_20260923/analogy_repair_t4_job/results/preservation_OFF_T4_seed<seed>.json`
  and `.../preservation_control_20208c92_T4_seed<seed>.json`, as the coordinator's decision 2 names them. Through
  Python filters I printed their top-level keys, completeness, torch version, pin comparisons (true/false), each
  result's label, `init_seed`, checkpoint path and record count, and digest comparisons (true/false). The per-question
  maps were parsed and compared, not printed. I printed 5 record ids (public course ids, `typed-input-<hash>`) and
  one file's wall and load seconds (820.13 s, 168.90 s);
- `records/helm_eval_design_20260923/analogy_wiring_probe/preservation_digest.py` (whole file);
- `records/helm_eval_design_20260923/analogy_repair_t4_job/job.sh.template` (a `grep` for the preservation, model,
  container-kwargs, pip, wheel and environment lines, then lines 74-90).
I opened no other file under any `results/` folder.

**Read in the working copy (protected source, unedited):** `pointer_learner.py` (lines 465-480, 676-760, 850-875,
1092-1108, 1686-1720, 1751-1860, 2180-2195, plus `grep`s); `pointer_contract.py` (`grep`s; lines 655-682);
`practice_contract.py`, `matched_contract.py`, `worker_contract.py` (`grep`s; matched lines 160-195, worker lines
20-40 and 116-126); `pointer_inputs.py` (`grep`s; lines 301-325); `encoder.py` (`grep`s; lines 216-228); the import
lines of `checker.py`, `checker_v2.py`, `answers_v2.py`, `slots_v2.py`, `encoder.py`, `real_framework.py`, and a
`grep` of the names `checker_v2.py` uses from `answers`, `focal` and `source`; `source.py` (`CORPUS_PATH` line);
`cncm/typed_matched_worker.py` (lines 30-50 and 105-118). Also the whole review file, the builder report's Revision 1
section and its diff, all `eval_paths` files, and the v0.1 T4 script (from `git show cc68d8b3`).

**Written outside the working copy:** the session scratchpad only: `t4_old.py` (the v0.1 script from git),
`verify_t4_ref.py`, `sample_ids.py`, `fake_main_run.py`, `fake_check_a.py`, `fake_preflight.py`, and this section's
draft. The fake runs and the tests wrote and deleted temporary files in the system temp folder.

**Local machine, not project data:** `python` 3.14.0 and pytest 9.0.2.

**Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` or `*sealed*` file, any `*_eval.jsonl`, any path containing
`hset1a` or `hset1b`, any salt, S3 or AWS, the meta1 ledger, other worktrees' files, and Claude transcripts. No torch
import, no GPU, no training.
