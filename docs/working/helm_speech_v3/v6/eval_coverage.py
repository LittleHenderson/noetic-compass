"""Coverage evaluation: does a reply address every component of a compound turn, and name what is absent?

Guard pass is not enough (A5 passed 22/22 while talking nonsense). This checks, per component above weight 0.3, whether
the reply carries a cue for that component; and for absence rows, whether it names the missing thing or asks for it.

    python eval_coverage.py --ckpt A4-s1_final.pt --out coverage.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from helm_cas_translator import model as M, param_count
from mouth_task import check, vocab_m

CUES = {
    "EMPATHY": r"sorry|draining|hear you|hear that|heavy|hard|tough|carry|rough",
    "PLAN": r"step|first|next|start|today|one thing",
    "SUGGEST": r"what would|could|might|try|maybe|option|instead",
    "STATUS": r"where|stands|done|left|pending|state|finished",
    "CLARIFY": r"which|mean|confirm|check|\?",
    "HEDGE": r"sure|certain|might|not sure|verify|check",
    "THANKS": r"glad|welcome|pleasure|any time|happy",
    "APOLOGY": r"no harm|fine|alright|no need|don't worry|forget",
    "EXPLAIN": r"because|since|reason|so that|explains",
    "CONGRATS": r"excellent|great|well done|congrat|brilliant|good news",
    "CONDOLENCE": r"sorry|loss|heavy|no rush|gentle|here",
    "ENCOURAGE": r"next|smallest|one piece|not all at once|stuck|further|step",
    "REFUSE_POLITE": r"won't|decline|rather not|can't|don't",
    "WARN": r"risk|catch|careful|watch|danger",
    "REASSURANCE": r"nothing|lost|fine|intact|safe|alright",
    "CONFIRM": r"right|correct|yes|agreed|confirmed",
    "PLAYFUL": r"joke|funny|pun|ha|udp",
    "SMALLTALK": r"day|quiet|busy|you|here",
}

COMPOUNDS = [
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
]

def brain_absence_cases():
    """Absence cases whose missing item comes from the recipe brain's own receipt."""
    try:
        sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
        from helm_brain_22x40 import HELMRecipeBrain22x40
        from brain_absence import ledger, worth_raising, SCENARIOS
    except Exception:
        return []
    brain = HELMRecipeBrain22x40()
    cases = []
    for user, inputs, requested in SCENARIOS:
        led = ledger(brain, inputs)
        pick = worth_raising(inputs, led["absent"], requested)
        if pick:
            cases.append((user, pick[0], pick[1], led["status"], led["gate"]))
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="A4-s1_final.pt")
    ap.add_argument("--model", default="A4-s1")
    ap.add_argument("--out", default="coverage.json")
    a = ap.parse_args()
    import re
    import torch
    device = M.require_cuda()
    vm = vocab_m.load(str(HERE / "data" / "vocab.json"))
    cfg = param_count.CONFIGS["A4_9p6M" if a.model == "A4-s1" else "A5_2p5M"]
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

    rows = []
    for i, (c1, c2, prompt) in enumerate(COMPOUNDS):
        situation = f"{c1[0].lower()} {c1[1]} {c2[0].lower()} {c2[1]}"
        reply = speak(situation, prompt, None, 7000 + i)
        ok, why = check.check("SMALLTALK", prompt, reply, fact_words, None)
        covered = {}
        for tag, _w in (c1, c2):
            covered[tag] = bool(re.search(CUES.get(tag, r"(?!)"), reply, re.I))
        rows.append({"prompt": prompt, "situation": situation, "reply": reply, "guard": ok, "why": why,
                     "covered": covered, "coverage": sum(covered.values()) / 2})
    abs_rows = []
    for i, case in enumerate(brain_absence_cases()):
        prompt, absent = case[0], case[1]
        kind = case[2] if len(case) > 2 else "unknown"
        reply = speak("clarify 1.0", prompt, absent, 8000 + i)
        ok, why = check.check("CLARIFY", prompt, reply, fact_words, None)
        named = absent.lower() in reply.lower()
        abs_rows.append({"prompt": prompt, "absence": absent, "kind": kind, "reply": reply, "guard": ok,
                         "named": named, "asked": "?" in reply,
                         "named_or_asked": named or "?" in reply})
    out = {"model": a.model, "compounds": rows,
           "mean_coverage": round(sum(r["coverage"] for r in rows) / len(rows), 4),
           "all_components": sum(1 for r in rows if r["coverage"] == 1.0),
           "guard_pass": sum(1 for r in rows if r["guard"]),
           "of": len(rows),
           "absence": abs_rows,
           "absence_hit": sum(1 for r in abs_rows if r["named_or_asked"]),
           "absence_of": len(abs_rows)}
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("model", "mean_coverage", "all_components", "guard_pass", "of",
                                          "absence_hit", "absence_of")}, indent=1))
    for r in rows:
        print(f"  {r['coverage']:.2f} {r['covered']} | {r['prompt'][:52]} -> {r['reply'][:70]}")
    for r in abs_rows:
        print(f"  ABS {r['named_or_asked']} [{r['absence']}] -> {r['reply'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
