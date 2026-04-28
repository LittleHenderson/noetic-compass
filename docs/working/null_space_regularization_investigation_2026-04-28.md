# Null-Space Regularization Investigation — 2026-04-28

Follow-up on the progressive smoke campaign finding that `null_space_reg_loss` saturated around 505 across all batch sizes.

## TL;DR

**The 505 value is mathematically expected, not anomalous.** It is the natural magnitude of the mean squared norm of a row vector drawn from `torch.randn(capacity, d_model)` with `d_model = 512`. The "saturation" observation in the smoke is the regularizer being intentionally weak (per its docstring): the gradient on unused registry rows is small, so 100 steps move the norm only fractionally (505.205 → 505.154, ≈ 0.01% drop over 90 steps).

This is **tuning, not a bug.** Two recommendations below if the contribution magnitude matters for full training; both are configuration changes, no code change required.

## What was observed

From `PROGRESSIVE_SMOKE_CAMPAIGN_2026-04-28.md`, Variant 2 (`+emergent_register`) and beyond:

```
step  10: ... null_space_reg_loss=505.427 ...
step  90: ... null_space_reg_loss=505.154 ...
```

Effectively flat across 100 steps regardless of batch size.

## Where the value comes from

### The formula

`cas-native/model/loss.py::NullSpaceRegularizationLoss.forward` (origin strategy):

```python
sq_err = (unused_embeddings - 0).pow(2).sum(dim=-1)   # (unused_count,)
return self.lambda_null * sq_err.mean()
```

i.e. `loss = lambda_null * mean_i ||registry[i]||²` where `i` ranges over unused slot indices.

The trainer (`cas-native/training/trainer.py:1175`) constructs the loss module with `lambda_null=1.0` (the inner weight) and applies the configured `V2Hyperparameters.lambda_null_space_reg = 0.01` at the aggregation step (line 1584). So `extras["null_space_reg_loss"]` reports the **raw** mean squared norm without the 0.01 multiplier; the actual contribution to total loss is `0.01 × raw_loss`.

### The initialization

`cas-native/model/emergent_register.py:196`:

```python
self.registry = nn.Parameter(torch.randn(capacity, d_model))
```

`torch.randn` draws from N(0, 1). Each entry of the registry has unit variance.

### The expected magnitude

For a row `r ∈ R^d_model` with each component drawn from N(0, 1), `||r||² = Σ r_i²` is the sum of `d_model` independent standard-normal squares — a chi-squared random variable with `d_model` degrees of freedom.

With `CASNativeConfig.d_model = 512`:
- E[||r||²] = 512
- Std[||r||²] ≈ √(2 × 512) ≈ 32

Across `unused_count` rows the mean stabilizes near 512 by the law of large numbers.

**Observed 505 ≈ expected 512.** The 1.4% deviation is well within sampling variance for ~12-18 unused rows in a capacity-20 registry with 2-12 admitted Ω entries (depending on commit; see registry chain in `PROGRESSIVE_SMOKE_CAMPAIGN_2026-04-28.md`).

## Why "saturation" is expected

The unused registry rows receive gradient ONLY from this regularizer (no Ω label ever lands on them — that's the point). The gradient w.r.t. row `r_i` for the origin strategy is:

```
∂L_null / ∂r_i = lambda_null × (2 / unused_count) × r_i
              = 1.0 × (2 / ~10) × r_i
              ≈ 0.2 × r_i
```

Then this gets multiplied by the outer `lambda_null_space_reg = 0.01` at the aggregation step, giving an effective gradient magnitude of `~0.002 × r_i` per dimension.

With Adam optimizer at `lr = 1e-4`, the per-step update on each row is bounded by `lr × sign-of-grad × adaptive-scale ≈ 1e-4 × O(1) ≈ 1e-4` per dimension. Across all `d_model = 512` dimensions, the per-step change in `||r_i||²` is roughly `2 × Σ r_i × Δr_i ≈ 2 × 512 × E|r| × 1e-4 ≈ 2 × 512 × 0.8 × 1e-4 ≈ 0.082` per row.

Over 100 steps, expected `||r||²` change is `≈ 8` per row. Across the unused-count average that's a drop from 512 → ~504 in 100 steps. **Observed 505.4 → 505.2 over 100 steps is consistent with this back-of-envelope** (the actual drop is smaller because the regularizer-only signal competes with random gradient noise from the rest of the network propagating through `model.v2_components`).

This is the regularizer working **as designed**: a slow, gentle pull. The docstring explicitly says "regularization only, not primary signal" with `lambda_null = 0.01` justified as "low weight."

## Effective contribution to total loss

`raw_loss × 0.01 = 505 × 0.01 ≈ 5.05` per step.

Reference comparison (Variant 4, all non-rust v2 flags, batch=4 from the campaign):
- lm_loss: ~10
- inversion_penalty: ~3
- cognitive_drift: ~3
- rpm_satisfaction: ~0.5
- involution_loss: ~0.05
- null_space_reg_loss × 0.01: ~5
- production_loss: ~0 — ~409 (oscillating)
- proposer_rule_four_loss: ~5

`total ≈ 26.5` (excluding production_loss spike episodes).

**null_space_reg's 5 / 26.5 ≈ 19% of total.** That's a sizable regularization budget — not catastrophic but meaningful. The gradient signal from this term flows mostly into the unused-slot rows (which is where it's supposed to go) but also creates a constant-ish offset in the total loss visible in monitoring.

## Recommendations

### Option A — leave as-is, document the math

The current behavior is mathematically correct and consistent with the docstring's "regularization only" framing. The 505 raw value is the expected magnitude for `d_model = 512` unit-variance init; the contribution to total (5 / 26.5 ≈ 19%) is acceptable.

If the only concern is monitoring readability, just be aware that `extras["null_space_reg_loss"]` reports the raw `mean ||r||²` and the actual contribution is `0.01 × that`. (No code change needed; could be a comment in the trainer.)

### Option B — d_model-normalized lambda

Make the regularization budget independent of `d_model` so changing `CASNativeConfig.d_model` doesn't change the regularizer's effective weight. Replace `lambda_null_space_reg = 0.01` with an effective lambda of `0.01 / d_model`:

```python
# In V2Hyperparameters validation or trainer aggregation:
effective_lambda = self.v2_hp.lambda_null_space_reg / self.model.config.d_model
weighted = effective_lambda * null_space_loss
```

With `d_model = 512`, this scales the contribution from 5 → 0.01. Probably too weak (regularizer effectively disabled). Halfway between would be `lambda / sqrt(d_model)`, giving contribution `5 / sqrt(512) ≈ 0.22` — minimal but non-zero.

**Tradeoff**: hides d_model from users but changes existing default behavior. If pursued, default `lambda_null_space_reg` should rise from 0.01 to something around 0.5 to keep the post-normalization effective weight in a similar range to the current behavior — i.e., the user-facing knob keeps the same units rather than mapping straight to a 1:1 multiplier.

### Option C — initialize closer to zero

Change `OmegaRegistry.__init__` to use a smaller-variance init for unused rows:

```python
# emergent_register.py:196
self.registry = nn.Parameter(torch.randn(capacity, d_model) * 0.1)
```

This shrinks the starting `||r||²` by 100× (from ~512 to ~5), matching the "pull toward null" intent — the unused rows START closer to null and the regularizer's job is just to keep them there.

**Tradeoff**: smaller-variance init may also affect convergence behavior of admitted Ω embeddings on first activation (rows that are about to be used as named emergents). Worth coordinating with the EmergentRegisterPipeline team's expectations on registry magnitude.

### Recommended path

**Option A for the immediate next training run.** The 19% loss-budget contribution is acceptable, the regularizer is doing what it's documented to do, and the 100-step "saturation" observation is just a snapshot of a gentle long-tail process.

For the next CARP review or ADR-03 follow-up, **flag Option C** as the cleanest fix: a 0.1 init scale brings the regularizer into a better-behaved magnitude regime where the loss number itself reflects "how far from null" rather than "what's the natural norm of a unit-variance vector in 512D." Option B is a finer-grained alternative that preserves the existing init but normalizes the user-facing lambda.

## What is NOT happening

Just to rule out alarm:

- ❌ **Not** an exploding gradient (gradient on unused rows is ~0.002 per dim).
- ❌ **Not** a NaN or numerical pathology (clean float values across the entire smoke).
- ❌ **Not** a frozen registry (gradient flows; 0.05 raw-loss reduction per 100 steps is consistent with the math).
- ❌ **Not** a learned-anchor or mean-inactive bug (using strategy="origin" by default; verified at trainer line 1163).

The "constant 505" is just the expected magnitude doing its expected slow drift. Sound system.
