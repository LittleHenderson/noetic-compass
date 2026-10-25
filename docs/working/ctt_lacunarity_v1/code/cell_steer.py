"""Bounded cell steering (v1) — inference-time only, weights frozen.

For a cell (Noetic x Domain) it builds a direction from the model's own encoder memory: the mean memory of rows that
contain the cell minus the mean of rows that do not. It then nudges the memory by alpha * direction and measures the
teacher-forced error on rows that contain the cell. A matched random direction of the same norm is the control: if
random does as much, the cell direction is not carrying the effect.

    python cell_steer.py --checkpoint <pt> --rows 600 --alphas 0.5,1.0,2.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helm_cas_translator import model as M, param_count
from helm_cas_translator.vocab import BOS, PAD
from mouth_task import vocab_m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--labels", default="data/labels_notation.jsonl")
    ap.add_argument("--alphas", default="0.5,1.0,2.0")
    ap.add_argument("--min-rows", type=int, default=20)
    a = ap.parse_args()

    import torch
    import torch.nn.functional as F
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.checkpoint, map_location=device, weights_only=True))
    net.eval()

    rows = [json.loads(l) for l in open(HERE / a.labels, encoding="utf-8") if l.strip()]
    texts = [r["text"] for r in rows]
    srcs = [vm.base.encode_source("N", t, [])[0] for t in texts]
    # targets come from the data file, aligned by text
    base_rows = {r["text"]: r for r in (json.loads(l) for l in open(HERE / "data" / "notation_new100.jsonl", encoding="utf-8") if l.strip())}
    tgts = [vm.base.encode_target(base_rows[t]["target"]) for t in texts]

    with torch.no_grad():
        src = M.pad_batch(srcs, device)
        mem, pad = net.encode(src)
        mask = (~pad).unsqueeze(-1).float()
        h = (mem * mask).sum(1) / mask.sum(1).clamp_min(1.0)

    def row_nll(mem_mod, idx):
        out = []
        with torch.no_grad():
            for i in idx:
                s = M.pad_batch([srcs[i]], device)
                t = M.pad_batch([[BOS] + tgts[i][:-1]], device)
                pp = s.eq(PAD)
                logp = net.decode_logp(s, mem_mod[i:i + 1, :s.size(1), :], pp, t)
                tgt = M.pad_batch([tgts[i]], device)
                nll = -logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
                msk = tgt.ne(PAD)
                out.append(float(nll[msk].mean()))
        return sum(out) / len(out)

    cells = sorted({c for r in rows for c in r["cells"]})
    alphas = [float(x) for x in a.alphas.split(",")]
    results = {}
    for c in cells:
        idx_c = [i for i, r in enumerate(rows) if c in r["cells"]]
        idx_o = [i for i, r in enumerate(rows) if c not in r["cells"]]
        if len(idx_c) < a.min_rows or len(idx_o) < a.min_rows:
            continue
        # split: direction from the discovery half, scoring on the confirmation half (no leakage)
        disc = [i for k, i in enumerate(idx_c) if k % 2 == 0]
        conf = [i for k, i in enumerate(idx_c) if k % 2 == 1]
        disc_o = [i for k, i in enumerate(idx_o) if k % 2 == 0]
        if len(disc) < 8 or len(conf) < 8:
            continue
        v = h[disc].mean(0) - h[disc_o].mean(0)
        v = v / v.norm().clamp_min(1e-9)
        rng = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(c.encode()).hexdigest(), 16) % (2 ** 31))
        r = torch.randn_like(v.cpu(), generator=rng).to(device)
        r = r / r.norm().clamp_min(1e-9)
        scale = h[disc].norm(dim=1).mean()
        base = row_nll(mem, conf)
        entry = {"rows_with_cell": len(idx_c), "confirmation_rows": len(conf), "baseline": round(base, 6), "alphas": {}}
        for alpha in alphas:
            steer = mem.clone()
            steer[conf] += (alpha * scale) * v
            rand = mem.clone()
            rand[conf] += (alpha * scale) * r
            entry["alphas"][str(alpha)] = {
                "steered": round(row_nll(steer, conf), 6),
                "random": round(row_nll(rand, conf), 6),
            }
        results[c] = entry
        print(json.dumps({c: entry}, ensure_ascii=False), flush=True)

    print(json.dumps({"checkpoint": a.checkpoint, "cells_tested": len(results)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())




