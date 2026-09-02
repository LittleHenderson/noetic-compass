# RGM-0.1 FINDINGS — plain English (builder's report; independent cross-model audit invited)

Owner ruling executed: RGM-0.1 correction round (audit closure + attribution repair).
Mechanism name (binding): BOUNDED_ACTIVATION_PROPAGATION. $0, CPU-only, no GPU, no model, no
protected data. Branch research/cmb-r1-rgm0-v1; v0.1 commit 95cedfe5 and all original artifacts
PRESERVED, not rewritten. Original status annotated per owner: PARTIAL_PASS.

# THE TEN REGISTERED STATUSES (20 independently seeded worlds; world = statistical unit)

STATIC_GEOMETRY_VALUE        SUPPORTED        B>A +0.0493 mean world delta, 19/20 worlds
TRAJECTORY_VALUE             SUPPORTED        C>B +0.0305, 20/20 worlds
GRAPH_PROPAGATION_VALUE      SUPPORTED        best prop (D) vs C on pattern completion +0.3330, 20/20
ADDITIVE_CORROBORATION_VALUE SUPPORTED        D vs X_MAX on corroboration +0.4856, 20/20 worlds
RESONANCE_SPECIFIC_VALUE     SUPPORTED*       D vs best graph control (X_SUM) aggregate +0.0159, 20/20
GENERIC_GEOMETRY_ADVANTAGE   SUPPORTED        D vs E2 (real generic) +0.1217, 20/20 worlds
COHERENCE_ECHO_CONTROL       FAILED           near-miss attack penetrates the TAU_COH boundary
PROVENANCE_ROOT_CONTROL      NOT_SUPPORTED    root-only unsafe: echo 334/400, overlap 327/400
RETRIEVAL_EFFICIENCY         SUPPORTED        corrected per-query ratio mean 0.0105, median 0.0104
SELECTIVE_REPLAY_READINESS   NOT_READY        completion recall 0.336 < 0.50 bar; coherence gate failed

*See the asterisk note below — the gate fired, but the value has one source.

# The three headline facts

1. THE AUDIT'S ATTRIBUTIONS REPRODUCE EXACTLY ACROSS 20 WORLDS. Echo defense: BOTH config safe
   (0/460), coherence-only safe (0/460), root-only UNSAFE (334/460), neither (443/460 unsafe).
   The defense is trajectory-coherence, not provenance-root counting. The relabeled
   misinformation control (M_NOISE) collapses to 0.2471 aggregate. And the efficiency bug
   repair reproduces the auditor's number: corrected ratio 0.0105 mean (their 0.0104).

2. RECURRENT PERSISTENCE HAS EXACTLY ONE REAL ADVANTAGE: ADDITIVE CORROBORATION. Arm means:
   A 0.5913, B 0.6426, C 0.6981, X_MAX 0.7069, E2 0.7280, X_SUM 0.8338, D 0.8497.
   Per-family, the plain additive expansion X_SUM BEATS the recurrent engine on LOOKALIKE
   (0.9789 vs 0.9733), ORDER_MATTERS (0.9835 vs 0.9789), and CROSS_DOMAIN (0.9872 vs 0.9833),
   ties pattern completion (0.3313 vs 0.3361 — inside the margin), and loses corroboration
   badly (0.8881 vs 0.9768). The aggregate gate fired SUPPORTED, but the honest reading is:
   the recurrent engine's value IS corroboration accumulation, nothing else. Twenty independent
   worlds confirm the cross-model audit's per-family finding.

3. THE EXISTING KNOBS ARE NEARLY INERT. Ablations across 20 worlds: no damping 0.8491,
   coupling 1.0 0.8489, depth 5 0.8492, inhibition off 0.8494 — against D 0.8497. Removing
   damping, doubling coupling, deepening propagation, or removing inhibition moves the
   aggregate by less than 0.001. The owner's "do not add pulse knobs" ruling is now measured,
   not just argued: the dials already present do almost nothing. (X_MAX has none of them and
   still beats C.)

# New vulnerability found (was not in the audit)

NEAR-MISS ECHO PENETRATES EVERY CONFIGURATION. One substituted operation (levenshtein 1 —
similarity 0.75-0.833, at the TAU_COH = 0.75 boundary) lets 20 false copies into the top-5 in
~90% of attack queries under EVERY config, including both defenses on (359/400). The saving
nuance: falses almost never rank ABOVE a true memory (3/400 above-a-true violations under
BOTH) — the witnesses still win. But by the frozen top-5 criterion the coherence gate FAILED,
and that is the correct status: the boundary is open. Any RP0 design must close it (e.g.
margin-above-threshold admission, or witness-quorum gating) before replay selection trusts
the verified set.

# Real generic geometry (the repaired opponent)

E2 is a coherent 5-role event language (TRIGGER/ASSESS/DECOMPOSE/OUTCOME/STATE — a deliberate
coarsening that loses the CAS 2-vs-3 distinction), query mapped by the same coarsening, links
rebuilt by role similarity with the same procedure, same verifier including geometric
coherence. CAS beats it by +0.1217 aggregate, 20/20 worlds, and E2 fails pattern completion
entirely. The v0.1 "generic" arm (noise, no query mapping, weakened verifier) is retained as
M_NOISE, RELATIONAL_MISINFORMATION_CONTROL: 0.2471.

# Determinism and integrity

Two full battery passes byte-identical on content: canonical hash 56ff7d7ae3512252 (the first
hash attempt included wall-clock timing and was voided — the voiding is recorded in the
receipt; content was never in doubt, the hash was wrong). CHK-M battery: all 7 mutants fired
(N1 static zeroed, N2 order-insensitive, N3 propagation off, N4 law-level generic-equals-CAS,
N5 echo coherence removed, N6 charging bug reintroduced, N7 root-defense fiat — the gate
refused all seven). The recurrent engine exactly reproduces the frozen v0.1 resonate()
activation sets (unit test), tying this battery to the audited artifact.

# Deviations honored (spec addendum v0.1)

V1 two passes (not three) for determinism; V2 arm H cut; V3 corruption control rests on the
preserved v0.1 result; V4 peak memory via tracemalloc. Ten statuses per the owner directive —
no single pass/fail word. RGM-1 and CMB-RP1 NOT started (not authorized).

# Builder's bottom line

The corrected battery says: ordered geometry is a real second key, trajectory order a real
third, graph propagation a real fourth — and the recurrent engine earns its keep ONLY as an
evidence accumulator. The echo shield is coherence, it has a hole at the one-step boundary,
and provenance roots do not shield anything on this bench. The memory board is ready to be
re-modeled honestly: a damped accumulator over an ordered-geometry graph with a coherence
verifier that needs a boundary margin — pointed at the replay-selection problem, which it is
NOT yet ready to take.

---

# AUDIT ANNOTATION (Claude audit 2f62fb5a, PARTIAL_PASS with blocker — appended, original text above preserved)

1. BLOCKER (CHANGELOG destruction) — OWNED AND FIXED at dfa08de8. Cause: the builder read 30
   lines of the shared ledger and rewrote the whole file. Rule adopted: append-only operations
   on shared ledgers use append-only tools.
2. RESONANCE_SPECIFIC_VALUE — OVERTURNED, builder concurs. Per-family D-X_SUM: LOOKALIKE
   -0.0055 (1/20 worlds), ORDER_MATTERS -0.0046 (0/20), CROSS_DOMAIN -0.0040 (0/20),
   PATTERN_COMPLETION +0.0047 (3/20), INDEPENDENT_CORROB +0.0887 (20/20). Drop-one residual
   -0.0023. The SUPPORTED status was a one-family-dominated aggregate that double-counted
   ADDITIVE_CORROBORATION_VALUE. The real mechanism (auditor identified): D and X_SUM differ
   only in activation persistence; decay magnitude is inert, so the carry-forward itself is
   the mechanism. Pending owner ruling: NOT_SUPPORTED, or the scoped label
   ACTIVATION_PERSISTENCE_CORROBORATION_INCREMENT.
3. LAW EXTENDED (second occurrence of this defect class): drop-one residual now applies to
   EVERY gate without exception — recorded as spec amendment V5 below.
4. UPHELD by audit: GENERIC_GEOMETRY_ADVANTAGE (drop-one +0.0698/+0.0778),
   COHERENCE_ECHO_CONTROL FAILED (BOTH 359 indistinguishable from NEITHER 360 on near-miss),
   PROVENANCE_ROOT_CONTROL NOT_SUPPORTED, RETRIEVAL_EFFICIENCY SUPPORTED, all seven typed
   mutants, the E2 repair (C-1/C-2 closed).
5. COMPUTE (auditor-measured): 87% of runtime is 2,647,625 Levenshtein calls on integer
   sequences of length 3-6; GPU cannot accelerate this kernel class; measured path: 2.26x
   (dedup vs 714 distinct trajectories) x ~20x (world parallelism) = ~39x, all CPU; heavy
   batteries move to AWS compute-optimized instances. Owner compute ruling pending.
