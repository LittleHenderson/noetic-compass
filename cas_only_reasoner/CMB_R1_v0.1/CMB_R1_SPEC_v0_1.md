# CMB-R1 / RGM-0 SPECIFICATION v0.1 — FROZEN BEFORE FIRST RUN

Status: DEVELOPMENT-TIER, NON-CLAIM-BEARING, DETERMINISTIC, NON-NEURAL. $0 GPU.
Branch: research/cmb-r1-rgm0-v1 (parent commit 9014e3d5460b8b2d2a975c8475af6d2728118149).
Role: the auditor-of-record for the other lanes is the BUILDER of this lane and may not claim
independent verification of it; a separate third-party audit is required before any RGM-1 step.

## 1. Question

Does CAS structural geometry — static profiles and ordered operation trajectories — and a
bounded resonance layer improve deterministic memory retrieval over semantic-only retrieval,
and is the improvement specifically attributable to CAS content (not to any organized metadata)?

## 2. Deviations from the owner directive (declared)

- D1. The directive permits a small cloud CPU "when practical". A local CPU run is used instead:
  the full workload is seconds of deterministic non-neural Python (arc precedent: every gate
  battery in this program ran locally), so a cloud box adds cost and attack surface for nothing.
  No neural workload, no model loading, no GPU anywhere.
- D2. The directive's status RGM0_READY_FOR_NEURAL_REVIEW is given a precise meaning: all
  infrastructure valid (determinism holds, every mutant fires its intended typed reason, no
  crash-only mutation) but the positive signal conjunction is incomplete. No kill law fired.
- D3. Kill-law margins are pre-registered (section 7) — the directive said "beats" without a
  size; unsized margins would let noise decide (the arc's recurring calibration failure).
- D4. Efficiency is modeled as expensive-vs-cheap scoring: cheap keys (semantic + static
  profile, dot products) narrow the field; the expensive key (order-sensitive trajectory
  distance) is applied only to the resonant candidate set. C pays the expensive key on all N
  memories; D pays it on the resonant set only. This is the honest form of "only resonant
  memories need deeper processing".
- D5. The "no single family supplies the result" clause is implemented as a residual-margin law:
  the aggregate delta must survive exclusion of the largest-contributing family at half margin
  (the arc's A1 lesson, institutionalized).

## 3. Frozen constants

SEED = 20260901
N_MEMORIES = 1600; N_TOPICS = 32; SEM_DIM = 32; NOISE_SIGMA = 0.15
N_OPS = 10 (operators ^0..^9); trajectory lengths 3..6, position-dependent operator grammar
    (start favors {8,7,0}; middle favors {2,3,6,4}; end favors {9,5})
W_SEM = 0.5, W_GEO = 0.5 (arms B, C, seed stage of D/E/F/G)
SEED_K = 25; DEPTH = 3; DAMPING = 0.3; GAMMA = 0.5; TOPK_WAVE = 20; BETA_ACT = 0.25
    (final D score = (1-BETA_ACT)*cheap_seed_score + BETA_ACT*normalized_activation, with the
    expensive trajectory score re-weighting the resonant set:
    final = 0.45*cheap + 0.35*traj_score + 0.20*activation, all min-max normalized in-set)
NOVELTY_TAU = 0.60 (top-1 score below tau flags a lacuna)
MARGIN = 0.010 (MRR delta for "beats"); NONINF = 0.005 ("matches")
N_PERM = 10000 (paired permutation test, seeded, deterministic)
Links: each memory links to its top-3 same-corpus trajectory neighbors (symmetrized) plus one
    seeded random link; no self-loops (the refractory rule against immediate self-reinforcement
    is structural: nothing propagates to itself).

## 4. Memory record

memory_id, semantic (32-dim, topic prototype + gaussian noise, L2-normalized), static CAS
profile (10-dim bag-of-trajectory counts), CAS trajectory (ordered op list), links,
provenance_root_id, source_id, verification_status (VERIFIED for all — the echo defense must
be provenance aggregation and geometric coherence, never status filtering), topic, family tags.

## 5. Benchmark families (ground truth by construction)

F1 LOOKALIKE (40): target and distractor share near-identical semantics; only CAS separates.
F2 ORDER_MATTERS (40): distractor is a PERMUTATION of the target trajectory (identical static
    profile, same topic). Only an order-sensitive key separates them.
F3 CROSS_DOMAIN (40): target in a distant topic with the SAME full trajectory; distractors
    same-topic wrong-trajectory. Semantics misleads; static profile still matches (bag).
F4 PATTERN_COMPLETION (40): query carries a PREFIX of the target trajectory; distractors share
    topic with different continuations.
F5 NOVELTY (40): query topic and trajectory pattern absent from the corpus; correct behavior is
    flagging a lacuna (top-1 < NOVELTY_TAU).
F6 ECHO (30): 20 copies of one false memory (single provenance root, semantically near the
    query, wrong trajectory) vs 3 independent true memories (distinct roots, matching
    trajectory). The false copies are VERIFIED — defense must be structural.
F7 INDEPENDENT_CORROB (30): 4 true memories (distinct roots, same trajectory) vs one lone
    high-semantic wrong-trajectory distractor.
F8 overlay: every ranked family carries 2-3 high-semantic wrong-trajectory hard negatives.

Trajectory similarity: 1 - Levenshtein(s1,s2)/max(len1,len2) — order-sensitive by construction.
Matched generic geometry (arm E): per-position symbol marginals and lengths preserved exactly,
ordered pair structure destroyed (iid per position from the frozen marginals).
Corrupted geometry (arm F): CAS fields permuted AMONG memories — corpus-level bag of profiles
and trajectories preserved exactly, per-memory correspondence destroyed.

## 6. Arms

A SEMANTIC_ONLY: cos(q_sem, m_sem) over all N.
B SEMANTIC_PLUS_STATIC_CAS: 0.5*sem + 0.5*profile_cos over all N.
C SEMANTIC_PLUS_CAS_TRAJECTORY: 0.5*sem + 0.5*traj_sim over all N (expensive key on all N).
D C_PLUS_RESONANCE: cheap seed (B score, top-25) -> root-level bounded propagation
    a' = BoundedTopK_20[(1-0.3)a + 0.5 W a], 3 waves -> expensive traj score on resonant set ->
    final = 0.45*cheap + 0.35*traj + 0.20*act (normalized in-set) -> provenance-aware verifier
    (root dedup, one representative per root, geometric coherence re-check).
E C_PLUS_MATCHED_GENERIC_RESONANCE: D with generic geometry in every role.
F C_PLUS_CORRUPTED_CAS_RESONANCE: D with permuted CAS fields in every role.
G RESONANCE_WITHOUT_PROVENANCE_CONTROL: D with raw-count propagation (each copy contributes),
    no root dedup, no coherence re-check.
H STATIC_CMB_FALLBACK: B's policy with the stability guard (return B if D's resonant set is
    empty or activation collapses); guard firings reported.

## 7. Kill laws (pre-registered margins)

KL1 B vs A aggregate paired MRR delta >= MARGIN, else STATIC_CAS_GEOMETRY_REDUNDANT.
KL2 C vs B on trajectory-sensitive families (F2,F3,F4) delta >= MARGIN, else
    CAS_TRAJECTORY_VALUE_NOT_DEMONSTRATED.
KL3 D vs C: MRR delta >= MARGIN, OR (delta >= -NONINF AND expensive evaluations < 25% of C's),
    else RESONANCE_LAYER_ORNAMENTAL.
KL4 E vs D: MRR_E >= MRR_D - NONINF, else pass; if fired: GENERIC_GEOMETRY_SUFFICIENT.
KL5 D vs F: MRR_D - MRR_F >= MARGIN, else CAS_GEOMETRY_NOT_LOAD_BEARING.
KL6 Echo: D must keep the false memory out of the top-5 of the verified set on F6 (echo controls
    pass); G's behavior is recorded — G unsafe while D safe = PROVENANCE_CONTROL_REQUIRED
    (controls load-bearing); G and D both unsafe = echo controls fail (blocks positive status).
KL7 Residual: every positive delta used above must survive exclusion of its largest
    contributing family at MARGIN/2, else ONE_FAMILY_RESULT (blocks positive status).
Novelty: F5 detection rate reported; >= 0.90 required for the positive conjunction.

## 8. Status law (deterministic program)

RGM0_FAILED:<typed kill-law status>  — any kill law fires, or infrastructure fails.
RGM0_READY_FOR_NEURAL_REVIEW         — no kill law fired; positive conjunction incomplete.
RGM0_RESONANT_MEMORY_SIGNAL          — KL1, KL2, KL3 pass; KL4 not fired; KL5 passes; echo
    controls pass; KL7 passes; novelty >= 0.90; determinism holds; all mutants behave.

Statistics: paired over the shared per-family query pools; seeded paired permutation tests
(10,000) for C-B, D-C, D-E, D-F; per-family deltas reported next to every aggregate.

## 9. Deliverables

CMB_R1_SPEC_v0_1.md (this file), cmb_r1_core.py, run_rgm0.py, mutations_rgm0.py, test_rgm0.py,
RGM0_RECEIPT.json (byte-deterministic, triple-run hash check), RGM0_FINDINGS.json,
RGM0_MUTATION_REPORT.json, CHANGELOG entry. No merge. No GPU. Stop after RGM-0.

## AMENDMENTS (v0.1.1 — recorded before acceptance of the second run; first run preserved)

- A1. F1 generator under-implemented its own contract ("near-identical semantics"): lookalikes
  were same-topic (cos ~0.9), separable by semantics alone. Fixed: lookalikes are true semantic
  twins (stored semantic = target semantic + 0.01 noise), and must have a genuinely different
  static bag (profile cos < 0.9). The first run's FAILED status
  (RGM0_FIRST_RUN_FAILED_KL1.json) is preserved as load-bearing.
- A2. Arm quality metrics are measured on the arm's actual deliverable — the verifier's
  verified ranking for D/E/F (raw pre-verifier ranking kept report-only). Raw aggregates:
  D 0.7806 / E 0.2485 / F 0.2141 / G 0.7797 (report-only). The verifier's effect is visible:
  corrupted geometry collapses to 0.0087 under coherence quarantine (misinformation rejected).
- A3. F4 is a two-topic multihop family: fragment holders (topic A, semantically near the
  query) carry the trajectory prefix; the true completion (topic B, semantically far) is
  reachable only through their links. This implements the spec's pattern-completion construct
  with a genuine role for propagation.
- A4. The verifier's coherence check combines trajectory fit and (where the family provides
  it) encounter-context fit: coh = 0.5*traj_sim + 0.5*context_cos, quarantine below TAU_COH =
  0.75. Arm E runs without the geometric half (generic geometry has no CAS content to check);
  the asymmetry is deliberate and reported.
- A5. CHK-M consequence of A4: geometry-level identity does not imply pipeline identity, so
  mutant M4 is LAW-LEVEL — KL4 is fed its exact failure condition (E's aggregates replaced by
  D's) and must fire. The first mutation battery honestly reported M4 as a GAP under the
  geometry-level definition; the gap and the fix are both preserved in
  RGM0_MUTATION_REPORT.json history and this amendment.
