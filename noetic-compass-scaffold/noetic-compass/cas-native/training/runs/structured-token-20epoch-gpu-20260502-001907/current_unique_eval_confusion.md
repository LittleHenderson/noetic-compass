# Structured-Token Eval Confusion Report

Total samples: 1000
All-heads exact: 851
All-heads failures: 149

## Head Failures

| Head | Failures |
|---|---:|
| transition_kind | 84 |
| expression_family | 83 |
| register_mode | 28 |
| drive | 16 |
| noetic | 16 |
| registers | 13 |
| domain | 4 |
| meta_relations | 1 |
| authority | 0 |
| has_meta_logic | 0 |
| has_omega | 0 |
| turn_type | 0 |

## Bucket Failures

| Bucket | n | Failures |
|---|---:|---:|
| v77_rule_four | 123 | 84 |
| v75_register | 264 | 39 |
| meta_logic | 102 | 13 |
| v76_production | 108 | 11 |
| v77_omega | 203 | 2 |
| v74_baseline | 200 | 0 |

## v77_rule_four Confusions

### Expression Patterns

| Pattern | n | Exact | Rate |
|---|---:|---:|---:|
| omega_emergent | 64 | 0 | 0.0% |
| plus_copresence | 59 | 39 | 66.1% |

### expression_family

| Target | Prediction | Count |
|---|---|---:|
| rule_four | omega | 64 |
| rule_four | register_state | 19 |

### transition_kind

| Target | Prediction | Count |
|---|---|---:|
| relation | omega_bind | 64 |
| relation | state | 19 |
