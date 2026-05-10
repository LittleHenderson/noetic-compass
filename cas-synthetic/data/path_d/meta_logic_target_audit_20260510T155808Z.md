# Meta-logic target audit

Strict structural validation of every meta-logic-shaped (PartitionOf / CoverOf / Product) training row in the v1 mix.

## Files scanned

| File | Rows | Meta-logic rows |
|---|---:|---:|
| `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` | 7395 | 380 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl` | 412 | 20 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl` | 412 | 21 |

## Aggregate

- Total meta-logic rows: **421**
- Strict match (all 3 checks pass): **27 (6.4%)**
- Relation type matches: 270 (64.1%)
- Cluster cardinality matches: 93 (22.1%)
- All cluster members present: 31 (7.4%)

## By relation type

| Relation | Rows | Strict match |
|---|---:|---:|
| PartitionOf | 233 | 7 (3.0%) |
| CoverOf | 158 | 3 (1.9%) |
| Product | 30 | 17 (56.7%) |

## By cluster count

| n_clusters | Rows | Strict match |
|---:|---:|---:|
| 1 | 4 | 0 (0.0%) |
| 2 | 188 | 26 (13.8%) |
| 3 | 229 | 1 (0.4%) |

## Sample of worst offenders

**id**: `v1mix_invalid_to_explanation_001672` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^1, ^3, ^4, ^6, ^7, ^8, ^9, ^99}, NoeticCluster{^2}, NoeticCluster{^5})`
- checks: relation=False (expected CoverOf, detected None), cardinality=False (expected 3, detected 0), members=False
  - cluster 0: missing [0, 1, 3, 4, 6, 7, 8, 9, 9] from [0, 1, 3, 4, 6, 7, 8, 9, 9]
  - cluster 1: missing [2] from [2]
  - cluster 2: missing [5] from [5]
- target: The expression tries to refer to an operator using the number 99, but the system only recognizes operators numbered from 0 through 9. The number 99 falls outside that allowed range entirely, so the compiler cannot identify what operator is 

**id**: `v1mix_invalid_to_explanation_001679` (train)

- source: `CoverOf(Noetics, NoeticCluster{^2, ^10}, NoeticCluster{^0, ^1, ^4, ^5, ^6, ^7, ^8, ^9}, NoeticCluster{^3})`
- checks: relation=False (expected CoverOf, detected None), cardinality=False (expected 3, detected 0), members=False
  - cluster 0: missing [2, 1] from [2, 1]
  - cluster 1: missing [0, 1, 4, 5, 6, 7, 8, 9] from [0, 1, 4, 5, 6, 7, 8, 9]
  - cluster 2: missing [3] from [3]
- target: One of the groups listed includes a slot numbered 10, but the system only recognizes slots numbered 0 through 9. Ten is simply out of bounds — there is no such slot in the available vocabulary — so the whole expression is rejected.

**id**: `v1mix_invalid_to_explanation_001689` (train)

- source: `PartitionOf(Noetics, NoeticCluster{^5, ^11}, NoeticCluster{^1, ^2, ^3, ^4, ^6, ^7, ^8}, NoeticCluster{^0, ^9})`
- checks: relation=False (expected PartitionOf, detected None), cardinality=False (expected 3, detected 0), members=False
  - cluster 0: missing [5, 1] from [5, 1]
  - cluster 1: missing [1, 2, 3, 4, 6, 7, 8] from [1, 2, 3, 4, 6, 7, 8]
  - cluster 2: missing [0, 9] from [0, 9]
- target: The expression tries to group items using a reference numbered 11, but the formal vocabulary only allows references numbered 0 through 9. The number 11 simply does not exist in the system, so the grouping cannot be built. Any careful reader

**id**: `v1mix_invalid_to_explanation_001704` (train)

- source: `CoverOf(Noetics, NoeticCluster{^7, ^12}, NoeticCluster{^0, ^1, ^2, ^3, ^4, ^5, ^6, ^8, ^9})`
- checks: relation=False (expected CoverOf, detected None), cardinality=False (expected 2, detected 0), members=False
  - cluster 0: missing [7, 1] from [7, 1]
  - cluster 1: missing [0, 1, 2, 3, 4, 5, 6, 8, 9] from [0, 1, 2, 3, 4, 5, 6, 8, 9]
- target: The expression tries to reference an operator identified by the number 12, but the system only recognizes operators numbered 0 through 9. Twelve is simply outside the range the system allows, so the expression cannot be compiled. A careful 

**id**: `v1mix_invalid_to_explanation_001686` (train)

- source: `CoverOf(Noetics, NoeticCluster{^1, ^2, ^5, ^6, ^9}, NoeticCluster{^0, ^10, ^4, ^7, ^8})`
- checks: relation=False (expected CoverOf, detected None), cardinality=False (expected 2, detected 0), members=False
  - cluster 0: missing [1, 2, 5, 6, 9] from [1, 2, 5, 6, 9]
  - cluster 1: missing [0, 1, 4, 7, 8] from [0, 1, 4, 7, 8]
- target: The expression tries to refer to a thinking-tool numbered 10, but the system only recognizes thinking-tools numbered 0 through 9. Ten falls outside that permitted range, so the expression cannot be compiled. To fix it, every item in both gr

**id**: `v1mix_invalid_to_explanation_001698` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^2, ^7, ^8}, NoeticCluster{^1, ^3, ^4}, NoeticCluster{^15, ^6, ^9})`
- checks: relation=False (expected CoverOf, detected None), cardinality=False (expected 3, detected 0), members=False
  - cluster 0: missing [0, 2, 7, 8] from [0, 2, 7, 8]
  - cluster 1: missing [1, 3, 4] from [1, 3, 4]
  - cluster 2: missing [1, 6, 9] from [1, 6, 9]
- target: One of the groupings contains a reference to operator slot 15, but the system only recognizes slots numbered 0 through 9. The number 15 falls outside that permitted range entirely, so the expression cannot be processed. A careful reader wou
