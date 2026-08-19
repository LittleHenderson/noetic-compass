# RESULT — Component Atlas v0, full run (2026-08-18)

**Verdict: `NULL_ATLAS_V0` — 0 of 4 evaluable labels stuck. The CAS-PCBA component labels did
NOT earn their keep on pythia-1b.** Honest, preregistered, and reported as-is.
Run: `EleutherAI/pythia-1b` rev `f73d7dcc…`, A40, 161.9s. Report: `atlas_v0_FULL_report.json`.

## Headline numbers
| Test | Status | Why |
|---|---|---|
| `DR_F5` (drive rail) | **FAIL** | targeted drop `0.0339` vs best matched-random control `0.0313` — no better than random. The **cross-rail cover did MORE** (`0.0675`). `sign_test_p = 0.891`. |
| `DR_F2` (contrast rail) | **FAIL** | targeted drop **negative** (`-0.0268`). |
| `AMP_F5` (amplifier) | **FAIL** | beat cross-direction (`0.112` vs `0.039`) but failed the remaining gates. |
| `RS_F5` (brake — the increase-sign anchor) | **VACUOUS** | baseline hedging `0.00` (frac `0.00 < 0.25`). The brake never demonstrably fires, so removing it predicts nothing. Never evaluable — same as smoke. |
| `CONN` (rail → amplifier) | **FAIL** | selective-starvation signature absent. |
`kill_statement_triggered: None`. Aggregate is DESCRIPTIVE-ONLY (tests are correlated by design).

## The load-bearing caveat: BOTH harness-sanity checks also failed
Sanity checks exist to tell "the labels are wrong" apart from "the instrument isn't measuring."
- `CHECK_SANITY` **SANITY_FAIL — but informatively**: ablating the induction heads dropped the
  gate score `12.77 → 9.21` nats (drop `3.56`) against a best control drop of `0.175` — a **~20×
  margin over controls**. It failed only the aggressive preregistered bar (drop ≥ 50% of baseline
  = `6.38`). So the apparatus DOES produce large, selective causal effects; the threshold was steep.
- `MEM_SANITY` **SANITY_FAIL, uninformative**: `n_judgment_items = 6`, baseline copy accuracy `0.50`
  (barely over its own precondition), and ablation made copying *better* (`0.667`, drop `-0.167`).
  At n=6 this is noise, not a finding.

## Honest reading
- **This is a WEAK null, not a refutation.** Real: the ablation machinery works and can produce
  strongly selective effects (CHECK, 20× controls). But the sharpest CAS-PCBA test (`RS`, the
  increase-sign brake — the one generic damage cannot fake) was **never evaluable**, one sanity
  check is uninformative at n=6, and judge banks are small (12 prompts, 6 sanity items).
- **What DID fail cleanly:** `DR_F5`. A cover chosen to carry F5 was no more consequential than
  activation-matched random coordinates, and the *other* drive's cover mattered more. On this
  model, at this scale, with these banks, there is no evidence for a typed "drive rail."
- **What this does NOT say:** nothing about CAS-specificity (GREY by design), and nothing about
  larger models. pythia-1b may simply lack the behavioral separation these tests need — baseline
  presence and hedging rates were marginal throughout.

## Next levers (in order of value)
1. **Fix RS evaluability** — it is the sign-anchor; without it the battery has no test that generic
   degradation cannot mimic. Needs prompts that make hedging actually fire (longer continuations,
   or genuinely conflict-laden frames), preregistered as rev 0.3 BEFORE re-running.
2. **Scale up** — pythia-2.8b is already in the pod cache; 20B is where the η→ε bridge was strongest
   (`+1.412`). Behavioral separation should improve with scale.
3. **Power** — 12 judge prompts makes the sign test need near-unanimity; raise n before re-judging.
