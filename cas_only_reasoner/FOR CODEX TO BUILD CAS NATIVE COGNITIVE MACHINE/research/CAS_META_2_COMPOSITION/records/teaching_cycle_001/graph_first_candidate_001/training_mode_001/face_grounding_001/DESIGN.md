# CUBE_FACE_GROUNDING_001 and CFC_LOOP_001 — what was built, and what is not built yet

Written 2026-09-10. Status: **non-neural implementation complete and tested;
launcher binding and package build not yet done.** Nothing here trains, reserves,
loads a model or launches. No execution is authorised by this document.

The two owner plans are pinned beside this file as
`Cross_Cube_Face_Grounding_Plan_v0.1.md` (sha256 `c9de1732e15382c3…`, 28,212 bytes)
and `Cube_Face_Cube_Learning_Loop_v0.1.md` (sha256 `87765a17eb374d57…`, 22,656
bytes); `SOURCE.json` records their origin. They are the specification; this
document reports the implementation against them.

## 1. What exists now

| module | what it holds |
| --- | --- |
| `cas_meta2/graph_teaching/face_roles.py` | the six-role registry with its declared objectives, subtypes and cues; the stable cue per role, one neutral cue, and a cue-free arm; group rotation over all fifteen role pairs |
| `cas_meta2/graph_teaching/face_corpus.py` | 96 authored lesson families, 6 domains x 16, six structural arrangements, four renderer rotations, the 64/16/16 split assigned before any rendering exists, cross-domain analogy partners, the declared scoped correspondence, the coverage report and the dataset manifest |
| `cas_meta2/graph_teaching/face_tasks.py` | both profiles for all six faces: `ROLE_FROM_CONTENT` and `FACE_APPLY`, the worked supports, the neutralised recognition excerpts, the ambiguity screen, the public-only record id and the public-content-derived option order |
| `cas_meta2/graph_teaching/face_schedule.py` | the grounding sweeps (Phase A/B), the CFC loop (within/across/return), the mixed-order control, the cue arms and the exact arithmetic with both update accountings |
| `cas_meta2/graph_teaching/face_evaluation.py` | the 96+96 held-out panel, the cue-free evaluation arm, the rename/reorder/rewire diagnostics, per-layer and per-face reporting, constant-rule baselines, paired before/after and between-condition comparison, the milestone report |
| `cas_meta2/graph_teaching/face_experiment.py` | the four-condition runner: batched teaching, per-episode rows with the correction pass's own scores, containment and checkpoint verification through the accepted helpers, `TEACHING_INCOMPLETE`, matched-initial-weights enforcement, and the result envelope |
| `tools/graph6_face_records.py` | writes the manifest, coverage, bindings, ambiguity report, schedule, panel and one worked episode per face |

Evidence generated from those sources is in this directory: `FAMILY_MANIFEST.json`,
`COVERAGE_REPORT.json`, `ROLE_REGISTRY.json`, `TASK_BINDINGS_FACE.json`,
`AMBIGUITY_REPORT.json`, `SCHEDULE.json`, `EVALUATION_PANEL.json`,
`WORKED_EPISODES.json` and the readable `WORKED_EPISODES.md`.

## 2. The declared arithmetic, as compiled

| quantity | value |
| --- | --- |
| training families / all families | 64 / 96 (dev 16, final held-out 16) |
| base face presentations | 576 |
| Phase A queries and supports | 6,144 / 18,432 |
| Phase B recognition / application queries | 1,536 / 1,536 |
| supervised query presentations | 9,216 |
| optimizer updates at batch 8 | 1,152 |
| optimizer updates if one per episode | 9,216 (stated, never relabelled) |
| CFC round | within 28 + across 12 + return 8 = 48 |
| CFC total decisions | 6 cohorts x 16 rounds x 48 = 4,608 |
| held-out panel | 96 recognition + 96 application + 24 diagnostics |

Recognition events are exactly balanced across the six roles at 1,536 each, and
every role pair competes in some question group.

## 3. The boundaries this build keeps

- **The cue is the only difference between the two cue arms.** The delivered slot
  order is derived from public content alone and is therefore *identical* across
  arms, so the comparison cannot be given a second difference by accident.
- **The private target cannot reach the public bytes.** Swapping the teacher's
  answer leaves the record id, the problem text and the delivered option order
  unchanged; a test pins it. The earlier compilation folded a private target field
  into the record id, and that is why `verified_training.public_projection` exists.
- **Recognition excerpts do not name the role.** Face id, role title and
  category-revealing field names are absent, and content words that resemble a role
  title are neutralised; the screen is enforced, not merely reported.
- **Worked supports never come from the query's own family**, and the support
  answers are visible while the query's answer stays private until the prediction
  is recorded.
- **Scores come from the correction pass.** The batched step returns the per-episode
  scores and losses it actually back-propagated; the recording path never takes an
  independent later forward call with the same argmax.
- **Per-question rows are retained**, so the paired comparison that Attempt 007
  could not compute afterwards is computable from this delivery.
- **No architecture change.** The tasks are compiled into the campaign's frozen
  public codec and travel the accepted three-choice scoring path; `batch_step`
  reaches the learner's own forward and optimizer and adds no head, no parameter
  and no readout. The trainable scope remains the accepted `operation:^6` allowlist,
  checked by the accepted `trainer.scope_parameters` and
  `trainer.containment_report`.
- **Incompleteness is reported.** A run that reaches its stopping limit before the
  planned exposure reports `TEACHING_INCOMPLETE` with the counts it reached.
- **A sweep over six roles is not a completed seven-stage neural cycle**, and no
  counter in this build calls it one.

## 4. What is not built yet — stated plainly

1. **The launcher binding and the package build.** The runner is complete and
   rehearsed with injected stubs, but there is no rendered worker, no `DESIGN`
   binding for the four conditions, and no built source package, so the execution
   request below cannot yet name a package hash. This is the one remaining
   implementation step, and it is inside this assignment's scope rather than a
   blocker outside it.
2. **The interface-capacity question is not answered, and cannot be answered
   without a model.** Whether the accepted transform can represent these six tasks
   is exactly what the eventual job's pre-training input and gradient checks are
   for: changed roles, changed contents and same-token rewiring must produce
   different model-facing representations, and scores and losses must be finite
   with useful target-dependent gradients. Compilation proves the tasks *reach* the
   encoder; it cannot prove the encoder separates them. If it does not, that is a
   finding to report with the concrete restriction named, not a reason to
   substitute a name-lookup task.
3. **Batching is implemented but has never run on real tensors.** The rehearsal
   proves one optimizer step per batch and the row shape with an injected stub;
   the real path is exercised only when the job runs.

## 5. Interpretation rules this pilot will be held to

- Repeating a role name when the number is shown is **association only**.
- Recognising an unlabelled role but failing to apply it is **category
  recognition without demonstrated operational use**.
- Recognising and applying on held-out families is **bounded evidence of face-role
  grounding in this profile** — not unrestricted metaphor comprehension, not a
  general theory of analogy.
- Both conditions performing similarly means **no demonstrated additional benefit
  from the explicit numbering**, even if both learned.
- A role that fails while others succeed is reported as that role's boundary, never
  hidden in a pooled average.
- The capability targets in the plan are declared engineering targets; meeting them
  does not establish that stable cues beat the neutral control.

## 6. Preserved, untouched

Attempt 007 and its negative result, its two retained checkpoints, the accepted
models and weights, historical negatives, the pending retained-checkpoint
investigation and the answer-selection audit all remain exactly as they were. This
build claims nothing about that readout: it is a new, separately named candidate.
