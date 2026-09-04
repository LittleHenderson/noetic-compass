# CCB-D1 Dialogue Control Board v0.1

Status: normative deterministic dialogue-state contract; implementation `UNSUPPORTED` in CNCM-RRK `0.1.0`

CCB-D1 carries conversation state between turns. It manages topics, referent candidates, unresolved questions, clarification, dialogue-local corrections, response constraints, and provenance links. It does not reason about domain truth, commit conclusions, execute commands, or write durable memory.

## 1. State identity and ordering

`DialogueState` is an immutable snapshot. A transition consumes exactly one pre-state and one admitted `DialogueTurn`, then emits one post-state. `state_revision` increments by one. An implementation must reject a stale revision, mismatched conversation ID, duplicate turn ID, non-monotonic turn index, or unknown participant.

Ordering is canonical:

- participants by `participant_id`;
- topic stack by stack position, oldest first;
- referents by `referent_id`;
- unresolved questions by source turn then question ID;
- prior turns in chronological order;
- commitments by creation turn then commitment ID;
- memory links by memory record ID.

The current topic is the top active topic. Returning to an earlier topic moves that topic to the top while preserving the others. A new topic is pushed. Topic switching does not delete referents or unresolved questions from earlier topics.

## 2. Turn transition

For an accepted user turn, CCB-D1 performs:

1. validate conversation, participant, turn index, and state revision;
2. register explicitly introduced entities and aliases;
3. construct referent candidates for each unresolved semantic slot;
4. resolve or mark ambiguity using the procedure below;
5. update the active topic only from an explicit topic operation or a uniquely selected topic-bearing act;
6. update active goals and unresolved questions;
7. create, update, or clear one pending clarification;
8. attach exact memory links that were admitted by the memory controller;
9. append the turn ID and produce the next immutable snapshot.

A system response turn may close a pending clarification only after all slots are resolved, or may keep it open with the same child-goal identity. A renderer cannot mutate state.

## 3. Reference resolution

For each referent slot, build candidates from active non-retracted referents whose entity type and grammatical features are compatible. Rank with this deterministic tuple, highest first:

1. explicit binding supplied in the current clarification response;
2. exact registered name or alias;
3. current-topic membership;
4. grammatical compatibility;
5. most recent mention turn;
6. lexical `entity_id` ascending as ordering only, never as a tie breaker for meaning.

Resolution succeeds only when the semantic criteria through recency leave one candidate. Lexical ordering makes evidence stable but must not choose between semantically tied candidates. A tie is `AMBIGUOUS`; no candidate is `UNRESOLVED`. Every candidate records its basis and source provenance. Probabilities and language-model confidence are ignored.

## 4. Clarification and RPM mapping

One or more required unresolved slots suspend the parent dialogue goal. CCB-D1 creates:

- one unresolved-question record;
- one `pending_clarification` with stable missing-slot order;
- one RPM child-goal ID derived from conversation, parent goal, source turn, and missing slots;
- one exact clarification response plan.

The clarification plan names every missing slot and all candidate entity IDs. The child result may bind only those slots. A clarification answer that introduces a different task is processed as a topic shift while the original clarification remains open.

This is an interface mapping. The current kernel has typed RPM for missing semantic prerequisites, but it does not yet execute conversational clarification goals or external commands.

## 5. Corrections

An explicit correction identifies the target act, referent, alias, or proposition. The state transition:

1. marks the superseded dialogue-local item `RETRACTED`;
2. adds the corrected item as `PROVISIONAL` with correction-turn provenance;
3. updates later reference resolution within the same conversation;
4. creates a memory-write proposal only when requested by the response plan.

No correction becomes persistent merely because the user stated it. A durable episode requires the existing kernel commitment and write-back gates. Generalization beyond the exact corrected symbol or alias is unsupported.

## 6. Memory recall

CCB-D1 may request memory by an exact semantic key. It may use only a record admitted by the memory controller and must store the record ID and provenance link in `memory_links`. The response plan includes a `MEMORY_ATTRIBUTION` content unit. If no exact admitted record exists, the correct result is missing information; CCB-D1 must not fabricate recollection.

Similarity search, latent personal profiles, untraceable summaries, and implicit cross-conversation context are unsupported.

## 7. Commitments and actions

Conversational commitments record what a participant said or what the system promised to report. They are not decision commitments and do not grant external authority. A command dialogue act may be understood semantically while action execution remains prohibited. The response must state that no action occurred unless a future separately authorized tool contract supplies verified execution evidence.

## 8. Response controls

`response_style` supplies bounded rendering constraints: tone, detail level, and maximum sentences. These constraints cannot override truth status, required clarification, provenance, limitations, or safety/authority boundaries. A hybrid renderer receives only the admitted `ResponsePlan`, never direct access to mutable dialogue or kernel state.

## 9. v0.1 capability disposition

The schemas and fixtures define expected state transitions for single turn, multi-turn context, pronouns, ambiguity, clarification, correction, topic switching, and exact memory recall. They do not implement those transitions. Accordingly:

- contract status: `SUPPORTED`;
- behavioral capability claim: `PROVISIONAL`;
- current CNCM-RRK conversation implementation: `UNSUPPORTED`;
- runtime qualification and direct-semantic equivalence: `NOT_RUN`.

