# CCB-M1: Mathematical Learning and Proof Board v0.1

## CAS Mathematical Reasoning Processor

**Status:** FROZEN for Phase 1. Built ABOVE the kernel and beside
CAS-RLP. CAS governs the search; the trusted checker decides validity.
No mathematical conclusion becomes VERIFIED without an accepted proof
object or independently checked computation.

---

## 1. The board

    Mathematical input
    -> notation parser (JSON CAS-Math IR, v0.1)
    -> expression IR
    -> definition and rule memory (axioms + learned procedures)
    -> strategy / conjecture generator (bounded search)
    -> exact mathematical operations (no floats)
    -> candidate conclusion
    -> PROOF CHECKER / COUNTEREXAMPLE CHECKER   (sole authority)
    -> commit verified result
    -> store episode, update strategy knowledge (via the RLP law)

## 2. The CAS-Math IR (v0.1 subset)

    Number      Natural / Integer / Rational, exact (1/3 stays 1/3)
    Symbol      x, y, n
    Expression  var, num, add, mul, pow (non-negative integer exponent),
                neg
    Equation    left expression, right expression
    Relation    equal, less_than, greater_than (exact comparison)
    ProofStep   rule applied, focus, resulting expression
    Conjecture  proposed statement, evidence, status
    Counterexample  assignment falsifying a claim, with exact witness values
    Strategy    ordered problem-solving procedure

Every claim carries a status (given / assumed / derived / conjectured /
verified / disproved / unknown) and provenance (teacher / book /
prior_proof / generated_conjecture / verified_calculation).

## 3. The exact-math rule

Exact operations wherever exactness is possible. 1/3 stays 1/3; it does
not silently become 0.333333. Approximate values must carry value, error
bound, precision, method, and assumptions - v0.1 implements exact
arithmetic only and refuses approximation.

    CJT gain does not prove an equation.
    CAS-Ohm residual does not prove a theorem.
    High activation does not mean mathematically true.
    Foundation satisfaction does not mean mathematically true.

## 4. Axioms versus procedures

Axioms are trusted, versioned, and protected (definitions may not
change silently). Procedures are LEARNED transformations: a procedure
step is valid only if the checker confirms the transformation is
equality-preserving - by exact structural application plus exact
evaluation on sample points. A procedure that fails the sample check is
invalid at that step, which is how an overgeneralized rule is caught.

## 5. The checker is the sole validity authority

    walk proof steps in order (oscilloscope walk-down)
    step continuity: each step starts where the previous ended
    axiom steps: exact structural application, canonical equality
    procedure steps: exact structural application, canonical equality,
        and exact sample validation
    final: canonical equality with the target
    verdict: VERIFIED or REJECTED with first_invalid_step

Polynomial identities over exact rationals are decided exactly by
canonical expansion (sound and complete for that class). Sample
validation of procedures is a sound rejection test, not a substitute
for the canonical check.

## 6. Counterexamples

A counterexample immediately invalidates a universal conjecture under
the same declared assumptions. The generator searches the declared
domain exactly and returns the witness with its exact evaluations.

## 7. Learning from a mathematical mistake

    attempt proof -> checker REJECTED at the first invalid step
    -> diagnose the guilty rule and fault class
    -> propose repairs from the lesson library
    -> sandbox descendants (held-out + regression tasks)
    -> acceptance law: gain, no protected regression, checker untouched,
       deterministic, sealed evidence, rollback preserved
    -> promote or reject
    -> corrected proof verified by the same unchanged checker

## 8. Authority invariants (verbatim from the charter)

    No mathematical conclusion becomes VERIFIED without an accepted
    proof object or independently checked computation.

    A candidate branch may propose a theorem but cannot store it as a
    verified theorem.

    A failed proof may update strategy memory but may not alter the
    proof rules.

    The component proposing a mathematical improvement may not modify
    the benchmark or checker used to judge that improvement.

    Approximate values must carry precision and error information.

    A counterexample immediately invalidates a universal conjecture
    under the same declared assumptions.

    Definitions, axioms, and mathematical theories are versioned and
    may not change silently.

    The proof kernel is outside autonomous write authority.

## 9. Non-goals (v0.1)

No real-number or interval arithmetic, no trigonometric or analytic
functions, no automated theorem proving beyond bounded structural
search over the declared rule set, no claims of mathematical novelty
(novelty requires validity AND independent checking of prior
knowledge).
