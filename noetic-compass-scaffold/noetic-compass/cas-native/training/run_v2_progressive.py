"""CAS-Native v2 progressive smoke runner.

Runs N steps with a specific subset of v2 component flags enabled.
Captures: loss curve (total + per-component), GPU memory peak,
wall-clock, NaN/Inf detection, and which loss-component keys appear.
"""
import os, sys, time, json, types, math, argparse
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))

import torch
from cas_native.training.trainer import CASTrainer
from cas_native.training.data_pipeline import run_pipeline
from cas_native.training.config import (
    TrainingConfig, V2ComponentFlags, V2Hyperparameters, V74Hyperparameters,
)
from cas_native.model import CASNativeModel, CASNativeConfig

DATASET_PATH = Path("/root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.json")
RUNS_ROOT = REPO_ROOT / "cas-native" / "training" / "runs"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--flags", default="", help="comma-separated v2 flags")
    p.add_argument("--label", default=None, help="run label suffix")
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--batch-size", type=int, default=4)
    return p.parse_args()


def build_flags(flag_csv):
    requested = set(s.strip() for s in flag_csv.split(",") if s.strip())
    return V2ComponentFlags(
        use_register_film="register_film" in requested,
        use_emergent_register="emergent_register" in requested,
        use_production_semantics="production_semantics" in requested,
        use_rust_validation="rust_validation" in requested,
        use_expression_proposer="expression_proposer" in requested,
    )


def main():
    args = parse_args()
    flags = build_flags(args.flags)
    flag_summary = ",".join(k for k, v in flags.__dict__.items() if v) or "none"
    label = args.label or flag_summary.replace(",", "+")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_ROOT / ("smoke-" + timestamp + "-" + label)
    run_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("=== smoke run " + timestamp + " | flags: " + flag_summary)
    print("=" * 70)
    print("Run dir: " + str(run_dir))

    print("\n[1/4] Initializing model...")
    model = CASNativeModel(CASNativeConfig())
    n_params = sum(p.numel() for p in model.parameters())
    print("      params: " + format(n_params, ","))

    print("\n[2/4] Loading dataset...")
    train_loader, val_loader, _, stats = run_pipeline(
        json_paths=[str(DATASET_PATH)],
        augment=False,
        batch_size=args.batch_size,
        max_length=512,
        seed=42,
    )
    print("      stages: " + str(stats["stages"]))

    print("\n[3/4] Building trainer with flags=" + flag_summary + "...")
    cfg = TrainingConfig(
        component_flags=flags,
        v7_4_hyperparameters=V74Hyperparameters(
            lr=1e-4,
            warmup_steps=10,
            max_steps=args.steps,
            checkpoint_every=args.steps + 10,
            eval_every=args.steps + 10,
            checkpoint_dir=str(run_dir / "checkpoints"),
        ),
    )
    trainer = CASTrainer(model=model, train_loader=train_loader, val_loader=val_loader, config=cfg)
    model.to("cuda")
    trainer.device = next(model.parameters()).device  # reset cached device
    print("      v2 sub-modules instantiated:")
    if hasattr(model, "v2_components"):
        for name in model.v2_components:
            print("        - model.v2_components[" + repr(name) + "]")

    print("\n[4/4] Smoke loop (" + str(args.steps) + " steps, batch=" + str(args.batch_size) + ")...")
    start = time.time()
    loss_curve = []
    peak_mem_gb = 0.0
    seen_keys = set()
    nan_step = None

    trainer.model.train()
    data_iter = iter(train_loader)
    for step in range(args.steps):
        try:
            batch = next(data_iter)
        except StopIteration:
            data_iter = iter(train_loader)
            batch = next(data_iter)
        # Move batch tensors to cuda before _train_step (v2 path doesn't auto-move)
        for _k, _v in list(batch.items()):
            if isinstance(_v, torch.Tensor):
                batch[_k] = _v.to("cuda", non_blocking=True)
        try:
            metrics = trainer._train_step(batch)
        except Exception as e:
            import traceback; traceback.print_exc()
            print("  EXCEPTION at step " + str(step) + ": " + type(e).__name__ + ": " + str(e))
            return 1, None
        seen_keys.update(metrics.keys())
        m_floats = {}
        for k, v in metrics.items():
            if isinstance(v, torch.Tensor):
                v = v.item()
            try:
                m_floats[k] = float(v)
            except (TypeError, ValueError):
                pass
        loss_val = m_floats.get("total", m_floats.get("loss", float("nan")))
        loss_curve.append({"step": step, **m_floats})

        if torch.cuda.is_available():
            peak_mem_gb = max(peak_mem_gb, torch.cuda.max_memory_allocated() / 1024 ** 3)

        if step % 10 == 0:
            extras = {k: m_floats[k] for k in m_floats if k not in ("total", "lr", "current_tau")}
            extras_str = ", ".join(k + "=" + format(v, ".3f") for k, v in sorted(extras.items()) if abs(v) > 1e-10)
            print("  step " + format(step, "3d") + ": total=" + format(loss_val, ".4f") + "  mem=" + format(peak_mem_gb, ".2f") + "GB  [" + extras_str + "]")

        if math.isnan(loss_val) or math.isinf(loss_val):
            nan_step = step
            print("  FATAL: total loss is " + str(loss_val) + " at step " + str(step))
            break

    elapsed = time.time() - start
    final_step = len(loss_curve)

    with open(run_dir / "loss_curve.json", "w") as f:
        json.dump(loss_curve, f, indent=2)

    loss_first = loss_curve[0].get("total", float("nan")) if loss_curve else float("nan")
    loss_last = loss_curve[-1].get("total", float("nan")) if loss_curve else float("nan")
    loss_min = min((c.get("total", float("inf")) for c in loss_curve), default=float("nan"))
    if loss_last < loss_first - 0.01:
        direction = "DECREASING"
    elif loss_last > loss_first + 0.01:
        direction = "INCREASING"
    else:
        direction = "FLAT"

    component_keys_active = sorted(
        k for k in seen_keys
        if k not in ("total", "lr", "current_tau")
        and any(abs(c.get(k, 0)) > 1e-10 for c in loss_curve)
    )
    component_keys_zero = sorted(
        k for k in seen_keys
        if k not in ("total", "lr", "current_tau")
        and not any(abs(c.get(k, 0)) > 1e-10 for c in loss_curve)
    )

    summary = {
        "timestamp": timestamp,
        "label": label,
        "flags_enabled": [k for k, v in flags.__dict__.items() if v],
        "status": "COMPLETED" if nan_step is None else "HALTED_NAN_AT_STEP_" + str(nan_step),
        "steps_run": final_step,
        "steps_target": args.steps,
        "batch_size": args.batch_size,
        "params": n_params,
        "loss_first": loss_first,
        "loss_last": loss_last,
        "loss_min": loss_min,
        "loss_direction": direction,
        "peak_mem_gb": peak_mem_gb,
        "wall_clock_s": elapsed,
        "steps_per_sec": final_step / max(elapsed, 1e-6),
        "component_keys_active": component_keys_active,
        "component_keys_zero": component_keys_zero,
    }
    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\nCompleted " + str(final_step) + "/" + str(args.steps) + " steps in " + format(elapsed, ".1f") + "s")
    print("  Direction: " + direction + " (" + format(loss_first, ".3f") + " -> " + format(loss_last, ".3f") + ", min " + format(loss_min, ".3f") + ")")
    print("  Peak mem: " + format(peak_mem_gb, ".2f") + " GB / 20 GB")
    print("  Active components: " + str(component_keys_active))
    print("  Zero/inactive: " + str(component_keys_zero))
    print("\nArtifacts: " + str(run_dir))
    return 0, summary


if __name__ == "__main__":
    rc, _ = main()
    sys.exit(rc)
