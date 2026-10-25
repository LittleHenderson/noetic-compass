"""Gradient-conditioned cell steering (v2) — follows the CAS Harness conditioning method.

Three directions per cell, scored on the confirmation half only:
  * oracle   : -grad_mem(NLL) at the last source position, computed from that row's own gold target (uses the answer,
               so it is an upper bound, not a deployable controller);
  * cell     : mean memory of rows with the cell minus rows without, built on the discovery half (deployable);
  * random   : matched norm, deterministic seed (control).

The sign of the oracle step is checked against a finite difference, the way the Harness checks its JVP.

    python cell_steer_grad.py --checkpoint <pt> --alphas 0.5,1.0 --min-rows 20
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
    ap.add_argument("--data", default="data/notation_new100.jsonl")
    ap.add_argument("--alphas", default="0.5,1.0")
    ap.add_argument("--min-rows", type=int, default=20)
    a = ap.parse_args()

    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.checkpoint, map_location=device, weights_only=True))
    net.eval()

    labels = [json.loads(l) for l in open(HERE / a.labels, encoding="utf-8") if l.strip()]
    data = {r["text"]: r for r in (json.loads(l) for l in open(HERE / a.data, encoding="utf-8") if l.strip())}
    texts = [r["text"] for r in labels if r["text"] in data]
    srcs = [vm.base.encode_source("N", t, [])[0] for t in texts]
    tgts = [vm.base.encode_target(data[t]["target"]) for t in texts]
    cells = [r["cells"] for r in labels if r["text"] in data]

    def encode_with_grad(i):
        s = M.pad_batch([srcs[i]], device)
        mem, pad = net.encode(s)
        return s, mem, pad

    def nll_of(i, mem, s, pad):
        t_in = M.pad_batch([[BOS] + tgts[i][:-1]], device)
        tgt = M.pad_batch([tgts[i]], device)
        logp = net.decode_logp(s, mem, pad, t_in)
        nll = -logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        mask = tgt.ne(PAD)
        return nll[mask].mean()

    with torch.no_grad():
        base_mem = []
        for i in range(len(srcs)):
            s = M.pad_batch([srcs[i]], device)
            mem, pad = net.encode(s)
            base_mem.append((mem, pad))

    def pooled_memory():
        hs = []
        with torch.no_grad():
            for mem, pad in base_mem:
                m = (~pad).unsqueeze(-1).float()
                hs.append(((mem * m).sum(1) / m.sum(1).clamp_min(1.0))[0])
        return torch.stack(hs)

    h = pooled_memory()
    alphas = [float(x) for x in a.alphas.split(",")]
    out = []
    for c in sorted({c for row in cells for c in row}):
        idx = [i for i, row in enumerate(cells) if c in row]
        other = [i for i, row in enumerate(cells) if c not in row]
        if len(idx) < a.min_rows or len(other) < a.min_rows:
            continue
        disc = [i for k, i in enumerate(idx) if k % 2 == 0]
        conf = [i for k, i in enumerate(idx) if k % 2 == 1]
        if len(conf) < 8:
            continue
        v = (h[disc].mean(0) - h[other].mean(0))
        v = v / v.norm().clamp_min(1e-9)
        rng = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(c.encode()).hexdigest(), 16) % (2 ** 31))
        r = torch.randn(v.shape, generator=rng).to(device)
        r = r / r.norm().clamp_min(1e-9)
        scale = h[disc].norm(dim=1).mean()

        base = grad = cellv = rand = fd = 0.0
        for i in conf:
            mem, pad = base_mem[i]
            s = M.pad_batch([srcs[i]], device)
            with torch.no_grad():
                b = float(nll_of(i, mem, s, pad))
            m2 = mem.clone().requires_grad_(True)
            loss = nll_of(i, m2, s, pad)
            g = torch.autograd.grad(loss, m2)[0]
            pos = int((~pad[0]).sum().item()) - 1
            d = -g[0, pos, :]
            d = d / d.norm().clamp_min(1e-9)
            def with_dir(vec):
                m3 = mem.clone()
                m3[0, pos, :] = m3[0, pos, :] + (1.0 * scale) * vec
                with torch.no_grad():
                    return float(nll_of(i, m3, s, pad))
            base += b
            grad += with_dir(d)
            cellv += with_dir(v)
            rand += with_dir(r)
        n = len(conf)
        out.append({"cell": c, "conf_rows": n, "baseline": round(base / n, 6), "oracle_grad": round(grad / n, 6),
                    "cell_dir": round(cellv / n, 6), "random": round(rand / n, 6)})
        print(json.dumps(out[-1]), flush=True)

    # analytic sign check on one row: does a small step along -grad lower the NLL?
    i = next(iter(range(len(srcs))))
    mem, pad = base_mem[i]
    s = M.pad_batch([srcs[i]], device)
    m2 = mem.clone().requires_grad_(True)
    loss = nll_of(i, m2, s, pad)
    g = torch.autograd.grad(loss, m2)[0]
    pos = int((~pad[0]).sum().item()) - 1
    d = -g[0, pos, :] / g[0, pos, :].norm().clamp_min(1e-9)
    eps = 1e-3
    m3 = mem.clone()
    m3[0, pos, :] = m3[0, pos, :] + eps * d
    with torch.no_grad():
        after = float(nll_of(i, m3, s, pad))
    before = float(loss)
    print(json.dumps({"sign_check": {"before": round(before, 6), "after": round(after, 6),
                                     "lowered": after < before}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
