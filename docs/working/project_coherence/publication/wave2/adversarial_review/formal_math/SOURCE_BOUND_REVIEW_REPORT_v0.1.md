# Independent adversarial review of the Wave 1 formal-mathematics lane

Review version: `v0.1`

Control status: `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

Reviewed commit: `3c8491db6f5559cf090909d9de0efa03d924f53f`

Review date: 2026-08-05

## 1. Outcome

The two formal-mathematics publication deltas are mathematically viable as
Ring-4 research drafts. This adversarial pass found **no false theorem, failed
counterexample, reversed inequality, type collapse, or unsupported empirical
conclusion** among the twenty local claim records.

That is not a submission recommendation. Three source/evidence-interface
changes block submission or lead-owned registry integration:

1. Paper 1 must choose between the *category of finite sets* and a genuinely
   *finite category on a frozen finite object catalog*. The current phrase
   "a finite category" is not justified by the later definition whose objects
   are named finite sets without a finite object universe.
2. `PUB-P1-THM-004` says `STANDARD_RESULT_CITED`, but no finite-semigroup
   citation is attached. The mathematics is correct; the evidence label is not.
3. The OpenAI artifact is verifiably a public technical manuscript with no
   peer-review receipt in the reviewed source set. The stronger categorical
   label "unrefereed" should be replaced by "peer-review status unverified / no
   receipt in the reviewed source set" unless attributable status evidence is
   added.

These are publication blockers, not reasons to delete the safely quarantined
drafts. Every claim remains `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD`.
The detailed dispositions are in
`CLAIM_BY_CLAIM_DISPOSITION_MATRIX_v0.1.json`, and no Wave 1 file was rewritten.

## 2. Source identity and review boundary

The review read the exact nine files under
`docs/working/project_coherence/publication/wave1/formal_math/`. Their byte
lengths and SHA-256 values are recorded in
`REVIEW_SOURCE_INVENTORY_v0.1.json`. The upstream manifest binds eight of those
files and excludes itself; this review separately binds the upstream manifest.

The nested source inventory was replayed rather than trusted by declaration:

| Source class | Checked | Exact byte/hash matches | Missing or mismatched |
|---|---:|---:|---:|
| Repository sources | 42 | 42 | 0 |
| External registered sources | 7 | 7 | 0 |
| Wave 1 formal-math artifacts | 9 | 9 | 0 |

The primary moving-projector source was the local file
`C:\Users\wakil\Downloads\ten-proofs-oai.pdf`, SHA-256
`64B900D5FAE6FE22F2AE1B8E3B712D20055194A6C81CF343A2455E5898AC7DD6`.
The current public artifact at
<https://cdn.openai.com/pdf/ten-proofs-oai.pdf> returned the same 2,266,371
bytes and the same hash. The relevant source pages were rendered and inspected:
physical PDF pages 48-49, printed pages 46-47, containing Chapter 2,
Proposition 4.1 and its proof.

Hash identity establishes which source was reviewed. It does not establish
novelty, peer review, semantic fidelity, empirical validity, or publication
authority.

## 3. Review method

The review used five independent checks:

1. **Claim/source reconciliation.** Every one of the twenty matrix records was
   matched to its paper statement, evidence map, source or citation reference,
   counterexample, and retained obligation.
2. **Direct mathematical reproof.** The finite-category laws, deterministic
   lift formulas, fixed-power result, denotational shortlex argument, finite
   set-operator result, approximation estimate, projector geometry, simplex
   bound, Welch specialization, and source Proposition 4.1 were derived again.
3. **Adversarial examples.** The two-state deterministic lift and weakened
   moving-projector transfer were recomputed, including nonrealizability of the
   omitted intertwiner in the latter example.
4. **Executable and formal replay.** Existing unit, Gate 1, integrated, and Lean
   checks were rerun. Additional independent bounded checks covered 394 finite
   set-operator families, 289 finite endomaps, 160 real/complex projector
   profiles, one equality case for Proposition 4.1, and the weakened-premise
   nonrealizability fixture.
5. **Citation and notation audit.** All fifteen citation identities and uses
   were checked against DOI/publisher metadata or the exact public manuscript.
   TKS/CAS axes and the simplex/projector/kernel symbols were compared with the
   registered terminology.

This remains an internal bounded review. It is not a substitute for the
qualified external review, proof-assistant completion, semantic migration,
experiments, disclosure review, or submission authority already left open.

## 4. Paper 1: typed dynamics and finite-fractal semantics

### 4.1 Typed category

The identity and associativity statements are correct. The Python reference
kernel enforces finite named carriers and exact object identity. The Lean
`Arrow` fragment proves the same equations over arbitrary carrier types, so it
validly covers the finite specialization but does not itself encode finiteness.

The remaining defect is the object universe. "Finite category" ordinarily
means finitely many arrows/objects, whereas "the category whose objects are
named finite sets" can be infinite. The draft should use one of these precise
forms:

- the category of finite sets and total functions; or
- the finite category/full subcategory generated from a frozen finite catalog
  of named finite carriers.

No Noetic semantic conclusion depends on this edit, but publication-level
mathematical typing does.

### 4.2 Deterministic lift

For (A_fe_x=e_{f(x)}), the input Gram matrix has entry one precisely when two
inputs share an output. Grouping by fibers produces a direct sum of (J_m)
blocks. Consequently,

\[
\lVert A_f\rVert^2=\max_y |f^{-1}(y)|,
\qquad \operatorname{tr}(A_f^*A_f)=|X|,
\qquad \operatorname{rank}(A_f)=|\operatorname{im} f|.
\]

The output operator (A_fA_f^*) is the multiplicity diagonal, and its
zero-one support projector is a separate operator. The two-state constant map
has matrix

\[
\begin{bmatrix}1&1\\0&0\end{bmatrix},
\]

is idempotent, has norm (sqrt2), and is neither a partial isometry nor an
orthogonal projector. These statements all passed direct and executable review.
The draft accurately limits the Lean evidence to entries, basis actions,
support composition, and literal/function-level counterexample fragments.

### 4.3 Fixed powers and denotational normal forms

The factorial-power result is correct. For an (n)-point map, (n!) lies past
every transient and is divisible by every possible cycle length. For one
element of a nonempty finite semigroup of size (m), eventual powers have
index and period at most (m), while (m!) is beyond the index and divisible
by the period. The record should either present this as a direct elementary
proof or add a real citation; it cannot say "cited" with no citation.

The shortlex algorithm also survives review. A candidate with shorter length
must be generated from a shorter prefix first. At equal length, lexicographic
order is inherited from the earlier prefix and declared generator iteration.
Suppressing later candidates for an already queued denotation is therefore
sound. Resource guards raise an exception and never expose a partial table as
complete. A universal formal proof remains open exactly as the draft says.

### 4.4 Finite and metric "fractal" layers

For (H(A)=\bigcup_g g(A)), monotonicity and (H(X)\subseteq X) make the
whole-carrier iterates descend. Every fixed subset remains inside every iterate,
so the stabilized set is the greatest fixed subset. This is not the metric
Hutchinson attractor theorem. Renaming the result to "finite union-image
set-operator stabilization" would make the distinction harder to miss.

When the classical metric theorem is invoked, the final paper should explicitly
state a nonempty compact metric carrier, a finite nonempty contraction family,
and the Hausdorff hyperspace of nonempty compact subsets. The present draft is
directionally correct and already prohibits importing metric, dimension, or
attractor conclusions into the finite symbolic layer.

## 5. Paper 3: projection geometry and capacity

### 5.1 Standard projector geometry

The normalized overlap

\[
k(i,j)=\operatorname{tr}(P_iP_j)/d
\]

is the Hilbert-Schmidt Gram kernel of (P_i/\sqrt d), hence positive
semidefinite and normalized. The principal-angle and chordal identities are
standard and correctly scoped. Centering by (Q_i=P_i-(d/D)I) gives

\[
\max_{i\ne j}k(i,j)\geq \frac{dN-D}{D(N-1)},
\]

and the rearranged cardinality condition is used only where
(mu<d/D). The Welch specialization uses valid real feature dimensions for
real symmetric and complex Hermitian matrices. None of these statements proves
that model activations instantiate the proposed subspaces.

The notation interface is clean: the registered mixed-simplex address and
Fisher-Rao metric remain distinct from the projector profile; normalized
(k(x,y)), unnormalized manuscript (K(x,y)), and code-coordinate
(t(x,y)) are not conflated.

### 5.2 Direct audit of Proposition 4.1

The exact source assumes unit code vectors (ell_x), rank-(d) projectors
(P_x) on a (D)-dimensional space, an isometry
(B:V\to W\otimes V), and

\[
B^*(\ell_x\otimes u)=\sqrt\Lambda,u
\quad (u\in\operatorname{im}P_x).
\]

Let (K(x,y)=\operatorname{tr}(P_xP_y)) and
(Theta_x=(\ell_x\otimes\mathrm{id})P_x-\sqrt\Lambda BP_x). The source
hypotheses give

\[
\langle\Theta_x,\Theta_y\rangle_{\mathrm{HS}}
=(t(x,y)-\Lambda)K(x,y).
\]

Therefore

\[
(t(x,y)-s)K(x,y)
=(\Lambda-s)K(x,y)+
\langle\Theta_x,\Theta_y\rangle_{\mathrm{HS}}.
\]

For distinct code points the left side is nonpositive, and on the diagonal it
is ((1-s)d). Summing over (C^2), retaining the nonnegative Gram norm, and
using trace Cauchy-Schwarz,

\[
\left\lVert\sum_{x\in C}P_x\right\rVert_{\mathrm{HS}}^2
\geq \frac{|C|^2d^2}{D},
\]

yields the source bound. This internal reproof found no missing dimension,
sign, adjoint, or inequality step.

That result does not close the CAS transfer. No reviewed CAS artifact constructs
the required (B), proves it is isometric, or verifies the adjoint identity on
every projector image. The source proposition and the proposed CAS
specialization should ideally become separate claim records so a valid source
proof cannot be mistaken for a completed transfer.

### 5.3 Weakened-transfer witness

With (D=d=1), two orthogonal code vectors, duplicate projectors (P_1=P_2=I),
(s=0), and a freely substituted (Lambda=1), the weakened formula gives
(2\leq1). More structurally, an isometry (B:\mathbb R\to W) would be a
unit vector (b), while the deleted condition would require both
(\langle b,\ell_1\rangle=1) and
(\langle b,\ell_2\rangle=1), impossible for orthogonal unit vectors.

The example is valid against the explicitly weakened statement. For maximum
logical clarity, the paper should either state that false weakened theorem in
full or call the example a parameter-underdetermination/nonrealizability
witness. It does not refute Proposition 4.1 with all hypotheses.

## 6. Citation audit

All fifteen citation IDs resolve and their narrow uses are defensible. DOI and
publisher metadata support the registered titles, authors, dates, venues, and
pages, subject to two harmless normalization suggestions: preserve the
diacritics in "Åke Björck" and either include Welch's publisher suffix
"(Corresp.)" or declare the shortened-title policy.

The final paper may also benefit from an authoritative Fisher-information-
geometry reference if it teaches the Fisher-Rao formula as background rather
than merely reporting the source-bound PCBA baseline.

The OpenAI manuscript identity is unusually strong: local and current remote
bytes match exactly. Its review status is not comparably established. The safe
claim is "public technical manuscript; peer-review status unverified; no
peer-review receipt in the reviewed source set."

## 7. Reproduction results

| Check | Result | Boundary retained |
|---|---|---|
| TKS v8 unit suite | 20 tests passed | Bounded executable evidence only |
| TKS v8 Gate 1 verifier | Passed; 12 hash-bound artifacts | Integration remains open |
| Lean Gate 1 verifier | Passed; Lean 4.32.1; 16 axiom audits | Matrix/Gram/trace/rank bridge open |
| Integrated Gate 1 verifier | Passed; 23 top-level artifacts; 6 subordinate receipts | Gate 1 remains open and not frozen |
| Independent small-model audit | Passed all enumerated and randomized checks | Not universal formalization or empirical evidence |

The review package's own manifest will bind every review artifact except itself.
No test result changes the authority or license boundary.

## 8. Handoff disposition

The lead can retain both Wave 1 formal drafts as useful source-bound research
deltas. Before any submission or shared-registry integration, resolve
`RFM-BLK-001` through `RFM-BLK-003`, regenerate affected hashes, and repeat
cross-review. The seven strengthening suggestions can be handled in the same
editorial pass.

All twenty upstream claims, all twenty-four upstream obligations, external
specialist review, formalization gaps, CAS semantic migration, experiments,
authorship/disclosure review, and submission authority remain open. This review
does not promote canon, license, product status, public disclosure, or empirical
validity.
