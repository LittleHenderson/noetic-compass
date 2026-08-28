# CAS-Sem v0.1 — Minimal Semantic Content Layer

## Idea, Entity, Relation, Reference, Time, Truth, and Provenance

**Status:** FROZEN for Phase 1. This is the minimal content model the
kernel reasons ABOUT. Full English-facing CAS-Sem is a later artifact.

---

## 1. Propositions

A proposition is a predicate application over constant or variable terms:

    Proposition { pred: string, args: [string] }

Variables start with ?. A ground proposition contains no variables.
The negation convention: a proposition whose pred begins with not_
negates the proposition formed by removing the prefix
(not_viable(P1) negates viable(P1)).

## 2. Rules

    Rule { rule_id: string, premises: [Proposition],
           conclusion: Proposition, source: string }

A rule is knowledge (the ^5 Female substrate). Applying a rule is the
^6 Male + ^9 Below/Effect compound; seeing that a rule might apply is
^8 Above/Cause association, and it never counts as proof.

## 3. Evidence status

Every proposition under consideration carries exactly one status:

    SUPPORTED      a complete proof path exists from stored facts/rules
    UNSUPPORTED    no complete proof path exists
    FALSIFIED      the negation is SUPPORTED
    CONTRADICTED   both the proposition and its negation are SUPPORTED

Truth policy: the kernel never marks a proposition SUPPORTED without a
stored proof path (premises consumed, rules applied). A missing premise
is a typed unknown, never a fabricated fact.

## 4. The twelve native reasoning operations

    RECALL         retrieve memories relevant to a typed CAS query
    FORK           create isolated candidate branches
    ASSOCIATE      surface related states through an ^8 operation
    DECOMPOSE      break a candidate into premises, components,
                   dependencies, and constraints through ^6
    INFER          produce a supported ^9 conclusion from declared
                   premises and rules
    COMPARE        compare candidates under one shared evaluative bias
    CONTRADICT     mark incompatible propositions and identify their
                   dependencies
    PUSH_RPM       create a prerequisite subgoal
    RETURN_RPM     return a typed result to the suspended parent
    COMMIT_BRANCH  request acceptance of one candidate
    WRITE_EPISODE  store the committed episode and its result
    HALT           request a typed terminal state

Association is not deduction. The candidate generator may not impersonate
the inference engine: only INFER produces SUPPORTED conclusions, and the
transaction coordinator re-validates every INFER intent by re-proving the
proposed conclusion (the proof kernel decides validity).

## 5. RPM and goals

    GoalFrame { goal_id, parent_goal_id, kind, desired_outcome,
                requirements, status }

kind is question, plan, or subgoal. PUSH_RPM suspends the parent and
pushes a child; RETURN_RPM returns a typed result to the recorded
return address. A child must always preserve a valid parent identity -
losing it is a typed stack fault.
