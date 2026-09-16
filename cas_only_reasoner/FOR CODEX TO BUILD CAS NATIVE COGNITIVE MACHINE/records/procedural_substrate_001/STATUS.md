# Checked procedure substrate: implemented, not native integration

The new isolated modules execute an input-dependent rational procedure and check
its proposed solution using the existing CAS-Math substitution checker. They do
not change `MachineState`, install a native skill, resume an RPM caller, or grant
new authority to runtime 0.1.0.

`cncm/procedural_substrate.py` admits exactly six instructions: load three distinct
inputs, add or subtract two, divide by the third, and emit the computed register.
The 12 forms contain no answer literals, lookup, imports, loops or dynamic code.
Canonical rational text is bounded before integer parsing; conservative integer
growth checks run before multiplication. Default caps are 128 input bits and
512 intermediate bits. Resource refusal may reject a mathematically reducible
expression; admission never relies on reduction after an oversized allocation.

`cncm/procedural_qualification.py` selects one form using two development cases,
then separately checks eight fixed engineering cases plus two zero-coefficient
refusals. The selected form computes `(c-b)/a`; the checker independently
substitutes its result into `a*x+b=c`. The ordinary linear solver does not produce
the candidate answer. Each later call still requires its own check.

The case sets are disjoint, public fixtures. They are not a secret benchmark,
external examiner custody, universal correctness proof or neural learning.
Candidate provenance is self-described, not authentication. Qualification
receipts are reconstructed by execution; a future native coordinator must repeat
that reconstruction, authenticate its own permitted issuer boundary, charge all
work, and perform the installation transition itself.

Every checked call binds artifact, input, caller, branch, theory and checker.
The old checker retains its fixed internal math branch; the outer binding names
the real caller without relabeling the old proof. Replay compares reconstructed
canonical JSON so booleans/floats cannot pass as integer fields by Python equality.

Evidence:

- `pure_tests.xml`: 37 substrate tests.
- `qualification_tests.xml`: 30 qualification tests.
- `regression_tests.xml`: 180 tests and 387 subtests passed, including the above
  and existing authority, reasoning, hardening, math and schema checks.
- The first broader run found an outdated schema inventory: the two new schema
  names were absent. `regression_tests_initial_schema_inventory_failure.xml`
  preserves that failure; the inventory now explicitly includes both schemas.
- `candidate_reproduction.json`: all 12 candidate development results, selected
  bytes, qualification, two example checks, and 768 comparisons against Python's
  independent `fractions.Fraction` implementation (576 results, 192 zero-divisor
  refusals).
- `fresh_process_replay.json`: a separate Python process loaded and reproduced
  that source-bound bundle. This proves candidate-byte reuse, not native journal
  recovery, installed memory, a suspended caller or behavioral rollback.

The native continuation plan is
`research/CAS_META_2_COMPOSITION/records/vision_continuation_20260916/NATIVE_PROCEDURE_INTEGRATION_PLAN.md`.
Next work must implement the versioned single-writer state and acquisition
transitions, qualified installation, exact caller continuation with conserved
budget, semantic journal replay, retained neighboring behavior, and rollback.
None of those gates is closed by this substrate.
