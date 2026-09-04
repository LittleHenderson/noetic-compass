# CAS-Math MVP v0.1

Status: normative bounded contract for the first post-kernel mathematical
domain described by the in-homebase `cas_reasoner.txt` at lines 6904-7691.

## 1. Authority split

CAS/CCB-M1 may parse a problem, propose a strategy, propose proof steps, and
request bounded counterexample search. It does not decide whether its own work
is valid.

`cncm.math-checker/0.1` is the bounded protected exact checker. It is a pure
reconstruction service with no state writer, tool, network, benchmark-editing,
theory-editing, or autonomous patch authority. A caller submits a
`MathStepProposal`; only the checker creates a `MathStepReceipt`. The proposal
wire has no `verified` field. Caller-created claims cannot assert `DERIVED` or
`VERIFIED`. Checked claims bind a receipt ID, and any later use of such a claim
requires semantic re-execution of its complete registered derivation chain.
Parsing a standalone checked-claim dictionary does not establish trust; the
containing proof bundle must be re-executed.

Current integration status is `IMPLEMENTED-BOUNDED/STANDALONE`. Exact solving,
step checking, semantic result re-execution, and bounded counterexample search
execute today. Math receipts are not yet fields in RRK `MachineState` and are
not yet committed through a versioned RRK math intent. That later integration
must preserve the existing transaction coordinator as sole writer.

## 2. Frozen exact scope

Implemented:

- exact integers and canonical rational numbers;
- ASCII variables;
- addition, subtraction, multiplication, unary signs, parentheses, and
  division with a nonzero guard;
- equality and strict less-than statements;
- exact evaluation and simplification;
- add, subtract, multiply, and divide on both sides;
- equality and less-than transitivity;
- substitution backed by cited equality claims;
- exact one-variable linear equations;
- final solution verification by substitution into the original equation;
- deterministic bounded-integer counterexample search over one to three
  variables;
- immutable claims, proposals, receipts, proof traces, hashes, and independent
  semantic re-execution of retained linear results and bounded counterexample
  searches.

Modus ponens remains an existing CAS-Sem operation. It is not silently
duplicated as a different mathematical truth rule.

Not implemented in this contract:

- implicit multiplication (`3x`), exponents, functions, decimal literals, or
  scientific notation;
- nonlinear equation solving, calculus, continuous theorem proving, advanced
  geometry, probability learning, textbook ingestion, or image equations;
- approximate arithmetic;
- autonomous definition, axiom, theory, checker, fixture, or benchmark changes;
- novelty or new-mathematics claims.

Unsupported work returns a typed rejection or terminal status. It must not be
approximated or guessed.

## 3. Notation grammar

```ebnf
statement  ::= expression relation expression EOF ;
relation   ::= "=" | "<" ;
expression ::= sum ;
sum        ::= product (("+" | "-") product)* ;
product    ::= unary (("*" | "/") unary)* ;
unary      ::= ("+" | "-") unary | primary ;
primary    ::= integer | identifier | "(" expression ")" ;
integer    ::= "0" | nonzero-digit digit* ;
identifier ::= letter (letter | digit | "_")* ;
```

Whitespace is insignificant. Multiplication is explicit. Operators are ASCII.
There is exactly one top-level relation in a statement. `/` is exact division;
`1/3` never becomes a floating-point approximation.

Default hard parser limits are 4,096 characters, 1,024 tokens, 4,096 AST
nodes, nesting depth 64, and 256 digits in one integer.

One proposal may cite at most 64 premises. Independent receipt validation
allows at most 128 derivation levels and 4,096 receipt rechecks, returning a
typed `BUDGET_EXHAUSTED` rejection instead of recursing without a bound.

## 4. Exact representation

`ExactRational(numerator, denominator)` rejects Booleans, floats, and a zero
denominator; normalizes the sign; divides by the greatest common divisor; and
stores zero only as `0/1`.

Expression kinds are:

- `integer`
- `rational`
- `variable`
- `negate`
- `add`
- `multiply`
- `divide`

Relations are `EQUAL` and `LESS_THAN`. Claim statuses are `GIVEN`, `ASSUMED`,
`DERIVED`, `CONJECTURED`, `VERIFIED`, `DISPROVED`, and `UNKNOWN`. Every claim
binds a theory identity, assumption IDs, provenance, and—only for `DERIVED` or
`VERIFIED`—the exact accepted derivation receipt.

The only current theory is `cncm.q-linear/0.1`, and the only current math branch
is `math_root`. Packet, claim, proposal, receipt, evidence, and semantic
re-execution must agree on those fixed identities. Content-derived claim,
proposal, and receipt IDs are recomputed at every supported object boundary.

## 5. Closed checker operations

- `EVALUATE_EXACT`
- `SIMPLIFY_EXACT`
- `ADD_BOTH_SIDES`
- `SUBTRACT_BOTH_SIDES`
- `MULTIPLY_BOTH_SIDES`
- `DIVIDE_BOTH_SIDES`
- `SUBSTITUTE`
- `TRANSITIVE_EQUAL`
- `TRANSITIVE_LESS_THAN`
- `VERIFY_LINEAR_SOLUTION`

The checker reconstructs the expected conclusion. Caller-supplied operation
names cannot extend this set. Division requires an exact nonzero divisor.
Scaling a strict inequality by a negative rational reverses the sides. A zero
scale is rejected. Substitution requires a cited admitted equality for every
replacement.

A `CONJECTURED`, `DISPROVED`, or `UNKNOWN` claim cannot support a verified
step. A `DERIVED` or `VERIFIED` premise cannot support a new step unless its
cited receipt chain re-executes exactly. Only `EVALUATE_EXACT` and
`VERIFY_LINEAR_SOLUTION` may issue `VERIFIED`; an intermediate transformation
may issue only `DERIVED`. Later valid-looking steps cannot repair an earlier
rejected step.

## 6. Linear solver

The bounded solver emits ordinary checked steps:

1. exact simplification;
2. subtraction of variable terms from both sides when required;
3. subtraction of the constant term from both sides when required;
4. division by the exact nonzero coefficient when required;
5. proof that the original premise is uniquely linear in exactly the requested
   variable, followed by independent exact substitution into that equation.

It distinguishes:

- `VERIFIED`: one exact solution with an accepted proof receipt;
- `UNDERDETERMINED`: both normalized sides are identical;
- `NO_SOLUTION`: variable terms cancel and constants disagree;
- `NEEDS_GUARD`: an exact guard, such as a nonzero denominator, is missing;
- `NEEDS_CAPABILITY`: content is outside the linear MVP;
- `INVALID_PROOF`: the protected checker rejected a generated step.

## 7. Counterexample search

Counterexample variables have explicit inclusive integer bounds. Search order
for each variable is zero (when in range), lower boundary, upper boundary, then
remaining integers ordered by absolute value and numeric value. Variables are
combined in declared order. Search is deterministic and stops at the first
falsifying assignment. Bound domains and their Cartesian product are generated
lazily; a large numeric interval cannot force allocation of the whole range
before `max_assignments` is enforced.

Statuses are `FOUND`, `NONE_WITHIN_BOUNDS`, `NEEDS_GUARD`,
`UNSUPPORTED_EXPRESSION`, and `BUDGET_EXHAUSTED`.

`FOUND` disproves that universal conjecture under the same guards and theory.
`NONE_WITHIN_BOUNDS` explicitly is not a proof. An undefined denominator is
`NEEDS_GUARD`; it is not silently skipped.

## 8. Non-negotiable invariants

- No conclusion is `VERIFIED` without an accepted receipt or exact checked
  computation whose receipt chain semantically re-executes.
- A candidate cannot self-promote a theorem.
- A failed proof may inform a later strategy but cannot alter checker rules.
- A proposer cannot modify its checker, benchmark, fixtures, bounds, or
  promotion threshold.
- Approximate values, when added in a future contract, must carry value, error
  bound, precision, method, and assumptions.
- Definitions, axioms, and theories are versioned and never change silently.
- M0 experience may be written after commitment; M1 strategy changes are
  proposals; M2 lemmas require proof; M3 theories require explicit versions;
  M4 checker changes remain outside autonomous write authority.

## 9. Required conformance evidence

The suite must cover rational canonicalization, frozen objects, parser limits,
unsupported syntax, every admitted checker operation, wrong conclusions,
zero division, inequality reversal, missing equality support, conjecture and
caller-status self-promotion, claim-map aliases, forged content IDs, forged
receipts, theory/branch substitution, nonlinear single-root attacks, guarded
transitivity, exact linear solution/identity/contradiction/capability cases,
deterministic counterexamples, search exhaustion, result tampering, and exact
semantic re-execution.
