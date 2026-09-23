# JUDGE: per run, the frozen-18 questions in the registered floor (rank-last | one-hop) that the START got right
# and that the FINAL got wrong; kinds from the gate reading. Pure JSON + regex.
import json, os, re
ROOTP = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
BASE = ROOTP + "/records/typed_pointer_001"
src = open(ROOTP + "/research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py", encoding="utf-8").read()
def tuple_ids(name):
    m = re.search(name + r"\s*=\s*\((.*?)\)\n", src, re.S)
    return re.findall(r'"(typed-query-[0-9a-f]{64})"', m.group(1))
floor = set(tuple_ids("RANK_LAST_SOLVED_QUESTION_IDS")) | set(tuple_ids("ORACLE_ONE_HOP_SOLVED_QUESTION_IDS"))
short = lambda q: q[len("typed-query-"):][:8]
for ver, adm, rec in (("2.0", "admission_001", "receipt_%s"), ("1.0", "admission_helm1_certified", "receipt_helm1_certified_%s")):
    g = json.load(open(os.path.join(BASE, adm, "gate_reading.json"), encoding="utf-8"))
    pop = g["seeds"]["20260917"]["G_LEARN_population"]["keys"]
    for seed in ("20260917", "20260918", "20260919"):
        ck = os.path.join(BASE, rec % seed, "checkpoints")
        rows = {}
        for phase in ("course_p00", "course_p10"):
            d = {}
            kinds = {}
            for r in json.load(open(os.path.join(ck, phase + "_scoring.json"), encoding="utf-8"))["rows"]:
                d.setdefault(r["query_id"], []).append(bool(r["correct"])); kinds[r["query_id"]] = r["kind"]
            rows[phase] = {q: all(v) for q, v in d.items()}
        start_right = [short(q) + ":" + kinds[q] for q in pop if rows["course_p00"][q]]
        final_wrong_in_floor = [short(q) + ":" + kinds[q] for q in pop if q in floor and not rows["course_p10"][q]]
        final_wrong_outside = [short(q) + ":" + kinds[q] for q in pop if q not in floor and not rows["course_p10"][q]]
        print(ver, seed, "start right", start_right, "| final wrong in floor", final_wrong_in_floor,
              "| final wrong outside floor", final_wrong_outside)
