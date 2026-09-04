# CAS Conversation Protocol v0.1

Status: normative interface contract; conversation implementation is not present in CNCM-RRK `0.1.0`

This document freezes the boundary between language, dialogue, semantic content, reasoning, response planning, and rendering. It does not claim fluent English, a conversational runtime, a trained language model, speech, or a qualified conversation grade.

## 1. Bounded purpose

The v0.1 path is:

```text
LanguageInput
    -> SemanticPacket

SemanticPacket
    -> ReasoningRequest

CommittedSemanticResult
    -> ResponsePlan

ResponsePlan
    -> LanguageOutput
```

The first reference front end is deterministic controlled English under profile `CCB-L1-CE-0.1`. Free-form English, idioms, metaphor, implicit world knowledge, speech, multilingual input, and open-ended fluency are unsupported. A future hybrid language model may propose parses or renderings, but it remains a replaceable peripheral.

## 2. Closed authority boundary

Language and dialogue components are not kernel authorities.

| Component | May propose | Must not do |
|---|---|---|
| Language front end / CCB-L1 | tokens, normalized text, candidate word senses, candidate `SemanticPacket` values | assert empirical truth, select a reasoning winner, commit a result, mutate runtime state, or write memory |
| Hybrid Transformer peripheral | candidate parses, paraphrases, candidate lexical senses, candidate surface renderings | bypass typed packets, mark a proof verified, commit a conclusion, write durable memory, change principles, grant capabilities, or edit the runtime |
| CCB-D1 | deterministic dialogue-state transitions, referent candidates, clarification requests, response constraints, memory-read requests | invent a referent, prove a proposition, commit a semantic result, authorize a tool, or write durable memory |
| CAS-Sem adapter | validate and lower selected semantic content into a typed reasoning request | import raw English into the reasoner or confer proof authority on a language parse |
| CAS-RRK | reason over an admitted typed request and emit a trace and typed result | infer natural-language meaning that was not present in the admitted packet |
| Response planner | order committed content, limitations, provenance, and exact clarification questions | add facts, hide uncertainty, change result status, or turn a provisional candidate into a conclusion |
| Renderer | render an admitted `ResponsePlan` | alter semantic content, omit a required limitation, or create a memory write |

Every peripheral output is data. It is never an intent credential or proof source. The authority and prohibition rules in `AUTHORITY_CONTRACT_v0.1.md` remain unchanged.

## 3. Canonical data contracts

The six schemas in `schemas/` are normative for this interface:

- `semantic_packet.schema.json`: selected, ambiguous, or unsupported meaning candidate;
- `dialogue_act.schema.json`: typed conversational purpose;
- `dialogue_turn.schema.json`: one admitted user or system turn record;
- `referent.schema.json`: a resolved, ambiguous, unresolved, or retracted discourse referent;
- `dialogue_state.schema.json`: the deterministic conversation snapshot;
- `response_plan.schema.json`: content authorized for rendering from a committed or abstaining semantic result.

IDs use `^[A-Za-z_][A-Za-z0-9_.:-]*$`. Arrays are ordered. Implementations must preserve the order rules in the board specifications; they must not rely on unordered object iteration. Floating-point confidence values are absent. Provenance names exact turns, packets, traces, or memory records.

`SemanticPacket.semantic_content` contains no raw English. Raw text remains in `DialogueTurn`. A `ReasoningRequest` adapter may consume only a packet whose interpretation status is `SELECTED`. `AMBIGUOUS` requires clarification. `UNSUPPORTED` requires a typed unsupported response and no reasoning handoff.

## 4. Deterministic turn protocol

For controlled-English input, an implementation performs these steps in order:

1. Normalize and tokenize under `CCB-L1-CE-0.1`.
2. Produce all grammar-valid candidate meanings in stable lexical order.
3. Apply the CCB-D1 reference-resolution procedure against the pre-turn state.
4. Select exactly one meaning only when every required referent and semantic slot is uniquely resolved.
5. If selection succeeds, emit a `SELECTED` language-derived `SemanticPacket` and its paired direct-semantic test packet.
6. If one or more required slots are unresolved, emit `AMBIGUOUS`, open one clarification child goal, and plan the exact clarification question.
7. If the utterance is outside the controlled profile, emit `UNSUPPORTED`; do not guess.
8. Advance dialogue state only through the deterministic transition in `CCB_D1_DIALOGUE_CONTROL_BOARD_v0.1.md`.

A clarification answer resumes the suspended parent goal only when it resolves every slot named by `pending_clarification.missing_slots`. Otherwise the system asks the remaining canonical question.

## 5. Direct-semantic equivalence gate

Every qualification case entering through controlled English must be run twice.

```text
Run A: controlled English -> selected SemanticPacket -> reasoning
Run B: paired DIRECT_SEMANTIC packet              -> reasoning
```

Before either run, the pair must have structurally identical `semantic_content`. The two packets may differ only in packet identity, source-turn identity, construction mode, language profile, and equivalence-link metadata.

After both runs, the following must be structurally equal after removing run-local IDs and trace-chain hashes:

- terminal disposition;
- committed semantic conclusion, or exact lacunae when no conclusion commits;
- reasoning branch topology and branch statuses;
- canonical inference operations, premises, and conclusions;
- RPM child-goal targets, order, success/failure status, and resume address;
- authoritative memory record IDs read or written;
- response-plan semantic content and required limitations.

Different English wording is not a failure if the two `ResponsePlan` values are semantically equal. If removing the language peripheral changes any reasoning dimension above, the case fails the CAS-authority gate. Static fixture equality is not a reasoning qualification; runtime comparison must separately report `PASSED`. The v0.1 fixtures therefore label runtime equivalence `NOT_RUN` until an adapter and runner exist.

## 6. Clarification contract

The system must not choose an ambiguous referent by style, likelihood, or language-model confidence. CCB-D1 emits one `pending_clarification` record and a `ResponsePlan.exact_clarification` object containing:

- the unresolved slots in stable slot order;
- the stable candidate entity IDs for each slot;
- one exact controlled-English question;
- the suspended parent goal;
- one RPM child-goal ID.

For the two-slot motion form `Move it beside the other one.`, the v0.1 canonical question is exactly:

```text
Which object should I move, and which object should I place it beside?
```

The planned question is evidence of detected missing information, not evidence that RPM or action execution is implemented. External actions remain prohibited by the current kernel.

## 7. Response planning

A response plan is admitted only from one of these sources:

- a committed semantic result;
- a typed `NEEDS_INFORMATION`, `CONFLICT_UNRESOLVED`, `INADMISSIBLE`, or budget disposition;
- an `AMBIGUOUS` language packet requiring clarification;
- an `UNSUPPORTED` language packet.

Content units preserve source references. A planner may add a required limitation or provenance statement, but not a new domain proposition. `planned_text` is a controlled deterministic template, not proof of a fluent decoder. A renderer may improve surface form only when the rendered text passes a semantic round-trip check against the same plan.

## 8. Memory and correction boundary

Conversation state may carry links to admitted memory records and may propose a correction. It may not install a durable record. A correction has three distinct stages:

1. dialogue-local update, marked `PROVISIONAL`;
2. kernel-admitted semantic conclusion, when reasoning is required;
3. separately authorized episodic write under the existing authority contract.

Until stage 3 succeeds, a fixture may demonstrate same-conversation use but must not claim persistent learning. Recall must identify the exact memory record and provenance used. Similarity retrieval and unproven recollection are unsupported.

## 9. Capability and evidence labels

Conversation claims use these exact labels:

| Label | Meaning |
|---|---|
| `SUPPORTED` | an implementation exists and the named qualification suite passed |
| `PROVISIONAL` | the contract, design, or fixture exists, but implementation qualification is incomplete |
| `UNSUPPORTED` | the current implementation does not expose the capability and must fail closed |
| `NOT_RUN` | the named measurement or equivalence execution has not been performed |

The presence of a schema or fixture is `PROVISIONAL`, not `SUPPORTED`. A fixture's expected result is not a measured runtime result. Conversation grades such as `CONV-4`, language grades such as `LANG-3`, and evidence grades remain unassigned until a separate qualification bench executes all required cases.

## 10. Required trace

An implemented conversational turn must retain, as typed trace data:

- raw and normalized input references;
- tokenizer and grammar profile versions;
- candidate meaning IDs and selected meaning or exact ambiguity;
- referent candidates, resolution basis, and source turn;
- pre-turn and post-turn dialogue-state identities;
- active topic and goal transitions;
- memory record IDs requested and admitted;
- reasoning request and CAS trace references;
- clarification child goal and resume address;
- committed semantic result or typed abstention;
- response-plan ID and renderer profile;
- proposed and admitted memory writes.

An explanation must be derived from this trace. A newly generated explanation with no trace reference is non-evidence.

## 11. v0.1 non-claims

This contract does not implement or establish:

- unrestricted English understanding or generation;
- common sense, pragmatics, sentiment, idioms, humor, or metaphor;
- voice recognition or speech synthesis;
- tool use or external action;
- persistent correction learning;
- similarity or associative conversation memory;
- a Transformer, neural language model, or CAS-Ohm language mechanism;
- native language acquisition;
- any `CONV-*`, `LANG-*`, `MEM-*`, CAS-G, CRQS, or Evidence grade.

The current kernel still accepts typed problem packets, not these conversation packets. Implementing the adapter, dialogue runtime, response planner, renderer, and qualification runner requires a later versioned change.

## 12. Compact CNCM runtime-view adapter

The initial conversational host may expose a smaller runtime transport view rather than the full protocol documents. The known compact view uses:

```text
ConversationalMind.turn(text).to_dict()
    schema_version = cncm.conversation-turn/0.1
    status
    response
    state
    trace

state.schema_version = cncm.dialogue-state/0.1
state = turn_index, entities, facts, rules,
        recent_entities, pending_reference

trace = parse_candidates, selected_meaning, references,
        problem_packet, reasoning_bundle, verification,
        response_plan
```

That compact `cncm.*` surface is a runtime/transport view. It is not silently identical to the broader `cas.dialogue_turn/0.1` or `cas.dialogue_state/0.1` protocol documents and is not directly validated by the six protocol schemas.

A versioned adapter must perform this mapping before a compact runtime result can claim protocol conformance:

| Compact runtime field | Protocol target |
|---|---|
| top-level `status` | `DialogueTurn.processing_status` plus the typed `ResponsePlan.source_result_status` |
| top-level `response` | `ResponsePlan.planned_text`; it must not introduce content absent from ordered content units |
| `state.turn_index` | `DialogueTurn.turn_index` and `DialogueState.state_revision`, with an explicit initial-revision rule |
| `state.entities` and `state.recent_entities` | ordered `DialogueState.referents`, including resolution status and source-turn provenance |
| `state.facts` and `state.rules` | semantic or reasoning-request references; never implicit dialogue authority |
| `state.pending_reference` | `DialogueState.pending_clarification`, unresolved question, and unresolved referent candidates |
| `trace.parse_candidates` | `SemanticPacket.ambiguity_candidates` and the trace candidate list |
| `trace.selected_meaning` | selected `SemanticPacket.semantic_content` |
| `trace.references` | referent candidates, selected bindings, and provenance |
| `trace.problem_packet` | the proposed typed reasoning request; adapter status remains request-only |
| `trace.reasoning_bundle` | CAS trace/result references used by `ResponsePlan` |
| `trace.verification` | evidence status; it cannot promote a language parse or grant authority |
| `trace.response_plan` | the typed `ResponsePlan`, after exact schema validation |

The adapter must synthesize no missing evidence. When the compact view lacks participants, topic provenance, clarification goal identity, memory provenance, or ordered response units, the adapter must emit `UNSUPPORTED` or `PROVISIONAL` for that dimension rather than inventing values. Adapter implementation and conformance are currently `PROVISIONAL`; runtime adapter qualification is `NOT_RUN`. A future schema for the compact `cncm.conversation-turn/0.1` envelope should be separate from these six protocol schemas.
