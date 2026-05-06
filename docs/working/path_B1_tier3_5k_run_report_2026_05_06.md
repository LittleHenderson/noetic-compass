# Path B-1 Tier 3 5K Run Report (2026-05-06)

## Summary

Path B-1 5K Tier 3 dialogue generation completed successfully.

- Output shard: `cas-synthetic/data/native_nl/v1_dialogue_5k_claude_20260506_0000.jsonl`
- Manifest: `cas-synthetic/data/native_nl/v1_dialogue_5k_claude_20260506_manifest.json`
- Spot review: `docs/working/path_B1_tier3_5k_spot_review_2026_05_06.md`
- English BPE artifact: `cas-synthetic/data/native_nl/english_bpe_5k_20260506.json`
- Run log: `tmp/tier3_5k_20260506.out.log`
- Error log: `tmp/tier3_5k_20260506.err.log`

## Run Command

```powershell
python cas-synthetic\scripts\generate_tier3_dialogue_v1.py `
  --target-records 5000 `
  --out-prefix cas-synthetic\data\native_nl\v1_dialogue_5k_claude_20260506 `
  --manifest cas-synthetic\data\native_nl\v1_dialogue_5k_claude_20260506_manifest.json `
  --records-per-shard 5000 `
  --seed 20260506 `
  --concurrency 5 `
  --cost-cap 75
```

## Result

- Accepted rows: 5,000
- Conversations: 1,002
- Validator pass rate: 100%
- API calls: 1,112
- Estimated cost: $15.0556
- Hard cap: $75.00
- Error log bytes: 0
- Model: `claude-sonnet-4-6`
- Trace ID: `9c0655ad-f3d5-4643-b99b-f4f29fd044d7`

The generator needed three rounds:

- Round 1: 4,884 accepted rows, cost $14.67
- Round 2: 109 accepted rows, cost $15.04 cumulative
- Round 3: 7 accepted rows, cost $15.06 cumulative

Rejected conversations:

- 17 `register` jargon leaks
- 1 `drive` jargon leak
- 1 overlong reply
- 1 JSON parse failure

Rejected rows were not written to the accepted shard.

## Distribution Checks

The 5K shard is balanced enough for the first native generation training pass:

- Noetic: 491-513 per class
- Domain: 1,241-1,256 per class
- Drive: 708-723 per class
- Register: 1,244-1,258 per class
- Tone: 968-1,016 per tone
- Demographic profile: 567-664 per profile

Expression families:

- `base`: 3,914
- `register_set`: 435
- `copresence`: 270
- `omega_emergent`: 209
- `recipe`: 172

## Reply Leakage Scan

Across all 5,000 accepted replies:

- `CAS`: 0 hits
- `noetic`: 0 hits
- `domain`: 0 hits
- `drive`: 0 hits
- `register`: 0 hits
- caret state notation such as `^2`: 0 hits
- drive notation such as `F6`: 0 hits

## Spot Review

Generated a 20-conversation spot-review file:

`docs/working/path_B1_tier3_5k_spot_review_2026_05_06.md`

Sampling seed: `20260506`.

Automated checks in the sampled conversations:

- banned reply jargon / notation
- empty prompt or reply
- overlong replies
- turn-index continuity

Sampled issue count: 0.

Qualitative read from early manual inspection: replies are conversational, not CAS-explanatory. Some responses are rhetorically dense, but they are normal English and suitable for the first native generation corpus.

## English BPE Artifact

Trained a project-native English BPE artifact on the accepted 5K dialogue shard.

```powershell
# Executed through the same cas_native package alias used by tests.
train_english_bpe(
  corpus="cas-synthetic/data/native_nl/v1_dialogue_5k_claude_20260506_0000.jsonl",
  vocab_size=24000,
  min_frequency=2,
  output_path="cas-synthetic/data/native_nl/english_bpe_5k_20260506.json",
  vocab_version="english-bpe-tier3-5k-20260506",
)
```

Result:

- Artifact: `cas-synthetic/data/native_nl/english_bpe_5k_20260506.json`
- English vocab size: 15,332
- BPE merge count: 15,072
- Corpus hash: `d2958e63110fa06fe52e893b0e419c4c045f4ca884367b88bdf3ed932b8194a3`
- Wall time: 34.9 seconds

## Current Status

B-1 has reached the 5K gate. The next decision is whether to:

1. commit the B-1 generator/tests/report now, keeping the generated 5K JSONL ignored by git;
2. run a B-3 native generation training smoke on the 5K corpus;
3. scale to 50K with the same Claude generator; or
4. run a separate 500-record Gemini provider bakeoff before choosing the 50K provider.

Recommendation: commit the B-1 code/report, then run a small B-3 CPU/GPU smoke before spending on a 50K expansion.
