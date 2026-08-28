# CAS-RR Reasoning Capability Criterion

## A difficulty ladder for the native CAS reasoning machine

**Status:** Executable criterion. Implemented in cas-rr/tasks/levels.py and
cas-rr/cas_rr/benchmark.py; run with: python run.py report (from the
cas-rr directory). Conformance tests: cas-rr/tests/test_benchmark.py.
**Date:** 2026-08-28.

---

## 1. Principles

1. **Measurable, not vibes.** Every level is a CAS-encoded task with an
   expected typed terminal status and expected conclusion. Grading is
   exact status/string comparison - deterministic, no rubrics, no judge.
2. **Typed halts are answers.** CONCLUDED, NEEDS_INFORMATION,
   NEEDS_CAPABILITY, CONFLICT_UNRESOLVED, INADMISSIBLE,
   RESOURCE_EXHAUSTED, LOOP_LIMIT_REACHED are all legitimate results.
   A task that must end in NEEDS_INFORMATION is graded on that refusal.
3. **Refusal is capability, not failure.** When the machine lacks an
   operator (induction, counting, conditional proof), the CORRECT
   behavior is a typed refusal. Frontier probes are scored PASS when the
   machine refuses honestly. And refusing never raises the tier -
   honesty is not attainment.
4. **No LLM anywhere.** The ladder runs on the bare runtime; problems are
   CAS-encoded data.
5. **Deterministic.** The same spec always produces the same grade; the
   report is reproducible by anyone with the repo.

---

## 2. Difficulty axes

Each level adds measured load:

| Axis | Symbol | What it measures |
| --- | --- | --- |
| proof depth | D | rule applications needed to land the conclusion |
| branching factor | B | number of candidates compared |
| constraint load | C | conditions per plan / premises per rule |
| negation load | N | falsifications and contradictions handled |
| uncertainty load | U | missing information that must become a typed halt |
| memory dependence | M | whether the result changes only via stored memory |
| recursion depth | R | nested subgoal levels descended and ascended |

---

## 3. The ladder

| Level | Task | Expected result | Load |
| --- | --- | --- | --- |
| L0 | fact recall | CONCLUDED color(sky,blue) | D=0 B=2 |
| L1 | modus ponens | CONCLUDED mortal(socrates) | D=1 C=1 B=2 |
| L2 | chained deduction | CONCLUDED precedes(a,d) | D=3 B=2 |
| L3 | constraint satisfaction | CONCLUDED viable(P1); two plans falsified | C=5 B=3 N=2 |
| L4 | fault diagnosis (walk-down) | CONCLUDED first_bad(S3) | B=5 N=4 U=1 |
| L4 | honest refusal | NEEDS_INFORMATION with typed lacunae | U=1 M=1 |
| L5 | recursive planning, depth 1 | CONCLUDED executable(P_launch) | R=1 C=2 |
| L5 | recursive planning, depth 2 | CONCLUDED executable(P_launch) | R=2 |
| L5 | memory-dependent reasoning | NEEDS_INFORMATION before the memory, CONCLUDED after | M=1 |
| L6 | arithmetic with comparison as data | CONCLUDED taller(ada,bo) | frontier |
| L6 | arithmetic without comparison | NEEDS_INFORMATION (refuses to compute) | frontier |
| L6 | induction | NEEDS_INFORMATION (no generalization operator) | frontier |
| L6 | probabilistic reasoning | NEEDS_INFORMATION (no counting machinery) | frontier |
| L6 | hypothetical reasoning | NEEDS_INFORMATION (no conditional proof) | frontier |

---

## 4. Tiers

| Tier | Levels | Meaning |
| --- | --- | --- |
| R0 | L0-L1 | recall and single-step deduction |
| R1 | L2 | multi-step chained deduction |
| R2 | L3-L4 | constrained search, falsification, diagnostics, honest refusal |
| R3 | L5 | recursive planning, principled action, memory-dependent behavior |
| R4 | L6 | induction, native arithmetic, probabilistic and hypothetical reasoning |

Tier computation: the highest tier whose levels ALL pass, in ladder
order. L6 frontier probes are excluded from tier computation entirely -
they measure honesty at the boundary, not attained capability.

---

## 5. What the criterion deliberately does NOT measure

- Natural language understanding or generation (no encoders in scope)
- Generalization to unseen task families (each level is fixed)
- Learning across episodes (v0.1 disables durable learning by design)
- Speed, scale, or parallelism
- Creativity or open-ended exploration

These are real capabilities - they are simply not claimed, so they are
not scored. The criterion measures what the architecture promises: a
deterministic, provable, self-diagnosing reasoning core.
