# CAS-RPA mathematical review

Review date: 2026-09-16. Status: **mathematical design review; no implementation or performance acceptance**.

The atlas's main mathematical claims are sound within its stated scope. It can support a bounded, typed view of an episode. Coordinates, visual overlap, compatibility labels and routing weights supply no proof, observation, scheduling permission or kernel authority.

Reviewed the complete extracted text of **CAS_Recursive_Possibility_Atlas_v0_1.pdf**, 26 pages, and **CAS_RPA_Map_Overview.pdf**, one page. Page numbers below are PDF pages; the atlas's printed numbers agree. Source identities are recorded in `records/rpa_001/source_identity.json`:

| Supplied PDF | SHA-256 |
| --- | --- |
| Full atlas | `e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab` |
| Overview | `999cd83381b316b1284a65ebaa48736c4a73ad41b08cb12c2099a43e0787c2fb` |

This review checks the mathematical statements printed in these two documents. It does not independently re-audit their separate CAS references C1-C6, including `noetic-topos.pdf`, or establish that the proposed atlas has been implemented.

## 1. Forty components and centered coordinates

**Atlas pp.6-7, 20-21; overview p.1: correct.** The set

\[
\Delta^{39}_{>0}=\{p\in\mathbb R^{40}:p_i>0,\ \sum_{i=1}^{40}p_i=1\}
\]

has 39 independent dimensions. It is open relative to its affine hyperplane, not open in all of R40. The 40 labels do not describe 40 future events. On p.21, 0.61 plus 39 copies of 0.01 sums to one; row-major index 25 (zero-based) is ^6/C. That fixture is dimensionally valid and explicitly synthetic.

With a fixed component order, denominator 40 and positive reference p*, the p.6 chart is

\[
z_i=\log(p_i/p_{40})-\log(p_i^*/p_{40}^*),\quad i=1,\ldots,39.
\]

It maps p* to zero and is bijective onto R39. The standard ALR definition uses a chosen denominator and D-1 coordinates. [scikit-bio ALR documentation](https://scikit.bio/docs/dev/generated/skbio.stats.composition.alr.html)

**Derived inverse, needed in an implementation:** define

\[
w_i=p_i^*\exp(z_i)\ (i<40),\quad w_{40}=p_{40}^*,\quad
p_i=w_i/\sum_jw_j.
\]

This follows by restoring the reference log ratios before applying ordinary inverse ALR. Using `softmax(z, 0)` alone loses p*: at zero it returns a uniform profile. Ordinary inverse ALR exponentiates the uncentered coordinates and normalizes. [scikit-bio inverse ALR documentation](https://scikit.bio/docs/dev/generated/skbio.stats.composition.alr_inv.html)

For another positive reference q*, `z(p;q*) = z(p;p*) - z(q*;p*)`. This changes the chart, not p, state identity, time or evidence. Use log differences and a log-sum-exp inverse for numerical stability; still reject unrepresentable results rather than silently introducing zeros. Exact zeros require a separately named boundary model. Rounding tolerance, coordinate order, denominator and reference identity must be explicit.

## 2. Fisher-Rao geometry is separate

**Atlas pp.6 and 20: correct, with a citation distinction.** Its metric

\[
g_p(u,v)=\sum_i u_iv_i/p_i
\]

acts on tangent vectors with `sum(u)=sum(v)=0`. With this scale convention the categorical Fisher-Rao distance is

\[
d_{FR}(p,q)=2\arccos\!\left(\sum_i\sqrt{p_iq_i}\right).
\]

The factor two matters. [Nielsen and Sun, *Clustering in Hilbert simplex geometry*, v7, §2.1, p.4, Eq.(1)](https://arxiv.org/pdf/1704.00454v7#page=4)

The scikit-bio non-isometry statement concerns **Aitchison geometry**; it is not itself a Fisher-Rao proof. Independently, substituting the ALR inverse into the atlas metric gives `G = diag(a) - a a^T`, where `a = (p_1,...,p_39)`. This matrix varies with p. Thus ordinary Euclidean distance between ALR coordinates is not this metric. Screen distance and transition cost remain separate.

Because the atlas explicitly permits a non-injective descriptor `sigma:X→Delta`, distinct complete states can have the same profile and zero profile distance. That distance cannot establish state equality, semantic equivalence, reachability or truth. A measured interpretation for sigma remains unspecified.

## 3. A nerve needs common intersections

**Atlas pp.10 and 20; overview p.1: correct.** For a fixed, versioned family of regions in one state space, k+1 regions form a k-simplex when their common intersection is nonempty. Pairwise edges alone do not certify a filled triangle. For example, `{a,b}`, `{b,c}` and `{a,c}` intersect pairwise but have empty triple intersection. A clique construction would fill this triangle incorrectly for the intended nerve. [Erickson, *Examples of Cell Complexes*, §§15.1.1-15.1.2, pp.1-2](https://jeffe.cs.illinois.edu/teaching/comptop/2009/notes/cell-complex-examples.pdf#page=1)

A checked common witness certifies inclusion and also witnesses every face. Failure to find a witness only establishes **unknown**, unless the relevant universe was fully enumerated or an adequate emptiness checker proved the intersection empty. Finite witness sampling generally gives a partial complex, not the full semantic nerve. Cross-scope parts require the declared projections in p.20.

Recovering the union's topology requires additional hypotheses; the cited nerve lemma uses a finite open cover with every nonempty finite intersection contractible. No such conditions are established for arbitrary idea regions. [Erickson, §15.1.1, p.1](https://jeffe.cs.illinois.edu/teaching/comptop/2009/notes/cell-complex-examples.pdf#page=1)

Reference caution: the [GUDHI 3.12 cover documentation](https://gudhi.inria.fr/doc/3.12.0/group__cover__complex.html) uses an off-by-one shorthand in its prose about k-fold intersections. Preserve the atlas's correct **k+1 regions / dimension k** convention, supported by M1.

## 4. Compatibility does not establish a sheaf

**Atlas p.11: correctly limited.** Shared-field comparison requires matching objects, variable meanings, scopes, times and versions. For a presheaf, restriction maps must also preserve identity and compose consistently. A sheaf additionally requires a unique global section for every compatible local family over every allowed cover. The empty cover has a condition as well. [Stacks Project, §6.7, Definition 6.7.1 and Remark 6.7.2](https://stacks.math.columbia.edu/tag/006S)

A few matching records do not prove these universal obligations, nor that a merged record satisfies other global constraints. Conversely, in an already established sheaf, pairwise restriction agreement of a fixed family is exactly the compatibility condition; do not confuse this with pairwise existential witnesses for unrelated region intersections. A finite record checker should be called an overlap/compatibility checker until its space or site, restriction maps, covers and gluing contract are established. No topos equivalence or complete global model follows from the drawing.

## 5. Expansion and allocation arithmetic

**Atlas p.19: correct arithmetic; one budget convention needs resolution.** A complete six-child tree to depth three, with root at depth zero, has `1+6+36+216 = 259` nodes. It needs 258 new nodes if the root already exists. The table says 100 **new** nodes, while pp.21-22 use `max_nodes:100` / a 100-node display counter. Define either a total-node cap including the root or a new-node cap excluding it. Those permit 100 or 101 total nodes respectively; neither completes this tree. Reused IDs can reduce unique nodes, but neither depth nor deduplication proves completeness. An expansion cap also does not, by itself, bound the cost of arbitrary generators or membership predicates.

**Atlas p.16: the synthetic 15/15/0 allocation is correct.** Scores 12/4 and 6/2 both equal three; a 30-unit budget splits equally. Valid normalization requires finite nonnegative scores and a strictly positive denominator. All-zero scores need the declared no-ready result. An implementation needs deterministic integer rounding with an explicit accounting rule. A hard-disabled branch should be excluded before arithmetic, so a large or invalid Drive cannot turn `0*infinity` into NaN or defeat the mask.

The ratio alone does not identify separate Drive and resistance values. These must have independently specified producers and units or declared scales. Nothing here validates native CAS-Ohm telemetry, allocator superiority, a calibrated future probability, or new scheduling authority. Page 16 already separates these claims.

## Adoption boundary

The overview accurately summarizes the full atlas's cautions. Pages 19 and 23-26 expressly avoid claims of complete enumeration, formal fractal dimension, quantum behavior or measured superiority. Preserve those limits.

A bounded adoption can represent typed nodes, exact recorded transition references, checked finite overlap witnesses, explicit conflicts and deferred expansion. If profiles or geometry are included, label their basis and numerical policy. The existing coordinator and checker remain authoritative; a view, chart change, profile value or shared witness never promotes a hypothetical action to an executed or verified outcome. Performance benefit, measured CAS semantics, a complete nerve, a sheaf implementation and native neural-flow closure remain unproved by these PDFs.
