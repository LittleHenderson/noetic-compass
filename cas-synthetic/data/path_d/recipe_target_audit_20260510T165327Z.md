# Recipe target audit

Strict structural validation of every recipe-shaped training row in the v1 mix corpus.

## Files scanned

| File | Rows | Recipe rows |
|---|---:|---:|
| `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` | 7395 | 433 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl` | 412 | 24 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl` | 412 | 24 |

## Aggregate

- Total recipe rows: **481**
- Strict match (all checks pass): **240 (49.9%)**
- Primary Ω preserved: 481 (100.0%)
- Side Ω preserved (where present): 481 (100.0%)
- Coefficient multiset preserved: 481 (100.0%)
- Λ side-product mentioned (where present): 481 (100.0%) [Λ-bearing rows: 122]
- All Noetic indicators present per term: 267 (55.5%)
- All domain indicators present per term: 438 (91.1%)
- All drive indicators present per term: 479 (99.6%)
- All register indicators present per term: 474 (98.5%)

## By LHS term count

| n_terms | Rows | Strict match |
|---:|---:|---:|
| 2 | 343 | 184 (53.6%) |
| 3 | 138 | 56 (40.6%) |

## Sample of worst offenders

**id**: `v1mix_cas_to_english_000161` (train)

- source: `Θ(Ω_rest_45) = 1*^2^P + 0.5*^9^O_{F6} → Ω_rest_45`
- checks: pri_Ω=True side_Ω=True coef=True sideΛ=True noetic_misses=[1] domain_misses=[1] drive_misses=[]
- target: To produce the outcome called rest_45, combine 1 of what you're drawn to in foundational thinking with 0.5 of a realization about the need for structure and order — together these inputs generate rest_45.

**id**: `v1mix_cas_to_english_000311` (train)

- source: `Θ(Ω_engagement_16) = 0.5*^4^E_{F2} + 1.5*^5^O + 0.5*^4^P → Ω_engagement_16`
- checks: pri_Ω=True side_Ω=True coef=True sideΛ=True noetic_misses=[0, 2] domain_misses=[1] drive_misses=[]
- target: To produce the outcome called engagement_16, combine 0.5 of a resonant evaluative judgment tied to wisdom and insight, add 1.5 of who you are shaped by your experiences, and add 0.5 of a resonant impression from a foundational principle.

**id**: `v1mix_cas_to_english_000432` (train)

- source: `Θ(Ω_tracking_33) = 0.7*^6^O + 0.7*^3^C_{F2}|T → Ω_tracking_33`
- checks: pri_Ω=True side_Ω=True coef=True sideΛ=True noetic_misses=[0] domain_misses=[1] drive_misses=[]
- target: To produce the outcome called tracking_33, combine a 0.7 contribution from breaking down an idea in operational thinking with a 0.7 contribution from being pushed away from wisdom and insight in an analytical way, expressed through the big-

**id**: `v1mix_cas_to_english_000659` (train)

- source: `Θ(Ω_translation_95) = 0.7*^7^O_{F3} + 0.5*^7^E → Ω_translation_95`
- checks: pri_Ω=True side_Ω=True coef=True sideΛ=True noetic_misses=[0, 1] domain_misses=[0] drive_misses=[]
- target: Take 0.7 of practiced behavioral skill tied to the need for vitality and energy, and add 0.5 of evaluative judgment expressed through practice — together these inputs produce the outcome called translation_95.

**id**: `v1mix_cas_to_english_000869` (train)

- source: `Θ(Ω_reasoning_52) = 1.5*^8^E|A + 0.7*^3^O_{F4} + 0.7*^6^P → Ω_reasoning_52`
- checks: pri_Ω=True side_Ω=True coef=True sideΛ=True noetic_misses=[0] domain_misses=[1] drive_misses=[]
- target: To produce the outcome called reasoning_52, combine 1.5 of a memory trigger in evaluative judgment expressed analytically, add 0.7 of aversion to connection and belonging expressed analytically, and add 0.7 of unpacking a foundational idea 

**id**: `v1mix_cas_to_english_001120` (train)

- source: `Θ(Ω_rest_53) = 2*^8^O|A + 0.5*^3^C|A → Ω_rest_53 + 0.1*Λ·Ω_translation_side`
- checks: pri_Ω=True side_Ω=True coef=True sideΛ=True noetic_misses=[1] domain_misses=[1] drive_misses=[]
- target: To produce the outcome called rest_53, combine 2 of something that triggered a memory in operational thinking expressed in an analytical way with 0.5 of something that rubs you the wrong way in operational thinking expressed in an analytica
