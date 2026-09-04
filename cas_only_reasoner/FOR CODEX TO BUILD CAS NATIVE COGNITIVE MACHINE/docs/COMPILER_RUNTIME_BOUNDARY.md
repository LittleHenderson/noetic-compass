# Compiler–Runtime Boundary

## Current boundary

The CNCM kernel still begins at an already typed `cncm.problem/0.1` object. `ProblemPacket.from_dict` remains its admission boundary. A separate `cncm.conversation/0.1` facade now lowers one frozen controlled-English subset into that exact packet; general natural language, CCDL, CAS diagrams, arbitrary prompts, model output, and external ontologies remain non-executable.

```text
controlled-English facade or future compiler
        |
        | emits cncm.problem/0.1 JSON
        v
ProblemPacket.from_dict
        |
        | strict structural + relational validation
        v
deterministic runtime and authority kernel
```

Facade/compiler success proves only that a sentence was lowered into the packet shape. It does not authenticate facts/rules, authorize runtime intents, establish Foundation/D/W/P meanings, or make a proposition externally true.

## Implemented controlled-English facade

`ConversationalMind` admits only five frozen patterns: explicit positive/negative facts, unary universal rules, positive/negative questions, bounded pronouns, and `I mean Name.` clarification. It retains immutable dialogue facts/rules/referents in one process and constructs a new exact packet for each resolved question. That same compiled packet is run on two fresh machines; both evidence bundles must verify and their terminal status, conclusion, branches, trace, state, and evidence identities must match before any answer is rendered. This establishes deterministic re-execution for the compiled packet, not independent correctness of the language interpretation.

This is not a general source compiler. It has no vocabulary acquisition, morphology, unrestricted syntax, world knowledge, topic stack, correction learning, external model, or tool authority. The broader `cas.*` protocol schemas remain distinct from the compact `cncm.*` runtime transport and require a versioned adapter.

## Exact runtime input

A compiler must emit:

- declared entities and their types;
- predicates with exact argument types and optional transitivity;
- grounded, asserted, provenance-bearing facts;
- only `INFER_MODUS_PONENS` or structurally valid `INFER_TRANSITIVE` rules with provenance;
- one grounded query;
- optional declared candidates, resolver packets, opaque Foundation reference, and finite budgets.

The accepted and defaulted keys are frozen in `schemas/problem_packet.schema.json` and `cncm/model.py`. Unknown fields and recursively non-string canonical mapping keys fail closed. Collection order is normalized before identity and execution.

## Relational obligations

JSON shape alone is insufficient. The runtime checks:

- unique entity, predicate, candidate, semantic fact-key, top-level rule, resolver-target, and resolver-local fact/rule IDs; candidate ID `root` is reserved;
- declared predicates, arity, entity types, and groundness;
- candidate fact/assumption evidence classes and provenance;
- range-restricted, consistently typed variables;
- exact transitive-rule structure;
- Foundation reference membership;
- positive budgets and at least two ticks.

A future compiler should check these earlier for better diagnostics, but the runtime must retain the same checks because compiler output is not automatically trusted.

## Semantic lowering status

| Source concept | v0.1 lowering |
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
| `^8` | Meaning admitted, lowering/execution absent. |
| `^9` | Runtime proof conclusion; no source syntax frozen. |
| `^0`-`^5`, `^7` | `OPEN-SEMANTICS`; no lowering. |
| Foundation/Sub-Foundation | Opaque optional `foundation_ref` only. |
| Foundation-to-Drive, D/W/P | `OPEN-SEMANTICS`; no fields or lowering. |
| Registers and domain coordinates | Frozen identifiers only; no IR fields. |
| Frozen controlled-English subset | Deterministic `ConversationalMind` lowering with trace and parity check. |
| Raw/general English or full CCDL | Out of scope. |

## Trust boundary

Facts and rules become packet-authorized symbolic premises after structural validation, but that says nothing about external truth. Provenance is descriptive text/identifiers, not a signature. Candidate hypotheses may drive mechanical matching but cannot become authoritative support unless a verified chain reaches asserted or source-reconstructed roots. A compiler driven by an LLM or external source cannot make its claims externally trustworthy merely by passing the schema.

For a future untrusted compiler, add a policy layer that authenticates source packages, rule sets, ontology revisions, and issuer identities before constructing `ProblemPacket`. Keep that policy separate from proof reconstruction and from kernel mutation authority.

The same rule applies to episodic memory. Public nonempty injection is rejected; `verified=True` is not an import signature. Private `_from_trusted_snapshot` replay is trusted same-process plumbing, not a security control or ownership proof. A future version must define an authenticated durable adapter and explicit restore API before external records can be admitted.

## Output boundary

The runtime emits structured artifacts only: run summary, final `MachineState`, ordered `TraceEvent` array, and `EvidencePacket`. Diagnostics are strings but have no proof authority. A future explanation generator may summarize these artifacts, but the machine-readable proof/trace remains normative.

## External actions

No compiler output can request an external action in v0.1. `EXTERNAL_ACTION` and `PROTECTED_PATCH` intents are deliberately typed and always rejected. The CLI's explicit file reads/writes are host operations requested by the caller and are outside the kernel intent graph.

## Integration boundary

The protected sibling `../CAS_RRK_v0.1` is not a library dependency or source tree for this implementation. Any future integration must exchange reviewed, versioned packet/ontology artifacts across a documented boundary. Do not import or copy hidden runtime authority from that sibling into v0.1.

The CAS Foundry/Cognitive Board Studio/CADA web-workbench text appended to `cas_reasoner.txt` is also outside this runtime boundary. No board, canvas, editor, collaboration, registry, or publishing object lowers into `ProblemPacket` today. Freeze a Board Ontology/Capability Specification first; any later bridge must declare which board objects are inert presentation metadata and which, if any, may compile into typed packet content.

The CRQS v0.1 qualification-bench proposal at source lines 10031-11171 is outside both the compiler and runtime boundary and remains `PROPOSED-NOT-IMPLEMENTED` / `OPEN-SPECIFICATION`. A CRQS task manifest, `D0`-`D10` grade, `CAS-G` result, Capability Vector (`CV`), `E-Tier`, `A-Level`, Reference Model Benchmark (`RMB`), qualification report, failure localization, or repair proposal is not a `ProblemPacket`, inference rule, proof, intent, or authority grant. No such object is accepted or emitted today.

A future CRQS evaluator must sit beside the runtime as a separately versioned consumer of frozen tasks and verified artifacts:

```text
frozen CRQS task + evaluation policy (not present)
        |                         runtime artifacts
        |                                |
        v                                v
independent CRQS evaluator (not present; no kernel mutation authority)
        |
        v
versioned qualification report (evidence about a bounded evaluation, not an authority grant)
```

Keep the three boundaries explicit: capability is demonstrated behavior, evidence is the support for that claim, and authority is separately granted permission. A future `A-Level` field may reflect an external policy decision, but an evaluator must not derive or widen deployment authority from `CAS-G`, `CV`, `E-Tier`, topology, or a passing test. Likewise, a repair recommendation must remain advisory: `PROTECTED_PATCH` and external action remain prohibited unless a later authority contract separately admits them.

## Minimum future compiler acceptance

Before claiming a compiler exists, require:

1. a versioned source grammar and semantics;
2. deterministic lowering to canonical `cncm.problem/0.1`;
3. source-to-packet provenance and authenticated rule packages;
4. negative tests for unknown/open semantic constructs;
5. differential tests proving reordered equivalent source produces the same packet hash;
6. no expansion of the issuer/capability matrix;
7. explicit abstention when the source needs an `OPEN-SEMANTICS` construct.

Compiler acceptance does not establish CRQS qualification. CRQS requires its own frozen task/report schemas, evaluator-independence rules, protected and held-out suite controls, anti-gaming requirements, and evidence/authority policy bindings.
