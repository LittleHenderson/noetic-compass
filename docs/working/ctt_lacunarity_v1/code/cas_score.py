"""Score cas_val rows with one checkpoint and report per-Noetic error."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG))
from helm_cas_translator import model as M, param_count
from helm_cas_translator.vocab import BOS, PAD, context_units
from mouth_task.vocab_m import VocabM, base

NOETICS = tuple("^%d" % i for i in range(10))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rows", type=int, default=0)
    ap.add_argument("--file", default="cas_val.jsonl")
    ap.add_argument("--rows-out", default=None)
    ap.add_argument("--batch", type=int, default=64)
    a = ap.parse_args()
    import torch
    device = M.require_cuda()
    vm = VocabM(base(str(PKG / "data" / "vocab.json")))
    vocab = vm.base
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.checkpoint, map_location=device, weights_only=True))
    net.eval()
    rows = [json.loads(l) for l in open(PKG / "data" / a.file, encoding="utf-8") if l.strip()]
    if a.rows:
        rows = rows[: a.rows]
    sums = {n: [0.0, 0] for n in NOETICS}
    per_row = []
    total = [0.0, 0]
    with torch.no_grad():
        for start in range(0, len(rows), a.batch):
            batch = rows[start:start + a.batch]
            pairs = [(vocab.encode_source(r["direction"], r["text"], context_units(r.get("context") or []))[0],
                      vocab.encode_target(r["target"])) for r in batch]
            src = M.pad_batch([s for s, _t in pairs], device)
            tgt_out = M.pad_batch([t for _s, t in pairs], device)
            tgt_in = M.pad_batch([[BOS] + t[:-1] for _s, t in pairs], device)
            logp = net(src, tgt_in)
            nll = -logp.gather(-1, tgt_out.unsqueeze(-1)).squeeze(-1)
            mask = tgt_out.ne(PAD)
            for j, r in enumerate(batch):
                vec = nll[j][mask[j]].tolist()
                if not vec:
                    continue
                m = sum(vec) / len(vec)
                total[0] += m
                total[1] += 1
                addr = {t for t in r["target"] if t in NOETICS}
                per_row.append((m, addr, r.get("text", ""), r.get("seed_id")))
                for n in NOETICS:
                    if n in addr:
                        sums[n][0] += m
                        sums[n][1] += 1
    row_out = []
    for r, (nllv, addr, txt, sid) in zip(rows, per_row):
        row_out.append({"text": txt, "seed_id": sid, "nll": round(nllv, 9), "noetics": sorted(addr)})
    if a.rows_out:
        json.dump(row_out, open(a.rows_out, "w", encoding="utf-8"))
    out = {"checkpoint": a.checkpoint, "rows": total[1], "mean_row_nll": round(total[0] / max(1, total[1]), 6),
           "by_noetic": {n: {"rows": c, "mean_row_nll": round(s / c, 6) if c else None}
                         for n, (s, c) in sums.items()}}
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())




