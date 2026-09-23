# Across the whole PUBLIC bank: for every ordered pair of distinct, same-size worlds that are contains-isomorphic,
# is the no-edges "participant order" map one of the isomorphisms? Is it the lexical-first one?
import json, itertools, collections
from pathlib import Path
CN = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
bank = json.loads((CN / "records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]
def structure(w):
    return sorted(n["ref"] for n in w["nodes"]), {(e["source"], e["target"]) for e in w["contains"]}
def isos(a, b):
    rs, es = structure(a); rt, et = structure(b)
    if len(rs) != len(rt): return []
    out = []
    for perm in itertools.permutations(rt):
        m = dict(zip(rs, perm))
        if {(m[x], m[y]) for x, y in es} == et:
            out.append(tuple(sorted(m.items())))
    return out
def participant_order(a, b):
    m = {a["declared_whole"]: b["declared_whole"]}
    for x, y in zip(a["declarations"]["participants"], b["declarations"]["participants"]):
        m[x] = y
    rs, _ = structure(a); rt, _ = structure(b)
    left = [r for r in rs if r not in m]; free = [r for r in rt if r not in m.values()]
    for x, y in zip(left, free): m[x] = y
    return tuple(sorted(m.items()))
sizes = collections.Counter(len(w["nodes"]) for w in bank)
pairs = iso_pairs = is_iso = is_first = 0
for a, b in itertools.permutations(bank, 2):
    pairs += 1
    allm = isos(a, b)
    if not allm: continue
    iso_pairs += 1
    pm = participant_order(a, b)
    is_iso += pm in allm
    is_first += pm == allm[0]
print("bank worlds by node count:", dict(sizes))
print("ordered pairs %d; contains-isomorphic pairs %d; participant-order map is an isomorphism in %d; equals lexical-first isomorphism in %d"
      % (pairs, iso_pairs, is_iso, is_first))
