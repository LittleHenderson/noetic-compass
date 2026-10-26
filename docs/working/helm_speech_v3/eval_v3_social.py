"""Evaluate the v3 mouth on social tags: guard pass, variety, and what it actually says.

The fact lock is wrong for small talk (it only permits words from the input), so this uses a permissive mask: any
English piece or punctuation. The guard still decides whether a reply is acceptable, which is the point — the lock is
not the safety mechanism, the check is.

    python eval_v3_social.py --ckpt final.pt --out results.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helm_cas_translator import model as M, param_count
from mouth_task import check, vocab_m
from speech_tags_v2 import TAGS, TONES

SOCIAL = ["GREETING", "EMPATHY", "SMALLTALK", "ENCOURAGE", "THANKS", "FAREWELL", "PLAYFUL", "APOLOGY",
          "CONGRATS", "REASSURANCE", "CLARIFY", "CONFIRM", "CORRECT", "HEDGE", "REFUSE_POLITE", "EXPLAIN",
          "STATUS", "PLAN", "WARN", "SUGGEST", "SELF", "CONDOLENCE"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="final.pt")
    ap.add_argument("--out", default="results.json")
    a = ap.parse_args()
    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.ckpt, map_location=device, weights_only=True))
    net.eval()
    fact_words = set(json.load(open(HERE / "data" / "FACT_WORDS.json", encoding="utf-8")))

    eos_id = vm.id["[EOS]"]
    allowed = [i for i, t in enumerate(vm.tokens) if t.startswith("en:") or t in (".", ",", "?", "!", ";", ":", "'")]
    allowed.append(eos_id)
    mask = torch.full((len(vm.tokens),), float("-inf"), device=device)
    mask[torch.tensor(allowed, device=device)] = 0.0
    eos = vm.id["[EOS]"]

    def speak(tag, text, seed):
        src = vm.encode_mouth_source(tag, TONES[seed % len(TONES)], text, None, None)
        s = M.pad_batch([src], device)
        mem, pad = net.encode(s)
        toks = [1]
        g = torch.Generator(device=device); g.manual_seed(seed)
        for _ in range(40):
            logp = net.decode_logp(s, mem, pad, torch.tensor([toks], device=device))[0, -1]
            scores = logp + mask
            probs = torch.softmax(scores, dim=-1)
            sp, si = torch.sort(probs, descending=True)
            keep = torch.cumsum(sp, dim=-1) - sp < 0.9
            sp = sp * keep; sp = sp / sp.sum()
            k = int(si[torch.multinomial(sp, 1, generator=g)].item())
            if k == eos:
                break
            toks.append(k)
        return vocab_m.detokenize([vm.tokens[i] for i in toks[1:]], {})

    out = {}
    total_ok = total = 0
    for tag in SOCIAL:
        triggers = TAGS[tag]["triggers"][:8]
        replies, passes = [], 0
        for j, trig in enumerate(triggers):
            try:
                r = speak(tag, trig, 1000 + j)
            except Exception as e:
                r = ""
            ok, why = check.check(tag, trig, r, fact_words, None)
            passes += int(ok)
            total += 1
            total_ok += int(ok)
            replies.append({"trigger": trig, "reply": r, "ok": ok, "why": why})
        out[tag] = {"pass": passes, "of": len(triggers), "distinct": len({r["reply"] for r in replies}),
                    "replies": replies}
        print(f"{tag:14s} guard {passes}/{len(triggers)} distinct {out[tag]['distinct']}", flush=True)
    summary = {"guard_pass": total_ok, "of": total, "rate": round(total_ok / total, 4),
               "tags": out}
    Path(a.out).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({"guard_pass": total_ok, "of": total, "rate": summary["rate"]}, indent=1))
    for tag in ("GREETING", "EMPATHY", "SMALLTALK", "REFUSE_POLITE"):
        print("\n---", tag)
        for r in out[tag]["replies"][:4]:
            print(f"  [{r['trigger'][:34]}] -> {r['reply'][:100]}   ok={r['ok']} {r['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
