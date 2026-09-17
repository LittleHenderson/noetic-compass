# Typed matched teaching study v0.1

Status: **IMPLEMENTED_NOT_RUN**. These rules and their implementation are fixed by the source commit admitted for launch. A separate pre-run admission record must bind that commit, the source archive, this document, exact material, tokenizer, schedules, endpoints and per-job authorities before the first numerical result. This document alone is not an execution receipt. Changes after results arrive require a new study version.

## Question and permitted conclusion

Does component-first grouping improve the speed or final accuracy of this typed learner, compared with mixing the same component/whole examples into the same-size update groups? The complete teaching course remains intact. This is a comparison of teaching order and grouping on one learner, not a comparison of CAS architecture against ordinary neural architectures.

The six development graph shapes provide a limited transfer test: new directed topologies with 8–10 nodes, after training on 3–4-node worlds. Report this as **development structural-and-size transfer on parts/reach**. It does not establish six-face transfer, final held-out performance, general reasoning, durable native memory, or CCB-T1 promotion. The earlier recurrent-depth result remains NOT_MET, with 0/3 positive seeds.

## Paired arms and fixed inputs

Run three fresh model-initialization pairs, using model seeds **20260917, 20260918 and 20260919**. Every pair compares `ALT_COMPONENT_WHOLE` with `MIXED_SAME_ITEMS`. Both arms use source curriculum seed **101**, encoder seed **20260916**, the same training-only tokenizer, the same optimizer settings and identical initial model/optimizer/encoder state bytes. Verify the initial state match; matching seed labels alone is insufficient. No earlier trained checkpoint or measured result is an arm.

The fixed encoder and curriculum make this a comparison conditional on one representation and one source schedule. Three model seeds do not establish robustness to encoder seeds, source curricula or independently sampled tasks. Retain and report all three pairs, including negative, tied or incomplete outcomes; do not choose seeds after inspecting results.

Each main arm contains all **1,152 presentations, 160 update groups, 16 rounds and eight typed answer kinds**. Preserve repeated occurrences as repeated presentations. The two supplement groups in every round contain the same eight component/whole pairs: ALT places eight component questions before eight whole questions; MIXED places four component/whole pairs in each eight-item group. Thus **256 supplement presentations change order/grouping, while 896 foundation and maintenance presentations remain unchanged**. MIXED includes no optimizer update between a component and its paired whole inside a batch; this is part of the treatment.

At batch size 8, the current ordinary dependency-graph policy produces exactly ALT's supplement batches. Its authored edges mean “teach this component before this whole,” not a logical prerequisite for answering. Preserve this exact schedule comparison as an audit. Do not spend a third arm on the identical schedule or call it a distinct numerical control.

## Equal information and measured work

Before execution, require exact equality between paired arms of the occurrence multiset, public packet bytes, legitimate worked supports, private correction contents, assigned depths, group sizes and complete source bank. Order-dependent identifiers must not change the learner-visible problem. Compare correction content independently of condition-specific receipt identity. Main prediction seals must be durable before their private targets are accessed.

Require the same counted work per arm: main presentations, slot evaluations, core forward calls, backward calls and optimizer updates. For the admitted source-101 course, the existing complete main-run expectations are **4,613 slot calls and 17,178 core forward calls**; reconstruct these expectations from the pinned typed plans rather than copying a success flag. Evaluation and validation work must also match between arms and remain separate from main teaching. Measure wall time, memory and total calls; equal counted work does not guarantee equal elapsed time or dollar cost.

The complete new arm contains **160 main updates + 16 further-instruction updates + 2 independent validation replay updates = 178 actual updates**. The further-instruction phase has 128 presentations, giving 1,280 presentations on the main trajectory. The two main-last-update replays each add their own eight presentations on disposable branches, giving 1,296 actual presentations including validation. Record every category separately. Replays must not change the main or retention trajectory. Reconstruct their exact forward counts from the replayed batch instead of treating them as free.

## Development transfer panel and learning speed

Use only the six previously allocated development topologies. Construct target-free typed public packets: one parts query at the declared root and a reach query from that root to **every other node**. Include every such query; do not select or balance questions by their answer, prediction or observed difficulty. Freeze the exact panel count, order, topology identities and packet bytes before execution. Keep the original training bank and add only the focused development world to its public context. Do not put development frames in the tokenizer fit.

This is an explicit typed parts/reach adaptation. The old 18-task development panel also contained `FIND_SHARED_PART`, which is not part of the current typed answer contract. Do not claim exact reproduction of that old panel. Do not read or construct final-target files for this development study, and do not use the perspective variants known to overlap development topology allocation.

Evaluate the same development panel at main updates **0, 40, 80, 120 and 160**, all complete-round boundaries. These boundaries give equal cumulative training exposures between arms. Use prediction depth 8 in both arms. For each phase, save the complete public prediction seal before deriving or accessing the private scoring targets. Do not repair predictions using the checker or use development corrections in training.

For each family, give the parts query and the mean of its reach queries equal weight; then average the six family scores equally. This avoids assigning greater weight to a topology solely because it has more nodes. Also report raw query accuracy and separate parts/reach accuracy, with exact denominators.

The primary speed endpoint is trapezoidal area under that family-balanced accuracy curve, divided by 160 updates. With five equally spaced checkpoints, this is `(A0 + 2*A40 + 2*A80 + 2*A120 + A160) / 8`. Report all five accuracies. The primary transfer endpoint is the same family-balanced accuracy at update 160. Report ALT minus MIXED for each seed and the mean of the three paired differences. These are development estimates; no statistical power, final-set confirmation or general advantage is established by their sign alone. Do not silently replace these endpoints with a threshold-crossing result. A threshold that is not reached must be reported as not reached.

Retain all **564 exposed training-packet predictions at updates 0 and 160**, with per-kind accuracy and paired gains, losses and retained-correct counts. These diagnose learning on the supplied course; they are not held-out transfer observations. Avoid adding full-registry intermediate evaluations unless the matched work and resource contract explicitly includes them before launch.

## Retention during different-question teaching

Freeze a separate, no-support parts/reach probe panel and its exact source/query bytes before the run. Assess it at update 160, before further instruction, and after 16 additional eight-item batches. Those batches contain only fixed **definition/context** training occurrences, identically ordered in both arms. They contain no probe packets, parts/reach targets or answer-bearing worked supports. Exclude `edge_account`: its complete edge corrections would directly rehearse tested containment knowledge.

Public source facts remain visible in the further-instruction inputs. The claim is therefore retention of answers during different-question teaching, not retention while the relevant facts are inaccessible. Course maintenance examples are rehearsed training and do not independently establish retention. Checkpoint reload equality establishes persistence of stored state, not this behavioral retention endpoint.

For each arm and seed, report accuracy before/after further instruction, absolute change, the number correct before instruction, retained/lost/gained counts and the fraction of baseline-correct answers retained. Apply the **initial probe accuracy >= 0.5** eligibility rule at update 160. If it is not met, label that arm's retention `RETENTION_UNASSESSED` while still reporting all observed counts. A paired retention contrast requires both arms to be eligible; one eligible arm does not establish a comparative retention benefit. Report parts and reach separately so aggregate competence cannot conceal failure in one kind. No long-delay, broad-capability or protected final retention claim follows from this short intervention.

## Execution entrypoints and admission still required

- `cas_meta2/typed_teaching/course_plan.py::compile_plan` and `course.py::compile_course` provide the two complete source schedules. `course.py::model_packet` supplies the closed public projection; `validate_model_packet` validates it without semantic repair.
- `source.py::freeze_bank`, `compile_source` and `validate_public` support a 64-world bank plus one focused world, with up to ten nodes in a world. `answers.py::compile_query` provides typed parts/reach queries. The correspondence/analogy oracle's four-node limit is irrelevant to this restricted transfer panel and must not be weakened or misreported.
- `input_frames.py::compile_packet` and `tokenization.py::FrameTokenizer.encode_frame` must admit every development/probe packet under the unchanged training-only fit and declared token limit. Refuse overflow; do not truncate, refit on development inputs or filter failed examples silently.
- `learner.py::TypedCourseLearner.predict`, `stage_batch`, `train_sealed_batch`, `export_checkpoint` and `restore_checkpoint` provide the measured learner path. The old constructor's 160-update limit requires an explicit, bounded new admission for the 176-update trajectory; validation branches need separate accounting.
- The existing `worker_contract.py` and `cncm/typed_course_worker.py` admit one source-101 ALT engineering run with fixed material and an older 162-global-update design. They are implementation references, not permission to retag the old receipt or silently run this six-arm study. New exact material/configuration, aggregate work limits, package/source attestation, launch authority and evidence schema must match this protocol before execution.

Freeze the new worker, source package, public schedules/panels, tokenizer, initial-state pairing rules, prediction/scoring joins, endpoints and per-job budget before admitting the first arm. Preserve failed or incomplete attempts with their actual work and costs; do not automatically retry or omit them. Keep each bounded job's timeout, instance deadline, reservation and cleanup proof explicit. A successful pure test, package rehearsal or this document alone is not numerical acceptance.

## Implementation and fixed material

`cas_meta2/typed_teaching/matched_contract.py` admits both full schedules, the 59-question development panel and 96 no-support retention probes. The compact development material is 685,549 bytes, SHA-256 `5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4`; lossless expansion restores the exact public packets, with maximum 28,281 tokens under the unchanged 32,768-token limit. The original public bundle and its original constructor are preserved separately.

`cncm/typed_matched_worker.py` executes one fresh arm, seals each prediction phase before scoring, records condition-independent correction identities, and measures all training, evaluation and replay work. `cas_meta2/typed_teaching/matched_analysis.py` fixes the arithmetic and validates joins before comparing six complete arms. The summary reports all three paired differences. Mean retention is withheld if any pair fails the competence rule; individual counts remain visible.

`aws/typed_matched_launch.py` admits six separately bound one-job authorities, each reserving $7 against the existing $5,000 campaign cap: at most $42 for this planned six-arm study, with no automatic retry. Jobs run sequentially because the inherited provider rejects overlapping campaign compute. Each numerical worker has a 3,300-second bound, with the inherited two-hour instance ceiling and independent shutdown timer. Completion and cleanup must be verified for each job before admitting the next. A failed or incomplete arm leaves the paired comparison incomplete; it is retained rather than silently replaced.
