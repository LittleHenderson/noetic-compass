# CCB-L1 v0.1 — English Acquisition Board

English encoding, lexicon, grammar, grounding, and decoding - STRICTLY
OUTSIDE the reasoning loop. CCB-L1 encodes English into CAS-Sem at the
edge, hands the propositions to the unchanged kernel for reasoning, and
decodes the verdict back into English. The kernel never calls CCB-L1
(conformance-tested: no kernel file imports lang). No LLM anywhere.

## Run

    cd cas_only_reasoner/CCB_L1_v0.1
    python -m pytest      # 18 tests
    python run_demo.py    # parse, learn, ask, answer

## What it demonstrates

- Round-trip meaning: parse(generate(p)) == p for property, relation,
  negation, and question forms.
- Paraphrase convergence: "the cat is gray." and "it is gray." carry
  the same meaning after reference resolution.
- Referential tests: "it" resolves to the last mentioned entity.
- Grounding: "is the cat gray?" runs through the CAS-RRK kernel
  (facts from the semantic CMB, rule r_prop) and the typed verdict
  decodes to English - CONCLUDED becomes "yes, the cat is gray.",
  NEEDS_INFORMATION becomes "i do not know whether the dog is gray."
  The refusal is carried into language honestly.
- Word learning: the unknown word "flurpy" is detected TYPED AND
  LOCATED ("I did not understand 'flurpy' at word 4"); two candidate
  senses are stored provisionally; examples and held-out sentences
  promote "gray" and the contrast test (antonym conflict with the
  known fact has(cat, quiet)) rejects "loud"; promotion is versioned
  under the acceptance law.
- Novel composition: after learning "flurpy" on cats and dogs, the
  unseen combination "the zorp is flurpy." parses (systematicity).
- Correction retention: correcting flurpy to "black" versions the
  entry; the old sense stays in history - verified entries never
  change silently.
- Ablation: removing "gray" breaks parsing with a typed, located
  error and leaves other sentences intact.
- Determinism: the acquisition cycle is deterministic with a sealed
  cycle digest; rollback preserves the parent lexicon.

## Layout

    spec/CCB_L1_SPEC_v0.1.md   the boundary, the grammar fragment,
                                learning loop, acceptance law, the eight
                                English tests, non-goals
    lang/lexicon.py             versioned surface lexicon
    lang/sem.py                 CAS-Sem propositions
    lang/discourse.py           pronoun resolution state
    lang/grammar.py             deterministic parse/generate + located errors
    lang/acceptance.py          the acceptance law for lexicon promotion
    lang/acquirer.py            the word-learning loop with contrast
    lang/kernel_bridge.py       the one-way grounding rail to CAS-RRK
    lang/l1.py                  the CCB-L1 orchestrator
    fixtures/                   seed lexicon + grounding facts, teach spec
    tests/                      18 tests

## Honest boundary

The v0.1 grammar fragment covers copular, transitive, negation, and
question forms with "it" reference. No phonetics, free-form
conversation, idioms, tense/aspect, or nested clauses - the
curriculum's later stages, not Phase 1. CCB-L1 is an acquired
interface, never the brain.
