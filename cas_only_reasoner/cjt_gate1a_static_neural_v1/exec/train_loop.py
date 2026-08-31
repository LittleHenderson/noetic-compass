"""train_loop.py -- the FROZEN head-training loop (Gate 1B jobs only).

Frozen hyperparameters (STATIC_CONDITIONS): AdamW lr 1e-3, betas (0.9, 0.999),
weight_decay 0.01, cosine decay with 5% linear warmup, batch 32, EXACTLY 3000
updates, gradient clip 1.0, fp32 heads over cached fp16 activations, NO early
stopping. Guarded: require_gpu() is the FIRST statement -- no CPU fallback.

Split law: this entry accepts TRAIN examples only (validation is read for
monitoring curves, never for stopping). Protected examples can never reach it:
dataset_assembly refuses them, and this entry re-refuses by split field.
"""
from __future__ import annotations

try:
    from exec.gpu_guard import require_gpu
    from exec.arms import build_arm_head
except ImportError:
    from gpu_guard import require_gpu
    from arms import build_arm_head

UPDATES, BATCH, LR, BETAS, WD, WARMUP_FRAC, CLIP = 3000, 32, 1.0e-3, (0.9, 0.999), 0.01, 0.05, 1.0


def lr_lambda(step: int) -> float:
    """5% linear warmup then cosine decay to 0 at UPDATES (frozen schedule)."""
    import math
    warm = int(UPDATES * WARMUP_FRAC)
    if step < warm:
        return (step + 1) / warm
    t = (step - warm) / max(1, UPDATES - warm)
    return 0.5 * (1.0 + math.cos(math.pi * min(1.0, t)))


def set_determinism(seed: int):
    import torch
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=False)


def run_training(arm_id: str, seed: int, widen_w: int, train_batches,
                 monitor_batches, log_every: int = 20):
    """Train one arm/seed head for exactly UPDATES steps. train_batches is a
    deterministic iterable of pre-assembled tensor batches from the TRAIN split
    (each batch dict carries split='train'); monitor_batches is validation, read
    for curve logging only. Returns (state_dict, curve)."""
    device = require_gpu()                              # FIRST -- fail closed
    import torch
    set_determinism(seed)
    head = build_arm_head(arm_id, widen_w).float().to(device)
    opt = torch.optim.AdamW(head.parameters(), lr=LR, betas=BETAS, weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda)
    loss_fn = torch.nn.CrossEntropyLoss()
    curve, it = [], iter(train_batches)
    for step in range(UPDATES):                         # exactly 3000; NO early stop
        try:
            batch = next(it)
        except StopIteration:
            it = iter(train_batches)
            batch = next(it)
        if batch.get("split") != "train":
            raise RuntimeError("SPLIT_LAW_VIOLATION: non-train batch in training")
        logits = head(batch["h"].to(device), batch["g"].to(device),
                      None if batch["p"] is None else batch["p"].to(device),
                      batch["idea_mask"].to(device), batch["cand_enc"].to(device),
                      batch["cand_mask"].to(device))
        loss = loss_fn(logits, batch["answer_index"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(head.parameters(), CLIP)
        opt.step()
        sched.step()
        if (step + 1) % log_every == 0 or step == 0:
            curve.append({"step": step + 1, "train_loss": float(loss.item())})
    return head.state_dict(), curve
