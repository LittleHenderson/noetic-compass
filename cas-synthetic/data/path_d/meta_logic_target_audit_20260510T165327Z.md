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
- Strict match (all 3 checks pass): **68 (64.8%)**
- Relation type matches: 84 (80.0%)
- Cluster cardinality matches: 101 (96.2%)
- All cluster members present: 89 (84.8%)

## By relation type

| Relation | Rows | Strict match |
|---|---:|---:|
| PartitionOf | 38 | 31 (81.6%) |
| CoverOf | 38 | 12 (31.6%) |
| Product | 29 | 25 (86.2%) |

## By cluster count

| n_clusters | Rows | Strict match |
|---:|---:|---:|
| 2 | 71 | 54 (76.1%) |
| 3 | 34 | 14 (41.2%) |

## Sample of worst offenders

**id**: `v1mix_cas_to_english_003898` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^2, ^9}, NoeticCluster{^0, ^4, ^8}, NoeticCluster{^1, ^3, ^5, ^6, ^7})`
- checks: relation=False (expected CoverOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 0: missing [0] from [0, 2, 9]
  - cluster 1: missing [0, 8] from [0, 4, 8]
- target: This expression states that the ten ways of thinking partition into three distinct groups. The first group contains something on your mind, drawn to it, and it just clicked. The second group contains something on your mind, struck a chord, 

**id**: `v1mix_cas_to_english_000698` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0}, NoeticCluster{^1, ^2, ^3, ^4, ^5, ^6, ^7, ^8, ^9})`
- checks: relation=True (expected CoverOf, detected CoverOf), cardinality=False (expected 2, detected 0), members=False
  - cluster 1: missing [5] from [1, 2, 3, 4, 5, 6, 7, 8, 9]
- target: The full repertoire of ten ways of thinking—from a thought through to something that popped into mind—is completely covered by a single foundational thought together with a cluster of nine additional ways: paying attention, drawn to it, can

**id**: `v1mix_cas_to_english_002501` (train)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^1, ^2, ^3, ^8}, NoeticCluster{^2, ^4, ^5, ^6, ^7, ^9})`
- checks: relation=True (expected CoverOf, detected CoverOf), cardinality=False (expected 2, detected 0), members=False
  - cluster 0: missing [0] from [0, 1, 2, 3, 8]
- target: The collection of thoughts, paying attention, drawn to it, pushed away from, and that reminds me forms a cover of the full set of ten ways of thinking. This means every instance of thinking—whether it's something on your mind, struck a chor

**id**: `v1mix_cas_to_english_003661` (train)

- source: `PartitionOf(Noetics, NoeticCluster{^2, ^3, ^4, ^6, ^8, ^9}, NoeticCluster{^0}, NoeticCluster{^1, ^5, ^7})`
- checks: relation=True (expected PartitionOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 0: missing [2, 4] from [2, 3, 4, 6, 8, 9]
- target: The ten ways of thinking partition into three groups: the first group contains those that speak to you, pulled toward, rubs the wrong way, hit hard, who you are, breaking it down, practice makes perfect, triggered a memory, and popped into 

**id**: `v1mix_cas_to_english_002410` (test)

- source: `CoverOf(Noetics, NoeticCluster{^0, ^1, ^3, ^4, ^6, ^7, ^8, ^9}, NoeticCluster{^2}, NoeticCluster{^5})`
- checks: relation=False (expected CoverOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 0: missing [8] from [0, 1, 3, 4, 6, 7, 8, 9]
- target: The ten ways of thinking partition into three groups: the first cluster contains thoughts, paying attention, an aversion, something that struck a chord, practice makes perfect, unpacking an idea, triggering a memory, and what just clicked; 

**id**: `v1mix_cas_to_english_000767` (train)

- source: `PartitionOf(Noetics, NoeticCluster{^0, ^1, ^2, ^3, ^6}, NoeticCluster{^8}, NoeticCluster{^4, ^5, ^7, ^9})`
- checks: relation=True (expected PartitionOf, detected PartitionOf), cardinality=True (expected 3, detected 3), members=False
  - cluster 0: missing [0] from [0, 1, 2, 3, 6]
- target: The full collection of ten ways of thinking partitions into three groups: the first group contains thoughts, paying attention, drawn to it, pushed away from it, breaking it down, and practice makes perfect; the second group contains somethi
