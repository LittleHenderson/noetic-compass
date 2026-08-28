# CAS-Sem v0.1 — Semantic Content and Binding Layer

## Idea, Entity, Relation, Reference, Time, Truth, and Provenance

**Status:** FROZEN for Phase 1. CAS-Sem separates the CONTENT of thought
from the cognitive operation being performed on it. The CAS cognitive
coordinate says what kind of cognition is occurring; the semantic
payload says what it is occurring about. The CAS-RRK remains the
reasoner; the proof kernel remains the validity oracle.

---

## 1. The content model

    Idea         a distinguishable object, event, property, or concept
    Entity       dog_1, person_4, book_7 (typed referents with identity)
    Type         dog, person, book, color
    Property     gray(cat_1)
    Relation     left_of(cube_1, sphere_1) with ROLE positions
    Event        chase(dog_1, cat_1) at a time with an aspect
    Role         agent, patient, instrument, location
    Variable     x, y, someone, something
    Binding      which entity a word or pronoun refers to
    Quantifier   all, some, none, most (declared; v0.1 checks form only)
    Negation     not(P)
    Time/aspect  past, present, future; completed, continuing
    Modality     possible, necessary, permitted, desired (declared; v0.1
                 checks form only)
    Truth status GIVEN, ASSUMED, DERIVED, OBSERVED, VERIFIED,
                 CONJECTURED, CONTRADICTED, UNKNOWN, UNDERDETERMINED
    Provenance   who said it, when, and what evidence supports it

## 2. The coherence laws (enforced)

    1. Referential integrity: every entity reference and every binding
       resolves to a registered entity. Unresolved references are typed
       errors, and the CMB reports them as ENTITY_MISSING lacunae.
    2. Temporal consistency: declared before/after orderings must not
       contradict, directly or by transitivity.
    3. Truth discipline: a claim cannot be both VERIFIED and
       CONTRADICTED; a DERIVED claim must carry a derivation; a
       CONTRADICTED claim must carry the contradicting evidence pair.
    4. Provenance completeness: every claim carries provenance (source,
       when, evidence).
    5. Type discipline: properties and relations use registered types
       where schemas declare them.
    6. Derivation validity: a DERIVED claim's derivation must re-prove
       through the UNCHANGED proof kernel (CAS-RRK). The proof kernel
       decides validity; CAS-Sem only records.

## 3. The boundary

CAS-Sem is a content layer. It never schedules, commits, or halts; the
kernel does. It never decides mathematical validity; CCB-M1's checker
does. It never generates English; CCB-L1 does. It binds meaning and
keeps it coherent.

## 4. Non-goals (v0.1)

No quantifier or modality SEMANTICS (forms are validated, inference is
not), no tense/aspect logic beyond the declared labels, no word-sense
disambiguation, no probabilistic truth degrees.
