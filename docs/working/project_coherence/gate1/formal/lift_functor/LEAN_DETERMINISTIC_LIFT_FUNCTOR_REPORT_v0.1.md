# Deterministic Standard-Basis Lift — Lean Proof Report v0.1

## Control status

- Evidence ring: **Ring 4** (formal/executable seed evidence only).
- License status: **NOT LICENSED**.
- Review status: **PRESENT; internal kernel verification passed**.
- Public-release status: **NOT AUTHORIZED**.
- Claim scope: the exact finite, typed, standard-basis statements listed below.

## Formal model

For natural numbers `m` and `n`, `FiniteMap m n` contains a total typed map
`Fin m -> Fin n`.  For a column `x : Fin m`, the deterministic lift sends the
standard basis vector `e_x` to `e_(f x)`.  Its natural-number entry semantics
is therefore

```text
A_f(row, column) = 1  if row = f(column)
                   0  otherwise.
```

The source and target sizes occur in the types, so an ill-typed composition
cannot be supplied to `FiniteMap.comp`.

## Kernel-checked results

| Lean declaration | Exact result | Axiom audit |
|---|---|---|
| `FiniteMap.comp_id_left` | left identity for typed finite maps | none |
| `FiniteMap.comp_id_right` | right identity for typed finite maps | none |
| `FiniteMap.comp_assoc` | associativity for typed finite maps | none |
| `lift_entry_identity` | `A_id = I`, at every entry | none |
| `lift_basis_identity` | the identity lift fixes every basis vector | none |
| `lift_basis_composition` | `A_(g o f)` agrees with successive lift action on every basis vector | none |
| `lift_entry_eq_one_iff` | an entry is one exactly at the mapped row | none |
| `lift_entry_composition_support` | composite support equals the relational product of factor supports | none |
| `lift_entry_eq_zero_iff` | an entry is zero exactly away from the mapped row | none |

The audit file uses Lean's `#print axioms` command for every declaration in the
table.  Lean reported that all nine declarations depend on no axioms.  The
module contains no `axiom`, `sorry`, or `admit` declarations.

## Composition boundary

This module deliberately does **not** define a finite scalar sum or a generic
matrix-multiplication operator.  Consequently it does not claim a literal
formal theorem of the form

```text
A_(g o f)(z,x) = sum_y A_g(z,y) * A_f(y,x).
```

Instead, `lift_entry_composition_support` proves the exact entrywise
relational-product equivalent:

```text
A_(g o f)(z,x) = 1
  iff there exists y with A_g(z,y) = 1 and A_f(y,x) = 1.
```

Together with the exact basis-action equality in `lift_basis_composition`, this
is sufficient for the deterministic standard-basis identity/composition lane.
A later finite-sum matrix layer may bridge this result to numerical matrix
multiplication, but that bridge remains **OPEN** here.

## Explicit nonclaims

This report does not establish:

- a generic finite-sum or semiring matrix multiplication theorem;
- a linear extension from basis vectors to arbitrary vectors;
- operator-norm, singular-value, Gram, rank, or trace theorems;
- a categorical functor into a formally defined category of modules;
- equivalence with the Python reference implementation;
- any full TKS v8, Noetic Topos 2.0, CAS, or Harness theorem.

Those broader claims remain **OPEN** unless separately evidenced.

## Reproduction

The isolated toolchain is pinned by `formal/lean/lean-toolchain` to Lean
`4.32.1`.  With
`ELAN_HOME=C:\Users\wakil\.codex\tools\project-coherence-elan`, run from
`formal/lean`:

```powershell
lake build PSR8Formal.DeterministicLiftFunctor
lake env lean DeterministicLiftFunctorAudit.lean
```

Observed tool identities:

- Lean `4.32.1`, commit `f054605aea4b840552cca2e725580bffd1e1b704`, Release.
- Lake `5.0.0-src+f054605` with Lean `4.32.1`.

The adjacent JSON manifest binds the exact source, audit, project-pin, and
report bytes by SHA-256.
