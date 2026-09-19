"""Is each reach answer fixed by graph STRUCTURE, or by the lexical order of hidden node refs? (no torch)
A permutation-equivariant pointer machine sees no ref order, so a lexically-decided answer is a ceiling."""
import json, sys
from collections import Counter
from itertools import permutations
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
for p in (CNCM, CNCM / "research/CAS_META_2_COMPOSITION", CNCM / "records/typed_practice_001"):
    sys.path.insert(0, str(p))
from cas_meta2.typed_teaching import practice_contract as c, checker
import evaluate_gates as eg
assert "torch" not in sys.modules

frozen, _, _ = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
side = {**{k: "held" for k in held}, **{k: "trained" for k in trained}, **{k: "excluded" for k in excluded}}
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}
w0 = next(iter(worlds.values()))
print("declarations example", json.dumps(w0["declarations"])[:600], "declared_whole", w0["declared_whole"])

def relabel(world, pi):
    new = dict(world)
    new["contains"] = [{**e, "source": pi[e["source"]], "target": pi[e["target"]]} for e in world["contains"]]
    return new

lex = Counter(); total = Counter(); lex_q = set()
for r in frozen["registry"]:
    q = r["query"]
    if q["kind"] != "reach":
        continue
    w = worlds[q["focus_world_id"]]
    refs = sorted(n["ref"] for n in w["nodes"])
    base, _ = checker._reach(w, q)
    determined = True
    for order in permutations(refs):
        pi = dict(zip(refs, order))              # structural position of ref -> new ref name
        w2 = relabel(w, pi)
        q2 = {**q, "arguments": {"whole": pi[q["arguments"]["whole"]], "part": pi[q["arguments"]["part"]]}}
        a2, _ = checker._reach(w2, q2)
        expect = {"state": base["state"], "via": None if base["via"] is None else pi[base["via"]]}
        if a2 != expect:
            determined = False
            break
    total[side[r["record_id"]]] += 1
    if not determined:
        lex[side[r["record_id"]]] += 1
        lex_q.add(q["query_id"])
print("reach records total by side", dict(total))
print("reach records whose answer depends on hidden lexical ref order", dict(lex))
held_q = c.held_back_questions(frozen)
eligible, _, _ = eg.eligible_questions(frozen, set(trained), held_q)
kind_of = {r["query"]["query_id"]: r["query"]["kind"] for r in frozen["registry"]}
er = [q for q in eligible if kind_of[q] == "reach"]
print("eligible held reach questions", len(er), "of which lexically decided", sum(1 for q in er if q in lex_q))
world_of = {r["query"]["query_id"]: r["source_world_id"] for r in frozen["registry"]}
rel = [q for q in eligible if kind_of[q] in ("parts", "edge_account", "reach", "correspondence", "analogy")]
print("relational eligible per world", dict(Counter(world_of[q][:14] for q in rel)))
