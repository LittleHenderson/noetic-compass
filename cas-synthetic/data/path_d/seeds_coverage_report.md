# Path D Wave 1B — Seed Coverage Report

- Total accepted seeds: **5802**
- Total rejected attempts: **0**
- Validation rejection rate: **0.00%**

## Per task slot

| task_slot | count |
|---|---|
| cas_to_english | 968 |
| english_to_cas | 986 |
| expression_to_trace | 920 |
| invalid_to_corrected | 926 |
| invalid_to_explanation | 999 |
| operation_to_outcome | 1003 |

## Per grammar category

| grammar_category | count |
|---|---|
| binary_composition | 746 |
| cross_register_omega | 658 |
| diagram_export | 480 |
| fractal_sequence | 576 |
| inversion | 78 |
| let_binding | 480 |
| meta_logic_relation | 768 |
| recipe | 576 |
| rpm_chain | 384 |
| state_literal | 1056 |

## 7-category coverage check (≥500 threshold per memory rule)

| category | count | met ≥500 |
|---|---|---|
| 1. state_literal | 1056 | PASS |
| 2. drive subscripts (drives_used > 0) | 2021 | PASS |
| 3. registers (registers_used > 0) | 1968 | PASS |
| 4. operators (binary_composition + arrows + ∘) | 746 | PASS |
| 5. recipes (uses_theta_recipe) | 576 | PASS |
| 6. meta-logic (uses_meta_logic) | 893 | PASS |
| 7. fractals (uses_fractal) | 576 | PASS |

## Per axis token distribution

### Noetics used (count of seeds containing each Noetic)

| Noetic | count |
|---|---|
| ^0 | 1269 |
| ^1 | 967 |
| ^2 | 976 |
| ^3 | 980 |
| ^4 | 919 |
| ^5 | 964 |
| ^6 | 935 |
| ^7 | 956 |
| ^8 | 914 |
| ^9 | 934 |

### Domains used

| Domain | count |
|---|---|
| C | 1631 |
| E | 1686 |
| O | 1389 |
| P | 1642 |

### Drives used

| Drive | count |
|---|---|
| F1 | 326 |
| F2 | 309 |
| F3 | 313 |
| F4 | 311 |
| F5 | 291 |
| F6 | 320 |
| F7 | 313 |

### Registers used

| Register | count |
|---|---|
| A | 797 |
| E | 725 |
| T | 745 |
| f | 800 |

### Operators used

| Operator | count |
|---|---|
| `=` | 2601 |
| `→` | 1639 |
| `Ω` | 1250 |
| `+` | 943 |
| `×` | 854 |
| `Θ` | 699 |
| `*` | 699 |
| `·` | 142 |
| `∘` | 126 |
| `∩` | 28 |
| `∖` | 26 |
| `∪` | 23 |
| `∈` | 18 |
| `⊂` | 13 |
| `⊆` | 11 |

## Special-flag counts

- uses_named_omega : 1250
- uses_theta_recipe: 576
- uses_meta_logic  : 893
- uses_fractal     : 576

## Rejection reasons (top 10)

(no rejections)
