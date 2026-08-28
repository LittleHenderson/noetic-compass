# CCB-L1: English Acquisition Board v0.1

## English Encoding, Lexicon, Grammar, Grounding, Dialogue, and Decoding

**Status:** FROZEN for Phase 1. CCB-L1 is STRICTLY OUTSIDE the reasoning
loop: it encodes English into CAS-Sem propositions at the edge, hands
the propositions to the kernel for reasoning, and decodes the result
back into English. The kernel never calls CCB-L1; CCB-L1 calls the
kernel. No LLM is anywhere in the loop.

---

## 1. The boundary

    English
    -> parse (CCB-L1)
    -> CAS-Sem meaning (propositions + entities)
    -> CAS reasoning (the unchanged CAS-RRK kernel)
    -> CAS-Sem conclusion
    -> language planning (CCB-L1)
    -> English

CCB-L1 is an acquired interface, not the brain. Its lexicon and grammar
are CONTENT: they are learned and promoted under the same acceptance
law as CAS-RLP ring R1 - held-out tests before durable promotion,
regression intact, the evaluator untouched, sealed evidence, rollback
preserved.

## 2. Two kinds of memory

    Surface language memory   word forms, spelling, POS, surface patterns
    Semantic CMB              entities, properties, relations, referents

Parsing consults both: the surface lexicon tells the grammar what each
token can be; the semantic CMB grounds words to referents.

## 3. The v0.1 grammar fragment

    the N is ADJ .            -> property(N, ADJ)
    the N is not ADJ .        -> negation(property(N, ADJ))
    the N1 V the N2 .         -> relation(V, N1, N2)
    PRON is ADJ .             -> property(resolve(PRON), ADJ)
    PRON V the N2 .           -> relation(V, resolve(PRON), N2)
    is the N ADJ ?            -> question(property(N, ADJ))
    is PRON ADJ ?             -> question(property(resolve(PRON), ADJ))

Pronouns resolve through the discourse state (last mentioned entity).
Unsupported forms fail TYPED and LOCATED: the machine says which word
it did not understand and where.

## 4. Learning an unknown word

    detect unknown token (lexicon miss, located)
    -> infer candidate part of speech from the frame
    -> generate candidate senses (from teacher definitions/examples)
    -> store provisionally with provenance
    -> test on examples and held-out sentences
    -> contrast-test candidate senses against the semantic CMB
       (a sense that contradicts known facts is rejected)
    -> promote the surviving sense under the acceptance law
    -> corrections revise provisional entries and VERSION verified
       entries; verified entries never change silently

## 5. The acceptance law for lexicon promotion

A new entry is promoted only when ALL hold: every held-out sentence
parses to the expected meaning; regression sentences still parse to
their expected meanings; the grammar (the evaluator) was not modified;
a complete evidence packet is sealed; the lexicon is versioned and
rollback remains possible. This mirrors CAS-RLP's acceptance law
exactly.

## 6. The eight English-learning tests (charter section 14)

    round-trip meaning     parse(generate(p)) == p
    paraphrase convergence different surface forms, same propositions
    contrast testing       candidate senses rejected by known facts
    novel composition      unseen word combinations parse (systematicity)
    referential tests      pronouns resolve to the right entity
    grounding tests        sentences about known entities consult the
                           semantic CMB; the kernel answers; the answer
                           decodes to English
    correction retention   corrections persist and are re-tested
    ablation               removing an entry breaks parsing with a typed,
                           located error

## 7. Non-goals (v0.1)

No phonetics, no free-form conversation, no idioms, no tense/aspect,
no nested clauses, no ambiguity resolution beyond candidate-sense
contrast. These are the curriculum's later stages, not Phase 1.
