"""Read-back (round-trip) scoring with a FIXED listener: the three original un-finetuned copies, unanimous.

For every fact-situation reply in a generation file, the listeners read the reply back; the read counts only if all
three agree on the same reading and that reading matches the fact the reply was asked about. Non-fact situations are
not read and are not part of the round-trip rate. A fact reply that failed the guard counts as a round-trip failure:
it was never read, so it cannot pass.

    python rt_score.py --gen <jsonl> --out <json>
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG))

from cube_task import target
from mouth_task import roundtrip, vocab_m
from helm_cas_translator import model as M, param_count

FACT = ("ANSWER", "SAYBACK", "ASK")
EAR_COPIES = ("A4-s1",)   # one fixed listener: the ear before mouth training


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch", type=int, default=64)
    a = ap.parse_args()

    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(PKG / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    ears = []
    for name in EAR_COPIES:
        net = M.CTTModel.from_config(len(vm.base), cfg, dropout=0.0).to(device)
        net.load_state_dict(torch.load(str(PKG / "weights" / f"{name}.pt"), map_location=device, weights_only=True))
        net.eval()
        ears.append(net)

    rows = [json.loads(l) for l in open(a.gen, encoding="utf-8") if l.strip()]
    exam = [json.loads(l) for l in open(PKG / "data" / "mouth_exam.jsonl", encoding="utf-8") if l.strip()]
    if len(rows) > len(exam):
        raise SystemExit("more rows than exam items: %d > %d" % (len(rows), len(exam)))
    exam = exam[:len(rows)]
    indexed = list(enumerate(rows))
    fact_rows = [(i, r) for i, r in indexed if r["situation"] in FACT]
    passed = 0
    for start in range(0, len(fact_rows), a.batch):
        batch = fact_rows[start:start + a.batch]
        texts = [r["text"] for _i, r in batch]
        srcs = [vm.base.encode_source(target.DIRECTION, t, [])[0] for t in texts]
        autos = [target.automaton_for(t) for t in texts]
        reads = []
        for net in ears:
            res = M.greedy_locked(net, srcs, autos, vm.tokens, vm.id, device, max_len=48)
            reads.append([target.fill(r["tokens"], t) if r.get("complete") else None for r, t in zip(res, texts)])
        for j, (idx, r) in enumerate(batch):
            reading = exam[idx].get("reading")
            same = reads[0][j]
            ok = bool(r.get("guard_ok")) and same is not None and reading is not None and \
                roundtrip.same_fact(same, reading, r["situation"])
            r["round_trip"] = ok
            passed += int(ok)
        print("%d/%d" % (min(start + a.batch, len(fact_rows)), len(fact_rows)), flush=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in rows:
            if "round_trip" not in r:
                r["round_trip"] = None       # non-fact: not read, not in the round-trip denominator
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"gen": a.gen, "fact_rows": len(fact_rows), "round_trip_pass": passed,
                      "round_trip_rate": round(passed / max(1, len(fact_rows)), 6)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())


