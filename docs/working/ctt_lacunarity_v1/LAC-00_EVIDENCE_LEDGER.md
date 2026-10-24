# LAC-00 — Evidence ledger, Phase 0 (CAS-LAC-001)

Status: **Phase 0 deliverable.** Built from repository inspection, artifact hashes, and an independent verification
pass. Every entry carries a status: `OBSERVED`, `INFERRED`, `HYPOTHESIS`, `PROPOSAL`. Where an earlier project report
is contradicted by an artifact, the contradiction is recorded here and the old report is patched, never deleted.

## 1. Provenance

| Item | Value |
|---|---|
| Repository | `C:\Users\wakil\OneDrive\Desktop\tksCAS`, branch `helm/creativity-rpa-valve-v1` |
| HEAD at audit | `50a31052` |
| Generation run artifacts | `C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws` |
| Checkpoints | `cs_aws\results\out\A4-s1|s2|s3` |
| Payload/data | `C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1` |
| AWS spend, both training runs | ~2.40 USD (historical; not a new allowance) |

## 2. Commits verified (`OBSERVED`)

- `50a31052` exists; adds `N1_HELDOUT_RESULT_20261024.md` (77 lines) and **one blank line** to `CHANGELOG.md`.
- `87d9a4d7` exists; adds `N1_PROBE_RESULT_20261024.md` (62 lines) and one blank line to `CHANGELOG.md`.
- Both commit messages are detailed; the changelog hunks are empty. Correction to an earlier claim: the commits *do*
  describe their work — the changelog entries are what is missing.

## 3. Generation result — verified, with a second deviation found (`OBSERVED`)

Three seeds, not two. Per-seed composite difference (final − early): `+0.121088`, `+0.106669`, `+0.122451`. The
final checkpoint wins guard, fact-exactness and read-back in every seed. Decision: **early-stopping hypothesis
FAILED, 3 of 3.**

Two deviations from the preregistration:

1. **Single listener** (already recorded): the frozen three-vote ear was replaced by one fixed listener because two
   pre-training copies returned empty readings.
2. **Denominators** (newly found by verification): the preregistration says each rate is measured over **all 1,517
   items**, with non-fact replies counting as round-trip passes. The implementation computed fact-exact and read-back
   over the **800 fact rows** only. Under the prereg-literal denominators the composites are:

| Seed | Early (literal) | Final (literal) | Difference |
|---|---|---|---|
| A4-s1 | 0.197192 | 0.267512 | +0.070320 |
| A4-s2 | 0.216385 | 0.277804 | +0.061419 |
| A4-s3 | 0.216260 | 0.289607 | +0.073347 |

The decision is unchanged (final still wins by more than the 0.02 bar in 3 of 3), but the reported composite values
are **not** the preregistered metric.

## 4. N1 held-out result — the published verdict is reversed by the preregistered definition (`OBSERVED`)

The report used **token occurrences** where the preregistration defines **row counts**. Corrected counts:

| Cell | Training **rows** (preregistered exposure) | Training occurrences (what the report used) | Held-out rows | Held-out occurrences |
|---|---:|---:|---:|---:|
| `^0` | 537 | 661 | 114 | 114 |
| `^1` | 438 | 595 | 150 | 162 |
| `^2` | 368 | 495 | 132 | 144 |
| `^3` | 353 | 472 | 66 | 72 |
| `^4` | 366 | 498 | 132 | 156 |
| `^5` | 353 | 450 | 132 | 132 |
| `^6` | 370 | 534 | 120 | 120 |
| `^7` | 403 | 540 | 204 | 234 |
| `^8` | 346 | 460 | 108 | 126 |
| `^9` | 383 | 471 | 114 | 120 |

Re-running the two predeclared checks with the **row** split (median 369; high = `^0`,`^1`,`^6`,`^7`,`^9`; low =
`^2`,`^3`,`^4`,`^5`,`^8`) gives:

| Seed | High-exposure Δ | Low-exposure Δ | Low > High at both points? |
|---|---:|---:|---|
| A4-s1 | +0.003762 | +0.007546 | yes (0.547469 vs 0.453849 early; 0.555015 vs 0.457611 final) |
| A4-s2 | +0.100202 | +0.126395 | yes (0.451725 vs 0.423699; 0.578120 vs 0.523901) |
| A4-s3 | +0.069732 | +0.065494 | yes (0.437801 vs 0.424030; 0.503295 vs 0.493762) |

**Corrected verdict: H-overfit 1 of 3 — FAILS the 2-of-3 bar. H-neglect 3 of 3 — SUPPORTED.** The published report
says the opposite. The substantive reading is therefore *not* "overfitting, not neglect"; it is "low-exposure cells
carry more error at both checkpoints, in all three seeds". The overall rise in held-out error (3 of 3 seeds) is
unchanged.

Other corrections to that report:

- The set is **588 rows from 98 sources × 6** (clean + 5 noise), not 99 × 6 = 594. One DEV key yielded no pair.
- There are **500 distinct (text, target) pairs and 88 duplicate rows** (multiplicities 2×37, 3×21, 4×3). "Their
  surface forms differ" is false for those 88.
- The preregistered unit was `cas_val.jsonl`; the result ran on `notation_dev99.jsonl`. That departure was undeclared.
- `notion_dev99` avoids `cas_keep` cleanly (0 overlap) but **17 distinct texts overlap `cas_val`** — the 17
  Noetic-bearing `cas_val` rows. Not training contamination (neither partition trained the model), but not disjoint
  from the preregistered unit either.

## 5. Artifacts verified (`OBSERVED`)

- 18 checkpoint files exist; all 18 SHA-256 match `checkpoints.jsonl`.
- Each `final.pt` matches `final_sha256` in its `WEIGHTS_MANIFEST.json` (`ee5163d6…`, `32f0b700…`, `bd7bebe8…`).
- Three extra `resume.pt` files (115,178,797 bytes each) are on disk, unhashed and outside every manifest.
- All six generation files have 1,517 rows and 800 fact rows; the six reported composites reproduce from their
  components to ≤5.2e-7.
- The six reported Λ values reproduce exactly with population variance over the ten cell means.

## 6. Code inventory corrections (`OBSERVED`)

An earlier inventory draft declared these absent. They exist under `noetic-compass-scaffold\noetic-compass\`:

- `cas-engine\src\scoring\lacunarity.rs` — the four coverage metrics (`1 − unique/10`, `1 − active/4`, `1 − active/7`,
  `1 − mechanisms/4`) and the Var/Mean² composite.
- `api\pipeline\lacunarity.py` — Python mirror.
- `cas-native\model\lacunarity_gate.py` — `Var/Mean²` over a **40-slot** vector (`num_slots=40`), wired into
  `cas_native_model.py`.
- `cas-native\model\lacunarity_head.py` — 40-element gap map.

So the book's 40-state measure **is** implemented, contrary to the first draft.

## 7. Mathematical correction (`OBSERVED`)

The design note's bridge is wrong. For one box covering the whole vector there is exactly one window, so `Var = 0`
and `L = 1` always. The identity is **`Λ = L(b=1) − 1`**, not `L(b=n) − 1`. The corrected statement is patched into
the design notes.

## 8. What remains open

| Question | Status |
|---|---|
| Does any measure predict held-out failure beyond exposure and loss? | `HYPOTHESIS` — N1's overfit result failed; neglect signal survives but needs a second source |
| Does any measure select a better repair? | `PROPOSAL` — no intervention has been run |
| Does the recipe or RPM family have a working measure? | `PROPOSAL` — neither exists in code; definitions in LAC-02 |
| Is the 40-slot gate a diagnostic or a learned correction? | `HYPOTHESIS` — must be read before any claim |
| Does the generation decision survive the prereg-literal denominator? | `OBSERVED` — yes, 3 of 3, see §3 |

## 9. Rank 1 result — the corrected N1 verdict is stable (2026-10-24, free re-run)

Re-ran the two predeclared checks three ways: all 588 rows, the 500 deduplicated rows, and source-level (mean within
each of the 98 sources, then across sources). The verdict is identical in all three:

| Variant | H-overfit (high-exposure worsens more) | H-neglect (low-exposure worse at both points) |
|---|---|---|
| All 588 rows | 1 of 3 — FAILS | 3 of 3 — SUPPORTED |
| 500 distinct rows | 1 of 3 — FAILS | 3 of 3 — SUPPORTED |
| 98 sources | 1 of 3 — FAILS | 3 of 3 — SUPPORTED |

Deduplication changes the per-cell numbers only in the third decimal (A4-s1 high +0.003762 → +0.003507, low
+0.007546 → +0.005065). The 88 duplicate rows were not driving the result. Source-level averaging is identical to
row-level because each source contributes six rows.

**Conclusion: the published "overfitting, not neglect" verdict is wrong and stays corrected. The surviving signal is
neglect — cells with fewer training rows carry higher held-out error at both checkpoints, in all three seeds.** The
rise in held-out error (3 of 3 seeds) is unchanged. This is a descriptive association, not a causal claim: the
low-exposure cells may simply be harder.

Artifacts: `cs_aws\notation_dev_scores\<seed>_<checkpoint>.rows.json` (per-row error and address, 18 files).

## 10. Rank 4 result — the exposure–error signal replicates; the overfitting signal does not (2026-10-24)

A second source was built from 100 new CAS compositions with six English phrasings each (600 rows, all Noetic-bearing,
**0** overlap with training and with the first held-out set). It was scored on the same 18 checkpoints.

| Source | Rows | H-overfit | H-neglect | Overall rise |
|---|---|---|---|---|
| First (`notation_dev99`) | 588 | 1 of 3 — FAILS | 3 of 3 — SUPPORTED | 3 of 3 |
| Second (`notation_new100`) | 600 | 2 of 3 — MEETS | 3 of 3 — SUPPORTED | 3 of 3 |

Per-seed second-source totals: A4-s1 1.471022 → 1.641994 (+0.170972), A4-s2 1.685291 → 2.131292 (+0.446001),
A4-s3 1.651655 → 2.006977 (+0.355323).

`Λ` over cell means: first source 0.009832–0.018011 → 0.016672–0.019795; second source 0.043385–0.066019 →
0.038498–0.070758. It moves in different directions and is small in both.

**Reading:** the low-exposure/high-error association replicates across two independent source sets (3 of 3 seeds
each). The high-exposure overfitting pattern does not (1 of 3 then 2 of 3, straddling the bar). The lacunarity scalar
adds nothing beyond the cell-level split. Cost: **0 USD**; no LLM was used.
