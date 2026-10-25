"""Learned cell-directed probe (v3) — can a map learned offline predict the gradient direction without the answer?

For every row we compute the oracle direction: -grad_mem(NLL) at the last source position. That uses the gold target,
so it is an upper bound only. We then learn a ridge map from the row's pooled memory to that direction on a discovery
half, and apply the predicted direction on the untouched half. Three comparisons on the same rows:

  oracle    : the true gradient (upper bound, uses the answer)
  probe     : W @ h, learned on discovery rows only (deployable; no answer)
  classmean : mean oracle direction of the row's cell, from discovery rows (deployable)
  random    : matched norm, seeded (control)

    python cell_probe.py --checkpoint <pt> --lam 1.0
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
    ap.add_argument("--lam", type=float, default=1.0)
    ap.add_argument("--knn", type=int, default=0)
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
    cells_by_text = {r["text"]: r["cells"] for r in labels}
    rows = [(t, cells_by_text[t], data[t].get("seed_id", "row_%d" % i))
            for i, t in enumerate(data) if t in cells_by_text]
    texts = [t for t, _c, _s in rows]
    srcs = [vm.base.encode_source("N", t, [])[0] for t in texts]
    tgts = [vm.base.encode_target(data[t]["target"]) for t in texts]
    cells = [c for _t, c, _s in rows]
    seeds = [s for _t, _c, s in rows]
    # discovery = even source index, confirmation = odd, so no source is in both halves
    disc = [i for i, s in enumerate(seeds) if (int(s.split("_")[-1]) % 2 == 0)]
    conf = [i for i, s in enumerate(seeds) if (int(s.split("_")[-1]) % 2 == 1)]

    def nll_of(i, mem, s, pad):
        t_in = M.pad_batch([[BOS] + tgts[i][:-1]], device)
        tgt = M.pad_batch([tgts[i]], device)
        logp = net.decode_logp(s, mem, pad, t_in)
        nll = -logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        return nll[tgt.ne(PAD)].mean()

    def oracle(i):
        s = M.pad_batch([srcs[i]], device)
        mem, pad = net.encode(s)
        m2 = mem.clone().requires_grad_(True)
        loss = nll_of(i, m2, s, pad)
        g = torch.autograd.grad(loss, m2)[0]
        pos = int((~pad[0]).sum().item()) - 1
        d = -g[0, pos, :]
        return mem.detach(), pad, s, pos, d / d.norm().clamp_min(1e-9), float(loss)

    H, V, base_nll = [], [], {}
    MEMS, PADS, SRCS, POSS = [], [], [], []
    for i in range(len(srcs)):
        mem, pad, s, pos, d, b = oracle(i)
        m = (~pad).unsqueeze(-1).float()
        H.append(mem[0, pos, :])
        V.append(d)
        base_nll[i] = b
        MEMS.append(mem); PADS.append(pad); SRCS.append(s); POSS.append(pos)
    H = torch.stack(H)
    V = torch.stack(V)

    Xd, Vd = H[disc], V[disc]
    lam = a.lam
    A = Xd.T @ Xd + lam * torch.eye(Xd.size(1), device=device)
    W = torch.linalg.solve(A, Xd.T @ Vd)          # (d, d)

    # class-mean directions from discovery rows only
    cell_mean = {}
    for c in sorted({c for row in cells for c in row}):
        idx = [i for i in disc if c in cells[i]]
        if idx:
            v = V[idx].mean(0)
            cell_mean[c] = v / v.norm().clamp_min(1e-9)

    def apply(i, vec):
        mem, pad, s, pos = MEMS[i], PADS[i], SRCS[i], POSS[i]
        scale = float(H[i].norm())
        m3 = mem.clone()
        m3[0, pos, :] = m3[0, pos, :] + scale * vec
        with torch.no_grad():
            return float(nll_of(i, m3, s, pad))

    out = []
    for i in conf:
        if a.knn:
            d2 = ((H[disc] - H[i]) ** 2).sum(1)
            nn = torch.topk(d2, k=min(a.knn, len(disc)), largest=False).indices
            pred = V[disc][nn].mean(0)
        else:
            pred = W @ H[i]
        pred = pred / pred.norm().clamp_min(1e-9)
        rng = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(cells[i][0].encode()).hexdigest(), 16) % (2 ** 31))
        r = torch.randn(pred.shape, generator=rng).to(device)
        r = r / r.norm().clamp_min(1e-9)
        cm = cell_mean.get(cells[i][0])
        b = base_nll[i]
        out.append({"cells": cells[i], "baseline": b,
                    "oracle": apply(i, V[i]), "probe": apply(i, pred),
                    "classmean": apply(i, cm) if cm is not None else None, "random": apply(i, r)})

    def mean(key):
        vals = [o[key] for o in out if o[key] is not None]
        return sum(vals) / len(vals)

    res = {"rows": len(out), "baseline": round(mean("baseline"), 6), "oracle": round(mean("oracle"), 6),
           "probe": round(mean("probe"), 6), "classmean": round(mean("classmean"), 6),
           "random": round(mean("random"), 6)}
    res["gain_oracle"] = round(res["baseline"] - res["oracle"], 6)
    res["gain_probe"] = round(res["baseline"] - res["probe"], 6)
    res["gain_classmean"] = round(res["baseline"] - res["classmean"], 6)
    res["gain_random"] = round(res["baseline"] - res["random"], 6)
    res["probe_fraction_of_oracle"] = round(res["gain_probe"] / res["gain_oracle"], 4) if res["gain_oracle"] else None
    res["lam"] = lam
    res["checkpoint"] = a.checkpoint
    print(json.dumps(res, indent=1))
    Path(HERE / ".." / "cs_aws").resolve()
    return 0


if __name__ == "__main__":
    sys.exit(main())




