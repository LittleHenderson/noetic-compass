"""The translator's own process: reads proposal requests on stdin, writes proposals on stdout. GPU host only.

Run as a script, isolated:  python -X utf8 -I -B helm_cas_translator/serve.py --weights W --vocab V --config C
                                   --audit AUDIT.json
An audit hook (helm_cas_translator/audit.py) is installed BEFORE torch is imported. It records every file opened
for writing, every network call and every process start; the record is written to the audit file at exit and judged
outside (ctt_ears/client.audit_clean, amendment A-CTT-2: audit log, null device, own temp folder and torch / CUDA
caches allowed; anything under a forbidden root is a violation) (gate H-WRITE). The process reads its weights and vocabulary; it never sees the brain, the store or a receipt.

Request line:  {"batch": [{"id": str, "direction": "A"|"N", "text": str, "context": [record, ...]}, ...]}
Answer line:   {"batch": [{"id": str, "tokens": [str, ...], "complete": bool, "src_len": int,
                           "slots": {...}}, ...]}
End:           {"cmd": "quit"}  -> the audit is written, the process exits 0.
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

from helm_cas_translator import aworld_target, notation_target  # noqa: E402
from helm_cas_translator.vocab import Vocab, context_units  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--config", required=True, help="A4_9p6M or A5_2p5M")
    ap.add_argument("--audit", required=True)
    ap.add_argument("--max-out", type=int, default=128)
    a = ap.parse_args(argv)
    import torch  # noqa: E402  (after the hook)
    from helm_cas_translator import model as M, param_count
    device = M.require_cuda()
    vocab = Vocab.load(a.vocab)
    cfg = param_count.CONFIGS[a.config]
    net = M.CTTModel.from_config(len(vocab), cfg, dropout=0.0).to(device)
    state = torch.load(a.weights, map_location=device, weights_only=True)
    net.load_state_dict(state)
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
        srcs, autos, extra = [], [], []
        for r in rows:
            ids, sl = vocab.encode_source(r["direction"], r["text"], context_units(r.get("context") or []))
            srcs.append(ids)
            q_ok, n_ok = frozenset(sl["q"]), frozenset(sl["n"])
            if r["direction"] == "A":
                c_ok = frozenset("⟦c%d⟧" % k for k in range(1, min(8, len(r.get("context") or [])) + 1))
                autos.append(aworld_target.Automaton(q_ok, n_ok, c_ok))
            else:
                autos.append(notation_target.Automaton(q_ok, n_ok))
            extra.append({"src_len": len(ids), "slots": {"q": sl["q"], "n": sl["n"]}})
        res = M.greedy_locked(net, srcs, autos, vocab.tokens, vocab.id, device, max_len=a.max_out)
        out = [dict(id=r["id"], **res[i], **extra[i]) for i, r in enumerate(rows)]
        sys.stdout.write(json.dumps({"batch": out}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    report = audit.report(weights=os.path.abspath(a.weights))
    with open(a.audit, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
