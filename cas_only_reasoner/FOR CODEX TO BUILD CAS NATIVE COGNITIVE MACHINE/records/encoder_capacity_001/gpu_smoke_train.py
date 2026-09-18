"""DEV SMOKE RUN on the local RTX 4070. Does the neuron level actually learn?

Run under WSL, where `platform.system() == "Linux"` and CUDA torch is present:
    CAS_META2_RUN_TEACHING_CYCLE=1 python3 records/encoder_capacity_001/gpu_smoke_train.py

This is a **smoke/dev run on the local GPU**, which is what the local 4070 is for. It is NOT a
claim-bearing run: no receipt, no sealed study, no result of record. It exists to answer one question
the owner asked directly -- **are the neurons learning?** -- by printing the loss and the exposed-course
accuracy at every update, plus the state change the run itself asserts.

What it does, faithfully to `cncm/typed_matched_worker.py`:
  - the same framework builder, encoder seed, optimizer config and learner
  - the same loop shape: `stage_batch` -> seal the public bytes -> `train_sealed_batch`
  - targets are derived by the project's own `checker.derive_target`, exactly as the worker does

Two arms, so the comparison the record has been arguing about becomes a measurement:
  random   -- the registered module as initialised
  analytic -- the same module with Fix A's closed-form `T` written in
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import time

os.environ.setdefault("CAS_META2_RUN_TEACHING_CYCLE", "1")

HERE = pathlib.Path(__file__).resolve()
HOME = HERE.parents[2]
sys.path[:0] = [str(HOME), str(HOME / "research" / "CAS_META_2_COMPOSITION")]

# `build_graph_training_framework` imports `casformer` -- "the reference wheel, not cas_cjt". The
# pinned wheels live in-tree under CAS_CJT_TRANSFORMER_v0_2, and a wheel is importable straight from
# sys.path, so they go on the path rather than being installed.
_DIST = (HOME / "research" / "CAS_CJT_TRANSFORMER_v0_2"
         / "artifacts" / "release_reproduction" / "dist")
if _DIST.is_dir():
    for _wheel in sorted(_DIST.glob("*.whl")):
        sys.path.insert(0, str(_wheel))

import torch  # noqa: E402

from cas_meta2.graph_teaching.real_framework import build_graph_training_framework  # noqa: E402
from cas_meta2.typed_teaching import checker, learner as learner_module, slots, worker_contract  # noqa: E402
from cas_meta2.typed_teaching.encoder import build_frozen_typed_encoder  # noqa: E402

ENCODER_SEED = 20260916
MODEL_SEED = 20260916
OPTIMIZER = {"learning_rate": 3e-3, "weight_decay": 0.01, "betas": [0.9, 0.999], "eps": 1e-8}


def admissible(packet, target):
    import json as _json
    return {_json.dumps(row["value"], sort_keys=True) for row in target["admissible_answers"]}


def score_packets(learner, packets, targets):
    hits = total = 0
    for record_id, packet in packets.items():
        body = learner.predict(packet, 8)
        try:
            value = json.dumps(body["answer"]["value"], sort_keys=True)
        except Exception:                                             # noqa: BLE001
            value = ""
        total += 1
        hits += 1 if value in admissible(packet, targets[record_id]) else 0
    return hits, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--updates", type=int, default=20)
    parser.add_argument("--arm", choices=("random", "analytic"), default="random")
    parser.add_argument("--probe", type=int, default=60, help="packets used for the accuracy probe")
    args = parser.parse_args()

    print(f"torch {torch.__version__}  cuda {torch.cuda.is_available()}  "
          f"{torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'}", flush=True)
    device = "cuda"
    frozen, tokenizer, schedule = worker_contract.load_material(HOME)
    packets = dict(worker_contract.public_packets(frozen))
    batches = frozen["batches"]
    print(f"course packets {len(packets)}   course batches {len(batches)}   "
          f"presentations {len(frozen['presentations'])}", flush=True)

    probe_ids = list(packets)[: args.probe]
    probe = {key: packets[key] for key in probe_ids}
    probe_targets = {key: checker.derive_target(p["source"], p["record"]["query"])
                     for key, p in probe.items()}

    framework = build_graph_training_framework(torch, device, seed=MODEL_SEED, encoder={"d_model": 64})
    if args.arm == "analytic":
        from cncm.analytic_decompose import decompose_from_free_readout_rectangular, identity_parameters
        readout = [[float(v) for v in row] for row in
                   build_frozen_typed_encoder(torch, tokenizer, seed=ENCODER_SEED, d_model=64,
                                              device=device).readout_rows.detach().cpu().tolist()]
        # a free readout that is the frozen readout itself: makes R T = R, so T = I is exact and the
        # block starts transparent. This is the analytic arm's most defensible form: it does not
        # pretend to install a readout the readout cannot carry (round 36).
        weights = [list(row) for row in zip(*readout)]
        _params, report = decompose_from_free_readout_rectangular(weights, readout)
        print(f"analytic arm: construction residual {report['residual']:.10f} exact {report['exact']}",
              flush=True)

    encoder = build_frozen_typed_encoder(torch, tokenizer, seed=ENCODER_SEED, d_model=64, device=device)
    if args.arm == "analytic":
        from cncm.analytic_decompose import parameters_for_map
        import cncm.analytic_decompose as ad
        identity = ad.identity_parameters()
        with torch.no_grad():
            framework.module.left.weight.copy_(
                torch.tensor(identity.left, dtype=torch.float32, device=device))
            framework.module.right.weight.copy_(
                torch.tensor(identity.right, dtype=torch.float32, device=device))
            framework.module.merge.weight.copy_(
                torch.tensor(identity.merge, dtype=torch.float32, device=device))
        print("analytic arm: block set to T = I (forward(x) = tanh(x), a transparent read path)",
              flush=True)

    learner = learner_module.TypedCourseLearner(
        torch, framework, encoder,
        optimizer_config=dict(OPTIMIZER),
        run_context={"run_id": "smoke-" + args.arm,
                     "course_sha256": worker_contract.MATERIAL[worker_contract.COURSE_PATH]["sha256"],
                     "condition": "MIXED_SAME_ITEMS", "source_seed": 101},
        limits={"max_updates": 176, "max_core_calls": 200000, "max_wall_seconds": 3600},
        device=device)

    initial_state = learner_module.state_identity(torch, dict(learner.module.state_dict()))
    hits, total = score_packets(learner, probe, probe_targets)
    print(f"\nupdate   0   loss      --      probe {hits:3d}/{total}  {hits / total:7.4%}", flush=True)

    started = time.monotonic()
    artifacts = pathlib.Path("/tmp/cncm_smoke"); artifacts.mkdir(exist_ok=True)
    history = []
    for cursor, batch in enumerate(batches[: args.updates]):
        selected = [packets[key] for key in batch["record_ids"]]
        staged = learner.stage_batch(selected, batch["depth"], cursor=batch["cursor"],
                                     occurrence_ids=batch["occurrence_ids"])
        path = artifacts / ("smoke_%03d_batch.json" % cursor)
        path.write_bytes(staged["bytes"])
        targets = [checker.derive_target(p["source"], p["record"]["query"]) for p in selected]
        update = learner.train_sealed_batch(path, expected_sha256=staged["sha256"],
                                            target_receipts=targets)
        loss = update.get("loss", update.get("mean_loss"))
        grad = update.get("gradient_squared_norm")
        hits, total = score_packets(learner, probe, probe_targets) if (cursor + 1) % 5 == 0 else (hits, total)
        history.append({"cursor": cursor + 1, "train_loss": loss, "grad_sq": grad,
                        "probe_hits": hits, "probe_total": total})
        print(f"update {cursor + 1:3d}   loss {loss!s:>8.5}   grad^2 {grad!s:>10.4}   "
              f"probe {hits:3d}/{total}  {hits / total:7.4%}", flush=True)

    final_state = learner_module.state_identity(torch, dict(learner.module.state_dict()))
    print(f"\nstate changed: {initial_state != final_state}")
    print(f"optimizer updates: {learner.counters['optimizer_updates']}   "
          f"backward calls: {learner.counters['backward_calls']}   "
          f"elapsed {time.monotonic() - started:.1f}s")
    out = HERE.parent / f"gpu_smoke_{args.arm}.json"
    out.write_text(json.dumps({"arm": args.arm, "updates": args.updates,
                               "state_changed": initial_state != final_state,
                               "history": history}, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
