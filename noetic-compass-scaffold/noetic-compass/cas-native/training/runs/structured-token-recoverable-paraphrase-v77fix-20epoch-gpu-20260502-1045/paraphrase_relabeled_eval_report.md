# Structured-Token Paraphrase-Invariance Report

Canonical samples: 1000
Paraphrase samples: 3000
Comparable samples: 3000

| Metric | Value |
|---|---:|
| Paraphrase all-heads exact | 0.469 |
| Prediction consistency vs canonical | 0.484 |
| Canonical-exact retention | 0.495 |

## Per-Head Prediction Consistency

| Head | Rate |
|---|---:|
| noetic | 0.715 |
| domain | 0.774 |
| registers | 0.791 |
| drive | 0.794 |
| expression_family | 0.960 |
| meta_relations | 0.970 |
| transition_kind | 0.982 |
| register_mode | 0.984 |
| has_meta_logic | 0.990 |
| has_omega | 0.995 |
| authority | 1.000 |
| turn_type | 1.000 |

## Bucket Summary

| Bucket | n | Exact Rate | Consistency |
|---|---:|---:|---:|
| meta_logic | 306 | 0.170 | 0.219 |
| v74_baseline | 600 | 0.187 | 0.188 |
| v75_register | 792 | 0.245 | 0.239 |
| v76_production | 324 | 0.756 | 0.772 |
| v77_omega | 801 | 0.873 | 0.875 |
| v77_rule_four | 177 | 0.599 | 0.751 |
