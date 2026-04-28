"""CAS-Native v2 first full training run on Level 2 dataset.

Implements the Tuesday training directive:
  - batch_size=128, seq_len=512, epochs=3
  - lr=1e-4 with linear warmup 500 steps
  - bf16 mixed precision (autocast)
  - gradient checkpointing off
  - v2 flags: register_film, emergent_register, production_semantics, expression_proposer
  - use_rust_validation: False
  - data_mix_meta_logic: 0.00 (Level 3 NOT in mix; symbolic-only)
  - validation split 10%, checkpoint every 100 steps, log every 25 steps
  - evaluation every 100 steps
  - production_warmup_steps=100 so short batch=128 runs reach full weight
  - output to cas-native/training/runs/v2-first-full-<timestamp>/

Designed to run UNATTENDED in the background on the pod. Logs to a file
so a wedged SSH connection doesn't hang training.
"""
import os, sys, time, json, types, math
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))

import torch

# Seed before any torch random init so model weight initialization is
# deterministic across re-runs at the same seed (modulo CUDA/cuDNN/bf16
# nondeterminism which we don't suppress — they cost throughput).
_SEED = int(os.environ.get("CAS_V2_SEED", 42))
torch.manual_seed(_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(_SEED)

from cas_native.training.trainer import CASTrainer
from cas_native.training.data_pipeline import run_pipeline
from cas_native.training.tokenizer import HybridCASTokenizer, tokenizer_from_loader
from cas_native.training.config import (
    TrainingConfig, V2ComponentFlags, V2Hyperparameters, V74Hyperparameters,
)
from cas_native.model import CASNativeModel, CASNativeConfig

# ------------------------------------------------------------ config

DATASET_PATH = Path("/root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl")
RUNS_ROOT = REPO_ROOT / "cas-native" / "training" / "runs"
TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
RUN_DIR = RUNS_ROOT / ("v2-first-full-" + TIMESTAMP)
RUN_DIR.mkdir(parents=True, exist_ok=True)
CKPT_DIR = RUN_DIR / "checkpoints"
CKPT_DIR.mkdir(exist_ok=True)

BATCH_SIZE = int(os.environ.get("CAS_V2_BATCH_SIZE", 128))
MAX_LENGTH = 512
EPOCHS = int(os.environ.get("CAS_V2_EPOCHS", 3))
REQUESTED_MAX_STEPS = int(os.environ.get("CAS_V2_MAX_STEPS", 0))
LR = 1e-4
WARMUP_STEPS = 500
LOG_EVERY = int(os.environ.get("CAS_V2_LOG_EVERY", 25))
EVAL_EVERY = int(os.environ.get("CAS_V2_EVAL_EVERY", 100))
CHECKPOINT_EVERY = int(os.environ.get("CAS_V2_CHECKPOINT_EVERY", 100))
# Curriculum delay on production_loss outer weight: ramps 0 → lambda_production
# linearly over the first PRODUCTION_WARMUP_STEPS training steps. Smooths the
# untrained-head noise spike that produced step-450's production_loss=0 dip in
# the first full v2 run (commit e6cd8e4).
PRODUCTION_WARMUP_STEPS = int(os.environ.get("CAS_V2_PRODUCTION_WARMUP", 100))

# ------------------------------------------------------------ logging

LOG_PATH = RUN_DIR / "train.log"
_log_file = open(LOG_PATH, "w", buffering=1)


def log(msg: str) -> None:
    line = "[" + datetime.now().strftime("%H:%M:%S") + "] " + msg
    print(line, flush=True)
    _log_file.write(line + "\n")


log("=== CAS-Native v2 first full training run ===")
log("Run dir: " + str(RUN_DIR))
log("Dataset: " + str(DATASET_PATH))


# ------------------------------------------------------------ data + model

log("[1/5] Loading dataset + fitting frozen CAS tokenizer...")
train_loader, val_loader, test_loader, stats = run_pipeline(
    json_paths=[str(DATASET_PATH)],
    augment=False,
    batch_size=BATCH_SIZE,
    max_length=MAX_LENGTH,
    seed=42,
)
log("      stages: " + str(stats["stages"]))
steps_per_epoch = len(train_loader)
if REQUESTED_MAX_STEPS > 0:
    total_steps = REQUESTED_MAX_STEPS
    # Ensure the outer epoch loop covers the requested step budget.
    EPOCHS = max(EPOCHS, math.ceil(total_steps / max(steps_per_epoch, 1)))
else:
    total_steps = EPOCHS * steps_per_epoch
log(
    "      train batches/epoch: "
    + str(steps_per_epoch)
    + " | epochs scheduled: "
    + str(EPOCHS)
    + " | total steps: "
    + str(total_steps)
)
tokenizer = tokenizer_from_loader(train_loader)
tokenizer_meta = {}
if isinstance(tokenizer, HybridCASTokenizer):
    tokenizer_path = RUN_DIR / "tokenizer.json"
    tokenizer.save(tokenizer_path)
    tokenizer_meta = tokenizer.metadata()
    log("      tokenizer: " + str(tokenizer_meta))
    log("      tokenizer artifact: " + str(tokenizer_path))
else:
    tokenizer_path = None
    log("      tokenizer: legacy/unknown")

model_vocab_size = int(getattr(tokenizer, "vocab_size", 32000))
log("[2/5] Initializing model...")
model = CASNativeModel(CASNativeConfig(vocab_size=model_vocab_size))
n_params = sum(p.numel() for p in model.parameters())
log("      params: " + format(n_params, ","))
log("      vocab_size: " + str(model_vocab_size))


# ------------------------------------------------------------ trainer

log("[3/5] Building trainer with v2 flags...")
v74_hp = V74Hyperparameters(
    lr=LR,
    warmup_steps=WARMUP_STEPS,
    max_steps=total_steps,
    grad_clip=1.0,
    checkpoint_every=CHECKPOINT_EVERY,
    eval_every=EVAL_EVERY,
    checkpoint_dir=str(CKPT_DIR),
)
v2_hp = V2Hyperparameters(production_warmup_steps=PRODUCTION_WARMUP_STEPS)
# data_mix_meta_logic=0.00 (Level 3 NOT in mix). Default already 0.0.
assert v2_hp.data_mix_meta_logic == 0.0, "directive: data_mix_meta_logic must be 0.00"
log("      production_warmup_steps: " + str(v2_hp.production_warmup_steps))

cfg = TrainingConfig(
    component_flags=V2ComponentFlags(
        use_register_film=True,
        use_emergent_register=True,
        use_production_semantics=True,
        use_rust_validation=False,
        use_expression_proposer=True,
    ),
    v2_hyperparameters=v2_hp,
    v7_4_hyperparameters=v74_hp,
)
trainer = CASTrainer(model=model, train_loader=train_loader, val_loader=val_loader, config=cfg)
model.to("cuda")
log("      v2 sub-modules: " + ", ".join(model.v2_components.keys()) if hasattr(model, "v2_components") else "      v2_components missing")


# ------------------------------------------------------------ training loop

log("[4/5] Training: " + str(EPOCHS) + " epochs, batch=" + str(BATCH_SIZE) + ", lr=" + str(LR) + ", bf16, warmup=" + str(WARMUP_STEPS))
log("      checkpoint every " + str(CHECKPOINT_EVERY) + " steps, eval every " + str(EVAL_EVERY) + " steps, log every " + str(LOG_EVERY))

start = time.time()
all_metrics = []
peak_mem_gb = 0.0
nan_step = None
oom_at_step = None

trainer.model.train()
for epoch in range(EPOCHS):
    log("--- Epoch " + str(epoch + 1) + "/" + str(EPOCHS) + " ---")
    for batch in train_loader:
        step = trainer.global_step
        if step >= total_steps:
            break

        try:
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                metrics = trainer._train_step(batch)
        except torch.cuda.OutOfMemoryError as e:
            oom_at_step = step
            log("FATAL: OOM at step " + str(step) + ": " + str(e))
            break
        except Exception as e:
            log("EXCEPTION at step " + str(step) + ": " + type(e).__name__ + ": " + str(e))
            import traceback
            traceback.print_exc(file=_log_file)
            nan_step = step
            break

        # Coerce metrics to floats
        m_floats = {}
        for k, v in metrics.items():
            if isinstance(v, torch.Tensor):
                v = v.item()
            try:
                m_floats[k] = float(v)
            except (TypeError, ValueError):
                pass
        loss_val = m_floats.get("total", float("nan"))
        m_floats["step"] = step
        m_floats["epoch"] = epoch
        all_metrics.append(m_floats)

        if torch.cuda.is_available():
            peak_mem_gb = max(peak_mem_gb, torch.cuda.max_memory_allocated() / 1024 ** 3)

        if math.isnan(loss_val) or math.isinf(loss_val):
            nan_step = step
            log("FATAL: total loss is " + str(loss_val) + " at step " + str(step))
            break

        if step % LOG_EVERY == 0:
            extras = {k: m_floats[k] for k in m_floats if k not in ("total", "lr", "current_tau", "step", "epoch") and not k.startswith("register_latent/")}
            extras_str = ", ".join(k + "=" + format(v, ".3f") for k, v in sorted(extras.items()) if abs(v) > 1e-10)
            log("  step " + format(step, "4d") + "/" + str(total_steps) + " ep=" + str(epoch) + ": total=" + format(loss_val, ".4f") + "  mem=" + format(peak_mem_gb, ".2f") + "GB  [" + extras_str + "]")

        # Checkpointing
        if step > 0 and step % CHECKPOINT_EVERY == 0:
            ckpt_path = CKPT_DIR / ("step_" + str(step) + ".pt")
            try:
                torch.save({
                    "step": step,
                    "epoch": epoch,
                    "model_state_dict": trainer.model.state_dict(),
                    "optimizer_state_dict": trainer.optimizer.state_dict(),
                    "tokenizer": tokenizer_meta,
                }, ckpt_path)
                log("  [ckpt] wrote " + str(ckpt_path))
            except Exception as e:
                log("  [ckpt] write FAILED: " + str(e))

        # Validation — uses trainer._eval_step (forward-only, no_grad-safe).
        # Fixed in the same commit that added _eval_step to trainer.py.
        if step > 0 and step % EVAL_EVERY == 0:
            log("  [eval] step " + str(step) + " — running validation pass...")
            val_total = 0.0
            val_n = 0
            val_components = {}
            for vb_idx, vb in enumerate(val_loader):
                if vb_idx >= 32:  # cap eval batches to keep eval fast
                    break
                try:
                    with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                        vm = trainer._eval_step(vb)
                except Exception as e:
                    log("  [eval] exception in eval batch: " + str(e))
                    break
                vm_floats = {}
                for k, v in vm.items():
                    if isinstance(v, torch.Tensor):
                        v = v.item()
                    try:
                        vm_floats[k] = float(v)
                    except (TypeError, ValueError):
                        pass
                val_total += vm_floats.get("total", 0.0)
                val_n += 1
                for k, v in vm_floats.items():
                    if k in ("total", "lr", "current_tau") or k.startswith("register_latent/"):
                        continue
                    val_components.setdefault(k, []).append(v)
            val_avg = val_total / max(val_n, 1)
            comp_avgs = {k: sum(v) / len(v) for k, v in val_components.items() if v}
            log("  [eval] val avg total=" + format(val_avg, ".4f") + " over " + str(val_n) + " batches")
            for k, v in sorted(comp_avgs.items()):
                if abs(v) > 1e-6:
                    log("  [eval]   " + k + "=" + format(v, ".4f"))

        trainer.global_step += 1

    if nan_step is not None or oom_at_step is not None:
        break

elapsed = time.time() - start
final_step = trainer.global_step

log("=== Training complete ===")
log("  Final step: " + str(final_step) + "/" + str(total_steps))
log("  Wall-clock: " + format(elapsed, ".1f") + "s = " + format(elapsed / 60.0, ".1f") + " min")
log("  Peak GPU memory: " + format(peak_mem_gb, ".2f") + " GB")

# Save final checkpoint
final_ckpt = CKPT_DIR / "final.pt"
try:
    torch.save({
        "step": final_step,
        "model_state_dict": trainer.model.state_dict(),
        "optimizer_state_dict": trainer.optimizer.state_dict(),
        "tokenizer": tokenizer_meta,
    }, final_ckpt)
    log("  Final checkpoint: " + str(final_ckpt))
except Exception as e:
    log("  Final checkpoint FAILED: " + str(e))

# Save metrics
with open(RUN_DIR / "metrics.json", "w") as f:
    json.dump({
        "config": {
            "batch_size": BATCH_SIZE,
            "max_length": MAX_LENGTH,
            "epochs": EPOCHS,
            "requested_max_steps": REQUESTED_MAX_STEPS,
            "lr": LR,
            "warmup_steps": WARMUP_STEPS,
            "production_warmup_steps": v2_hp.production_warmup_steps,
            "log_every": LOG_EVERY,
            "eval_every": EVAL_EVERY,
            "checkpoint_every": CHECKPOINT_EVERY,
            "total_steps": total_steps,
            "v2_flags": [k for k, v in cfg.component_flags.__dict__.items() if v],
            "data_mix_meta_logic": v2_hp.data_mix_meta_logic,
            "tokenizer": tokenizer_meta,
            "tokenizer_path": str(tokenizer_path) if tokenizer_path is not None else None,
        },
        "all_metrics": all_metrics,
        "summary": {
            "final_step": final_step,
            "wall_clock_s": elapsed,
            "wall_clock_min": elapsed / 60.0,
            "peak_mem_gb": peak_mem_gb,
            "nan_step": nan_step,
            "oom_at_step": oom_at_step,
            "status": "COMPLETED" if nan_step is None and oom_at_step is None else ("HALTED_NAN_AT_" + str(nan_step) if nan_step is not None else "OOM_AT_" + str(oom_at_step)),
        },
    }, f, indent=2)

log("[5/5] Metrics + checkpoint saved to " + str(RUN_DIR))
_log_file.close()
