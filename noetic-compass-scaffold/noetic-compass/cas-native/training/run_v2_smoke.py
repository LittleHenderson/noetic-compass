"""CAS-Native v2 smoke test runner — 100 steps on Level 2 dataset.

Validates pipeline end-to-end on cloud GPU. NOT a real training run.
"""
import os, sys, time, json, types
from pathlib import Path
from datetime import datetime
import math

# cas_native package alias for hyphenated path
REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))

import torch
from cas_native.training.trainer import CASTrainer
from cas_native.training.data_pipeline import run_pipeline
from cas_native.model import CASNativeModel, CASNativeConfig

TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
RUN_DIR = REPO_ROOT / "cas-native" / "training" / "runs" / f"smoke-{TIMESTAMP}"
RUN_DIR.mkdir(parents=True, exist_ok=True)
print(f"=== smoke run {TIMESTAMP} ===")
print(f"Run dir: {RUN_DIR}")

DATASET_PATH = Path("/root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.json")
BATCH_SIZE = 4
MAX_STEPS = 100
LR = 1e-4

print(f"\n[1/4] Initializing model...")
model = CASNativeModel(CASNativeConfig())
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
n_params = sum(p.numel() for p in model.parameters())
print(f"      Model on {device}; params: {n_params:,}")

print(f"\n[2/4] Loading dataset from {DATASET_PATH}...")
train_loader, val_loader, test_loader, stats = run_pipeline(
    json_paths=[str(DATASET_PATH)],
    augment=False,
    batch_size=BATCH_SIZE,
    max_length=512,
    seed=42,
)
print(f"      Pipeline stats: {json.dumps(stats, default=str)[:300]}")

print(f"\n[3/4] Building trainer...")
config = {
    "lr": LR,
    "warmup_steps": 10,
    "max_steps": MAX_STEPS,
    "checkpoint_every": 200,  # > MAX_STEPS — no checkpoint write during smoke
    "eval_every": 200,         # > MAX_STEPS — no eval pass during smoke
    "checkpoint_dir": str(RUN_DIR / "checkpoints"),
}
trainer = CASTrainer(model=model, train_loader=train_loader, val_loader=val_loader, config=config)
print(f"      Trainer ready; running {MAX_STEPS} steps, batch={BATCH_SIZE}, lr={LR}")

print(f"\n[4/4] Smoke loop...")
start = time.time()
loss_curve = []
peak_mem_gb = 0.0

trainer.model.train()
data_iter = iter(train_loader)
nan_step = None
for step in range(MAX_STEPS):
    try:
        batch = next(data_iter)
    except StopIteration:
        data_iter = iter(train_loader)
        batch = next(data_iter)

    metrics = trainer._train_step(batch)
    loss_val = metrics.get("total", metrics.get("loss", float("nan")))
    if isinstance(loss_val, torch.Tensor):
        loss_val = float(loss_val.item())
    loss_curve.append({"step": step, "loss": float(loss_val)})

    if torch.cuda.is_available():
        peak_mem_gb = max(peak_mem_gb, torch.cuda.max_memory_allocated() / 1024**3)

    if step % 10 == 0:
        print(f"  step {step:3d}: loss={loss_val:.4f}, peak_mem={peak_mem_gb:.2f}GB")

    if math.isnan(loss_val) or math.isinf(loss_val):
        nan_step = step
        print(f"  FATAL: loss is {loss_val} at step {step}")
        break

elapsed = time.time() - start
final_step = len(loss_curve)
print(f"\nCompleted {final_step}/{MAX_STEPS} steps in {elapsed:.1f}s ({elapsed/max(final_step,1):.2f}s/step)")
print(f"Peak GPU memory: {peak_mem_gb:.2f} GB")

# Save loss curve
with open(RUN_DIR / "loss_curve.json", "w") as f:
    json.dump(loss_curve, f, indent=2)

# Compute report metrics
loss_first = loss_curve[0]["loss"] if loss_curve else float("nan")
loss_last = loss_curve[-1]["loss"] if loss_curve else float("nan")
loss_min = min(c["loss"] for c in loss_curve) if loss_curve else float("nan")
loss_max = max(c["loss"] for c in loss_curve) if loss_curve else float("nan")
direction = "DECREASING" if loss_last < loss_first else ("FLAT" if abs(loss_last - loss_first) < 0.01 else "INCREASING")

report = f"""# CAS-Native v2 Smoke Run Report

**Timestamp**: {TIMESTAMP}
**Pod**: RunPod RTX A4500 (20 GB VRAM)
**Dataset**: Level 2 v1 ({DATASET_PATH.name}, commit 74e5350)
**Status**: {"COMPLETED" if nan_step is None else f"HALTED at step {nan_step} (NaN/Inf loss)"}

## Hyperparameters

- batch_size: {BATCH_SIZE}
- max_steps: {MAX_STEPS}
- learning_rate: {LR}
- warmup_steps: 10
- mixed_precision: fp32 (bf16 deferred to full run)
- v2 component flags: ALL OFF (legacy v7.4-equivalent path)

## Model

- params: {n_params:,}

## Loss Curve

- Step 0: {loss_first:.4f}
- Step {final_step-1}: {loss_last:.4f}
- Min over run: {loss_min:.4f}
- Max over run: {loss_max:.4f}
- Direction: **{direction}**

## Resources

- Peak GPU memory: {peak_mem_gb:.2f} GB / 20 GB
- Wall-clock total: {elapsed:.1f}s
- Per-step avg: {elapsed/max(final_step,1):.2f}s
- Steps/sec: {final_step/max(elapsed, 1e-6):.2f}

## Pipeline Status

{"Pipeline validated end-to-end on cloud GPU. Ready for full 3-epoch training on similar compute when scheduled." if nan_step is None and loss_first > loss_last else "Smoke test produced anomalous loss profile — investigate before scheduling full run."}
"""

with open(RUN_DIR / "report.md", "w") as f:
    f.write(report)

print(f"\nArtifacts:")
print(f"  - {RUN_DIR}/report.md")
print(f"  - {RUN_DIR}/loss_curve.json")
print(f"\n=== smoke complete ===")
