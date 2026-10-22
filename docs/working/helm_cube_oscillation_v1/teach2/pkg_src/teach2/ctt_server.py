"""teach2/ctt_server.py -- the audited serving process of the CTT copies for one TEACH-2 unit (A-TEACH2-18 P2). GPU only.

    python -X utf8 -I -B teach2/ctt_server.py --copy A4-s1=<weights>:<config> [--copy ...] --vocab V --audit AUDIT.json

The CUBE TRAIN decoder (ctt/cube_task/cube_serve.py) in one process for several copies: the same write-audit hook,
installed BEFORE torch is imported (helm_cas_translator.audit); the same grammar-locked greedy decoding in direction
[B] (helm_cas_translator.model.greedy_locked, cube_task.target.automaton_for); the same require_cuda() (no CPU
fallback). One request decodes the given lines with every named copy; nothing is cached between requests, so every
round of the oscillation decodes again.
Request line:  {"copies": [name, ...], "texts": [str, ...]}
Answer line:   {"outputs": {name: [str, ...]}}   -- each str is cube_task.target.fill(...) ("NONE", the four-field
               reading HELM's adapter reads), or "" when the decode was incomplete or malformed (no reading)
End:           {"cmd": "quit"}    The process writes nothing but its audit file, at exit.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CTT = os.path.join(os.path.dirname(HERE), "ctt")
sys.path.insert(0, CTT)

from helm_cas_translator import audit  # noqa: E402  (stdlib only; installed before anything else is imported)

audit.install()

import argparse  # noqa: E402
import json  # noqa: E402

from cube_task import target  # noqa: E402
from helm_cas_translator.vocab import Vocab  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", action="append", required=True, help="name=weights_path:config")
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--max-out", type=int, default=48)
    a = ap.parse_args(argv)
    import torch  # noqa: E402  (after the hook)
    from helm_cas_translator import model as M, param_count
    device = M.require_cuda()
    vocab = Vocab.load(a.vocab)
    nets = {}
    for spec in a.copy:
        name, rest = spec.split("=", 1)
        weights, config = rest.rsplit(":", 1)
        cfg = param_count.CONFIGS[config]
        net = M.CTTModel.from_config(len(vocab), cfg, dropout=0.0).to(device)
        net.load_state_dict(torch.load(weights, map_location=device, weights_only=True))
        M.assert_parameter_count(net, len(vocab), cfg)
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
        texts = list(req["texts"])
        out = {}
        for name in req["copies"]:
            srcs = [vocab.encode_source(target.DIRECTION, t, [])[0] for t in texts]
            autos = [target.automaton_for(t) for t in texts]
            res = M.greedy_locked(nets[name], srcs, autos, vocab.tokens, vocab.id, device, max_len=a.max_out)
            row = []
            for i, t in enumerate(texts):
                filled = target.fill(res[i]["tokens"], t) if res[i]["complete"] else None
                row.append(filled or "")
            out[name] = row
        sys.stdout.write(json.dumps({"outputs": out}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    report = audit.report(copies=sorted(nets))
    with open(a.audit, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
