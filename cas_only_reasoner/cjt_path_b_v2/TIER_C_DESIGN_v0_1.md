# TIER C DESIGN v0.1 — Fixed Nonpermutable CAS Relational Structure

**Status: DESIGN ONLY. No model, no GPU, no run. Non-claim-bearing. Awaiting owner ruling.**

Per the owner ruling "PATH-B-A1 CLOSURE AND TIER-C TRANSITION" (2026-09-01).
Predecessor: commit `3bbcd2c1`, official status `NO_PATH_B_OPERATION_SIGNAL` (preserved, not rewritten).

---

## 1. What Tier C tests, in plain English

PATH B gave the model flat operation labels — four interchangeable name-tags. The math
(the S-PERM equivariance identity) says name-tags can be relabeled by the learner without
loss: the tags carry no fixed structure, only identity. Tier C replaces the tags with a
**frozen relational structure**: a directed composition table saying which operation can
follow which, what composing them yields, and which compositions are forbidden — with the
CAS involution sign (`^2` attract = +, `^3` avert = −) and the in-vocabulary asymmetry
(the duals of `^6` and `^8`, namely `^5` and `^9`, are absent from the operation set, so
their columns are structurally missing).

The question: does a model that receives the operation structure — not just the operation
identity — solve compositional questions better than (a) a model with no structure and
(b) a model with a **matched generic structure** of the same statistical shape but no CAS
content? Only a win over BOTH earns any structural finding, and even then it is
development-signal language only. No CAS-specific claim is licensed by Tier C alone.

## 2. The frozen structure R (candidate — freezes at C0 with the proof artifact)

Operation classes (unchanged from PATH B): A=`^2` attract, B=`^3` avert, C=`^6` decompose,
D=`^8` trigger.

`R` is a 4×4×F frozen tensor (F small, integer-coded feature planes), derived ONLY from:
1. **Solver semantics already in the corpus** — what `solve()` licenses: `^8∘^8` chains
   (trigger propagates), `^3` blocks propagation onto its object, `^2` passes/marks,
   `^6` opens part-scope for its object.
2. **CAS structural invariants** (CLAUDE.md / Clarification 1 layer): involution sign
   s(^2)=+1, s(^3)=−1; missing-dual asymmetry for `^6`/`^8` (forbidden columns).

Derivation is a deterministic script (`build_tier_c_structure.py`) — no hand-editing after
freeze. Candidate feature planes: `follows_allowed[i,j]` (directed, asymmetric),
`composition_class[i,j]` (what an i-then-j composition licenses: chain / block / mark /
scope / forbidden), `sign[i]`, `dual_present[i]`.

**Non-negotiable acceptance test — PROOF_OF_NON_EQUIVARIANCE (runs before any spend):**

- **(P-a) Trivial automorphism group.** Enumerate all 4! = 24 class permutations P;
  require that ONLY the identity satisfies R[P(i),P(j),:] = R[i,j,:] for all i,j.
  Executable check, exact, no tolerance.
- **(P-b) Pathway pinning.** For EVERY learned parameter on the complete profile pathway
  of every tournament transform (T1–T4 below), show by symbolic argument + numeric check
  that no parameter transformation family (the A1 failure mode: W_r → PᵀW_r absorbing a
  label permutation) can map the permuted-label model onto the true-label model, BECAUSE
  the frozen R enters between learned maps and is not permutation-symmetric (by P-a).
  Concretely: run the A1-style paired-permutation conformance test per transform and
  require it to **FAIL to conform** (divergence >> tolerance) — the mirror image of the
  A1 S-PERM test, which conformed at 7.15e-07. A transform whose permuted twin still
  conforms is REJECTED from the tournament before spend.
- **(P-c) Mutant discipline (CHK-M extension).**
  - M13_SYMMETRIC_R: replace R with a permutation-symmetric table → P-a must FAIL
    (proves the proof can fail).
  - M14_STRUCTURE_ZEROED: zero R inside a transform → that arm must lose its structural
    behavior (proves R is load-bearing in the implementation, not decorative).

If any of P-a/P-b fails for the frozen candidate R: emit `TIER_C_CONSTRUCTION_FAILED`,
stop, report to owner. No repair-in-place.

## 3. Matched generic relational control (mandatory sibling arm)

`R_gen`: a frozen directed table drawn deterministically (HashPRNG, registered seed
string) subject to MATCHING constraints: same number of allowed/forbidden entries, same
in/out-degree multiset, same count of signed classes, same missing-column count, and
trivial automorphism group (verified by the same P-a script). No CAS content.

Decision meaning:
- CAS-R beats no-structure but NOT R_gen → `GENERIC_RELATIONAL_STRUCTURE_SUFFICIENT` +
  `CAS_SPECIFICITY_NOT_ESTABLISHED`. That is a real, honest finding — recorded, not spun.
- CAS-R beats both by the registered margins → `TIER_C_CAS_STRUCTURAL_SIGNAL_DEV`
  (development signal only; non-claim-bearing).

## 4. Task addition (same construction-gold law as PATH B)

The structure must MATTER for answers, or the model can ignore R. One new question family:

- **QC_VALID (path-validity / reachability under composition rules):** "starting from X,
  which idea does the chain reach?" where the gold answer depends on `follows_allowed` /
  `composition_class` (a `^3` block truncates, a `^6` scope diverts into parts, `^8∘^8`
  chains). Formal trace first → deterministic templates → independent round-trip parser
  recovers graph + order + answer exactly; exclusion never relabeling.

QB_REL / QB_COMP / QB_INT retained unchanged for cross-tier comparability. QB_ORD stays
OUT (its re-entry is a standing owner decision; clean PRB-POS at the frozen layer L6 was
0.789, and at L18 0.848 — both below the 0.90 re-entry bar as measured).

Full CHK-1..11 battery + CHK-M (now 14 mutants) rerun on the extended dataset on CPU
($0) before any GPU spend. Any battery failure → stop, report.

## 5. Bounded CAS Transform Tournament (inside Tier C, per ruling)

Same model skeleton (A1 recurrent clause-entity graph executor, frozen L6 activations,
cached once), same data, same seeds {11, 23, 47}, same optimizer/schedule, matched
parameter counts (±1% law), same compute per arm. Arms differ ONLY in how structure
enters:

- **T0 — no CAS structure.** Uniform profile (A1's S6 configuration). Baseline.
- **T1 — additive structural routing.** Hop scores get an additive term from R-derived
  edge features between the current pointer's clause-class and the candidate clause-class.
- **T2 — operation-conditioned matrix transform.** Per-class message matrices selected by
  the frozen class label; R gates which (i→j) messages are allowed to flow.
- **T3 — bilinear question-operation-entity transform.** score = qᵀ B_{class} e with R
  constraining cross-hop composition (forbidden compositions masked to −inf).
- **T4 — recurrent composition tensor.** Hop state updated by contraction with the frozen
  R core through a learned lens (learned input/output maps, frozen middle).

Every Tx runs twice: once with CAS-R, once with R_gen (T0 needs no pair). Total GPU
arms: 1 + 4×2 = 9 configurations × 3 seeds = 27 runs.

## 6. Separated axes (per ruling — never mixed again)

Run AFTER the tournament, on the single winning transform only:

- **Attenuation axis (information amount, never wrong):**
  p_λ = λ·p_exact + (1−λ)·p_uniform, λ ∈ {0, 0.25, 0.5, 0.75, 1.0}. Registered
  expectation: accuracy monotone nondecreasing in λ (violation is itself a finding).
- **Misinformation axis (information wrongness):** corruption fraction ρ ∈ {0, 0.25, 0.5}
  using the frozen alt50-style map generalized to ρ. Analyzed separately; NO monotone
  clause spans the two axes. The A1 lesson stands: wrong labels are not partial labels.

Dose runs: (5 + 2 new ρ points) × 3 seeds = 21 runs on the winner.

## 7. Formal-path faithfulness measurements (registered outcomes, not gates)

A1 left `FORMAL_PATH_FAITHFULNESS: UNESTABLISHED` (S3 bridge-top1 0.330 < S6 0.550 while
S3 won accuracy). Tier C measures, per arm:

1. **Bridge agreement:** hop-1 pointer top-1 vs the symbolic solver's designated bridge.
2. **Forced-path delta:** teacher-force the formal bridge at eval; report accuracy change.
3. **Blocked-path delta:** mask the formal bridge at eval; report accuracy change.
4. **Per-example coupling:** agreement between bridge-correctness and answer-correctness
   (contingency table, not a single number).

Registered readout statuses: `FORMAL_PATH_FAITHFUL_DEV` (agreement high AND forced-path
delta ≈ 0 AND blocked-path damage large) vs `USEFUL_BUT_UNFAITHFUL_ROUTE` (accuracy wins
via a route that disagrees with the formal derivation) vs `UNESTABLISHED`. These describe;
they do not gate the tournament.

## 8. Deterministic status law (frozen at C0; program-emitted, not prose)

Margins reuse the A1 scale: primary margin ≥ 0.02 vs T0, ≥ 0.02 vs R_gen sibling,
each > the B-KEY shortcut increment measured on the extended dataset, on ≥ 2/3 of the
non-ceiling families, surviving best-family removal **with the residual margin itself
required ≥ 0.01** (tightened from A1's strict-positivity clause; A1's version is
preserved unchanged in its own record).

- `TIER_C_CONSTRUCTION_FAILED` — proof or battery fails before spend.
- `NO_TIER_C_STRUCTURAL_SIGNAL` — no Tx/CAS-R beats T0 by law.
- `GENERIC_RELATIONAL_STRUCTURE_SUFFICIENT` (+ `CAS_SPECIFICITY_NOT_ESTABLISHED`) —
  beats T0, not R_gen.
- `TIER_C_CAS_STRUCTURAL_SIGNAL_DEV` — beats both by law. Development language only.

Prohibited regardless of outcome: "CAS-specific" as a claim, `EMPIRICALLY_SUPPORTED`,
`GATE1B_PASS`, `CJT_TRANSFORMER_VALIDATED`, any claim promotion, any protected read.

## 9. Phasing, budget, stop laws

| Phase | Content | Compute | Est. cost | Stop law |
|---|---|---|---|---|
| C0 | structure derivation + PROOF_OF_NON_EQUIVARIANCE + dataset extension + CHK battery + CHK-M(14) + spec freeze | local CPU | $0 | `TIER_C_CONSTRUCTION_FAILED` |
| C1 | tournament: 27 runs (cached activations, A1 harness pattern) | 1 self-terminating g4dn.xlarge | ≈ $0.55 (A1 scaling: 12 runs ≈ $0.233) | four-blocker law + watchdog, hard sub-cap $0.80 |
| C2 | dose axes on winner: 21 runs | same pattern | ≈ $0.45, sub-cap $0.60 | same |

Cumulative program spend before Tier C ≈ $1.71 of the $30 ceiling. Tier C adds ≈ $1.00
at estimate, ≤ $1.40 at caps. All AWS us-west-2, one instance per phase, self-terminating
user-data + client watchdog, receipts by `instance_runtime_estimate` (authoritative) with
`compute_wall_estimate` reported alongside as lower bound, per the standing method law.

C0 → owner sees proof artifact + battery report → **owner-signed approval required before
C1 spend**. C1 → results + status → owner ruling before C2.

## 10. Harness laws inherited from the 3bbcd2c1 independent audit

The audit (PATHB_A1_INDEPENDENT_AUDIT.json) found zero numerical discrepancies but four
form/robustness findings. Each becomes a Tier C law:

1. **Persist every gate's raw inputs** (fixes F1). No gate boolean may enter a results
   JSON without the raw numbers it was computed from stored beside it (grad norms,
   deltas, counts). "Unverifiable from committed artifacts" must be impossible.
2. **Tightened survives-clause** (fixes F2). Best-family-removal requires residual
   margin ≥ 0.01 against ALL comparison arms, not strict positivity vs one arm.
   (A1's audited residuals: 0.006222 vs S6, 0.001333 vs S0, 0.008000 vs SALT50.)
3. **Cache binding** (fixes F3). Activation caches are stamped with the dataset content
   sha256 and checked on load; per-record candidate-count/shape assertions in pack().
4. **Receipt law** (fixes F4). Every cloud run files a standalone receipt (instance id,
   runtime, self-termination statement, cost + method = instance_runtime_estimate) in
   the SAME commit as its results. A crashed run gets a receipt too.

## 11. What Tier C cannot show (registered up front)

- It cannot promote any claim to the spec sheet above development status.
- A `TIER_C_CAS_STRUCTURAL_SIGNAL_DEV` outcome shows the CAS-derived table helped THIS
  synthetic task under THIS matched control — not that transformers are CAS-structured,
  not that the structure is uniquely CAS (one matched control is one control).
- Faithfulness measurements describe the learned route; they do not certify the formal
  derivation is "how the model thinks."
