# CCB-M1 v0.1 — Mathematical Learning and Proof Board

The CAS Mathematical Reasoning Processor. CAS governs the search; the
trusted checker decides validity; exact arithmetic everywhere. Built
above the kernel, beside CAS-RLP, using the same acceptance law.

## Run

    cd cas_only_reasoner/CCB_M1_v0.1
    python -m pytest      # 19 tests
    python run_demo.py    # evaluate, prove, refute, learn

## What it demonstrates

- Exact math: 1/3 + 1/6 = 1/2, 2/3 * 3/4 = 1/2, substitution with
  exact fractions. The exact module contains no floating-point code
  (conformance-tested).
- Identities decided exactly by canonical expansion (sound and complete
  for polynomial identities over rationals), with step proofs for
  constructed transformations.
- The checker is the sole validity authority: continuity, structural
  rule application, exact sample validation of LEARNED procedures,
  final canonical equality, first-invalid-step walk-down.
- Counterexamples: x+y = x*y is refuted by (1,1); x^2 > x is refuted
  by the boundary point x=1; the true square identity survives the
  search. Witnesses carry exact values.
- Learning from a mistake: the ruleset holds the incorrect procedure
  square_sum ((a+b)^2 -> a^2+b^2). The false claim (x+1)^2 = x^2+1 is
  rejected at the first step by exact sample validation (x=1: 4 != 2);
  diagnosis names square_sum; the lesson library supplies
  square_expand; the repaired descendant passes the held-out proof
  task and keeps regression intact -> PROMOTED under the acceptance
  law, with versioned rulesets and rollback.
- Authority: no VERIFIED without the checker; repairs never target the
  checker or benchmarks (REJECTED_AS_PROTECTED); definitions are
  versioned and never change silently; the whole mistake cycle is
  deterministic with sealed decision evidence.
- Curriculum: a prerequisite DAG from exact arithmetic through
  mistake recovery, topologically ordered.

## Layout

    spec/CCB_M1_SPEC_v0.1.md   board contract + the eight authority invariants
    cas_math/exact.py           rational arithmetic, never floats
    cas_math/expr.py            expression IR + exact canonical expansion
    cas_math/rules.py           axioms (trusted) and procedures (learned)
    cas_math/checker.py         the proof checker (sole validity authority)
    cas_math/prover.py          bounded deterministic proof search
    cas_math/counterexample.py  exact counterexample generator
    cas_math/lessons.py         mistake diagnosis + lesson library
    cas_math/curriculum.py      prerequisite DAG
    cas_math/acceptance.py      the acceptance law for math improvements
    cas_math/m1.py              the CCB-M1 orchestrator
    fixtures/                   arithmetic, identities, conjectures, mistake
    tests/                      27 tests

## Honest boundary

Polynomial identities over exact rationals are decided exactly. No
real/interval arithmetic, no analysis, no novelty claims. A theorem may
be called potentially novel only after validity checking AND
independent investigation of prior knowledge - out of v0.1 scope.
