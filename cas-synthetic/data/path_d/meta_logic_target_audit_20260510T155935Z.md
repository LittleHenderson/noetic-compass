# Meta-logic target audit

Strict structural validation of every meta-logic-shaped (PartitionOf / CoverOf / Product) training row in the v1 mix.

## Files scanned

| File | Rows | Meta-logic rows |
|---|---:|---:|
| `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl` | 7395 | 96 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl` | 412 | 5 |
| `cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl` | 412 | 4 |

## Aggregate

- Total meta-logic rows: **105**
- Strict match (all 3 checks pass): **27 (25.7%)**
- Relation type matches: 84 (80.0%)
- Cluster cardinality matches: 92 (87.6%)
- All cluster members present: 31 (29.5%)

## By relation type

| Relation | Rows | Strict match |
|---|---:|---:|
| PartitionOf | 38 | 7 (18.4%) |
| CoverOf | 38 | 3 (7.9%) |
| Product | 29 | 17 (58.6%) |

## By cluster count

| n_clusters | Rows | Strict match |
|---:|---:|---:|
| 2 | 71 | 26 (36.6%) |
| 3 | 34 | 1 (2.9%) |

## Sample of worst offenders

**id**: `v1mix_cas_to_english_003898` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^2, ^9}, NoeticCluster{^0, ^4, ^8}, NoeticCluster{^1, ^3, ^5, ^6, ^7})`
- checks: relation=False (expected CoverOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 0: missing [0] from [0, 2, 9]
  - cluster 1: missing [0, 8] from [0, 4, 8]
  - cluster 2: missing [3, 5] from [1, 3, 5, 6, 7]
- target: This expression states that the ten ways of thinking partition into three distinct groups. The first group contains something on your mind, drawn to it, and it just clicked. The second group contains something on your mind, struck a chord, 

**id**: `v1mix_cas_to_english_002584` (train)

- source: `PartitionOf(Noetics, NoeticCluster{^7}, NoeticCluster{^2, ^5}, NoeticCluster{^0, ^1, ^3, ^4, ^6, ^8, ^9})`
- checks: relation=True (expected PartitionOf, detected PartitionOf), cardinality=False (expected 3, detected 0), members=False
  - cluster 1: missing [2] from [2, 5]
  - cluster 2: missing [3] from [0, 1, 3, 4, 6, 8, 9]
- target: The complete set of ten ways of thinking partitions into three distinct groups: the first group contains practice makes perfect; the second group contains pulled toward and who one is; the third group contains a thought, paying attention, a

**id**: `v1mix_cas_to_english_002410` (test)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^1, ^3, ^4, ^6, ^7, ^8, ^9}, NoeticCluster{^2}, NoeticCluster{^5})`
- checks: relation=False (expected CoverOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 0: missing [3, 8] from [0, 1, 3, 4, 6, 7, 8, 9]
- target: The ten ways of thinking partition into three groups: the first cluster contains thoughts, paying attention, an aversion, something that struck a chord, practice makes perfect, unpacking an idea, triggering a memory, and what just clicked; 

**id**: `v1mix_cas_to_english_000107` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^2, ^4}, NoeticCluster{^0, ^1, ^3, ^5, ^6, ^7, ^8, ^9})`
- checks: relation=True (expected CoverOf, detected CoverOf), cardinality=False (expected 2, detected 0), members=False
  - cluster 1: missing [3] from [0, 1, 3, 5, 6, 7, 8, 9]
- target: The covering relation states that a cluster of three—something on your mind, drawn to it, and struck a chord—covers a larger cluster of ten: a thought, paying attention, drawn to it, an aversion, struck a chord, who one is, breaking it down

**id**: `v1mix_cas_to_english_000181` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^1, ^4, ^5, ^9}, NoeticCluster{^6, ^7, ^8}, NoeticCluster{^2, ^3})`
- checks: relation=False (expected CoverOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 2: missing [3] from [2, 3]
- target: The ten ways of thinking partition into three groups: the first group contains a thought, paying attention, something that struck a chord, who one is, that reminds me, and it just clicked; the second group contains unpacking an idea, breaki

**id**: `v1mix_cas_to_english_000241` (train)

- source: `PartitionOf(Noetics, NoeticCluster{^2}, NoeticCluster{^0, ^1, ^3, ^4, ^5, ^6, ^7, ^8, ^9})`
- checks: relation=True (expected PartitionOf, detected PartitionOf), cardinality=True (expected 2, detected 2), members=False
  - cluster 1: missing [3, 5] from [0, 1, 3, 4, 5, 6, 7, 8, 9]
- target: The ten ways of thinking partition into two groups: the first group contains something drawn to it, and the second group contains a thought, paying attention, an aversion, something that struck a chord, the sum of one's experiences, unpacki
