"""LEAKS LENS lk1: does the DESIGN_DRAFT_v0.1 section 2.1 input list carry the held answer?

Pure Python, no torch, no network, read-only on every existing file.
Walks the exact proposed input fields against the private checker's answer rules
(checker.py _derive_values / _reach / focal.derive_roles) for all eight kinds.

    python lk1_answer_carriers.py
"""
import re
import sys
import time
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for  # noqa: E402

assert "torch" not in sys.modules
sys.stdout.reconfigure(line_buffering=True)

m = Material()
frozen, checker, answers, slots, tok = m.frozen, m.checker, m.answers, m.slots, m.tokenizer
packets, worlds, by_id, side = m.packets, m.worlds, m.by_id, m.side
held_questions, trained_questions = m.held_questions, m.trained_questions
kind_of, world_of = m.kind_of, m.world_of
flags = flags_for(m)
ok, score, recount = m.ok, m.score, m.recount
canonical = m.canonical

print()
print("MATERIAL")
print("  records held/trained/excluded", len(m.held), len(m.trained), len(m.excluded))
print("  held questions", len(held_questions), "records covered", sum(len(v) for v in held_questions.values()))
print("  trained questions", len(trained_questions))
print("  eligible", len(m.eligible), "shortcut-removed", len(m.shortcut_hit))
print("  eligible by kind", dict(sorted(Counter(kind_of[q] for q in m.eligible).items())))
print("  eligible by world", dict(sorted(Counter(world_of[q][:14] for q in m.eligible).items())))
print("  held questions by kind (all)", dict(sorted(Counter(kind_of[q] for q in held_questions).items())))
print("  shortcut per kind (input-blind, the registered removal)", m.shortcut)


def table(label, rule_of_kind, kinds=KINDS):
    rec_ok = score(rule_of_kind)
    rec, rec_tot, q, q_tot = recount(rec_ok)
    print("  %s" % label)
    for k in kinds:
        print("    %-14s held-eligible %d/%d | held-all %d/%d | trained %d/%d | records %s"
              % (k, q["held_eligible"][k], q_tot["held_eligible"][k], q["held_all"][k], q_tot["held_all"][k],
                 q["trained"][k], q_tot["trained"][k],
                 " ".join("%s %d/%d" % (s, rec[s][k], rec_tot[s][k]) for s in SIDES)))
    return rec_ok


print()
print("PART A -- the checker's answer components and the proposed input field that carries each")
print("  (input fields are exactly DESIGN_DRAFT_v0.1 section 2.1)")
ROWS = (
    ("role_set", "roles[1..6] + status, from the focal_excerpt text ONLY (focal.py:246-272)",
     "the query's focal_excerpt text itself (the entire input for this kind)",
     "no candidate set: the answer text IS part of the input"),
    ("definition", "whole = focus.declared_whole; kind_ref and function_ref = the FOCUS world's own ids",
     "per-node flag is_declared_whole; per-world flag is_focus_world; the focus world's kind/function text",
     "kind_ref/function_ref slots list all 64 worlds"),
    ("context", "setting_ref = the FOCUS world's id; participants = focus.declarations.participants",
     "per-node flag is_participant; per-world flag is_focus_world; the focus world's setting text",
     "setting_ref slot lists all 64 worlds"),
    ("analogy", "every bank world with a different declared domain and an isomorphic graph",
     "per-world domain word; per-world graph (through message passing)",
     "world_id slot lists NO_MATCH + all 64 worlds"),
    ("correspondence", "NO_MATCH, or every edge-preserving node bijection",
     "per-world flag is_correspondence_target; both graphs through message passing",
     "candidate list = NO_MATCH + every syntactic bijection of the two node sets"),
    ("parts", "children of the query's whole argument (one directed hop)",
     "the contains adjacency given to message passing; per-node is_participant",
     "one ABSENT/PRESENT slot per node of the focus world"),
    ("edge_account", "the complete contains edge set of the focus world",
     "the contains adjacency given to message passing",
     "one ABSENT/PRESENT slot per ordered node pair (including self-pairs)"),
    ("reach", "DIRECT / VIA(via) / ABSENT, BFS over sorted-ref neighbour order",
     "the contains adjacency given to message passing; question flags is_whole / is_part",
     "one slot: ABSENT, DIRECT, VIA_<every node>"),
)
for kind, answer_text, input_text, cand in ROWS:
    print("  %-14s answer  : %s" % (kind, answer_text))
    print("  %-14s input   : %s" % ("", input_text))
    print("  %-14s candidate space in the input: %s" % ("", cand))

print()
print("PART B -- role_set: the excerpt text IS the answer (the TEXT tier is not a world-reading test)")
from cas_meta2.typed_teaching import focal as focal_mod  # noqa: E402
from cas_meta2.typed_teaching import tokenization  # noqa: E402

PREFIX = focal_mod.PREFIXES
PREFIX_ROLES = dict(focal_mod._ROLES)


def clause_roles(excerpt):
    roles = set()
    for one_line in excerpt.split("\n"):
        names = [n for n, pre in PREFIX.items() if one_line.startswith(pre)]
        assert len(names) == 1, one_line[:40]
        roles.update(PREFIX_ROLES[names[0]])
    return sorted(roles)


vocab_units = {bytes.fromhex(v[6:-1]).decode() for v in tok.vocabulary[tokenization.WORD_START:]}
UNIT = re.compile(tokenization.UNIT_RULE)


def bag_roles(excerpt):
    """Position-free bag of token units: a clause prefix is present iff its words are all in the bag."""
    bag = Counter(UNIT.findall(excerpt))
    roles = set()
    for name, prefix in PREFIX.items():
        words = UNIT.findall(prefix)
        if words and all(bag[w] >= words.count(w) for w in set(words)):
            roles.update(PREFIX_ROLES[name])
    return sorted(roles)


def status(roles):
    return "INSUFFICIENT" if not roles else "UNIQUE" if len(roles) == 1 else "AMBIGUOUS"


role_status = defaultdict(Counter)
bag_groups = defaultdict(set)
for row in frozen["registry"]:
    if row["query"]["kind"] != "role_set":
        continue
    rid = row["record_id"]
    excerpt = row["query"]["arguments"]["focal_excerpt"]
    role_status[side[rid]][status(clause_roles(excerpt))] += 1
    bag_groups[tuple(sorted(tok.encode_text(excerpt)))].add(tuple(clause_roles(excerpt)))
print("  clause-prefix -> role map (public, printed by focal.grammar_profile):", PREFIX_ROLES)
print("  role_set status by side:", {s: dict(role_status[s]) for s in SIDES if role_status[s]})
print("  distinct token-bag signatures", len(bag_groups), "carrying >1 distinct role answer",
      sum(1 for v in bag_groups.values() if len(v) > 1))
table("role_set solved by the line-prefix rule (zero learned weights)",
      lambda k, r: {"roles": clause_roles(r["query"]["arguments"]["focal_excerpt"]),
                    "status": status(clause_roles(r["query"]["arguments"]["focal_excerpt"]))} if k == "role_set" else None,
      ("role_set",))
table("role_set solved by the POSITION-FREE token-bag rule (no order read at all)",
      lambda k, r: {"roles": bag_roles(r["query"]["arguments"]["focal_excerpt"]),
                    "status": status(bag_roles(r["query"]["arguments"]["focal_excerpt"]))} if k == "role_set" else None,
      ("role_set",))

print()
print("PART C -- definition and context: two input flags each, no single flag")
table("definition flag copy = is_declared_whole + is_focus_world (+ the world's kind/function text)",
      lambda k, r: {"whole": flags(r)["DW"], "kind_ref": answers.declaration_ref(flags(r)["F"], "kind"),
                    "function_ref": answers.declaration_ref(flags(r)["F"], "function")} if k == "definition" else None,
      ("definition",))
table("context flag copy = is_participant + is_focus_world (+ the world's setting text)",
      lambda k, r: {"setting_ref": answers.declaration_ref(flags(r)["F"], "setting"),
                    "participants": flags(r)["Psorted"]} if k == "context" else None,
      ("context",))

print()
print("PART D -- parts / edge_account / reach: how often the FLAGS or the ADJACENCY already ARE the answer")


def parts_flag(k, r):
    f = flags(r)
    if f["WA"] != f["DW"]:
        return {"nodes": []}
    return {"nodes": [p for p in f["Psorted"] if p != f["DW"]]}


def parts_adj(k, r):
    return {"nodes": sorted(checker._adjacency(flags(r)["w"])[flags(r)["WA"]])}


def edge_flag(k, r):
    f = flags(r)
    return {"edges": [{"source": f["DW"], "target": p} for p in f["Psorted"] if p != f["DW"]]}


def edge_adj(k, r):
    return checker._derive_values(packets[r["record_id"]]["source"], r["query"])[0][0]


def reach_flag(k, r):
    f = flags(r)
    if f["WA"] == f["DW"] and f["PA"] in f["Psorted"]:
        return {"state": "DIRECT", "via": None}
    return {"state": "ABSENT", "via": None}


def reach_adj(k, r):
    f = flags(r)
    return {"state": "DIRECT", "via": None} if f["PA"] in checker._adjacency(f["w"])[f["WA"]] else {"state": "ABSENT", "via": None}


def parts_child_set_in_participants(k, r):
    """The strong form of FP2: are the children of the whole EXACTLY participants minus whole?"""
    f = flags(r)
    kids = sorted(checker._adjacency(f["w"]).get(f["WA"], []))
    return {"nodes": kids} if kids == sorted(p for p in f["Psorted"] if p != f["WA"]) else {"nodes": []}


table("parts = participants - declared_whole (the FP2 rule)",
      lambda k, r: parts_flag(k, r) if k == "parts" else None, ("parts",))
table("parts = children of the whole argument (ONE adjacency hop; the input GIVES the adjacency)",
      lambda k, r: parts_adj(k, r) if k == "parts" else None, ("parts",))
table("edge_account = (declared_whole -> participants - whole) (FP2's edge analogue)",
      lambda k, r: edge_flag(k, r) if k == "edge_account" else None, ("edge_account",))
table("edge_account = the full adjacency recomputed by the checker's own rule (sanity: the input contains it)",
      lambda k, r: edge_adj(k, r) if k == "edge_account" else None, ("edge_account",))
table("reach = DIRECT if whole==declared_whole and part is a participant, else ABSENT (FP2's reach rule)",
      lambda k, r: reach_flag(k, r) if k == "reach" else None, ("reach",))
table("reach = DIRECT iff part is a child of whole, else ABSENT (one adjacency hop, no learning)",
      lambda k, r: reach_adj(k, r) if k == "reach" else None, ("reach",))

print()
print("PART E -- analogy and correspondence: what the candidate lists and the domain word give away")
domains = Counter(w["declarations"]["domain"] for w in worlds.values())
print("  bank worlds", len(worlds), "distinct domains", len(domains), "worlds per domain", dict(sorted(domains.items())))
anal = Counter()
tot_anal = Counter()
for row in frozen["registry"]:
    if row["query"]["kind"] != "analogy":
        continue
    s = side[row["record_id"]]
    f = flags(row)
    diff = [k for k, w in worlds.items() if w["declarations"]["domain"] != f["w"]["declarations"]["domain"]]
    here = m.admissible[row["record_id"]]
    tot_anal[s] += 1
    anal[("diff", s)] += len(diff)
    anal[("answers", s)] += len(here)
    anal[("nomatch_only", s)] += (here == {canonical({"world_id": None})})
    anal[("domain_rule", s)] += ok(row["record_id"], {"world_id": diff[0] if len(diff) == 1 else None})
print("  analogy records", {s: tot_anal[s] for s in SIDES})
print("  worlds with a DIFFERENT declared domain (domain-word filter width)",
      {s: "%d/%d" % (anal[("diff", s)], tot_anal[s]) for s in SIDES})
print("  admissible answer worlds (the answer is ANY ONE of them, checker.py:213-237)",
      {s: "%d/%d" % (anal[("answers", s)], tot_anal[s]) for s in SIDES})
print("  records whose only admissible answer is NO_MATCH", {s: "%d/%d" % (anal[("nomatch_only", s)], tot_anal[s]) for s in SIDES})
print("  solved by 'name the single different-domain world, else NO_MATCH'",
      {s: "%d/%d" % (anal[("domain_rule", s)], tot_anal[s]) for s in SIDES})
print("  chance of one admissible world from the different-domain pool",
      {s: "%d/%d" % (anal[("answers", s)], anal[("diff", s)]) for s in SIDES})
tot_anal_all = sum(tot_anal.values())
print("  chance of one admissible world from the whole 65-symbol candidate list",
      "%d/%d" % (sum(anal[("answers", s)] for s in SIDES), tot_anal_all * 65))
corr = Counter()
tot_corr = Counter()
for row in frozen["registry"]:
    if row["query"]["kind"] != "correspondence":
        continue
    s = side[row["record_id"]]
    f = flags(row)
    src = sorted(n["ref"] for n in worlds[f["F"]]["nodes"])
    tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"])
    cands = answers.correspondence_candidates(packets[row["record_id"]]["source"], row["query"])
    here = m.admissible[row["record_id"]]
    tot_corr[s] += 1
    corr[("forced", s)] += (len(cands) == 1)
    corr[("nomatch_admissible", s)] += (canonical({"status": "NO_MATCH", "pairs": []}) in here)
    corr[("counts_differ", s)] += (len(src) != len(tgt))
    corr[("edges_differ", s)] += (len(worlds[f["F"]]["contains"]) != len(worlds[f["T"]]["contains"]))
    corr[("mappings", s)] += len(here)
    corr[("candidates", s)] += len(cands)
    guess = ({"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(src, tgt)]}
             if len(src) == len(tgt) else {"status": "NO_MATCH", "pairs": []})
    corr[("count_rule", s)] += ok(row["record_id"], guess)
    guess2 = ({"status": "NO_MATCH", "pairs": []}
              if len(src) != len(tgt) or len(worlds[f["F"]]["contains"]) != len(worlds[f["T"]]["contains"])
              else {"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(src, tgt)]})
    corr[("count_edge_rule", s)] += ok(row["record_id"], guess2)
print("  correspondence records", {s: tot_corr[s] for s in SIDES})
print("  NO_MATCH is among the admissible answers",
      {s: "%d/%d" % (corr[("nomatch_admissible", s)], tot_corr[s]) for s in SIDES},
      "-> the mode slot is a constant across the whole course when this is 0")
print("  forced candidate space (len(candidates)==1: the decision is NO_MATCH with no input read)",
      {s: "%d/%d" % (corr[("forced", s)], tot_corr[s]) for s in SIDES})
print("  node counts differ", {s: "%d/%d" % (corr[("counts_differ", s)], tot_corr[s]) for s in SIDES},
      "| edge counts differ", {s: "%d/%d" % (corr[("edges_differ", s)], tot_corr[s]) for s in SIDES})
print("  admissible mappings / syntactic candidates (chance of a random bijection)",
      {s: "%d/%d" % (corr[("mappings", s)], corr[("candidates", s)]) for s in SIDES})
print("  solved by the node-count rule", {s: "%d/%d" % (corr[("count_rule", s)], tot_corr[s]) for s in SIDES})
print("  solved by the node-count-or-edge-count rule", {s: "%d/%d" % (corr[("count_edge_rule", s)], tot_corr[s]) for s in SIDES})
print("  admissible-answer multiplicity per record (analogy = answer worlds, correspondence = admissible bijections,")
print("  reach = 1 by construction): the checker counts a prediction right if it equals ANY admissible answer")
for kind in ("analogy", "correspondence"):
    dist = defaultdict(Counter)
    for row in frozen["registry"]:
        if row["query"]["kind"] != kind:
            continue
        dist[side[row["record_id"]]][len(m.admissible[row["record_id"]])] += 1
    print("    %-14s %s" % (kind, {s: dict(sorted(dist[s].items())) for s in SIDES if dist[s]}))

print()
print("PART F -- slot-plan symbol alphabets (what the answer has to be expressed in)")
sizes = defaultdict(Counter)
for row in frozen["registry"]:
    plan = slots.compile_slots(packets[row["record_id"]])
    for slot in plan["slots"]:
        sizes[(plan["kind"], slot["field"])][len(slot["symbols"])] += 1
for key in sorted(sizes):
    print("  %-16s %-14s symbols %s" % (key[0], key[1], dict(sizes[key])))

print()
print("PART G -- node-name order and the optional rank feature")
print("  checker._nodes = sorted(node['ref']) (checker.py:72-73); slots.alias_table N0..N9 = sorted refs (slots.py:55-60)")
print("  so 'rank among the world's sorted node refs' IS the alphabetical position of the hidden ref.")
rank_change = Counter()
rank_tot = Counter()
for row in frozen["registry"]:
    if row["query"]["kind"] != "reach":
        continue
    s = side[row["record_id"]]
    rank_tot[s] += 1
    q = row["query"]
    w = worlds[q["focus_world_id"]]
    refs = sorted(n["ref"] for n in w["nodes"])
    base, _ = checker._reach(w, q)
    for order in permutations(refs):
        pi = dict(zip(refs, order))
        w2 = dict(w)
        w2["contains"] = [{**e, "source": pi[e["source"]], "target": pi[e["target"]]} for e in w["contains"]]
        q2 = {**q, "arguments": {"whole": pi[q["arguments"]["whole"]], "part": pi[q["arguments"]["part"]]}}
        a2, _ = checker._reach(w2, q2)
        expect = {"state": base["state"], "via": None if base["via"] is None else pi[base["via"]]}
        if a2 != expect:
            rank_change[s] += 1
            break
print("  reach records whose answer changes under a node-name relabelling:",
      {s: "%d/%d" % (rank_change[s], rank_tot[s]) for s in SIDES})

print()
print("PART H -- the declared participants list is an AUTHORED order, not a graph fact")
print("  example: participants", [x[-2:] for x in worlds[sorted(worlds)[0]]["declarations"]["participants"]],
      "-> rank 1,2,3 follows the authored order, and the sorted refs are",
      [x[-2:] for x in sorted(n["ref"] for n in worlds[sorted(worlds)[0]]["nodes"])])
print("  worlds whose participants list is already in sorted ref order:",
      sum(1 for w in worlds.values() if w["declarations"]["participants"] == sorted(w["declarations"]["participants"])),
      "of", len(worlds))
print("  worlds whose primary_labels == participants:",
      sum(1 for w in worlds.values() if w["declarations"]["primary_labels"] == w["declarations"]["participants"]),
      "of", len(worlds))
print("  participants_basis values", dict(Counter(w["declarations"]["participants_basis"] for w in worlds.values())))
same_index = 0
total_nodes = 0
for w in worlds.values():
    refs = sorted(n["ref"] for n in w["nodes"])
    for position, ref in enumerate(refs):
        total_nodes += 1
        same_index += (ref.rsplit("/n", 1)[1] == str(position))
print("  node refs whose position in the sorted ref list equals its own stored index ('n<i>' == position i):",
      same_index, "of", total_nodes)
print("  -> the registered rank feature (DG3) IS the public node alias N<i> (slots.py:55-60), so adding rank adds")
print("     a per-node index the design says it excludes ('NO node alias index'), and it destroys the")
print("     permutation-equivariance the draft's section 5 vacuity paragraph relies on.")
w0 = worlds[sorted(worlds)[0]]
print("  example alias table vs stored index:",
      [(("N%d" % i), sorted(n["ref"] for n in w0["nodes"])[i].rsplit("/n", 1)[1])
       for i in range(len(w0["nodes"]))])
