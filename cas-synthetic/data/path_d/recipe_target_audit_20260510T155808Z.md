# Recipe target audit

Strict structural validation of every recipe-shaped training row in the v1 mix corpus.

## Files scanned

| File | Rows | Recipe rows |
|---|---:|---:|
| `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` | 7395 | 581 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl` | 412 | 32 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl` | 412 | 32 |

## Aggregate

- Total recipe rows: **645**
- Strict match (all checks pass): **0 (0.0%)**
- Primary Ω preserved: 0 (0.0%)
- Side Ω preserved (where present): 479 (74.3%)
- Coefficient multiset preserved: 482 (74.7%)
- Λ side-product mentioned (where present): 611 (94.7%) [Λ-bearing rows: 166]
- All Noetic indicators present per term: 256 (39.7%)
- All domain indicators present per term: 438 (67.9%)
- All drive indicators present per term: 573 (88.8%)
- All register indicators present per term: 578 (89.6%)

## By LHS term count

| n_terms | Rows | Strict match |
|---:|---:|---:|
| 1 | 70 | 0 (0.0%) |
| 2 | 413 | 0 (0.0%) |
| 3 | 162 | 0 (0.0%) |

## Sample of worst offenders

**id**: `v1mix_invalid_to_explanation_001884` (train)

- source: `Θ(Ω_reasoning_95) = 2*^0^K|T + 1.5*^4^E_{F7}|E + 1.5*^7^C → Ω_reasoning_95 + 0.15*Λ·Ω_remembering_side`
- checks: pri_Ω=False side_Ω=False coef=False sideΛ=False noetic_misses=[0, 1, 2] domain_misses=[1, 2] drive_misses=[1]
- target: The expression breaks down at the point where a recognized subject area is required. Instead of naming a valid domain, the notation uses an unrecognized identifier — essentially a label the system doesn't know how to categorize. Because tha

**id**: `v1mix_invalid_to_explanation_001895` (train)

- source: `Θ(Ω_engagement_00) = ^0^P + 0.5*^6^P|f + 1.5*^5^E_{F4} → Ω_engagement_00 + 0.1*Λ·Ω_verification_side`
- checks: pri_Ω=False side_Ω=False coef=False sideΛ=False noetic_misses=[0, 1] domain_misses=[0, 1] drive_misses=[1]
- target: One part of the recipe lists a required input but gives it no quantity — the compiler needs a number there to know how much of that input to expect. Without a figure attached, the instruction is incomplete and cannot be processed.

**id**: `v1mix_invalid_to_explanation_001900` (train)

- source: `Θ(Ω_engagement_03) = 2*^7^E + 0.5*^6^O_{F4}|M + 0.7*^0^O → Ω_engagement_03 + 0.1*Λ·Ω_reasoning_side`
- checks: pri_Ω=False side_Ω=False coef=False sideΛ=False noetic_misses=[0, 1, 2] domain_misses=[0, 1, 2] drive_misses=[1]
- target: The expression names a category label that isn't recognized as a valid destination for the kind of information being tracked. Specifically, the slot that should identify one of four permitted categories — Thinking, Affective, a third option

**id**: `v1mix_invalid_to_explanation_001906` (train)

- source: `Θ(Ω_rest_06) = ^2^P_{F1} + 2*^2^E_{F2} + 1*^7^E_{F3}|T → Ω_rest_06 + 0.15*Λ·Ω_self_correction_side`
- checks: pri_Ω=False side_Ω=False coef=False sideΛ=False noetic_misses=[0, 1] domain_misses=[0, 1] drive_misses=[0, 1]
- target: The recipe expects a plain number before one of its required ingredients, but instead finds a special abstract operator where that number should be. Because the system cannot treat that operator as a quantity, it cannot calculate how much o

**id**: `v1mix_invalid_to_explanation_002060` (train)

- source: `Θ(Ω_production_35) = 0.5+^2^O_{F5} + 1*^8^P + 1.5*^6^P_{F7}|f → Ω_production_35 + 0.15*Λ·Ω_decision_side`
- checks: pri_Ω=False side_Ω=False coef=False sideΛ=False noetic_misses=[0, 1] domain_misses=[0, 1] drive_misses=[1]
- target: There is a missing multiplication sign between a numeric coefficient and the item it modifies. Right after the first plus sign, the expression jumps straight from a number into an exponent marker without the required connector between them.

**id**: `v1mix_invalid_to_explanation_002074` (train)

- source: `Θ(Ω_engagement_46) = ^5^C_{F7} + 0.5*^6^C_{F1}|f → Ω_engagement_46 + 0.05*Λ·Ω_tracking_side`
- checks: pri_Ω=False side_Ω=False coef=False sideΛ=False noetic_misses=[0] domain_misses=[0] drive_misses=[0]
- target: The recipe expects a plain number to appear before one of its ingredients, but instead it finds a special mental-state marker that doesn't belong there. Numbers are required in that position to tell the system how much of something to use; 
