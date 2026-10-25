"""Rank 4: build a second, independent Noetic-labelled set from new CAS compositions (no LLM, no training overlap)."""
import json, random, sys
from pathlib import Path
PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19\cas_token_transformer\HELM_CTT_20261019")
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG))
from ctt_build import notation_pairs as NP, paths as P
from helm_cas_translator import slots as S

comp = P.compiler_module()
NOETIC = {
 "0": "an idea", "1": "a mind", "2": "an attraction", "3": "an aversion", "4": "a resonance",
 "5": "a composed mind", "6": "an idea that composes another", "7": "a practiced rhythm",
 "8": "a cause", "9": "an effect",
}
DOMAIN = {"P": "principled", "C": "cognitive", "E": "evaluative", "O": "operational"}
rng = random.Random(20261024)
rows, made = [], 0
for i in range(100):
    a, b = rng.sample(list(NOETIC), 2)
    da, db = rng.choice("PCEO"), rng.choice("PCEO")
    op = rng.choice(["\u00d7", "\u2192"])
    src = "^%s^%s %s ^%s^%s" % (a, da, op, b, db)
    A, B = NOETIC[a], NOETIC[b]
    DA, DB = DOMAIN[da], DOMAIN[db]
    if op == "\u00d7":
        variants = [
            "%s in the %s arena, integrated with %s in the %s arena." % (A.capitalize(), DA, B, DB),
            "Integrated with %s in the %s arena is %s in the %s arena." % (B, DB, A, DA),
            "There is %s in the %s arena, together with %s in the %s arena." % (A, DA, B, DB),
            "%s in the %s arena is combined with %s in the %s arena." % (A.capitalize(), DA, B, DB),
            "One finds %s in the %s arena and, integrated with it, %s in the %s arena." % (A, DA, B, DB),
            "%s in the %s arena co-occurs with %s in the %s arena." % (A.capitalize(), DA, B, DB),
        ]
    else:
        variants = [
            "%s in the %s arena that triggers %s in the %s arena." % (A.capitalize(), DA, B, DB),
            "%s in the %s arena leads to %s in the %s arena." % (A.capitalize(), DA, B, DB),
            "There is %s in the %s arena, which brings about %s in the %s arena." % (A, DA, B, DB),
            "%s in the %s arena causes %s in the %s arena." % (A.capitalize(), DA, B, DB),
            "One finds %s in the %s arena, and it triggers %s in the %s arena." % (A, DA, B, DB),
            "%s in the %s arena, followed by %s in the %s arena." % (A.capitalize(), DA, B, DB),
        ]
    for k, text in enumerate(variants):
        sl = S.find_slots(text, "N")
        try:
            toks = NP.to_ctt(src, sl, comp)
        except Exception:
            continue
        if not any(t in ("^0","^1","^2","^3","^4","^5","^6","^7","^8","^9") for t in toks):
            continue
        rows.append({"direction": "N", "text": text, "target": toks, "source": "NEW100",
                     "seed_id": "new_%03d" % i, "variant": k})
    made += 1
out = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1\data\notation_new100.jsonl")
with open(out, "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("sources", made, "rows", len(rows), "written", out)
