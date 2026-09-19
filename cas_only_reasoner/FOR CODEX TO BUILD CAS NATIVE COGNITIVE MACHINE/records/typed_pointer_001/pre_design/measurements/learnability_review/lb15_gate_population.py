"""LB15 — the exact ceiling of the draft's correspondence head as specified in section 2.2,
and the exact eligible-question population of the unchanged gate.

Part 1. The draft's correspondence head is
    logit(v) = <W_p q_slot, h_v>,  q_slot = q (+ h_source)
and the per-node score has no input carrying the target world's edge set (section 2.1
forbids derived relations, and asks for "is the query's whole/part argument" flags only).
The declared decision rule is "first candidate wins exact scalar ties" with candidates in
lexical order: NO_MATCH first, then all target-ref permutations in lexical order against
lexical source refs. So the head can only ever express the FIRST syntactic bijection or a
bijection it can justify by a score that is constant across automorphisms. This script
measures, for every correspondence record, whether the first-candidate mapping is correct.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION"), str(CNCM / "records/typed_practice_001")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, checker, slots, answers
import evaluate_gates as eg

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
heldset, trainedset = set(held), set(trained)
packets = dict(c.public_packets(frozen))


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


# ---- candidate enumeration order, exactly as slots.assemble_answer walks it ----
first_acc = Counter()
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "correspondence":
        continue
    plan = slots.compile_slots(p)
    cands = plan["correspondence_candidates"]
    # order the way the decision rule describes: NO_MATCH first, then permutations in
    # lexical order of the permutation tuple
    tgt = sorted({s["symbols"][0] for s in plan["slots"] if s["field"] == "mapping_target"})
    perm_cands = [cand for cand in cands[1:]]
    first = cands[0] if not perm_cands else perm_cands[0]
    adm = {checker._canonical(a["value"]) for a in checker.derive_target(p["source"], q)["admissible_answers"]}
    if checker._canonical(first["value"]) in adm:
        first_acc[(side(rid), "FIRST_CANDIDATE_OK")] += 1
    else:
        first_acc[(side(rid), "FIRST_CANDIDATE_WRONG")] += 1
    first_acc[(side(rid), "TOTAL")] += 1
print("correspondence: is the FIRST candidate (the tie-break winner for an information-free head) correct?")
for s in ("held", "trained", "excluded"):
    print("   %-9s %d/%d first-candidate correct" % (s, first_acc[(s, "FIRST_CANDIDATE_OK")], first_acc[(s, "TOTAL")]))

# ---- the eligible-question population of the unchanged gate, by kind ----
heldq = c.held_back_questions(frozen)
eligible, shortcut_hit, shortcut = eg.eligible_questions(frozen, trainedset, heldq)
kind_of = {r["query"]["query_id"]: r["query"]["kind"] for r in frozen["registry"]}
world_of = {r["query"]["query_id"]: r["source_world_id"] for r in frozen["registry"]}
print()
print("held-back questions %d ; eligible %d ; removed as input-blind shortcut %d"
      % (len(heldq), len(eligible), len(shortcut_hit)))
print("eligible questions by kind:", dict(sorted(Counter(kind_of[q] for q in eligible).items())))
print("eligible questions by world:", dict(sorted(Counter(world_of[q] for q in eligible).items())))
print("eligible questions by (kind, world):")
for key in sorted({(kind_of[q], world_of[q]) for q in eligible}):
    print("   %-16s %s  %d" % (key[0], key[1][-12:], sum(1 for q in eligible if (kind_of[q], world_of[q]) == key)))
DR = ("definition", "context")
REL = ("parts", "edge_account", "reach", "correspondence", "analogy")
rel = [q for q in eligible if kind_of[q] in REL]
dr = [q for q in eligible if kind_of[q] in DR]
print("DIRECT_READ eligible %d (worlds %d) ; RELATIONAL eligible %d (worlds %d)"
      % (len(dr), len({world_of[q] for q in dr}), len(rel), len({world_of[q] for q in rel})))
print("relational eligible by kind:", dict(sorted(Counter(kind_of[q] for q in rel).items())))
print("relational eligible by world:", dict(sorted(Counter(world_of[q] for q in rel).items())))
print("shortcut-removed questions by kind:", dict(sorted(Counter(kind_of[q] for q in shortcut_hit).items())))
print()
for b in (6, 7, 8, 9, 10):
    print("   binomial upper tail P(X>=%d | n=%d, 1/2) = %s" % (b, b, eg.binomial_upper_tail(b, b)))
print()
print("minimum passing b at alpha = 1/100 with c=0:", [b for b in range(0, 12) if eg.binomial_upper_tail(b, b) <= eg.ALPHA][0])

# ---- what a flag/input copier achieves on the relational population ----
print()
print("RELATIONAL population size %d over %d worlds; a machine answering only from the" % (len(rel), len({world_of[q] for q in rel})))
print("draft's stated input flags (is whole, is part, focus marker, participants) can solve:")
flag_solved = []
for q in rel:
    rid = heldq[q][0]
    p = packets[rid]
    kind = kind_of[q]
    focus = next(w for w in p["source"]["worlds"] if w["world_id"] == p["source"]["focus_world_id"])
    nodes = sorted(n["ref"] for n in focus["nodes"])
    if kind == "reach":
        g = {"state": "ABSENT", "via": None}
    elif kind == "parts":
        whole = p["record"]["query"]["arguments"]["whole"]
        g = {"nodes": sorted(r for r in focus["declarations"]["participants"] if r != whole)}
    elif kind == "edge_account":
        g = {"edges": []}
    elif kind == "correspondence":
        tgt = sorted(n["ref"] for n in next(w for w in p["source"]["worlds"]
                                            if w["world_id"] == p["record"]["query"]["arguments"]["target_world_id"])["nodes"])
        g = {"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(nodes, tgt)]}
    else:
        g = {"world_id": None}
    adm = {checker._canonical(a["value"]) for a in checker.derive_target(p["source"], p["record"]["query"])["admissible_answers"]}
    if checker._canonical(g) in adm:
        flag_solved.append((kind, q, world_of[q][-12:]))
print("   flag-only solved relational eligible questions:", len(flag_solved), "of", len(rel))
for kind, q, w in flag_solved:
    print("      %-16s %s %s" % (kind, q[-12:], w))
print()
print("so the relational gate population a strict reader would use is %d questions"
      % (len(rel) - len(flag_solved)))
