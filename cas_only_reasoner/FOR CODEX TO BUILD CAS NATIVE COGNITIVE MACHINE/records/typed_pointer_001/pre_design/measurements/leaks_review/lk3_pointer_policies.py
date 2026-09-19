"""LEAKS LENS lk3: zero-learning POINTING policies, scored in the machine's own slot space.

Each policy writes one score per symbol of every slot of the EXISTING slot plan, then
the shared decoder slots.score_decisions + slots.assemble_answer turn that into an
answer, and the private checker says whether it is right. This is the pointer machine's
own output path with no learned weights at all. Pure Python, no torch, no network.

    python lk3_pointer_policies.py
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for  # noqa: E402

assert "torch" not in sys.modules
sys.stdout.reconfigure(line_buffering=True)

m = Material()
frozen, slots, checker, answers = m.frozen, m.slots, m.checker, m.answers
packets, worlds, side = m.packets, m.worlds, m.side
flags = flags_for(m)
ok, recount = m.ok, m.recount
kind_of = m.kind_of

print()
print("MATERIAL")
print("  records held/trained/excluded", len(m.held), len(m.trained), len(m.excluded))
print("  held questions", len(m.held_questions), "trained questions", len(m.trained_questions))
print("  eligible", len(m.eligible), "shortcut-removed", len(m.shortcut_hit))
print("  eligible by kind", dict(sorted(Counter(kind_of[q] for q in m.eligible).items())))
PLANS = {row["record_id"]: slots.compile_slots(packets[row["record_id"]]) for row in frozen["registry"]}


def aliases(plan):
    node, world, nodes_of = {}, {}, {}
    for w in plan["aliases"]["worlds"]:
        world[w["world_id"]] = w["alias"]
        nodes_of[w["world_id"]] = w["nodes"]
        for n in w["nodes"]:
            node[n["ref"]] = n["alias"]
    return node, world, nodes_of


def blank(plan):
    return {slot["slot_id"]: {symbol: 0.0 for symbol in slot["symbols"]} for slot in plan["slots"]}


def pick(scores, slot, symbol):
    assert symbol in slot["symbols"], (slot["field"], symbol, slot["symbols"][:5])
    scores[slot["slot_id"]] = {name: (1.0 if name == symbol else 0.0) for name in slot["symbols"]}


def node_of_rank(plan, row, rank):
    """The ref whose rank among the world's sorted node refs is `rank` (rank 0 = first)."""
    f = flags(row)
    return f["refs"][rank] if len(f["refs"]) > rank else None


def apply_policy(policy):
    rec_ok = {}
    for row in frozen["registry"]:
        rid = row["record_id"]
        plan = PLANS[rid]
        scores = policy(plan, row)
        decision = slots.score_decisions(packets[rid], scores)
        answer = slots.assemble_answer(packets[rid], decision)
        rec_ok[rid] = ok(rid, answer["value"])
    return rec_ok


def report(label, policy, kinds=KINDS, note=""):
    rec, rec_tot, q, q_tot = recount(apply_policy(policy))
    print()
    print("  POLICY: %s" % label)
    for k in kinds:
        print("    %-14s held-eligible %d/%d | held-all %d/%d | trained %d/%d | records %s"
              % (k, q["held_eligible"][k], q_tot["held_eligible"][k], q["held_all"][k], q_tot["held_all"][k],
                 q["trained"][k], q_tot["trained"][k],
                 " ".join("%s %d/%d" % (s, rec[s][k], rec_tot[s][k]) for s in SIDES)))
    print("    ALL EIGHT KINDS held-eligible %d/%d | held-all %d/%d | trained %d/%d"
          % (sum(q["held_eligible"][k] for k in KINDS), sum(q_tot["held_eligible"][k] for k in KINDS),
             sum(q["held_all"][k] for k in KINDS), sum(q_tot["held_all"][k] for k in KINDS),
             sum(q["trained"][k] for k in KINDS), sum(q_tot["trained"][k] for k in KINDS)))
    if note:
        print("    %s" % note)
    return rec


# ---------------------------------------------------------------- policies
def argument_node(pick_whole=True):
    """Point at the node the question itself names; the declared whole when it names none."""
    def policy(plan, row):
        f = flags(row)
        node_alias, world_alias, _ = aliases(plan)
        target_ref = f["WA"] if (pick_whole and f["WA"]) else f["DW"]
        scores = blank(plan)
        for slot in plan["slots"]:
            field, syms = slot["field"], slot["symbols"]
            if field == "node":
                pick(scores, slot, "PRESENT" if slot["coordinates"][0] == target_ref else "ABSENT")
            elif field == "participant":
                pick(scores, slot, "PRESENT" if slot["coordinates"][0] == target_ref else "ABSENT")
            elif field == "whole":
                pick(scores, slot, node_alias[target_ref])
            elif field == "reach":
                pick(scores, slot, "VIA_" + node_alias[target_ref])
            elif field in ("kind_ref", "function_ref", "setting_ref"):
                pick(scores, slot, world_alias[f["F"]])
            elif field == "world_id":
                pick(scores, slot, world_alias[f["F"]])
            elif field == "mode":
                pick(scores, slot, "MAPPING")
            elif field == "mapping_target":
                src = slot["coordinates"][0]
                tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"])
                rank = f["refs"].index(src) if src in f["refs"] else 0
                pick(scores, slot, node_alias[tgt[min(rank, len(tgt) - 1)]])
            elif field == "edge":
                pick(scores, slot, "ABSENT")
            elif field == "role":
                pick(scores, slot, "ABSENT")
        return scores
    return policy


def argument_part():
    """Point at the query's `part` argument wherever a node must be named."""
    def policy(plan, row):
        f = flags(row)
        node_alias, world_alias, _ = aliases(plan)
        scores = blank(plan)
        for slot in plan["slots"]:
            field = slot["field"]
            if field == "reach":
                pick(scores, slot, "VIA_" + node_alias[f["PA"]])
            else:
                pick(scores, slot, "ABSENT" if "ABSENT" in slot["symbols"] else slot["symbols"][0])
        return scores
    return policy


def focus_world():
    """Point at the focus world in every world-choice slot; the declared whole for nodes."""
    def policy(plan, row):
        f = flags(row)
        node_alias, world_alias, _ = aliases(plan)
        scores = blank(plan)
        for slot in plan["slots"]:
            field = slot["field"]
            if field in ("kind_ref", "function_ref", "setting_ref", "world_id"):
                pick(scores, slot, world_alias[f["F"]])
            elif field == "whole":
                pick(scores, slot, node_alias[f["DW"]])
            elif field in ("node", "participant"):
                pick(scores, slot, "PRESENT" if slot["coordinates"][0] == f["DW"] else "ABSENT")
            elif field == "reach":
                pick(scores, slot, "VIA_" + node_alias[f["DW"]])
            elif field == "edge":
                pick(scores, slot, "ABSENT")
            elif field == "role":
                pick(scores, slot, "ABSENT")
            elif field == "mode":
                pick(scores, slot, "MAPPING")
            elif field == "mapping_target":
                src = slot["coordinates"][0]
                tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"])
                rank = f["refs"].index(src) if src in f["refs"] else 0
                pick(scores, slot, node_alias[tgt[min(rank, len(tgt) - 1)]])
        return scores
    return policy


def present_non_argument():
    """PRESENT for every node except the one the question argues from."""
    def policy(plan, row):
        f = flags(row)
        excl = f["WA"] or f["DW"]
        scores = blank(plan)
        for slot in plan["slots"]:
            field = slot["field"]
            if field in ("node", "participant"):
                pick(scores, slot, "ABSENT" if slot["coordinates"][0] == excl else "PRESENT")
            elif field == "edge":
                pick(scores, slot, "ABSENT" if excl in slot["coordinates"] else "PRESENT")
            elif field == "role":
                pick(scores, slot, "PRESENT")
            else:
                pick(scores, slot, slot["symbols"][0])
        return scores
    return policy


def present_all(include_self_pairs):
    """PRESENT for every node (and every edge slot)."""
    def policy(plan, row):
        scores = blank(plan)
        for slot in plan["slots"]:
            field = slot["field"]
            if field in ("node", "participant", "role"):
                pick(scores, slot, "PRESENT")
            elif field == "edge":
                a, b = slot["coordinates"]
                pick(scores, slot, "PRESENT" if (include_self_pairs or a != b) else "ABSENT")
            else:
                pick(scores, slot, slot["symbols"][0])
        return scores
    return policy


def rank_policy(rank):
    def policy(plan, row):
        f = flags(row)
        node_alias, world_alias, _ = aliases(plan)
        ref = f["refs"][rank] if len(f["refs"]) > rank else f["refs"][0]
        scores = blank(plan)
        for slot in plan["slots"]:
            field = slot["field"]
            if field in ("node", "participant"):
                pick(scores, slot, "PRESENT" if slot["coordinates"][0] == ref else "ABSENT")
            elif field == "whole":
                pick(scores, slot, node_alias[ref])
            elif field == "reach":
                pick(scores, slot, "VIA_" + node_alias[ref])
            elif field in ("kind_ref", "function_ref", "setting_ref", "world_id"):
                pick(scores, slot, world_alias[f["F"]])
            elif field == "mode":
                pick(scores, slot, "MAPPING")
            elif field == "mapping_target":
                tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"])
                src = slot["coordinates"][0]
                r = f["refs"].index(src) if src in f["refs"] else 0
                pick(scores, slot, node_alias[tgt[min(r, len(tgt) - 1)]])
            elif field == "edge":
                pick(scores, slot, "ABSENT")
            elif field == "role":
                pick(scores, slot, "ABSENT")
        return scores
    return policy


def all_ties():
    """Every symbol of every slot gets 0.0: score_decisions picks the FIRST declared symbol."""
    def policy(plan, row):
        return blank(plan)
    return policy


# majority symbol per (kind, field), estimated on the TRAINED records' correct answers
def majority_table():
    counts = defaultdict(Counter)
    for row in frozen["registry"]:
        if side[row["record_id"]] != "trained":
            continue
        plan = PLANS[row["record_id"]]
        node_alias, world_alias, _ = aliases(plan)
        for answer in checker.derive_target(packets[row["record_id"]]["source"], row["query"])["admissible_answers"]:
            value = answer["value"]
            for slot in plan["slots"]:
                field, syms = slot["field"], slot["symbols"]
                if field == "role":
                    symbol = "PRESENT" if slot["coordinates"][0] in value["roles"] else "ABSENT"
                elif field == "whole":
                    symbol = node_alias[value["whole"]]
                elif field in ("kind_ref", "function_ref", "setting_ref"):
                    symbol = world_alias[value[field].rsplit("/decl/", 1)[0]]
                elif field == "participant":
                    symbol = "PRESENT" if slot["coordinates"][0] in value["participants"] else "ABSENT"
                elif field == "world_id":
                    symbol = "NO_MATCH" if value["world_id"] is None else world_alias[value["world_id"]]
                elif field == "node":
                    symbol = "PRESENT" if slot["coordinates"][0] in value["nodes"] else "ABSENT"
                elif field == "edge":
                    symbol = "PRESENT" if {"source": slot["coordinates"][0], "target": slot["coordinates"][1]} in value["edges"] else "ABSENT"
                elif field == "reach":
                    symbol = "VIA_" + node_alias[value["via"]] if value["state"] == "VIA" else value["state"]
                elif field == "mode":
                    symbol = value["status"]
                elif field == "mapping_target":
                    src = slot["coordinates"][0]
                    if not value["pairs"]:
                        symbol = "NO_MATCH"
                    else:
                        rank = [p["source"] for p in value["pairs"]].index(src)
                        symbol = node_alias[value["pairs"][rank]["target"]]
                else:
                    symbol = "ABSENT"
                key = (plan["kind"], field)
                if field == "mapping_target":
                    src = slot["coordinates"][0]
                    focus_refs = sorted(n["ref"] for n in worlds[row["query"]["focus_world_id"]]["nodes"])
                    key = (plan["kind"], field, focus_refs.index(src))
                counts[key][symbol] += 1
    return {key: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for key, c in counts.items()}


MAJORITY = majority_table()


def majority_policy():
    def policy(plan, row):
        f = flags(row)
        scores = blank(plan)
        for slot in plan["slots"]:
            key = (plan["kind"], slot["field"])
            if slot["field"] == "mapping_target":
                src = slot["coordinates"][0]
                key = (plan["kind"], slot["field"], f["refs"].index(src))
            symbol = MAJORITY.get(key, MAJORITY.get((plan["kind"], slot["field"]), slot["symbols"][0]))
            if symbol not in slot["symbols"]:
                symbol = slot["symbols"][0]
            pick(scores, slot, symbol)
        return scores
    return policy


print()
print("ZERO-LEARNING POINTING POLICIES (the machine's own decoder, no learned weights)")
report("point at the ARGUMENT node (the query's `whole`; the declared whole when the question names none)",
       argument_node())
report("point at the query's `part` argument wherever a node must be named", argument_part())
report("point at the FOCUS world (world-choice slots) and the declared whole (node slots)", focus_world())
report("PRESENT for every NON-ARGUMENT node (all nodes except the query's `whole` / declared whole)",
       present_non_argument())
report("PRESENT for every node, every edge pair INCLUDING self-pairs", present_all(True))
report("PRESENT for every node, edge pairs EXCLUDING self-pairs", present_all(False))
report("pick the alphabetically FIRST node ref (rank 0)", rank_policy(0))
report("pick the node with the LOWEST rank (rank 0 -- identical to the alphabetical rule by construction)",
       rank_policy(0))
report("pick the node with the HIGHEST rank (alphabetically last ref)", rank_policy(-1))
print()
print("  MAJORITY SYMBOL PER SLOT (estimated on the trained records' correct answers, no neurons):")
for key in sorted(MAJORITY, key=lambda k: (k[0], k[1], k[2] if len(k) > 2 else -1)):
    print("    %-16s %-14s %-6s -> %s" % (key[0], key[1], "" if len(key) < 3 else "rank %d" % key[2], MAJORITY[key]))
report("pick the MAJORITY symbol for the slot (a fitted constant, no neuron is trained)", majority_policy())
report("ALL SYMBOLS TIED at 0.0: the shared decoder's first-declared-symbol tie rule fires", all_ties(),
       note="this is what an untrained pointer machine with equal logits emits (slots.py:293 argmax over the declared order)")

print()
print("NOTE: rank 0 IS 'alphabetically first ref' (checker.py:72-73 sorts node refs, slots.py:55-60 makes the aliases),")
print("      so the two policies above are the same function and necessarily give identical numbers.")
print("      policy functions are applied per record, so a question counts only when ALL its records are right.")
