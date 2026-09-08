# CAS teaching cycle: input-binding candidate

Status: implementation and pure checks only. No lessons delivered to a neural
student yet. This is separate from frozen condition-skill v9.

## What this teaches

The required source must reach the intended operation in the required role.
The student selects `BIND0`, `BIND1`, or `BIND2` from the existing META2 policy.
The child is a fixed, declared `RUN A` call. Its program is not predicted.
This is binding-selector training, not training A's internal `^6` operation.

The input is the supported problem text plus three tagged eight-number
observations. Use the existing base `CASProgramGenerator` and matched
`GenericProgramGenerator`, with the lossless text tokenizer. The first
prediction after BOS already selects a binding. No neural-core redesign,
accepted checkpoint replacement, new pulsation, or new Noetic meaning is used.

The seven aligned stages are name/function, context, analogy, explicit
technical/context/analogy mapping, guided `^6` decomposition, recomposition,
and reinforcement. Full guidance includes worked answers and corrections.
All seven views use the same checked formal case. The model receives their
bounded text through its real input; alignment is not metadata alone.

These finite teaching templates test a narrow relationship. Passing them
would not establish unrestricted English or metaphor understanding.

## Allocation and assistance

Each aligned learner must receive at least **1,024 complete seven-stage
cycles across all 256 training families** before readiness is considered:
7,168 supervised stage presentations per learner at minimum. This is a
declared pilot allocation, not a universal guarantee of understanding.
Require at least four full guided cycles for each family; repeating one case
many times cannot substitute for the other families' exposure.

Keep full guidance initially. Check unassisted development performance after
1,024 completed cycles, then after each additional 256 completed cycles.
Require three consecutive checks at or above 90% binding accuracy before
moving from full guidance to hints. Require another three before removing
the task-specific hint, then another three before declaring readiness for
final evaluation. All seven stages remain connected during teaching.
Feedback is a teaching signal, not a mastery verdict.
Each check covers all 64 registered development cases; the controller derives
the score from predictions, not a supplied percentage or an undersized sample.

Stop at 4,096 blocks per arm or the launch's declared wall-time/cost limit,
whichever comes first. Save progress. If the minimum was not delivered,
report `TEACHING_INCOMPLETE`. If the allocation was completed without
readiness, report that fact without claiming the architecture cannot learn.
The end-to-end scheduler and crash-safe exposure/checkpoint pairing are still
required before launch; the current controller validates in-memory events.

## Comparisons and partitions

Four candidate arms: CAS/aligned, CAS/ordinary, generic/aligned,
generic/ordinary. The ordinary control receives seven definition/example
presentations per block, not seven aligned stages. Use matching initialization
within each model family, the same cases, common train-only tokenizer,
optimizer-step and example budgets, declared checkpoint rule, and evaluator.
Record actual tokens, time, teacher construction work and changed parameters.
Richer text is not free supervision. A later ablation can isolate alignment.

| Partition | Cases | What it tests |
| --- | ---: | --- |
| Training | 256 | Guided learning |
| Development | 64 | Fresh instances for readiness and checkpoint selection |
| Test: fresh | 64 | New values with familiar task forms and tags |
| Test: context | 64 | Unseen irrelevant context combinations, using known words |
| Test: names | 64 | Unseen color/shape tag combinations, using known words |

The three final tests are distinct; none tests unfamiliar nested programs.
All views of one formal family stay together. Final public inputs contain no
worked binding or program answer. Gold belongs to the independent evaluator,
not the training worker. Folder separation alone does not enforce that rule.
Before launch, package/access checks must prove the boundary and freeze the
scorer. Final tests cannot feed the teaching/readiness controller.

## Evidence that must accompany real teaching

Count only ordered stages from registered training cases that have matching
input/target receipts and an optimizer step in the declared candidate scope.
Record full-cycle and per-stage counts, distinct families, assistance level,
state hashes, nonzero-gradient names, changed-parameter names and actual cost.
Zero gradients or unchanged parameters are not evidence of learning.
Presentation counts remain visible even when gradients are zero. Before
readiness, every family must have participated in at least one complete cycle
whose seven stage batches had nonzero gradients in the binding path. That
batch-level observation does not localize a concept to individual neurons.
Simulated receipts remain `SIMULATED_ONLY_NOT_DELIVERED`.

The CUDA adapter uses the existing candidate's embeddings, encoder/control
adapter, decoder and binding path. Its nominal scope is not a claim that
every parameter received a nonzero update. All accepted native weights remain
outside this adapter. CUDA availability and an enable flag do not prove AWS
identity; independently bind the eventual run and retained artifacts.

Final scoring must separately check binding accuracy and exact selected input
bytes at the native call boundary. A constant authored output from A is not
sufficient evidence of correct binding. Native execution scoring, paired
relevant/irrelevant-change probes, a rule control, retention after intervening
learning, and save/restart/retest still need end-to-end integration. Restart
alone is not resistance to forgetting. No final mastery result exists yet.

## Current run boundary

No new paid job or reservation was made for this preparation. The latest
observed campaign ledger is revision 17: $102 reserved and $298 unreserved
of the $400 cap. Reservations are not invoices. No refund is inferred from
the failed v9 launch. Its one-shot authorization is not silently reused.

The AWS profile rejection and separate launch-path hazards are preserved in
`../condition_skill_v9_001/launch_forensics_001/FINDING.md`. Fix and verify
the required launch dependencies before any future paid experiment.

Preserve familiar-program `24/24` and held-out composition CAS `0/72`
(depth 3: `0/48`; depth 4: `0/24`) as separate historical results. This new
preparation changes none of them. It establishes no new learning, CAS-specific
advantage, broad reasoning, language capability or completed CNCM brain.

## Reproduce the preparation

From the CAS_META_2_COMPOSITION directory, with Python 3.12 and pytest:

```powershell
python -B tools/check_teaching_cycle.py records/teaching_cycle_001/checks_NEW
python -B tools/prepare_teaching_cycle.py records/teaching_cycle_001/material_NEW
```

Use fresh output names. The checker blocks neural, database and provider
imports and network calls. Preparation does pure data work only. Neither
command starts training. Source hashes and raw check outputs are retained.
