# CAS-Ohm compiler calculations — 2026-09-21

The active CAS compiler now calculates attention flow, required Drive, and
effective constraint through named operations. PCBA, synthetic-data and CAS-RPA
connections are prepared and exercised with declared examples. This is tested
software arithmetic. It does not measure Helm, run a circuit, control a model,
or show that Helm learned these calculations.

## Run the supplied example

From the repository root of this isolated checkout:

~~~powershell
$source = Get-Content -Raw 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/cas_ohm_evidence/attention_3.cas'
& 'C:\Python314\python.exe' dist/cas-offline/cas.py $source --json --no-color --no-terminal-diagram
~~~

The actual expression is:

~~~cas
ohm_flow(
  ohm_drive("12", ohm_scale("demo-linear", "declared_drive", "declared_attention"), "design", "demo:first"),
  ohm_constraint("4", ohm_scale("demo-linear", "declared_drive", "declared_attention"), "design", "demo:second")
)
~~~

It returns a valid compiler artifact whose calculated attention value is the
decimal string **"3"**, with exact fraction **3/1**. The AST contains the named
call; the bytecode executes CALL. This is not a separately printed mock result.
Changing only constraint from **"4"** to **"6"** calculates **"2"**.

The sibling **invalid_zero_constraint.cas** supplies constraint **"0"**.
It returns an invalid artifact with **OHM_ZERO_CONSTRAINT**, no result, and
offline CLI exit code **1**. A successful offline CLI call exits **0**.
The direct compiler artifact, CLI stdout/stderr and source identities are
recorded in **cas_ohm_evidence/**.

## Quantity contract

| Constructor or operation | Meaning |
|---|---|
| ohm_scale(id, drive_unit, attention_unit) | Declare one coherent ratio-scale convention |
| ohm_drive(value, scale, origin, reference) | Supply Drive potential |
| ohm_attention(value, scale, origin, reference) | Supply attention flow |
| ohm_constraint(value, scale, origin, reference) | Supply opposition to flow |
| ohm_flow(drive, constraint) | Calculate attention I = V / R |
| ohm_required_drive(attention, constraint) | Calculate required Drive V = I × R |
| ohm_effective_constraint(drive, attention) | Calculate effective constraint R = V / I |

The optional compiler types are **ohm_scale**, **ohm_drive**,
**ohm_attention**, and **ohm_constraint**. Existing CAS symbols retain their
meanings. Use named operations for Ohm arithmetic.

The declared convention is **cas.ohm.declared-linear/0.1**. Constraint units are
derived as Drive units divided by attention units. Both operands must have
the same complete scale descriptor, not merely the same name. There is no
automatic unit conversion or proof that the caller's calibration is valid.

This choice is deliberate. The book and identified extensions share the three
equations but use different ranges, normalizations and measurement procedures.
A bare state such as **^8^C_{F2}|A** supplies none of these numeric magnitudes.
The example values are design declarations, not a book-wide numerical scale.
See **cas_ohm_evidence/SOURCE_REVIEW.md** for the source comparison.

Every supplied quantity requires an origin and a reference:

- **design**: a declared setting or illustrative value.
- **supplied_observation**: a caller-supplied observation with
  **CALLER_SUPPLIED_UNVERIFIED** status. The module did not collect or verify it.
- **calculated**: produced by an operation, with complete input lineage.
  The input constructors do not accept this origin.

Every report keeps its quantity, scale, source reference, input representation,
exact value and calculation history. Reports state **NO_MEASUREMENT_PERFORMED**,
**NOT_CONNECTED**, and **NOT_ASSESSED** for measurement, control and semantic
outcome. More calculated attention is not proof of a correct cognitive answer.
Effective constraint is the stated ratio; it does not identify a hidden cause.

## Numbers and invalid inputs

Use decimal strings for exact decimal input. Integer and finite float inputs
also work; floats explicitly retain their binary-float-to-decimal origin.
The compiler's existing numeric-literal semantics are unchanged.

Arithmetic uses exact rational numbers. The display uses 40 significant decimal
digits and indicates rounding; the exact numerator and denominator remain
available as strings. Output is independent of ambient Decimal settings.

Missing values, booleans, NaN, infinity, negative quantities, wrong quantity
types, mismatched scales and incomplete provenance fail. Both divisions refuse
zero denominators, including 0/0. No epsilon, clipping, normalization, gain or
voltage-drop rule is silently added. Multiplication by zero is allowed and
labels the degenerate design case; it does not make the inverse ratio defined.

Limits protect the calculation and its records: 512 characters for decimal
text, 4096 bits for a rational numerator/denominator, 16 levels and 256 nodes
for input lineage. These are software limits, not physical or book ranges.

## Prepared connections

**PCBA:** **pcba_resistor_flow(...)** first requires the board to pass the
existing static checker. It obtains the selected supported Resistor's exact R
literal from that board. The caller must declare the Drive, compatible units
and provenance. It calculates one resistor's flow; it does not infer total,
series or parallel resistance from a list of parts. Board execution and
full-book validation stay open.

**Synthetic data:** **make_synthetic_demo(expression, reference_id)** accepts a
bounded named Ohm expression and calls the actual compiler. It emits separate
input and reference-target records with content- and implementation-bound IDs.
Targets are **REFERENCE_CALCULATED_NOT_LEARNED**. This is a standalone fixture
generator; existing Q3 datasets, splits, manifests and learner objectives are
preserved. Training Helm to predict these results remains a separate task.

**CAS-RPA:** **project_cas_rpa(rows)** validates and replays each calculation,
then retains explicitly supplied parent/child records without aggregation.
The separate **cas.rpa.ohm-projection/0.1** format is preparatory. It does not
pretend to be a complete AtlasNode, a connected atlas UI, a measurement record
or a live **cncm.cas-ohm-stage/0.1** event. Parent/child links remain caller
declarations; a valid formula is not evidence for the link.

Runnable Python calls for all three are in
**cas_ohm_evidence/run_demonstrations.py**. Run from this lab directory:

~~~powershell
& 'C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe' cas_ohm_evidence/run_demonstrations.py
~~~

PCBA requires Pydantic 2, available in the installed Python 3.12 environment.
The numeric module, compiler and offline CLI require no new third-party package.

## Historical data and distribution

The active compiler ships with **api/notation/cas_ohm.py** in the scaffold,
offline directory and offline ZIP. These two files form the implementation;
hashing only compiler.py no longer identifies all Ohm behavior. The evidence
receipt records both hashes and checks exact source/folder/ZIP equality.

The Q3 v0.7 generator and PCBA state parser retain the byte-pinned pre-Ohm
compiler at **pinned_sources/compiler_pre_ohm_61ed5a45.py**. Q3 uses
**historical_compiler.py**; PCBA retains its independent, cached state loader
and verifies the same pin on loading. The snapshot's LF SHA-256 remains
**61ed5a45970459e49a6948282ce4060e7c3d3d3f7042078228bc97ff252b2527**.
The Q3 loader verifies the pin even when cached and never falls back to current
compiler code. Frozen data and contracts are not repointed to the new compiler.

The Rust engine is unchanged. This branch is an engineering continuation,
**codex/helm-cas-ohm-20260921**, and is not a Helm release or deployment.
Verification commands, results and initial failed invocations are in
**cas_ohm_evidence/VERIFICATION.md**.
