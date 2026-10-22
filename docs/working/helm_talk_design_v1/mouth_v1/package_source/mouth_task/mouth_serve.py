"""mouth_task/mouth_serve.py -- the audited process that writes with the mouth and reads back with the ear (A-TALK-4
W4, W5). GPU only.

    python -X utf8 -I -B mouth_task/mouth_serve.py --copy A4-s1=<weights>:<config> [--copy ...] --audit AUDIT.json

The write-audit hook is installed before torch is imported (helm_cas_translator.audit). Requests on stdin, one per line:
  {"mode": "mouth", "copy": name, "top_p": p, "items": [{"id", "situation", "tone": [state, register], "input_text",
   "turn", "names": {lower: Written}}]}  -> {"outputs": [{"id", "tokens", "complete", "text"}]}
  {"mode": "ear", "copies": [names], "texts": [str]}  -> {"outputs": {name: [the [B] reading string or ""]}}
  {"cmd": "quit"}
The mouth writes under the whole-word lock (mouth_task.lock) with seeded top-p sampling (mouth_task.sample); the ear
reads with its own grammar lock, greedy (cube_task.target). Nothing is written but the audit file, at exit.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, PKG)

from helm_cas_translator import audit  # noqa: E402

audit.install()

import argparse  # noqa: E402
import json  # noqa: E402

from cube_task import target  # noqa: E402
from helm_cas_translator import aworld_target, notation_target  # noqa: E402
from helm_cas_translator.vocab import context_units  # noqa: E402
from mouth_task import lock, sample, vocab_m  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", action="append", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--max-out", type=int, default=64)
    a = ap.parse_args(argv)
    import torch  # noqa: E402  (after the hook)
    from helm_cas_translator import model as M, param_count
    device = M.require_cuda()
    vm = vocab_m.load(os.path.join(PKG, "data", "vocab.json"))
    function = json.load(open(os.path.join(PKG, "data", "FUNCTION_WORDS.json"), encoding="utf-8"))
    nets = {}
    for spec in a.copy:
        name, rest = spec.split("=", 1)
        weights, config = rest.rsplit(":", 1)
        cfg = param_count.CONFIGS[config]
        net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
        net.load_state_dict(torch.load(weights, map_location=device, weights_only=True))
        M.assert_parameter_count(net, len(vm), cfg)
        net.eval()
        nets[name] = net
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        if req.get("cmd") == "quit":
            break
        if req["mode"] == "mouth":
            items = req["items"]
            srcs = [vm.encode_mouth_source(it["situation"], tuple(it["tone"]), it["input_text"]) for it in items]
            autos = [lock.MouthAutomaton(vm, lock.allowed_words(function, it["input_text"])) for it in items]
            seeds = [sample.seed_of(it["input_text"], it["situation"], str(it.get("turn", ""))) for it in items]
            res = sample.sample_locked(nets[req["copy"]], srcs, autos, vm.tokens, vm.id, device, seeds,
                                       top_p=float(req.get("top_p", 0.9)), max_len=a.max_out)
            out = []
            for it, r in zip(items, res):
                text = vocab_m.detokenize(r["tokens"], it.get("names") or {}) if r["complete"] else ""
                out.append({"id": it["id"], "tokens": r["tokens"], "complete": r["complete"], "text": text})
            sys.stdout.write(json.dumps({"outputs": out}, ensure_ascii=False) + "\n")
        elif req["mode"] == "ear":
            texts = list(req["texts"])
            out = {}
            for name in req["copies"]:
                srcs = [vm.base.encode_source(target.DIRECTION, t, [])[0] for t in texts]
                autos = [target.automaton_for(t) for t in texts]
                res = M.greedy_locked(nets[name], srcs, autos, vm.tokens, vm.id, device, max_len=48)
                out[name] = [{"tokens": res[i]["tokens"], "complete": res[i]["complete"]} for i in range(len(texts))]
            sys.stdout.write(json.dumps({"outputs": out}, ensure_ascii=False) + "\n")
        else:                                   # "cas": the kept CAS directions [A] / [N], as helm_cas_translator/serve.py
            rows = req["batch"]
            srcs, autos = [], []
            for r in rows:
                ids, sl = vm.base.encode_source(r["direction"], r["text"], context_units(r.get("context") or []))
                srcs.append(ids)
                q_ok, n_ok = frozenset(sl["q"]), frozenset(sl["n"])
                if r["direction"] == "A":
                    c_ok = frozenset("⟦c%d⟧" % k for k in range(1, min(8, len(r.get("context") or [])) + 1))
                    autos.append(aworld_target.Automaton(q_ok, n_ok, c_ok))
                else:
                    autos.append(notation_target.Automaton(q_ok, n_ok))
            res = M.greedy_locked(nets[req["copy"]], srcs, autos, vm.tokens, vm.id, device, max_len=128)
            out = [{"id": r["id"], "tokens": res[i]["tokens"], "complete": res[i]["complete"]} for i, r in enumerate(rows)]
            sys.stdout.write(json.dumps({"batch": out}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    report = audit.report(copies=sorted(nets))
    with open(a.audit, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
