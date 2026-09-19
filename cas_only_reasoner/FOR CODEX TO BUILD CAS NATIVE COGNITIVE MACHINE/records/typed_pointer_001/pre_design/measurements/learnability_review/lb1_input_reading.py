"""LB1/LB3 — the exact input reading implied by DESIGN_DRAFT v0.1 2.1, applied to every record.

This is a reading, not a model. It records, per record, exactly which fields the reader of
section 2.1 can produce, and where it must fail or fall back. No torch.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, slots, checker, answers

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
dev = c.development_packets(devdoc)
by_id = {r["record_id"]: r for r in frozen["registry"]}
heldset, trainedset, excludedset = set(held), set(trained), set(excluded)


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


# ---------- 1. which worlds the draft's reader must read, per kind ----------
WORLD_CHOICE_FIELDS = ("kind_ref", "function_ref", "setting_ref", "world_id")
worlds_read = Counter()
per_kind_worlds = defaultdict(Counter)
for rid, p in packets.items():
    plan = slots.compile_slots(p)
    kinds = {s["field"] for s in plan["slots"]}
    focus = p["source"]["focus_world_id"]
    n_worlds = 1
    if "kind_ref" in kinds or "function_ref" in kinds or "setting_ref" in kinds or "world_id" in kinds:
        n_worlds = 1 + len(p["source"]["worlds"]) - (0 if focus in {w["world_id"] for w in p["source"]["worlds"]} else 1)
    if plan["kind"] == "correspondence":
        n_worlds += 1
    kind = p["record"]["query"]["kind"]
    worlds_read[kind] += n_worlds
    per_kind_worlds[kind][n_worlds] += 1
print("worlds the reader must encode, total presentations per kind (564 records):")
for kind in c.KINDS:
    print("  ", kind, worlds_read[kind], "of 564 records; distribution", dict(sorted(per_kind_worlds[kind].items())))
print("  all kinds total", sum(worlds_read.values()), "of", 564)

# ---------- 2. per node, which of the stated flags exist and are readable ----------
def node_facts(world):
    refs = sorted(n["ref"] for n in world["nodes"])
    decl = world["declarations"]
    return {
        "refs": refs,
        "label": {n["ref"]: n["label"] for n in world["nodes"]},
        "declared_whole": world["declared_whole"],
        "participants": sorted(decl["participants"]),
        "primary_labels": list(decl["primary_labels"]),
        "edges": sorted((e["source"], e["target"]) for e in world["contains"]),
    }


flag_errors = Counter()
opaque_apostrophe_labels = 0
for rid, p in packets.items():
    q = p["record"]["query"]
    focus = next(w for w in p["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
    f = node_facts(focus)
    argnodes = set()
    for key in ("whole", "part"):
        if key in q["arguments"]:
            argnodes.add(q["arguments"][key])
    if not argnodes <= set(f["refs"]):
        flag_errors["ARGUMENT_OUTSIDE_FOCUS"] += 1
    if f["declared_whole"] not in f["refs"]:
        flag_errors["WHOLE_NOT_A_NODE"] += 1
    if not set(f["participants"]) <= set(f["refs"]):
        flag_errors["PARTICIPANT_NOT_A_NODE"] += 1
    if not set(f["primary_labels"]) <= set(f["refs"]):
        flag_errors["PRIMARY_NOT_A_NODE"] += 1
    for ref in f["label"]:
        if "'" in f["label"][ref] or '"' in f["label"][ref]:
            opaque_apostrophe_labels += 1
print("reader flag construction failures (course packets):", dict(flag_errors) or "none")
print("course node labels containing a quote character:", opaque_apostrophe_labels)

# label multiplicity: are labels unique inside a world?
dup_in_world = 0
for w in frozen["bank"]["worlds"]:
    labels = [n["label"] for n in w["nodes"]]
    if len(set(labels)) != len(labels):
        dup_in_world += 1
print("bank worlds whose node labels are NOT unique inside the world:", dup_in_world, "of", len(frozen["bank"]["worlds"]))
devdup = 0
for q in dev.values():
    fw = next(w for w in q["source"]["worlds"] if w["world_id"] == q["source"]["focus_world_id"])
    labels = [n["label"] for n in fw["nodes"]]
    if len(set(labels)) != len(labels):
        devdup += 1
print("development packets whose focus labels are not unique:", devdup, "of", len(dev))

# ---------- 3. the query-argument flags: what they hand over for free ----------
# is the query's `whole` / `part` mark enough to solve the kind with zero learning?
import functools


def flag_rule(public, query):
    worlds = {w["world_id"]: w for w in public["worlds"]}
    focus = worlds[query["focus_world_id"]]
    adj = checker._adjacency(focus)
    kind = query["kind"]
    if kind == "parts":
        whole = query["arguments"]["whole"]
        return {"nodes": sorted(adj[whole])}
    if kind == "definition":
        return {"whole": focus["declared_whole"],
                "kind_ref": answers.declaration_ref(focus["world_id"], "kind"),
                "function_ref": answers.declaration_ref(focus["world_id"], "function")}
    if kind == "context":
        return {"setting_ref": answers.declaration_ref(focus["world_id"], "setting"),
                "participants": sorted(focus["declarations"]["participants"])}
    if kind == "edge_account":
        return {"edges": checker._edge_rows(checker._edges(focus))}
    if kind == "reach":
        whole, part = query["arguments"]["whole"], query["arguments"]["part"]
        value, _ = checker._reach(focus, query)
        return value
    if kind == "correspondence":
        other = worlds[query["arguments"]["target_world_id"]]
        matches, audit = checker._isomorphisms(focus, other)
        if matches:
            return {"status": "MAPPING", "pairs": matches[0]}
        return {"status": "NO_MATCH", "pairs": []}
    if kind == "analogy":
        bank = [worlds[k] for k in public["bank"]["world_ids"]]
        for other in bank:
            if other["declarations"]["domain"] == focus["declarations"]["domain"]:
                continue
            matches, _ = checker._isomorphisms(focus, other)
            if matches:
                return {"world_id": other["world_id"]}
        return {"world_id": None}
    return None


correct = Counter()
total = Counter()
for rid, p in packets.items():
    kind = p["record"]["query"]["kind"]
    if kind == "role_set":
        continue
    target = checker.derive_target(p["source"], p["record"]["query"])
    admissible = {checker._canonical(a["value"]) for a in target["admissible_answers"]}
    try:
        guess = flag_rule(p["source"], p["record"]["query"])
    except Exception as exc:
        guess = {"__error__": repr(exc)}
    hit = checker._canonical(guess) in admissible
    total[(side(rid), kind)] += 1
    correct[(side(rid), kind)] += int(hit)
print("zero-learning rule using ONLY the focus world + the query arguments (graph edges allowed):")
for s in ("held", "trained", "excluded"):
    for kind in c.KINDS:
        if kind == "role_set":
            continue
        if total[(s, kind)]:
            print("   ", s, kind, "%d/%d" % (correct[(s, kind)], total[(s, kind)]))

# ---------- 4. a reader that has NO edge access: what is left ----------
noedge_correct = Counter()
noedge_total = Counter()
for rid, p in packets.items():
    q = p["record"]["query"]
    kind = q["kind"]
    if kind in ("role_set", "parts", "edge_account", "reach"):
        continue
    target = checker.derive_target(p["source"], q)
    admissible = {checker._canonical(a["value"]) for a in target["admissible_answers"]}
    focus = next(w for w in p["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
    if kind == "definition":
        guess = {"whole": focus["declared_whole"],
                 "kind_ref": answers.declaration_ref(focus["world_id"], "kind"),
                 "function_ref": answers.declaration_ref(focus["world_id"], "function")}
    elif kind == "context":
        guess = {"setting_ref": answers.declaration_ref(focus["world_id"], "setting"),
                 "participants": sorted(focus["declarations"]["participants"])}
    else:
        continue
    noedge_total[(side(rid), kind)] += 1
    noedge_correct[(side(rid), kind)] += int(checker._canonical(guess) in admissible)
print("flags only, no edges at all (definition, context):")
for key in sorted(noedge_total):
    print("   ", key, "%d/%d" % (noedge_correct[key], noedge_total[key]))

# ---------- 5. reach: the lexical tie-break needs the node NAME order ----------
lex = Counter()
for rid, p in packets.items():
    q = p["record"]["query"]
    if q["kind"] != "reach":
        continue
    worlds = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = worlds[q["focus_world_id"]]
    adj = checker._adjacency(focus)
    whole, part = q["arguments"]["whole"], q["arguments"]["part"]
    if part in adj[whole]:
        continue
    children = adj[whole]
    if not children:
        continue
    # A machine blind to ref order sees a SET of children. The checker picks the first child
    # that reaches part, in sorted-ref order. Multiple reaching children means the answer is
    # decided by an order the reader is forbidden to see.
    reaching = [f for f in children if checker._bfs(adj, f, part)[0] is not None]
    if len(reaching) > 1:
        lex[side(rid)] += 1
print("reach records whose VIA node is decided by the hidden node-ref order:", dict(lex))

print()
print("TOTALS: held %d trained %d excluded %d ; dev packets %d" % (len(held), len(trained), len(excluded), len(dev)))
