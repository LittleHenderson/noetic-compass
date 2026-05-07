# Path B-3 Native NL Generation Smoke: 50K Corpus

Date: 2026-05-07 UTC
Status: PASS

## Purpose

Validate that the B-2 real training bridge works against the completed 50K Tier 3 corpus and 50K English BPE artifact:

```text
CASNativeModel
  + NativeNLCollator
  + NLGenerationHead
  + forward_with_lm
  + masked_cross_entropy
```

This was a CPU smoke only. It was not intended to produce a useful conversational checkpoint.

## Command Shape

```powershell
python noetic-compass-scaffold\noetic-compass\cas-native\training\train_native_nl_gen.py `
  --data-path cas-synthetic\data\native_nl\v1_dialogue_50k_claude_20260507_0000.jsonl `
  --output-dir tmp\native_nl_b3_smoke_50k_20260507 `
  --epochs 1 `
  --limit 256 `
  --batch-size 8 `
  --device cpu `
  --english-bpe-path cas-synthetic\data\native_nl\english_bpe_50k_claude_20260507.json `
  --d-model 64 `
  --encoder-n-layers 1 `
  --encoder-n-heads 2 `
  --head-n-layers 1 `
  --head-n-heads 2 `
  --max-prompt-len 128 `
  --max-reply-len 128 `
  --max-cas-prefix-len 32 `
  --train-log-every-steps 5 `
  --logging-steps 5 `
  --seed 42
```

## Result

Training completed successfully.

```text
mode: real
global_step: 31
n_epochs: 1
n_train_records: 243
n_val_records: 13
final_loss_total: 0.970168948173523
use_fallback_head: false
use_cas_prefix: false
```

Observed train progress:

```text
step 1:  loss_total 1.0147
step 5:  loss_total 0.9990
step 10: loss_total 0.9928
step 20: loss_total 0.9826
step 30: loss_total 0.9719
```

The loss decreased cleanly across the smoke.

## Output Artifacts

Smoke output directory:

```text
tmp/native_nl_b3_smoke_50k_20260507
```

Files:

```text
checkpoint_manifest.json
english_bpe.json
model_final.pt
tokenizer.json
training_events.jsonl
```

These artifacts are intentionally not committed. The smoke proves the training path works; the checkpoint is not a production candidate.

## Tokenizer Provenance

The manifest confirms the trainer used the committed 50K BPE artifact:

```text
tokenizer_kind: ExtendedHybridCASTokenizer
english_bpe_source_path: cas-synthetic\data\native_nl\english_bpe_50k_claude_20260507.json
english_bpe_hash: 9dcd7fa372ac096a9bbe5742a3e2e01e3a3b9967661db645afee11c19b7adab4
bpe_merge_count: 23740
english_vocab_size: 24000
extended_vocab_size: 25759
vocab_version: english-bpe-tier3-50k-claude-20260507
```

## Interpretation

B-3 is unblocked at the pipeline level:

- Real path ran, not fallback.
- `NativeNLCollator` produced usable batches.
- `CASNativeModel.forward_with_lm` completed.
- `masked_cross_entropy` trained on reply positions.
- Tokenizer and BPE artifacts saved into the run directory with provenance.

This does not yet prove fluent generation. It proves the first native generation training path can run end to end on the new 50K/BPE assets.

## Next Execution Order

1. Decide whether the first serious B-3 run should be local CPU, local GPU, or RunPod GPU.
2. For a low-cost next smoke, run 1 epoch on 5K-10K records with the same 50K BPE artifact and the real path.
3. For the first useful training run, move to GPU and train long enough to evaluate generated replies, not only loss.
4. Add an inference/generation sampling helper if one does not already exist for `forward_with_lm`.
5. Only after generated replies are inspectable should B-4 two-stage chat REPL wiring begin.

