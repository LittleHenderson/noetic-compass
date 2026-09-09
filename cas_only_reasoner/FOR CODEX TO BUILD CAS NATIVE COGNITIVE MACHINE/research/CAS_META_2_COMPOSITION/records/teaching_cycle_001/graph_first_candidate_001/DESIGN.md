# Graph-first teaching candidate — design record (owner-corrected)

Status: **DESIGN CANDIDATE** — pure implementation and deterministic tests only.
No AWS launch, no reservation, no neural run. This candidate complements the
pending binding-fit learning-path diagnosis; it does not replace it, and it
does not modify any accepted model, trainer, ledger, or existing campaign file.

## 1. What the memory graph contains: FOUR pieces (owner correction)

The owner corrected the earlier five-piece sketch: **branches and connectors
are the same**. A branch is not a separate kind of thing — it is a connector
viewed from the item it leaves. The choices available from an item are exactly
that item's outgoing connectors; following a branch means following a
connector.

| Piece | Plain-English meaning |
|---|---|
| **Node** | An identifiable item in memory: an object, idea, event, procedure, or result |
| **Node contents** | The information stored about that item: its fields, its components, and its relationships |
| **Connector** | A named relationship between items. **This is also the branch**: the set of outgoing connectors from an item IS its branch structure |
| **Intersection/commonality** | A shared property, component, dependency, or other relationship connecting different items |

The executable rule: `Graph.outgoing(node)` — the branch choices — returns the
node's outgoing connectors, and there is no other branch data anywhere in the
model. A test locks this identity.

## 2. Core invariants

1. **Node identity is separate from node contents.** Renaming a node changes
   nothing; changing its contents may change which answer is correct. The
   learner must follow the information, not a familiar position or name.
2. **Connectors carry explicit names.** Kinds such as `has_color`,
   `has_shape`, `has_value`, `requires`, `contains`, `triggers`,
   `produced_by`, `shares`. An arrow's direction alone does not establish
   causation.
3. **Derived connectors are never stored.** `shares` (commonality) and
   `produced_by` (the result side) are computed by the deterministic reference
   checker from the stored facts; the learner's graph never contains them.
4. **No answer edges.** Nothing in the graph marks the correct selection. The
   reference checker computes it deterministically; it never smuggles the
   answer into the structure the learner sees.

## 3. Connector semantics (executable meanings, anti-drift preserved)

| Connector | Meaning | Exercised in lesson 1 |
|---|---|---|
| `has_color` / `has_shape` / `has_value` | object → stored property value (read what is inside) | yes |
| `requires` | request → requirement (request requires color=red) | yes |
| `triggers` | request → object (^8: what brought this idea into consideration — associative triggering, NOT deduction; the checker never uses triggers as matching evidence) | yes |
| `contains` | procedure → its steps/inputs/return relationship (idea containing ideas; recursive extension) | schema-defined, not exercised in lesson 1 |
| `shares` | DERIVED from field equality; sharing implies neither identity nor causation | derived only |
| `produced_by` | DERIVED: the selection result produced by the follow operation (^9 landing) | derived only |

## 4. The three Noetic questions organize what the learner does

| Noetic perspective | Question to teach | Executable operation |
|---|---|---|
| ^8 Above / Cause | What brought this idea into consideration? | read the `triggers` connectors (associative, not reasoning) |
| ^6 Male | What ideas or parts are inside it, and how are they arranged? | read the node's fields and its outgoing connectors |
| ^9 Below / Effect | What idea or result follows from the operation we performed? | the selection the checker derives (`produced_by`, never stored) |

An Effect of one step supplies the Cause of the next: ^8 and ^9 are the source
and result sides of the same transition — not two unrelated relationships.

## 5. The golden thread

> Across different examples, the same relationship keeps determining the
> answer.

The generator varies node names, positions, contents, palettes, and option
order; the derivation recorded by the reference checker names the same
relation kinds every time. A test asserts the derivation labels are identical
across differently-labeled families.

## 6. First lesson: tiny, reusable, built on the binding problem

Object nodes carry `color`, `shape`, `value` fields; a request node names
required properties; several candidate objects are presented. The learner must
(1) read what is inside, (2) identify the connection, (3) follow the
connection, and (4) select the object satisfying the request. The reference
checker verifies the choice. The graph supplies the public structure only —
never an edge labeled "this is the answer."

Three recurring activities (repeated guided phase stays intact):

1. **Read what is inside** — which field gives which value; which node
   contains this value; distinguishing a node's name from its value.
2. **Identify the connection** — name the relation kind that holds, with
   nearby alternatives so the learner must attend to the KIND of connection.
3. **Follow the connection and use the result** — one hop, then two hops; a
   changed-request variant ("the request changes to blue and square — which
   object now?").

The same graph information serves both the CAS arm and the generic comparison
arm. CAS framing adds the three Noetic questions; generic framing is plain.
Both framings are computed from identical graph bytes and share the identical
reference answer (test-locked).

## 7. Dataset discipline (owner's standing rules applied)

- `train` and `practice` are the only splits any future learner may see.
- `validation` and `test` are **sealed and disjoint**: generated once,
  byte-fixed by receipt, and never read by any teaching path in this package.
- Records are deduplicated by content hash; answers are included for
  supervised correction (this synthetic candidate is not the protected
  final-test material of the binding task).

## 8. Boundaries

- No claim that this candidate fixes the poor fitting; it complements the
  pending binding-fit diagnosis (attempt 004 authorization request remains
  awaiting owner signature).
- No neural execution here; pure deterministic code and tests only. Any
  claim-bearing training run would be a separate, owner-authorized AWS job.
- No modification to accepted models, trainers, the campaign ledger, frozen
  negatives, or any file owned by another lane.

## 9. Owner refinements recorded (2026-09-09)

1. **Branches and connectors are the same.** Four pieces, not five; the
   branch structure of an item is exactly its outgoing connectors
   (`Graph.outgoing`), and no other branch data exists (test-locked).
2. **A node is an idea box: a label plus contents about itself.** Identity
   (label) and contents are separate; renaming changes nothing, changing
   contents can change answers (test-locked).
3. **The information a connector contains IS the commonality of the two
   adjacent boxes it connects.** Every stored connector carries `content`
   equal to the commonality of its endpoints; `Graph.validate` recomputes the
   commonality and rejects any mismatch (test-locked). Per kind:
   `has_color/has_shape/has_value` carry the shared `(field, value)`;
   `contains` carries the shared constituent; `requires` carries the shared
   requirement; `triggers` carries the shared consideration.
4. **No limit on how many connectors or contents a node may have**
   (test-locked with 64 fields and 64 connectors on one node).
5. **Shared constituent means DIRECT constituents in common** (plus the case
   where one idea is itself a direct constituent of the other). Bicycle and
   cart share `wheel`; the parts inside `wheel` are reached THROUGH it, which
   is the REACHED_VIA lesson, not FIND_SHARED_PART.

## 10. Targeted ^6 specialist (owner directive)

The candidate's whole-part family targets the registered
`cas.cjt.operation.^6.decompose/0.2` neural module (see
`TARGETED_SPECIALIST_PLAN.md`): train only the admit-listed plasticity group
(`operator.^6`) through the existing governed-learning machinery, keep all
other parameters fixed, and verify BOTH the learned skill and the containment
of the update. The graph holds the particular ideas; the targeted group learns
how to inspect and connect them — no permanent neuron per node.
