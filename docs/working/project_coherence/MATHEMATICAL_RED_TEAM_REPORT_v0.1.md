# Project Coherence mathematical red-team report v0.1

Status: `INTERNAL RED TEAM COMPLETE / INDEPENDENT REVIEW OPEN`

Date: 2026-08-04

This report audits load-bearing claims in the registered TKS v7.4 corpus, the conservative Noetic Topos source, and the proposed Project Coherence transfers. It is an internal adversarial review, not external peer review or proof-assistant verification.

## 1. Disposition summary

The current materials contain several correct standard constructions, but blanket theorem inheritance is not defensible. Four clusters require correction or quarantine before academic citation:

1. ACBE and RPM add no nonmaximal covers to the stated Noetic topology; proposed separate modalities are trivial or identical under the present generators.
2. The proposed moving-projector capacity transfer omits an essential intertwining/isometry hypothesis.
3. The deterministic-lift norm, occupation trace, partial-isometry, and projector claims contain explicit false statements.
4. Several spectral, MVR, normal-form, stochastic-product, and probabilistic-gluing claims lack required hypotheses or have finite counterexamples.

The governing migration records are in `INITIAL_MIGRATION_MATRIX_v0.1.json`. Nothing below is admitted to Ring 1 or Ring 2 by this report.

## 2. Decisive finite counterexample

Let `f:{1,2}->{1,2}` be the constant map `f(1)=f(2)=1`. Its standard basis lift is

```text
A_f = [1 1]
      [0 0].
```

Then

```text
A_f^2 = A_f,
A_f* A_f = [1 1]
             [1 1],
||A_f|| = sqrt(2),
tr(A_f* A_f) = 2,
rank(A_f) = 1.
```

This single example establishes all of the following:

- the claimed universal bound `||A_f|| <= 1` is false;
- idempotence does not imply partial isometry;
- idempotence does not make `A_f` an orthogonal projector;
- `tr(A_f* A_f)` is not `rank(A_f)`; and
- `A_f* A_f` is not the image-support projector.

For any function `f:X->Y`, the correct standard-lift formula is

```text
||A_f|| = sqrt(max_y |f^{-1}(y)|).
```

Also, `tr(A_f* A_f)=|X|`. Input-fiber collisions are represented by `A_f* A_f`; output support belongs on the `A_f A_f*` side and still requires the correct normalization if an orthogonal projector is wanted.

Required disposition: retract or replace the affected theorem/corollary/proposition cluster and publish an explicit corrigendum.

## 3. Noetic coverage and modalities

### 3.1 ACBE and RPM clauses are maximal-sieve clauses

In the conservative Noetic Topos source:

- Noe-Cov-2 requires the sieve to contain all designated ACBE descent maps. Reflexivity includes `iota_i,i^(W,W)=id_Xi`. A sieve containing an identity is maximal.
- Noe-Cov-3 requires the sieve to contain `epsilon_X:R(X)->X`. Because `epsilon_X eta_X=id_X` and a sieve is closed under precomposition, the sieve also contains `id_X` and is maximal.

Therefore ACBE and RPM contribute no nonmaximal covers. Together with Lemma 6.3, this gives

```text
J_noe = J_joint-surjective.
```

The source theorem that `J_noe` is a Grothendieck topology remains valid under its axioms, but the semantic claim must be narrowed: the stated topology does not separately retain ACBE or RPM provenance.

### 3.2 Separate modalities do not work as proposed

If the current ACBE clauses alone generate a topology, it is the coarsest/trivial topology. The same is true for the RPM clauses. Their sheafification modalities are therefore identity modalities and commute vacuously.

If both are augmented with the same jointly-surjective observational coverage, they generate the same topology and again cannot provide noncommuting modalities.

Any Noetic Topos 2.0 claim of distinct or noncommuting ACBE/RPM modalities must change the construction. Defensible options include colored/marked coverage not erased by ordinary sieve generation, nontrivial generator families that omit identities/split epis as sufficient covers, and explicit coherence plus a concrete noncommutation witness.

## 4. Subcanonicity and marked objects

The current axioms do not imply that the jointly-surjective topology is subcanonical. A finite countermodel is the pullback-closed category whose objects are sets of size at most two and whose morphisms are injections. The two point-inclusions jointly cover the two-point set. Compatible local injections into a singleton do not extend to a global injection from the two-point set.

Consequences:

- a site object `X_i` is not itself an object of `Sh(Noetica,J)`;
- a representable presheaf `yX_i` need not be a sheaf;
- making the topology finer cannot repair a representable that already fails a sheaf condition; and
- a marked successor should use `a_J(yX_i)` explicitly, prove subcanonicity after changing the site/coverage, or define a marked-site construction rather than silently marking bare `X_i` inside the topos.

## 5. Projector transfers

### 5.1 Safe standard kernel

For common finite rank `d>0`, orthogonal self-adjoint projectors `P_i` in one real or complex Hilbert space define

```text
k(i,j) = tr(P_i P_j)/d.
```

This is a normalized positive-semidefinite Hilbert-Schmidt Gram kernel with `0<=k<=1` and `k(i,i)=1`. For complex coefficients the quadratic form uses conjugation. The kernel need not be strictly positive definite.

Disposition: `STANDARD_SPECIALIZATION`, subject to a direct proof and correct citation. It is not evidence that a model's latent states actually form those subspaces.

### 5.2 Capacity transfer has a missing hypothesis

The prior CAS formulation used projector rank and code coherence but omitted the manuscript's essential condition. Proposition 4.1 requires, among its data, an isometry

```text
B: V -> W tensor V
```

and vectors `ell_x` satisfying

```text
B*(ell_x tensor u) = sqrt(Lambda) u
```

for every `u` in `im(P_x)`, with `Lambda>s` and the stated code relation.

Without that condition, take two orthogonal `ell_x`, `D=d=1`, `P_x=I`, `s=0`, and `Lambda=1`. The transferred bound would assert `2<=1`.

Disposition: `PROOF_GAP`, Ring 4. A CAS-specific intertwiner must be constructed and verified before any capacity specialization is stated.

## 6. Other theorem obligations

| Severity | Cluster | Audit finding | Required correction |
|---|---|---|---|
| Critical | Deterministic lift | Norm bound is false; exact norm depends on maximum fiber size. | Replace theorem and add finite counterexamples/tests. |
| Critical | Occupation/projector | Trace, image-support, idempotent partial-isometry, and orthogonal-projector claims are conflated. | Retract or replace affected records. |
| High | Spectral/MVR dynamics | Deterministic lifts are generally nonnormal. Every total-map lift on a nonempty finite set has spectral radius one; generic tables below/above one lack concrete maps. | Supply maps and use correct nonnormal theory. |
| High | Alternating dynamics | Alternating inverse pairs can give period-two partial products rather than convergence. | State sequence hypotheses or downgrade. |
| High | Exact normal forms | Finiteness does not prove termination or confluence. | Prove both, or define a fixed-order shortlex representative and renormalize after composition. |
| High | Finite semigroups | Common semigroup typing requires all generators to be endomaps of one carrier. Arbitrary time-varying generator sequences need not be eventually periodic. | Use a finite category/semigroupoid for typed maps; restrict power theorems to a fixed element. |
| High | RPM computation | Renaming does not create a monad; the base category, coproduct/failure type, unit, multiplication, and laws are required. | Define the monad and any bridge to realization `R`, or state that none is known. |
| High | Probabilistic gluing | Pairwise compatible marginals may have no global joint distribution. | Require junction-tree/acyclic structure, obstruction vanishing, or a feasibility theorem. |
| Medium | Approximate cancellation | Local error can be amplified by surrounding operator norms. | Name a reverse arrow unless a true inverse exists; add contraction/norm and composition-order hypotheses. |
| Medium | Stochastic RPM | `p_D p_W p_P` is a chain-rule product only when later terms are conditional probabilities. | Type marginal versus conditional fields and state independence only when established. |
| Medium | Cellular Laplacian | `L=delta*delta` needs a finite linear cellular sheaf and chosen inner products. | Do not apply it directly to arbitrary Set-valued sheaves or stochastic kernels. |
| Low | Noetic dimension | Valid as a declared bookkeeping score, not a standard graph/image dimension. | Retain the caveat or rename it `noetic dimension score`. |

## 7. Safe finite results

The following standard result is safe at the correct type:

- for a function on an `n`-element set, `f^(n!)` is idempotent;
- for an element `s` of a finite semigroup `S`, `s^(|S|!)` is idempotent.

This concerns powers of one fixed endomorphism/semigroup element. It does not imply that an arbitrary controlled sequence of different generators becomes periodic.

## 8. Novelty boundary

- Standard mathematics: the projector Gram kernel, finite-semigroup idempotent powers, norm-aware telescoping estimates, the probability chain rule, and linear cellular-sheaf Laplacians.
- Conditional specialization: the moving-projector capacity theorem, but only after the exact intertwiner hypotheses are realized in CAS.
- Generic construction: a small site with a Grothendieck topology yields a Grothendieck topos. The current ACBE/RPM clauses do not add Noetic topological content.
- Potentially original CAS work: a typed quotient with proved normal forms; a nontrivial marked/modal site with an explicit noncommutation witness; a CAS-specific projector/intertwiner; or a quantitative contextual-gluing theorem validated on CAS evidence.

## 9. Required next review

Before Gate 1 can close:

1. transcribe every affected source statement and page/section identity;
2. publish the finite counterexamples as regression fixtures;
3. assign `CORRECTED`, `DOWNGRADED`, `REFUTED`, or another migration disposition item by item;
4. obtain independent specialist review in category theory, operator theory, probability, and theoretical computer science; and
5. create proof-assistant artifacts for the corrected load-bearing finite results.

This report changes no empirical or product-claim status.
