"""Independent re-measurement of auditor finding signal-1 (context ranking signal). Read-only."""
import json, pathlib, sys, itertools
from collections import Counter, defaultdict
from fractions import Fraction
HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import answers, checker, course, slots, worker_contract

R = HOME / "records/typed_matched_001"
frozen, _t, _ = worker_contract.load_material(HOME)
runs = sorted(d for d in R.iterdir() if (d / "collected/results/artifacts/final_predictions.json").is_file())
print("runs", [r.name for r in runs])
cache = {}
agg = defaultdict(Counter)
aucs = defaultdict(list)
aucs_pres = defaultdict(list)
cross = defaultdict(lambda: ([], []))
absent_pos = Counter()


def auc(pos, neg):
    return Fraction(sum((2 if p > n else 1 if p == n else 0) for p in pos for n in neg), 2 * len(pos) * len(neg))


for run in runs:
    art = run / "collected/results/artifacts"
    preds = json.loads((art / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    scoring = {r["record_id"]: r for r in json.loads((art / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    A = agg[run.name]
    for pr in preds:
        rid = pr["record_id"]
        if scoring[rid]["kind"] != "context":
            continue
        if rid not in cache:
            packet = course.model_packet(frozen, rid)
            assert packet["record"]["query"]["kind"] == "context"
            plan = slots.compile_slots(packet)
            tgt = checker.derive_target(packet["source"], packet["record"]["query"])
            truth = tgt["admissible_answers"][0]["value"]
            adm = {json.dumps(a["value"], sort_keys=True) for a in tgt["admissible_answers"]}
            ts = None
            for w in plan["aliases"]["worlds"]:
                if answers.declaration_ref(w["world_id"], "setting") == truth["setting_ref"]:
                    ts = w["alias"]
            cache[rid] = (packet, plan, truth, adm, ts, len(tgt["admissible_answers"]))
        packet, plan, truth, adm, ts, nadm = cache[rid]
        A["q"] += 1
        A[f"nadm={nadm}"] += 1
        ps = [s for s in plan["slots"] if s["field"] == "participant"]
        tset = set(truth["participants"])
        slotvals = [s["coordinates"][0] for s in ps]
        assert tset <= set(slotvals), (rid, tset, slotvals)
        assert len(set(slotvals)) == len(slotvals)
        sc = pr["scores"]
        for s in ps:
            assert set(sc[s["slot_id"]]) == {"PRESENT", "ABSENT"}
        m = {s["slot_id"]: sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"] for s in ps}
        lab = {s["slot_id"]: s["coordinates"][0] in tset for s in ps}
        n, k = len(ps), len(tset)
        A[f"n{n}k{k}"] += 1
        cp, cn = cross[run.name]
        cp += [m[s] for s in m if lab[s]]
        cn += [m[s] for s in m if not lab[s]]
        order = sorted(ps, key=lambda s: m[s["slot_id"]], reverse=True)
        sel = dict(pr["decisions"]["selected"])
        for i, s in enumerate(order):
            sel[s["slot_id"]] = "PRESENT" if i < k else "ABSENT"
        for s in plan["slots"]:
            if s["field"] == "setting_ref":
                sel[s["slot_id"]] = ts
        dec = {**pr["decisions"], "selected": sel, "correspondence_candidate_id": None}
        ok = json.dumps(slots.assemble_answer(packet, dec)["value"], sort_keys=True) in adm
        A["topk_exact_assembled"] += ok
        good = 0
        tot = 0
        for combo in itertools.combinations(ps, k):
            ids = {s["slot_id"] for s in combo}
            sel2 = dict(sel)
            for s in ps:
                sel2[s["slot_id"]] = "PRESENT" if s["slot_id"] in ids else "ABSENT"
            dec2 = {**pr["decisions"], "selected": sel2, "correspondence_candidate_id": None}
            good += json.dumps(slots.assemble_answer(packet, dec2)["value"], sort_keys=True) in adm
            tot += 1
        A["rand_exact_x"] += Fraction(good, tot)
        if n > k and k > 0:
            A["eval"] += 1
            pos = [m[s] for s in m if lab[s]]
            neg = [m[s] for s in m if not lab[s]]
            a = auc(pos, neg)
            aucs[run.name].append(a)
            A["auc_lt"] += a < Fraction(1, 2)
            pp = {s["slot_id"]: sc[s["slot_id"]]["PRESENT"] for s in ps}
            aucs_pres[run.name].append(auc([pp[s] for s in pp if lab[s]], [pp[s] for s in pp if not lab[s]]))
            hits = sum(lab[s["slot_id"]] for s in order[:k])
            A["p_hits"] += hits
            A["p_den"] += k
            A["exact_eval"] += hits == k
            A["ties_boundary"] += m[order[k - 1]["slot_id"]] == m[order[k]["slot_id"]]
            for i, s in enumerate(ps):
                if not lab[s["slot_id"]]:
                    absent_pos[(n, i)] += 1
            for i, s in enumerate(order):
                if not lab[s["slot_id"]]:
                    A[f"absent_rank{i}"] += 1
        else:
            A["auto"] += 1
            A["auto_exact"] += ok

P = Counter()
allA, allPr, gp, gn = [], [], [], []
for r in runs:
    A = agg[r.name]
    L = aucs[r.name]
    print(f"\n{r.name}: " + str({k: (float(v) if isinstance(v, Fraction) else v) for k, v in sorted(A.items())}))
    print(f"  mean AUC {float(sum(L) / len(L)):.6f}  PRESENT-only AUC {float(sum(aucs_pres[r.name]) / len(L)):.6f}  cross AUC {float(auc(*cross[r.name])):.6f}")
    print(f"  topk exact assembled {A['topk_exact_assembled']}/{A['q']} = {100 * A['topk_exact_assembled'] / A['q']:.4f}%  random-subset expectation {float(A['rand_exact_x'])}/{A['q']} = {100 * float(A['rand_exact_x']) / A['q']:.4f}%")
    for kk, v in A.items():
        P[kk] += v
    allA += L
    allPr += aucs_pres[r.name]
    gp += cross[r.name][0]
    gn += cross[r.name][1]
print("\nPOOLED", {k: (float(v) if isinstance(v, Fraction) else v) for k, v in sorted(P.items())})
print(f"mean within-q AUC {float(sum(allA) / len(allA)):.6f} over {len(allA)}; PRESENT-only {float(sum(allPr) / len(allPr)):.6f}")
print(f"cross AUC pooled {float(auc(gp, gn)):.6f}")
print(f"precision@k {P['p_hits']}/{P['p_den']} = {100 * P['p_hits'] / P['p_den']:.4f}%")
print(f"exact top-k (4-slot) {P['exact_eval']}/{P['eval']} = {100 * P['exact_eval'] / P['eval']:.4f}%")
print(f"topk exact assembled {P['topk_exact_assembled']}/{P['q']} = {100 * P['topk_exact_assembled'] / P['q']:.4f}%")
print(f"random-subset expectation {float(P['rand_exact_x'])}/{P['q']} = {100 * float(P['rand_exact_x']) / P['q']:.4f}%")
print("absent slot position counts", dict(sorted(absent_pos.items())))
