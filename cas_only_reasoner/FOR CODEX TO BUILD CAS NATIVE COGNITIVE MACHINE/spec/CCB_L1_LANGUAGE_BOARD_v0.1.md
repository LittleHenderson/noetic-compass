# CCB-L1 Language Board v0.1

Status: normative controlled-English contract; implementation `UNSUPPORTED` in CNCM-RRK `0.1.0`

CCB-L1 converts a deliberately small English profile into candidate semantic packets and renders approved response plans with fixed templates. It is not a fluent English engine and has no reasoning, commitment, action, or memory-write authority.

## 1. Profile `CCB-L1-CE-0.1`

The first profile supports only explicitly registered vocabulary and these sentence families:

- declarative property: `<referent> is <property>.`;
- declarative relation: `<referent> <registered-verb> <referent>.`;
- transfer event: `<referent> gave <referent> to <referent>.`;
- yes/no question: `Does <referent> <registered-verb> <referent>?`;
- wh-question over one registered slot;
- command: `<registered-imperative> <referent> <registered-relation> <referent>.`;
- explicit correction: `Correction: <registered alias statement>.`;
- topic operation: `New topic: <registered topic>.`, `Return to <registered topic>.`;
- exact clarification response containing explicit registered noun phrases.

Fixture-specific lexicon entries may register names, nouns, verbs, predicates, aliases, and inflection. Registration is data, not learned knowledge. Unknown tokens, unregistered senses, unsupported syntax, and multiple valid parses fail closed.

## 2. Normalization and tokenization

Normalization is deterministic:

1. require Unicode text and normalize to NFC;
2. reject control characters except horizontal space;
3. trim leading and trailing whitespace;
4. replace each internal whitespace run with one U+0020 space;
5. preserve lexical case for provenance while matching registered forms case-insensitively;
6. admit only the terminal marks `.`, `?`, `:`, comma, and apostrophe used by a registered production;
7. tokenize punctuation separately and assign token positions from zero.

The board records the original text outside `SemanticPacket` and the normalized text in `DialogueTurn`. It never embeds raw English into the reasoning request.

## 3. Typed lexicon

Each lexicon entry has a stable ID, one or more surface forms, a category, a semantic symbol, admissible argument types, and source provenance. A surface form with multiple senses produces one candidate per sense in ascending sense ID. Context may eliminate candidates only by exact grammar, type, and dialogue-state constraints. Frequency, neural confidence, and unstated world plausibility are not selectors.

Pronouns in v0.1 are `it`, `he`, `she`, `they`, and their object forms. Their grammatical features constrain CCB-D1 resolution; CCB-L1 does not choose an entity. Definite descriptions are resolved by registered type and aliases. Deictic forms such as `this`, `that`, `here`, and `there` are unsupported unless a future input packet supplies an explicit grounding peripheral contract.

## 4. Candidate semantic construction

For each grammar-valid parse, CCB-L1 emits:

- a typed dialogue act;
- registered entities and events;
- ordered predicate atoms with polarity and epistemic status;
- explicit tense when the production carries it;
- unresolved referent slots rather than guessed bindings;
- source-turn and token-span provenance;
- unsupported features detected during parsing.

Candidate packets are sorted by grammar production ID, then lexical sense IDs, then canonical semantic content. Exactly one surviving complete candidate may become `SELECTED`. More than one becomes `AMBIGUOUS`. Zero becomes `UNSUPPORTED`.

Negation is supported only when a production explicitly declares it and emits `polarity: false`. Absence of a positive atom never emits a negative atom. Implied causality, intention, obligation, emotion, and common-sense facts are not added.

## 5. Deterministic rendering

The v0.1 decoder is a template renderer for admitted `ResponsePlan` values. It supports:

- direct answer;
- exact clarification question;
- correction acknowledgement with a named referent;
- topic-shift acknowledgement;
- memory answer with a required provenance unit;
- typed limitation or unsupported notice.

Content units render in their stored order. Required limitations and provenance units may not be dropped. Entity labels come from the selected referent table; the renderer does not invent synonyms. If no template covers the plan, renderer status is `EXTERNAL_PERIPHERAL_REQUIRED` and the contract produces no language output.

A hybrid Transformer may propose an alternate rendering. The alternate is not admitted unless a deterministic semantic round-trip yields the same ordered content units, polarity, referents, result status, and limitations. Failure falls back to the controlled template or typed unsupported output.

## 6. Correction and acquisition

The board may parse an explicit correction and propose:

- retracting one dialogue-local alias or sense link;
- installing one replacement dialogue-local link;
- attaching correction-turn provenance;
- proposing, but not authorizing, a later memory record.

The proposal is `PROVISIONAL`. Durable lexical learning, generalization to new grammar, autonomous vocabulary acquisition, and cross-conversation retention are unsupported. Only an existing authorized memory path may persist an admitted result.

## 7. Qualification requirements

A future CCB-L1 implementation must pass:

- exact normalization/token tests;
- accepted and rejected grammar tests;
- lexical ambiguity and unknown-token tests;
- pronoun-slot emission tests without internal resolution;
- controlled rendering and required-limitation tests;
- hybrid rendering round-trip rejection tests;
- every paired direct-semantic equivalence case in the conversation protocol.

Until those tests execute against an implementation, language capability is `PROVISIONAL`, implementation is `UNSUPPORTED`, and evidence is `NOT_RUN`.

