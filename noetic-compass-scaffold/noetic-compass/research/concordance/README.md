# Compass <-> Atlas Concordance Harness

Research-grade harness that runs the same scenario through Noetic Compass
(`/assess` / `/wrap`) and Atlas LIVE (live-trace worker), then produces a
side-by-side agreement / mismatch report.

**Status — M1 scaffold.** Comparison logic and report schema are real and
tested. Live endpoint wiring is NOT in this iteration.

## What this is

Two paths, one scenario, one report:

- **Compass path.** Output-grading: prompt -> wrap pipeline ->
  NCCS composite (0-100) + per-operator scores + certification band +
  inversion flags. Source: `api/routes/assess.py`, `api/routes/wrap.py`.
- **Atlas LIVE path.** Model-internal trace: prompt -> Pythia-160M (v0.1)
  with hooks -> SSE stream of per-token activations, Mode 7 attention
  attribution, per-class neuron cover sets. Source: `live-trace-worker/`.

The harness projects both onto a common comparison surface (10 operator
scores, 4 domain marginals, 1 composite, 1 DCI, inversion-flag set,
register tags), then runs a five-layer agreement check. Mismatches are
classified under a taxonomy that distinguishes *calibration*
disagreements (e.g., band-only) from *semantic* disagreements (e.g.,
operator-direction flip).

Investor framing: "same input, two independent paths, here's how often
they agree." Neither path alone is sufficient — Compass can be talked
into anything by a clever grader; Atlas can over-fit on neuron
coincidences. The intersection is what we trust.

## What this is NOT

- Not production code. Lives in `research/`, not `cas-engine/` or `api/`.
- Not on the API surface. No FastAPI routes added.
- Not statistically rigorous. M1 ships fixtures, not a calibrated study.
- Not live. `call_compass` and `call_atlas` raise `NotImplementedError`
  with the M2 wiring plan inline as comments.

## Layout

```
research/concordance/
  __init__.py
  harness.py             # Scenario, CompassResult, AtlasResult,
                         # ConcordanceReport, SetReport.
                         # compare() and run_set() are real.
                         # call_compass/call_atlas are documented stubs.
  README.md              # this file
  tests/
    __init__.py
    test_compare.py      # Fixture coverage of every taxonomy bucket.
```

Design doc: `docs/working/compass_atlas_concordance_harness_2026_05_24.md`.

## Running the tests

From the repo root (`noetic-compass/`):

```bash
pytest research/concordance/tests/ -v
```

All tests are pure logic over fixture `CompassResult` / `AtlasResult`
pairs. No network, no model load, no GPU. Should complete in
sub-second on any machine.

## How to use the harness today (M1)

Build `CompassResult` and `AtlasResult` objects by hand (or from
recorded JSON fixtures) and feed them to `run_set()`:

```python
from research.concordance import (
    CompassResult, AtlasResult, Scenario, run_set,
)

scenarios = [Scenario(id="s1", prompt="...")]
compass_results = [CompassResult(scenario_id="s1", ...)]
atlas_results = [AtlasResult(scenario_id="s1", ...)]

report = run_set(
    scenarios,
    compass_results=compass_results,
    atlas_results=atlas_results,
)

print(report.summary)
for r in report.reports:
    print(r.scenario_id, r.verdict, r.agreement.operator_correlation)
```

`run_set()` requires both pre-computed result lists at M1. Calling it
with `compass_results=None, atlas_results=None` raises
`NotImplementedError` — that's the M2 hook.

## What needs to happen for M2 (live wiring)

1. **Implement `call_compass(scenario)`** to POST to staging Compass
   `/wrap` with `provider="mock"` and parse the `WrapResponse`. Full
   plan in `harness.py::call_compass` docstring.
2. **Implement `call_atlas(scenario)`** as a two-step session-then-SSE
   consumption against `noetic-compass-api /api/atlas/live/session`.
   Auth via invite-code header during alpha; swaps to Bearer license
   token later. Full plan in `harness.py::call_atlas` docstring.
3. **Persist raw responses** under
   `research/concordance/runs/<set_id>/compass/` and `/atlas/` before
   the comparator runs. This is the reproducibility receipt for the
   hash-based traceability in `ConcordanceReport`.
4. **Wire `run_set()` fallback** to call `call_compass` / `call_atlas`
   when results aren't pre-computed.
5. **Add a CLI** (`python -m research.concordance.run <fixture_path>`)
   that loads a scenario set, drives both endpoints, writes the
   `SetReport` to JSON.

## How to read the output

A `SetReport` has two main pieces:

**Summary.** Headline numbers across the batch:
- `mean_operator_correlation` — Pearson r averaged over scenarios.
  Above 0.7 is strong, 0.4-0.7 is moderate, below 0.4 is weak.
- `mean_dci_delta` — average gap between Compass DCI and Atlas DCI.
  Under 10 is agreement.
- `band_agreement_rate` — fraction of scenarios where both paths land
  in the same certification band.
- `mean_inversion_jaccard` — agreement on which 7-axis inversion flags
  fired.
- `worst_band_gap` — the most embarrassing band disagreement in the
  run (largest composite delta among band-mismatches). Useful for
  investor demos and triage.
- `taxonomy_breakdown` — how many scenarios fell into each mismatch
  bucket.

**Reports.** One `ConcordanceReport` per scenario, hashed for integrity:
- `verdict` — primary taxonomy bucket (see below).
- `agreement` — five-layer metrics.
- `taxonomy.secondary` — other buckets that also tripped.
- `taxonomy.detail` — bucket-specific evidence (which involution pair
  flipped, what the composite delta was, etc.).
- `scenario_hash`, `compass_response_hash`, `atlas_response_hash` —
  SHA-256 receipts. Same three inputs always produce the same report.

## Mismatch taxonomy — short version

(Long version in the design doc.)

| Bucket                       | Severity | Means                                                          |
|------------------------------|----------|----------------------------------------------------------------|
| `no_mismatch`                | -        | All five agreement layers clean.                               |
| `band_only`                  | Low      | Composite within 5 pts but lands in different bands.           |
| `operator_direction_flip`    | High     | The two paths pick opposite members of an involution pair.     |
| `domain_precedence`          | High     | Different dominant domain. P-vs-O heavier than E-vs-O.         |
| `register`                   | Low (M1) | Phenomenological Register specifications disagree.             |
| `residual`                   | Mixed    | None of the above but still not clean. Dump to human review.   |

Priority resolves to the most semantically severe bucket as `primary`;
the rest tag as `secondary`.

## Dependencies in flight

- **Agent C's `scenarios/atlas_alpha_set_v0.json`.** Until that lands,
  `load_scenarios()` falls back to an inline 3-scenario stub fixture
  (ethics / AI safety / healthcare). Once the file is in tree, it's
  picked up automatically.
- **Live-trace worker M1 (shipped).** Schema mirrored from
  `live-trace-worker/app/schemas/events.py`.
- **API `/wrap` and `/assess` (shipped).** Response shape from
  `api/models.py`.

## Math notes

- **Open simplex normalization (CLAUDE.md Correction 4).** Both
  Compass-derived and Atlas-derived 40-state vectors get Laplace-smoothed
  to strict positivity before any comparison. Zeros would break
  Fisher-Rao distance.
- **Pearson correlation, not absolute match.** The two systems are
  calibrated differently and probably always will be. We care about
  consistent operator *ranking*, not numerical identity.
- **Register canonicalization per CAS v7.7 Clarification 10.** Single
  chars (`"T"`) canonicalize to 1-element frozensets; lists canonicalize
  to frozensets (so `["T", "A"]` matches `["A", "T"]`); multi-char
  strings are compared by string identity (named emergent results).

## Anti-drift

- **No live HTTP from this scaffold.** If you find yourself adding
  `requests.post` or `httpx.AsyncClient` to `harness.py`, stop. That's
  M2 work and belongs in a separate `live.py` module that imports the
  stubs.
- **Hashing input shape matters.** `compass_response_hash` covers the
  full `CompassResult.raw` dict when present. If a future change drops
  raw to save memory, the hash falls back to the dataclass `asdict()` —
  still stable, but no longer captures the upstream JSON byte-for-byte.
  Keep `raw` populated through M2 so audit trails reproduce.
