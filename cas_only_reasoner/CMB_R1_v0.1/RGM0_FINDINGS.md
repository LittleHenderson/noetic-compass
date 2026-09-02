# RGM-0 FINDINGS — plain English (builder's report; independent third-party audit required)

PRIMARY STATUS (deterministic program): RGM0_RESONANT_MEMORY_SIGNAL
Triple-run byte-determinism: TRUE. CHK-M mutation battery: see RGM0_MUTATION_REPORT.json.
Spend: $0. No GPU, no model, no protected data. Branch research/cmb-r1-rgm0-v1 (isolated
worktree; parent 9014e3d5460b8b2d2a975c8475af6d2728118149). No merge performed.

## The seven registered questions, answered by the program

1. Does static CAS geometry add beyond semantics? YES — B beats A by +0.0578 mean MRR
   (paired permutation p < 0.001). Residual after dropping the biggest family: +0.0376.
2. Does CAS trajectory add beyond static geometry? YES — C beats B by +0.0340 on the
   trajectory-sensitive families (p = 0.0159). Residual: +0.0118.
3. Does the resonance pipeline add beyond static trajectory retrieval? YES — D beats C by
   +0.0600 (p = 0.0077). The efficiency leg was NOT needed: the expensive-evaluation ratio is
   0.36 (above the 0.25 cap), so D passed on quality alone. Reported as-is.
4. Does CAS geometry beat matched generic geometry? YES — D beats E by +0.5781. Generic
   geometry with identical dimensionality, lengths, and per-position marginals collapses to
   0.2294. The value is the CAS content, not "having organized metadata".
5. Does corrupted geometry damage retrieval? YES, catastrophically — D beats F by +0.7988;
   the corrupted arm falls to 0.0087 because the verifier's coherence check quarantines
   misinformation. Wrong structure is misinformation, not absence (the J0 lesson, now measured
   in a retrieval setting).
6. Do provenance controls prevent echo amplification? YES — 20 copies of one false memory
   (sharing topic AND static profile with the query) cannot outvote 3 independent true
   memories under root-level budgeting, root dedup, and coherence quarantine; the same corpus
   WITHOUT those controls (arm G) is unsafe (false memory in the top-5), and arm E (generic
   geometry) is also unsafe — the echo defense is CAS-specific, not generic.
7. Does resonance improve recall, efficiency, or neither? Recall (quality), measured. The
   efficiency claim is structural (seed economy: 4,255 vs 11,830 expensive evaluations) but
   did not meet the pre-registered 25% cap, so the positive status rests on quality only.

## Where the value enters (per-family, arm D, verified metric)

LOOKALIKE 0.9613 (semantic twins separated only by CAS) | ORDER_MATTERS 0.9412 (permutation
distractors, identical static profiles) | CROSS_DOMAIN 0.9600 | PATTERN_COMPLETION 0.2059
(multihop: the true completion is semantically distant and reachable only through fragment
holders' links — propagation's clearest job) | INDEPENDENT_CORROB 0.9579.

## Honest limits (read before praising)

- L1. This is a SYNTHETIC corpus built so that CAS keys CAN matter. It shows the mechanisms
  extract structure that is there; it cannot show that real text has that structure. The
  neural stage (RGM-1) with construction-gold profiles on real text is the next question.
- L2. The builder designed the corpus, the arms, and the laws — the classic self-test risk.
  Mitigations actually applied: kill laws pre-registered with margins BEFORE the first run;
  the first run FAILED (STATIC_CAS_GEOMETRY_REDUNDANT, preserved as
  RGM0_FIRST_RUN_FAILED_KL1.json) and the failure was traced to a generator that under-
  implemented its own spec (lookalikes were same-topic, not semantic twins) — fixed as a spec
  compliance correction, not a threshold change; matched-generic and corrupted controls; an
  echo family designed so copy count WOULD win without provenance controls; and a mutation
  battery proving every gate fires on a broken mechanism. Still: a third-party audit is
  required before any neural stage.
- L3. D's quality advantage over C includes the verifier stage (propagation + verifier as one
  registered pipeline). The M3 mutant isolates propagation's share: without propagation the
  multihop completion family collapses (the true completion never enters the resonant set).
- L4. The resonance constants (depth 3, damping 0.3, gamma 0.5, budgets) were frozen before
  the run and never tuned. No sweep was run. A sweep would be RGM-1 work.
- L5. Deviation D1 (declared in spec): local CPU was used instead of a cloud CPU box — the
  workload is seconds of deterministic non-neural Python.

## Builder's bottom line

Static CAS geometry is a real second key. Order-sensitive trajectories are a real third key.
Bounded resonance with provenance-rooted activation is a real fourth layer — and the echo
result is the most important one: twenty loud copies of a lie lose to three independent
witnesses only when the provenance machinery is switched on.
