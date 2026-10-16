# R1-RT — design, appendix B: the output rule, frozen and verified

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** DESIGN, APPENDIX. This freezes
the second and last piece parts one and two left open: how the brain's symbol becomes the tensor the
runtime will read. It runs nothing, changes no package, spends nothing.

## The decoder we must satisfy, exactly

`semantic.py:103-126`, five steps in this order:

1. the effect must be a real `torch.Tensor`, floating-point, finite, non-empty;
2. `effect.shape[-1]` must equal `contract.effect_width`, which for v2 is `input_width`;
3. `logits = effect.mean(dim=all leading dimensions)`;
4. for v2, `logits = logits[channel_indices]` — and `__post_init__` requires
   `len(channel_indices) == len(labels)`, the indices **distinct** and each in `range(input_width)`;
5. **if every element of the effect is exactly zero → `zero_symbol` (`NO_EFFECT`), which is not an
   answer**; otherwise `argmax` over the selected logits, **lowest index wins ties**.

Measured elsewhere and reused here: eight labels, `channel_indices = (0,…,7)`, `input_width = 64`,
and the frozen v2 algorithm string `MEAN_SELECTED_LOGIT_ARGMAX_LOWEST_INDEX_V2`.

## The rule, frozen

```
Let L = 8 (the labels), W = 64 (the effect width), N = 8 (rows),
    k = the index of the answer label, 0 <= k < L,
    C = a positive constant whose float32 representation is not zero.

Build one effect of shape [1, N, W]:

  for every row n in 0..N-1 and every channel c in 0..W-1:   effect[0][n][c] = C
  then set                                                    effect[0][0][k] = C + 1

Return the wrapped proposal with that effect as candidate_effect.
```

**Why each clause is there:**

| clause | what it guarantees |
|---|---|
| every channel set to `C` first | the effect is **never all-zero**, so the runtime's zero trap at `semantic.py:120` cannot fire — this is the clause that answers `RT_ZERO_TRAP` |
| `+1` at channel `k` of row 0 only | after the mean over all 8 rows, channel `k` reads `C + 1/8` while the other seven answer channels read exactly `C`, so the argmax selects `k` |
| the other seven rows left flat | the signal is carried on one row and the mean spreads it exactly once; repeating it on every row would make channel `k` read `C + 1` while the others read `C`, which also works but changes nothing except the margin — flat rows keep the arithmetic inspectable |
| `C > 0` and representable in float32 | a `C` that underflows to zero in float32 would make the all-zero test fire. See the boundary table below |
| channels 8–63 all `C` | they are never selected by `channel_indices`, but they must not be zero, or the trap returns |

## The verification

Two checks, both run before this document was written.

**Check 1 — the rule against a faithful model of the decoder.** A pure-python model of the five
steps above (mean over leading dimensions, slice the eight channels, all-zero test, argmax with
lowest index on ties), with no torch:

| `C` | all eight labels decoded correctly |
|---|---|
| 0.5 | 8 of 8 |
| 1.0 | 8 of 8 |
| 3.0 | 8 of 8 |
| 0.001 | 8 of 8 |

**32 of 32 combinations correct.** And the trap, demonstrated on the same model: the naive all-zero
encoding decodes as **`NO_EFFECT`**, not as any answer — which is exactly the failure the rule
exists to prevent.

**Check 2 — the boundary of `C`.** The trap tests **exact** zero, so any positive `C` that float32
can represent defeats it. Checked with a real float32 view (`struct.pack("f", …)`), not with
Python's float64:

| `C` | float32 view | all-zero effect | safe |
|---|---|---|---|
| `1e-7` | `1e-07` | no | yes |
| `1e-30` | `1e-30` (a subnormal) | no | **yes** |
| `0` | `0` | **yes** | no |
| below about `1.4e-45` | `0` | **yes** | no — the only unsafe region |

**A correction to this appendix's own first draft.** It said `1e-30` underflows to zero in float32
and is therefore unsafe. **That was wrong**, and the checking script caught it: `1e-30` is a
subnormal float32 and survives, and the script's first version reported it as safe for a *different*
reason — it was modelling float32 with float64. The script now takes a real float32 view, and the
corrected statement is above: the unsafe region is only values that round to zero, below roughly
`1.4e-45`. The conclusion is unchanged — **`C = 1.0` is safe** — but the reason is stated correctly.

**`C` is frozen at `1.0`.** It is the simplest positive constant that is exactly representable, it
keeps the arithmetic readable, and it leaves the margin at exactly `1/8` after the mean. The
boundary above is recorded so that a later reader does not have to re-derive where the danger is.

## What this rule does not decide, and must not be read as deciding

- **It does not decide the answer.** It transports a symbol the brain already produced. `k` comes
  from the recipe brain's own `min(stock/requirement)`; the encoder reads it and writes it down.
  That is what `RT_SHIM_NO_MATH` checks.
- **It does not make the effect meaningful to the runtime's own learning.** A one-hot-plus-constant
  effect is a legitimate decoder input and a meaningless gradient target. Under shape 2, where the
  shim sits inside the runtime's process, the design must state that **no teaching tick is run
  against a bridged brain** — a rule, not a hope, because feeding that tensor to `GovernedLearner`
  would "teach" a neural module to imitate a decision rule.
- **It does not claim the runtime will like it.** Whether any *other* runtime check rejects this
  effect is unmeasured. The run measures it, which is why `A1_HOSTED` is the arm and the rest are
  controls.

## Both free pieces are now frozen

Appendix A froze the input rule and proved it against the runtime's own oracle on 118,304 cases.
This appendix freezes the output rule and verified it on 32 label × constant combinations plus the
trap and the boundary.

**What remains before a run:** the run envelope (machine, window, cost) — free to write — and the
owner's shape choice, which is not an agent's to make.
