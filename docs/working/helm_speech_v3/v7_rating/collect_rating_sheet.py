"""Collect 50 compound replies and 10 held-out absence replies, shuffled, for a blind human rating.

Outputs:
- rating_sheet.json  : [{"id", "prompt", "reply"}] in random order, no labels
- rating_key.json    : the answer key (components, coverage, guard, absence kind)
- rating_sheet.csv   : the same sheet for reading in a spreadsheet

    python collect_rating_sheet.py --ckpt A4-s1_final.pt --out rating
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helm_cas_translator import model as M, param_count
from mouth_task import check, vocab_m

COMPOUND_PROMPTS = [
    (("EMPATHY", 0.6), ("PLAN", 0.4), "I'm shattered but the audit still has to be finished by Thursday."),
    (("EMPATHY", 0.6), ("SUGGEST", 0.4), "I'm anxious and I can't decide whether to sign the contract."),
    (("EMPATHY", 0.5), ("STATUS", 0.5), "I'm drained and the migration is still sitting there."),
    (("THANKS", 0.5), ("CLARIFY", 0.5), "Thanks, that helped — which branch did you mean?"),
    (("APOLOGY", 0.5), ("EXPLAIN", 0.5), "Sorry I'm late, the tram was cancelled."),
    (("CLARIFY", 0.6), ("HEDGE", 0.4), "I think it's the staging file, but I'm not sure."),
    (("PLAN", 0.6), ("STATUS", 0.4), "We still need to migrate the database; where are we?"),
    (("CONGRATS", 0.5), ("THANKS", 0.5), "The review passed — thanks for the push."),
    (("CONDOLENCE", 0.6), ("ENCOURAGE", 0.4), "I lost my sister and I can't face the backlog."),
    (("REFUSE_POLITE", 0.5), ("EXPLAIN", 0.5), "Just invent the percentage — why not?"),
    (("WARN", 0.5), ("SUGGEST", 0.5), "Is the shipment risky, and what would you do?"),
    (("REASSURANCE", 0.5), ("PLAN", 0.5), "Did I break the deployment? What now?"),
    (("ENCOURAGE", 0.5), ("SUGGEST", 0.5), "I keep failing at the handover. Any ideas?"),
    (("STATUS", 0.5), ("HEDGE", 0.5), "Where are we on the budget? I think it's nearly done, but I'm not sure."),
    (("PLAN", 0.5), ("EXPLAIN", 0.5), "What's next on the audit, and why that first?"),
    (("CONDOLENCE", 0.5), ("ENCOURAGE", 0.5), "My father died last month and the invoice still isn't done."),
    (("APOLOGY", 0.5), ("EXPLAIN", 0.5), "Sorry about the report — the call ran over."),
    (("EMPATHY", 0.5), ("PLAN", 0.5), "I'm exhausted and the deck is due tomorrow."),
    (("THANKS", 0.5), ("SUGGEST", 0.5), "Thanks for the help — what would you do next time?"),
    (("CLARIFY", 0.5), ("EXPLAIN", 0.5), "Which file do you mean, and why that one?"),
    (("REFUSE_POLITE", 0.5), ("SUGGEST", 0.5), "Skip the check and just send it — or what else?"),
    (("WARN", 0.5), ("EXPLAIN", 0.5), "Is it risky? Why do you say that?"),
    (("REASSURANCE", 0.5), ("EXPLAIN", 0.5), "Did I lose the work? What happened?"),
    (("CONGRATS", 0.5), ("PLAN", 0.5), "We got the contract — what's the next milestone?"),
    (("EMPATHY", 0.5), ("HEDGE", 0.5), "I'm worried about the review, though I'm not sure I should be."),
]


def build_prompts():
    prompts = []
    for c1, c2, text in COMPOUND_PROMPTS:
        prompts.append({"kind": "compound", "prompt": text,
                        "situation": f"{c1[0].lower()} {c1[1]} {c2[0].lower()} {c2[1]}",
                        "components": {c1[0]: c1[1], c2[0]: c2[1]}, "absence": None})
    # duplicate with different tone to reach 50 compounds
    for i, p in enumerate(list(prompts)):
        if len([x for x in prompts if x["kind"] == "compound"]) >= 50:
            break
        q = dict(p)
        q["prompt"] = p["prompt"].rstrip(".") + " I'd rather sort it now than later."
        prompts.append(q)
    try:
        sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
        from brain_absence import ledger, worth_raising, HELDOUT_SCENARIOS
        from helm_brain_22x40 import HELMRecipeBrain22x40
        brain = HELMRecipeBrain22x40()
        for user, inputs, requested in HELDOUT_SCENARIOS:
            led = ledger(brain, inputs)
            pick = worth_raising(inputs, led["absent"], requested)
            if pick:
                prompts.append({"kind": "absence", "prompt": user, "situation": "clarify 1.0",
                                "components": {"CLARIFY": 1.0}, "absence": pick[0]})
    except Exception as e:
        print("brain absence unavailable:", e)
    return prompts[:60]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="A4-s1_final.pt")
    ap.add_argument("--out", default="rating")
    a = ap.parse_args()
    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M"]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    net.load_state_dict(torch.load(a.ckpt, map_location=device, weights_only=True))
    net.eval()
    fact_words = set(json.load(open(HERE / "data" / "FACT_WORDS.json", encoding="utf-8")))
    eos = vm.id["[EOS]"]
    allowed = [i for i, t in enumerate(vm.tokens) if t.startswith("en:") or t in (".", ",", "?", "!", ";", ":", "'")]
    allowed.append(eos)
    mask = torch.full((len(vm.tokens),), float("-inf"), device=device)
    mask[torch.tensor(allowed, device=device)] = 0.0

    def speak(situation, text, absence, seed):
        src = vm.encode_mouth_source(situation, ("^1", "|f"), text, None, None, absence)
        s = M.pad_batch([src], device)
        mem, pad = net.encode(s)
        toks = [1]
        g = torch.Generator(device=device); g.manual_seed(seed)
        for _ in range(40):
            logp = net.decode_logp(s, mem, pad, torch.tensor([toks], device=device))[0, -1]
            probs = torch.softmax(logp + mask, dim=-1)
            sp, si = torch.sort(probs, descending=True)
            keep = torch.cumsum(sp, dim=-1) - sp < 0.9
            sp = sp * keep; sp = sp / sp.sum()
            k = int(si[torch.multinomial(sp, 1, generator=g)].item())
            if k == eos:
                break
            toks.append(k)
        return vocab_m.detokenize([vm.tokens[i] for i in toks[1:]], {})

    rows, key = [], []
    for i, p in enumerate(build_prompts()):
        reply = speak(p["situation"], p["prompt"], p["absence"], 5000 + i)
        ok, why = check.check("SMALLTALK", p["prompt"], reply, fact_words, None)
        rows.append({"id": i + 1, "prompt": p["prompt"], "reply": reply})
        key.append({"id": i + 1, "kind": p["kind"], "components": p["components"], "absence": p["absence"],
                    "guard": ok, "why": why})
    order = list(range(len(rows)))
    random.Random(11).shuffle(order)
    shuffled = [rows[i] for i in order]
    key_by_id = {k["id"]: k for k in key}
    shuffled_key = [key_by_id[r["id"]] for r in shuffled]
    Path(a.out + "_sheet.json").write_text(json.dumps(shuffled, indent=1), encoding="utf-8")
    Path(a.out + "_key.json").write_text(json.dumps(shuffled_key, indent=1), encoding="utf-8")
    with open(a.out + "_sheet.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "prompt", "reply", "warm (1-5)", "natural (1-5)", "held all parts (yes/no)", "notes"])
        for r in shuffled:
            w.writerow([r["id"], r["prompt"], r["reply"], "", "", "", ""])
    print(json.dumps({"rows": len(shuffled), "guard_pass": sum(k["guard"] for k in key),
                      "sheet": a.out + "_sheet.json", "csv": a.out + "_sheet.csv"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
