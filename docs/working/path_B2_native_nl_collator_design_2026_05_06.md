# Path B-2 Design — NativeNLCollator + Masked-CE Loss + Training Wiring

**Author:** Claude
**Status:** v2 — revised 2026-05-06 after Codex audit
**Scope:** Bridge between training script's record stream and `CASNativeModel.forward_with_lm()` (NOT `NLGenerationHead.forward` directly).
**Goal:** Make `python -m cas_native.training.train_native_nl_gen` build a full `CASNativeModel`, attach `NLGenerationHead` via `attach_nl_gen_head()`, and run real generation training end-to-end on Codex's Tier 3 dialogue records.

---

## 0. Codex audit corrections from v1

v1 had three substantive errors and three smaller fixes. All accepted, design rewritten around them:

1. **`forward_with_lm()` already exists** at `cas_native_model.py:656`. It already routes `pooled_hidden_state` → `bottleneck_z`, `hidden_states` → `encoder_outputs`, `attention_mask` → `domain_mask`. v1's proposed `encode()` helper duplicated this. REMOVED.
2. **Trainer doesn't build the encoder.** `train_native_nl_gen.py:162-210` only builds the head. v1's "swap collator, call head directly" cannot work — no encoder, no `bottleneck_z`, no `encoder_outputs`. The trainer must build `CASNativeModel`, attach the head, and call `forward_with_lm()`. REWRITTEN.
3. **d_model defaults already match at 512** (`cas_native_model.py:61`, `nl_generation_head.py:87`). The 64→512 projection concern was false. Enforce matching d_model at construction; add a guard, no projection.
4. **Real path fails loudly, not silently.** Real head loads cleanly today. Trainer fails at the call site with a TypeError once the real head is wired. Fallback stays only behind explicit `--use-fallback-head` (or `--smoke-test`).
5. **Tokenizer split.** English-BPE extended tokenizer for prompt and reply text. `HybridCASTokenizer` for the CAS expression only, with `add_special=False` to avoid double BOS/EOS.
6. **`loss_structured` defined or zeroed.** v1 wrote `α·L_struct + β·L_lm` without sourcing `L_struct`. v2: `α=0` for the first bridge (pure LM loss). Structured loss is wired separately in a follow-on step from `CASNativeModel.forward()` outputs against label targets.
7. **`domain_mask` is encoder attention validity**, not a semantic CAS domain mask. Pass `attention_mask` (1 over real prompt tokens, 0 over pad) to the head. v1 §8.3 followup ("derive from CAS Domain field later") REMOVED.

---

## 1. Current state (as of 2026-05-06)

### 1.1 What the existing bridge does (`cas_native_model.py:646-748`)

`CASNativeModel` already exposes the full bridge:

```python
def attach_nl_gen_head(self, head: nn.Module) -> None: ...

def forward_with_lm(
    self,
    input_ids: torch.Tensor,                    # encoder input (B, S)
    lm_decoder_input_ids: torch.Tensor,         # decoder input (B, L)
    *,
    attention_mask: Optional[torch.Tensor] = None,
    register_activations: Optional[torch.Tensor] = None,
    cas_prefix_ids: Optional[torch.Tensor] = None,
    register_id: Optional[torch.Tensor] = None,
    bottleneck_z: Optional[torch.Tensor] = None,
    return_lm_meta: bool = False,
) -> dict[str, torch.Tensor]:
    """Runs forward() then the attached head. Returns the full forward()
    output dict plus `lm_logits` (and optionally `lm_meta`)."""
```

Internally it calls `self.forward(input_ids, attention_mask, register_activations)`, then routes `pooled_hidden_state[:, :bottleneck_dim]` → `bottleneck_z` (with zero-pad if `d_model < bottleneck_dim`), `hidden_states` → `encoder_outputs`, `attention_mask` → head's `domain_mask`. The trainer doesn't need to know the head's internal contract — it just needs to feed `forward_with_lm` correctly shaped inputs.

### 1.2 What the trainer emits today (`train_native_nl_gen.py:162-210, 597-632`)

- `_build_nl_generation_head` instantiates the real `NLGenerationHead` if importable, else falls back. Real path loads cleanly today.
- `_records_to_batch` is a thin passthrough that expects `record["input_ids"]` and `record["target_ids"]` to already be present. No tokenization happens. This is what gets replaced.
- The trainer never instantiates `CASNativeModel`. There is no encoder. The structured-loss path the loop currently runs uses a `_FallbackNLGenerationHead.forward(input_ids, target_ids, struct_targets)` that returns its own `lm_loss` + `structured_loss`. That contract does NOT match the real head.

### 1.3 Codex's Tier 3 dialogue record shape

```json
{
  "id": "...", "trace_id": "...", "schema_version": "native_nl.v1",
  "tier": "tier3", "conversation_id": "...", "turn_index": 0, "turn_count": 6,
  "cas_expression": "^2^E_{F6}|f",
  "noetic": "^2", "domain": "E", "drive": "F6", "register": "f",
  "register_set": ["f"], "expression_family": "base",
  "topic": "...", "demographic_profile": "lay_casual", "tone": "neutral",
  "prompt": "...", "prompt_text": "...",
  "reply": "...", "reply_text": "...",
  "validator_pass": true, "validator_reasons": [],
  "round_trip_validator": "deferred",
  "generation_version": "native_nl_tier3_dialogue_v1"
}
```

---

## 2. Design

### 2.1 New file: `cas-native/training/datasets/native_nl_collator.py`

```python
class NativeNLCollator:
    """Convert Tier 3 dialogue records into a forward_with_lm()-shaped batch.

    Tokenization sources:
      - English-BPE extended tokenizer for prompt_text and reply_text
      - HybridCASTokenizer for cas_expression, add_special=False

    Outputs match what CASNativeModel.forward_with_lm() needs as kwargs.
    """

    def __init__(
        self,
        text_tokenizer,            # English-BPE extended tokenizer
        cas_tokenizer,             # HybridCASTokenizer for CAS expressions
        *,
        max_prompt_len: int = 256,
        max_reply_len: int = 256,
        register_to_id: dict[str, int] | None = None,  # default {T:0,A:1,f:2,E:3}
    ): ...

    def __call__(self, records, *, device) -> dict | None: ...
```

### 2.2 Output dict (consumed by trainer)

```python
{
    # forward_with_lm() positional + keyword args:
    "input_ids":            Tensor[B, S_prompt],   # encoder input — prompt tokens
    "attention_mask":       Tensor[B, S_prompt],   # 1=valid, 0=pad
    "lm_decoder_input_ids": Tensor[B, L_dec],      # [BOS, reply[:-1]], pad=pad_id
    "cas_prefix_ids":       Tensor[B, K],          # CAS tokens, no special tokens
    "register_id":          Tensor[B],             # long, [0, 4)

    # For loss computation only — not passed to forward_with_lm:
    "lm_targets":           Tensor[B, L_dec],      # reply_ids (shifted), pad target = -100
    "loss_mask":            Tensor[B, L_dec],      # bool, True over reply token positions

    # Provenance pass-through:
    "record_ids":           list[str],
    "trace_ids":            list[str],
}
```

The trainer maps these into the call:

```python
out = model.forward_with_lm(
    batch["input_ids"],
    batch["lm_decoder_input_ids"],
    attention_mask=batch["attention_mask"],
    cas_prefix_ids=batch["cas_prefix_ids"],
    register_id=batch["register_id"],
)
loss = masked_cross_entropy(
    out["lm_logits"], batch["lm_targets"], batch["loss_mask"]
)
```

### 2.3 Decoder-input + targets (right-shifted teacher forcing)

```
reply_ids   = [t1, t2, t3, t4, EOS]
dec_input   = [BOS, t1, t2, t3, t4]                # right-shifted
lm_targets  = [t1, t2, t3, t4, EOS]                # un-shifted

# After padding:
dec_input   = [BOS, t1, t2, t3, t4, PAD, PAD]
lm_targets  = [t1, t2, t3, t4, EOS, -100, -100]
loss_mask   = [1, 1, 1, 1, 1, 0, 0]
```

CAS-prefix logits are stripped internally by the head (per `nl_generation_head.py` docstring), so output `lm_logits` is `(B, L_dec, V)` matching `lm_targets` shape.

### 2.4 Tokenizer split + special-token policy

- **English-BPE extended tokenizer** (`cas_native.training.english_bpe_extension`) for prompt and reply.
  - prompt: encode WITHOUT BOS/EOS; pad to max_prompt_len; build attention_mask from non-pad positions.
  - reply: encode WITH EOS appended; build `lm_decoder_input_ids = [BOS] + ids[:-1]` and `lm_targets = ids` (or simply build the shifted pair explicitly to control where BOS/EOS land).
- **HybridCASTokenizer** for `cas_expression`, `add_special=False`. CAS literal tokens (e.g., `^3`, `^E`, `_{F6}`, `|f`) live at reserved low IDs; encode them directly, no BOS/EOS.

Single source of truth for BOS/EOS/PAD constants: pull from the English-BPE tokenizer's special-tokens table at collator init; assert they are integers ≥ 0; never hardcode.

### 2.5 register_id parsing

```python
DEFAULT_REGISTER_TO_ID = {"T": 0, "A": 1, "f": 2, "E": 3}
```

From `record["register"]`. Unknown/missing → 0 with a debug log line, no exception (records are validator-passed upstream so this should be rare).

### 2.6 What the collator does NOT do

- No structured-prediction targets. v1 wired `struct_targets`. v2 drops them — the structured loss path is rebuilt as a separate change after the LM bridge works.
- No domain mask synthesis. Encoder padding mask is used directly as `attention_mask` (which `forward_with_lm` forwards to the head's `domain_mask` parameter). No semantic CAS-domain masking.
- No projection / linear adapters. d_model matches by construction.

---

## 3. New file: `cas-native/training/masked_ce_loss.py`

```python
def masked_cross_entropy(
    logits: torch.Tensor,                  # (B, L, V)
    targets: torch.Tensor,                 # (B, L), -100 ignored
    mask: torch.Tensor | None = None,      # (B, L) bool; if None use targets!=-100
    reduction: str = "mean",               # "mean" | "sum" | "none"
    label_smoothing: float = 0.0,
) -> torch.Tensor:
    """Reply-only LM loss. Prompt and CAS-prefix positions never enter logits
    here (the head strips CAS-prefix logits internally; prompt is encoder-side)."""
```

Implementation: `F.cross_entropy(logits.view(-1, V), targets.view(-1), ignore_index=-100, reduction=reduction, label_smoothing=label_smoothing)`. Mask param accepted explicitly for intent-clarity even though `-100` does the work.

---

## 4. Trainer changes (`train_native_nl_gen.py`)

### 4.1 Build full CASNativeModel + attach head

Replace the head-only construction with:

```python
from cas_native.model.cas_native_model import CASNativeModel, CASNativeConfig
from cas_native.model.nl_generation_head import NLGenerationHead, NLGenerationHeadConfig

cas_cfg = CASNativeConfig(d_model=512, ...)         # or load from manifest
model = CASNativeModel(cas_cfg).to(device)

head_cfg = NLGenerationHeadConfig(vocab_size=tokenizer.vocab_size, d_model=512, ...)
head = NLGenerationHead(head_cfg).to(device)

# Hard guard from Codex audit fix #3:
if model.config.d_model != head.config.d_model:
    raise ValueError(
        f"d_model mismatch: CASNativeModel={model.config.d_model}, "
        f"NLGenerationHead={head.config.d_model}. Match them at construction."
    )

model.attach_nl_gen_head(head)
```

When `--use-fallback-head` or `--smoke-test` is passed: skip CASNativeModel construction, build only `_FallbackNLGenerationHead`, take the legacy `forward(input_ids, target_ids, ...)` path. Two clearly-separated branches; no silent fallback.

### 4.2 Replace `_records_to_batch` with `NativeNLCollator`

```python
collator = NativeNLCollator(text_tokenizer=text_tok, cas_tokenizer=cas_tok)

for batch_records in dataloader:
    batch = collator(batch_records, device=device)
    if batch is None:
        continue

    out = model.forward_with_lm(
        batch["input_ids"],
        batch["lm_decoder_input_ids"],
        attention_mask=batch["attention_mask"],
        cas_prefix_ids=batch["cas_prefix_ids"],
        register_id=batch["register_id"],
    )

    loss_lm = masked_cross_entropy(
        out["lm_logits"], batch["lm_targets"], batch["loss_mask"]
    )

    # First bridge: structured loss weight = 0.
    loss_total = loss_lm

    loss_total.backward()
    optimizer.step()
    ...
```

### 4.3 Trace surface preserved

`forward_with_lm(..., return_lm_meta=True)` returns `lm_meta` (per-token attention attributions, layer activations). When `--trace-mode=full` is set, dump per-record `GenerationTrace` rows with the metadata, keyed by `record_ids` and `trace_ids` from the collator. Mode 7 surface is unchanged — same structure, now populated with real model values.

### 4.4 train_progress logging preserved

Per durable rule, batches 1, 3, 5 of epoch 0 always-print, then every `--train-log-every-steps N`. Fields unchanged. Adds `lm_loss` to the JSON; structured loss fields nulled until structured path is wired.

### 4.5 Hparam baselines

For full runs (not smokes), explicit `--lr`, `--batch-size`, `--weight-decay` always passed. v1 didn't define generation-side baselines yet; first real run will set them and they get added to the durable rule.

---

## 5. Tests (`cas-native/tests/training/test_native_nl_collator.py`)

12 tests:

1. Single-record collator output: 9 fields present, correct shapes, dtypes.
2. Right-shifted decoder: `lm_decoder_input_ids[i, 0] == BOS`, `[i, j] == reply_ids[i, j-1]`.
3. Loss mask correctness: 1 over real reply tokens, 0 over pad.
4. CAS prefix uses no special tokens (BOS not at position 0).
5. Register parsing happy path: `"f"` → `2`.
6. Register parsing fallback: missing → `0`, no exception.
7. Padding correctness across mixed-length batch.
8. attention_mask matches input_ids non-pad positions exactly.
9. Provenance pass-through: record_ids and trace_ids preserve order.
10. Tokenizer-mismatch rejection: passing wrong tokenizer object raises clearly at __init__.
11. d_model guard at trainer level: head and model with mismatched d_model raises.
12. Smoke step on CPU with random-init `CASNativeModel` + `NLGenerationHead` at small d_model (e.g., 32, both sides): 4 records, 1 forward+backward, finite loss, gradients flow into both encoder and head.

Plus 4 tests for `masked_cross_entropy` (`test_masked_ce_loss.py`):

13. Mask of all 1s reduces to standard CE.
14. `-100` in targets is ignored.
15. All-masked input returns finite (0 or NaN-protected) loss.
16. Label smoothing changes loss vs no smoothing.

---

## 6. Rollout sequence

1. **This v2 doc reviewed.** No code commits yet.
2. Read `cas-native/training/english_bpe_extension.py` and `tokenizer.py` to confirm the exact special-token API and choose the prompt/reply tokenizer instance correctly.
3. Implement `NativeNLCollator` + tests on CPU.
4. Implement `masked_cross_entropy` + tests.
5. Patch `train_native_nl_gen.py`:
   - Real path: build CASNativeModel + attach head + use `forward_with_lm`.
   - Fallback path: gate behind `--use-fallback-head`. Real path raises clearly if anything is missing rather than silently downgrading.
6. CPU smoke at small d_model (32 both sides) on 4 of Codex's Tier 3 records. Verify 1 step produces finite loss, gradients flow.
7. Single commit: `feat: B-2 — NativeNLCollator + forward_with_lm wiring + masked CE`. Includes all tests passing.

Effort: ~half a day focused work. No GPU. ~250 LOC code + ~200 LOC tests + trainer patch.

---

## 7. Risks + open questions

### 7.1 Tokenizer instance selection

Need to confirm at implementation time:
- Whether English-BPE extended tokenizer is a separate object or a mode of `HybridCASTokenizer`.
- Whether prompt and reply share the same vocab (must) or separate vocabs (rules out a single LM head).
- The exact special-token constants and whether `add_special=False` is the API or a different flag.

If the extended-vocab tokenizer turns out to be `HybridCASTokenizer` with English BPE merges added (single object, single vocab), §2.4 simplifies to "one tokenizer, two encode calls with different `add_special` settings."

### 7.2 NLGenerationHead initial seed sensitivity

Random-init head against a structured-pretrained encoder may produce very loud loss curves on the first few steps. Not a correctness issue; expected. Logged in `train_progress` so we see it.

### 7.3 sequence length budgets

`NLGenerationHead.max_len = 512`. Decoder stream is `[CAS prefix | reply]`. With CAS expressions averaging ~10-15 tokens and replies capped at ~60-80 BPE tokens, plenty of headroom. Cap reply at `max(50, 512 - K - 8)` defensively in collator.

### 7.4 Structured loss reattach

After the LM bridge stabilizes, wiring the structured loss back means computing it from `out["logits"]` (existing classifier head) + `out["cognitive_state"]` + provided structured targets, then summing with `loss_lm` at a tunable α. Not B-2 scope; tracked as B-2.5 follow-on.

### 7.5 Inference path for B-4

B-4 will need an inference helper on top of `forward_with_lm` that supports greedy/beam decoding. The training collator builds teacher-forced inputs. A separate `generate()` helper reuses the encoder pass + iteratively samples decoder tokens. Out of B-2 scope; designed in B-4.

---

## 8. What this does NOT do

- Does not run training — that's B-3, after Tier 3 SDG scales.
- Does not change `NLGenerationHead` or `CASNativeModel` architecture.
- Does not add an inference-time `generate()` helper.
- Does not wire structured loss — first bridge is LM-only.
- Does not commit anything until you sign off on v2.

---

## 9. Decisions needing your call before implementation

1. **v2 reads OK?** Codex's six audit points are all incorporated. Anything still missing or thin.
2. **English-BPE tokenizer location.** Authorize me to read `cas-native/training/english_bpe_extension.py` and `tokenizer.py` next to confirm §2.4.
3. **Smoke d_model.** 32 on both sides for the unit test. OK or prefer different.
4. **First-bridge structured loss = 0.** Confirm it's fine to ship the bridge with α=0 and re-wire structured loss as a B-2.5 follow-on, vs requiring it in B-2.
5. **Fallback flag name.** `--use-fallback-head` and `--smoke-test` both gate it. Prefer one or both.

End of v2.
