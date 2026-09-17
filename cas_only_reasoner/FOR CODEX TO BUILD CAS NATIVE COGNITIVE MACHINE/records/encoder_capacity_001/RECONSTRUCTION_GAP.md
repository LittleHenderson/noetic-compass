# The reconstruction gap: what was eliminated, and why it cannot be closed here

**Record:** `records/encoder_capacity_001/`
**Scripts:** diagnostics run inline this round; the durable artifacts are the two facts below and
`recurrence_collapse.txt` from the previous round.
**Spend:** $0.00. No GPU work. No AWS. `torch` used only to deserialise checkpoints.

---

## Why this was attempted

`measure_recurrence_collapse.py` (previous round) rebuilt the learner's whole forward pass in
pure Python and got 15 distinct aliases with `W8` at 18.3% where the record shows 9 with `W36` at
44.3%. It did not reproduce. That number was used to help refute a "collapse" mechanism, so the
gap matters: either the rebuild is wrong, or the record is.

## Finding 1 — the encoder material is byte-identical to the recorded run

The worker recorded its frozen encoder identity in `encoding_checks.json`. Rebuilding the same
identity locally from `worker_contract.load_material` gives an **exact match on every field**:

| field | recorded | match |
|---|---|---|
| `identity_digest` | `a00930c51a06adc88ad0194b0439c076a2ddd7096eb8329be5ffc4d4935fc68b` | **exact** |
| `projection.sha256` | `4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9`, shape `[3829, 64]` | **exact** |
| `readout.sha256` | `14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667`, shape `[90, 64]` | **exact** |
| `tokenizer_digest` | `5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798` | **exact** |
| `seed`, `d_model` | `20260916`, `64` | **exact** |

So the projection rows, the readout rows, the tokenizer and the seed are not the difference. The
inputs to the rebuild are right.

## Finding 2 — the reference encoder refuses to run here, and cannot

`encoder.build_frozen_typed_encoder` raises **`TYPED_ENCODER_CUDA_ONLY`** when asked for a CPU
device:

```
_device(torch, device): _require(re.fullmatch(r"cuda(?::[0-9]+)?", name) is not None,
                                 "TYPED_ENCODER_CUDA_ONLY")
```

The installed runtime is `torch 2.11.0+cpu` with `torch.cuda.is_available() == False` and
`device_count() == 0`.

**So the reference encoder cannot be executed in this environment on any device.** That is the
guard working as designed — it fails closed rather than silently falling back — and it means the
rebuild **cannot be validated here at all**. Closing the gap needs a CUDA environment, and
launching GPU work needs an owner record, which does not exist.

## Finding 3 — the rebuild reaches 78% of the recorded structure, not 100%

On one `context` question with a 64-alias slot, comparing my pure-Python logit vector against the
recorded `scores` for the same slot (the recorded `scores` field *is* the logit vector — see
below):

| | mean | sd | min | max |
|---|---:|---:|---:|---:|
| mine | +0.061979 | 0.867230 | −1.772876 | +1.708160 |
| recorded | −0.097628 | 0.712338 | −1.722596 | +1.308992 |

**Correlation +0.781143.** Comparable scale, substantial shared structure, and the top-1 differs
(mine `W58`, recorded `W49`).

At slot level the rebuild agreed with the recorded decisions on **5 of 14** slots — the binary
slots mostly matched and the 64-way slots did not, which is what a ~0.78 correlation predicts.

**The recorded `scores` are the logits.** `_forward` stores
`scores = {slot_id: {symbol: float(logits[i])}}` directly, and the recorded `selected` is the
argmax of the recorded `scores` in every case checked. So this comparison is against the actual
pre-argmax quantity, not a derived one.

**The remaining difference is unfound.** Eliminated by reading the source line by line: the
projection and readout material (Finding 1); the token indices (`compile_packet` returns
vocabulary indices, `projection_bytes` builds rows in `tokenizer.vocabulary` order); the row
binding (`gather` then `mul(signs)` then `sum(dim=0)` then `normalize`, matched exactly); the row
and packet normalisation (the `/sqrt(count)` and `/sqrt(rows)` are absorbed by the trailing
`normalize`); the slot encoding (`normalize((packet + query)/sqrt(2))`); the block
(`merge @ concat(tanh(left x), tanh(right x))`, and `linear_weight_mode` defaults to
`"standard"`, so the layers are plain `nn.Linear`); the recurrence (`lambda_ = 0.5`,
`epsilon = 1e-6`, `depth = 8`, `reinjected`/`feedback` matched term for term); the checkpoint
(`final.pt`, cursor 160, matching `model_revision: 160` on every recorded prediction).

## Finding 4 — the recurrence is neither chaotic nor amplifying

Measured on the same slot by perturbing the encoded vector by a relative amount and re-running
the pass:

| perturbation | depth 1 | depth 2 | depth 4 | depth 8 |
|---|---|---|---|---|
| 1e-6 | cos +1.00000, no flip | +1.00000, no flip | +1.00000, no flip | +1.00000, no flip |
| 1e-4 | +1.00000, no flip | +1.00000, no flip | +1.00000, no flip | +1.00000, no flip |
| 1e-2 | +0.99993, no flip | +0.99996, no flip | +0.99996, no flip | +0.99996, no flip |
| 1e-1 | +0.99221, no flip | +0.99514, no flip | +0.99533, no flip | +0.99506, **flip** |

A **10%** change in the input moves the logit vector by cos 0.995. And the logit scale settles
after two passes and then barely moves:

| depth | 1 | 2 | 4 | 8 |
|---|---:|---:|---:|---:|
| logit sd | 0.47975 | 0.83679 | 0.86503 | 0.86723 |

**Two consequences.** First, float32-versus-float64 round-off **cannot** explain a correlation of
0.78 — the system is not an amplifier, so round-off stays round-off. The difference is structural
and mine. Second, the registered recurrence is **numerically stable**: it does not turn small
input differences into different answers, and depths 2, 4 and 8 give materially the same logits.

## What this does to the previous round's refutation

The refutation of the "collapse" mechanism rested on three checks. Only the third used the
rebuild, and it was supporting evidence rather than the load-bearing part:

| check | depends on the rebuild? | status |
|---|---|---|
| the weights **grew** — effective linear operator norm 0.361559 → 7.135410, ×19.73 | no — read from `initial.pt` and `final.pt` | **stands** |
| the trained block is **more** input-sensitive — mean pairwise cosine 0.563576 → 0.491361, rms-from-mean 0.028791 → 0.280260 | no — `block_forward` is two lines read from `cas_cjt/neural.py`, applied to the saved weights | **stands** |
| a rebuilt forward pass gives 15 distinct aliases | **yes** | **downgraded; supporting only** |

So the collapse refutation stands on rebuild-independent evidence. The third check is now labelled
for what it is — a 78%-correlation approximation — and is not relied on.

## What is NOT established here

- **The rebuild is not validated and must not be treated as the machine.** It reaches +0.781
  correlation with the recorded logits. Every number derived from it is approximate and is
  labelled as such.
- **The cause of the recorded alias concentration remains open.** This round narrowed where it is
  *not* — not in the encoder material, not in round-off, not in recurrence amplification — and did
  not find where it is.
- **The gap cannot be closed in this environment.** The reference encoder is CUDA-only by an
  explicit fail-closed guard and the installed torch is CPU-only. Closing it needs an
  owner-authorised CUDA environment.
- **No GPU work was launched**, locally or otherwise. The local device is not available to this
  runtime and the standing rule requires an owner record regardless.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`.
