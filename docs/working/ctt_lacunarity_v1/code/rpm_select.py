"""RPM-guided selector test (CAS-LAB-007).

Five selectors choose which discovery rows contribute to a steering direction for each confirmation row:
  D1 unguided kNN (memory distance), D2 same-cell, D3 same-operator, D4 distance x requirement-concentration
  weight, D5 random rows. Same k, same checkpoint, same split; only the selection rule changes.

    python rpm_select.py --checkpoint <pt> --out results.json
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

K = 10


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.checkpoint, map_location=device, weights_only=True))
    net.eval()

    labels = [json.loads(l) for l in open(HERE / "data" / "labels_notation.jsonl", encoding="utf-8") if l.strip()]
    data = {r["text"]: r for r in (json.loads(l) for l in open(HERE / "data" / "notation_new100.jsonl", encoding="utf-8") if l.strip())}
    rows = [(r["text"], r["cells"], data[r["text"]].get("seed_id", "")) for r in labels if r["text"] in data]
    srcs = [vm.base.encode_source("N", t, [])[0] for t, _c, _s in rows]
    tgts = [vm.base.encode_target(data[t]["target"]) for t, _c, _s in rows]
    cells = [c for _t, c, _s in rows]
    ops = []
    for t, _c, _s in rows:
        toks = data[t]["target"]
        ops.append("x" if "×" in toks else ("arrow" if "→" in toks else "other"))
    disc = [i for i, (_t, _c, s) in enumerate(rows) if int(s.split("_")[-1]) % 2 == 0]
    conf = [i for i, (_t, _c, s) in enumerate(rows) if int(s.split("_")[-1]) % 2 == 1]

    def nll(i, mem, s, pad):
        t_in = M.pad_batch([[BOS] + tgts[i][:-1]], device)
        tgt = M.pad_batch([tgts[i]], device)
        logp = net.decode_logp(s, mem, pad, t_in)
        return ((-logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1))[tgt.ne(PAD)].mean())

    H, V, MEM = [], [], []
    for i in range(len(srcs)):
        s = M.pad_batch([srcs[i]], device)
        mem, pad = net.encode(s)
        pos = int((~pad[0]).sum().item()) - 1
        H.append(mem[0, pos, :].detach())
        MEM.append((mem.detach(), pad, s, pos))
        m2 = mem.clone().requires_grad_(True)
        loss = nll(i, m2, s, pad)
        g = torch.autograd.grad(loss, m2)[0]
        d = -g[0, pos, :]
        V.append((d / d.norm().clamp_min(1e-9)).detach())
    H = torch.stack(H); V = torch.stack(V)          # oracle directions for EVERY row
    Vd = V[disc]                                     # selection pool: discovery rows only
    assert V.shape[0] == len(srcs), (V.shape, len(srcs))
    assert Vd.shape[0] == len(disc), (Vd.shape, len(disc))

    def gain(i, vec):
        mem, pad, s, pos = MEM[i]
        m3 = mem.clone()
        m3[0, pos, :] = m3[0, pos, :] + float(H[i].norm()) * vec
        with torch.no_grad():
            return float(nll(i, mem, s, pad)) - float(nll(i, m3, s, pad))

    # distance matrix conf x disc
    d2 = ((H[conf][:, None, :] - H[disc][None, :, :]) ** 2).sum(-1)
    sigma2 = float(torch.median(d2)) + 1e-9
    results = {name: [] for name in ("D1", "D2", "D3", "D4", "D5", "oracle")}
    for j, i in enumerate(conf):
        d1 = d2[j]
        def pick(idx):
            if not idx:
                return None
            sub = d1[torch.tensor(idx, device=device)]
            kk = min(K, len(idx))
            loc = torch.topk(sub, k=kk, largest=False).indices
            return Vd[torch.tensor([idx[z] for z in loc.tolist()], device=device)].mean(0)
        cand = {
            "D1": list(range(len(disc))),
            "D2": [z for z, gi in enumerate(disc) if cells[gi] and cells[i] and cells[gi][0] == cells[i][0]],
            "D3": [z for z, gi in enumerate(disc) if ops[gi] == ops[i]],
            "D5": None,
        }
        for name, idx in cand.items():
            if name == "D5":
                g = torch.Generator(device="cpu").manual_seed(int(hashlib.sha256(str(i).encode()).hexdigest(), 16) % (2 ** 31))
                sel = torch.randperm(len(disc), generator=g)[:K].to(device)
                v = Vd[sel].mean(0)
            else:
                v = pick(idx)
            if v is None:
                continue
            v = v / v.norm().clamp_min(1e-9)
            results[name].append(gain(i, v))
        w = torch.exp(-d1 / sigma2) * torch.tensor([1.0 / max(1, len(cells[gi])) for gi in disc], device=device)
        v = (Vd * w.unsqueeze(1)).sum(0)
        v = v / v.norm().clamp_min(1e-9)
        results["D4"].append(gain(i, v))
        results["oracle"].append(gain(i, V[i]))

    def mean(x):
        return round(sum(x) / len(x), 6) if x else None
    out = {k: mean(v) for k, v in results.items()}
    out["fraction_D1"] = round(out["D1"] / out["oracle"], 4) if out["oracle"] else None
    for name in ("D2", "D3", "D4", "D5"):
        if out[name] is not None and out["oracle"]:
            out["fraction_" + name] = round(out[name] / out["oracle"], 4)
            out["ratio_vs_D1_" + name] = round(out["fraction_" + name] / out["fraction_D1"], 4) if out["fraction_D1"] else None
    out["k"] = K
    out["rows"] = len(conf)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())






