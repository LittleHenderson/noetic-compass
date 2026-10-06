# TKS v7.4 theorem and claim corrigendum v0.1

Status: `INTERNAL AUDIT / OPEN / NOT FROZEN`

Date: 2026-08-04

License boundary: `NOT LICENSED`

## Result

The registered v7.4 corpus cannot support blanket theorem inheritance. The
deterministic-lift, finite-dynamics, graph-spectral, normal-form, representable-
sheaf, and several higher-structure claims require retraction or explicit
conditionalization. Three narrow corrections are internally verified: the
type-correct RPM coverage arrow, reduction to jointly-surjective coverage under
the stated axioms, and use of the open probability simplex as the smooth target.

This is an internal mathematical audit. It is not external peer review and does
not claim proof-assistant verification.

## Source and completeness boundary

The line-addressed source is the registered integrated text (SHA-256
`980ABA9F...F414A`); physical PDF pages refer to the registered 539-page
rendering (SHA-256 `1CE09D96...CA469`). The review/correction, referee-defensible,
and corrected-chapter overlays are used only within their registered scopes.

The deterministic surface scan found 1,258 numbered declarations:

| Kind | Count |
|---|---:|
| Axiom | 6 |
| Corollary | 60 |
| Definition | 768 |
| Lemma | 4 |
| Proposition | 181 |
| Theorem | 239 |

The surface-sequence digest is
`7666B6FCE1503321C0B2695EA4C21EA09B8B6585CF43B1DB0EFF69522F69915E`.
This is complete only for the recorded heading regex. The 29 records below are
the bounded load-bearing subset identified by the overlays and mathematical red
team; every unlisted declaration remains `OPEN` by default.

The integrated text also contains 84 unresolved `??` tokens on 71 lines. Until
those edges are resolved, its proof-reference graph is not citation-complete.

Visual inspection of physical PDF pages 253 and 313 confirms the audited norm
and occupation statements, but also shows malformed TeX fragments, duplicated
running-page numbers, a missing `begin{proof}` backslash, and the occupation
definition's `k in 1,...,22` despite the registered ten-noetic ontology. These
are source/rendering defects, not extraction artifacts, and must be repaired in
the publication source.

## Item-level dispositions

| ID | Source location | Short finding | Source status | Corrected status |
|---|---|---|---|---|
| TKS74-CORR-001 | lines 12-15; PDF p.3 | Blanket inheritance has no conservative-extension proof. | `RETRACTED` | `OPEN` |
| TKS74-CORR-002 | 84 placeholders on 71 lines | Cross-reference graph is incomplete. | `OPEN` | `OPEN` |
| TKS74-CORR-003 | lines 11981-12006; PDF p.361 | Noe-Cov-3 is type-correct with `epsilon_I:R(I)->I`. | `VERIFIED` | `VERIFIED` |
| TKS74-CORR-004 | lines 12016-12026; PDF p.362 | ACBE/RPM clauses reduce to jointly-surjective coverage. | `VERIFIED` | `VERIFIED` |
| TKS74-CORR-005 | lines 12032-12082; PDF pp.362-363 | General topos conclusion is conditional on a verified site. | `OPEN` | `VERIFIED` (conditional theorem) |
| TKS74-CORR-006 | lines 12332-12338; PDF p.373 | A representable is used as a sheaf without subcanonicity. | `RETRACTED` | `VERIFIED` (`a_J(yI)` repair) |
| TKS74-CORR-007 | lines 1593-1612; PDF p.32 | RPM state/failure monad is not typed over the stated category. | `OPEN` | `VERIFIED` only on a suitable closed base |
| TKS74-CORR-008 | lines 2324-2330; PDF p.56 | A finite endomap need not have a fixed point. | `RETRACTED` | `VERIFIED` (eventual periodicity) |
| TKS74-CORR-009 | lines 2340-2379; PDF pp.56-57 | Frequency entropy is conflated with one orbit's dimension. | `RETRACTED` | `OPEN` |
| TKS74-CORR-010 | lines 2514-2520; PDF p.62 | Finiteness does not force a strict contraction. | `RETRACTED` | `VERIFIED` (extra hypothesis required) |
| TKS74-CORR-011 | lines 2618-2631; PDF p.65 | Finite descent is valid; unique-attractor language is not. | `OPEN` | `VERIFIED` (greatest stabilized subset) |
| TKS74-CORR-012 | lines 2678-2685; PDF p.66 | Prefix-IFS attractor monotonicity is reversed. | `RETRACTED` | `VERIFIED` |
| TKS74-CORR-013 | lines 3611-3628; PDF p.94 | Repetition is conflated with constant-tail stabilization. | `RETRACTED` | `VERIFIED` (eventual periodicity) |
| TKS74-CORR-014 | lines 3990-4002; PDF p.106 | A nonreversible Markov difference is treated as a self-adjoint Laplacian. | `RETRACTED` | `OPEN` |
| TKS74-CORR-015 | lines 4021-4027; PDF p.107 | Orthogonal spectral decomposition lacks self-adjointness. | `RETRACTED` | `VERIFIED` (conditional spectral theorem) |
| TKS74-CORR-016 | lines 4067-4094; PDF p.108 | Average invariance, common invariance, and mixing are conflated. | `RETRACTED` | `OPEN` |
| TKS74-CORR-017 | lines 8317-8336; PDF p.253 | Universal lift norm bound `<=1` is false. | `RETRACTED` | `VERIFIED` (maximum-fiber formula) |
| TKS74-CORR-018 | lines 8464-8466; PDF p.258 | Idempotent lift is not necessarily an orthogonal projector. | `RETRACTED` | `VERIFIED` |
| TKS74-CORR-019 | lines 10305-10313; PDF p.313 | Occupation trace and support-projector identities are false. | `RETRACTED` | `VERIFIED` |
| TKS74-CORR-020 | lines 10589-10599; PDF p.320 | Product spectrum/norm claims omit normality and contraction. | `RETRACTED` | `OPEN` |
| TKS74-CORR-021 | lines 14745-14794; PDF p.460 | No rewrite system proves canonical normal forms. | `OPEN` | `OPEN` |
| TKS74-CORR-022 | lines 14805-14820; PDF p.461 | Alternating inverse partial products form a two-cycle. | `RETRACTED` | `VERIFIED` |
| TKS74-CORR-023 | lines 15084-15104; PDF pp.471-472 | Spectral table has no maps and contradicts total-map lifts. | `RETRACTED` | `VERIFIED` |
| TKS74-CORR-024 | lines 15492-15509; PDF p.491 | Quasi-category and Kan claims remain a program. | `OPEN` | `OPEN` |
| TKS74-CORR-025 | lines 15752-15886; PDF pp.506-507 | Open-simplex smooth target repairs the discrete-target defect. | `VERIFIED` | `VERIFIED` |
| TKS74-CORR-026 | lines 15875-15886; PDF p.507 | `dim(M)+rank(d sigma)` is a declared score, not a standard dimension. | `OPEN` | `VERIFIED` as a definition |
| TKS74-CORR-027 | lines 16384-16404; PDF p.525 | A later chapter reintroduces the finite-Idea manifold defect. | `RETRACTED` | `OPEN` |
| TKS74-CORR-028 | lines 1528-1534; PDF p.30 | Approximate dual cancellation has no norm or error bound. | `OPEN` | `OPEN` |
| TKS74-CORR-029 | lines 1671-1679; PDF p.34 | Kleene theorem is standard; its TKS model hypotheses are unproved. | `OPEN` | `VERIFIED` (conditional theorem) |

## Decisive finite fixtures

The two-state constant map `f(0)=f(1)=0` has standard-basis lift

```text
A = [1 1]
    [0 0].
```

It satisfies `A^2=A`, `||A||=sqrt(2)`, `tr(A* A)=2`, and
`rank(A)=1`. It is not self-adjoint, `A* A` is not a projector, and
therefore `A` is not a partial isometry. This single fixture decides records
017-020.

For the graph operator on functions, the same constant map gives

```text
Delta = P-I = [0  0]
              [1 -1].
```

For `x=(2,1)`, `x^T Delta x=1`, contradicting claimed negative
semidefiniteness. Its eigenvectors for `0` and `-1` are not orthogonal in the
stated Euclidean inner product, deciding records 014-015.

A two-state swap has no fixed point and yields a period-two orbit. It refutes
fixed-point existence and constant-tail stabilization. The permutation system
`{identity,swap}` never contains a strict contraction. Constant-0 followed by
adding constant-1 makes a prefix IFS attractor expand from `{0}` to `{0,1}`.

## Corrected core statements safe for the next gate

1. For a finite map `f:X->Y` with `A_f e_x=e_{f(x)}`,
   `||A_f||=sqrt(max_y |f^{-1}(y)|)` and
   `tr(A_f* A_f)=|X|`.
2. A finite deterministic orbit is eventually periodic. It converges to a
   fixed point only when its eventual period is one.
3. For a finite Hutchinson set operator, `H_S^n(X)` descends and stabilizes at
   the greatest reached fixed subset; uniqueness as a metric attractor requires
   additional hypotheses.
4. `Delta=P-I` is a generally nonnormal Markov difference. Orthogonal spectral
   theory requires a self-adjoint/reversible construction.
5. Use `a_J(yI)` for the marked Idea object unless the exact site is proved
   subcanonical.
6. Treat `dim(M)+rank(d sigma)` as a named noetic score, not as a standard
   geometric dimension.

## Gate 1 closure obligations

- Resolve all 84 placeholder tokens and duplicate theorem-number keys.
- Apply every `RETRACTED` or `CORRECTED` disposition to a versioned v7.4
  corrigendum source, not only this audit ledger.
- Freeze concrete typed maps before making MVR, spectrum, normal-form, or
  contraction claims.
- Add regression fixtures for every finite counterexample.
- Obtain independent category-theory, operator-theory, dynamics, domain-theory,
  and higher-category review.
- Produce proof-assistant artifacts for the finite-map norm, eventual
  periodicity, and finite Hutchinson stabilization statements.

Until those obligations close, the corrected v7.4 theorem record remains
`OPEN` as a release artifact.
