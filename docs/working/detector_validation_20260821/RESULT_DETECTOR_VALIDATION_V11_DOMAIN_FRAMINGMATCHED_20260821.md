# V11 — Framing-matched Domain-4 control: is P/C/E/O real structure or giveaway words?

**Date:** 2026-08-21
**Model:** `pythia-160m` (reserialized snapshot `d5861d32…`), attested engine (`load_open_weight_runtime` / `capture_greedy_trajectory`), CPU, **$0, no GPU**.
**Results file (co-located):** `detector_validation_v11_domain_framingmatched_results.json`, sha256 `de41171b4822c6a8…`

## 1. Why

Today's pythia-6.9b run (v10) left **Domain-4 flagged surface-lexical**: activation `1.000` but the char-ngram word-counter also `0.875`. v4/v9 had already noted the P/C/E/O framings carry lexical signatures (`ought`→P, `first/then`→O, superlatives→E, plain declaratives→C). This is the test those results pointed at.

## 2. Design (controls topic AND framing at once)

- **TRAIN** on the original **framing-rich** Domain sentences (8 topics, markers present).
- **TEST** on **4 NEW topics** (aviation, carpentry, banking, teaching) whose sentences **strip the giveaway markers**: duty shown by *action* not modals (no must/ought/should), evaluation *without* superlatives, procedure *without* first/then, plain declaratives for C.
- Compare, on the same 16-item stripped test set, activation nearest-centroid vs a char-ngram (n=2,3,4) surface baseline (vocab from train), plus a label-shuffle null.

## 3. Results (exact)

| | overall | P | C | E | O |
|---|---|---|---|---|---|
| **activation** (best L6) | **0.625** (10/16) | 1/4 | 3/4 | 2/4 | 4/4 |
| **char-ngram surface** | **0.438** (7/16) | 0/4 | 2/4 | 1/4 | 4/4 |
| label-shuffle null | 0.250 | — | — | — | — |

- chance = `0.25` (4-way). activation − surface = **+0.188** (3 items). activation beats chance: a single layer reaching ≥10/16 under the 4-way null has P≈`0.00164`; across best-of-12 layers P≈`0.0196` (≈2%) — so 10/16 is real above chance, but thinly so, and it beats surface only by 3 items.

## 4. Honest reading — PARTIAL, and the per-domain breakdown is the real finding

**Domain-4 is neither purely surface-lexical nor cleanly structural.** The overall +0.188 edge over surface is **real but thin** (3 items, n=16, best-of-12-layers selected on the test set — so read it as best-case). What actually carries it:

- **`O` procedure: 4/4 activation AND 4/4 surface.** The word-counter gets O perfectly even with "first/then" stripped — the period-separated imperative structure is itself a surface signal. **O's separation is NOT evidence of deep structure.**
- **`P` principled: collapses to 1/4** (chance) once "must/ought/should" are removed. **P was largely modal-word-carried** — strip the modals and the "principled" domain nearly disappears. This *confirms* the surface worry for P.
- **`C` 3/4 vs 2/4, `E` 2/4 vs 1/4:** thin one-item activation edges over surface. A faint real signal, not a robust one.

**Net:** the earlier "surface-lexical" flag is **refined, not overturned** — `O` is surface-carried, `P` is modal-carried and collapses, and only `C`/`E` show a faint activation-over-surface signal. There is *some* real domain structure beyond giveaway words, but it is weak and uneven, and the "perfect" Domain-4 scores of v4/v9/v10 were substantially framing-carried.

## 5. Claim-state separation

- **Real:** all numbers, on real pythia-160m weights via the attested engine.
- **Accepted:** none — research-grade.
- **Verdict:** **PARTIAL / BEATS_SURFACE_WEAK.** (The script auto-labeled `DOMAIN4_STRUCTURE_HARDENED` on an arbitrary 0.60/0.15 rule; the per-domain collapse of P and the surface-carried O make "hardened" an overclaim — corrected here to PARTIAL.)
- **Open:** larger n; a truly framing-matched C (declaratives are hard to strip); a bigger model (6.9b framing-matched control); per-domain is n=4 each.

## 6. Caveats

- Best-of-12-layers selected on the 16-item test set; the surface baseline gets no such selection. n=4 held-out topics per domain — research-grade, not significance.
- Stripping is imperfect: `O` still carries imperative structure; `C` is inherently declarative and cannot be fully "de-framed."
