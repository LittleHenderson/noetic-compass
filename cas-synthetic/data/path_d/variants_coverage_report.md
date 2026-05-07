# Path D Wave 2C — Variant Coverage Report

- Total source seeds processed: **5802**
- Total accepted variants: **16110**
- Total rejected attempts: **0**
- Validation rejection rate: **0.00%**
- Avg variants per seed: **2.78**

## Per variant_type

| variant_type | count |
|---|---|
| drive_intensity | 6583 |
| register | 4521 |
| operation | 744 |
| order | 4262 |

## Per source grammar category

| source_grammar_category | count |
|---|---|
| binary_composition | 1060 |
| cross_register_omega | 2632 |
| diagram_export | 856 |
| inversion | 380 |
| let_binding | 680 |
| meta_logic_relation | 2216 |
| recipe | 2118 |
| rpm_chain | 2304 |
| state_literal | 3864 |

## Cross-table: source category × variant_type

| source\type | drive_intensity | register | operation | order | total |
|---|---|---|---|---|---|
| binary_composition | 0 | 120 | 720 | 220 | 1060 |
| cross_register_omega | 0 | 1760 | 0 | 872 | 2632 |
| diagram_export | 436 | 0 | 0 | 420 | 856 |
| inversion | 156 | 48 | 24 | 152 | 380 |
| let_binding | 378 | 302 | 0 | 0 | 680 |
| meta_logic_relation | 128 | 158 | 0 | 1930 | 2216 |
| recipe | 929 | 521 | 0 | 668 | 2118 |
| rpm_chain | 2304 | 0 | 0 | 0 | 2304 |
| state_literal | 2252 | 1612 | 0 | 0 | 3864 |

## Oversample stats — thin lanes (rpm_chain, inversion)

| lane | seed count | variant count | ratio | target | met? |
|---|---|---|---|---|---|
| rpm_chain | 384 | 2304 | 6.00 | ≥3 | PASS |
| inversion (all axes) | 78 | 380 | 4.87 | ≥5 | PARTIAL |
| inversion (productive shapes only) | 60 | 380 | 6.33 | ≥5 | PASS |

_Note: 18 axis-W inversion seeds (shape `^N^Da -> ^N^Db`) have no variable fiber/marginal that preserves the base — no drives, no registers, mandatory domain-descent direction. Per the Wave 2C kickoff memo ("if you can't vary an axis without changing the base, skip the variant"), these seeds yield 0 variants by design. The productive-shape ratio is the meaningful oversample metric._

## Per axis token distribution

### Noetics used (count of variants containing each Noetic)

| Noetic | count |
|---|---|
| ^0 | 4887 |
| ^1 | 2854 |
| ^2 | 3050 |
| ^3 | 3071 |
| ^4 | 2790 |
| ^5 | 2923 |
| ^6 | 2895 |
| ^7 | 2875 |
| ^8 | 2826 |
| ^9 | 2921 |

### Domains used

| Domain | count |
|---|---|
| C | 6137 |
| E | 6121 |
| O | 3846 |
| P | 6197 |

### Drives used

| Drive | count |
|---|---|
| F1 | 1297 |
| F2 | 1221 |
| F3 | 1232 |
| F4 | 1291 |
| F5 | 1303 |
| F6 | 1324 |
| F7 | 1260 |

### Registers used

| Register | count |
|---|---|
| A | 2375 |
| E | 2322 |
| T | 2443 |
| f | 2520 |

### Operators used

| Operator | count |
|---|---|
| `=` | 8760 |
| `Ω` | 4878 |
| `→` | 4464 |
| `×` | 2952 |
| `+` | 2734 |
| `Θ` | 2118 |
| `*` | 2118 |
| `·` | 526 |
| `∘` | 372 |
| `∖` | 95 |
| `∩` | 85 |
| `∪` | 68 |
| `⊂` | 27 |
| `⊆` | 17 |

## Special-flag counts

- uses_named_omega : 4878
- uses_theta_recipe: 2118
- uses_meta_logic  : 2726
- uses_fractal     : 0

## Rejection reasons (top 10)

(no rejections)
