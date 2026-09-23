"""Map LB18's 17 held analogy records to question ids; check they are the frozen-18 analogy questions.
Pure JSON, no torch."""
import json, sys
from pathlib import Path
R = Path(sys.argv[1])
TP = R / "records/typed_pointer_001"
lb18_rids = """1374d8b8432c 69d6b554ce25 adf5318ae5db 889a93b1f916 53870b56d366 de7d25c7d5e1 1b51609b7d4d 2e09ef23d9a7
fbbd55675810 d81bdc6ba341 af56d18c5704 c73be6489364 9a30ca37b668 117dbea75693 c3d238a923dc 33510a144755 7dddbc3db00c""".split()
g = json.load(open(TP / "admission_helm1_certified/gate_reading.json", encoding="utf-8"))
pop = set(g["population"]["question_ids"])
oc = g["oracle_ceilings"]
floor = set(oc["population_ids_the_rule_solves"]) | set(oc["rank_last_ids_the_rule_solves"])
print("frozen population", len(pop), "one-hop|rank-last floor", len(floor & pop))
for receipt in ["receipt_helm1_certified_20260917", "receipt_20260917", "receipt_20260918", "receipt_20260919",
                "receipt_helm1_certified_20260918", "receipt_helm1_certified_20260919"]:
    d = json.load(open(TP / receipt / "collected/results/artifacts/course_p10_scoring.json", encoding="utf-8"))
    rows = d["rows"]
    rid2 = {r["record_id"][-12:]: r for r in rows}
    hits = [rid2[x] for x in lb18_rids if x in rid2]
    qids = sorted({h["query_id"] for h in hits})
    kinds = {h["kind"] for h in hits}
    adm = sorted({h["admissible_answer_count"] for h in hits})
    in_pop = [q for q in qids if q in pop]
    pop_analogy = sorted({r["query_id"] for r in rows if r["query_id"] in pop and r["kind"] == "analogy"})
    correct_final = sum(1 for h in hits if h["correct"])
    # union floor if analogy added
    union = (floor & pop) | set(in_pop)
    finals = {}
    for r in rows:
        if r["query_id"] in pop:
            finals.setdefault(r["query_id"], []).append(r["correct"])
    q_right = {q for q, v in finals.items() if all(v)}
    beyond = sorted(q[12:20] for q in q_right - union)
    missed_in_union = sorted(q[12:20] for q in union - q_right)
    print(receipt, "| LB18 held rids found", len(hits), "kinds", kinds, "admissible counts", adm,
          "| distinct questions", len(qids), "in frozen18", len(in_pop), "| frozen-18 analogy qids", len(pop_analogy),
          "same set", set(in_pop) == set(pop_analogy),
          "| model correct on these 17 records at p10", correct_final,
          "| union floor (one-hop|rank-last|LB18 analogy)", len(union),
          "| frozen questions right at p10", len(q_right), "right outside union", beyond, "union questions missed", len(missed_in_union))
