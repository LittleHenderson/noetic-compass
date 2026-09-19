"""LB2 — the honest zero-learning baseline for the draft's input, plus the per-node feature table.

Every rule below uses ONLY: the focus world's raw fields (declared_whole, declarations
{participants, primary_labels, domain, kind, function, setting}), the world's node list,
and the query's arguments (whole/part node refs). NO edges, NO checker, NO reachability.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, answers, checker

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
heldset, trainedset = set(held), set(trained)


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


def admissible_values(p, q):
    """Exact admissible answer VALUES, via the checker (used here only to grade a guess)."""
    target = checker.derive_target(p["source"], q)
    return {answers._json(a["value"]) for a in target["admissible_answers"]}


def guess(public, query):
    """The draft's reading, turned directly into an answer with zero learning and zero edges."""
    focus = next(w for w in public["worlds"] if w["world_id"] == query["focus_world_id"])
    kind = query["kind"]
    nodes = sorted(n["ref"] for n in focus["nodes"])
    if kind == "definition":
        return {"whole": focus["declared_whole"],
                "kind_ref": answers.declaration_ref(focus["world_id"], "kind"),
                "function_ref": answers.declaration_ref(focus["world_id"], "function")}
    if kind == "context":
        return {"setting_ref": answers.declaration_ref(focus["world_id"], "setting"),
                "participants": sorted(focus["declarations"]["participants"])}
    if kind == "parts":
        # The reader sees its own `whole` mark; declared_whole is the only whole flag it has.
        # With no edges the best guess is: declared_whole's participants minus the whole itself.
        whole = query["arguments"]["whole"]
        return {"nodes": sorted(r for r in focus["declarations"]["participants"] if r != whole)}
    if kind == "reach":
        # No edges: DIRECT for every node the declared_whole flag could imply, else ABSENT.
        whole, part = query["arguments"]["whole"], query["arguments"]["part"]
        return {"state": "ABSENT", "via": None}
    if kind == "edge_account":
        # No edges: the only edge-free claim is the empty set.
        return {"edges": []}
    if kind == "correspondence":
        if query["arguments"]["target_world_id"] == query["focus_world_id"]:
            return {"status": "MAPPING", "pairs": [{"source": r, "target": r} for r in nodes]}
        return {"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(nodes, nodes)]}
    if kind == "analogy":
        return {"world_id": None}
    return None


counts, hits = Counter(), Counter()
parts_detail = Counter()
for rid, p in packets.items():
    q = p["record"]["query"]
    kind = q["kind"]
    if kind == "role_set":
        continue
    ok = answers._json(guess(p["source"], q)) in admissible_values(p, q)
    counts[(side(rid), kind)] += 1
    hits[(side(rid), kind)] += int(ok)
    if kind == "parts":
        parts_detail[(side(rid), ok)] += 1

print("honest zero-learning baseline from the draft's reading (no edges, no reachability):")
for s in ("held", "trained", "excluded"):
    for kind in c.KINDS:
        if kind == "role_set":
            continue
        if counts[(s, kind)]:
            print("   %-9s %-14s %d/%d" % (s, kind, hits[(s, kind)], counts[(s, kind)]))
print("parts detail (correct, wrong) by side:", dict(parts_detail))

# how often IS the declared_whole's participant set exactly its child set?
exact = Counter()
for rid, p in packets.items():
    q = p["record"]["query"]
    focus = next(w for w in p["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
    children = sorted(e["target"] for e in focus["contains"] if e["source"] == focus["declared_whole"])
    guess_set = sorted(r for r in focus["declarations"]["participants"] if r != focus["declared_whole"])
    exact["match" if children == guess_set else "differ"] += 1
print("declared_whole: children == participants-minus-whole  (over all 564 focus-world reads):", dict(exact))
world_exact = Counter()
for w in frozen["bank"]["worlds"]:
    children = sorted(e["target"] for e in w["contains"] if e["source"] == w["declared_whole"])
    guess_set = sorted(r for r in w["declarations"]["participants"] if r != w["declared_whole"])
    world_exact["match" if children == guess_set else "differ"] += 1
print("same, over the 64 bank worlds:", dict(world_exact))

# ---------- per-node feature table: exactly what section 2.1 gives a node ----------
print()
print("per-node field availability across the 64 bank worlds (3-4 nodes) and the 6 dev worlds (9-10 nodes):")
row = Counter()
for w in frozen["bank"]["worlds"] + [next(x for x in q["source"]["worlds"] if x["world_id"] == q["source"]["focus_world_id"]) for q in c.development_packets(devdoc).values()]:
    n = len(w["nodes"])
    row[("nodes", n)] += 1
for key in sorted(k for k in row if k[0] == "nodes"):
    print("   worlds with", key[1], "nodes:", row[key])
print("   a node gets: label token vector, is_declared_whole, is_participant(+rank), is_primary_label(+rank)")
print("   a node does NOT get: degree, parent count, child count, depth, alias index, ref text, ref order")
print("   is_whole/is_part marks exist only for the 2 kinds that name them: parts(whole), reach(whole,part)")

# which kinds put a query mark on a node
marked = Counter()
for rid, p in packets.items():
    q = p["record"]["query"]
    marked[q["kind"]] = marked[q["kind"]] + len(q["arguments"])
print("total query marks per kind over 564 records:", dict(marked))

# role_set: the reader hands the excerpt over as a bag of token vectors.
print()
print("role_set questions:", sum(1 for r in frozen["registry"] if r["query"]["kind"] == "role_set"))
excerpts = [r["query"]["arguments"]["focal_excerpt"] for r in frozen["registry"] if r["query"]["kind"] == "role_set"]
print("distinct excerpts:", len(set(excerpts)), "of", len(excerpts))
prefixes = Counter(e.split(":", 1)[0] for e in excerpts)
print("clause prefixes seen across all role_set excerpts:", dict(prefixes))
