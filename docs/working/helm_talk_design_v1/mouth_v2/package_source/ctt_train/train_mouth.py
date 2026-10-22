"""Teach one CTT copy to WRITE: the mouth direction [M], alongside its ear ([B]) and the kept CAS skills (A-TALK-4 W2,
W6). GPU_REQUIRED (fails closed).

    python -X utf8 -B -m ctt_train.train_mouth --model A4-s1 --out <dir> --order-seed <int> [--max-steps N]

Starts from weights/<model>.pt (the CUBE TRAIN c57 final weights, sha256 checked against FROZEN_MOUTH.json), adds the
[M] row (mouth_task.surgery), asserts the parameter count at the new vocabulary size, then trains the frozen number of
steps on batches mixed MOUTH : CUBE ([B], SDG + AI-written) : CAS kept rows ([A]/[N]) = FROZEN_MOUTH.json "mix" (no
early stopping, no checkpoint choice). Writes final.pt, WEIGHTS_MANIFEST.json, progress.jsonl (every 100 steps).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def seed_of(model: str) -> int:
    return int(hashlib.sha256(("MOUTH-TRAIN-%s-20261022" % model).encode()).hexdigest(), 16) % (2 ** 63)


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log(path: Path, obj) -> None:
    line = json.dumps(obj, sort_keys=True)
    print(line, flush=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=("A4-s1", "A4-s2", "A4-s3", "A5-s1"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--order-seed", type=int, required=True)
    ap.add_argument("--max-steps", type=int, default=None, help="smoke only")
    a = ap.parse_args(argv)

    import torch
    import torch.nn.functional as F
    from cube_task import mix, target
    from helm_cas_translator import model as M, param_count
    from helm_cas_translator.vocab import BOS, PAD, context_units
    from mouth_task import surgery, vocab_m

    device = M.require_cuda()
    fz = json.loads((HERE / "FROZEN_MOUTH.json").read_text(encoding="utf-8"))
    rec = fz["models"][a.model]
    cfg = param_count.CONFIGS[rec["config"]]
    seed = seed_of(a.model)
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prog = out / "progress.jsonl"
    data = HERE / "data"
    vm = vocab_m.load(str(data / "vocab.json"))
    base_size = len(vm.base.tokens)
    init_path = HERE / "weights" / (a.model + ".pt")
    if sha256_file(init_path) != rec["init_sha256"]:
        raise SystemExit("start weights of %s do not match FROZEN_MOUTH.json" % a.model)
    state = torch.load(init_path, map_location="cpu", weights_only=True)
    net = M.CTTModel.from_config(len(vm), cfg, dropout=fz["dropout"]).to(device)
    net.load_state_dict(surgery.add_m_row(state, base_size))
    n_params = M.assert_parameter_count(net, len(vm), cfg)

    def load(name):
        return [json.loads(l) for l in open(data / name, encoding="utf-8") if l.strip()]

    mouth = load("mouth_train.jsonl")
    cube = load("train_cube.jsonl")
    cas = load("cas_keep.jsonl")
    ear_m = load("ear_m.jsonl")                    # A-TALK-7 H2 + A-TALK-8 I1: the ear learns the mouth's sentences and
                                                   # the corpus's chat lines ("nothing to save")
    enc = {
        "MOUTH": [(vm.encode_mouth_source(r["situation"], tuple(r["tone"]), r["input_text"],
                                          tuple(r["style"]) if r.get("style") else None), vm.encode_mouth_target(r["target"]))
                  for r in mouth],
        "EAR_M": [(vm.base.encode_source(target.DIRECTION, r["text"], [])[0], vm.base.encode_target(r["target"])) for r in ear_m],
        "CUBE": [(vm.base.encode_source(target.DIRECTION, r["text"], [])[0], vm.base.encode_target(r["target"])) for r in cube],
        "CAS": [(vm.base.encode_source(r["direction"], r["text"], context_units(r["context"]))[0], vm.base.encode_target(r["target"]))
                for r in cas],
    }
    total = a.max_steps or fz["steps"]
    plan = mix.batch_plan(total, fz["batch"], {k: len(v) for k, v in enc.items()}, fz["mix"], a.order_seed)
    opt = torch.optim.AdamW(net.parameters(), lr=fz["lr"], weight_decay=fz["weight_decay"])
    warm = min(fz["warmup_steps"], max(1, total // 10))

    def lr_at(step):
        if step < warm:
            return fz["lr"] * (step + 1) / warm
        p = (step - warm) / max(1, total - warm)
        return fz["lr"] * 0.5 * (1 + math.cos(math.pi * min(1.0, p)))

    manifest = {"schema": "mouth-train.weights-manifest/1", "model": a.model, "seed": seed, "order_seed": a.order_seed,
                "config_name": rec["config"], "config": cfg, "parameters": n_params, "vocab_size": len(vm),
                "init_sha256": rec["init_sha256"], "vocab_sha256": sha256_file(data / "vocab.json"),
                "data_manifest_sha256": sha256_file(data / "DATA_MANIFEST_MOUTH.json"), "torch": torch.__version__,
                "gpu": torch.cuda.get_device_name(0), "frozen": {k: fz[k] for k in ("steps", "batch", "lr", "mix")},
                "pool_rows": {k: len(v) for k, v in enc.items()}}
    log(prog, {"event": "start", "model": a.model, "steps_total": total, "parameters": n_params,
               "pool_rows": manifest["pool_rows"], "gpu": manifest["gpu"]})
    net.train()
    t0, last = time.time(), None
    for step, batch in enumerate(plan):
        for g in opt.param_groups:
            g["lr"] = lr_at(step)
        pairs = [enc[k][i] for k, i in batch]
        src = M.pad_batch([s for s, _t in pairs], device)
        tgt_out = M.pad_batch([t for _s, t in pairs], device)
        tgt_in = M.pad_batch([[BOS] + t[:-1] for _s, t in pairs], device)
        logp = net(src, tgt_in)
        loss = F.nll_loss(logp.reshape(-1, logp.size(-1)), tgt_out.reshape(-1), ignore_index=PAD)
        if not torch.isfinite(loss):
            log(prog, {"event": "nan", "step": step})
            raise SystemExit("non-finite loss at step %d" % step)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), fz["grad_clip"])
        opt.step()
        last = float(loss.item())
        if (step + 1) % 100 == 0 or step + 1 == total:
            el = time.time() - t0
            log(prog, {"event": "step", "step": step + 1, "of": total, "loss": round(last, 5), "lr": lr_at(step),
                       "elapsed_s": round(el, 1), "eta_s": round(el / (step + 1) * (total - step - 1), 1)})
    torch.save(net.state_dict(), out / "final.pt")
    manifest.update(steps=total, final_train_loss=last, seconds=round(time.time() - t0, 1),
                    final_sha256=sha256_file(out / "final.pt"))
    (out / "WEIGHTS_MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    log(prog, {"event": "done", "steps": total, "final_sha256": manifest["final_sha256"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
