# Structured-Token Paraphrase-Invariance Report

Canonical samples: 1000
Paraphrase samples: 3000
Comparable samples: 3000

| Metric | Value |
|---|---:|
| Paraphrase all-heads exact | 0.372 |
| Prediction consistency vs canonical | 0.444 |
| Canonical-exact retention | 0.424 |

## Per-Head Prediction Consistency

| Head | Rate |
|---|---:|
| noetic | 0.657 |
| drive | 0.777 |
| registers | 0.785 |
| domain | 0.849 |
| expression_family | 0.937 |
| transition_kind | 0.958 |
| register_mode | 0.969 |
| meta_relations | 0.973 |
| has_meta_logic | 0.989 |
| has_omega | 0.995 |
| authority | 1.000 |
| turn_type | 1.000 |

## Bucket Summary

| Bucket | n | Exact Rate | Consistency |
|---|---:|---:|---:|
| meta_logic | 306 | 0.255 | 0.317 |
| v74_baseline | 600 | 0.083 | 0.083 |
| v75_register | 792 | 0.191 | 0.188 |
| v76_production | 324 | 0.627 | 0.630 |
| v77_omega | 609 | 0.878 | 0.875 |
| v77_rule_four | 369 | 0.271 | 0.808 |
