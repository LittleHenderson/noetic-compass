# JUDGE: which frozen-18 questions each run broke / gained, and whether the broken ones are in the contract's
# RANK_LAST_SOLVED_QUESTION_IDS and ORACLE_ONE_HOP_SOLVED_QUESTION_IDS (read as text; no import). Pure JSON + regex.
import json, os, re
ROOTP = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
BASE = ROOTP + "/records/typed_pointer_001"
src = open(ROOTP + "/research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py", encoding="utf-8").read()
def tuple_ids(name):
    m = re.search(name + r"\s*=\s*\((.*?)\)\n", src, re.S)
    return re.findall(r'"(typed-query-[0-9a-f]{64})"', m.group(1))
rank_last = set(tuple_ids("RANK_LAST_SOLVED_QUESTION_IDS"))
one_hop = set(tuple_ids("ORACLE_ONE_HOP_SOLVED_QUESTION_IDS"))
print("RANK_LAST ids", len(rank_last), "ONE_HOP ids", len(one_hop), "union", len(rank_last | one_hop))
for ver, adm in (("2.0", "admission_001"), ("1.0", "admission_helm1_certified")):
    g = json.load(open(os.path.join(BASE, adm, "gate_reading.json"), encoding="utf-8"))
    pop = g["seeds"]["20260917"]["G_LEARN_population"]["keys"]
    print(ver, "population", len(pop), "in rank_last", len(set(pop) & rank_last), "in one_hop", len(set(pop) & one_hop),
          "in union", len(set(pop) & (rank_last | one_hop)))
    rec = "receipt_%s" if ver == "2.0" else "receipt_helm1_certified_%s"
    for seed in ("20260917", "20260918", "20260919"):
        ck = os.path.join(BASE, rec % seed, "checkpoints")
        def qc(phase):
            rows = json.load(open(os.path.join(ck, phase + "_scoring.json"), encoding="utf-8"))["rows"]
            out = {}
            for r in rows:
                out.setdefault(r["query_id"], []).append(bool(r["correct"]))
            return {q: all(v) for q, v in out.items()}
        b0, b1 = qc("course_p00"), qc("course_p10")
        gained = [q for q in pop if not b0[q] and b1[q]]
        broken = [q for q in pop if b0[q] and not b1[q]]
        right_final = [q for q in pop if b1[q]]
        print("  ", ver, seed, "start", sum(b0[q] for q in pop), "final", len(right_final), "gained", len(gained), "broken",
              [(q[len("typed-query-"):][:8], "rank_last" if q in rank_last else "-", "one_hop" if q in one_hop else "-") for q in broken],
              "final-right outside union", [q[len("typed-query-"):][:8] for q in right_final if q not in (rank_last | one_hop)])
