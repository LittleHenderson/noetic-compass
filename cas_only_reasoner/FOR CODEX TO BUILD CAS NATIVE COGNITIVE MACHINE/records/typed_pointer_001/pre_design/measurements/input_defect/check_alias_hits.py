"""Where do held aliases occur inside TRAINED slot query specs? (coordinates/scope vs symbol lists)"""
import sys; sys.dont_write_bytecode = True
import pickle, json
from collections import Counter
from pathlib import Path
d = pickle.loads((Path(__file__).resolve().parent / "build2.pkl").read_bytes())
S = d["slots"]; held = set(d["held_worlds"])
alias_of = {}
for s in S: alias_of.setdefault(s["scope_world"], s["scope_alias"])
ha = {alias_of[w] for w in held}
where = Counter()
for s in S:
    if s["split"] != "trained": continue
    spec = json.loads(s["spec_c"])
    in_scope = spec["scope"] in ha
    in_coord = any(isinstance(c, str) and c.split("/")[0] in ha for c in spec["coordinates"])
    in_sym = any(x in ha for x in spec["symbols"])
    if in_scope or in_coord or in_sym:
        where[(in_scope, in_coord, in_sym, s["kind"], s["field"])] += 1
print("held aliases", sorted(ha))
for k, v in sorted(where.items(), key=lambda kv: -kv[1]): print("(scope,coord,symbols,kind,field)", k, v)
