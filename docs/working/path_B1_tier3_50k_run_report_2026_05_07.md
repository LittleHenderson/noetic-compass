# Path B-1 Tier 3 50K Claude Run — Completion Report

**Date:** 2026-05-07
**Status:** COMPLETE — all automated gates PASS, corpus ready for B-3 native generation training
**Final cost:** $153.26 (under $155 original budget; $54.50 original + $98.76 resume)

## Run summary

```
trace_id:               115e5e62-8f1b-4642-b2db-dacf9bd49689
seed:                   20260507
target_records:         50,000
total_records:          50,000  (100%)
total_conversations:    10,064
provider:               claude
primary_model:          claude-sonnet-4-6
fallback_model:         claude-3-5-sonnet-20241022
final_model:            claude-sonnet-4-6 (no fallback triggered)
validator_pass_count:   50,000 / 50,000  (100%)
cost_aborted:           False
total_cost_usd:         $98.76 (resume run only — original spent ~$54.50 separately)
api_calls:              7,326 (resume) + ~2,800 (original) ≈ 10,100 total
```

## Run trajectory

The run had two distinct phases:

**Phase 1 — original launch (13:23 → 15:25 PDT)**: PID 60528, concurrency=10, cap=$155. Wrote 17,756 records (3.5 full shards) before crashing with `PermissionError` on shard 0003. **Cause: OneDrive sync race.** OneDrive locked the file briefly during a write attempt; the script's `append_records` method doesn't catch `PermissionError`. Process died.

**User mitigation**: killed OneDrive process via Task Manager. Eliminated the file-lock race for the rest of the run.

**Phase 2 — resume (15:33 → 19:20 PDT)**: PID 34748, same `--out-prefix` → script's `load_existing_records` recognized the 17,756 existing records, set new target to 32,244. Cap=$110. Completed cleanly at 19:20 PDT. Total wall-clock for resume: ~3h 47m. Total wall-clock from launch: ~6h.

**Power blip mid-resume**: brief flicker around 15:38 PDT didn't kill the machine (UPS or PSU caps held); same PID 34748 continued. No data loss.

## Failure breakdown

176 failures across ~10,100 API calls (~1.7% failure rate, all validator rejects):

```
145  validation:jargon:\bregister[s]?\b
 25  validation:jargon:\bdrive[s]?\b
  3  turn_count_mismatch
  2  validation:too_long
  1  validation:jargon:\bdomain[s]?\b
```

These were caught and rejected at validation time — none made it into the corpus. The corpus's `validator_pass_count` is 50,000 / 50,000.

## Automated quality gates — ALL PASS

### Schema integrity
- 50,000 / 50,000 records have all required fields (id, trace_id, schema_version, tier, conversation_id, turn_index, cas_expression, prompt_text, reply_text, validator_pass, source)
- 0 schema drift

### Provenance check
- `source: claude_api` on all 50,000 records ✓ (the `d8e37d4` provenance fix worked)
- `generator_model: claude-sonnet-4-6` on all 50,000 ✓

### Leakage scan (all 50K records)
| Pattern | Hits |
|---|---|
| `CAS` (literal) | 0 |
| `noetic[s]?` | 0 |
| `domain[s]?` | 0 |
| `drive[s]?` | 0 |
| `register[s]?` | 0 |
| `^N` caret-state notation | 0 |
| `F1`-`F7` drive notation | 0 |
| **TOTAL LEAKS** | **0** |

### Reply length distribution
- Mean: **373.1 chars** (matches 5K bakeoff's 373.5 — corpus style is consistent at scale)
- Median: 372
- Min: 104, Max: 597
- p25: 332, p75: 413

The 5K-bakeoff length distribution survived 10× scale-up. No drift toward terser or longer replies.

## CAS axis distribution (from manifest)

Even coverage across all axes:

```
Noetic   ^0..^9    each ~5,000 ± 30   (target: ~5,000)
Domain   P/C/E/O   each ~12,500       (target: ~12,500)
Drive    F1..F7    each ~7,150        (target: ~7,143)
Register T/A/f/E   each ~12,500       (target: ~12,500)
```

Expression family distribution:
- base (single state): 39,114 (78.2%)
- register_set: 4,349
- (rest in compound / omega / production / meta_logic — meta_logic underrepresented as expected; that's a Tier 4 follow-on slice)

## English BPE artifact trained on 50K

```
path:                cas-synthetic/data/native_nl/english_bpe_50k_20260507.json
schema_version:      english_bpe_artifact.v1
vocab_version:       english_bpe.50k.v1.0
english_vocab_size:  24,000  (hit target cap)
bpe_merge_count:     23,740
n_records_trained:   50,000
trained_from_corpus_hash: 3ad2596d71945b8c...
file size:           1.57 MB
training time:       197.6 sec
```

24K vocab is the production BPE for the v0 conversational model. Codex's prior 5K BPE artifact (15,332 vocab) is now superseded.

## Cost economics for the record

```
Phase 1 (original):  ~$54.50  for ~17,756 records  → $0.00307/record
Phase 2 (resume):    $98.76   for 32,244 records   → $0.00306/record
Total:               $153.26  for 50,000 records   → $0.003065/record
```

Compare to projection lines:
- Original budget: $155 — under by $1.74
- Codex projected $148-153 at 50K — actual lands in the middle of that range
- Pro-preview Gemini 50K extrapolation was $434 (2.9× Claude); Flash-Lite would have been $30 but failed manual blind review (20/20 distinguishable)

Claude wins on cost-per-quality. Pro-preview's hidden thinking tokens make it more expensive than Claude despite the per-token rate appearance. Flash-Lite's terse replies failed quality. The Claude path has been the right choice empirically.

## Path B status now

| Item | State |
|---|---|
| B-1: 50K Tier 3 corpus | **DONE — 50K Claude records, 0 leakage, validator-clean** |
| B-1: English BPE on 50K | **DONE — 24K vocab artifact** |
| B-2: NativeNLCollator + masked CE | DONE — committed `62f0299` |
| **B-3: First native gen training run** | **READY — corpus + BPE + collator + trainer all in place** |
| B-4: Two-stage chat REPL | Blocked on B-3 |
| Path C: Simplex Δ°₃₉ | Parked POST v0 |

## What unblocks next (B-3)

The B-2 trainer (`cas-native/training/train_native_nl_gen.py`) can now run real training against:
- Corpus: `cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_*.jsonl`
- BPE artifact: `cas-synthetic/data/native_nl/english_bpe_50k_20260507.json`

The CPU-side B-3 smoke (1 epoch, small d_model) is free and validates pipeline. The production GPU run is multi-day work that needs explicit user authorization (compute cost) and probably moves to RunPod.

## Lessons / followups for next time

1. **OneDrive race is a real risk** for files in OneDrive-synced directories. The writer's `append_records` should catch `PermissionError` and retry with backoff. Filed as a potential follow-up code fix; not required for v0 ship since killing OneDrive worked.

2. **Cost cap should be set with margin from the start.** Original $155 left only ~1% buffer; we got lucky the original Phase 1 didn't ALSO hit the cap. Future runs: set cap at 1.10× projected, not 1.01×.

3. **The script's resume-from-prefix logic worked perfectly** — script picked up exactly where the crash left off, no duplicate conversation_ids, no records lost, no double-charging.

4. **Concurrency 10 hit Anthropic rate limits**, getting only ~1.5× speedup over concurrency 5. Not worth bumping further without paid tier upgrade. For 100K+ corpus runs, consider Anthropic Build/Scale tier or batch API.

## Artifacts on disk

```
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0000.jsonl    5,000 records
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0001.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0002.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0003.jsonl    4,999
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0004.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0005.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0006.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0007.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0008.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0009.jsonl    5,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_0010.jsonl        1
                                                                         ------
                                                            TOTAL       50,000
cas-synthetic/data/native_nl/v1_dialogue_50k_claude_20260507_manifest.json   3,656 bytes
cas-synthetic/data/native_nl/english_bpe_50k_20260507.json              1.57 MB
```

50K JSONL stays gitignored (large, regenerable). Manifest + BPE artifact tracked.

End of report.
