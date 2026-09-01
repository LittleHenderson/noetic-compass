# PATH B — Operation-Graph Task Specification v0.3 (CJT-T2) — AS BUILT

**Status:** the owner-approved v0.2 (+ v0.3 ruling amendments) IMPLEMENTED and
its CPU integrity stage EXECUTED. Development-only, non-claim-bearing.
Supersedes v0.2 for execution; v0.1/v0.2 and the 19-finding review record are
preserved.

## Owner v0.3 ruling — how each item landed
- **D1 (dose-response):** arms are **S0 / S3 / S-ALT50 / S6** with the frozen
  50% deterministic corruption map (`pathb_core.alt50_class`, hash-keyed per
  (passage, clause), balanced across the other 3 classes, identical across
  seeds). `CAS-specific` remains prohibited in all PATH B reporting.
- **D2:** K = 6 clauses (frozen `MAX_IDEAS = 6` honored).
- **D3:** QB-ORD retained under **CHK-8** (counterfactual order swap, 100%)
  + **PRB-POS** (linear clause-position probe from frozen layer-18 states
  must reach ≥0.90 val accuracy at P0, else the family auto-drops).
- **D4:** target ACCEPTED counts 12,000 / 1,500 / 1,500 — achieved with **0
  exclusions** (constructive generation); the
  `INSUFFICIENT_PATH_B_CLEAN_COVERAGE` law is implemented in the generator.
- **D5:** protected split (family D) generated IN MEMORY with a DISPOSABLE
  TEST SALT (sha recorded), digested (`5aca…` initial → current manifest),
  never written; the OWNER salt derivation is registered later by
  `SHA256(salt)` commitment only. The v1 protected split is untouched.
- **S-PERM:** implementation-conformance ONLY —
  `test_sperm_equivariance.py` runs the paired parameter+optimizer-state
  permutation over 5 AdamW steps: **`SPERM_EQUIVARIANCE_CONFIRMED`**, max
  deviation 7.15e-07 (tolerance 1e-5).
- **CHK-M:** implemented (`pathb_mutations.py`): 11 registered mutants + the
  clean reference under the 7-point validity law (in-process patching only;
  clean re-verified after all mutants). **`CHK_M_PASS`** — every mutant
  caught semantically by its target gate; no crash-only successes.
  Notably, CHK-M caught three defects in the gate battery itself before it
  was trusted (fixed pre-freeze): the adversary read profiles from the trace
  instead of the model's actual channel (`idea_labels`); fixed statistical
  margins were noise-fragile at small n; two mutants acted post-render.
- **Tier C:** `PROOF_OF_NON_EQUIVARIANCE_REQUIRED` over the complete profile
  pathway stands as the precondition for any future specificity test; not
  exercised here.

## Registered corrections (v0.2 → v0.3, applied openly)
- **C-2:** the "≥3 class-pairs" clause of CHK-2 was unsatisfiable with the
  approved family set (INT answers are parts; one ^6 family). Corrected:
  ≥30% of distinct IDEA answers must appear under BOTH {^2} and {^8}
  final-hop class-sets (achieved: 100%). Parts excluded; recorded.
- **C-4b:** CHK-4's bound is the UNIFORM-RANDOM same-class strategy
  (uniform final-class clause, then uniform object within it) + a
  registered n-aware margin `max(0.05, 2·sd)`; the same margin law governs
  CHK-7. Fixed absolute bounds were either unsatisfiable (^6's object
  granularity) or noise-fragile.
- **CHK-10 added:** candidate-order-law conformance (entity-set equality +
  first-mention-order fraction ≤10%) — CHK-M showed order leaks were
  otherwise invisible.
- Two generator leaks found by the battery and fixed before freezing:
  QB-INT answers sat in ^6 slot p1 (part lists now shuffled); QB-ORD
  clause extremity correlated with the answer (m2's clauses now occupy
  discourse slots 0 and 5).

## CPU integrity stage — results (all deterministic, $0)
- Dataset: train 12,000 (fam A,B) / val 1,500 (fam C) / protected 1,500
  (fam D, in-memory), **0 exclusions**; round-trip parser (family DERIVED
  from surface; graph+order+answer equality) **100%**.
- **`PATHB_GATES_PASS`** — every gate green per family × split. Key val
  numbers: CHK-4 matcher/bound: REL .440/.466, COMP .515/.550, INT
  .224/.272, ORD **.000**/.300. CHK-7 trained-adversary profile increments:
  REL 0.000, COMP 0.000, INT −0.019, ORD +0.019 (margin law ≈0.05 at full
  n). B-suite: B1-GRAPH 1.000; **B-MEMBER 0.875** (the symbolic
  membership+classes ceiling — COMP's ^8 orientation is the text-residual,
  0.5); H-INT-repeated 0.34 (registered, post-fix); candidate-uniform ≈0.11.
- **`CHK_M_PASS`**, **`SPERM_EQUIVARIANCE_CONFIRMED`** (above).

## The P0 stage (GPU; the owner return contract)
`run_pathb_pilot.py`: frozen P1.3 MixtureHead (router + clause-local answer
experts; λ init 1.0; NO model change, NO third binder); S0-only layer
selection over 6/12/18/24; binding smoke gates re-frozen for v2 data
(128-memorization ≥95%, gold-vs-shuffled routing ≥10pp via the solver's
answer-bearing edge, binding-shuffle ≥5pp); profile-gradient, S3-swap, and
S6-exact-invariance gates; PRB-POS; per-family transfer floor-guard
(S0 ≥ uniform+0.05 on ≥2 of 4 families). Failure of memorization or
gold-routing ⇒ `BINDING_REPAIR_FAILED`. One self-terminating T4 under the
standing $30/2h law. **Return: the exact failed gate, or the P0 numbers.**
P1 (3 seeds × 1000 updates, total interpretation law incl.
`SHORTCUT_BOUNDED_SIGNAL` measured against the B-KEY increment and B-MEMBER
reference) runs only after the owner sees P0.
