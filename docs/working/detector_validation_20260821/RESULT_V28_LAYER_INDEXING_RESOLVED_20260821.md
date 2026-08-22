# V28 — Layer indexing RESOLVED: `L0` is the output of transformer block 0, not the embeddings

**Date:** 2026-08-21 · **$0**, no GPU, code+runtime inspection.

## Why this mattered
v25 (`1.000`), v26 (`1.000`) and v27's weak `0.625` all peaked at **`L0`**, and every write-up carried a standing caveat: *"if `L0` denotes the state after the first transformer block, one attention pass suffices — real binding but shallow; confirm the engine's layer indexing before any 'deep structure' language."* That caveat is now **closed**.

## What was checked
- `engine.py:179` — `layer_count = len(adapter.residual_paths)`.
- `adapter_binding.py:87-109` — residual hooks are built by enumerating `discovery.layer_hooks`, one `residual_module` per layer, each verified `register_forward_hook`-able.
- **Live runtime resolution** (`pythia-160m`, attested load):
  - `layer_count = 12`
  - `residual_paths[0] = gpt_neox.layers.0`
  - `residual_paths[1] = gpt_neox.layers.1`
  - `residual_paths[11] = gpt_neox.layers.11`

## Verdict
**`L0` = `gpt_neox.layers.0` = the OUTPUT of the first transformer block.** It is **not** the embedding layer. There is no `embed_in` entry in `residual_paths`; index 0 is already post-attention, post-MLP for block 0.

## Consequences for the standing results

**1. The v25/v26 results are NOT an embedding artifact — this strengthens them.**
A pure-embedding explanation would have been fatal: with identical tokens at identical positions, the last-token embedding of A and B would be *identical*, so any separation would have been an artifact. That explanation is now **ruled out** — self-attention has run before the capture, so the final position has legitimately attended to the differing tokens earlier in the sequence. The binding signal is real.

**2. "Shallow" is confirmed, not merely suspected.**
One attention pass is sufficient to move the marker/role information to the final position. So the licensed wording stays: **binding, not deep multi-layer composition.** Any future "deep structure" phrasing remains **unlicensed**.

**3. It sharpens the v27 null.**
The speaker-binding null is now a null *after* a full attention pass, not a null at the embeddings — i.e. the model had the mechanism available and still did not encode the speaker→instruction binding. That makes the null stronger evidence, not weaker.

## Claim state
- **Real:** live runtime resolution of the adapter's residual paths, `$0`.
- **RESOLVED and closed:** the `L0` indexing caveat on v25, v26, v27.
- **Licensed wording unchanged:** binding is real and shallow (one attention pass suffices); deep multi-layer composition remains **NOT LICENSED**.
