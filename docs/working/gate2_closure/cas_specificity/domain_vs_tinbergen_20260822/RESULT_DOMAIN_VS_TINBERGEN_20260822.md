# RESULT — Domain axis vs matched Tinbergen taxonomy — INCONCLUSIVE BY DESIGN (2026-08-22)

**Pre-registered:** `PREREG_DOMAIN_VS_TINBERGEN_20260822.md` (sha256 `14ace6dda991cee4cdb4c1d165161d856dcce4e3a4557093897fe8ba87076d74`), written BEFORE capture; criteria frozen, no criterion edited after the run.

## What ran

- Fixture: the v4 domain fixture, AST-extracted verbatim from `detector_validation_v4_domain.py` — 8 topics × 4 domains = 32 sentences (sha256 `0fb11c26a17203edfa8d3bb3a8017e80ea1707c99103612151ca0e7454ce0d7b`).
- Model: `pythia-160m-reserialized`, revision `d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97`, attested engine, CPU, $0. 32 captures, one pass, `max_new_tokens=1`, `seed=0` (captures sha256 `f5c93ab4cf2ad08e…`, full in results JSON).
- Two arms on the SAME vectors: CAS domains (P/C/E/O) vs Tinbergen's four questions under two bijections frozen before capture (primary: abstractness-aligned; sensitivity: positional).
- Classifier: nearest-centroid, 4-way, train 6 topics / test 2 held-out topics (8 items, chance 0.25), every layer, shuffled-label null × 100 seeds, random-4-dim-subspace control per layer.

## Numbers (exact)

| arm | layer-mean | best layer | best acc | shuffle (best-layer mean) | random-subspace (best layer) |
|---|---|---|---|---|---|
| CAS_DOMAIN_PCEO | **0.875** | 2 | **1.0** | 0.25875 | 0.25 |
| TINBERGEN primary (aligned) | **0.875** | 2 | **1.0** | 0.25875 | 0.25 |
| TINBERGEN sensitivity (positional) | **0.875** | 2 | **1.0** | 0.25875 | 0.25 |

Per-layer real accuracies are **identical across all three arms at all 12 layers** (0.75, 0.75, 1.0, 0.875, 1.0, 0.875, 1.0, 1.0, 0.875, 1.0, 1.0, 0.375). McNemar at best CAS layer: **p = 1.0**, discordant pairs **0/8**. Δ layer-mean = **0.0**.

Pre-registered criteria: **C1 ✓** (CAS sanity), **C2 ✓** (TIN sanity), **C3 ✗**, **C4 ✗**.

## Why the tie is structural, not measured — the equivariance proof

Nearest-centroid accuracy is **invariant under any bijective class relabeling**. For a fixed bijection φ, the centroid of label ℓ equals the centroid of the domain φ⁻¹(ℓ), i.e. the same four centroids under renaming; nearest-centroid assignment then renames each prediction identically, so item-wise correctness — and therefore accuracy at every layer, every shuffle, and every subspace — is identical across arms. **Any matched taxonomy assigned by a fixed bijection ties CAS by construction.** The observed exact ties (Δ = 0.0, p = 1.0, zero discordant pairs) are the theorem, not a finding.

## Disposition

**`INCONCLUSIVE BY DESIGN`** (project legend): the measurement cannot discriminate the hypothesis as constructed — a negative result about the fixture/instrument, not about the hypothesis. The prereg's literal decision-rule output was `DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS` (C3/C4 false); that wording is **NOT citable**, because the instrument could not have returned anything else.

**Standing positive content:** the CAS arm reproduces v4's cross-topic domain decodability on the attested engine (layer-mean 0.875, best 1.0 at layer 2, shuffle 0.259, random-subspace 0.25) — a clean replication, nothing more.

## What this does and does not say

- Does NOT say CAS domains are or are not more recoverable than a generic abstractness taxonomy. The run was structurally incapable of saying either.
- Does say: the activation-probe relabeling design is the wrong instrument for frontier #1's lever, and the frontier text's own wording ("run arm E against the domain axis") under-specified the instrument.
- Frontier #1 remains **OPEN**. What would actually settle the lever: the **Condition-3 blind-rater instrument** (independent semantic annotation of the fixture into Tinbergen levels that cross-cut the domain partition) or a dual-labeled fixture bank — not a relabeling probe.

## Artifacts

- `PREREG_DOMAIN_VS_TINBERGEN_20260822.md` — sha256 `14ace6dda991cee4cdb4c1d165161d856dcce4e3a4557093897fe8ba87076d74`
- `run_domain_vs_tinbergen.py` — sha256 `75cc73d9301ad23dbd058be2cecec37ef9a9cbb85794cc367c652d626cabf043`
- `fixture_domain_v4.json` — sha256 `0fb11c26a17203edfa8d3bb3a8017e80ea1707c99103612151ca0e7454ce0d7b`
- `domain_vs_tinbergen_results.json` — sha256 `d6b0787db74c059453f873a226836e4256250915e87bc2f82c68c48e9a5a83ef`
- `extract_fixture_hash.py`
