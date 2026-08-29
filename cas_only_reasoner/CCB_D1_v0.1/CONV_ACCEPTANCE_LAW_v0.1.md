# CONV v0.1 — THE FROZEN ACCEPTANCE LAW

Owner directive 2026-08-29 (GOAL.txt, verbatim):

```text
The machine may acknowledge a user-told fact only after
a provenance-bearing session assertion has been atomically committed.

It may answer from that assertion only while preserving its source.

It may never silently promote a user assertion into verified knowledge.

When no admissible record supports the answer, it asks or says it does not know.
```

The cardinal failure:

```text
The machine says it remembered something
when no committed assertion record exists.
```

Acknowledgment must occur only after state commit.

## The three-store separation (never silently collapsed)

1. **VERIFIED KNOWLEDGE STORE** — the seed CMB facts and rules
   (`CCB_L1_v0.1/fixtures/seed_lexicon.json` `cmb_facts` + `rules`).
   CCB-D1 never writes here.
2. **SESSION ASSERTION STORE** — what this user told the machine this
   session (`dialogue/assertions.py`). Truth status `GIVEN` (the
   CAS-Sem vocabulary: stated by a source, not independently
   verified — the goal sketch's `ASSERTED` maps onto CAS-Sem `GIVEN`
   rather than duplicating the status system, per the goal's own
   reuse rule). `source_class != truth_status`.
3. **DIALOGUE STATE** — pronouns (router discourse), pending
   questions, dialogue acts (`dialogue/board.py`).

## The authority path (the project's first law)

```text
CCB-L1 parses
CAS-Sem-format proposition formed (the router's projection packet)
CCB-D1 proposes a typed SessionAssertionWriteIntent
the intent VALIDATOR (the CAS-RRK validation station for dialogue
    intents, dialogue/intents.py) refuses defects typed
the TransactionCoordinator alone applies the mutation, atomically
the trace is sealed
```

No subsystem directly mutates the session store. A write intent that
claims `truth_status: VERIFIED` is refused typed — that is the
laundering path, closed at the validator.

## Scope of automatic storage (CONV-1A)

Stored: direct, non-quoted, non-hypothetical declarative assertions
that parsed on a NATIVE lane (native L1 or the learned grammar).
Not stored: questions, commands, quotations, greetings, hypothetical
or attributed forms (all currently unsupported language → typed
refusal), and cortex-proposed readings (model guesses are never
promoted to user assertions).
