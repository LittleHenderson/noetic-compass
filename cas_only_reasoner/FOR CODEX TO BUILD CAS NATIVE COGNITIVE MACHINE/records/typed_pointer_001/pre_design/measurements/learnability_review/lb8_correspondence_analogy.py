"""LB8 — correspondence and analogy: exact structure of every question, held and trained.

For each correspondence record: the focus world, the target world, whether the correct
status is MAPPING or NO_MATCH, how many bijections are admissible, and whether the node
mapping is forced by structure (degree classes) or is free.
"""
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, checker

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
heldset, trainedset = set(held), set(trained)


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


def degrees(w):
    ind, outd = Counter(), Counter()
    for e in w["contains"]:
        outd[e["source"]] += 1
        ind[e["target"]] += 1
    return {n["ref"]: (ind.get(n["ref"], 0), outd.get(n["ref"], 0)) for n in w["nodes"]}


def degree_multiset(w):
    return tuple(sorted(degrees(w).values()))


rows = []
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "correspondence":
        continue
    worlds = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus, target = worlds[q["focus_world_id"]], worlds[q["arguments"]["target_world_id"]]
    target_obj = checker.derive_target(p["source"], q)
    values = [a["value"] for a in target_obj["admissible_answers"]]
    statuses = {v["status"] for v in values}
    matches = [v for v in values if v["status"] == "MAPPING"]
    dm_f, dm_t = degree_multiset(focus), degree_multiset(target)
    # is the node mapping forced by degree classes?
    df, dt = degrees(focus), degrees(target)
    forced = False
    free = 0
    if matches:
        refs, trefs = sorted(df), sorted(dt)
        same_deg = all(df[a] == dt[b] for a, b in zip(refs, trefs))
        # count how many node pairs are forced: nodes in singleton degree classes on both sides
        cf = Counter(df.values())
        singleton = [r for r in df if cf[df[r]] == 1]
        forced = len(singleton) == len(df)
        free = len(df) - len(singleton)
    rows.append({"rid": rid, "side": side(rid), "status": "MAPPING" if matches else "NO_MATCH",
                 "n_matches": len(matches), "focus_nodes": len(focus["nodes"]), "target_nodes": len(target["nodes"]),
                 "deg_equal": dm_f == dm_t, "mapping_fully_forced_by_degree_classes": forced,
                 "nodes_not_forced": free,
                 "same_shape": checker._isomorphisms(focus, target)[1]["reason"]})

print("correspondence records: %d" % len(rows))
for s in ("held", "trained", "excluded"):
    sub = [r for r in rows if r["side"] == s]
    if not sub:
        continue
    print("  %-9s records %d  MAPPING %d  NO_MATCH %d  degree-multiset equal %d  mapping fully forced by degree classes %d"
          % (s, len(sub), sum(1 for r in sub if r["status"] == "MAPPING"),
             sum(1 for r in sub if r["status"] == "NO_MATCH"),
             sum(1 for r in sub if r["deg_equal"]),
             sum(1 for r in sub if r["mapping_fully_forced_by_degree_classes"])))
print()
print("distribution of admissible-bijection counts (MAPPING records only):")
print("  ", dict(sorted(Counter(r["n_matches"] for r in rows if r["status"] == "MAPPING").items())))
print("mapping never forced for any record (some node sits in a non-singleton degree class):",
      sum(1 for r in rows if r["status"] == "MAPPING" and not r["mapping_fully_forced_by_degree_classes"]),
      "of", sum(1 for r in rows if r["status"] == "MAPPING"))
print()
print("per-record detail (held):")
for r in rows:
    if r["side"] == "held":
        print("   %s status=%-8s bijections=%-2d deg_equal=%-5s forced=%-5s unforced_nodes=%d"
              % (r["rid"][-12:], r["status"], r["n_matches"], r["deg_equal"],
                 r["mapping_fully_forced_by_degree_classes"], r["nodes_not_forced"]))

# ---------- analogy ----------
print()
print("analogy records: which world is the correct answer, and how many candidates share its shape?")
an = []
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "analogy":
        continue
    worlds = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = worlds[q["focus_world_id"]]
    target_obj = checker.derive_target(p["source"], q)
    values = [a["value"] for a in target_obj["admissible_answers"]]
    chosen = [v["world_id"] for v in values if v["world_id"]]
    dm = degree_multiset(focus)
    same = [w for w, obj in worlds.items() if w != q["focus_world_id"] and degree_multiset(obj) == dm]
    an.append({"rid": rid, "side": side(rid), "n_answers": len(chosen), "chosen": chosen,
               "candidates_with_focus_shape": len(same),
               "chosen_is_bank_world": all(w in worlds for w in chosen),
               "target_is_in_bank_list": all(w in p["source"]["bank"]["world_ids"] for w in chosen),
               "domain_focus": focus["declarations"]["domain"]})
print("analogy records %d" % len(an))
for s in ("held", "trained", "excluded"):
    sub = [a for a in an if a["side"] == s]
    if not sub:
        continue
    print("  %-9s records %d  answers per record %s  candidates sharing the focus world's exact shape: %s"
          % (s, len(sub), dict(sorted(Counter(a["n_answers"] for a in sub).items())),
             dict(sorted(Counter(a["candidates_with_focus_shape"] for a in sub).items()))))
print()
print("ALL analogy answers, with the exact shape-equality route to them:")
for a in an:
    print("   %-12s side=%-9s answers=%d candidates-with-focus-shape=%d domain=%s"
          % (a["rid"][-12:], a["side"], a["n_answers"], a["candidates_with_focus_shape"], a["domain_focus"]))

# ---------- reach and parts: how much does the graph matter? ----------
print()
print("parts and reach: the answer as a function of the graph")
parts = Counter()
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "parts":
        continue
    worlds = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = worlds[q["focus_world_id"]]
    whole = q["arguments"]["whole"]
    t = checker.derive_target(p["source"], q)
    n = len(t["admissible_answers"][0]["value"]["nodes"])
    parts[(side(rid), n)] += 1
print("  parts answer-size histogram:", dict(sorted(parts.items())))
reach = Counter()
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "reach":
        continue
    t = checker.derive_target(p["source"], q)
    v = t["admissible_answers"][0]["value"]
    reach[(side(rid), q["rule"], v["state"])] += 1
print("  reach (side, rule, state) histogram:", dict(sorted(reach.items())))
edgeacc = Counter()
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "edge_account":
        continue
    t = checker.derive_target(p["source"], q)
    edgeacc[side(rid)] += len(t["admissible_answers"][0]["value"]["edges"])
print("  edge_account: total true edges by side:", dict(edgeacc))
