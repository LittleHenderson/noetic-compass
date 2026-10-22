"""cube_task/cube_serve.py -- the audited decoding process for the cube task (direction [B]). GPU host only.

    python -X utf8 -I -B cube_task/cube_serve.py --weights W --vocab V --config C --audit AUDIT.json

Like helm_cas_translator/serve.py: the write-audit hook is installed BEFORE torch is imported; requests come on stdin,
answers go to stdout; the process writes nothing but its audit file at exit.
Request line:  {"batch": [{"id": str, "text": str}, ...]}   Answer line: {"batch": [{"id", "tokens", "complete"}]}
End:           {"cmd": "quit"}
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from helm_cas_translator import audit  # noqa: E402  (stdlib only; installed before anything else is imported)

audit.install()

import argparse  # noqa: E402
import json  # noqa: E402

from cube_task import target  # noqa: E402
from helm_cas_translator.vocab import Vocab  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--max-out", type=int, default=48)
    a = ap.parse_args(argv)
    import torch  # noqa: E402  (after the hook)
    from helm_cas_translator import model as M, param_count
    device = M.require_cuda()
    vocab = Vocab.load(a.vocab)
    cfg = param_count.CONFIGS[a.config]
    net = M.CTTModel.from_config(len(vocab), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.weights, map_location=device, weights_only=True))
    M.assert_parameter_count(net, len(vocab), cfg)
    net.eval()
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
        rows = req["batch"]
        srcs = [vocab.encode_source(target.DIRECTION, r["text"], [])[0] for r in rows]
        autos = [target.automaton_for(r["text"]) for r in rows]
        res = M.greedy_locked(net, srcs, autos, vocab.tokens, vocab.id, device, max_len=a.max_out)
        out = [{"id": r["id"], "tokens": res[i]["tokens"], "complete": res[i]["complete"]} for i, r in enumerate(rows)]
        sys.stdout.write(json.dumps({"batch": out}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    report = audit.report(weights=os.path.abspath(a.weights))
    with open(a.audit, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
