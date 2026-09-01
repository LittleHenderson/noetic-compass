# TIER C SPEC v0.2 — governing document (C0 authorized)

**Status: C0 CPU construction AUTHORIZED by owner ruling "TIER C v0.2 — C0 CONSTRUCTION
AUTHORIZED" (2026-09-01). C1/C2 GPU execution NOT YET AUTHORIZED — waits on C0 gates and
a focused owner review. Non-claim-bearing. No GPU. No protected read. No claim promotion.**

Supersedes `TIER_C_DESIGN_v0_1.md` wherever they differ. The owner authorized the C0
DIRECTION under binding amendments — not a line-by-line endorsement of v0.1 (owner's
explicit honesty point: v0.1 was summarized to the owner, not read in full).

Predecessor record preserved: commit `3bbcd2c1`, status `NO_PATH_B_OPERATION_SIGNAL`,
separated component findings per `PATHB_A1_COMPONENT_FINDINGS.json`.

---

## 1. The Tier C question (amended per ruling)

Stop testing whether labels help. Test whether a **fixed operation algebra** gives the
neural system an advantage over **learned and data-derived relation machinery**.

Owner's control-logic amendment (binding): a matched random table is still WRONG
relational information — PATH B proved wrong signs are misinformation, not a weaker dose.
Therefore `R-RANDOM` is classified `RELATIONAL_MISINFORMATION_CONTROL`, NOT the
CAS-specificity control. Beating R-RANDOM establishes only "correct task-aligned
structure beats wrong task-matched structure." The serious rivals ("killer controls"):

- **R-LEARNED** — same tensor shape and parameter budget, randomly initialized,
  learned from training data.
- **R-EMPIRICAL** — frozen relation structure estimated ONLY from training traces,
  without importing the CAS composition table.

Only if the fixed CAS structure beats these may the result be described as a **CAS
relational-prior advantage in development**. "CAS-specific" remains prohibited until the
standing claim law's matched-control and protected-evaluation requirements are met.

## 2. The frozen relation algebra R = (M, C, J)

Minimal typed algebra — no kitchen-sink matrices, no invented continuous strengths.
Derivation is deterministic (`tier_c_structure.py` → `tier_c/R_CAS.json`); every cell
carries `{value, status: DERIVED|UNDEFINED, source_rule, derivation}`.

Derivation sources (ONLY these):
1. **Solver semantics** — the frozen `solve()` rules in `pathb_core.py` (lines 241-282)
   for the three RETAINED primary families. QB_ORD's rule is excluded (family dropped,
   final for this dataset version; its side condition is discourse order, not relational
   algebra).
2. **CAS structural invariants** (canonical layer): involution pair CO-2↔CO-3; the duals
   of `^6` (CO-5) and `^8` (CO-9) are absent from the operation vocabulary.

**M — ordered defined-composition mask** (rows = first op a, cols = second op b):

| a\b | ^2 | ^3 | ^6 | ^8 |
|---|---|---|---|---|
| ^2 | 0 | 0 | **1** (INT: idea-bridge) | **1** (COMP: mind-bridge) |
| ^3 | **1** (REL: mind-bridge) | 0 | 0 | 0 |
| ^6 | 0 | 0 | **1** (INT join: part-intersection) | 0 |
| ^8 | 0 | 0 | 0 | 0 |

An undefined entry is typed UNDEFINED — never silently an ordinary numerical zero
(the φ encoding gives UNDEFINED its own indicator dimensions).

**C — ordered composition-result tensor** (typed planes; one-hot result classes):
- result_type ∈ {IDEA, PART_SET, PART, UNDEFINED}: C[^3,^2]=IDEA (REL answer),
  C[^2,^8]=IDEA (COMP answer), C[^2,^6]=PART_SET (INT step), C[^6,^6]=PART (INT join).
- mediator_type ∈ {MIND, IDEA, PART, UNDEFINED}: MIND, MIND, IDEA, PART respectively.
- Order matters: C[a,b] ≠ C[b,a] wherever only one direction is DERIVED (3 of 4 cells).

**J — typed duality / orientation plane:**
- Pair matrix: diagonal SAME; (^2,^3) and (^3,^2) DUAL (CO-2↔CO-3); all else UNDEFINED.
- Per-class dual presence: ^2 PRESENT, ^3 PRESENT, ^6 NO_DUAL, ^8 NO_DUAL
  (NO_DUAL, neutral, and undefined are distinct typed states).
- Per-class orientation sign ∈ {POS, NEG, NEUTRAL}: ^2 POS (affinity/attracted),
  ^3 NEG (adverse/repelled) — from the canonical definitions; ^6, ^8 NEUTRAL.

**φ — frozen typed pair encoding** (shared by every transform and every R-variant):
φ(a,b) = [M(1) | result_type(4) | mediator_type(4) | J_pair(3) | sign_a(3) | sign_b(3)
| dual_a(1) | dual_b(1)] — 20 binary dims. Design law
`STRUCTURE_VIEW_MUST_CONTAIN_M`: every transform's structure view includes the M bit
(M alone already has trivial automorphism group — degree signature (out,in):
^2=(2,1), ^3=(1,0), ^6=(1,2), ^8=(0,1), all distinct).

Registered dependency disclosure (C0 review): M-only triviality depends on the (^6,^6)
join cell — a symmetric set-intersection recorded on the diagonal (where directedness is
vacuous), categorically unlike the three sequential bridged cells. Without it the M-only
group grows to {identity, ^6↔^8}; the FULL structure stays trivial via the C plane. The
counterfactual computation is persisted in the proof artifact
(`join_cell_counterfactual`).

## 3. PROOF_OF_NON_EQUIVARIANCE (precise phrasing per ruling)

Any relational structure can be consistently renamed. The claim is NOT "the structure
cannot be renamed." The scientific object is the **relational isomorphism class**, not
the literal coordinate names. Enumerate all 24 operation permutations; two tests:

- **Test A — consistent-renaming invariance (must PASS all 24):** permute operation
  profiles + every class-indexed axis of R + coordinate-coupled parameters (W_r rows;
  optimizer state follows) → per-step training losses equal within TOL_A = 1e-6.
  Proves literal names like `^2`, `^3` are coordinates, not content.
- **Test B — structure-held-fixed sensitivity (absorption must FAIL for every
  non-automorphism):** permute profiles while R is held fixed, apply the full
  class-indexed absorption recipe (the recipe that conformed at 7.15e-07 in A1's
  S-PERM test) → divergence must be ≥ FLOOR_B = 1e-3 for all 23 non-identity
  permutations, for every tournament transform, on every registered data seed. A
  transform whose permuted twin still conforms is REJECTED before any spend.
- **Criterion law (C0 review hardening):** conformance/divergence is measured on
  PER-EXAMPLE loss trajectories (steps × n residuals), never batch means — a free
  init-search can curve-fit 5 batch-mean scalars with hundreds of free parameters
  (the review's attack matched means to 1e-4 while diverging 1.68 per example and
  "absorbing" R_RANDOM under identity labels — a vacuous criterion); it cannot fit
  steps × n per-example residuals. Two independent data seeds guard the
  universally-quantified Test B gate. **Scope law:** Test B refutes the CLASS-INDEXED
  recipe — the complete canonical group action on the only class-indexed parameter.
  Divergence proves the recipe twin is not functionally equivalent, hence the canonical
  action is not a symmetry when R is frozen. It does not claim that no curve-fit of
  scalar summaries exists.
- **Automorphism report:** full group of R-CAS (expected trivial; hand-check: the only
  candidate ^6↔^8 breaks at M[^6,^6]=1 vs M[^8,^8]=0) AND the per-transform
  effective-view groups, all persisted with raw per-permutation numbers.

## 4. Controls (per ruling section 4)

Generated and FROZEN before any neural result (`tier_c_controls.py`):
- **Pool:** ≥ 1000 structurally matched, pairwise non-isomorphic candidate structures,
  none isomorphic to R-CAS. Hard-matched: tensor dimensions, defined-cell count,
  row/column degree multisets, diagonal-defined count, result-class frequencies,
  mediator frequencies, sign/duality counts, M-rank, walk-count vector (lengths 2-4),
  automorphism-group size (=1). Per-stat match table persisted. Shortfall below 1000 →
  gate `CONTROL_POOL_INSUFFICIENT` with exact counts (no criterion loosening).
- **R-RANDOM** (RELATIONAL_MISINFORMATION_CONTROL): the pool entry with the smallest
  SHA-256 of its canonical form — a frozen selection law, chosen blind to any neural
  result.
- **R-EMPIRICAL:** M/C planes estimated from train-split edge traces of the three
  primary families only, under the registered ESTIMATOR LAW (C0 review fix — the C
  plane is genuinely estimated, not transcribed): the mediator of a composed pair is
  the literal shared entity between the two traced clauses' arguments, typed by its
  membership in the split's registered surface entity pools; the result is the record's
  answer entity (typed by pool) or, for a step whose second clause carries a syntactic
  list argument, that list (PART_SET). No family→type table exists in the estimator.
  J plane carries NO information (all UNDEFINED / NO_DUAL / NEUTRAL — duality and sign
  are not trace-observable). Honest pre-registered observation: because the task is
  generated by the solver, M_emp and C_emp are expected to CONVERGE to R-CAS's M/C on
  this dataset; the exact overlap is computed (now a genuine measurement) and persisted. **Consequence: the C2 contrast R-CAS vs R-EMPIRICAL isolates the value of
  the J plane (duality/sign prior) plus any C detail not trace-visible.** A tie means
  the composition machinery is data-derivable here (`RELATIONAL_MACHINERY_SUFFICIENT`);
  it does not license a CAS-prior claim and is recorded as the honest outcome.
- **R-LEARNED:** trainable tensor, φ-shaped, same parameter budget, random init —
  instantiated in the C1/C2 harness (definition frozen now).
- **R-ZERO:** exact class labels, no relational table (the A1 S3 configuration —
  isolates the table's value beyond labels).

## 5. QC_VALID — diagnostic only (per ruling section 1)

Role: structure-consumption and faithfulness probe. EXCLUDED from primary win status,
headline task accuracy, and best-family-removal. Construction:
- Two-clause passages realizing an entity-bridged ordered class pair in the licensed
  slots, built from the three ASYMMETRIC defined cells: (^3,^2) mind-bridge, (^2,^8)
  mind-bridge, (^2,^6) idea-bridge. (The symmetric (^6,^6) cell admits no
  order-flipped twin and is out of QC scope — registered.)
- **Paired counterfactuals:** the invalid twin is the SAME two clause strings in
  swapped discourse order — a string permutation, which cancels every ORDER-INSENSITIVE
  surface statistic exactly (C0 review wording fix: gold is by design a function of
  clause order, so ORDER-SENSITIVE shallow cues can correlate with it through
  class-conditional verb/form length differences; a registered char-level surface
  adversary measures that ceiling and persists it as a disclosure — standing char-level
  control law honored). The swapped class order lands on an UNDEFINED cell. Gold =
  M[cls(first), cls(second)] under the registered discourse-order convention.
- Question: one frozen function-word frame, zero operation verbs. Candidates: the
  registered constant pair ("carried", "stalled"), shuffled per record (candidate law).
  Passage-id tags are HashPRNG-scrambled per pair (C0 review fix: the original v/x
  suffix encoded gold with 100% fidelity), with a decorrelation gate.
- Gates: independent round-trip (class-disjoint verb-inventory regexes over the full
  registered inventory; recompute gold from frozen M), pair integrity (twin = exact
  string swap, gold flipped), 50/50 balance, gold-candidate-first fraction ≈ 0.5,
  pid-tag decorrelation, R-only oracle = 1.000 by construction, surface ceiling
  persisted (report-only disclosure).
- Interpretation law: QC accuracy is a consumption diagnostic under matched training
  exposure — a model can learn the 3-cell mapping from data without reading R, so the
  informative readout is the contrast between R-variants, not QC accuracy alone.

**R-only shortcut law (primary families):** an adversary receiving ONLY the ordered
clause class sequence + R features + candidate position (NO entity identities, NO
candidate types, NO clause text) must score ≤ candidate-chance + 0.05 on EVERY primary
family, else the relational table has become another answer key
(`RONLY_SHORTCUT_DETECTED`). Candidate type is deliberately excluded: the answer's
entity type is a task-structural given already measured by B-MEMBER/B-KEY, not a
relational-table leak — registered rationale.

## 6. Evidence hardening (per ruling section 5 — Tier C code laws)

- **Cache binding** (`tier_c_cache_binding.py`): every activation cache binds
  {canonical per-record SHA-256, passage id, dataset-manifest SHA-256, model SHA-256,
  tokenizer SHA-256, selected layer, extraction-code SHA-256, candidate-span digest};
  loader requires EXACT set equality between dataset records and cache records and
  per-record digest match; any mismatch → `CACHE_BINDING_VIOLATION`, fail closed.
- **No Boolean-only gates:** every gate persists the raw quantities that decided it
  (gradient norms, divergences, accuracies, counts, per-permutation numbers). The A1
  `gate_s3_profile_grads` unverifiability cannot recur.
- **Receipt law:** every future cloud run files a standalone receipt (instance id,
  runtime, self-termination statement, cost + method) in the same commit as results.

## 7. C1 — transform tournament (NOT YET AUTHORIZED; law frozen now)

Same frozen task/data/seeds {11,23,47}/optimizer/compute; matched parameter counts
(±1%); λ_structure init 1.0 (the λ-lock law). Arms: T0 (no structure), T1 (additive
structural routing), T2 (operation-conditioned matrix transform), T3 (bilinear
question-operation-entity transform), T4 (recurrent composition tensor) — each with
R-CAS. Purpose: find which transform can USE R. A win over R-RANDOM at C1 is not yet
a CAS-content claim. Hard cap **$0.80**; one instance; no autoscaling; self-terminating
+ watchdog; actual and estimated cost recorded separately; no unused budget transfers
to C2.
- C1 statuses: `NO_TRANSFORM_CONSUMES_STRUCTURE` (no Tx beats T0 by ≥0.02 on ≥2/3
  primary families) | `TRANSFORM_SELECTED:<Tx>` (best Tx by the frozen margin law;
  ties broken by pre-registered order T1<T2<T3<T4 favoring the simpler transform).

## 8. C2 — structure-content and dose test (NOT YET AUTHORIZED; law frozen now)

Winning transform only, frozen; exactly seven conditions × three seeds = 21 runs:
1. R-CAS  2. R-LEARNED  3. R-EMPIRICAL  4. R-ZERO  5. R-RANDOM (misinformation)
6. R-ATTENUATED50 (φ features blended 0.5 toward the uninformative encoding —
   information amount)  7. R-CORRUPTED50 (frozen hash-keyed 50% CELL-TRANSPLANT
   corruption, v2 law per C0 review: each corrupted cell receives the full typed
   content of a uniformly drawn different R-CAS cell — expected defined-cell density
   preserved, no density confound — and the J pair/sign/dual planes are corrupted by
   the same per-entry law — information wrongness). The two dose axes stay separate;
   "50% wrong" is never called a half-dose. Hard cap **$0.60**.
- Frozen C2 status law (deterministic program; margins on primary-family accuracy):
  - `NO_TIER_C_STRUCTURAL_SIGNAL` — R-CAS fails to beat R-ZERO by ≥0.02 on ≥2/3
    primary families.
  - `RELATIONAL_MACHINERY_SUFFICIENT` + `CAS_PRIOR_NOT_SEPARATED` — R-CAS beats
    R-ZERO but not BOTH killer controls (R-LEARNED, R-EMPIRICAL) by ≥0.02 each on
    ≥2/3 primary families with best-family-removal residual ≥0.01 vs ALL rivals.
  - `TIER_C_CAS_RELATIONAL_PRIOR_ADVANTAGE_DEV` — R-CAS beats R-ZERO, R-LEARNED and
    R-EMPIRICAL by the full margin law. Development language only; "CAS-specific"
    remains prohibited.
  - Report-only axes: R-RANDOM (misinformation sensitivity), R-ATTENUATED50
    (attenuation monotonicity: R-ZERO ≤ R-ATTENUATED50 ≤ R-CAS expected; violation is
    a finding, not a gate), R-CORRUPTED50 (wrongness sensitivity), QC_VALID
    consumption contrast, formal-path faithfulness (bridge agreement, forced-path
    delta, blocked-path delta, per-example coupling; statuses
    `FORMAL_PATH_FAITHFUL_DEV` / `USEFUL_BUT_UNFAITHFUL_ROUTE` / `UNESTABLISHED`).

## 9. QB-ORD (per ruling section 7)

REMAINS DROPPED. `QB_ORD_REJECTED_POSITION_SHORTCUT: FINAL FOR THIS DATASET VERSION`
(clean position-probe L6 0.789 / L12 0.846 / L18 0.848 / L24 0.792, all < frozen 0.90).
The 0.90 gate is not lowered or reinterpreted. Return only via a newly versioned family.

## 10. C0 gate battery (this build; all CPU, $0)

| Gate | Content | Fail status |
|---|---|---|
| G-C0-1 | R_CAS derived; every cell DERIVED/UNDEFINED with source rule; schema forbids continuous strengths | TIER_C_CONSTRUCTION_FAILED |
| G-C0-2 | Aut(R_CAS) trivial over all 24 perms (raw per-perm violations persisted) | TIER_C_CONSTRUCTION_FAILED |
| G-C0-3 | Test A conforms ≤1e-6, all 24 perms × T1-T4 | TIER_C_CONSTRUCTION_FAILED |
| G-C0-4 | Test B diverges ≥1e-3, all 23 non-identity perms × T1-T4 | TIER_C_CONSTRUCTION_FAILED |
| G-C0-5a | control pool ≥1000 matched non-isomorphic; R-RANDOM frozen by law | CONTROL_POOL_INSUFFICIENT |
| G-C0-5b | R-EMPIRICAL built (estimator law) + overlap persisted + Aut trivial; R-CORRUPTED50 v2 frozen | TIER_C_CONSTRUCTION_FAILED |
| G-C0-6 | QC_VALID round-trip 100%, pair integrity 100%, balance 50/50, gold-first ≈0.5, pid decorrelated, R-only oracle 1.000, surface ceiling persisted | TIER_C_CONSTRUCTION_FAILED |
| G-C0-7 | R-only adversary ≤ chance+0.05 on every primary family (train-fit, val-eval) | RONLY_SHORTCUT_DETECTED |
| G-C0-8 | cache-binding schema + verifier unit tests pass | TIER_C_CONSTRUCTION_FAILED |
| G-C0-9 | mutation battery M13-M17 all detected under the 7-point validity law | TIER_C_CONSTRUCTION_FAILED |

Receipt: `tier_c/TIER_C_C0_RECEIPT.json` — deterministic verdict = first failed gate,
or `TIER_C_C0_READY_FOR_FOCUSED_REVIEW`. Every gate's raw quantities persisted; the
receipt is byte-reproducible (wall clock to stdout only) and records library versions
(C0 review: sklearn-dependent gate numbers are version-scoped facts).

**C0 adversarial review record:** before the owner's focused review, a 14-agent
adversarial workflow attacked the build (5 dimensions + per-finding verification).
Findings, verdicts, and the applied fixes: `TIER_C_C0_REVIEW_FINDINGS.json`. The one
CRITICAL claim (an init-search can match Test B's batch-mean losses) was REFUTED as an
absorption (it diverges 1.68 per example and "absorbs" R_RANDOM under identity labels)
but its hardening was adopted anyway: the criterion is now per-example trajectories.

## 11. Prohibitions (standing)

No GPU in C0. No protected read (generation guard untouched; Tier C adds NO protected
records). No claim promotion. No status rewrite of any frozen record. Prohibited claim
terms unused. QB-ORD stays out. C1/C2 launch only after owner-signed approval following
the focused review of this C0 package.
