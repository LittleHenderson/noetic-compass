# CAS Mathematical Apprenticeship Ladder v0.1 — THE ACCEPTANCE LAW

Owner directive 2026-08-29 (MATH LESSONS.txt). The constitutional
shape is the general apprenticeship's, specialized to mathematics.

## The twelve steps (every lesson, in order)

```text
 1. RPM: the prerequisite graph names the first missing prerequisite;
    a lesson whose prerequisites are not yet promoted is refused typed.
 2. The teacher proposes a typed MathLessonPacket (two channels:
    the FORMAL channel is authoritative; the language channel teaches
    accessibility).
 3. The packet's formal content parses into CAS-Math IR (the CCB-M1
    expression classes; a deterministic infix reader, no model).
 4. Every worked example is checked EXACTLY by the CCB-M1 engine -
    one wrong example rejects the lesson with the exact witness.
 5. The counterexample generator ATTACKS: a proposed rewrite rule
    must survive schema equality + grid evaluation; the packet's
    declared common mistake must actually BE a mistake (a refutation
    witness is required - a 'mistake' that is true is a defect).
 6. CAS-SDG generates independent practice variations (seeded,
    deterministic, disjoint from the teacher's examples).
 7. The student solves the development exercises using ONLY promoted
    skills plus the candidate.
 8. The student solves the PROTECTED held-out exercises (our channel,
    separate seed, never shown to the teacher). Exact mathematics:
    the bar is 100%.
 9. Every previously mastered skill's regression guards re-solve.
10. Delayed retention: the skill store reloads fresh from disk and
    the retention exercises re-solve.
11. Verdict: PROMOTED / QUARANTINED / REJECTED_* (typed).
12. The complete episode seals with teacher identity, examiner
    identity, provenance, evidence, the checker-source digest, and a
    rollback pointer (the prior store revision).
```

## What the teacher may never do (enforced, not requested)

- mark its own content verified — a packet carrying `verified`,
  `promote`, or any authority field is refused typed;
- alter the proof checker — the episode seals the checker source
  digest; a mismatch voids the run;
- write into durable math memory — only the ladder's coordinator
  writes the skill store, only on PROMOTED;
- see or set the protected battery — it derives from our seed in our
  channel;
- weaken the promotion threshold — 100% exact, not configurable by
  any packet field.

## Validity authority

CCB-M1 remains the sole validity authority: canonical polynomial
equality (sound and complete for this class) verifies rewrite-rule
schemas; exact evaluation verifies computations; substitution into
the ORIGINAL equation verifies every claimed solution. CAS-Ohm
measures learning flow (P_cap before/after, compute-only); it never
decides whether an equation is true.
