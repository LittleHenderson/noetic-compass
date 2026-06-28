# Diagram-Loop Honest Two-Pass Eval Report

> **Protocol**: self-prediction priors only — no oracle, no ground-truth leak.

## Four-Condition Summary

| Condition | Exact Rate |
|---|---:|
| Canonical text-only (pass 1) | 0.630 |
| Paraphrase text-only | 0.287 |
| Paraphrase with self-prior (pass 2) | 0.464 |
| **Honest lever lift (pp)** | **+17.6 pp** |

## Per-Head Accuracy — Canonical Text-Only

| Head | Rate |
|---|---:|
| drive | 0.863 |
| noetic | 0.881 |
| registers | 0.935 |
| register_mode | 0.948 |
| domain | 0.952 |
| expression_family | 0.968 |
| transition_kind | 0.976 |
| meta_relations | 0.979 |
| has_meta_logic | 0.999 |
| turn_type | 1.000 |
| authority | 1.000 |
| has_omega | 1.000 |

## Per-Head Accuracy — Paraphrase with Self-Prior

| Head | Rate |
|---|---:|
| drive | 0.754 |
| noetic | 0.763 |
| register_mode | 0.895 |
| domain | 0.899 |
| registers | 0.918 |
| meta_relations | 0.945 |
| transition_kind | 0.957 |
| expression_family | 0.969 |
| has_meta_logic | 0.991 |
| turn_type | 1.000 |
| authority | 1.000 |
| has_omega | 1.000 |

## Bucket Breakdown — Paraphrase with Self-Prior

| Bucket | n | Exact Rate |
|---|---:|---:|
| meta_logic | 306 | 0.196 |
| v74_baseline | 600 | 0.708 |
| v75_register | 792 | 0.111 |
| v76_production | 324 | 0.324 |
| v77_omega | 801 | 0.795 |
| v77_rule_four | 177 | 0.429 |
