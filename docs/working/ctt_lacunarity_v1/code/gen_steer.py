"""Reply-quality guard for the steering probe (CAS-LAB-003 §5): baseline vs steered generation.

For one seed: compute oracle directions on the notation DISCOVERY rows only, build a kNN lookup, then for each of 300
exam items take the direction of its nearest notation rows, inject it at the last source position, and decode with the
frozen lock and seeded sampling. Baseline uses the identical decode with no injection.

    python gen_steer.py --seed A4-s1 --rows 300 --out-dir cs_aws/guard
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
from mouth_task import check, lock, sample, vocab_m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="A4-s1")
    ap.add_argument("--rows", type=int, default=300)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--results", default=r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\results\out")
    a = ap.parse_args()

    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(Path(a.results) / a.seed / "step_01000.pt", map_location=device, weights_only=True))
    net.eval()

    # ---- oracle directions on notation DISCOVERY rows only
    labels = [json.loads(l) for l in open(HERE / "data" / "labels_notation.jsonl", encoding="utf-8") if l.strip()]
    ndata = {r["text"]: r for r in (json.loads(l) for l in open(HERE / "data" / "notation_new100.jsonl", encoding="utf-8") if l.strip())}
    rows = [(t, data.get("seed_id", "")) for t, data in ndata.items() if t]
    disc = [i for i, (_t, s) in enumerate(rows) if int(s.split("_")[-1]) % 2 == 0]
    nsrc = [vm.base.encode_source("N", rows[i][0], [])[0] for i in disc]
    ntgt = [vm.base.encode_target(ndata[rows[i][0]]["target"]) for i in disc]

    def nll(i, mem, s, pad):
        t_in = M.pad_batch([[BOS] + ntgt[i][:-1]], device)
        tgt = M.pad_batch([ntgt[i]], device)
        logp = net.decode_logp(s, mem, pad, t_in)
        return (-logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1))[tgt.ne(PAD)].mean()

    Hd, Vd = [], []
    for j in range(len(disc)):
        s = M.pad_batch([nsrc[j]], device)
        mem, pad = net.encode(s)
        m2 = mem.clone().requires_grad_(True)
        loss = nll(j, m2, s, pad)
        g = torch.autograd.grad(loss, m2)[0]
        pos = int((~pad[0]).sum().item()) - 1
        d = -g[0, pos, :]
        Hd.append(mem[0, pos, :].detach())
        Vd.append((d / d.norm().clamp_min(1e-9)).detach())
    Hd = torch.stack(Hd); Vd = torch.stack(Vd)

    # ---- exam items
    items = [json.loads(l) for l in open(HERE / "data" / "mouth_exam.jsonl", encoding="utf-8") if l.strip()][: a.rows]
    function = json.load(open(HERE / "data" / "FUNCTION_WORDS.json", encoding="utf-8"))
    fact_words = set(json.load(open(HERE / "data" / "FACT_WORDS.json", encoding="utf-8")))
    srcs = [vm.encode_mouth_source(it["situation"], tuple(it["tone"]), it["input_text"],
                                   tuple(it["style"]) if it.get("style") else None) for it in items]
    autos = [lock.MouthAutomaton(vm, lock.allowed_words(function, it["input_text"])) for it in items]
    seeds = [sample.seed_of(it["input_text"], it["situation"], str(it.get("turn", ""))) for it in items]

    with torch.no_grad():
        src = M.pad_batch(srcs, device)
        mem, pad = net.encode(src)
        last = (pad.logical_not().sum(1) - 1)
        h = mem[torch.arange(len(items)), last, :].clone()
    scale = h.norm(dim=1)
    dist = ((h[:, None, :] - Hd[None, :, :]) ** 2).sum(-1)
    nn = torch.topk(dist, k=min(a.k, len(Hd)), largest=False).indices
    dirs = [Vd[nn[i]].mean(0) for i in range(len(items))]
    dirs = [d / d.norm().clamp_min(1e-9) for d in dirs]

    def decode(inject):
        import torch
        gens = []
        for s in seeds:
            g = torch.Generator(device=device)
            g.manual_seed(int(s))
            gens.append(g)
        with torch.no_grad():
            s0 = M.pad_batch(srcs, device)
            m0, sp = net.encode(s0)
            if inject:
                for i in range(len(items)):
                    p = int(last[i].item())
                    m0[i, p, :] = m0[i, p, :] + a.dose * scale[i] * dirs[i]
            b = len(srcs)
            tgt = torch.full((b, 1), 1, dtype=torch.long, device=device)
            done = [False] * b
            out = [[] for _ in range(b)]
            cache = {}
            for _ in range(64):
                logp = net.decode_logp(s0, m0, sp, tgt)[:, -1, :]
                nxt = torch.zeros((b,), dtype=torch.long, device=device)
                for i in range(b):
                    if done[i]:
                        continue
                    allowed = autos[i].allowed()
                    if not allowed:
                        done[i] = True
                        continue
                    m = cache.get(allowed)
                    if m is None:
                        m = torch.full((net.vocab_size,), float("-inf"), device=device)
                        m[torch.tensor([vm.id[t] for t in allowed], device=device)] = 0.0
                        cache[allowed] = m
                    scores = logp[i] + m
                    probs = torch.softmax(scores, dim=-1)
                    srt, si = torch.sort(probs, descending=True)
                    keep = torch.cumsum(srt, dim=-1) - srt < 0.9
                    srt = srt * keep
                    srt = srt / srt.sum()
                    k = int(si[torch.multinomial(srt, 1, generator=gens[i])].item())
                    tok = vm.tokens[k]
                    autos[i].step(tok)
                    nxt[i] = k
                    if tok == "[EOS]":
                        done[i] = True
                    else:
                        out[i].append(tok)
                tgt = torch.cat([tgt, nxt.unsqueeze(1)], dim=1)
                del logp
                torch.cuda.empty_cache()
                if all(done):
                    break
        return out

    # fresh automata per condition
    def run(inject, tag):
        for i, it in enumerate(items):
            autos[i] = lock.MouthAutomaton(vm, lock.allowed_words(function, it["input_text"]))
        toks = decode(inject)
        path = Path(a.out_dir) / f"gen_{a.seed}_{tag}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for it, t in zip(items, toks):
                done_flag = bool(getattr(autos[len(fh_lines)], "ended", False)) if False else True
                fh.write(json.dumps({"id": it.get("id") or it.get("input_key"), "situation": it["situation"],
                                     "input_text": it["input_text"], "text": vocab_m.detokenize(t, {}),
                                     "complete": True}, ensure_ascii=False) + "\n")
        print(tag, "written", path, flush=True)

    run(True, "steered_d%g" % a.dose)
    return 0


if __name__ == "__main__":
    sys.exit(main())


