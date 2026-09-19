"""LEAKS LENS lk5: other routes to a false LEARNS_NEW_WORLDS through the unchanged pipeline.

Covers the depth schedule coordinate, the joint correspondence loss, the world-choice
candidate lists, the choice of evaluation checkpoints, and the shortcut-removal rule.
Pure Python, no torch, no network, read-only on every existing file.

    python lk5_pipeline_routes.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for  # noqa: E402

assert "torch" not in sys.modules
sys.stdout.reconfigure(line_buffering=True)

m = Material()
frozen, slots, checker, eg = m.frozen, m.slots, m.checker, m.eg
packets, worlds, side, by_id = m.packets, m.worlds, m.side, m.by_id
flags = flags_for(m)
ok, score, recount = m.ok, m.score, m.recount
kind_of, world_of, canonical = m.kind_of, m.world_of, m.canonical
CNCM = m.c.__file__

print()
print("MATERIAL")
print("  records held/trained/excluded", len(m.held), len(m.trained), len(m.excluded))
print("  held questions", len(m.held_questions), "trained questions", len(m.trained_questions))
print("  eligible", len(m.eligible), "shortcut-removed", len(m.shortcut_hit))
print("  eligible by kind", dict(sorted(Counter(kind_of[q] for q in m.eligible).items())))

batch_by_id = {}
batches, stats = m.c.practice_schedule(frozen)
for b in batches:
    for rid in b["record_ids"]:
        batch_by_id.setdefault(rid, []).append(b)

print()
print("PART 1 -- the depth schedule coordinate")
print("  learner._forward accepts depth in (1,2,4,8) only (learner.py:128); every evaluation calls predict(., 8)")
print("  (typed_practice_worker.py:145); DESIGN_DRAFT_v0.1 says 'depth (=8, the worker's existing argument)'.")
print("  batch depth distribution", dict(sorted(Counter((b["pass"], b["depth"]) for b in batches if b["pass"] == 1).items())))
depth_kind = defaultdict(Counter)
for b in batches:
    for rid in b["record_ids"]:
        depth_kind[b["depth"]][kind_of[by_id[rid]["query"]["query_id"]]] += 1
print("  TRAINING PRESENTATIONS by depth and kind:")
for d in sorted(depth_kind):
    print("    depth %d: %s" % (d, dict(sorted(depth_kind[d].items()))))
print("  interference batches (16) are definition+context only, and they run AFTER the pass-10 evaluation")
print("  (typed_practice_worker.py:355-358 exports 'final' and evaluates pass 10; :366-385 then runs retention")
print("  and interference), so they cannot enter the gated checkpoints.")
kind_depth = {}
for kind in KINDS:
    present = [b["depth"] for b in batches for rid in b["record_ids"] if kind_of[by_id[rid]["query"]["query_id"]] == kind]
    kind_depth[kind] = (min(present), max(present), sorted(set(present)))
    print("    kind %-14s trained only at depths %s (min %d, max %d)" % (kind, kind_depth[kind][2], kind_depth[kind][0], kind_depth[kind][1]))
low = Counter()
tot = Counter()
for row in frozen["registry"]:
    if side[row["record_id"]] != "trained":
        continue
    k = row["query"]["kind"]
    for b in batch_by_id.get(row["record_id"], []):
        tot[k] += 1
        low[k] += (b["depth"] < 8)
print("  presentations at depth < 8 per kind (of all presentations):",
      {k: "%d/%d" % (low[k], tot[k]) for k in KINDS})

print()
print("PART 2 -- the joint correspondence loss")
corr_train = Counter()
for row in frozen["registry"]:
    if row["query"]["kind"] != "correspondence":
        continue
    s = side[row["record_id"]]
    corr_train[(s, "records")] += 1
    corr_train[(s, "presentations")] += len(batch_by_id.get(row["record_id"], []))
    corr_train[(s, "admissible")] += len(m.admissible[row["record_id"]])
print("  correspondence records / training presentations / admissible mappings",
      {s: "%d / %d / %d" % (corr_train[(s, "records")], corr_train[(s, "presentations")], corr_train[(s, "admissible")])
       for s in SIDES})
print("  the loss term is a valid-SET logsumexp over public candidates (learner.py:202-220), and the valid set")
print("  comes from the private target (loss_plan.py:100-105) -- it is applied to TRAINED records only.")
trained_naming_held = [r["record_id"] for r in frozen["registry"]
                       if side[r["record_id"]] == "trained"
                       and any(w in json.dumps(r, sort_keys=True) for w in m.c.held_worlds(frozen))]
print("  trained records whose text names a held world:", len(trained_naming_held))
trained_corr_targets = sorted({r["query"]["arguments"].get("target_world_id") for r in frozen["registry"]
                               if r["query"]["kind"] == "correspondence" and side[r["record_id"]] == "trained"})
print("  distinct correspondence target worlds in the trained set:", len(trained_corr_targets))
print("  any of them a held world:", bool(set(trained_corr_targets) & set(m.c.held_worlds(frozen))))
print("  analogy answers naming a held world in the trained set:",
      sum(1 for r in frozen["registry"] if r["query"]["kind"] == "analogy" and side[r["record_id"]] == "trained"
          and any(json.loads(a)["world_id"] in set(m.c.held_worlds(frozen)) for a in m.admissible[r["record_id"]])))
print("  NO_MATCH is never the admissible correspondence answer (measured in lk1), so the mode slot is a")
print("  constant: a machine that learns 'always MAPPING' converts every correspondence record into a")
print("  mapping guess. Chance per record = admissible mappings / syntactic candidates.")

print()
print("PART 3 -- the world-choice candidate lists")
wc = [q for q in m.eligible if kind_of[q] in ("definition", "context", "analogy")]
print("  held-eligible questions whose answer names a WORLD:", len(wc), "of", len(m.eligible),
      dict(sorted(Counter(kind_of[q] for q in wc).items())))
print("  of those, solved by the flag copy (is_focus_world + the declaration text): 5 definition + 5 context = 10")
print("  answer alphabet: definition kind_ref/function_ref 64 symbols, context setting_ref 64, analogy world_id 65")
print("  the input supplies every world's kind/function/setting declaration TEXT, so definition and context are")
print("  a text-matching task over the input, not a graph task (measured in lk1/lk2: 10/10 solved, no learning).")
print("  analogy keeps the whole 64-world bank as candidates: the domain word removes the 16 same-domain worlds,")
print("  leaving 48; the admissible answer set is 6-9 worlds, so one guess is right with probability 6/65..9/65.")

print()
print("PART 4 -- the choice of evaluation checkpoints")
print("  typed_practice_worker.py:326 evaluates pass 0; :357-358 evaluates passes 2,4,6,8,10")
print("  FULL_COURSE_CHECKPOINTS = (0,1,10) so held-back questions are read from the COURSE evaluations at")
print("  0, 1 and 10 and from the dedicated held-back evaluations at 2,4,6,8 (evaluate_gates.py:201-203).")
print("  The primary gate G_LEARN compares pass 0 with pass 10 only (evaluate_gates.py:216); the held-back")
print("  trajectory at 2/4/6/8 is reported but gates NOTHING. MORE_PRACTICE compares 1 with 10.")
print("  'final' is exported before retention/interference (typed_practice_worker.py:355-358), so the 'retained'")
print("  checkpoint is outside every gate.")
per_question = Counter(len(v) for v in m.held_questions.values())
print("  records per held-back question", dict(sorted(per_question.items())))
one = [q for q, v in m.held_questions.items() if len(v) == 1]
print("  held-back questions decided by a single record:", len(one), "of", len(m.held_questions),
      dict(sorted(Counter(kind_of[q] for q in one).items())))
print("  eligible ones:", len([q for q in one if q in m.eligible_set]))
print("  analogy questions: 5 eligible; the admissible answer set is 6-9 worlds out of 65, so a single record")
print("  can be right by guessing (measured chance band 6/65..9/65 per record).")

print()
print("PART 5 -- the shortcut-removal rule itself")
bank_order = eg._bank_order(frozen)
shortcut_registered = eg.shortcut_answers(frozen, m.trained_set)
forms_of = {row["record_id"]: {eg.alias_form(json.loads(a), bank_order) for a in m.admissible[row["record_id"]]}
            for row in frozen["registry"]}
counts_first = defaultdict(Counter)
counts_any = defaultdict(Counter)
for row in frozen["registry"]:
    if side[row["record_id"]] != "trained":
        continue
    k = row["query"]["kind"]
    first = sorted(m.admissible[row["record_id"]])[0]
    counts_first[k][eg.alias_form(json.loads(first), bank_order)] += 1
    for form in forms_of[row["record_id"]]:
        counts_any[k][form] += 1
best_first = {k: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, c in counts_first.items()}
best_any = {k: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, c in counts_any.items()}
print("  the registered removal uses the most common FIRST admissible trained answer per kind:",
      shortcut_registered == best_first)
removed_first, removed_any = set(), set()
for q in m.held_questions:
    k = kind_of[q]
    forms = set().union(*(forms_of[r] for r in m.held_questions[q]))
    if best_first.get(k) in forms:
        removed_first.add(q)
    if best_any.get(k) in forms:
        removed_any.add(q)
print("  registered removal size", len(m.shortcut_hit), "| recomputed from the same rule", len(removed_first),
      "| equal:", set(removed_first) == set(m.shortcut_hit))
print("  questions removed if the shortcut is the most common ANY admissible trained answer:", len(removed_any))
print("  extra questions that rule would remove:", sorted(removed_any - removed_first))
print("  per-kind constant ceilings (best single alias-form constant answer, trained estimate):")
for k in KINDS:
    held_q = [q for q in m.held_questions if kind_of[q] == k]
    solv = sum(1 for q in held_q if best_any.get(k) in set().union(*(forms_of[r] for r in m.held_questions[q])))
    elig = [q for q in m.eligible if kind_of[q] == k]
    solv_e = sum(1 for q in elig if best_any.get(k) in set().union(*(forms_of[r] for r in m.held_questions[q])))
    print("    %-14s all held %d/%d | eligible %d/%d | constant %s" % (k, solv, len(held_q), solv_e, len(elig), best_any.get(k)))
print("  the removal is recomputed at gate time and is NOT frozen as an explicit id list; any later change to")
print("  the split, the checker or the alias order silently changes the population. Freeze it (P13).")

print()
print("PART 6 -- what an untrained machine already answers (proxy: equal logits -> first declared symbol)")
def first_symbol(kind, row):
    plan = slots.compile_slots(packets[row["record_id"]])
    value = None
    scores = {s["slot_id"]: {sym: 0.0 for sym in s["symbols"]} for s in plan["slots"]}
    decision = slots.score_decisions(packets[row["record_id"]], scores)
    return slots.assemble_answer(packets[row["record_id"]], decision)["value"]


rec_ok = score(lambda k, r: first_symbol(k, r))
rec, rec_tot, q, q_tot = recount(rec_ok)
print("  equal-logit answers (every slot's first declared symbol) as a zero-information p0 proxy:")
for k in KINDS:
    print("    %-14s held-eligible %d/%d | held-all %d/%d | trained %d/%d"
          % (k, q["held_eligible"][k], q_tot["held_eligible"][k], q["held_all"][k], q_tot["held_all"][k],
             q["trained"][k], q_tot["trained"][k]))
print("  these are right at p0 by construction, so they cannot be scored as gains; they only add right-to-wrong risk.")

print()
print("PART 7 -- the reported label versus the reported tiers")
print("  G_LEARN_p0_to_p10 (the label) is computed on the 45 eligible questions over all eight kinds")
print("  (evaluate_gates.py:216). A flag copier gets definition 5/5 + context 5/5 there, so b=10, c=0 and")
print("  p = 2**-10 = 0.0009765625 <= 0.01, with two kinds and five held worlds. The label is printed from")
print("  that test alone; the tier split is prose. Until the primary label is the RELATIONAL test, the")
print("  pipeline's own reading can be satisfied with no relational competence at all.")
