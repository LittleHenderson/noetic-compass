# An Axiomatic Finite Site and Information-Geometric Layer for the TKS v7.4 Core

## Abstract

This note isolates the mathematically defensible core of the TKS v7.4 referee
draft. The construction is explicitly axiomatic. It specifies:

1. a finite concrete category `Noetica` built from distinguished objects and
   admissibility data,
2. a Grothendieck topology `J_noe` on that category,
3. the associated sheaf category `Sh(Noetica, J_noe)`, and
4. an information-geometric state-space layer based on the open probability
   simplex and the Fisher-Rao metric.

The purpose of this document is formal clarification, not empirical
validation. No claim is made here that the axioms are uniquely determined by
data, that the resulting structures model cognition in a validated scientific
sense, or that the framework has predictive power. The mathematically relevant
claim is narrower: if the stated axioms hold, then the stated categorical and
geometric consequences follow.

## 1. Scope

The original v7.4 materials mix formal mathematics, research-program notes,
and broader interpretive claims. For peer-review purposes, those roles should
not be conflated.

This manuscript therefore restricts attention to two layers only:

- a finite categorical/site/topos layer, and
- an information-geometric state-space layer.

Everything beyond that scope should be treated as separate work.

## 2. Primitive Data

Fix a finite index set $\mathcal{I}$ of cardinality $40$, partitioned into four
distinguished subsets

$$
\mathcal{I} = \mathcal{I}_A \sqcup \mathcal{I}_B \sqcup \mathcal{I}_C \sqcup \mathcal{I}_D.
$$

The labels `A, B, C, D` are formal domain labels. They are not interpreted
empirically in this manuscript.

Assume also a preorder on the domain labels

$$
A \succeq B \succeq C \succeq D.
$$

For each operator index $k \in \{0,1,\dots,9\}$, fix an admissibility relation

$$
D_k \subseteq \mathcal{I} \times \mathcal{I}.
$$

For each $i,j \in \mathcal{I}$ with $(i,j) \in D_k$, fix distinguished finite
sets $X_i,X_j$ and a generating morphism

$$
\nu_{k,i,j} : X_i \to X_j.
$$

The case $k=0$ is reserved for identity data, so we require

$$
D_0 = \{(i,i): i \in \mathcal{I}\}, \qquad \nu_{0,i,i} = \mathrm{id}_{X_i}.
$$

## 3. The Category `Noetica`

### 3.1 Assumption A1: finite concrete realization

Assume that each index $i \in \mathcal{I}$ is realized by a finite set $X_i$,
and that all generating morphisms are actual functions between those sets.

### 3.2 Assumption A2: pullback-complete finite category

Define `Noetica` to be the smallest subcategory of `FinSet` satisfying:

- the distinguished objects are included,
- the generating morphisms $\nu_{k,i,j}$ are included,
- identities and composites are included, and
- pullbacks of morphisms in the category are again objects of the category,
  together with their projection morphisms and the universal morphisms induced
  by the pullback property.

In particular, morphisms are concrete functions, and equality of morphisms is
extensional.

### 3.3 Assumption A3: smallness

Assume that the pullback-closure process yields only finitely many objects up to
the identifications intended by the construction. Under that assumption,
`Noetica` is a small category with finite hom-sets.

This assumption should be read literally as a hypothesis on the chosen data. It
is not proved here from more primitive ingredients.

### 3.4 Proposition

Under Assumptions A1-A3, `Noetica` is a small concrete category with pullbacks.

### Proof

Because all objects are finite sets and all morphisms are actual functions,
faithfulness of the inclusion functor

$$
U : \mathrm{Noetica} \hookrightarrow \mathrm{FinSet}
$$

is immediate. Pullbacks exist by construction. Finiteness of hom-sets follows
because for finite sets $X,Y$ there are only finitely many functions
$X \to Y$.

## 4. ACBE Descent and RPM Structure

### 4.1 Assumption A4: descent maps

For each pair of domain labels $W',W$ with $W' \succeq W$, assume the existence
of designated descent morphisms

$$
\iota^{W'W}_{i',i} : X_{i'} \to X_i
$$

for appropriate $i' \in \mathcal{I}_{W'}$ and $i \in \mathcal{I}_W$.

Assume reflexivity and transitivity in the obvious sense, and assume pullback
stability strong enough to ensure that the pullbacks of these descent maps
jointly cover the source object in the concrete sense used below.

### 4.2 Assumption A5: section-retraction endofunctor

Assume an endofunctor

$$
R : \mathrm{Noetica} \to \mathrm{Noetica}
$$

with natural transformations

$$
\eta : \mathrm{id} \Rightarrow R,
\qquad
\varepsilon : R \Rightarrow \mathrm{id}
$$

satisfying

$$
\varepsilon_X \circ \eta_X = \mathrm{id}_X
\qquad
\text{for all } X \in \mathrm{Ob}(\mathrm{Noetica}).
$$

This is a section-retraction pair, not an adjunction.

### 4.3 Proposition

For any morphism $g : J \to I$, the pullback of $\varepsilon_I : R(I) \to I$
along $g$ has projection to $J$ that is surjective on underlying sets.

### Proof

Let

$$
P := J \times_I R(I).
$$

Define

$$
\phi := \langle \mathrm{id}_J,\, R(g)\circ \eta_J \rangle : J \to P.
$$

Naturality of $\varepsilon$ and the identity
$\varepsilon_J \circ \eta_J = \mathrm{id}_J$ give

$$
\varepsilon_I \circ R(g) \circ \eta_J
= g \circ \varepsilon_J \circ \eta_J
= g.
$$

Hence $\phi$ is a well-defined section of the projection $P \to J$, so that
projection is surjective.

## 5. The Noetic Coverage

Define a sieve $S$ on an object $X$ to be covering if at least one of the
following conditions holds:

1. `Joint surjectivity`: $S$ contains a family of morphisms into $X$ whose
   underlying functions are jointly surjective on the finite set $U(X)$.
2. `World descent`: $S$ contains the designated descent maps into $X$.
3. `RPM realization`: $S$ contains the counit morphism
   $\varepsilon_X : R(X) \to X$.

Denote the resulting coverage by $J_{\mathrm{noe}}$.

### Lemma

Under Assumptions A4-A5, conditions (2) and (3) reduce to condition (1).

### Proof

For condition (2), apply the assumed pullback-stability of descent maps to the
identity morphism on $X$; the resulting family is jointly surjective by
assumption.

For condition (3), $\varepsilon_X$ has section $\eta_X$, so its underlying
function is surjective.

### Theorem

Under Assumptions A1-A5, $J_{\mathrm{noe}}$ is a Grothendieck topology on
`Noetica`.

### Proof

After the reduction lemma, it is enough to prove the Grothendieck axioms for
jointly surjective covering families.

- Maximality holds because the identity is surjective.
- Stability under pullback holds because pullbacks exist in `Noetica`, and
  pullback of a jointly surjective family is again jointly surjective in
  `FinSet`.
- Transitivity holds because composition of jointly surjective families is
  jointly surjective.

Thus $(\mathrm{Noetica}, J_{\mathrm{noe}})$ is a site.

## 6. Sheaf Topos

Let

$$
\mathrm{NoeTop} := \mathrm{Sh}(\mathrm{Noetica}, J_{\mathrm{noe}}).
$$

### Assumption A6: subcanonicity

Assume that $J_{\mathrm{noe}}$ is subcanonical, that is, every representable
presheaf is a sheaf.

This assumption is not needed for the existence of the sheaf topos itself, but
it is needed if one wants to identify the original objects of `Noetica` with
their Yoneda images inside the sheaf category.

### Theorem

Under Assumptions A1-A5, `NoeTop` is a Grothendieck topos, hence in particular
an elementary topos.

### Proof

The previous section gives a small site
$(\mathrm{Noetica}, J_{\mathrm{noe}})$. Standard topos theory implies that the
sheaf category on any small site is a Grothendieck topos.

## 7. State Space and Noetic Manifolds

### 7.1 Open and closed state spaces

Define the open simplex

$$
S^\circ
:=
\left\{
p \in \mathbb{R}^{40} :
p_k > 0 \text{ for all } k,\;
\sum_{k=1}^{40} p_k = 1
\right\}.
$$

This is the interior of the standard $39$-simplex and therefore a smooth
$39$-dimensional manifold.

Define also the closed simplex

$$
S
:=
\left\{
p \in \mathbb{R}^{40} :
p_k \ge 0 \text{ for all } k,\;
\sum_{k=1}^{40} p_k = 1
\right\},
$$

which is a compact manifold with corners.

### 7.2 Noetic manifolds

A noetic manifold is a pair $(M,\sigma)$ consisting of a smooth manifold $M$
and a smooth map

$$
\sigma : M \to S^\circ.
$$

The insistence on the open simplex is deliberate: it guarantees that the
Fisher-Rao metric is finite everywhere on the image.

### 7.3 A model-specific dimension count

For this framework one may define the model-specific quantity

$$
\dim_\sigma(p) := \dim(T_pM) + \mathrm{rank}(d\sigma_p).
$$

This should not be presented as an intrinsic dimension theorem of differential
geometry. It is a framework-specific descriptor attached to the pair
$(M,\sigma)$.

## 8. Fisher-Rao Geometry

For $p \in S^\circ$ and tangent vectors $u,v \in T_pS^\circ$ satisfying
$\sum_k u_k = \sum_k v_k = 0$, define

$$
g_p^{FR}(u,v) := \sum_{k=1}^{40}\frac{u_k v_k}{p_k}.
$$

This is the standard Fisher-Rao metric on the open probability simplex.

For a noetic manifold $(M,\sigma)$, pull back the Fisher-Rao metric along
$\sigma$:

$$
g_p^\sigma(u,v) := g_{\sigma(p)}^{FR}(d\sigma_p(u),d\sigma_p(v)).
$$

If $d\sigma_p$ is injective, this is a genuine Riemannian metric at $p$.
Without injectivity, it is a positive semidefinite quadratic form.

## 9. What Is and Is Not Proved

The manuscript proves only the following kind of statement:

- given Assumptions A1-A5, the coverage $J_{\mathrm{noe}}$ defines a small site,
- given that site, the associated sheaf category is a Grothendieck topos, and
- the state-space layer carries the standard Fisher-Rao information geometry.

The manuscript does **not** prove:

- that the axioms are uniquely motivated,
- that they are empirically validated,
- that they model cognition or consciousness in a scientific sense, or
- that bespoke descriptors such as $\dim_\sigma$ have external predictive
  meaning.

Those are distinct questions and would require separate argument or data.

## 10. Limitations and Submission Guidance

This manuscript should be submitted, if at all, as an axiomatic mathematical
framework note. It should not be marketed inside the paper as an assessment
theory, a validated cognitive science model, or a consciousness theory.

Any broader submission strategy should separate:

- the formal mathematics,
- empirical scoring studies, and
- philosophical interpretation.

Treating those as one undifferentiated claim set would weaken all three.

## References

- Saunders Mac Lane, *Categories for the Working Mathematician*, 2nd ed.,
  Springer.
- Saunders Mac Lane and Ieke Moerdijk, *Sheaves in Geometry and Logic: A First
  Introduction to Topos Theory*, Springer.
- Shun-ichi Amari and Hiroshi Nagaoka, *Methods of Information Geometry*,
  American Mathematical Society and Oxford University Press.
