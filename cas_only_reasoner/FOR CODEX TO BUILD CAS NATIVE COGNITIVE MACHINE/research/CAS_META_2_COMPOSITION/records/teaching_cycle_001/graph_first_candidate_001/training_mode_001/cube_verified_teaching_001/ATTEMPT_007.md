# Attempt 007 of the checked-component pilot — the run finished and delivered a result

Written 2026-09-10. Every number below is read out of the delivered artifact
(`receipt_cas-meta2-graph6cand-20260910174500-e33a6497/curriculum_result.json`),
not recalled and not rounded.

This is the pilot's **first completed run**. It produced a measured result, and
the result is negative on the question the pilot was built to ask.

## What was authorised and bound

| item | value |
| --- | --- |
| owner instruction | `GO` (`OWNER_AUTHORIZATION_CANDIDATE_PILOT_005.json`) |
| job | `cas-meta2-graph6cand-20260910174500-e33a6497` |
| source commit | `b2ff5a4bbdd3444cc8915bd0ed9665c350012222` |
| package | `candidate_package_006/`, archive sha256 `e33a64975fddb794706f3995688ebda7df86a7f821091b7fdbedecdeab3134fc`, manifest sha256 `becda10cebca22076be9556d87eafdcd6ace638b3a9a53c82deb8830c463c165` |
| reservation | `$7.00`, ledger revision 56, `RESERVED_NO_AUTOMATIC_REFUND` |
| instance | `i-0a86c9e3a0826ab60`, g7.2xlarge, launched 17:46:40 UTC |

Launcher verdict: **`AWS_CANDIDATE_FINISHED`**, `execution: FINISHED`,
`collection: VERIFIED`, `cleanup: COMPLETE`, `completed_deliverable: true`,
elapsed 551.9 s. Instance `CONFIRMED_TERMINATED`, security group deleted, roles
removed, bucket deleted after verified collection. Actual EC2 time was about
3 minutes 25 seconds, roughly `$0.14` at the `$2.52/h` ceiling.

## Run integrity (all read from the result)

| check | reading |
| --- | --- |
| optimizer updates | 128 (64 per condition), `planned_steps` 64 each, `stopping_reason: blocks complete` |
| automatic retries | 0 |
| seven-stage neural cycles | 0 |
| matched initial weights | true, `initial_weight_digest` `67d3ce8ffa9fbf024a2f35073cf4f972` |
| teaching allocation | checked 24 whole-answer + 40 component; final-answer-only 64 + 0 |
| containment | `contained: true`, `forbidden_changes: []`, exactly 3 permitted parameters changed: `left.weight`, `merge.weight`, `right.weight` |
| checkpoint | written, read back and verified true in both conditions |
| learner index identity | identical in both conditions: `1ea3e069063a0d5ca85fd585cf05be3d` |
| predictions | 64 per condition, taken before their update |
| delivered artifacts | `checkpoint_checked_component_teaching.pt` sha256 `e4b41c74…`, `checkpoint_final_answer_only.pt` sha256 `67f18a4c…` |

## The measurements

| set | checked_component_teaching | final_answer_only |
| --- | --- | --- |
| primary: 3 taught whole-answer questions | 2/3 (0.6667) → 3/3 (1.0000), **+1** | 2/3 (0.6667) → 3/3 (1.0000), **+1** |
| taught component: 5 questions | 2/5 (0.4000) → 2/5 (0.4000), **0** | 2/5 (0.4000) → 1/5 (0.2000), **−1** |
| untaught probe: 44 questions | 12/44 (0.2727) → 9/44 (0.2045), **−3** | 12/44 (0.2727) → 7/44 (0.1591), **−5** |

Probe by operation, after training:

| operation | checked | final-answer-only |
| --- | --- | --- |
| LIST_PARTS | 4/5 | 4/5 |
| FIND_SHARED_PART | 2/14 | 2/14 |
| REACHED_VIA | 3/25 | 1/25 |

Exact tests, computed from those counts:

- probe after, 9/44 vs 7/44 — Fisher two-sided **p = 0.7830**;
- taught component after, 2/5 vs 1/5 — Fisher two-sided **p = 1.0000**;
- primary after, 3/3 vs 3/3 — identical, both at the ceiling;
- probe against the three-option chance rate of 1/3: before training 12/44,
  `P(X ≤ 12) = 0.2474`; checked after 9/44, `P(X ≤ 9) = 0.0452`; final-answer-only
  after 7/44, `P(X ≤ 7) = 0.0081`.

## What the result says, and what it does not

1. **No established advantage for checked component teaching.** The only set
   where the two conditions differ is the 44-question probe, and 9 against 7 is
   not distinguishable from chance (p = 0.7830). The declared primary set cannot
   discriminate at all: both conditions reached 3/3, its own reported warning
   being that "one changed answer moves accuracy by 33.3 percentage points".
2. **No generalisation to untaught questions — the measured movement is the
   other way.** Both conditions answered *fewer* probe questions correctly after
   training than before: 12 → 9 and 12 → 7 out of 44.
3. **Both conditions finished below the three-option chance rate on the untaught
   probe** (20.45 % and 15.91 % against 33.33 %), and the departure is
   statistically visible in both. That is evidence of a systematic answer
   preference rather than partial skill, and it is preserved here as a negative
   finding. Caveat, stated exactly: chance is 1/3 only if the correct option is
   uniformly placed, which the design intends (order derived from public content
   alone), and 3 of the 44 probe questions have unequal item counts because their
   answer is empty.
4. **This says nothing about the seven-stage cube program.** The counters report
   `seven_stage_neural_cycles: 0`, and the result's own note is that only checked
   component teaching has a numerical delivery path here: definition, analogy,
   correspondence and story presentations were never delivered.
5. **Interpretation bound**, from the frozen design: this measures how to spend a
   fixed 64-update budget, not whether adding component instruction helps at
   equal final-question practice, because the control practised the final
   questions 64 times against 24. A negative result never means the seven-stage
   program failed.

## Two reporting gaps found in this delivery

Both are recorded rather than glossed, both belong to this pilot's own code, and
both were fixed after the run without touching the run's numbers:

1. **Every score and loss field reads "unavailable"** (`scores_unavailable_count:
   64`). `candidate_experiment._scores` looks for a `learner.scores(task)` method,
   and `GraphLearner` never had one, so the declared reporting plan's "all three
   scores and the loss" for the primary questions could not be reported. The
   code's behaviour is the honest one — it refuses to print zeros for unmeasured
   values — but the measurement was simply not taken.
2. **The per-question rows and the before-training per-operation breakdown were
   computed and then discarded.** `condition_report` keeps only
   `by_operation_after`, so the delivered report cannot say whether, for example,
   LIST_PARTS was already 4/5 before training. That matters here, because
   LIST_PARTS (4/5) dominates the 9/44 total.

## State afterwards

- The pilot's question is answered as **not established**: no measurable
  advantage for checked component teaching at this budget, on this data, with
  this encoder; and no generalisation, with both arms below chance on the
  untaught set. Nothing here licenses a claim about the seven-stage program.
- Ledger revision 56: `$305.00` reserved, `$95.00` free against the `$400.00` cap.
- No instance, bucket, IAM role, instance profile or security group remains from
  any of the five pilot jobs.
- The two checkpoints are delivered locally with their hashes recorded above;
  the evidence bucket was deleted only after verified collection.
