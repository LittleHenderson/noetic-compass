# LAC-01 — Existing measurement inventory (CAS-LAC-001, Phase 1)

Status: **Phase 1 deliverable, corrected after independent verification.** Each entry is tagged IMPLEMENTED, TESTED,
EVALUATED, or PROPOSED. "Implemented" means code exists; it does not mean validated. File paths are exact.

## 1. The five CAS lacunarity dimensions (implemented twice)

Implemented in Rust and mirrored in Python:

- `noetic-compass-scaffold\noetic-compass\cas-engine\src\scoring\lacunarity.rs` (12,231 bytes)
- `noetic-compass-scaffold\noetic-compass\api\pipeline\lacunarity.py` (6,417 bytes) — its docstring says it "Mirrors
  cas-engine/src/scoring/lacunarity.rs so it works without rebuilding the Rust PyO3 wheel".

| Measure | Formula (as coded) | Input | Range | Status |
|---|---|---|---|---|
| State lacunarity | `Var(p)/Mean(p)^2`, population variance | operator scores (10) or 40-slot vector | `[0, ∞)` | IMPLEMENTED, TESTED |
| Fractal lacunarity | `1 − unique/10` | sequence of operators | `[0, 1]` | IMPLEMENTED |
| Domain lacunarity | `1 − active/4`, active if `score > 0.2` | 4 domain scores | `[0, 0.75]` | IMPLEMENTED |
| Drive lacunarity | `1 − active/7`, active if `score > 0.15` | 7 drive scores | `[0, 6/7]` | IMPLEMENTED |
| RPM resolution lacunarity | `1 − mechanisms_used/4` | resolution details list | `[0, 1]` | IMPLEMENTED |

Classification thresholds in code: `< 0.5` Uniform, `0.5–1.5` Moderate, `1.5–3.0` Concentrated, `> 3.0` Extreme.
Two thresholds (`0.2` and `0.15`) are hard-coded and undocumented in the book passage; they are a silent choice.

**Duplication risk:** the Python mirror must be kept equal to the Rust implementation. No test in the packet proves
they agree.

## 2. The 40-slot gate (implemented, used in training-time inference)

`noetic-compass-scaffold\noetic-compass\cas-native\model\lacunarity_gate.py` (3,056 bytes):

- Computes `Var/Mean^2` on a **40-slot** activation vector (`num_slots=40`).
- When the value exceeds `threshold` (default `2.0`), applies a **learned** correction (`nn.Linear(40,40)` plus a
  gate) that boosts neglected slots and damps over-concentrated ones, then re-normalises to the open simplex.
- Status: IMPLEMENTED. It is a **controller**, not a measurement: the correction is learned, so the gate's behaviour
  is not a validated diagnostic. No evaluation of its effect is in the packet.

`lacunarity_head.py` (2,419 bytes): a metacognitive head predicting the five scores, a 40-element gap probability
map, and four domain confidences. Status: IMPLEMENTED (a learned predictor), not evaluated.

## 3. The numerical gliding-box measure (this program, 2026-10)

- `docs\working\ctt_lacunarity_v1\lacunarity.py`: `L(b) = 1 + Var(N_b)/E[N_b]^2` over a non-negative 1-D field, plus a
  bounded schedule. Status: IMPLEMENTED, TESTED (14 tests, `test_lacunarity.py`).
- EVALUATED: `E1_TRAJECTORY_RESULT_20261023.md` (field concentrates as training proceeds, 3 boxes, one run);
  `C60_LACUNARITY_TEST_20261023.md` (real CTT-v2 run); `N1_PROBE_RESULT_20261024.md` (fit only).

## 4. The Noetic per-cell measure (this program)

- `lacunarity_e1\cas_score.py`: attributes teacher-forced error to the ten Noetic cells present in a gold target.
- `notation_dev99.jsonl` (588 rows, 98 sources × 6) and `notation_heldout.jsonl` (2,034 training rows).
- Status: IMPLEMENTED, EVALUATED (held-out result, with a corrected verdict in LAC-00 §4).

## 5. Recipe family (no lacunarity implementation)

Specified in `docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 and implemented as yield arithmetic:

- `Y_T = min_i(x_i/a_i)` (limiting reagent), production efficiency `η = Y_A/Y_T`.
- Code exists in the v7.6 specification and in `cas_only_reasoner` modules; a **limiting reagent is not a
  lacunarity measure**.
- **LACUNARITY STATUS: PROPOSED, not implemented.** No file in the repository computes a recipe lacunarity.

## 6. RPM family

- Two RPM engines exist in the repo (`cas_only_reasoner`, `api`), but neither exposes a lacunarity over dependency
  chains. The existing "RPM resolution lacunarity" is only the coverage ratio `1 − mechanisms/4` (LAC-01 §1).
- **LACUNARITY STATUS: PROPOSED, not implemented** for depth, branching, blocker persistence, repair cost, or chain
  fragility.

## 7. What the inventory changes about earlier claims

- An earlier draft said `lacunarity.rs`, `api/pipeline/lacunarity.py` and `cas-native` heads were absent. They exist.
  The 40-state measure is implemented, not merely specified.
- The book's "five dimensions" and the code agree in formula. The two activity thresholds are additions in code.
- The gliding-box identity: `Λ = L(b=1) − 1`; a single box over the whole vector always yields `L = 1`.

## 8. Gap list

1. No test proves the Rust and Python implementations agree.
2. No evaluation of `LacunarityGate`'s effect on quality; its correction is learned and unvalidated.
3. Recipe and RPM lacunarities do not exist as code (see LAC-02 for definitions).
4. The 40-slot versus 10-Noetic choice is inconsistent across the family and undocumented.
5. No measure has been tested for incremental value over exposure and loss except the N1 exposure split (LAC-00 §4).
