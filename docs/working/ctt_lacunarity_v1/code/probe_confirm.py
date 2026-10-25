"""Predeclared confirmation of the kNN steering probe (CAS-LAB-002, section 6).

For each seed:
  1. compute the oracle direction for every row (uses the gold answer, upper bound only);
  2. choose k in {5,10,20,50} USING DISCOVERY ROWS ONLY (nearest other discovery rows), then freeze it;
  3. score the frozen k on the confirmation half, with a bootstrap interval over rows;
  4. score the class-mean and random controls on the same rows.

Success bar (written before the run): probe gain >= 10% of the oracle gain in at least 2 of 3 seeds, and strictly
above the random control in all three.

    python probe_confirm.py --seeds A4-s1,A4-s2,A4-s3
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

KS = (5, 10, 20, 50)


def run_seed(seed_name, ckpt, data, labels, device, vm, cfg):
    import torch
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
    net.eval()

    cells_by_text = {r["text"]: r["cells"] for r in labels}
    rows = [(t, cells_by_text[t], data[t].get("seed_id", "row_%d" % i))
            for i, t in enumerate(data) if t in cells_by_text]
    texts = [t for t, _c, _s in rows]
    srcs = [vm.base.encode_source("N", t, [])[0] for t in texts]
    tgts = [vm.base.encode_target(data[t]["target"]) for t in texts]
    cells = [c for _t, c, _s in rows]
    seeds = [s for _t, _c, s in rows]
    disc = [i for i, s in enumerate(seeds) if int(s.split("_")[-1]) % 2 == 0]
    conf = [i for i, s in enumerate(seeds) if int(s.split("_")[-1]) % 2 == 1]

    def nll_of(i, mem, s, pad):
        t_in = M.pad_batch([[BOS] + tgts[i][:-1]], device)
        tgt = M.pad_batch([tgts[i]], device)
        logp = net.decode_logp(s, mem, pad, t_in)
        nll = -logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        return nll[tgt.ne(PAD)].mean()

    H, V, B = [], [], []
    MEMS, PADS, SRCS, POSS = [], [], [], []
    for i in range(len(srcs)):
        s = M.pad_batch([srcs[i]], device)
        mem, pad = net.encode(s)
        m2 = mem.clone().requires_grad_(True)
        loss = nll_of(i, m2, s, pad)
        g = torch.autograd.grad(loss, m2)[0]
        pos = int((~pad[0]).sum().item()) - 1
        d = -g[0, pos, :]
        d = d / d.norm().clamp_min(1e-9)
        H.append(mem[0, pos, :].detach())
        V.append(d.detach())
        B.append(float(loss.detach()))
        MEMS.append(mem.detach()); PADS.append(pad); SRCS.append(s); POSS.append(pos)
    H = torch.stack(H); V = torch.stack(V); B = torch.tensor(B)

    def gain(i, vec, k_used=None):
        mem, pad, s, pos = MEMS[i], PADS[i], SRCS[i], POSS[i]
        scale = float(H[i].norm())
        m3 = mem.clone()
        m3[0, pos, :] = m3[0, pos, :] + scale * vec
        with torch.no_grad():
            after = float(nll_of(i, m3, s, pad))
        return B[i].item() - after

    # k sweep on discovery rows only: nearest OTHER discovery rows
    Hd = H[disc]; Vd = V[disc]
    dist = ((Hd[:, None, :] - Hd[None, :, :]) ** 2).sum(-1)
    dist.fill_diagonal_(float("inf"))
    sweep = {}
    for k in KS:
        nn = torch.topk(dist, k=k, largest=False).indices
        g = []
        for j, i in enumerate(disc):
            pred = Vd[nn[j]].mean(0)
            pred = pred / pred.norm().clamp_min(1e-9)
            g.append(gain(i, pred))
        sweep[k] = sum(g) / len(g)
    best_k = max(sweep, key=sweep.get)

    # confirmation: frozen k
    dist_c = ((H[conf][:, None, :] - Hd[None, :, :]) ** 2).sum(-1)
    nn_c = torch.topk(dist_c, k=best_k, largest=False).indices
    g_probe, g_oracle, g_rand, g_class = [], [], [], []
    cell_mean = {}
    for c in sorted({c for row in cells for c in row}):
        idx = [i for i in disc if c in cells[i]]
        if idx:
            v = V[idx].mean(0)
            cell_mean[c] = v / v.norm().clamp_min(1e-9)
    for j, i in enumerate(conf):
        pred = Vd[nn_c[j]].mean(0)
        pred = pred / pred.norm().clamp_min(1e-9)
        g_probe.append(gain(i, pred))
        g_oracle.append(gain(i, V[i]))
        rng = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(cells[i][0].encode()).hexdigest(), 16) % (2 ** 31))
        r = torch.randn(pred.shape, generator=rng).to(device)
        r = r / r.norm().clamp_min(1e-9)
        g_rand.append(gain(i, r))
        cm = cell_mean.get(cells[i][0])
        if cm is not None:
            g_class.append(gain(i, cm))

    import numpy as np
    def stats(x):
        x = np.array(x)
        boot = np.array([np.mean(np.random.choice(x, len(x), replace=True)) for _ in range(1000)])
        return {"mean": round(float(x.mean()), 6), "ci": [round(float(np.percentile(boot, 2.5)), 6),
                                                          round(float(np.percentile(boot, 97.5)), 6)]}
    o = stats(g_oracle)
    return {"seed": seed_name, "k_sweep": {str(k): round(v, 6) for k, v in sweep.items()}, "k_frozen": best_k,
            "conf_rows": len(conf), "oracle": o, "probe": stats(g_probe), "random": stats(g_rand),
            "classmean": stats(g_class) if g_class else None,
            "fraction_of_oracle": round(stats(g_probe)["mean"] / o["mean"], 4) if o["mean"] else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="A4-s1,A4-s2,A4-s3")
    ap.add_argument("--results", default=r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\results\out")
    a = ap.parse_args()
    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    labels = [json.loads(l) for l in open(HERE / "data" / "labels_notation.jsonl", encoding="utf-8") if l.strip()]
    data = {r["text"]: r for r in (json.loads(l) for l in open(HERE / "data" / "notation_new100.jsonl", encoding="utf-8") if l.strip())}
    out = []
    for seed in a.seeds.split(","):
        ckpt = Path(a.results) / seed / "step_01000.pt"
        res = run_seed(seed, ckpt, data, labels, device, vm, cfg)
        out.append(res)
        print(json.dumps(res), flush=True)
    print(json.dumps({"all": out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
