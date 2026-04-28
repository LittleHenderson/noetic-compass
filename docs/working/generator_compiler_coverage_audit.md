# Generator vs Compiler Coverage Audit

Worker C scope: documentation under `docs/working/` and non-synthesizer tests under `noetic-compass-scaffold/noetic-compass/tests/`.

## Purpose

This audit defines the compiler surfaces that generated CAS examples must satisfy during the compiler/generator catch-up. It is intentionally a compatibility gate, not a generator implementation plan: generator unit tests should still own randomization, templates, labels, and bucket mix behavior.

## Compiler-Accepted Surfaces Relevant to Generation

The public gate is `api.notation.compiler.compile_expression`. A generated `cas_expression` is compiler-compatible when it returns a valid artifact for valid examples, or a targeted invalid artifact for intentionally invalid training examples.

Relevant accepted surfaces:

- v7.4 baseline states: `^n^D_{Fk}`, `CO-n^D_{Fk}`, shorthand state refs such as `C2`, same-domain products, domain-descent relations, `RPM(Fk)`, `Phi<...>`, and multi-statement programs.
- v7.5 registers: register-neutral v7.4 expressions, state-level suffixes such as `^2^C_{F2}|A`, noetic-level suffixes such as `^2|T`, drive-level suffixes such as `F_2|A`, independent noetic/drive registers such as `^2|T^C_{F2|A}`, and valid register tokens `T`, `A`, `f`, `E`.
- v7.6 production semantics: `Theta(Omega_name) = coeff*primitive + ... -> Omega_name`, leakage products on the RHS, catalyst/inhibitor annotations before the arrow, state-vector literals, `Y_T`, `Y_A`, and `eta` yield queries. Recipe targets must be `Omega_*` tokens inside `Theta(...)` and on the RHS.
- v7.7 register multiplicity: register sets such as `^3^P|<A,f,T>` or Unicode angle equivalents, co-presence via `+`, explicit same-noetic emergent assignment via `(...) = ^n^D|Omega_name`, and Rule 4 rejection for bare same-noetic cross-register `*`.
- Meta-logic: canonical meta-sets (`Noetics`, `Domains`, `States`, `Registers`, `Foundations`, etc.), typed clusters (`NoeticCluster`, `StateCluster`, `StateVariantCluster`, `RelationCluster`), finite set operations, `Pullback` as finite meet/intersection only, `Product`, `CoverOf`, `PartitionOf`, `Coordinate`, tuple forms, membership/subset/cardinality assertions.
- Diagrams: every valid artifact may call `artifact.diagram()` and should expose graph nodes, edges, containers, and layout hints. Generation should not emit diagram-only syntax; diagrams are a projection of compiler-valid CAS.

## Coverage Matrix

| Surface | Generator bucket/source | Compiler status | QA gate |
| --- | --- | --- | --- |
| v7.4 single state `^n^D_{Fk}` | `v74_baseline` single-state branch | Accepted | Blocking compile case |
| v7.4 same-domain product | `v74_baseline` product branch | Accepted | Blocking compile case |
| v7.4 domain descent relation | `v74_baseline` relation branch | Accepted | Blocking compile case |
| v7.5 register suffix after full state | Desired register surface | Accepted | Blocking compile case |
| v7.5 independent noetic/drive registers | Expanded register surface | Accepted | Blocking compile case |
| v7.5 register before drive subscript, e.g. `^2^C|A_{F2}` | Legacy invalid shape generators must avoid | Not accepted | Strict xfail guardrail |
| v7.6 Omega recipe | Desired production surface | Accepted | Blocking compile case |
| v7.6 state-vector/yield query | Production support surface | Accepted | Blocking compile case |
| v7.6 bare production target, e.g. `Theta(goal)` | Legacy invalid shape generators must avoid | Not accepted | Strict xfail guardrail |
| v7.7 register set | Register multiplicity surface | Accepted | Blocking compile case |
| v7.7 same-noetic `+` co-presence | Rule 4 compliant generation | Accepted | Blocking compile case |
| v7.7 same-noetic `*` without emergent result | Intentional violation examples | Rejected with Rule 4 error | Blocking invalid guardrail |
| v7.7 same-noetic emergent assignment using `*` | Named emergent generation | Accepted | Blocking compile case |
| v7.7 same-noetic emergent assignment using `x` | Legacy invalid shape generators must avoid | Not accepted | Strict xfail guardrail |
| Meta-logic typed clusters | `v78_meta_logic` cluster families | Accepted | Blocking compile case |
| Meta-logic finite set operations | `v78_meta_logic` set-op families | Accepted with compiler tokens/aliases | Blocking compile case |
| Meta-logic covers/partitions/products | `v78_meta_logic` higher constructors | Accepted | Blocking compile case |
| Diagram projection | Any valid compiled representative | Accepted | Blocking diagram smoke case |

## QA Gate

Added `noetic-compass-scaffold/noetic-compass/tests/test_generator_compiler_coverage_gate.py`.

The gate has three roles:

- Blocking valid-surface cases: representative generated-style expressions across v7.4, v7.5, v7.6, v7.7, meta-logic, and diagrams must compile.
- Blocking invalid-surface guardrail: a deliberate Rule 4 violation must fail compilation, preserving supervised invalid-example semantics.
- Strict xfail guardrails: legacy generator-output shapes that are not compiler-compatible are recorded as expected failures. If the compiler intentionally begins accepting one of those forms, pytest reports XPASS so the audit can be updated and the row can graduate to blocking.

## Remaining Gaps

- Current generators should continue emitting compiler-recognized order for v7.5 registers: `^n^D_{Fk}|R` or independently registered forms, not `^n^D|R_{Fk}`.
- Current generators should continue emitting v7.6 recipe targets as `Theta(Omega_name) ... -> Omega_name`, not bare `Theta(name) ... -> name`.
- Decide whether `state_<id>` recipe prerequisites are a stable accepted shorthand or should remain banned in favor of explicit state primitives such as `^n^D`.
- Current generators should continue avoiding `x` as a cross-register separator unless compiler support is deliberately added in a separate parser task.
- Keep meta-logic generator templates encoded and emitted in compiler-recognized token forms; ASCII aliases such as `union`, `intersect`, and `setminus` are safer for generated fixtures when encoding is uncertain.
- Add fixture-based integration once generator output snapshots stabilize. The current gate uses representative static expressions plus direct generator tests to avoid overfitting to random output.
