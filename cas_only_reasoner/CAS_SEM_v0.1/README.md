# CAS-Sem v0.1 — Semantic Content and Binding Layer

Idea, Entity, Relation, Reference, Time, Truth, and Provenance. CAS-Sem
separates the CONTENT of thought from the cognitive operation being
performed on it. The kernel reasons; the proof kernel decides validity;
CAS-Sem binds meaning and keeps it coherent.

## Run

    cd cas_only_reasoner/CAS_SEM_v0.1
    python -m pytest      # 18 tests
    python run_demo.py    # bind, check, query, lacunae

## What it demonstrates

- The content model: typed entities with identity (cat_1 is not dog_1),
  property ideas, role-bearing relations and events, references (name /
  pronoun / description) with binding, time points with ordering,
  truth statuses (GIVEN, ASSUMED, DERIVED, OBSERVED, VERIFIED,
  CONJECTURED, CONTRADICTED, UNKNOWN, UNDERDETERMINED), and provenance
  (who said it, when, what evidence).
- The six coherence laws, each enforced and each demonstrated by a
  broken document: referential integrity (unresolved references are
  typed errors and CMB ENTITY_MISSING lacunae), temporal consistency
  (contradictory orderings detected, transitively), truth discipline
  (no VERIFIED AND CONTRADICTED; DERIVED requires a derivation;
  CONTRADICTED requires the conflict pair), provenance completeness,
  type discipline, and derivation validity - a DERIVED claim's
  derivation must RE-PROVE through the unchanged CAS-RRK proof kernel.
- The Semantic CMB: queries by entity, by truth status, and by time
  ordering; typed lacunae for missing entities; ablation (removing an
  entity breaks coherence with a located violation).
- The lift bridge: kernel-style propositions become DERIVED claims
  whose derivations the kernel re-proves.

## Layout

    spec/CAS_SEM_SPEC_v0.1.md   content model, six coherence laws, boundary
    cassem/idea.py              idea structures (property, relation, event,
                                negation, quantifier, modality)
    cassem/entity.py            typed entity registry with identity
    cassem/relation.py          role schemas
    cassem/reference.py         references and binding (name/pronoun/
                                description)
    cassem/time.py              timeline with transitive consistency
    cassem/truth.py             truth statuses and discipline
    cassem/provenance.py        provenance records
    cassem/coherence.py         the six-law checker (derivations re-proven
                                through the kernel)
    cassem/store.py             the Semantic CMB: queries and lacunae
    cassem/bridge.py            proposition lift bridge
    fixtures/story_good.json    the good story
    tests/                      18 tests

## Honest boundary

Quantifier and modality forms are validated, their inference semantics
are not implemented. Tense/aspect are declared labels. Word-sense
disambiguation and probabilistic truth degrees are out of v0.1 scope.
