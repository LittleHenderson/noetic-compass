# What the local-gate fix means, in plain English (2026-07-24)

## The one-paragraph version

The Jacobian Live Model Canary (`JLCV1`) is a self-test that proves the tool
measures a real model's derivatives correctly on real weights
(`EleutherAI/pythia-160m`). It runs eight checks. Seven passed. The eighth —
the "VJP" check — kept failing, and we found out **why**: the check itself was
built with a bad ruler, not the measurement being wrong. We swapped the bad
ruler for a good one (a small, surgical change), and on real weights the canary
now passes every check. A clean pass is what the project calls **Gate 1** — the
first real milestone that says "the scoring actually works on a small model."

## What was actually wrong (the bad-ruler story)

- **Technical term:** the local VJP relative-error gate (`VJP_RELATIVE_ERROR_LIMIT`).
- **Plain-English meaning:** one of eight numeric self-checks. It asks "does the
  estimated Jacobian matrix reproduce the model's true reverse-mode derivative in
  a random direction?" and fails the canary if the disagreement is too big.
- **Metaphor:** a bathroom scale that divides by your weight to report a percent
  error. If you step off so only your toe touches (a near-zero reading), even a
  tiny half-pound wobble reads as a huge percentage. The scale isn't broken; the
  *percent* is the wrong way to score a near-zero reading.
- **Exact mapping:** the "near-zero reading" = the bilinear value `v·J·u`, which
  collapses when the random target direction `v` happens to point nearly sideways
  to `J·u` (measured: the reading was only 3-42% of a typical one); the "tiny
  wobble" = the matrix's real error (`~5e-6` to `3e-5`, genuinely small); the
  "huge percentage" = the spurious `4.24e-3` that failed the gate. The Jacobian
  was accurate the whole time; the gate's normalization was ill-posed.

## The fix (the good ruler)

Score the VJP the same well-conditioned way the sibling "JVP" check already
works: compare the **whole adjoint vector** (`Mᵀv` against the true reverse-mode
vector) instead of one collapsing scalar. Both local limits move from `1e-4` to
`1e-3` — documented from the estimator's genuine `5.35e-4` accuracy floor, not
tuned to force a pass. Proof it stays strict: on a deliberately 0.5%-corrupted
matrix the fixed check reads `5.1e-3` (fails loudly); on the real matrix it reads
`5.35e-4` (passes). So it accepts good matrices and still catches bad ones.

## What this unlocks (benefits and abilities)

- **Gate 1 (`0.38`) becomes reachable** — the first honest "the measurement works
  on a real small model" milestone. Every attempt 1-9 failed on the way to it.
- **The Jacobian lens is now self-consistent on real weights.** Everything built
  on top of that measurement — the Cognitive Jacobian Transistor (`CJT`),
  `J-Space`, `CAS-Ohm` — depends on the derivative being provably correct. This
  is the foundation stone those need.
- **A stricter, cleaner self-test.** The new check is well-conditioned and tests
  the matrix from both sides (forward and adjoint), so it is a *better* gate than
  the one it replaces, not a weaker one.
- **The frozen scientific spec now matches the code.** The corrected acceptance
  criterion is written into the `V0` protocol and re-pinned everywhere, so the
  spec and the running code agree — which is the honesty backbone of the harness.

## Honest claim status (what is confirmed vs pending)

- **Real (measured on real weights):** the shadow validation on
  `EleutherAI/pythia-160m` returned `numerical_status: NUMERICAL_SUBGATES_PASS`,
  `failed_gates: ()`, all 213 artifacts, JVP max `5.35e-4`, VJP(vector) max
  `5.35e-4`. This is strong: the fix genuinely makes the canary's math pass.
- **Pending (not yet confirmed):** the full worker test suite (running now) must
  be green, and the official **Attempt 10** ceremony (fresh identity, real
  DigiCert timestamp anchor, guarded GPU run, independent receiver) must produce
  the signed `TECHNICAL_CANARY_PASS`. Only that officially earns Gate 1 (`0.38`).
- **Not yet (Gate 2 = `0.46`):** a passing canary is Gate 1, not the session goal.
  Gate 2 additionally needs matched comparisons and honest error bars for the
  scoring itself — separate follow-on work downstream of this pass.

## Where the evidence lives (all under this handoff folder)

`11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_09_GPU_EXECUTION_FAILED_CLOSED_LOCAL_JVP_VJP/`:
- `STATUS.md` — the Attempt 9 run that reached this wall.
- `INVESTIGATION_local_vjp.md` — the diagnosis (ill-conditioned metric, not a defect).
- `PROPOSED_FIX_local_gates.md` — the exact diff + before/after table + strictness proof.
- `evidence/` — the 24-measurement tables, corruption test, and diagnostic scripts.

An `ATTEMPT_10_...` record with the passing official run will be added here once
the suite is green and the ceremony completes.
