"""R7 meeting: does the frozen per-seed verdict depend on the untrained start more than on the final answers?

Pure JSON. Re-implements evaluate_gates.py:283-318 (b > c, exact one-sided binomial p <= 1/100,
>= 2 improved kinds, >= 2 improved worlds) and first checks it reproduces the six frozen per-seed
readings. Then pairs every final answer set with every untrained start set. No model is loaded.
"""
import collections, json
from fractions import Fraction
from math import comb

T = (r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
     r"/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001")
SEEDS = ("20260917", "20260918", "20260919")
VERS = {"helm1": ("receipt_helm1_certified_%s", "admission_helm1_certified"),
        "helm2": ("receipt_%s", "admission_001")}
ALPHA = Fraction(1, 100)
anchor = json.load(open(T + "/trust_anchor_helm2_experimental_20208c92.json", encoding="utf-8"))
kind_of, world_of = anchor["population"]["kind_of"], anchor["population"]["world_of"]
label18 = json.load(open(T + "/admission_001/gate_reading.json", encoding="utf-8"))["label_key_population"]
assert sorted(label18) == sorted(anchor["population"]["question_ids"])


def outcomes(ver, seed, phase):
    d = json.load(open("%s/%s/collected/results/artifacts/course_%s_scoring.json" % (T, VERS[ver][0] % seed, phase),
                       encoding="utf-8"))
    q = collections.defaultdict(list)
    for r in d["rows"]:
        q[r["query_id"]].append(bool(r["correct"]))
    return {k: all(q[k]) for k in label18}


def test(before, after):
    b = sum(1 for k in label18 if not before[k] and after[k])
    c = sum(1 for k in label18 if before[k] and not after[k])
    n = b + c
    p = Fraction(1) if n == 0 else Fraction(sum(comb(n, i) for i in range(b, n + 1)), 2 ** n)
    imp = [k for k in label18 if not before[k] and after[k]]
    ok = b > c and p <= ALPHA and len({kind_of[k] for k in imp}) >= 2 and len({world_of[k] for k in imp}) >= 2
    return b, c, p, ok


runs = {(v, s): (outcomes(v, s, "p00"), outcomes(v, s, "p10")) for v in VERS for s in SEEDS}
print("== reproduce frozen per-seed readings")
for (v, s), (st, fi) in runs.items():
    frozen = json.load(open("%s/%s/gate_reading.json" % (T, VERS[v][1]), encoding="utf-8"))["seeds"][s]["G_LEARN_population"]
    b, c, p, ok = test(st, fi)
    print(v, s, "start", sum(st.values()), "final", sum(fi.values()), "b", b, "c", c, "p", p, "pass", ok,
          "| frozen b", frozen["wrong_to_right"], "c", frozen["right_to_wrong"], "pass", frozen["passed"],
          "| agree", (b, c, ok) == (frozen["wrong_to_right"], frozen["right_to_wrong"], frozen["passed"]))
print("== identical final answer sets?")
for s in SEEDS:
    f1, f2 = runs[("helm1", s)][1], runs[("helm2", s)][1]
    print(s, "helm1 final == helm2 final:", f1 == f2, "| differ on", [(k[12:20], kind_of[k]) for k in label18 if f1[k] != f2[k]])
print("== each final answer set tested against each of the six untrained starts")
for (vf, sf), (_, fi) in runs.items():
    res = []
    for (vs, ss), (st, _) in runs.items():
        b, c, p, ok = test(st, fi)
        res.append("%s/%s:%d/%d/%s" % (vs[-1], ss[-2:], b, c, "P" if ok else "F"))
    print("final %s/%s (%d right):" % (vf, sf, sum(fi.values())), "passes against", sum(r.endswith("P") for r in res), "of 6 starts |", " ".join(res))
print("== untrained start sizes and which questions")
for (v, s), (st, _) in runs.items():
    print(v, s, "start right", sum(st.values()), [(k[12:20], kind_of[k]) for k in label18 if st[k]])
