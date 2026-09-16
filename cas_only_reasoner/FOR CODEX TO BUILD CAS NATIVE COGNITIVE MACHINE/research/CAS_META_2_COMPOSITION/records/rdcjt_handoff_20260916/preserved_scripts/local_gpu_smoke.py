"""Local RTX 4070 dev smoke for CAS_RDCJT_001 at the current source.

DEV ONLY. Under the owner's GPU-first rule the local GPU may run smoke/dev work
and nothing claim-bearing. This number is NOT a result and must never be cited
as one. Its only job is to prove the pipeline runs end to end on real CUDA
before a paid AWS job is authorised, so a packaging or indexing defect is found
here instead of after $7.00.

It drives the SAME entrypoint the deployed worker drives:
    cas_meta2.recurrent_cjt.runner.run(CONFIG, results=..., artifacts=..., root=...)
with device resolved from this machine's CUDA, exactly as the worker does.
"""

import json
import shutil
import sys
import time
from pathlib import Path

COMPOSITION = Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
    r"\research\CAS_META_2_COMPOSITION")
sys.path.insert(0, str(COMPOSITION))

RUN_ROOT = COMPOSITION / "_tmp" / "rdcjt_local_smoke"

CONFIG = {
    "schema": "cas.recurrent-cjt-config/1",
    "job": "rdcjt-local-smoke",
    "candidate": "CAS_RDCJT_001",
    "bucket": "local-smoke-no-bucket",
    "region": "us-west-2",
    "arms": ["one_pass", "recurrent"],
    "seed": 20260913,
    "learning_rate": 0.003,
    "round_depths": [1, 2, 4, 8, 2, 4, 8, 1, 4, 8, 1, 2, 8, 1, 2, 4],
    "evaluation_depths": ["R1", "R2", "R4", "R8", "RESET_8"],
    "updates_per_arm": 128,
    "decisions_per_arm": 896,
    "max_wall_seconds": 2400.0,
    "install_allowance_seconds": 600.0,
    "training": True,
}


def main():
    results = RUN_ROOT / "results"
    artifacts = results / "artifacts"
    if RUN_ROOT.exists():
        shutil.rmtree(RUN_ROOT)
    artifacts.mkdir(parents=True)

    import torch

    from cas_meta2.recurrent_cjt import runner

    # gpu_adapter._cuda() is the deployed Linux-worker path and refuses to run on
    # Windows (LINUX_WORKER_REQUIRED). runner.run takes torch/device as injectable
    # seams "so the rehearsal drives this same flow with no GPU", so the local
    # smoke resolves CUDA here and asserts the same fail-closed property the
    # adapter enforces: a CPU device is refused rather than silently used.
    if not torch.cuda.is_available():
        raise SystemExit("LOCAL_SMOKE_REFUSED:NO_CUDA_ON_THIS_MACHINE")
    device = torch.device("cuda")
    print("device:", torch.cuda.get_device_name(0), "| torch", torch.__version__)

    started = time.time()
    report = runner.run(CONFIG, results=results, artifacts=artifacts,
                        root=RUN_ROOT, torch=torch, device=device)
    elapsed = time.time() - started

    result_path = results / "result.json"
    payload = json.loads(result_path.read_bytes()) if result_path.is_file() else {}

    sweep = payload.get("sweep_comparison") or {}
    summary = {
        "label": "LOCAL_DEV_SMOKE_NOT_CLAIM_BEARING",
        "hardware": "local RTX 4070 (smoke/dev only under the GPU-first rule)",
        "source": "current worktree (branch codex/cas-meta-2-composition)",
        "config_seed": CONFIG["seed"],
        "elapsed_seconds": round(elapsed, 1),
        "status": report.get("status"),
        "arms": sorted(report.get("arms", {})),
        "artifact_count": len(report.get("artifacts", [])),
        "result_written": result_path.is_file(),
        "sweep_baseline_label": sweep.get("baseline_label"),
        "sweep_baseline_correct": sweep.get("baseline_correct"),
        "sweep_primary_label": sweep.get("primary_label"),
        "sweep_primary_correct": sweep.get("primary_correct"),
        "sweep_gained": sweep.get("gained"),
        "sweep_lost": sweep.get("lost"),
        "sweep_net": sweep.get("net"),
        "panel_items": sweep.get("panel_items"),
        "weights_unchanged": sweep.get("weights_unchanged"),
        "reset_matches_one_pass": sweep.get("reset_matches_one_pass"),
        "per_depth_net": {k: v.get("net") for k, v in
                          (sweep.get("per_depth") or {}).items()},
        "boundary": payload.get("boundary"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
