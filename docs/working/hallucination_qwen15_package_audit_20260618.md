# Qwen-1.5B Hallucination Package Audit - 2026-06-18

## Scope

Audited the claimed Qwen-1.5B hallucination trajectory package and fixes:

- `d4efd8ae` - `fix(hall-probe): correct balanced-accuracy bug in Qwen-1.5B probe scripts + add 1.5B audit package`
- `1326b6a7` - `docs(hall-probe): finalize Qwen-1.5B package with 1000-shuffle significance`
- `docs/working/HALLUCINATION_AUDIT_PACKAGE_QWEN1.5B.md`
- `pt_q15.py`
- `pt_q15_delta.py`

## Verdict

The package is materially stronger than the earlier broken-script claim. The balanced-accuracy bug is fixed in the inspected scripts, and the Markdown package now frames the result more honestly as a second-model replication lead rather than a size-scaling or causal claim.

However, this is not yet an audit-sealed hidden-state hallucination detector. Treat it as `OPEN` / `NOT LICENSED` for production claims until the missing reproducibility and control artifacts are committed.

## Findings

### P1 - The 1000-shuffle selection-aware p-value is not reproducible from committed code

The package reports selection-aware 1000-shuffle significance with p at the 1/1001 floor. The inspected commit does not include a runnable script or machine-readable result artifact that reproduces that exact test.

Observed:

- `pt_q15_delta.py` fixes and prints the per-layer delta balanced accuracy scan, but it does not run the 1000-shuffle selection-aware max-over-layer permutation.
- `pt_q15.py` fixes a permutation balanced-accuracy bug, but it targets the older 0.5B capture paths and uses 100 permutations, not the Qwen-1.5B 1000-shuffle selection-aware test.
- `1326b6a7` only changes the Markdown package.

Required fix:

- Commit the exact Qwen-1.5B selection-aware permutation runner.
- Commit a JSON/CSV report with seed, layer list, fold policy, n permutations, real max BA, per-permutation max scores or summary, count beating real, exact p-value, and artifact hashes.

### P1 - The result is not on the CAS Harness beta-candidate branch

Both commits are currently contained by `origin/codex/cascompass-legal-live-source`, not `origin/codex/cas-harness-public-beta-candidate`. The active CAS Harness claim auditor and launch gate work has been tracked on `codex/cas-harness-public-beta-candidate`.

Required fix:

- If this result is meant to affect the CAS Harness launch/auditor state, cherry-pick or merge only the audited artifacts onto the beta-candidate branch after the reproducibility package is complete.

### P2 - The p-value display is mathematically confusing

The package displays `p = 0.0010` while marking it as passing a `< 0.001` threshold. The exact floor value for zero successes in 1000 shuffles is `1 / 1001 = 0.000999000999...`, which does pass `< 0.001`. Rounded to four decimals, it displays as `0.0010`, which looks equal to the threshold.

Required fix:

- Report exact p as `0.000999` in the pass table, or explicitly state that the rounded display is `0.0010` but the exact value is below `0.001`.

### P2 - Text controls are still incomplete for a licensed internal hallucination claim

The package says the prompt text is identical and the text/majority baseline is 0.500. That is useful, but it does not close the full surface-control problem for a W0/W1 or trajectory hallucination detector.

Still open:

- Generated-prefix controls.
- Token-identity controls.
- Shuffled-time controls.
- A committed layer-0 / embedding control for this exact Qwen-1.5B trajectory package.
- A pre-registered layer or a fully committed selection-aware report.
- Causal intervention.

The package itself flags several of these as open, which is good, but the headline should not imply that text cannot compete in the broader sense. It only shows that the prompt text baseline cannot compete on this specific stale-majority subset.

### P3 - Branch wording should be tightened from "verified" to "replication lead"

Acceptable wording:

> Qwen-1.5B shows a second-model trajectory signal on the stale-majority subset: best-layer BA 0.7795 at L27, with the package claiming exact selection-aware p at the 1/1001 floor. This is a replication lead, not a size-scaling claim, not causal proof, and not yet a licensed hidden-state hallucination detector.

Do not say yet:

> CAS Harness has proven hidden-state hallucination detection.

Do not say yet:

> This validates hallucination detection across models.

## Positive Audit Notes

- The balanced-accuracy formula in the inspected scripts now uses mean per-class recall instead of the old identity bug.
- The package includes the full 8-layer scan rather than only the winning layer.
- The package explicitly says this is not a size-scaling claim.
- The package includes the matched-layer caveat: L14 on Qwen-1.5B is 0.7324 versus 0.7853 on Qwen-0.5B.
- The package correctly keeps the result observational, not causal.

## Claim State

- Hidden-state hallucination detection: `OPEN` / `NOT LICENSED`
- Hallucination prevention: `OPEN` / `NOT LICENSED`
- Causal proof: `OPEN` / `NOT LICENSED`
- Product-safe value: research evidence for a possible trajectory signal, useful for prioritizing the next controlled run

## Immediate Next Gate

Create a reproducible Qwen-1.5B audit bundle:

1. Exact 1000-shuffle selection-aware runner.
2. Machine-readable significance report.
3. Exact p-value formatting fix.
4. Generated-prefix, token-identity, shuffled-time, and layer-0 controls for the same package.
5. Active-goal auditor row that keeps hallucination hidden-state detection `OPEN` / `NOT LICENSED` until all controls pass.
