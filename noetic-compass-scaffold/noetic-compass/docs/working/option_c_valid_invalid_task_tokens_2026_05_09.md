# Option C — `[VALID]` / `[INVALID]` Task Tokens in CAS Prefix

## Origin and decision

The v1 PREFIX128 5ep 24-record audit (commit `7c01609`) found that
3/3 valid `rpm_chain` records misrouted: the model produced
byte-identical invalid-explanation language despite the compilability
gate routing them as `cas_to_english`.

The decoder-seeding diagnostic (commit `9bd5d20`, Option A) confirmed
the issue is task-control, not missing content. With seed
`"Let <var> name "`, the model produces let-binding-shaped output
on all 3 records with correct variable names and partial body
content. User grading: yellow / high-yellow / yellow vs control's
3× wrong. Treatment exceeded control by ≥1 grade band on every
record.

User direction (2026-05-09):

> Keep decoder-seeding diagnostic only, off by default. Do not wire
> it into production yet. It is a useful proof, but it is a hack.
>
> Next correct move is Option C:
> - rebuild/rewrite the v1 training format with explicit task tokens
>   in the CAS prefix,
> - especially `[VALID]` / `[INVALID]`,
> - retrain a small run,
> - re-evaluate rpm_chain, meta_logic, fractal, recipe.
>
> Why C: the model listens to the CAS prefix. Wrapper text does not
> dominate. So put the task signal where the model listens.

This doc captures the architectural design before any code or
training spend so the shape can be reviewed and signed off.

## Why CAS-prefix tokens, not wrapper text

The v1 PREFIX128 5ep run proved empirically that the discrete
cas_prefix dominates decoder conditioning. From
`docs/working/identifier_repair_and_rpm_routing_2026_05_09.md`:

- 5/5 wrapper-text variants produced byte-identical greedy output —
  the encoder/bottleneck-z is insensitive to wrapper differences
  when the cas_prefix dominates
- 20/20 high-entropy samples for valid `rpm_chain` routed as
  invalid — the valid trajectory has effectively zero probability
  mass

Conclusion: any task signal that lives only in `prompt_text` cannot
reach the head's autoregressive trajectory. The signal must enter
the cas_prefix path to actually change behavior. `[VALID]` /
`[INVALID]` placed at position 0 of the cas_prefix gives the head
an unambiguous discrete routing signal that flows through self-
attention from the very first decoder step.

## Token design

### Minimal vocabulary expansion: 2 new tokens

```
[VALID]     — prepended to cas_prefix_ids when route_by_compilability
              returns task_type="cas_to_english"
[INVALID]   — prepended when task_type="invalid_to_explanation"
```

We do NOT introduce `[CAS_TO_ENGLISH]` / `[INVALID_EXPLANATION]` as
separate tokens. The existing `[TASK_EXPR]` / `[TASK_EXPLAIN]`
tokens already exist in the tokenizer and were used in the v0 (B-3)
corpus shape — they're available as semantic anchors for embedding
warm-start (see below) but not used as the new task signal.

Two reasons for minimality:
1. The valid/invalid distinction is the actual axis the model needs
   to learn. Task type (`cas_to_english` vs `invalid_to_explanation`)
   is fully derivable from valid/invalid; adding a redundant second
   axis only doubles the vocabulary delta.
2. Two tokens is the smallest change that resolves the diagnosed
   failure mode. Larger expansions add training surface without
   evidence they're needed.

### Placement: position 0 of cas_prefix_ids

Training-time cas_prefix shape:
```
[VALID, ^, 0, ^P, ;, l, e, t, ...]    # for valid CAS
[INVALID, ^, 0, ^|, ...]                # for invalid CAS
```

The `[VALID]` / `[INVALID]` token sits BEFORE any CAS notation so
the head's first self-attention step over the cas_prefix sees the
task discriminator immediately. This matches how task tokens work
in standard seq2seq systems (T5, etc.).

### Tokenizer extension mechanics

`cas-native/training/tokenizer.py` defines `SPECIAL_TOKENS` as a
python list at module top. Adding two entries:

```python
SPECIAL_TOKENS = [
    "[PAD]", "[UNK]", "[BOS]", "[EOS]", "[SEP]",
    "[CAS]", "[/CAS]",
    "[TASK_EXPR]", "[TASK_EXPLAIN]", "[TASK_CHAT]",
    "[PROMPT]", "[RESPONSE]",
    "[SP]", "[NL]", "[TAB]",
    "[VALID]",     # NEW
    "[INVALID]",   # NEW
]
```

Vocab size: 38683 → 38685 (+2 reserved tokens). The English-BPE
extension (24K merges) and the rest of the CAS reserved tokens are
unchanged.

The existing tokenizer artifacts (`tokenizer.json`,
`english_bpe.json`) need to be regenerated or extended. Cleanest
path: load the existing tokenizer, append the two tokens to the
internal `word2id` map at indices 38683 and 38684, save as a new
artifact `tokenizer_v1c.json`. Backward compatible: any existing
checkpoint can be loaded against this tokenizer; new tokens just
sit unused.

### Embedding warm-start

The retrain loads the v1 PREFIX128 5ep checkpoint as the starting
point (rather than training from scratch). The token embedding
matrix needs to expand from `[38683, 512]` to `[38685, 512]`. Two
new rows initialized via warm-start:

```python
# Copy semantically-related existing embeddings as warm starts.
new_embed.weight.data[id_for("[VALID]")]   = old.weight.data[id_for("[TASK_EXPR]")]
new_embed.weight.data[id_for("[INVALID]")] = old.weight.data[id_for("[TASK_EXPLAIN]")]
```

Rationale: `[TASK_EXPR]` was used in the v0 corpus for valid CAS
expression handling; `[TASK_EXPLAIN]` for explanation tasks. Their
learned embeddings (from B-3 50K-record training that fed the
tokenizer) carry the semantic distinction we want the new tokens
to inherit. This is a cheap warm start — random init would also
work but converges slower.

## Corpus regeneration

The v1 mix at `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl`
already carries `v1mix_task_type` per record. The training-time
collator (`cas-native/training/datasets/native_nl_collator.py`)
needs to prepend the right special token to cas_prefix_ids based
on that field. Two paths:

**Path A — modify the collator at runtime.** No corpus regen needed;
the collator inspects each record's `v1mix_task_type` and prepends
`[VALID]` for `cas_to_english` and `[INVALID]` for
`invalid_to_explanation`. Cleanest for the data side; all the
information is already there.

**Path B — bake the token into the data file.** Run the
`build_path_d_v1_mix.py` aggregator with a flag to emit
`cas_expression` strings prefixed with `[VALID]` / `[INVALID]`.
More invasive but reproducible from the data file alone.

**Recommendation:** Path A. Keeps the data file format stable and
the task-token injection visible in the trainer code where it's
easy to audit.

## Trainer modifications

`cas-native/training/datasets/native_nl_collator.py` —
`NativeNLCollator.__call__`:

```python
def _prepend_task_token(
    self, cas_token_ids: list[int], task_type: str,
) -> list[int]:
    if task_type == "cas_to_english":
        return [self.valid_token_id] + cas_token_ids
    elif task_type == "invalid_to_explanation":
        return [self.invalid_token_id] + cas_token_ids
    else:
        # Defensive: if task_type missing, no prepend.
        return cas_token_ids
```

The collator already iterates records and tokenizes
`cas_expression`. The new helper inserts the task token at index
0 before padding. `max_cas_prefix_len` accommodates the +1 token
naturally (the cap was 128; adding 1 task token leaves 127 for
CAS content — comfortable for all observed records per the audit).

Trainer hparams stay identical to the v1 PREFIX128 5ep run:
- `--epochs 5`
- `--batch-size 8`
- `--lr 2e-4`
- `--beta-curriculum-steps 1500`
- `--use-cas-prefix`
- `--max-cas-prefix-len 128`
- `--sample-every-steps 250` (rotated sample records per
  `feedback_rotating_sample_prompts_required.md`)

## Inference modifications

`cas-native/inference/routed_generate.py` already calls
`route_by_compilability()` to get the task. The integration adds
one line: when `use_cas_prefix=True` AND the model checkpoint was
trained with task tokens, prepend `[VALID]` / `[INVALID]` to the
cas_prefix tokens passed into `generate_reply`.

Implementation-wise: a single new param
`prepend_task_token: bool = False` on `routed_generate` (default
False so existing checkpoints still work). When True, `routed_generate`
asks the tokenizer for the right token id (per
`routing.task_type`) and passes it through to `generate_reply`,
which prepends it before tokenizing the CAS expression.

## Retraining plan

| Item | Value |
|---|---|
| Base checkpoint | v1 PREFIX128 5ep (`runs/v1_path_d_PREFIX128_5ep_20260509T035024Z`) — already on D: archive |
| Tokenizer | Extended from v1 tokenizer (`+[VALID]`, `+[INVALID]` at indices 38683, 38684) |
| Embedding warm-start | Copy `[TASK_EXPR]` → `[VALID]`; copy `[TASK_EXPLAIN]` → `[INVALID]` |
| Corpus | Existing `v1_mix_nlgen_train.jsonl`; collator injects task tokens at runtime |
| Hparams | Identical to v1 PREFIX128 5ep |
| Compute | RTX A6000 RunPod, ~80 min, ~$3-5 |
| Output | New checkpoint `v1_path_d_VALIDTOK_5ep_<timestamp>` |
| Re-eval | Same 24-record stratified sample (deterministic, directly comparable to commit `7c01609`) |

## Validation plan

The eval pack runner (`cas-synthetic/scripts/v1_eval_pack_24records.py`)
gets a one-line update: load the v1c tokenizer, point at the new
checkpoint, set `prepend_task_token=True` in the
`routed_generate` call. Same 24 records, same greedy decoding,
same human grading template.

Comparison metrics (per-record human grades + auto-filled
structural):

| Axis | v1 PREFIX128 5ep (baseline) | v1 VALIDTOK 5ep (target) |
|---|---|---|
| rpm_chain wrong-task hijacks | 3/3 (100%) | 0/3 (0%) target |
| Combined strong + acceptable bands | 12/24 (50%) | ≥18/24 (75%) target |
| Truncation, hard notation, jargon | 0 / 0 / 0 | 0 / 0 / 0 |
| Ω + coef + var recovery (post-repair) | unchanged from baseline | unchanged target |

If rpm_chain hijacks drop to 0/3 on the new run, Option C is
validated and we move to the next blocker (likely body-semantics
drift, separate from routing). If hijacks persist, the embedding
warm-start may have failed and we'd retry with random-init or
copy-from-different-anchor.

## Risks

1. **Embedding warm-start may not transfer cleanly.** If `[TASK_EXPR]`
   embeddings encode v0 artifacts that don't match the v1
   corpus expectations, warm-started `[VALID]` could pull the
   model into v0 behavior. Mitigation: train for 1 epoch, sample
   on a known rpm_chain val record, sanity-check before letting
   it cook for 5 epochs. If outputs look v0-shaped, restart with
   random init (also viable, just slower).
2. **Tokenizer mismatch on inference.** New tokenizer must be
   loaded for the new checkpoint. Old tokenizer + new checkpoint
   (or vice versa) silently corrupts. Mitigation: tokenizer hash
   in checkpoint manifest; loader asserts match.
3. **The body-semantics drift problem stays unfixed.** Option C
   is specifically a routing/silhouette fix. The seeded diagnostic
   showed body content drifts even when silhouette is right
   (drive labels, operator aliases). Option C does not address
   this. Anticipated: rpm_chain routes correctly post-Option-C
   but body content remains yellow-quality.
4. **Retraining variance.** A single retrain might land at a
   slightly different loss minimum. The 24-record audit is
   deterministic given greedy decoding, so any genuine improvement
   should be visible. Sample-size guards (the `feedback_real_metric_is_samples`
   discipline): grade per-record, not just aggregate.

## Out of scope for Option C

- Body-semantics drift (drive label, operator alias) — separate from routing
- Repetition stuttering — already caught by `count_adjacent_duplicate_words`
  and `count_repeated_phrase_windows` gates from commit `9282597`
- Coefficient gen-completeness ceiling — repair fills slots that exist; can't
  invent slots. Improvement comes from training scale, not Option C.
- Chat REPL wiring — held until v1c stability confirmed by the same
  20-30 record human grading bar.

## File-touch summary (when implementation lands)

| File | Change |
|---|---|
| `cas-native/training/tokenizer.py` | Append `[VALID]`, `[INVALID]` to `SPECIAL_TOKENS` |
| `cas-native/training/datasets/native_nl_collator.py` | Prepend task token to cas_prefix_ids based on `task_type` |
| `cas-native/training/train_native_nl_gen.py` | Embedding warm-start logic when loading from a smaller-vocab checkpoint |
| `cas-native/inference/routed_generate.py` | Add `prepend_task_token` flag (default False); pass through to `generate_reply` |
| `cas-native/inference/native_nl_generate.py` | Honor task-token prepend when consuming cas_prefix |
| `cas-synthetic/scripts/v1_eval_pack_24records.py` | Wire to new tokenizer + checkpoint + `prepend_task_token=True` |
| Tests | Per-file regression tests pinning the new behavior |

## Sign-off needed

Before implementation:
1. Confirm minimal-vocab approach (2 tokens, not 4)
2. Confirm warm-start direction (copy `[TASK_EXPR]` → `[VALID]` etc.)
3. Confirm Path A (collator-time injection) over Path B (corpus regen)
4. Confirm hparams unchanged from v1 PREFIX128 5ep
5. Confirm RunPod spend ~$5 within budget

Once confirmed, implementation lands as one bundled commit
(tokenizer + collator + trainer + inference + tests) followed by
retrain run + re-eval + report.
