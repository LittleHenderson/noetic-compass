# Compass ↔ Atlas Concordance Harness — Design

**Status.** M1 scaffold. No live endpoint wiring in this iteration. Comparison
logic and report schema land first; live `call_compass` and `call_atlas` come
in a follow-up.

**Author.** Agent (this PR), 2026-05-24.

**Code lives at.** `research/concordance/`. NOT under `cas-engine/` or `api/` —
this is a research surface, not part of the product API.

---

## 1. What the harness does — in plain English

Two completely independent paths in Noetic Compass produce a verdict about a
scenario:

- **Path A — `/assess`.** The classic Noetic Compass scorer. Takes a prompt,
  runs the 8-stage wrap pipeline, returns NCCS (the 0–100 composite), a
  certification band, per-operator scores, domain coherence, and inversion
  flags. No model internals — it grades the *output* of an LLM.
- **Path B — Atlas LIVE.** The live-trace worker (Pythia-160M at v0.1,
  OLMo/Qwen at v0.2). Runs the same prompt through a real model and streams
  back per-token neuron activations, Mode 7 attention attribution, and the
  per-class neuron cover sets. Provenance is the model itself, not a grader.

These two paths *should* converge on the same scenario. If they don't, that's
a finding — either Compass's grader is misreading the output, or Atlas's
probes are picking up something the grader missed, or the scenario is
genuinely ambiguous. The harness runs the same input through both and
produces a side-by-side agreement/mismatch report.

**Why this matters for investors.** "Same input, two independent paths, here
is how often they agree" is a much stronger proof surface than either path
alone. Compass alone could be talked into anything by a clever grader.
Atlas alone could over-fit on neuron coincidences. The intersection is what
we trust.

**What this is not.** A live system. M1 ships fixtures and a real `compare()`
function. Wiring to staging Compass and staging Atlas is M2.

---

## 2. The five agreement layers

Concordance is not a single number. It's a stack of comparisons at different
layers. The harness reports all five.

### 2.1 Operator scores — numerical correlation

- **Compass side.** 10 numbers, one per Noetic operator (CO-0…CO-9), each in
  `[0, 100]`. From `NccsResponse.operator_profile` decomposed via the wrap
  pipeline.
- **Atlas side.** 10 numbers derived from per-class neuron cover activation
  density across the trace. Atlas does not natively emit 0–100 scores; we
  derive a [0, 1] activation density per Noetic from `top_activated_neurons`
  weighted by `per_class_neuron_covers`, then rescale to `[0, 100]`.
- **Agreement metric.** Pearson correlation `r` across the 10-vector pair,
  plus per-operator absolute deltas. `r ≥ 0.7` counts as "strong agreement,"
  `0.4 ≤ r < 0.7` as "moderate," `r < 0.4` as "weak."
- **Why correlation, not absolute match.** The two systems are calibrated
  differently and probably always will be. We care that they *rank* operators
  consistently, not that they hit the same number.

### 2.2 Domain coherence (DCI) — single-number comparison

- **Compass side.** `domain_coherence` from `NccsResponse`. Single 0–100
  number. Defined as `(weakest domain avg) / (strongest domain avg) × 100`.
- **Atlas side.** Same formula applied to the 4-domain marginals derived from
  the activation-density-per-operator (Section 2.1) projected onto the
  P/C/E/O domains via the 40-state mapping.
- **Agreement metric.** Absolute delta `|DCI_compass − DCI_atlas|`. Under
  10 points = agreement. 10–25 = soft mismatch. > 25 = hard mismatch.

### 2.3 NCCS band — exact-match required

- **Compass side.** `certification` field. One of `{Platinum, Gold, Silver,
  Bronze, Fail}`.
- **Atlas side.** The same cutoffs (90/75/60/40) applied to an Atlas-derived
  composite that mirrors the NCCS weighting (25/20/20/10/15/10) using
  Atlas-derived operator/domain/drive proxies. Last 10% (social engineering)
  is held flat for the M1 scaffold — Atlas doesn't have a manipulation
  signal yet.
- **Agreement metric.** Exact band match required for "agree." Anything else
  is a band mismatch. The taxonomy (Section 3) distinguishes band-mismatch
  severities.

### 2.4 Inversion flags — set agreement / Jaccard

- **Compass side.** Set of inversion axes flagged. Subset of `{N, W, F, E, S,
  A, P}`.
- **Atlas side.** Inversion-axis projections from the activation trace. N
  (operator-involution imbalance) is computed by comparing activation on
  `^2/^3`, `^5/^6`, `^8/^9` involution pairs. W (domain-precedence violation)
  is computed by checking whether O-domain neurons activate before
  P-domain neurons on the temporal axis (Mode 7 attribution gives
  ordering).
- **Agreement metric.** Jaccard similarity on the two flag sets.
  `|A ∩ B| / |A ∪ B|`. Empty-set agreement (both clean) reports as `1.0`.

### 2.5 Evidence ref overlap

- **Compass side.** Wrap pipeline emits `provenance` containing scoring
  rationale. We treat each rationale citation as an evidence ref tagged
  with the operator and domain it underwrites.
- **Atlas side.** `top_activated_neurons` + `per_class_neuron_covers` gives
  us, per Noetic class, the set of neuron indices that fired hardest. Each
  neuron is an evidence ref tagged the same way.
- **Agreement metric.** This one is asymmetric — Atlas evidence refs are
  neuron-level, Compass evidence refs are token/clause-level. We compute
  per-Noetic-class "did both surface ANY evidence" boolean agreement, and a
  total count delta. This is the weakest agreement layer at M1; in M3 we
  expect to bridge it via the Mode 7 token→neuron attribution.

---

## 3. Mismatch taxonomy

Not all disagreements are equal. The harness classifies each scenario's
disagreement (if any) under exactly one primary taxonomy bucket plus
optional secondary tags.

### 3.1 Band-only mismatch

The composite NCCS values are within 5 points of each other but they
straddle a certification cutoff (90/75/60/40). Example: Compass scores 76
(Gold), Atlas scores 74 (Silver). The systems agree on the underlying
quality but a cutoff fell between them.

- **Severity.** Low. This is a calibration issue, not a finding.
- **Trigger.** `|composite_compass − composite_atlas| < 5` AND
  `band_compass != band_atlas`.

### 3.2 Operator-direction mismatch (involution-pair flip)

The two systems point at the same operator family but disagree on the sign
of the involution pair. Example: Compass says ^2 (Positive — attracted
toward), Atlas says ^3 (Negative — repelled from). Or ^5/^6, or ^8/^9.

- **Severity.** High. This is a semantic disagreement, not a calibration
  issue. It says one system is reading the scenario as approach and the
  other as avoidance.
- **Trigger.** For each involution pair `(a, b) ∈ {(2,3), (5,6), (8,9)}`:
  if `argmax(score_compass[a], score_compass[b]) !=
  argmax(score_atlas[a], score_atlas[b])` AND the dominant operator's score
  is ≥ 60 in both systems, flag as involution-pair flip on that pair.
- **CLAUDE.md cross-reference.** Per the v7.7 anti-drift annotations, ^3 is
  *visceral aversion*, not analytical critique. An involution flip on the
  ^2/^3 axis is precisely the failure mode the colloquialism test catches.

### 3.3 Domain-precedence mismatch

The two systems disagree on which domain is dominant. P/C disagreement is
heavier than O/E disagreement because the domain total order is
`P ≻ C ≻ E ≻ O`.

- **Severity.** Scaled by the precedence gap. P-vs-O is the heaviest;
  E-vs-O is the lightest.
- **Trigger.** `argmax(domain_averages_compass) !=
  argmax(domain_averages_atlas)`. Severity score =
  `|precedence_rank(d_compass) − precedence_rank(d_atlas)|` where rank
  maps `P→4, C→3, E→2, O→1`.

### 3.4 Register mismatch

One system specifies a Phenomenological Register (T/A/f/E) on its operator
scores; the other is register-neutral. Or both specify but disagree.

- **Severity.** Low at M1 (Compass register support is in rollout, Atlas
  register-detection is M3+). We log the mismatch but don't weight it
  heavily until both systems consistently emit register data.
- **Trigger.** `score_registers_compass != score_registers_atlas` after
  normalizing for `None` ↔ empty list ↔ register-neutral.

### 3.5 No mismatch

All four prior buckets clean AND the operator correlation `r ≥ 0.7` AND
DCI delta < 10 AND Jaccard on inversion flags ≥ 0.7. Otherwise flag as
"residual mismatch" and dump the full diff into the report for human
review.

---

## 4. Pre-processing

The two systems live on different mathematical surfaces. Pre-processing
projects them onto a common ground before comparison.

### 4.1 Open-simplex normalization (CLAUDE.md Correction 4)

The state space is `S°_I = Δ°₃₉ = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }`.
**Strict positivity is required.** Both Compass-derived and Atlas-derived
40-state vectors must be normalized to this open simplex before any
comparison.

- **Atlas side.** Activation densities can be exactly zero on classes that
  did not fire. We add Laplace smoothing with `α = 1e-3` to ensure strict
  positivity, then renormalize.
- **Compass side.** Operator scores are 0–100. Domain averages from
  `AssessRequest.domain_averages` already satisfy the open-simplex
  constraint (see `validate_simplex` in `api/models.py`). For the 40-state
  projection we use a Dirichlet prior `α = 1` over the 40 cells weighted by
  operator × domain marginals.
- **Why this matters.** Fisher-Rao distance `d(p,q) = 2·arccos(Σ√(pk·qk))`
  diverges on the boundary. Zeros break it. Smoothing first is
  mathematically required, not stylistic.

### 4.2 Score-range alignment

Compass operator scores are `[0, 100]`. Atlas operator densities are
`[0, 1]`. We rescale Atlas to `[0, 100]` by linear scaling. We do NOT
attempt to recalibrate the distribution — recalibration would let us
manufacture agreement and is explicitly out of scope for the harness.

### 4.3 Register normalization

Per CAS v7.7 Clarification 10:

- `None` ≡ register-neutral.
- `"T"` (single char in `{T, A, f, E}`) ≡ v7.5 single register.
- `list[str]` ≡ v7.7 register-set `|⟨…⟩`.
- Multi-char `str` ≡ v7.7 named emergent result (e.g. `"Ω"`).

Compare via canonical form: any single-character register normalizes to a
1-element frozenset; a list normalizes to a frozenset; named-emergent
results are compared by string identity.

---

## 5. Post-processing — aggregating across a batch

`run_set()` returns a `SetReport` with:

- **Headline numbers.** Mean operator correlation across all scenarios. Mean
  DCI delta. Band-agreement rate (fraction of scenarios where bands match
  exactly). Mean inversion Jaccard.
- **Worst-case band gap.** Single scenario with the largest composite
  delta where bands disagree. This is the "investor demo cherry pick" —
  the most embarrassing disagreement in the run.
- **Axis-by-axis breakdown.** Of the scenarios that mismatched, what
  fraction tripped each taxonomy bucket. Tells us where the systems
  diverge most.
- **Per-scenario raw report.** Full `ConcordanceReport` for every scenario
  in the batch, hashed with the input scenario id + Compass raw response
  SHA-256 + Atlas raw response SHA-256. The hash is the integrity
  receipt — "object traceability is load-bearing" applies.

---

## 6. Output schema (canonical)

```jsonc
{
  "schema_version": "1.0",
  "set_id": "<uuid>",
  "generated_at": "<iso8601>",
  "scenarios_run": 3,
  "summary": {
    "mean_operator_correlation": 0.82,
    "mean_dci_delta": 6.4,
    "band_agreement_rate": 0.67,
    "mean_inversion_jaccard": 0.71,
    "worst_band_gap": {
      "scenario_id": "atlas-alpha-02",
      "composite_compass": 76,
      "composite_atlas": 58,
      "band_compass": "Gold",
      "band_atlas": "Bronze",
      "delta": 18
    },
    "taxonomy_breakdown": {
      "band_only": 0,
      "operator_direction_flip": 1,
      "domain_precedence": 0,
      "register": 0,
      "residual": 0,
      "no_mismatch": 2
    }
  },
  "reports": [
    {
      "scenario_id": "atlas-alpha-01",
      "scenario_hash": "<sha256>",
      "compass_response_hash": "<sha256>",
      "atlas_response_hash": "<sha256>",
      "verdict": "no_mismatch",
      "agreement": {
        "operator_correlation": 0.91,
        "dci_delta": 3.2,
        "band_match": true,
        "inversion_jaccard": 1.0,
        "evidence_overlap_count": 8
      },
      "taxonomy": {
        "primary": "no_mismatch",
        "secondary": []
      }
    }
  ]
}
```

Every report row is reproducible from `(scenario_hash, compass_response_hash,
atlas_response_hash)` — re-running the comparator against the same three
inputs yields the same row.

---

## 7. M2 wiring plan (forward-looking — NOT in this PR)

- `call_compass()` posts to staging Compass `/wrap` with `provider=mock` (so
  no LLM cost) and reads back the full `WrapResponse`. Auth via JWT against
  staging. Timeout 5 seconds, single retry on 5xx.
- `call_atlas()` posts to staging Atlas-via-noetic-compass-api
  `POST /api/atlas/live/session`, gets back a `stream_token`, opens the SSE
  stream at `GET /api/atlas/live/session/{id}/events?token=<stream_token>`,
  collects all `LiveTraceEvent` payloads until `complete`, builds the
  per-class activation density. Timeout 60 seconds.
- Both calls write raw responses to `research/concordance/runs/<set_id>/`
  before `compare()` runs. That way reports stay reproducible even if
  staging endpoints change between runs.

---

## 8. Dependencies

- **Agent C — `scenarios/atlas_alpha_set_v0.json`.** Their PR is in flight.
  Until it lands, the harness ships against an inline 3-scenario stub
  fixture (see `harness.py`). Once Agent C's file is in tree, the harness
  picks it up automatically — fixture path is configurable.
- **Live-trace worker (M1 shipped).** Schema lives at
  `live-trace-worker/app/schemas/events.py`. We mirror the relevant types
  in our `AtlasResult` dataclass.
- **API `/wrap` and `/assess` (shipped).** Response shape at
  `api/models.py::NccsResponse` and `api/models.py::WrapResponse`.

---

## 9. Out of scope for M1

- No HTTP. No staging calls. No SSE parsing in production code paths
  (we have a documented stub).
- No statistical significance testing. Mean correlation across 3 scenarios
  is not statistical evidence — it's a smoke test.
- No persistence to a database. Reports go to JSON on disk.
- No dashboard surface. The dashboard wires up against the JSON schema in
  Section 6 once the M2 harness produces real data.
- No social-engineering axis at the Atlas side. Held flat in the composite
  until we have a manipulation-detection probe.
