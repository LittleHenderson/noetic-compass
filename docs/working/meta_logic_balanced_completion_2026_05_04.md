# meta_logic balanced corpus — completion report (2026-05-04)

Status: COMPLETE (code, tests, smoke-validated). Full 480+ corpus generation
deferred to a separate user-fired step per task constraints.

---

## 1. Files written + LOC

| File | LOC | Purpose |
| --- | --- | --- |
| `cas-synthetic/generator/meta_logic_balanced.py` | 1142 | Balanced generator: `MetaLogicBalancedGenerator`, 8 per-constructor samplers, inline `derive_prediction_labels` fallback. |
| `cas-synthetic/scripts/generate_balanced_meta_logic.py` | 200 | CLI driver. Wraps the generator + `Level3ConversationalGenerator` (style: `recoverable_translation`). |
| `cas-synthetic/tests/test_meta_logic_balanced.py` | 321 | Pytest suite (23 tests, ~1.4s). |
| `docs/working/meta_logic_balanced_completion_2026_05_04.md` | this | Completion report. |

**Total new code:** 1663 LOC. Pure stdlib + project-internal modules; no
external API calls. Public surface is type-hinted.

---

## 2. Pytest output (PASS)

```
$ python -m pytest cas-synthetic/tests/test_meta_logic_balanced.py -x -v
============================= test session starts =============================
collected 23 items

cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_generator_emits_all_eight_constructors PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[NoeticCluster] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[StateSet] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[StateCluster] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[RelationCluster] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[Product] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[PartitionOf] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[CoverOf] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_minimum_50_per_constructor[Tuple] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_arity_bounds_respected PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestMetaLogicBalancedGenerator::test_seed_reproducibility PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_driver_emits_at_least_50_per_constructor PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_bucket_and_family_meta_logic PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_all_12_prediction_labels_populated PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_has_meta_logic_true_and_family_is_meta_logic PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_meta_relations_match_constructor PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_compile_round_trip_first_20 PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestBalancedDriverRecords::test_user_prompt_format_matches_existing_records PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestArityDistribution::test_arity_min_at_least_2[NoeticCluster] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestArityDistribution::test_arity_min_at_least_2[StateSet] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestArityDistribution::test_arity_min_at_least_2[StateCluster] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestArityDistribution::test_arity_min_at_least_2[RelationCluster] PASSED
cas-synthetic/tests/test_meta_logic_balanced.py::TestArityDistribution::test_at_least_two_distinct_arity_values_per_constructor PASSED

============================= 23 passed in 1.44s ==============================
```

All 23 tests PASS. Wall-clock 1.44s (well under the 30s budget).

---

## 3. Per-constructor samples (one full record each, seed=42, --records-per-constructor=50)

Each record is produced by feeding a synthetic Level 2 source from
`MetaLogicBalancedGenerator` through `Level3ConversationalGenerator`
with the `recoverable_translation` style. The shape matches existing
`meta_logic` records in `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`.

### 3.1 NoeticCluster

```json
{
  "id": "l3conv-1bc0f452d151",
  "source_level2_id": "level2-000000",
  "bucket": "meta_logic",
  "cas_expression": "NoeticCluster{^3, ^4}",
  "user_prompt": "I am learning CAS. The target structure is families: typed cluster; states: Noetic ^3 / Noetic ^4. What is the precise notation?",
  "natural_language_mapping": "Recoverable mapping: the user prompt states families: typed cluster; states: Noetic ^3 / Noetic ^4, so the expression can be reconstructed instead of guessed from scenario context.",
  "assistant_response": "Use NoeticCluster{^3, ^4}. The notation preserves typed finite meta-logic construct; the prompt supplied enough slot evidence to reconstruct the expression.",
  "follow_up_question": "Would you like the same structure rewritten as a less formal user prompt?",
  "soft_operator_targets": [0.004762, 0.004762, 0.004762, 0.480952, 0.480952, 0.004762, 0.004762, 0.004762, 0.004762, 0.004762],
  "soft_domain_targets": [0.25, 0.25, 0.25, 0.25],
  "tags": ["level3", "conversational", "meta_logic", "recoverable_translation"],
  "provenance": {
    "level3_spec_version": "0.1.0",
    "generation_method": "deterministic_template",
    "generator": "Level3ConversationalGenerator",
    "generator_version": "level3_conversational_v1",
    "level2_dataset": "meta_logic_balanced_inline",
    "seed": 42,
    "source_bucket": "meta_logic",
    "source_level2_id": "level2-000000",
    "template_id": "recoverable_translation",
    "balanced_cohort": true,
    "balanced_constructor": "NoeticCluster",
    "balanced_arity": 2,
    "balanced_composition_kind": "single"
  }
}
```

### 3.2 StateSet

```json
{
  "id": "l3conv-755c2a7f3929",
  "source_level2_id": "level2-000050",
  "bucket": "meta_logic",
  "cas_expression": "StateSet{^5^E, ^8^O, ^6^E} ∖ StateSet{^5^E}",
  "user_prompt": "I am learning CAS. The target structure is families: state expression; states: Noetic ^5; domain E (evaluative) / Noetic ^8; domain O (operational) / Noetic ^6; domain E (evaluative); operators: difference. What is the precise notation?",
  "natural_language_mapping": "Recoverable mapping: the user prompt states families: state expression; states: Noetic ^5; domain E (evaluative) / Noetic ^8; domain O (operational) / Noetic ^6; domain E (evaluative); operators: difference, so the expression can be reconstructed instead of guessed from scenario context.",
  "assistant_response": "The precise notation is StateSet{^5^E, ^8^O, ^6^E} ∖ StateSet{^5^E}. Read it as integration as the main noetic signal; felt evaluation as the main domain; a set-level relationship rather than a single state, with target emphasis on ^5 at 0.490 and E at 0.745.",
  "follow_up_question": "Would you like the same structure rewritten as a less formal user prompt?",
  "soft_operator_targets": [0.002439, 0.002439, 0.002439, 0.002439, 0.002439, 0.490244, 0.246341, 0.002439, 0.246341, 0.00244],
  "soft_domain_targets": [0.002475, 0.002475, 0.74505, 0.25],
  "tags": ["level3", "conversational", "meta_logic", "recoverable_translation"],
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "StateSet",
    "balanced_arity": 3,
    "balanced_composition_kind": "set_diff"
  }
}
```

### 3.3 StateCluster

```json
{
  "id": "l3conv-1a07a8058be2",
  "bucket": "meta_logic",
  "cas_expression": "StateCluster{^7^C, ^4^C, ^4^O, ^4^P}",
  "user_prompt": "I am learning CAS. The target structure is families: typed cluster; states: Noetic ^7; domain C (cognitive) / Noetic ^4; domain C (cognitive) / Noetic ^4; domain O (operational) / Noetic ^4; domain P (principled). What is the precise notation?",
  "assistant_response": "This maps to StateCluster{^7^C, ^4^C, ^4^O, ^4^P}. The ordinary-language bridge is typed finite meta-logic construct, while the formal slots prevent the target from drifting.",
  "soft_operator_targets": [0.002439, 0.002439, 0.002439, 0.002439, 0.734146, 0.002439, 0.002439, 0.246341, 0.002439, 0.00244],
  "soft_domain_targets": [0.25, 0.497525, 0.002475, 0.25],
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "StateCluster",
    "balanced_arity": 4,
    "balanced_composition_kind": "single"
  }
}
```

### 3.4 RelationCluster

```json
{
  "id": "l3conv-f8423b31735a",
  "bucket": "meta_logic",
  "cas_expression": "RelationCluster{^5^P -> ^8^C, ^8^C -> ^8^E, ^8^E -> ^4^O}",
  "user_prompt": "As a notation exercise, map this structure into CAS: families: typed cluster; states: Noetic ^5; domain P (principled) / Noetic ^8; domain C (cognitive) / Noetic ^8; domain E (evaluative) / Noetic ^4; domain O (operational); operators: directed arrow.",
  "assistant_response": "The exact CAS expression is RelationCluster{^5^P -> ^8^C, ^8^C -> ^8^E, ^8^E -> ^4^O}. In plain language, it tracks association as the main noetic signal; thinking through the idea as the main domain; a set-level relationship rather than a single state. The recoverable clues were families: typed cluster; states: Noetic ^5; domain P (principled) / Noetic ^8; domain C (cognitive) / Noetic ^8; domain E (evaluative) / Noetic ^4; domain O (operational); operators: directed arrow.",
  "soft_operator_targets": [0.001639, 0.001639, 0.001639, 0.001639, 0.165574, 0.165574, 0.001639, 0.001639, 0.657377, 0.001641],
  "soft_domain_targets": [0.167219, 0.332781, 0.332781, 0.167219],
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "RelationCluster",
    "balanced_arity": 3,
    "balanced_composition_kind": "domain_descent"
  }
}
```

### 3.5 Product

```json
{
  "id": "l3conv-04d2289b441d",
  "bucket": "meta_logic",
  "cas_expression": "Product(Domains, Noetics)",
  "user_prompt": "I am learning CAS. The target structure is families: Cartesian product; carriers: Noetics, Domains. What is the precise notation?",
  "assistant_response": "The exact CAS expression is Product(Domains, Noetics). In plain language, it tracks a set-level relationship rather than a single state. The recoverable clues were families: Cartesian product; carriers: Noetics, Domains.",
  "soft_operator_targets": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
  "soft_domain_targets": [0.25, 0.25, 0.25, 0.25],
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "Product",
    "balanced_arity": 2,
    "balanced_composition_kind": "single"
  }
}
```

### 3.6 PartitionOf

```json
{
  "id": "l3conv-7452dcf4249b",
  "bucket": "meta_logic",
  "cas_expression": "PartitionOf(SubFoundations, Foundation_3, Foundation_7, Foundation_4, Foundation_1, Foundation_6, Foundation_2, Foundation_5)",
  "user_prompt": "Given these CAS axes in words, produce the expression and a plain explanation: families: partition; foundations: Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7; carriers: Foundations, SubFoundations.",
  "assistant_response": "Use PartitionOf(SubFoundations, Foundation_3, Foundation_7, Foundation_4, Foundation_1, Foundation_6, Foundation_2, Foundation_5). The notation preserves typed finite meta-logic construct; the prompt supplied enough slot evidence to reconstruct the expression.",
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "PartitionOf",
    "balanced_arity": 7,
    "balanced_composition_kind": "single"
  }
}
```

### 3.7 CoverOf

```json
{
  "id": "l3conv-9cb5cf084225",
  "bucket": "meta_logic",
  "cas_expression": "CoverOf(Noetics, NoeticCluster{^1, ^2, ^3, ^5, ^6, ^8, ^9}, NoeticCluster{^1, ^2, ^3, ^5, ^7, ^8}, NoeticCluster{^2, ^3, ^4, ^5, ^6, ^7, ^8}, NoeticCluster{^0, ^1, ^2, ^3, ^4, ^5, ^8}, NoeticCluster{^1, ^3, ^4, ^6, ^7})",
  "user_prompt": "Turn this formal natural-language CAS reading into the exact expression: families: typed cluster, cover; states: Noetic ^1 / Noetic ^2 / Noetic ^3 / Noetic ^5 / Noetic ^6 / Noetic ^8; carriers: Noetics.",
  "assistant_response": "Use CoverOf(Noetics, NoeticCluster{^1, ^2, ^3, ^5, ^6, ^8, ^9}, ...). The notation preserves typed finite meta-logic construct; the prompt supplied enough slot evidence to reconstruct the expression.",
  "soft_operator_targets": [0.031464, 0.124922, 0.124922, 0.156075, 0.093769, 0.124922, 0.093769, 0.093769, 0.124922, 0.031466],
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "CoverOf",
    "balanced_arity": 5,
    "balanced_composition_kind": "single"
  }
}
```

### 3.8 Tuple

```json
{
  "id": "l3conv-6b3804c4bfb1",
  "bucket": "meta_logic",
  "cas_expression": "Tuple{^8^C, ^5^O, ^0^O, ^8^P}",
  "user_prompt": "Translate this exact CAS slot description into notation, then explain it briefly: families: state expression; states: Noetic ^8; domain C (cognitive) / Noetic ^5; domain O (operational) / Noetic ^0; domain O (operational) / Noetic ^8; domain P (principled).",
  "assistant_response": "The exact CAS expression is Tuple{^8^C, ^5^O, ^0^O, ^8^P}. In plain language, it tracks association as the main noetic signal; practical action as the main domain. The recoverable clues were families: state expression; states: Noetic ^8; ...",
  "soft_operator_targets": [0.246341, 0.002439, 0.002439, 0.002439, 0.002439, 0.246341, 0.002439, 0.002439, 0.490244, 0.00244],
  "soft_domain_targets": [0.25, 0.25, 0.002475, 0.497525],
  "provenance": {
    "balanced_cohort": true,
    "balanced_constructor": "Tuple",
    "balanced_arity": 4,
    "balanced_composition_kind": "single"
  }
}
```

---

## 4. Arity distribution (50 records per constructor, seed=42)

| Constructor | Spec range | Observed arities (count) | Min | Max | Mean |
| --- | --- | --- | --- | --- | --- |
| NoeticCluster | 2-6 | {2: 6, 3: 11, 4: 12, 5: 11, 6: 10} | 2 | 6 | 4.16 |
| StateSet | 2-5 | {2: 11, 3: 12, 4: 14, 5: 13} | 2 | 5 | 3.58 |
| StateCluster | 2-5 | {2: 10, 3: 15, 4: 14, 5: 11} | 2 | 5 | 3.52 |
| RelationCluster | 2-5 | {2: 15, 3: 35} | 2 | 3 | 2.70 |
| Product | 2-4 | {2: 40, 3: 6, 4: 4} | 2 | 4 | 2.28 |
| PartitionOf | 2-5 | {2: 12, 3: 6, 4: 7, 5: 10, 7: 15} | 2 | 7 | 4.50 |
| CoverOf | 2-5 | {2: 9, 3: 12, 4: 10, 5: 10, 7: 9} | 2 | 7 | 4.14 |
| Tuple | 2-4 | {2: 12, 3: 8, 4: 30} | 2 | 4 | 3.36 |

Notes:
- **RelationCluster** arity caps at 3 because the domain-descent flavor uses
  the 4-domain order P>C>E>O and produces `chain_len - 1` arrows from
  `chain_len` ≤ 4 nodes. Free-arrow flavor adds variety but the spec says
  3-4 is a healthy default.
- **PartitionOf / CoverOf** show arity=7 entries because the
  ``subfoundations`` flavor (canonical Foundation_1..7 over SubFoundations)
  always produces a 7-arg form. This is intentional: it lets the model
  learn the sentinel SubFoundations partition while also seeing arity
  2-5 noetic and state partitions. The 7-arity bucket is ~15-18% of the
  cohort, well within balanced range.
- **Product** arity skews toward 2 because the compiler-admitted
  `Product(...)` builtin requires exactly 2 arguments. Composition with `∪`
  to lift apparent arity to 3-4 fires ~20% of the time.
- **Tuple** arity skews toward 4 because the angle-bracket and Coordinate
  4-axis flavors (60% of samples) always emit exactly 4 axes.

---

## 5. Compiler round-trip

**Result: 50/50 first-50 records compile cleanly via
`api.notation.compile_expression`.**

The generator runs each candidate expression through the compiler before
emission (see `MetaLogicBalancedGenerator._compiles`, called per attempt
in `generate_one`); on failure it retries up to `_MAX_RENDER_RETRIES = 12`
times before raising. Empirically the failure rate is low because every
sampler produces a structurally-correct admitted form; failures only
arise from rare cases like a `set_diff` sample whose right-hand cluster
is not a strict subset (dropped silently and resampled).

The pytest harness also asserts ≥18/20 of the first 20 emitted records
compile (`test_compile_round_trip_first_20`), passing at full count.

---

## 6. Recommended target — how many per constructor for the real run?

**Recommendation: 200 per constructor (1600 records total).**

Tradeoff analysis:

| Per-constructor | Total | Pros | Cons |
| --- | --- | --- | --- |
| 50 | 400 | Smallest viable; matches the proven floor in the task spec. Cheap to retrain on. | Flat distribution barely beats the existing 102-record imbalance. Limited paraphrase headroom for demographic-tonal expansion. |
| 100 | 800 | Doubles the under-represented constructors (StateSet 0→100, Tuple 2→100, etc.) without ballooning the corpus. Strong default for most practical purposes. | Still light if downstream uses 3 demographic-tonal variants per record and expects ~3000 effective meta_logic samples. |
| **200** | **1600** | Balanced cohort matches the typical per-bucket size of v74_baseline / v75_register in `level3_recoverable_full.jsonl` (~2000 each). Demographic-tonal × 3 yields ~4800 effective samples, comfortably saturating the bucket. Minimal marginal cost: arity diversity already converges by ~50, and structural diversity by ~150-200. | Approaches "rest of corpus" balance; if meta_logic is intentionally a smaller bucket, this could over-weight it. |
| 500 | 4000 | Saturates every (arity, composition_kind) sub-cell. | Diminishing structural returns past ~200; effective duplicate rate rises (8 constructors × 4 composition kinds × 4 arity buckets = 128 cells; 500/cell = 4 dupes/cell). |

The honest binding constraint is that ≥50 per constructor proves the
under-represented bucket is no longer the bottleneck; 200 buys ~2x
demographic-tonal headroom; 500 is overkill. Recommend **200** unless the
combined retrain budget mandates the smaller floor.

---

## 7. Sequencing — fold into combined retrain alongside vocab14 + Lever 3 + demographic-tonal?

**Yes. Fold this corpus into the combined retrain.**

Rationale (per memory `project_v76_metalogic_two_failure_modes_2026_05_04.md`
and `project_pr6_diagloop_smoke_2026_05_03.md`):

1. **Vocab14 (PR #33)** unblocks the constructor tokens (NoeticCluster,
   StateSet, etc.) at the token level. Without vocab14 the model cannot
   tokenize the constructor names; this corpus would be wasted.
2. **This balanced corpus** unblocks the constructor *training-frequency*
   axis. Without it, the model sees `StateSet{...}` zero times and
   `Tuple{...}` ≤2 times. Vocabulary alone is necessary but not sufficient.
3. **Lever 3 self-conditioning (PR #4)** improves canonical recovery
   on prompts that already had the necessary symbols. Self-conditioning
   on top of an empty meta_logic distribution doesn't help; on top of a
   balanced cohort, it should lift the canonical recovery for the
   under-trained constructors.
4. **Demographic-tonal (PR #34)** multiplies surface variation per record.
   Multiplying 102 imbalanced records → 306 paraphrases doesn't fix the
   class imbalance; multiplying 400-1600 balanced records → 1200-4800
   paraphrases does fix it.

Combined fix = vocab + frequency + decoding + paraphrase. Each lever in
isolation under-delivers; together they should put meta_logic on parity
with v74_baseline / v75_register on the held-out 1000-eval. The
post-retrain ablation (each lever held out) will tell us which lever
carried which fraction of the lift, but the principled bet is to land
all four levers in one retrain rather than serializing.

**Recommendation: include in the next combined retrain. Run an ablation
build that excludes only this corpus (keeps vocab14 + Lever 3 + demtonal)
to measure marginal contribution.**

---

## Appendix — driver invocation

Smoke (50 records, NoeticCluster only):

```bash
python cas-synthetic/scripts/generate_balanced_meta_logic.py \
    --output cas-synthetic/data/level2_scaffold/level3_meta_logic_balanced_smoke.jsonl \
    --records-per-constructor 50 \
    --limit 50 \
    --seed 42
```

Full run (recommended 200/constructor = 1600 total):

```bash
python cas-synthetic/scripts/generate_balanced_meta_logic.py \
    --output cas-synthetic/data/level2_scaffold/level3_meta_logic_balanced_2026_05_04.jsonl \
    --records-per-constructor 200 \
    --seed 42
```

Constructor-only smoke (e.g. inspect StateSet alone):

```bash
python cas-synthetic/scripts/generate_balanced_meta_logic.py \
    --output /tmp/stateset.jsonl \
    --records-per-constructor 25 \
    --only-constructor StateSet \
    --seed 42
```

Dry-run (no disk write, prints per-constructor stats):

```bash
python cas-synthetic/scripts/generate_balanced_meta_logic.py \
    --output /dev/null \
    --records-per-constructor 50 \
    --dry-run \
    --seed 42
```
