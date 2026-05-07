# Path B-1 Tier 3 50K Claude Run Report

Date: 2026-05-07 UTC
Status: Complete

## Summary

The Tier 3 Claude dialogue corpus reached the target 50,000 records.

Primary output:

```text
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0000.jsonl
...
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0010.jsonl
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_manifest.json
```

Manifest:

```text
schema_version: native_nl.v1
generation_version: native_nl_tier3_dialogue_v1
provider: claude
primary_model: claude-sonnet-4-6
target_records: 50000
total_records: 50000
tier3_records: 50000
total_conversations: 10064
validator_pass_count: 50000
validator_pass_rate: 1.0
cost_aborted: false
```

## Resume History

The first process wrote 17,756 records, then hit a Windows/OneDrive file-lock permission error while appending shard `_0003`.

The resume process started with:

```text
existing_records: 17756
new_target: 32244
```

It completed the corpus in three rounds:

```text
round 1: 31304 new records
round 2:   892 new records
round 3:    49 new records
```

Final manifest reports:

```text
resumed_records: 17756
total_records: 50000
total_cost_usd: 98.759
hard_cost_cap_usd: 110.0
```

Important nuance: `total_cost_usd` in the final manifest is the resume-run cost, not the entire original-plus-resume billing estimate. The original process had already spent roughly $54.50 before the permission error. Combined estimated spend is therefore approximately $153.26, still inside the intended $155 envelope.

## Shard Counts

```text
0000: 5000
0001: 5000
0002: 5000
0003: 4999
0004: 5000
0005: 5000
0006: 5000
0007: 5000
0008: 5000
0009: 5000
0010:    1
TOTAL: 50000
```

Shard `_0003` has 4,999 lines and `_0010` has 1 line because the resume boundary happened after the earlier permission error. This is not a data loss issue; total record count is exact.

## Independent Sanity Check

A read-only JSONL pass over all shards found:

```text
record_count: 50000
unique_ids: 50000
duplicate_ids: 0
conversation_count: 10064
bad_json_lines: 0
validator_false: 0
missing_required_fields: {}
source: claude_api = 50000
generator_model: claude-sonnet-4-6 = 50000
turn_count_overflows: 0
conversation_size_min: 3
conversation_size_max: 7
```

## Leakage/Jargon Check

The generator validator rejected 176 attempts before acceptance:

```text
145 validation:jargon:\bregister[s]?\b
 25 validation:jargon:\bdrive[s]?\b
  3 turn_count_mismatch
  2 validation:too_long
  1 validation:jargon:\bdomain[s]?\b
```

All accepted records have `validator_pass=true`.

An independent regex pass over accepted prompts/replies flagged ordinary English uses of:

```text
drive
register
domain
```

Manual sample read showed these were colloquial uses such as "drive home," "mind registers," and "cross-domain resonance," not CAS notation leakage. No accepted-record hits were observed for stricter CAS leakage patterns such as `CAS`, `noetic`, `^3`, `F1`, `omega`, or `meta-logic`.

## Distribution Snapshot

Noetic distribution is balanced at approximately 5,000 per Noetic:

```text
^0: 4970
^1: 5025
^2: 5008
^3: 5020
^4: 4971
^5: 4973
^6: 5005
^7: 5016
^8: 5009
^9: 5003
```

Domain distribution:

```text
C: 12502
E: 12514
O: 12496
P: 12488
```

Drive distribution:

```text
F1: 7136
F2: 7140
F3: 7174
F4: 7130
F5: 7183
F6: 7110
F7: 7127
```

Register distribution:

```text
A: 12486
E: 12372
T: 12558
f: 12584
```

Expression-family distribution:

```text
base: 39114
register_set: 4349
omega_emergent: 2090
copresence: 2720
recipe: 1727
```

## English BPE Artifact

Trained a project-native English BPE artifact on the completed 50K corpus using the same settings as the earlier 5K artifact.

Training input:

```text
tmp/v1_dialogue_50k_claude_20260507_all.jsonl
```

The temporary combined JSONL was built from the 11 shard files and contained exactly 50,000 records. It was used only as the BPE training input; the canonical corpus remains the sharded files under `cas-synthetic/data/native_nl/`.

Artifact:

```text
cas-synthetic/data/native_nl/english_bpe_50k_claude_20260507.json
```

Settings/result:

```text
vocab_version: english-bpe-tier3-50k-claude-20260507
vocab_size target: 24000
min_frequency: 2
n_records_trained_on: 50000
english_vocab_size: 24000
bpe_merge_count: 23740
trained_from_corpus_hash: 3ad2596d71945b8c371d0cc38835e09d853be73ae86c9bd84783e70939050af4
wall time: 197.33 seconds
```

Verification:

```text
Artifact loads via load_english_bpe_artifact.
ExtendedHybridCASTokenizer composes with HybridCASTokenizer.
Round-trip smoke passed on mixed English + CAS text.
Focused tests passed: 33/33
```

## Recommended Next Execution Order

1. Do not regenerate the 50K corpus.
2. Use `english_bpe_50k_claude_20260507.json` as the BPE artifact for B-3.
3. Run the B-3 native generation smoke using the committed B-2 trainer bridge.
4. If B-3 smoke passes, proceed to B-4 two-stage inference wiring.
5. Keep Path C Simplex/SSM work parked until conversational v0 exists.
