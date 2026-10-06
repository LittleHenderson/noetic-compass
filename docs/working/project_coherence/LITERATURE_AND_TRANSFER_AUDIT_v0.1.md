# Project Coherence literature and transfer audit v0.1

Status: `PRIMARY-SOURCE AUDIT COMPLETE / INDEPENDENT PROOF REVIEW OPEN`

Date: 2026-08-04

## 1. Source status

The supplied source is OpenAI, *Ten Advances in Mathematics and Theoretical Computer Science*, 249 pages, dated 2026-08-01, SHA-256 `64B900D5FAE6FE22F2AE1B8E3B712D20055194A6C81CF343A2455E5898AC7DD6`, publicly hosted at <https://cdn.openai.com/pdf/ten-proofs-oai.pdf>.

The reviewed artifact has no DOI, arXiv identifier, journal or conference venue, or named chapter authors. Its metadata describes it as a collection of research papers by an internal model at OpenAI. It should be cited as an OpenAI public technical manuscript, not as a peer-reviewed publication. The ten new headline results remain `MANUSCRIPT_CLAIM` until independent verification.

The supplied Noetic Topos PDF is an eight-page axiomatic manuscript by Little Henderson. Its own scope statement defers empirical validation. It is not evidence that the formal construction measures cognition, alignment, or safety.

## 2. Claim-evidence-transfer matrix

| Item | Literature status | Defensible transfer | Prohibited shortcut |
|---|---|---|---|
| Projector kernel | Standard Hilbert-Schmidt Gram construction. | Use `tr(P_iP_j)/d` as a typed similarity kernel for common-rank orthogonal projectors. | Do not call it novel mathematics or validated latent geometry. |
| Projector capacity | New manuscript claim with strict Proposition 4.1 hypotheses. | Only after constructing the required isometry/intertwiner and code certificate in CAS. | Rank and coherence alone do not imply the bound. |
| Connes non-rigidity | New manuscript claim; concurrent arXiv work supports only part of the qualitative phenomenon and is also unrefereed. | Motivation for a defined CAS forgetful-functor/reconstruction problem. | Nonfaithfulness of group factors does not transfer automatically to boards, C*-algebras, or topoi. |
| Permanent lower bounds | New manuscript claim in exact arithmetic models. | Exact permanent-valued CAS component plus bounded-cost compilation into the same model. | No generic memory, latency, board-size, approximation, branching, or finite-precision lower bound follows. |
| Quantum repetition | New manuscript claim for a strict finite entangled-game model. | A formally defined two-player one-round game with independent coordinates, isolation, finite alphabets, all-win acceptance, and certified one-copy gap. | Adaptive prompt tests, communication, shared mutable state, correlated prompts, or threshold wins do not qualify. |
| CVP hardness | New manuscript claim for variable-dimensional integer lattices. | Explicit polynomial-time reduction into an exact CAS retrieval/repair decision problem. | Fixed 39/40-dimensional geometry or a similarity metaphor does not inherit NP-hardness. |
| Ehrhart volume | New manuscript claim; concurrent equality-case follow-up is unrefereed. | Compact affine body, specified covolume-normalized lattice, barycenter and interior-point proofs, and ordinary Euclidean volume. | The open Noetic simplex, Fisher-Rao volume, and code cardinality do not satisfy or follow from the theorem automatically. |
| Non-sofic group | New manuscript claim. | Only for a future explicitly infinite group-based TKS model after proving relevance. | No implication for the current finite calculus. |
| Ramsey and extremal graphs | New manuscript claims. | Only through an exact graph/coloring encoding and transfer theorem. | Analogy does not establish capacity, safety, or architecture bounds. |
| Finite semigroups | Established standard background at the correct type. | Total endomaps on one finite carrier; typed inter-object maps use a finite category/semigroupoid. | No unique attractor or literal reset-gate conclusion. |
| Markov categories | Established compositional stochastic framework. | Typed stochastic-kernel layer such as FinStoch. | No automatic contraction, stationarity, calibration, causal identification, or sheaf gluing. |
| Linear cellular sheaves | Established under finite-dimensional linear and inner-product hypotheses. | Consistency residuals, Laplacians, and heat flow after choosing a linear representation. | A Markov-valued functor or Grothendieck sheaf is not automatically such a cellular sheaf. |

## 3. Exact conditional statements that matter

### 3.1 Projector-capacity condition

The manuscript's projection bound requires a `D`-dimensional `V`, rank-`d` projectors `P_x`, unit vectors `ell_x`, a code relation `t(x,y)=<ell_x,ell_y><=s`, and an isometry `B:V->W tensor V` satisfying

```text
B*(ell_x tensor u)=sqrt(Lambda)u
```

for every `u` in `im(P_x)`, with `Lambda>s`. Only under those hypotheses does the displayed cardinality bound follow. The earlier CAS transfer omitted this condition.

Relevant established background includes Conway-Hardin-Sloane (<https://doi.org/10.1080/10586458.1996.10504585>), Bachoc-Vallentin (<https://doi.org/10.1090/S0894-0347-07-00589-9>), and Barg-Nogin (<https://doi.org/10.1134/S0032946006020025>).

### 3.2 Quantum repetition condition

The chapter considers finite two-player, one-round, tensor-product entangled games with finite question and answer alphabets, a binary predicate, no communication after questions, independent coordinate sampling, arbitrary joint local measurements, and all-coordinate acceptance. The one-copy entangled value must have a positive gap.

The published general baseline cited in this audit provides polynomial decay (Yuen, <https://doi.org/10.4230/LIPIcs.ICALP.2016.77>), while published exponential results use special structures such as anchored games (<https://doi.org/10.1145/3055399.3055433>) and projection games (<https://doi.org/10.1007/s00037-015-0098-3>). The OpenAI general exponential theorem remains a manuscript claim.

### 3.3 Ehrhart-to-Noetic condition

The manuscript uses a full-dimensional compact convex body in `R^n`, an ordinary Euclidean volume, a specified lattice, a barycenter condition, and a unique interior lattice point. The present Noetic state space is an open 39-simplex. Passing to a closure, recentering it, choosing an affine lattice, normalizing covolume, and proving all hypotheses are separate obligations. Even then, volume is not state-code cardinality without a lattice-point counting theorem.

Related primary literature includes Nill-Paffenholz (<https://doi.org/10.1515/advgeom-2014-0001>) and Berman-Berndtsson (<https://doi.org/10.1515/crelle-2014-0069>). A concurrent equality-case preprint, <https://arxiv.org/abs/2608.01040>, explicitly describes itself as a counterpart to the OpenAI inequality and is also unrefereed.

## 4. Citation and wording rules

Use the following evidence labels:

- `ESTABLISHED` - supported by checked peer-reviewed or authoritative primary background.
- `MANUSCRIPT_CLAIM` - a new result stated in the OpenAI 2026 technical manuscript.
- `CONDITIONAL_TRANSFER` - a result whose hypotheses and an explicit CAS/TKS encoding or reduction are fully stated but not yet discharged.
- `PROPOSED / OPEN` - analogy, architecture, experiment, or proof obligation without a completed transfer.

Do not write “the paper proves” in a public CAS claim without immediately identifying it as the OpenAI manuscript's claimed proof and preserving the review state. Do not convert a concurrent arXiv preprint into independent peer review. Do not omit arithmetic model, dimensional, compactness, independence, isolation, or intertwining hypotheses.

No checked reference in the relevant manuscript chapters was found to be fabricated. The dominant risks are status inflation, omitted hypotheses/model restrictions, and analogy-only transfer.

## 5. Admission decision

All ten new manuscript results and all bespoke CAS/TKS transfers remain Ring 4, `OPEN`, and `NOT LICENSED`. Standard background results may receive separate theorem records and advance only through their own proof, citation, typing, and review gates.
