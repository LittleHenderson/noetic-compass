# Typed teaching decoder design v0.1

Status: **PROPOSED DECODER; DRAFT PURE GRAMMAR WRITTEN; NO NUMERICAL ACCEPTANCE OR WORKER ADMISSION.**
This document changes no executable code. No model, tensor package, provider, or
final-target construction was executed for this design.
The current syntax authority is `cas_meta2/typed_teaching/answers.py`, using
`cas.typed-teaching-query/0.1`, `cas.typed-teaching-answer/0.1`, and
`cas.typed-teaching-answer-space/0.1`. Source validation and teacher integration
still require their own verification; this document does not claim it.

## Boundary and proposed reuse

Keep the complete complementary course: all six faces, 1,152 logical
presentations, 160 update groups, supports, maintenance, and scheduled recurrent
depths. Cache deduplication must not delete repeated presentations. The legacy
three-choice path and its target-conditioned construction remain a separate
profile; this proposal does not admit them to an unbiased study.

Reuse the registered 64-wide `^6` core, its parameter scope, and
`recurrent_cjt.recurrence.run_passes`. Replace `GraphLearner`'s three option sums
and target-reading scoring interface with a **fixed-slot typed decoder**. This
is a new input/output profile requiring fresh matched initialization, not a
compatible interpretation of an earlier checkpoint.

For each publicly declared output slot, combine the scoped source encoding with
a separately versioned frozen field-query vector. Its identity includes field,
world scope, and slot coordinates. Run the same core at the scheduled depth,
starting from fresh zero state for every slot. Score frozen symbol rows by dot
product. No new learned head or teacher-supplied prefix is proposed. Exact query
composition, scale, readout normalization, seed, and actual bytes must be pinned
before numerical execution; finite vectors and distinct symbol rows require
worker verification. No collision-free or learning claim follows from this design.

## Public references and output slots

The proposed source envelope has the complete declared focus world and a full
query-independent bank of at most 64 worlds: at most 65 distinct worlds total,
each with at most ten nodes. Node aliases `n0..n9` are assigned by the declared
public label order and are always scoped by public world identity. Bank aliases
must resolve through the complete public bank table. No valid-answer filtering,
selected-partner insertion, reachability pruning, or hidden-target ordering is
allowed.

| Grammar answer | Proposed model decisions and decoding |
| --- | --- |
| `role_set` | Six PRESENT/ABSENT slots, one for each role ID 1..6. Serialize the sorted selected subset and derive status from its cardinality: INSUFFICIENT for zero, UNIQUE for one, AMBIGUOUS for more. Status reflects the predicted set, not a teacher check. |
| `definition` | Three selections: a focus-world node for `whole`, a `kind_ref`, and a `function_ref`. Both declaration inventories include **every public world**, up to 65; do not restrict them to the focus world or generate literal answers. |
| `context` | One `setting_ref` from all public worlds plus one participant-membership slot per public focus node. |
| `analogy` | One selection over **all** bank world IDs plus null: up to 65 candidates. Any source-checked valid world may be correct; null expresses no match and is always syntactically allowed. |
| `correspondence` | One target-node score vector per source node, plus an independent NO_MATCH/MAPPING score. `correspondence_candidates` offers NO_MATCH and every syntactic bijection: up to 25 candidates at four nodes. A mapping score combines its node logits with the MAPPING score; relative score normalization must be pinned before execution. NO_MATCH has its own score, not a checker-controlled fallback. |
| `parts` | One membership slot per public focus node. Serialize the selected node set canonically, including the empty set. Direct containment is the current rule; a shared-part supplement needs its own explicit query/rule binding before admission. |
| `edge_account` | One membership slot for **every ordered focus-node pair, including self-pairs**, up to 100. Incorrect edges remain available. Serialize selected pairs as sorted, unique `{source,target}` records under `complete_edge_set_lexical_serialization_v1`; this is not temporal/process order. |
| `reach` | One categorical choice: DIRECT, ABSENT, or VIA with any public focus node. Serialize `{state,via}`, with null `via` outside VIA. Require `first_direct_constituent_lexical_v1` or `bfs_immediate_predecessor_lexical_v1`; no default silently merges their meanings. |

Ten-node correspondence is a grammar possibility, **not** supported by the
proposed numerical prototype: ten factorial candidates are not the 25-candidate
case. Admit the complete current course only after a pure sizing pass establishes
that every correspondence item fits the four-node bound. Do not drop a face or
silently substitute a smaller course when a bound fails.
Unequal source/target node counts yield only the syntactic NO_MATCH candidate;
report such forced decisions separately from learned choices. The target world
is a public query argument drawn from the full bank, not a teacher-selected match.

One concrete proposed readout has **90 fixed symbols**: `PRESENT`, `ABSENT`,
`DIRECT`, `NO_MATCH`, `MAPPING`; `N0..N9`; `VIA_N0..VIA_N9`; and `W0..W64`.
Its frozen matrix is `90 x 64`. World aliases follow sorted public world IDs.
A declaration field's selected `Wj` serializes to that world's `/decl/kind`,
`/decl/function`, or `/decl/setting`; an analogy choice serializes to that world
ID, or null for NO_MATCH. Node symbols resolve within the public field's explicit
focus/target scope. Bank membership is the only world mask for analogy, not
semantic similarity. Role IDs and ordered node pairs are field-query coordinates,
not additional output symbols. These aliases are numerical-proposal details;
the grammar's authoritative wire values remain full scoped references.
No EOS, target-length mask, or teacher-forced prefix is needed for fixed slots.

## Loss, inference, and measurement

Prediction accepts public source, public question, decoder profile, and weights
only. Grammar constraints may enforce reference ranges and syntactic bijections.
They must not enforce edge preservation, choose a reachable node, search for a
correct analogy, repair a wrong answer, or select an intermediate depth using a
checker. Seal the decoded answer and logits before releasing private targets.

For a public candidate universe `C` and privately checked acceptable set `V`, use
the valid-set negative log probability:

`loss = logsumexp(score(c), c in C) - logsumexp(score(v), v in V)`.

This handles multiple correct analogy worlds and correspondence automorphisms.
For mappings, `C` contains NO_MATCH and all syntactic bijections; only the teacher
constructs `V`, after prediction. Analogy likewise includes null. Never mark an alternative valid mapping wrong merely
because the source stored one representative. Membership slots use binary
cross-entropy. Semantic no-match cases have the corresponding sentinel as a
valid answer. An actually empty teacher-valid set is a checker/contract failure,
not a reason to inject an answer into the public candidates.

Average slot losses within each semantic field, then fields within each logical
task, then tasks within the existing batch. Make one optimizer update per batch.
Record raw losses and, for comparison across different alphabet sizes, a
predeclared normalization by `log(|C|)` using the **public** candidate count.
Singleton/forced fields need a separate count and no division by zero. Do not
weight by hidden answer length or positive-label count.

Primary accuracy is whole-answer validity/exact set agreement as specified by
the grammar. Also report per-face/per-operation accuracy, syntax failures,
membership precision/recall, and field accuracy. Report all-ABSENT and all-PRESENT
membership baselines. All-PRESENT now means all node pairs, not just the supplied
edges, so it generally fails. A separate visible-edge-copy baseline can still
solve a complete-edge account without learned recomposition; it must never be
inserted into the model's inference path. Full-world declaration inventories
remove singleton candidate restriction, although source copying can remain easy.
Keep all curriculum presentations without calling forced outputs evidence of
learning. Legacy three-choice accuracy/loss is not directly comparable.

## Admission work still required

Add pure slot compilation and answer assembly beside the new grammar; a separate
worker-only `TypedCourseLearner` supplies frozen queries/readout, public-only
`predict`, and post-seal loss. Existing `GraphLearner._content_ids`, option sums,
and `scores` are not suitable replacements. Checkpoints must bind source catalog,
reference tables, grammar, slot plan, scoped encoder, readout bytes, tokenizer,
model, optimizer, RNG, and committed course cursor.

Purely compile all 1,152 presentations before execution to measure actual source
tokens, reference counts, output slots, mapping counts, and full six-face
coverage. The current 1,024-token ceiling cannot be assumed sufficient for the
complete bank and declarations. Refuse overflow; do not truncate or prune with
teacher information. The edge-account maximum is 100 binary slots, including
self-pairs. The draft grammar separately bounds focal excerpts at 16,384 UTF-8
bytes and complete answer wire records at 32,768 bytes. These are syntax ceilings,
not measured tokenizer or GPU capacity. Schema and decoder coverage of any
shared-part extension must be resolved explicitly rather than mapped silently
to the direct-parts rule.

Report actual core calls as the sum of slot counts times scheduled depth, plus
all evaluation/reload calls. Equal 160-update schedules do not imply legacy
compute equality. Measure GPU time, peak memory, source encoding and decoding
cost, and forward/backward calls. Match slots, alphabets, losses, source bytes,
fresh origin, and budgets across new-profile arms. Fixed slots avoid
prediction-length-dependent compute, but full-source encoding and multi-slot
training are material new costs. Numeric bounds, full-course coverage, CUDA
behavior, study admission, and learning benefit all remain unverified.
