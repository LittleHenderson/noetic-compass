# Structured-Token Eval Confusion Report

Total samples: 1000
All-heads exact: 868
All-heads failures: 132

## Head Failures

| Head | Failures |
|---|---:|
| expression_family | 84 |
| transition_kind | 84 |
| noetic | 21 |
| drive | 14 |
| registers | 12 |
| register_mode | 8 |
| domain | 7 |
| authority | 0 |
| has_meta_logic | 0 |
| has_omega | 0 |
| meta_relations | 0 |
| turn_type | 0 |

## Bucket Failures

| Bucket | n | Failures |
|---|---:|---:|
| v77_rule_four | 123 | 81 |
| meta_logic | 102 | 22 |
| v75_register | 264 | 20 |
| v76_production | 108 | 6 |
| v77_omega | 203 | 2 |
| v74_baseline | 200 | 1 |

## v77_rule_four Confusions

### Expression Patterns

| Pattern | n | Exact | Rate |
|---|---:|---:|---:|
| omega_emergent | 64 | 0 | 0.0% |
| plus_copresence | 59 | 42 | 71.2% |

### expression_family

| Target | Prediction | Count |
|---|---|---:|
| rule_four | omega | 64 |
| rule_four | register_state | 16 |

### transition_kind

| Target | Prediction | Count |
|---|---|---:|
| relation | omega_bind | 64 |
| relation | state | 17 |
