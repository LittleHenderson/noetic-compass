# PRE-REGISTRATION — `CONFIRMATORY-PILOT-R1-R6`

**Committed before any confirmatory generation.** This pilot alone can authorize `TKS_672_V3`.
**Policy under test:** the selected E-arm architecture (`RESULT_PILOT_E_VS_S2.md`) — motive +
unlabeled criterion + opaque RF-family + universal target-blind instruction + private regex.

---

## 1. Arms

| Arm | Author model | Family | Size | Purpose |
|---|---|---|---|---|
| `A0` | `models/gemini-2.5-flash-lite` | Gemini | 16 cells × 4 plans × 5 = `320` | primary, fully replayable reproduction of the E result |
| `R6A` | `models/gemini-2.5-flash` | Gemini | 16 × 2 × 5 = `160` | same-family, stronger-author replication |
| `R6B` | `claude-haiku-4-5-20251001` | **Anthropic** | 16 × 2 × 5 = `160` | true cross-family author check |

Same 16 frozen cells as the pilots. Same prompt bytes for every arm (only the model differs).
`160` detects a large mechanism difference (`~0.40` vs `~0.01`); it is **not** sized for per-cell
estimates — that requires the full `320` design, disclosed.

**Held-out families now generate items:** `A0` plans `0–2` draw from TRAIN families, plan `3`
from a HELD-OUT family; `R6` arms use one train + one held-out plan. Held-out items exist **only**
to test `R4`/`R5`; they never enter v3 training folds.

## 2. Per-call logging — the replayability repair, mandatory

Every API call stores: exact rendered prompt (utf-8) · prompt SHA-256 · raw response text ·
response SHA-256 · model + revision · request parameters · cell + opaque RF-ID · held-out flag ·
parser source hash · normalized candidates · full retry history. Written as JSONL before any
scoring.

## 3. Dual leakage detectors

- **Primary (frozen historical):** `\b(spiritual(ly)?|mental(ly)?|emotional(ly)?|physical(ly)?)\b`
  — unchanged for comparability with v1/v2/S2/E. **Selection uses this detector only.**
- **Secondary (morphology-aware):** NFKC-normalized, casefolded,
  `\b(spiritual(ly)?|spirituality|physical(ly)?|physicality|mental(ly)?|mentality|emotional(ly)?)\b`
  — catches `spirituality`/`physicality`/`mentality` without counting `fundamental`,
  `experimental`, `environmental`. Reported alongside; a large primary/secondary gap is itself a
  finding.

## 4. Frozen criteria — numeric this time (the `R1` unscorable defect is not repeated)

| # | Criterion | Bar |
|---|---|---|
| `R1` | `A0` overall leakage (primary detector) | `<= 0.05` overall AND no cell `> 0.15` |
| `R1B` | criterion-copy recall mean | `<= 0.10` |
| `R2` | June surface gate on the selected `A0` corpus | all axes `<= 0.60` (frozen June code, hash-bound) |
| `R3` | blind judge (`gemini-2.5-flash`) on `A0` train-family items | `R3-JOINT >= 0.70`; `R3-WORLD`, `R3-DRIVE` reported |
| `R4` | held-out family transfer | held-out `R3-JOINT >= 0.55` AND `(train − heldout) <= 0.20` |
| `R5` | lexical resistance | judge held-out World accuracy exceeds char 3–5-gram AND word TF-IDF (trained on train-family items, tested held-out) by `>= 0.10` |
| `R6` | cross-author mechanism | leak matrices (World × drive × word, own/non-own) per arm; interpretation per the owner's frozen table in `PREREG_WORLD_REALIZATION_GRAMMAR_V1_PILOT.md` |

**All of `R1`–`R5` must pass, and `R6` must not land in an author-model-limitation row, for v3
authorization.** Then the v3 budget is simulated from the **worst observed World × drive cell**.

## 5. Unchanged

Selection = first-3-passing on the primary regex, frozen order, whole-family accept/reject.
Semantic retries prohibited. Judge-directed repair prohibited. Pilot items quarantined from v3.
June gate code hash `6fef2610cb92809c`, threshold `0.60`, asserted at startup.

## Status

`LOCKED / QUARANTINED / NOTHING LICENSED / Gate 2 OPEN at 0.38`
