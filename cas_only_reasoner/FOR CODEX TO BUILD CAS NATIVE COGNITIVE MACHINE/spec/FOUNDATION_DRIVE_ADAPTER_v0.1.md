# Foundation–Drive Adapter v0.1

Status: **required Phase 0 contract shell — OPEN-SEMANTICS / non-executable**

The exact v0.1 outcome is that no Foundation-to-Drive mapping is defined. This
artifact freezes the separation and fail-closed behavior required while that
mapping remains open. It contains no hidden, positional, default, or illustrative
mapping and does not declare Phase 0 closed.

## 1. Authority basis

The adapter is required by `cas_reasoner.txt:12570-12580`. Its controlling
constraints are:

- CAS Drives are `F1` through `F7` (`cas_reasoner.txt:12593-12594`);
- TKS Foundations are separately typed from CAS Drives
  (`cas_reasoner.txt:12596-12597`);
- the 28 Sub-Foundations are separately typed goal and consequence channels
  (`cas_reasoner.txt:12599-12600`);
- OS-001, OS-002, and OS-003 in `OPEN_QUESTIONS.md` leave Foundation meanings,
  Sub-Foundation meanings/World mappings, and the Foundation-to-Drive adapter
  unresolved;
- the current packet may carry an opaque Foundation reference, while
  Foundation-to-Drive and D/W/P have no fields or lowering
  (`docs/COMPILER_RUNTIME_BOUNDARY.md`);
- `NON_GOALS.md` prohibits inventing the missing meanings or treating
  `TF1`-`TF7` as identical to `F1`-`F7`.

## 2. Separated source and target types

| Side | Frozen namespace | v0.1 status |
|---|---|---|
| Foundation source | `TKSFoundation`: opaque `TF1` through `TF7` references | Meanings, precedence, and goal-generation behavior are `OPEN-SEMANTICS`. |
| Sub-Foundation source | `TKSSubFoundation`: opaque `TF1a` through `TF7d` goal/consequence references | Meanings, World mappings, consequences, and weights are `OPEN-SEMANTICS`. |
| Drive target | `CASDrive`: `F1` through `F7` | A separate namespace. This adapter contract assigns no rail meanings or weights. |

There is no implicit subtype relation, equality relation, cast, ordinal
correspondence, or executable mapping from either source type to the target
type.

## 3. Frozen v0.1 adapter behavior

For v0.1, the Foundation-to-Drive relation is **unspecified and unavailable**.
That means:

1. No runtime or compiler component may translate a `TKSFoundation` or
   `TKSSubFoundation` into one or more `CASDrive` values.
2. No component may infer a mapping from matching digits, declaration order,
   names, labels, storage locations, examples, or implementation convenience.
3. No default mixture, weight, precedence, or fallback Drive may be supplied.
4. An opaque `foundation_ref` may be validated and carried only as allowed by
   the existing problem-packet contract. Carrying the reference is not adapter
   execution and grants no truth, evidence, priority, proof, commitment,
   scheduling, learning, mutation, or action authority.
5. A request that requires Foundation-to-Drive conversion MUST fail closed or
   explicitly abstain as an `OPEN-SEMANTICS` construct. It MUST NOT silently
   drop the Foundation, reinterpret it as a Drive, or fabricate a mapping.
6. D/W/P prerequisite state is outside this adapter. D/W/P MUST NOT be used as
   Drive, flow, resistance, adapter weights, or a substitute mapping.

The absence of an executable v0.1 relation does not assert that a future
relation is impossible. It asserts only that the named authoritative sources do
not define one that may be executed now.

## 4. Prohibited representations and effects

The following are non-conforming:

- `TF1 == F1`, or any equivalent identity assertion for another ordinal;
- using a Foundation identifier where a CAS Drive type is required;
- using a CAS Drive identifier where a Foundation or Sub-Foundation type is
  required;
- attaching invented names, Worlds, consequences, scores, or weights to make a
  conversion executable;
- treating an adapter result as proof, external truth, authenticated evidence,
  commitment permission, deployment authority, or kernel mutation authority;
- allowing a model, prompt, UI, compiler, or caller declaration to bypass the
  open semantic status.

No mapping table appears in this contract because populating one would invent
the decision OS-003 says is absent.

## 5. Conditions for a future executable revision

The adapter MUST remain non-executable until a later versioned authority change
resolves, at minimum:

1. OS-001: canonical Foundation names, meanings, precedence, and
   goal-generation behavior;
2. OS-002: canonical Sub-Foundation definitions and World mappings;
3. OS-003: the actual Foundation-to-Drive mapping rule;
4. the exact typed input, output, revision, and failure contract for that rule;
5. authority and provenance requirements for admitting the ontology and mapping;
6. negative conformance tests proving that unknown, stale, malformed, and
   cross-typed mappings fail closed.

Items 4-6 state the boundary protections already required by the compiler,
runtime, and conformance sources. They do not define the missing semantic map.
Any future thaw requires coordinated versioned changes to the authority
manifest, ontology contract, packet/schema boundary, runtime only if runtime
behavior changes, and conformance plan.

## 6. v0.1 conformance checks

Conformance evidence MUST show:

- there is no default or ordinal Foundation-to-Drive conversion;
- opaque Foundation references remain opaque;
- invalid cross-namespace uses are rejected;
- an unresolved adapter request cannot alter proof, comparison, commitment,
  memory promotion, intent authorization, or external-action disposition;
- compiler and runtime behavior abstains rather than guessing when conversion
  is required.

These checks prove separation, not the correctness of any mapping.

## 7. Phase 0 gate status

This file supplies the required named adapter contract shell and records the
v0.1 no-mapping disposition. The adapter's semantic content remains
`OPEN-SEMANTICS`; therefore this artifact is not evidence that every core term
has one complete typed definition or that Phase 0 has closed. Phase 0 remains
**OPEN**.
