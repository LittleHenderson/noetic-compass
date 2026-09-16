# Typed teaching semantic review v0.1

Review date: 2026-09-16. Reviewed repository HEAD:
`3c73523fa56d5bd98e075d5fc75c2fbdcd1af205`.

The full six-face course can retain its 1,152 logical events and 160 groups,
provided that ambiguous answers remain explicit. Replacing a hidden answer and
two distractors with a public answer space does not make every task uniquely
answerable.

This is a source and pure-data design review. The new typed interface has **not
yet rebuilt or run all 1,152 events**. Preserving them is an acceptance requirement,
not a completed implementation claim. This review built no final targets,
imported no model or numerical framework, used no provider, and changed no runtime
source. The earlier single-graph smoke does not establish full-course execution,
held-out learning, or an advantage over a matched control.

## Evidence and required course coverage

Locations below are relative to the CNCM repository root. Line numbers identify
the reviewed source, whose hashes are listed at the end.

The retained pure preparation receipt
`records/matched_learning_preparation_001/checks_001/receipt.json`, SHA-256
`f063cccc371db83143faedd30e1c80e939a15c0ee5e3bf58157b25a55961807c`, reports the
following counts for each source schedule seed 101, 202 and 303. This review
recounted its group sizes and operation totals; it did not regenerate a typed
course or select new experimental seeds.

| Existing course quantity | Count |
| --- | ---: |
| Logical presentations | 1,152 |
| Groups / planned optimizer updates | 160 |
| Groups of eight / groups of four | 128 / 32 |
| FACE_APPLY presentations | 800 |
| ROLE_FROM_CONTENT presentations | 96 |
| LIST_PARTS / REACHED_VIA presentations | 128 / 128 |
| Existing unique public inputs / semantic questions | 624 / 252 |

The arithmetic is `128*8 + 32*4 = 1152`. The schedule emits all six recognition
faces each round at `graph_teaching/face_schedule.py:175–188`; its complete round
is at lines 155–201. The underlying paths are
`research/CAS_META_2_COMPOSITION/cas_meta2/`. The complementary compiler adds two
eight-event supplement groups per round at
`complementary_teaching/course.py:137–176`. The inherited foundation and maintenance
counts are in `recurrent_cjt/recurrence.py:64–65`.

New public facts, answer grammar and ambiguity handling will change public IDs,
token counts, and possibly unique-task counts. Do not require the old 624/252
deduplication counts to survive. Require every original event occurrence and
group boundary to remain traceable; deduplicating stored packets must not remove
repeated teaching events. Equal event counts alone do not establish equal
numerical work.

## Role recognition does not have a demonstrated unique-label oracle

`graph_teaching/face_tasks.py:741–750` builds recognition options from the scheduled
face plus two other faces, then assigns the scheduled face as correct. All six
fixed labels remove that answer-conditioned shortlist, but the existing
uniqueness check is insufficient:

- `recognition_is_unambiguous`, lines 673–686, checks prohibited words, cues and one
  possible Face 3/4 conflict.
- Its `_shares_candidate_table` hook, lines 689–693, always returns `False`.
- `compile_episode`, lines 718–799, does not invoke that check.

Recognition prepends the family's containment graph to its commentary
(`recognition_excerpt`, lines 615–648). **`facts_text` contains graph facts only**
(lines 91–93); it does not publish the family's kind, function or setting.
The question must publicly identify the focal excerpt being classified, so
supporting graph facts do not themselves supply a competing Face 5 purpose.

A concrete overlap remains even after focus is explicit. Face 6's commentary is
an `account:` followed by a static list such as `A contains B ; B contains C`
(lines 375–393, 439–441, 648). That is also a description of parts and structural
relationships, the Face 5 role. The static list alone does not establish an
exclusive construction or temporal-process purpose. A hidden scheduled face is
not evidence that all other role labels are false. This is a semantic ambiguity
finding, not a measured count of all ambiguous training events.

Use a fixed public universe of all six role labels. A protected judgment should
bind the focal excerpt and public interpretation rules to an admissible role set
and `UNIQUE`, `AMBIGUOUS` or `INSUFFICIENT` status. If a new public instruction makes
the rhetorical purpose exclusive, record that as a versioned task change. Merely
learning six marker-to-label associations would not demonstrate broad role
understanding.

## Analogy scope needs a public, exact meaning

`preserves_scope`, `graph_teaching/face_tasks.py:290–308`, tests full directed-graph
isomorphism: all nodes and edges must match under a renaming. Its prose scope
builder, lines 269–281, instead describes a small motif and independently chooses
the first sorted direct and indirect constituents. Those choices need not form a
path.

Training family `family:mechanical:05` is a concrete counterexample. The source
constants in `graph_teaching/face_corpus.py:43–50,67,177–179,238–273` give:

```text
Lathe -> Chuck
Lathe -> Tool
Tool  -> Bolt
```

The prose builder selects `Chuck` and `Bolt` and claims `Lathe -> Chuck -> Bolt`,
although `Chuck -> Bolt` is absent. The new interface must derive a real path
witness or state that it compares complete directed graphs. A motif-only task
and a full-graph task need different public rule identifiers.

The old analogy partner is selected by corpus traversal order, not by a proof
that it is the only valid match (`graph_teaching/face_corpus.py:292–323`). A public
bank can contain several valid graphs. Return all eligible matches, accept any
valid match when the request asks for one, or declare a public canonical tie rule.
Do not privately filter the bank down to the old chosen partner and two negatives.

Partner selection searches all 96 families. Combined with domain order and split
assignment (`face_corpus.py:170–171,221–227,250–277`), a container-domain training
family can select an organisational-domain development partner. A training-only
public bank therefore needs an explicit split boundary and fresh answer checking;
it cannot silently reuse that hidden partner selection.

## Correspondence has valid symmetries

`graph_teaching/face_corpus.py:326–355` pairs labels by their latent tuple positions.
That constructs one mapping; it does not prove uniqueness from public relations.
Independent standard-library enumeration of permutations over the literal
`ARCHETYPES` at lines 43–50 gives:

| Directed topology | Valid self-correspondences |
| --- | ---: |
| chain2 | 1 |
| branch3 | 6 |
| diamond | 2 |
| chain3 | 1 |
| pair_shared | 1 |
| fork_child | 1 |

In `branch3`, any permutation of the three leaves preserves all edges. In
`diamond`, swapping the two middle nodes preserves all edges. These counts use
only the six source topology constants, not held-out targets or a learner.

The new request must name public source and target worlds. A checker should test
complete, injective mappings against their declared directed relations and
completeness rules. Accept every valid mapping or use a public canonical rule.
List order or hidden original node positions cannot silently decide correctness.
Matching labels in different worlds must remain separate, scoped references.

## Supply missing facts without inventing process order

The old FACE_APPLY prompt publishes graph facts and a request
(`graph_teaching/face_tasks.py:588–612`), while the candidate answers can supply
information absent from that graph. Definition/function use source fields at
lines 197–205 and 234–246; context uses setting/participants at lines 214–266;
correspondence uses a partner's labels at lines 326–336.

A public source interface should explicitly declare kind, function, setting,
participants and both worlds where required. Distinguish authored facts from
presentation-derived conventions, such as selecting the first labels as
participants. Commit the complete supplied bank to public identity independently
of teacher answers. Scope any completeness assertion to the supplied snapshot;
it is not an assertion about the outside world.

Face 6 currently sorts containment branches, and calls procedural-domain content
ordered (`face_tasks.py:375–393`). Sorting edges or belonging to a procedural
domain does not supply temporal order. `process_order = null` must support only
an order-insensitive edge account, or an explicit insufficient-information result
for an ordered request. Preserve declared process constraints only when the
public source actually contains them.

## Proposed answer and acceptance rules

These are requirements for the new version, not descriptions of admitted runtime
behavior or a final experimental protocol.

1. Compile public source, focal request, answer grammar, bank membership and public
   IDs before private checking. No private answer, negative selection, ambiguity
   set or chosen mapping may filter these public bytes.
2. Keep role labels fixed at all six. Separate public reference validity from
   semantic correctness: every offered reference must exist, but existence must
   not mean that a teacher preselected it as a valid answer.
3. Use set-valued correctness or a declared canonicalization rule where several
   answers satisfy the request. For a role-set request, exact-set scoring can
   distinguish correct ambiguity from selecting every label. For a one-answer
   request, accept any supported answer and report ambiguous cases separately.
4. Bind protected judgments to public source/request digests, the versioned rule,
   admissible answers and witnesses. Hashes establish byte identity, not source
   authorship, world truth or independent semantic proof.
5. Preserve every event and all 160 groups, including ambiguity and insufficient
   information. Filtering such cases, zeroing their losses or replacing them with
   filler would change teaching and must not be reported as full preservation.
   The existing three-choice cross-entropy path cannot be assumed to support a
   new answer grammar or set-valued loss without separate validation.
6. Across matched arms, compare the complete public presentation multiset,
   protected corrections, group membership, tokens/options processed and observed
   work. Keep event lineage private where it would reveal the hidden face.

Required adversarial cases are: the Lathe false path; `branch3` and `diamond`
mapping ties; several valid public-bank analogies; static Face 5/6 overlap;
supporting-fact additions outside a fixed focal excerpt; null process order;
repeated labels across worlds; non-training bank entries; and private-target,
legacy-partner or distractor mutations that leave public bytes unchanged.
An end-to-end coverage test must retain all 800 application, 96 recognition and
256 graph events without silent omissions. No all-event ambiguity census, new
typed course execution, fresh model, matched learning result or final-panel result
is claimed here.

## Bounded review of the new pure interface

The subsequent implementation review covered
`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/source.py` at SHA-256
`d11b406faab7433739b1dc181e9c557772959ebff2e16538a42a5efee533d1f8` and
`answers.py` in that directory at SHA-256
`4d4cf21b65914c5b6878b58a52ab3cfe2f8864b319a3bb5ad1b95c6780686e5c`.
These are reviewed prototype bytes, not a claim that later edits inherit this
review.

Source inspection found no teacher-based bank filtering. Source worlds publish
their declarations uniformly, use world-scoped references, declare complete
supplied containment snapshots, and leave temporal `process_order` null. The
answer module separates syntax from correctness: six fixed role IDs, the whole
analogy bank, all scoped correspondence nodes and all possible node pairs for an
edge account. Reach rules are explicit. Bounded correspondence enumeration is
limited to four nodes even though source syntax supports up to ten.

A small independent in-memory probe, with numerical/model/provider/network
imports denied and bytecode writing disabled, checked the following on unchanged
before/after source bytes:

- The literal-only constructor creates 64 source worlds from the mechanical,
  grammatical, procedural and container domains. It constructs no answers or
  final targets.
- The public analogy bank retains all 64 worlds; null and same-focus candidates
  pass syntax even though they need not satisfy the analogy rule.
- All six role IDs are present, and `[5,6]` with `AMBIGUOUS` survives canonical
  answer encoding and decoding. This checks representability, not the truth of
  that role judgment.
- A four-node edge space has all 16 node pairs, including self-pairs; a wrong
  self-edge passes syntax. Correspondence supplies all 24 bijections plus
  `NO_MATCH`, and each passes syntax.
- Every generated source world's process order is null, and completeness is
  explicitly limited to the supplied snapshot.

An earlier probe attempt stopped at its final source-stability assertion while
the modules were being edited. The subsequent probe used unchanged bytes and
passed. Neither probe rebuilt the 1,152-event course. No runtime files or test
files were edited by this reviewer.

This interface does not yet implement a semantic checker, a full-course compiler,
a new loss/scoring path or learner execution. Also, an arbitrary received bank
is checked as caller-supplied content; its declared training membership and
self-consistent hashes are not authenticated source custody. Canonical training
construction and the eventual pinned harness must establish the narrower
experiment-specific source boundary.

## Reviewed source identities

All source paths in this table are under
`research/CAS_META_2_COMPOSITION/cas_meta2/`.

| Source | SHA-256 |
| --- | --- |
| graph_teaching/face_tasks.py | `9065997e63fca65318016f844578234fb60ebdc0d91b48e12b2836272fb7a3ab` |
| graph_teaching/face_roles.py | `463227f82faa2409dbd156481ae4dbc736c627d73510333f61df5f75a6c2fdc3` |
| graph_teaching/face_corpus.py | `69820d38be4981cfe3684306d86ab8c19e55d2d0dc1e6dc3a4267609dc7b0507` |
| graph_teaching/face_schedule.py | `d9174d9905af7b6cbb8dbe6fa80c695fbc6a48a65c7a08d837eca2ecedb5b2c1` |
| complementary_teaching/course.py | `dd6cc2687cabc8354beda5993d82f634d8350d288b258a5d9bf38c9488082ec0` |
| recurrent_cjt/recurrence.py | `45278c0455b042e5515a73eb629a0ae90c31d41ae373ad3527e11a9cae49d17c` |
