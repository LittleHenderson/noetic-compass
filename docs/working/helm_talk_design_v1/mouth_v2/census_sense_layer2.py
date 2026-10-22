"""census_sense_layer2.py -- A-TALK-7 H1 F3 layer 2 census (laptop GPU, smoke-size, 0 USD). Builder tool, not in the package.

Question: does the CTT's own confidence in a line it wrote (average log-probability per piece, teacher-forced, under
the c59 mouth weights A4-s1 and v1's source encoding) separate the lines the blind raters rejected from the ones they
preferred? The decision rule was frozen in A-TALK-7 before this census: layer 2 joins the guard only if, at ONE
threshold, it rejects at least half of the rater-rejected chat lines that layer 1 misses while rejecting at most 5 %
of the rater-preferred lines (all situations). Otherwise it is reported and left out.

    <cas-gpu python> -X utf8 -B census_sense_layer2.py <c59 A4-s1 final.pt>
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1 = os.path.join(os.path.dirname(HERE), "mouth_v1")
sys.path.insert(0, os.path.join(V1, "package_source"))           # the code c59 was trained with
import torch  # noqa: E402
from helm_cas_translator import model as M, param_count  # noqa: E402
from mouth_task import check, vocab_m  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "package_source"))


def main(weights: str) -> None:
    dev = M.require_cuda()
    vm = vocab_m.load(os.path.join(V1, "package_source", "data", "vocab.json"))
    net = M.CTTModel.from_config(len(vm), param_count.CONFIGS["A4_9p6M"], dropout=0.0).to(dev)
    net.load_state_dict(torch.load(weights, map_location=dev, weights_only=True))
    net.eval()
    pairs = json.load(open(os.path.join(V1, "rate", "PAIRS.json"), encoding="utf-8"))["pairs"]
    R = {f: json.load(open(os.path.join(V1, "rate", f"ratings_{f}.json"), encoding="utf-8"))["ratings"]
         for f in ("anthropic", "openai", "deepseek")}
    exam = {json.loads(l)["input_key"]: json.loads(l) for l in open(os.path.join(V1, "package_source", "data",
                                                                                 "mouth_exam.jsonl"), encoding="utf-8")}
    # the layer-1 rule exactly as frozen in the v2 package
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_v2", os.path.join(HERE, "package_source", "mouth_task", "check.py"))
    check2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check2)
    rows = []
    for p in pairs:
        x = exam[p["id"].rsplit("#", 1)[0]]
        line = p[p["mouth"]]
        src = vm.encode_mouth_source(x["situation"], tuple(x["tone"]), x["input_text"])
        tgt = vm.encode_mouth_target(line)
        with torch.no_grad():
            s = M.pad_batch([src], dev)
            mem, sp = net.encode(s)
            tin = torch.tensor([[1] + tgt[:-1]], device=dev)
            lp = net.decode_logp(s, mem, sp, tin)[0]
            score = float(lp[torch.arange(len(tgt), device=dev), torch.tensor(tgt, device=dev)].mean())
        won = sum(R[f].get(p["id"]) == p["mouth"] for f in R) >= 2
        rows.append({"id": p["id"], "situation": p["situation"], "won": won, "l1_ok": check2.sense_ok(line)[0],
                     "score": score})
    chat = ("OFF", "SMALL", "SELF", "WORLD")
    target = [r for r in rows if r["situation"] in chat and not r["won"] and r["l1_ok"]]
    liked = [r for r in rows if r["won"]]
    best = None
    for th in sorted({round(r["score"], 3) for r in rows}):
        caught = sum(1 for r in target if r["score"] < th)
        false = sum(1 for r in liked if r["score"] < th)
        if false <= 0.05 * len(liked) and (best is None or caught > best[1]):
            best = (th, caught, false)
    holds = best is not None and best[1] >= 0.5 * len(target)
    out = {"schema": "mouth-v2.sense-layer2-census/1", "weights": os.path.basename(os.path.dirname(weights)),
           "pairs": len(rows), "chat_rejected_layer1_missed": len(target), "rater_preferred": len(liked),
           "best_threshold": best[0] if best else None, "caught": best[1] if best else 0,
           "wrongly_rejected": best[2] if best else 0, "rule": ">= half caught, <= 5 % of preferred rejected",
           "joins_the_guard": holds,
           "mean_score": {k: round(sum(r["score"] for r in rows if (r["won"] if k == "won" else not r["won"])) /
                                   max(1, sum(1 for r in rows if (r["won"] if k == "won" else not r["won"]))), 4)
                          for k in ("won", "lost")}}
    with open(os.path.join(HERE, "SENSE_LAYER2_CENSUS.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
