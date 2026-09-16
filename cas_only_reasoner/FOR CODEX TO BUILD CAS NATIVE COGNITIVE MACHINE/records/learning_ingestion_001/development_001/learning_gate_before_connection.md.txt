# Next learning experiment gate

Status: **RESEARCH_PROTOCOL_ONLY — NOT_AN_ACCEPTED_RUN**.

Source inspection: 2026-09-16. This document proposes the smallest next connection
and measurement. It records no new neural execution, optimizer update, provider
call or spending. Existing runtime and research sources were not changed.

We will know whether teaching improves learned competence after an actual learner
improves on untouched task families, against matched controls, with answer-bearing
memory and tools withheld. A successful parser test, changed checkpoint, lower
training loss, correct symbolic recall or better viewer does not establish that.

## Two different questions

| Question | Current mechanism | Appropriate claim |
|---|---|---|
| Does cube/graph teaching improve a neural learner? | Existing graph encoder, `GraphLearner`, supervised corrections and optimizer | Measured transfer and retention after weight updates |
| Does native 0.6 memory improve arithmetic task execution? | `DerivedMachine`, formal proof checking, stored derived values, freshness checks and parent resumption | Symbolic task correctness, useful reuse, stale-result refusal and work saved |

These are different domains and input paths. The cube bridge is not an arithmetic
memory-to-neural adapter. Native 0.6 can improve the system's assisted performance
without changing neural weights. Its checked consequences remain conditional on
authorized formal inputs; they are not independently established world facts.
Relevant implementation: `cncm/derived_engine.py:70`,
`cncm/derived_verification.py:114`, `:129` and `:175`.

## Evidence that remains unchanged

The completed RDCJT criterion is **NOT_MET, 0 of 3 positive**. Paired R8 minus R1
correct counts were -16, -1 and -11 for seeds 20260912, 20260913 and 20260914.
The retained verification hashes checkpoints as opaque bytes; this inspection
did not load them. Do not add recurrent-depth seeds to rescue that completed
criterion. [E1:3, E1:24, E2]

The subsequent zero-update contrast diagnosis reproduced 109/109 selected
originally-correct practice answers, but scored 47/109 after consistent renaming,
109/109 after harmless reordering and 3/32 after a changed containment relation.
These are retrospective conditional results over the same 30-question practice
set across six learners, not 109 independent unseen problems. They motivate
testing relationship transfer; they do not identify a proven failure mechanism
or demonstrate that a new treatment works. [E3:8, E3:15]

A later, completed ordered-encoder diagnostic establishes a narrower positive
result: all 96 declared changed-answer pairs separated numerically, while all 32
graph-line-reorder controls retained equal coordinates. The unchanged legacy
encoder nearly collapsed all 96 pairs; only 32 were exactly coordinate-equal.
The run took zero optimizer updates and zero learner forward calls. This is a
measured encoding repair, not trained transfer, universal collision freedom or
an explanation of every earlier error. Its independent recount checks retained
vectors; projection stability is agreement of recorded digests because projection
bytes were not separately exported. The legacy checkpoints and negative results
remain unchanged. [E5:3, E5:15, E6]

The structural supply audit is **FREEZE_NOT_READY**. Its 96 face-family IDs contain
only six directed topologies, each present in train, development and final splits.
The old RDCJT panel has 16 already examined root families. The wider enumerator
has 47 potential topologies after conservative exclusions, but these are not yet
a frozen, demonstrated-unexposed panel; its 8–10-node envelope also differs from
the 3–4-node face corpus. New IDs or renamed labels do not establish novelty.
Historical exposure custody and the supported task envelope must be settled
before choosing final counts. [E4:3]

## Concrete connection gap

`cncm/rpa_cube_adapter.py:467` prepares a closed learner packet and a separate
teacher sidecar. At lines 546–548 it explicitly reports zero neural calls, zero
updates, zero delivered neural lessons and no established competence.
`cache_identity_bound` means supplied identity metadata is present; it does not
mean the real encoder or cache has accepted the input. [S1]

The bridge invokes the unchanged cube compiler. Its `cube_profile._prompt`
writes `Facts ...` and `A contains B` prose. The current graph learner's
`build_encoder` instead looks up the `node` and `rel` tokens and requires
structural line segments. The current cube presentation does not supply those
lines. This is a source-level incompatibility finding, not a new runtime failure
measurement. [S2:442, S3:142, S3:166]
The corrected ordered encoder also requires structural frames, so it does not
make the current Facts-prose export compatible by itself. [S13:49]

A compatible pattern already exists:
`verified_training.public_problem` uses
`cube_node.containment_graph(...).render()` plus the question. Its source
documents the historical Attempt006 failure on handwritten Facts prose.
`record_from_exercise`, `learner_index` and `correction_point` show where the
teacher answer becomes the training-only `encoded_correct_index`.
Its `connection_check` uses a stub and explicitly counts zero actual neural
presentations and updates. Reuse the pattern; do not relabel that stub as learning
or claim the new RPA export has already entered a learner. [S4:76, S4:103,
S4:240, S4:249, S4:315]

The next candidate must explicitly use the existing opt-in
`cas.graph-ordered-problem-encoder/0.1` profile equally in every teaching arm.
Do not route a new relation-learning comparison through the known lossy legacy
problem pooling, or silently load a historical checkpoint under the new encoder.
`ordered_encoder.build_ordered_encoder` wraps an already-built frozen encoder,
reuses its tokenizer/projection/option path and replaces `encode_problem`.
`profile_identity` and `validate_checkpoint_identity` bind the exact tokenizer,
projection, width, permutation seed and algorithm; they mark legacy checkpoint
compatibility false. [S13:131, S13:154, S13:171]

The learner already has the required injection hook:
`build_graph_training_framework(..., encoder=ordered_encoder)` stores the supplied
encoder, and `GraphLearner` uses `framework.encoder['encode_problem']` for both its
initial training cache and unseen prediction inputs. No `GraphLearner` rewrite
is needed to select the wrapper. A NEW candidate integration path is still needed
to bind the cube records, construct that encoder explicitly on the worker, admit
matching checkpoint/optimizer identities, and run the real smoke gate. Source
compatibility is not an observed cube-to-ordered-learner training run.
[S3:59, S3:246, S3:371]

## Smallest next code change

Add one versioned candidate ingestion adapter, with focused boundary tests,
leaving accepted sources unchanged. It should:

1. Revalidate the source-bound cube document and construct the existing
   `Graph.render()` presentation from its exact declared graph. Preserve
   question meaning and the ordered unmarked options. Fail on unsupported,
   lossy or ambiguous rendering.
2. Bind a new input ID to the actual public bytes, ordered options and actual
   tokenizer/ordered-encoder/checkpoint context. Construct the ordered wrapper
   explicitly through the existing injection hook and verify its complete
   profile in every arm. Preserve the original export's identity
   as provenance, rather than pretending changed bytes retain its identity.
3. Build a private training registry with the checked teacher target mapped to
   the correct encoded option. Pass only the closed public packet at prediction.
   The target reaches `GraphLearner.step` as the cross-entropy label; it does
   not become a prediction or a feature. [S3:297]
4. Enter `trainer.run_training` with those records and retain
   `scope_parameters`, parameter snapshots and containment checks.
   `trainer.launch` has no custom-record injection argument and selects its
   registered dataset; merely passing a new learner factory is insufficient.
   `trainer.evaluate_sealed` likewise builds its registered old dataset.
   A thin candidate evaluation path must use the newly frozen public panel.
   Existing `candidate_experiment.launch/evaluate` shows record-injection
   and measurement boundaries, but its historical conditions and panels are not
   automatically the new experiment. [S5:79, S5:122, S5:195, S5:250, S6:57, S6:142]

No new neural architecture or broad training framework is needed for this first
connection. Dataset, checkpoint/optimizer lineage, schedule, worker and resource
bindings remain separate open gates.

## No-answer-leakage gate

The prediction allowlist is exactly `record_id`, `public`, `encoded_options`;
any operation metadata needed by reporting stays outside the model call.
Private answers, encoded target indices, witnesses and answer-derived IDs or
choice ordering must not cross it. Audit the executed path, not just the export.

The inherited `trainer.prediction_input` removes only `correct`, while
`adapter.public_records` also returns `encoded_correct_index`.
Current `GraphLearner.predict` does not read that index, but a new experiment
must use the stricter allowlist instead of inheriting this broad boundary.
[S5:243, S7:155, S3:371]

Required checks:

- Swap or remove private target data while keeping public task content fixed:
  inference bytes, IDs, option order and encoder inputs must remain unchanged.
  Target-dependent option filtering, truncation and teacher-shaped metadata fail.
- Use fresh IDs for changed public bytes. Prove cached and on-demand encoding
  agree for identical bytes; demonstrate that a changed question cannot reuse an
  old cached vector under an inherited ID. [S3:246, S3:320, S8:222]
- Keep reference solvers and teacher checkers outside neural inference. Seal all
  predictions before evaluator-private targets are opened.
- Fit the tokenizer on training material only. Keep final families, checkpoint
  selection and curriculum decisions separate. Freeze test labels and receipts
  so failed attempts remain visible.

The broader teaching-cycle code supplies a useful evidence pattern:
`evaluation.export_public` and `score_packet` separate public prediction
material from private scoring. Its `BindingLearner.teach/predict` and
`TrainingSession` are a different existing program-binding path with
CAS/generic × aligned/ordinary arms; they are not already connected to this cube
adapter. Even its exposure ledger distinguishes delivered presentations from
learned skill. [S9:423, S9:369, S10:188, S10:241, S11:23, S11:86, S12:52]

## Mechanical smoke gate, then matched experiment

First prove the smallest real execution path on a bounded candidate worker:
source bytes → compatible encoder input → training-only loss target → permitted
parameter update → retained checkpoint → public-only prediction and private
score. Capture actual parameter changes and unchanged excluded parameters,
checkpoint/optimizer identities, every input identity and actual work.
A smoke pass means the connection works; it is not an improvement claim.

Then freeze topology-separated training, development and final families, a
retention panel, paired seeds, budgets and the success rule before final scores.
Use a development-only pilot to choose a feasible sample size; preserve it as
exposed material. Publish a matched multi-seed comparison on untouched families.

The smallest useful comparison is ordinary graph teaching versus one precisely
defined CAS prerequisite/contrast teaching sequence. For a first test, change
only ordering/grouping of the same public lesson multiset and corrections.
If adaptive selection is later used, log actual exposures and provide a matched
exposure control. Hold learner initialization, tokenizer/encoder, allowed
parameters, examples, supervision and compute limits constant.

A plain-instruction arm can be added only if it defines a distinct supported
presentation or teaching policy with equal information. If its actual bytes and
policy equal the ordinary-graph arm, it is the same control. The present encoder
does not support a prose-only control. UI geometry or renamed labels alone do
not define a machine-facing treatment. The old trainer identifies its conditions
as `prompt_framing_only`, not a CASformer-versus-generic architecture comparison.
[S5:29]

The primary endpoint is paired before/after held-out topology/family accuracy by
operation, and its gain over the matched control. Report seed-level results and
family-clustered uncertainty; multiple views of one graph are not independent
families. Predeclare the minimum useful effect and retention tolerance rather
than choosing them after viewing final results.

Secondary checks: old-task retention, consistent-renaming accuracy, harmless
reordering invariance, correct changed-relation answers, and all six option-slot
permutations. A changed answer is not enough when a relation changes: it must
become the correct answer. Existing `contrast_probe` transport helpers are
reusable, but its historical correctly-answered-only selection is not an unbiased
final transfer panel. [S8:152, S8:222, S8:239, S8:285]

## Memory-assisted performance and cost

For any later memory-enabled neural experiment, evaluate the same novel tasks
both with memory available and with answer-bearing memory/tools withheld.
Keep task facts that define the problem available in both conditions, and keep
final targets out of retrieval. Report tool-assisted accuracy separately from
competence retained in the learned parameters. Better lookup alone is useful
system behavior, not evidence of neural learning.

Test native arithmetic 0.6 separately against memory disabled and an ordinary
dependency-aware cache with the same authorized facts, checker access and work
budget. Measure correct task completion, exact parent resumption, stale/conflicting
source refusal and total work. This is not the cube/graph neural experiment.

Account for retrieval, proof checking, failed work, source admission and encoding
as well as forward/backward calls, input tokens, optimizer updates, wall time
and GPU time. Equal update counts alone do not establish equal compute.
Distinguish measured totals from proxies; existing teaching-cycle step-time
receipts explicitly exclude some admission, journal and provider overhead.
[S11:37, S10:20]

## Source locator and byte pins

Captured homebase:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/vision-next/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE
```

Below, `HOME/` is that exact directory and `R/` is
`HOME/research/CAS_META_2_COMPOSITION/`. Line references in this document refer
to the inspected source bytes, not a future revision.

| ID | Exact path within the captured root |
|---|---|
| E1 | `R/records/rdcjt_handoff_20260916/HANDOFF_STATUS.md` |
| E2 | `R/records/rdcjt_handoff_20260916/post_fix_verification.json` |
| E3 | `R/records/graph6_contrast_001/RESULT.md` |
| E4 | `R/records/structural_supply_20260916/post_fix/REPORT.md` |
| E5 | `R/records/ordered_encoder_001/STATUS.md` |
| E6 | `R/records/ordered_encoder_001/independent_recount_001/recount.json` |
| E7 | `R/records/ordered_encoder_001/receipt_cas-meta2-orderedencoder-20260916064137-e47349be/collected/results/result.json` |
| S1 | `HOME/cncm/rpa_cube_adapter.py` |
| S2 | `R/cas_meta2/graph_teaching/cube_profile.py` |
| S3 | `R/cas_meta2/graph_teaching/real_framework.py` |
| S4 | `R/cas_meta2/graph_teaching/verified_training.py` |
| S5 | `R/cas_meta2/graph_teaching/trainer.py` |
| S6 | `R/cas_meta2/graph_teaching/candidate_experiment.py` |
| S7 | `R/cas_meta2/graph_teaching/adapter.py` |
| S8 | `R/cas_meta2/graph_teaching/contrast_probe.py` |
| S9 | `R/cas_meta2/teaching_cycle/evaluation.py` |
| S10 | `R/cas_meta2/teaching_cycle/gpu_adapter.py` |
| S11 | `R/cas_meta2/teaching_cycle/runner.py` |
| S12 | `R/cas_meta2/teaching_cycle/controller.py` |
| S13 | `R/cas_meta2/graph_teaching/ordered_encoder.py` |

The ordered diagnostic ran source commit
`e47349be13ee5449d31ae8d5cc3962ae2571ba15`, job
`cas-meta2-orderedencoder-20260916064137-e47349be`. Its retained archive is
`R/records/ordered_encoder_001/package_e47349be/source.zip`, SHA-256
`57b17ab62301a4f026cde31fe54bec7e3988ee26f08a54e8072b1b6f6e167a0c`.
E6 identifies the exact result, measurements and saved-vector files and recounts
their gates. These historical receipts do not certify a new training run.

SHA-256 values below were read directly from retained files during this
inspection. They identify bytes, not authentic execution or experimental success.

| ID / source | SHA-256 |
|---|---|
| E1 | `80e116108ace5f210582e9d42cbd498a7a885ff13db4ba9200ba0f5b92de1b20` |
| E2 | `7259d8472079ce140d462a9524690430ffba1033340a7b84aa4de08dadac2ef0` |
| E3 | `905b7890db014e334b6ebd6aee63ec726ecb08509681a073908778177d455c52` |
| E4 | `698cae08e477cd366e3d1b4009dec386c4ae0acd6a06398c9542ebe010b2820b` |
| E5 | `854d8b77e6e6b0cbcf2fac8e9923b947a302f42231070f1cba3eeac9dabba966` |
| E6 | `5776af4a15e60a43a3bc9378a86e04331a28325aeafa618ec2da99b4a097f92d` |
| E7 | `a863dfd1c7b4eed485ca687d71ff925d5c3a011a64097795836a1ed8caee8ad7` |
| S1 | `00d4bdd06109dfa3324da548b37d5b10c6b117256d95f98eb875aa95938e1e62` |
| S2 | `08493344a5daff10e2fcaed5a1711cdf5299a7fa3e332f5efb63a75e5ac8bfef` |
| S3 | `82c177e8f70e6931d90a79b65defe9fe6848cce6ab690c67f890b12c4799cd3c` |
| S4 | `0d70665b5385bf0e1381ba571b9f287bec3f1e9cea8c07868e26f5a9e652ba8a` |
| S5 | `e3302b90030dd9da048d6aacdc1c806967455f8a51435665eae3489d25066bd4` |
| S13 | `670fb5acc42a9aa13fd7b1ff3d91bdd1ded38399833095293bec572313bc1bc4` |
| `HOME/cncm/derived_engine.py` | `2bc96b78a77e1af2ebe368bd9dc84e49d1553500815e3e5c8c07795ed995701b` |
| `HOME/cncm/derived_verification.py` | `67a8452e71ebfcb82e1df42a545c90a2e78d7afa058aa1a2166c1d149071239a` |
