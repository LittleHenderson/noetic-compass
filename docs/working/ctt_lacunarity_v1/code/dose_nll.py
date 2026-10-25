"""Notation-error gain at several doses (CAS-LAB-005 secondary outcome).

Builds the kNN direction from notation DISCOVERY rows, then applies it at each dose to the confirmation rows and
reports the fraction of the full-dose probe gain retained.

    python dose_nll.py --checkpoint <pt> --doses 0.05,0.1,0.2,0.4,1.0
"""
from __future__ import annotations

import argparse
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
    ap.add_argument("--doses", default="0.05,0.1,0.2,0.4,1.0")
    ap.add_argument("--k", type=int, default=10)
    a = ap.parse_args()

    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.checkpoint, map_location=device, weights_only=True))
    net.eval()

    ndata = {r["text"]: r for r in (json.loads(l) for l in open(HERE / "data" / "notation_new100.jsonl", encoding="utf-8") if l.strip())}
    rows = [(t, r.get("seed_id", "")) for t, r in ndata.items()]
    disc = [i for i, (_t, s) in enumerate(rows) if int(s.split("_")[-1]) % 2 == 0]
    conf = [i for i, (_t, s) in enumerate(rows) if int(s.split("_")[-1]) % 2 == 1]
    srcs = [vm.base.encode_source("N", rows[i][0], [])[0] for i in disc + conf]
    tgts = [vm.base.encode_target(ndata[rows[i][0]]["target"]) for i in disc + conf]

    def nll(idx, mem, s, pad):
        t_in = M.pad_batch([[BOS] + tgts[idx][:-1]], device)
        tgt = M.pad_batch([tgts[idx]], device)
        logp = net.decode_logp(s, mem, pad, t_in)
        return ((-logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1))[tgt.ne(PAD)].mean())

    H, V, MEM, B = [], [], [], []
    for j in range(len(disc)):
        s = M.pad_batch([srcs[j]], device)
        mem, pad = net.encode(s)
        m2 = mem.clone().requires_grad_(True)
        loss = nll(j, m2, s, pad)
        g = torch.autograd.grad(loss, m2)[0]
        pos = int((~pad[0]).sum().item()) - 1
        d = -g[0, pos, :]
        H.append(mem[0, pos, :].detach()); V.append((d / d.norm().clamp_min(1e-9)).detach())
        MEM.append((mem.detach(), pad, s, pos)); B.append(loss.item() if isinstance(loss, float) else float(loss))
    H = torch.stack(H); V = torch.stack(V)

    def gain(idx_global, j_local):
        mem, pad, s, pos = MEM[j_local]
        scale = float(H[j_local].norm())
        base = B[j_local]
        return mem, pad, s, pos, scale, base

    doses = [float(x) for x in a.doses.split(",")]
    # oracle + kNN prep
    out = {}
    per_dose = {d: [] for d in doses}
    for j, gi in enumerate(conf):
        mem, pad = net.encode(M.pad_batch([srcs[len(disc) + j]], device))
        with torch.no_grad():
            h = mem[0, int((~pad[0]).sum().item()) - 1, :]
        dist = ((H - h) ** 2).sum(1)
        nn = torch.topk(dist, k=min(a.k, len(H)), largest=False).indices
        v = V[nn].mean(0); v = v / v.norm().clamp_min(1e-9)
        pos = int((~pad[0]).sum().item()) - 1
        base = float(nll(len(disc) + j, mem, M.pad_batch([srcs[len(disc) + j]], device), pad))
        s = M.pad_batch([srcs[len(disc) + j]], device)
        for d in doses:
            m3 = mem.clone()
            m3[0, pos, :] = m3[0, pos, :] + d * float(h.norm()) * v
            with torch.no_grad():
                after = float(nll(len(disc) + j, m3, s, pad))
            per_dose[d].append(base - after)
    res = {str(d): round(sum(v) / len(v), 6) for d, v in per_dose.items()}
    full = res[str(max(doses))] if str(max(doses)) in res else None
    frac = {d: round(v / full, 4) for d, v in res.items()} if full else {}
    print(json.dumps({"gains": res, "fraction_of_full": frac}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())


