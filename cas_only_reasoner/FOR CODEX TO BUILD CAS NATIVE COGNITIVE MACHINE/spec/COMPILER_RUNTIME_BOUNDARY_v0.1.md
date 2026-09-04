# Compiler–Runtime Boundary v0.1

Status: **required Phase 0 contract candidate — bounded and explicit; Phase 0 OPEN**

This contract freezes the current handoff between a controlled facade or future
compiler and the deterministic CNCM-RRK v0.1 runtime. It does not claim a full
CCDL compiler, general-language compiler, ontology compiler, authenticated
source authority, or Phase 0 closure.

## 1. Authority basis

This artifact is required by `cas_reasoner.txt:12570-12580`; an explicit
compiler/runtime boundary is an exit-gate condition at
`cas_reasoner.txt:12618-12625`. Its bounded content restates
`docs/COMPILER_RUNTIME_BOUNDARY.md` under the constraints of
`OPEN_QUESTIONS.md`, `NON_GOALS.md`, `spec/CAS_KERNEL_IR_v0.1.md`, and
`spec/CONFORMANCE_PLAN_v0.1.md`.

## 2. Exact current handoff

```text
frozen controlled-English facade or future compiler
        |
        | emits canonical cncm.problem/0.1 data
        v
ProblemPacket.from_dict
        |
        | strict structural and relational validation
        v
deterministic runtime components
        |
        | typed intent requests
        v
single-writer authority kernel
        |
        | atomic state, trace, and evidence
        v
structured runtime artifacts
```

The runtime begins at an already typed `cncm.problem/0.1` object or mapping.
`ProblemPacket.from_dict` is the admission boundary. The compiler/facade does
not emit kernel state, an authorized intent, a trace event, an evidence packet,
or an authority grant.

## 3. Compiler/facade responsibility

A source-facing component is responsible only for the semantics of its own
frozen source subset and deterministic lowering into the exact problem packet.
It MUST:

- emit declared entities and their exact types;
- emit predicates with exact argument types and optional transitivity;
- emit grounded asserted facts with polarity and descriptive provenance;
- emit only structurally valid `INFER_MODUS_PONENS` or
  `INFER_TRANSITIVE` rules with provenance;
- emit one grounded query;
- emit only contract-admitted optional candidates, resolver packets, opaque
  Foundation reference, and finite budgets;
- reject or explicitly abstain on unknown syntax, unsupported semantics, or a
  construct that depends on `OPEN-SEMANTICS`;
- preserve deterministic canonicalization and source-to-packet provenance.

A future compiler may duplicate runtime checks to provide earlier diagnostics,
but successful compilation is not runtime admission and does not remove any
runtime check.

### Implemented facade, not a general compiler

The current `cncm.conversation/0.1` facade is limited to the frozen patterns
documented in `docs/COMPILER_RUNTIME_BOUNDARY.md`: explicit positive/negative
facts, unary universal rules, positive/negative questions, bounded pronouns,
and `I mean Name.` clarification. It retains immutable in-process dialogue
facts/rules/referents and constructs a fresh problem packet for each resolved
question.

Its two-fresh-machine parity check demonstrates deterministic re-execution of
the compiled packet. It does not establish that the language interpretation is
independently correct.

## 4. Runtime admission responsibility

The runtime MUST independently retain all structural and relational checks,
including:

- uniqueness of entity, predicate, candidate, semantic fact-key, top-level
  rule, resolver target, and resolver-local fact/rule identities;
- reservation of candidate ID `root`;
- declared predicates, arity, entity typing, and groundness;
- candidate evidence classes and provenance;
- range restriction and consistent variable typing;
- the exact transitive-rule structure;
- Foundation-reference membership;
- positive budgets and at least two ticks;
- rejection of unknown fields and recursively non-string canonical mapping
  keys;
- canonical collection ordering before identity and execution.

Packet admission grants only permission to evaluate packet-authorized symbolic
premises under the bounded runtime rules. It does not authenticate the premises
or establish external truth.

## 5. Runtime and kernel responsibility

After packet admission:

- deterministic components may propose only the closed intents described by
  `CAS_KERNEL_IR_v0.1.md`;
- an intent remains a request and never an authority token;
- the single-writer kernel validates issuer/capability, scope, snapshot,
  identity, typed mutation, proof reconstruction, conflicts, and budgets against
  the same pre-state;
- accepted writes apply atomically and rejected writes remain trace-visible;
- the runtime owns branch/RPM/comparison/commitment/memory execution within the
  KIR, terminal disposition, and structured output;
- every tick produces the sealed trace information required by the KIR;
- the runtime emits a run summary, final `MachineState`, ordered `TraceEvent`
  array, and `EvidencePacket`.

Diagnostics and later natural-language explanations are non-normative. The
machine-readable proof, state, trace, and evidence records remain the bounded
normative artifacts.

## 6. Semantic lowering freeze

| Source concept | v0.1 boundary disposition |
|---|---|
| Entity/type declaration | Direct `EntityDecl`. |
| Predicate/relation | Direct `PredicateDecl`. |
| Positive/negative ground proposition | `Proposition.polarity`. |
| Horn implication | `Rule` with modus ponens. |
| Explicit transitive relation | Frozen three-variable transitive rule form. |
| Query | Ground `Proposition`. |
| Candidate path | Caller-declared `CandidateSpec`; no generator. |
| Missing-prerequisite child | Caller-declared `ResolverSpec`; not D/W/P. |
| `^6` | Runtime decomposition; no source syntax frozen. |
| `^8` | Associative meaning distinguished from deduction; lowering and execution absent. |
| `^9` | Runtime proof conclusion; no source syntax frozen. |
| `^0`-`^5`, `^7` | `OPEN-SEMANTICS`; no lowering. |
| Foundation/Sub-Foundation | Opaque optional `foundation_ref` only; no semantic behavior is inferred. |
| Foundation-to-Drive and D/W/P | `OPEN-SEMANTICS`; no fields or lowering. |
| Registers and domain coordinates | Frozen identifiers only; no IR fields. |
| Frozen controlled-English subset | Deterministic facade lowering with trace and parity check. |
| Raw/general English, full CCDL, CAS diagrams, arbitrary prompts, model output, external ontologies | Non-executable and out of scope. |

## 7. Trust and authority boundary

Compiler or facade success MUST NOT:

- authenticate a fact, rule, source package, ontology, issuer, or memory record;
- establish Foundation, Sub-Foundation, Foundation-to-Drive, D/W/P, register,
  domain-stability, or other open meanings;
- authorize an intent, state write, learning promotion, protected patch,
  external action, or deployment;
- convert descriptive provenance into a signature;
- turn a candidate hypothesis into authoritative support without an exactly
  verified chain to an admitted root;
- establish CRQS capability, evidence maturity, deployment authority, or repair
  permission.

A future untrusted compiler requires a separate policy layer to authenticate
source packages, rule sets, ontology revisions, and issuer identities before a
packet is constructed. That policy must remain separate from proof
reconstruction and kernel mutation authority.

The same separation applies to memory. Public nonempty episodic injection is
rejected. Private exact-`RunResult` replay is same-process plumbing, not external
authentication or ownership proof.

## 8. Prohibited and external surfaces

No compiler output may request an external action in v0.1. `EXTERNAL_ACTION`
and `PROTECTED_PATCH` are typed solely so the kernel can reject them. Explicit
CLI file I/O requested by the caller is a host operation outside the kernel
intent graph.

The current boundary admits no Board/Foundry/CADA object and no CRQS task,
grade, capability vector, evidence tier, authority level, benchmark, repair, or
qualification object. Any future bridge or evaluator must be separately
versioned and cannot inherit kernel mutation authority.

## 9. Minimum gate before claiming a broader compiler

No broader compiler claim is permitted until there is:

1. a versioned source grammar and semantics;
2. deterministic lowering to canonical `cncm.problem/0.1`;
3. source-to-packet provenance and authenticated rule packages;
4. negative tests for unknown and open semantic constructs;
5. differential tests showing reordered equivalent source produces the same
   packet hash;
6. evidence that the issuer/capability matrix was not expanded;
7. explicit abstention when a source needs an `OPEN-SEMANTICS` construct.

Those conditions do not establish CRQS qualification, external truth, or
deployment authority.

## 10. Conformance and Phase 0 status

The conformance plan's schema, packet, authority, identity, trace, evidence,
replay, golden, and CLI checks apply across this boundary. Passing them supports
only the bounded behavior they cover.

This artifact makes the current compiler/runtime split explicit. It does not by
itself establish that every ontology term is defined, every source conflict is
disposed, the KIR has received final Phase 0 stability acceptance, or the first
goldens are frozen for Phase 0. The full exit gate at
`cas_reasoner.txt:12616-12628` remains **OPEN**.
