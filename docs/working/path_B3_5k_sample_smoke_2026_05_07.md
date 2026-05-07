# Path B-3 5K sample-reply smoke - 2026-05-07

## Verdict

PASS. The native NL generation pipeline now closes end to end on real Tier 3
dialogue data with the real model path, not the fallback head.

This run validates:

- Tokenizer + 50K English BPE artifact load correctly.
- `CASNativeModel.forward_with_lm()` trains on reply-only masked CE.
- `generate_reply()` runs during training via `--sample-every-steps`.
- `sample_reply` events are written with prompt, target reply, generated reply,
  CAS expression, register, token preview, EOS status, and provenance IDs.
- Loss falls while generated text moves from token noise toward English-like
  fragments.

## Run Artifacts

Run directory:

`tmp/native_nl_b3_smoke_5k_with_samples`

Important files:

- `training_events.jsonl`
- `checkpoint_manifest.json`
- `model_final.pt`
- `tokenizer.json`
- `english_bpe.json`

Human-readable sample summary:

`tmp/b3_smoke_5k_samples_summary.md`

These artifacts are local temporary outputs, not committed model assets.

## Configuration

Key manifest fields:

- `n_train_records`: 4750
- `n_val_records`: 250
- `global_step`: 594
- `n_epochs_completed`: 1
- `use_fallback_head`: false
- `use_cas_prefix`: false
- `sample_every_steps`: 100
- `sample_max_new_tokens`: 60
- `sample_sampling`: temperature
- `sample_temperature`: 0.8
- `d_model`: small smoke configuration, not production scale

Tokenizer:

- `tokenizer_kind`: `ExtendedHybridCASTokenizer`
- `english_bpe_source_path`:
  `cas-synthetic/data/native_nl/english_bpe_50k_claude_20260507.json`
- `extended_vocab_size`: 29944

## Observed Learning

Loss dropped strongly in one epoch:

- Early total loss: about 1.03
- Final total loss: about 0.52
- LM loss at logged train steps: 9.17 -> 3.56

Five sample events fired at steps 100, 200, 300, 400, and 500.

Held-out prompt:

> I've been asked to help shape the curriculum for our junior engineers -
> what's actually worth passing down, in your view?

CAS state:

`^5^C_{F5}|T`

Target reply:

> I worry I might be oversimplifying this, but - the technical skills age out;
> what doesn't is the capacity to author one's own judgment. Years of
> accumulated experience composing the mind, the slow-built sense of what
> matters and why - that's the inheritance worth transferring, if I'm reading
> this right.

Sample evolution:

- Step 100: concatenated random English fragments, no spacing.
- Step 200: still mostly blob text, but more corpus-like vocabulary.
- Step 300: spaces emerge and EOS fires at 30 tokens.
- Step 400: EOS fires again; spacing structure improves.
- Step 500: recognizable English fragments and punctuation appear.

No CAS notation leakage was observed in the five samples.

## What This Proves

- B-3 is no longer just a loss-only training script. It can show actual model
  speech during training.
- The inference helper and trainer use compatible routing.
- The tokenizer, encoder, decoder, masked loss, checkpoint manifest, and sample
  event stream are coherent enough to support a paid GPU run.

## What This Does Not Prove

- Fluency. The model is not yet producing grammatical replies.
- CAS grounding fidelity. The sample is too small and too early to prove that
  `^5/F5/T` changes word choice in the intended way.
- Production stability at `d_model=512`, six encoder layers, and six decoder
  layers.

## Next Execution Order

Do not jump directly from this CPU-scale smoke to a multi-day full run.

Recommended next gate:

1. Run a short GPU preflight using the production architecture shape:
   `d_model=512`, `encoder_n_layers=6`, `head_n_layers=6`, full 50K tokenizer
   and BPE, `--limit 5000`, `--epochs 1`, and `--sample-every-steps 100`.
2. Verify memory, throughput, loss descent, and sample event quality.
3. If clean, run a 10K or 50K multi-epoch GPU training job with the same
   architecture.
4. Only wire B-4 chat REPL after a checkpoint can produce non-empty English
   samples beyond random fragments.

The reason: the current pass proves the pipeline. The next risk is production
shape - GPU memory, throughput, and whether the 512-wide decoder learns without
new shape bugs.
