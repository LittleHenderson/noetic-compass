# CMB-R1 / RGM-0.1 SPECIFICATION ADDENDUM v0.1 — FROZEN BEFORE FIRST RUN

Owner ruling: RGM-0.1 correction round AUTHORIZED. Claude audit (68fdf570) ACCEPTED.
Original commit 95cedfe5, its status, and all original artifacts PRESERVED — no history rewrite.
Original status annotated: PARTIAL_PASS / GRAPH_PROPAGATION_VALUE_SUPPORTED /
RESONANCE_SPECIFIC_VALUE_NOT_ESTABLISHED.
Mechanism naming (binding): BOUNDED_ACTIVATION_PROPAGATION. The words "resonance-specific",
"CAS-specific", and "provenance control" (for the current defense) are prohibited in all
reports and commit messages. Correct labels: trajectory-coherence echo control; provenance-root
control (as a separate, separately-tested mechanism).

## Frozen constants

Inherited from v0.1: SEED base 20260901, N=1600 base memories, 32 topics, SEM_DIM 32, CTX_DIM 16,
W_SEM=W_GEO=0.5, SEED_K=25, DEPTH=3, DAMPING=0.3, GAMMA=0.5, TOPK_WAVE=20,
FINAL 0.45/0.35/0.20, NOVELTY_TAU 0.60, TAU_COH 0.75, MARGIN 0.010, NONINF 0.005.
New: N_WORLDS = 20 (world seeds = 20260901 + 1000*w, w = 0..19); determinism = 2 full battery
passes, byte-identical. World = primary statistical unit. Gate rule: mean world delta >= MARGIN
AND >= 70% of worlds (>= 14/20) show delta > 0 (unless stated otherwise).

## Arms (per world)

A SEMANTIC_ONLY; B SEMANTIC_PLUS_STATIC_CAS; C SEMANTIC_PLUS_CAS_TRAJECTORY (expensive on all N);
D BOUNDED_ACTIVATION_PROPAGATION (v0.1 recurrent: (1-d)a + gWa, root budget);
D_NODAMP (d=0); D_G1 (g=1.0); D_DEPTH5; D_NOINHIB (TOPK_WAVE=200);
X_MAX best-first max expansion (same seeds/graph/depth/budget/rescoring/verifier; score =
max over predecessors, no persistence);
X_SUM bounded additive message passing (sum of incoming messages, no persistence onto already
active nodes beyond their seed score);
E2 REAL GENERIC GEOMETRY: coherent 5-role event alphabet (TRIGGER/ASSESS/DECOMPOSE/OUTCOME/STATE
via a fixed many-to-one coarsening of CAS ops — loses the 2-vs-3 distinction by design), query
mapped by the same coarsening, same verifier including geometric coherence on role trajectories,
links rebuilt by role-trajectory similarity (same top-3+1-random procedure -> same degree stats);
M_NOISE the v0.1 marginal-noise arm, relabeled RELATIONAL_MISINFORMATION_CONTROL (report-only);
H CUT (never fired, duplicated B — cut documented).
Echo attribution configs (ECHO family only): BOTH (root budget + root dedup + coherence),
ROOT_ONLY (no coherence), COH_ONLY (no root budget/dedup), NEITHER. Harder attacks:
near-miss false cluster (trajectory = adjacent transposition of the true trajectory — lev 1)
and overlapping-provenance cluster (2 roots x 10 copies).

## The ten claim statuses (separate; no single pass/fail word)

G_STATIC  STATIC_GEOMETRY_VALUE: B vs A on LOOKALIKE.
G_TRAJ    TRAJECTORY_VALUE: C vs B on ORDER_MATTERS + CROSS_DOMAIN + PATTERN_COMPLETION.
G_PROP    GRAPH_PROPAGATION_VALUE: best of {D, X_MAX, X_SUM} by mean world MRR vs C on
          PATTERN_COMPLETION (primary).
G_ADDCORR ADDITIVE_CORROBORATION_VALUE: D vs X_MAX on INDEPENDENT_CORROB (accumulation vs max).
G_RESON   RESONANCE_SPECIFIC_VALUE: D vs best(X_MAX, X_SUM) aggregate over ranked families.
G_GENERIC GENERIC_GEOMETRY_ADVANTAGE: D vs E2 aggregate; if E2 >= D - NONINF, note
          GENERIC_SUFFICIENT.
G_COHECHO COHERENCE_ECHO_CONTROL: COH_ONLY safe (false memory not in top-5) on ECHO AND on the
          near-miss attack in >= 19/20 worlds.
G_ROOT    PROVENANCE_ROOT_CONTROL: ROOT_ONLY safe on ECHO AND on the overlapping-provenance
          attack in >= 19/20 worlds (expected NOT; honest either way).
G_EFF     RETRIEVAL_EFFICIENCY: corrected per-query expensive-call ratio, best propagation arm
          vs C, mean AND median < 0.25 across worlds. Also report edge evaluations, activated
          memories, propagation depth, wall-clock per arm, and peak memory (tracemalloc).
G_REPLAY  SELECTIVE_REPLAY_READINESS: composite readiness flag (NOT a scientific gate):
          best-prop PATTERN_COMPLETION recall@5 mean >= 0.50, BOTH-config echo safe in all
          worlds, graph integrity checks pass, G_EFF passes. Output READY_FOR_RP0_DESIGN or
          NOT_READY with reasons. No RP0/RGM-1 work is started.

Corruption control: dropped from the 0.1 battery (not disputed by the audit; v0.1 result stands,
artifact preserved). Per-world and per-family results persisted in the receipt.

## Mutations (CHK-M for the new gates)

N1 static term zeroed -> G_STATIC must fail. N2 order-insensitive trajectory -> G_TRAJ must fail.
N3 propagation disabled -> G_PROP must fail (pattern completion collapses). N4 law-level: E2 fed
D's aggregates -> G_GENERIC must fail to establish. N5 echo coherence removed from BOTH config ->
G_COHECHO must fail. N6 efficiency counter re-bugged (family-level charging) -> G_EFF must flag.
N7 root-only defense declared safe by fiat -> G_ROOT must flag NOT supported (proves the gate
does not rubber-stamp). Pristine rerun byte-identical after mutants.

## Deviations declared

V1. Battery passes = 2 (not 3) for determinism, to fit compute; v0.1 established the triple-run
protocol and its hash discipline is unchanged. V2. Arm H cut. V3. Corruption control moved to
report-only-via-v0.1. V4. Peak memory measured with tracemalloc around the propagation stage.
