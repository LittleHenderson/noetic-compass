"""Input-reading facts for the pointer design (no torch): tokenizer cost, OOV labels, world-choice widths,
reach rule/lexical dependence, flag-solvable kinds among eligible held questions."""
import json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
for p in (CNCM, CNCM / "research/CAS_META_2_COMPOSITION", CNCM / "records/typed_practice_001"):
    sys.path.insert(0, str(p))
from cas_meta2.typed_teaching import practice_contract as c, slots, checker, tokenization
import evaluate_gates as eg
assert "torch" not in sys.modules

frozen, tok, dev = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
print("vocab size", len(tok.vocabulary))
t = time.perf_counter(); ids = tok.encode_text("Bracket"); dt = time.perf_counter() - t
print("encode_text one label seconds", round(dt, 4), ids)

# node label / declaration OOV (byte fallback) in held vs trained worlds
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}
held_w = set(c.held_worlds(frozen))
vocab_units = {bytes.fromhex(v[6:-1]).decode() for v in tok.vocabulary[tokenization.WORD_START:]}
import re
unit = re.compile(tokenization.UNIT_RULE)
def oov(text):
    return [u for u in unit.findall(text) if u not in vocab_units]
w0 = next(iter(worlds.values()))
print("node example", w0["nodes"][0], "decl keys", sorted(w0["declarations"]))
lab_oov = Counter()
labels_by_world = {}
for wid, w in worlds.items():
    labs = [n.get("label") for n in w["nodes"]]
    labels_by_world[wid] = labs
    for l in labs:
        if l is not None and oov(l):
            lab_oov["held" if wid in held_w else "other"] += 1
print("labels with OOV units", dict(lab_oov))
# do held-world labels occur in any non-held world?
other_labels = Counter(l for wid, labs in labels_by_world.items() if wid not in held_w for l in labs)
held_labels = [l for wid in held_w for l in labels_by_world[wid]]
print("held labels", held_labels)
print("held labels also used in other worlds", sum(1 for l in held_labels if other_labels[l]), "of", len(held_labels))
print("distinct labels overall", len({l for labs in labels_by_world.values() for l in labs}), "nodes", sum(len(v) for v in labels_by_world.values()))

# world-choice widths and analogy bank size
widths = defaultdict(Counter)
for k, p in packets.items():
    plan = slots.compile_slots(p)
    for s in plan["slots"]:
        if s["field"] in ("kind_ref", "function_ref", "setting_ref", "world_id"):
            widths[s["field"]][len(s["symbols"])] += 1
print("world-choice slot widths", {k: dict(v) for k, v in widths.items()})

# reach: rule dependence and lexical ties
by_id = {r["record_id"]: r for r in frozen["registry"]}
rule_counts = Counter(); dep = Counter(); ties = Counter()
for r in frozen["registry"]:
    q = r["query"]
    if q["kind"] != "reach":
        continue
    side = "held" if r["record_id"] in set(held) else "trained" if r["record_id"] in set(trained) else "excluded"
    rule_counts[(side, q["rule"])] += 1
    pub = packets[r["record_id"]]["source"]
    alt = dict(q); alt["rule"] = [x for x in ("first_direct_constituent_lexical_v1", "bfs_immediate_predecessor_lexical_v1") if x != q["rule"]][0]
    w = worlds[q["focus_world_id"]]
    a1, _ = checker._reach(w, q)
    a2, _ = checker._reach(w, alt)
    if a1 != a2:
        dep[side] += 1
    # lexical tie: more than one child of whole with a path to part (rule 1) / multiple shortest predecessors (rule 2)
    adj = checker._adjacency(w)
    whole, part = q["arguments"]["whole"], q["arguments"]["part"]
    if part not in adj[whole]:
        cands = [f for f in adj[whole] if checker._bfs(adj, f, part)[0] is not None]
        if len(cands) > 1:
            ties[side] += 1
print("reach rule by side", dict(rule_counts))
print("reach records whose answer changes if the rule is swapped", dict(dep))
print("reach records with >1 child-of-whole reaching part (lexical tie-break decides rule-1 answer)", dict(ties))

# eligible held questions by kind and world; flag-solvable (definition/context) share
held_q = c.held_back_questions(frozen)
eligible, shortcut_hit, shortcut = eg.eligible_questions(frozen, set(trained), held_q)
kind_of = {r["query"]["query_id"]: r["query"]["kind"] for r in frozen["registry"]}
world_of = {r["query"]["query_id"]: r["source_world_id"] for r in frozen["registry"]}
print("eligible", len(eligible), "by kind", dict(Counter(kind_of[q] for q in eligible)))
dr = [q for q in eligible if kind_of[q] in ("definition", "context")]
print("DIRECT_READ eligible questions", len(dr), "worlds", len({world_of[q] for q in dr}))
rel = [q for q in eligible if kind_of[q] in ("parts", "edge_account", "reach", "correspondence", "analogy")]
print("RELATIONAL eligible", len(rel), dict(Counter(kind_of[q] for q in rel)), "worlds", len({world_of[q] for q in rel}))
# binomial: if a machine goes 0 -> all DIRECT_READ right and nothing else changes
b = len(dr)
print("p if b=%d c=0:" % b, float(eg.binomial_upper_tail(b, b)))
# records per eligible question (a question counts only if ALL its records are right)
print("records per eligible question", Counter(len(held_q[q]) for q in eligible))
