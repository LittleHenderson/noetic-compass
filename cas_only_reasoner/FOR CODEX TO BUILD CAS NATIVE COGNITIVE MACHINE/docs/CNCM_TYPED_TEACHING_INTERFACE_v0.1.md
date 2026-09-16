# Typed teaching source and answer interface v0.1

Status: pure source and syntax extension. This is not a rebuilt full course, a
semantic teacher, an implemented neural decoder, or an admitted learning study.

The input-v0.2 CUDA smoke established the teaching/reload connection on six
exposed questions. It did not settle whether the teaching method improves
learning. The next comparison also needs answer construction that does not
select its choices from the teacher's correct answer.

## What this extension implements

The separate `cas_meta2/typed_teaching/source.py` reads only the four training
domains' literals and constructs 64 training families. It never imports or calls
the old all-split corpus, task, or course constructors. A caller freezes the
complete public bank before choosing a focus. Every focus receives all supplied
worlds, declarations and containment facts; no matching partner or traversal
result is selected for the learner.

Each world supplies its declared kind, function, setting, domain, labels and
contains graph. Participants are explicitly marked as a presentation convention
over the first three source labels. They are not independently verified facts
about a real object. Snapshot completeness is public. Node references are scoped
to world identity. The bank admits at most 64 worlds, the focus/bank union at most
65, and each world at most ten nodes.

Source syntax and hashes do not authenticate authorship or world truth. The
generic caller interface accepts caller-asserted training sources; it does not
certify an unbiased bank. The dedicated training constructor is the audited
route to the current 64-family bank. Private family identifiers, rendering labels
and source pins are excluded from the public projection.

`answers.py` binds a public question and explicit rule to a public source digest.
It offers fixed answer forms:

| Kind | Answer form and boundary |
| --- | --- |
| Role recognition | A subset of all six role IDs, with UNIQUE, AMBIGUOUS or INSUFFICIENT status determined by subset size. The focal excerpt is explicit; this module does not determine its correct roles. |
| Definition | A whole-node reference and kind/function declaration references. All worlds' declarations remain available. |
| Context | A setting reference and a set of focus-world participants. |
| Analogy | Any ID from the complete public bank, or no match. No shape-based filtering occurs. |
| Correspondence | A scoped node bijection, or NO_MATCH. Graph preservation is not checked at inference. |
| Parts | A canonical set drawn from all focus nodes, including the empty set. |
| Edge account | A canonical set drawn from every focus-node pair, including incorrect and self-pairs. Serialization order does not mean process order. |
| Reach | DIRECT, ABSENT or VIA a focus node, with an explicit first-direct-constituent or BFS-immediate-predecessor rule. Self-reach requests are refused. |

Malformed answers, foreign references, duplicate set members, unknown fields and
noncanonical wire bytes are refused. Well-formed wrong answers remain admitted.
This distinction is required: an interface that repairs mistakes would hide the
learner's actual performance.

The optional pure correspondence candidate enumerator offers every syntactic
bijection and NO_MATCH. It admits at most four nodes (25 candidates), even though
the general syntax admits ten. It does not search graph edges for the right
mapping. Larger numerical correspondence work remains unadmitted.

## Why the next compiler needs new semantics

Review found that the old selected-answer menus can hide ambiguity. A static
edge account can describe both structure and recomposition. Training-bank
analogies can have several correct partners, and symmetric graphs admit several
correct maps: six for the four-node star and two for the diamond.

Old analogy helpers can choose a development-domain partner despite an outer
training selection. Some explanatory path text also joins a direct child and an
indirect node without verifying that particular path. Finally, sorting contains
edges does not establish a temporal process. All new source worlds therefore
declare `process_order: null`.

These findings do not rewrite historical results. They prevent old private
targets and prose from silently becoming the new teacher. See the separate
semantic review and decoder proposal under
`research/CAS_META_2_COMPOSITION/docs/`.

## Remaining work

Reconstruct all 1,152 logical presentations, 160 groups, supports, maintenance
and six face incidences through this new public contract. Keep a lineage row for
every old event; do not drop ambiguous or unsupported cases. Publish any changed
question meaning. Face 2 interactions and any genuine temporal process task
need an explicit source/rule before claiming full semantic parity.

Build an independent private checker from sealed public facts. Accept every
valid analogy or correspondence, and specify role ambiguity handling. The
current module validates syntax only; it does not provide training corrections.
Freeze the public compiler and compare its source information and lesson
multisets between arms before releasing targets.

Measure complete token/slot/forward/backward work, implement the new decoder
and fresh paired initialization, and validate the scoped encoder numerically.
The full bank changes input size and answer difficulty; legacy three-choice
scores and the old 1,024-token budget cannot be reused without measurement.

Only then freeze the matched multi-seed learning study, including speed,
untouched-family transfer and retention after intervening teaching. The present
ordinary dependency-graph schedule equals component-then-whole, so it is not a
distinct CAS-specific treatment. No learning gain is claimed here.
