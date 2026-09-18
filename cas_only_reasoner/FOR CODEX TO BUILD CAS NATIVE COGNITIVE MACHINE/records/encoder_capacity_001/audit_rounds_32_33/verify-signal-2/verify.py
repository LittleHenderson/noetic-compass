"""verify-signal-2: independent re-measure of edge_account ranking signal. Read-only."""
from __future__ import annotations
import json, pathlib, sys, math
from collections import Counter, defaultdict
from fractions import Fraction

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa

R = HOME / "records/typed_matched_001"


def pair_auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    num = Fraction(0)
    for p in pos:
        for q in neg:
            num += 1 if p > q else Fraction(1, 2) if p == q else 0
    return num / (len(pos) * len(neg))


def xauc(pos, neg):
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rs = 0.0
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        rs += (i + 1 + j) / 2 * sum(x[1] for x in allv[i:j])
        i = j
    return (rs - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def f4(x):
    return f"{float(x) * 100:.4f}%"


def main():
    frozen, _, _ = worker_contract.load_material(HOME)
    runs = sorted(d for d in R.iterdir() if d.is_dir() and (d / "collected/results/artifacts/final_predictions.json").is_file())
    print("runs", [r.name for r in runs], flush=True)
    cache = {}
    agg = defaultdict(Counter)
    aucs, paucs, offd = defaultdict(list), defaultdict(list), defaultdict(list)
    xq = defaultdict(lambda: ([], []))
    exact_rand, exact_rand_od = defaultdict(Fraction), defaultdict(Fraction)
    anomalies = Counter()
    for run in runs:
        art = run / "collected/results/artifacts"
        preds = json.loads((art / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {r["record_id"]: r for r in json.loads((art / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
        for pr in preds:
            rid = pr["record_id"]
            if scoring[rid]["kind"] != "edge_account":
                continue
            if rid not in cache:
                pk = course.model_packet(frozen, rid)
                q = pk["record"]["query"]
                assert q["kind"] == "edge_account"
                plan = slots.compile_slots(pk)
                tgt = checker.derive_target(pk["source"], q)
                if len(tgt["admissible_answers"]) != 1:
                    anomalies["multi_admissible"] += 1
                truth = {(e["source"], e["target"]) for e in tgt["admissible_answers"][0]["value"]["edges"]}
                focus = next(w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
                es = [s for s in plan["slots"] if s["field"] == "edge"]
                assert len(es) == len(plan["slots"])
                lab = [tuple(s["coordinates"]) in truth for s in es]
                assert sum(lab) == len(truth), "truth pair not in slot set"
                cache[rid] = (es, lab, len(focus["contains"]), any(a == b for a, b in truth))
            es, lab, kdecl, selfloop = cache[rid]
            if selfloop:
                anomalies["true_selfloop"] += 1
            sc = pr["scores"]
            if set(sc) != {s["slot_id"] for s in es}:
                anomalies["slot_key_mismatch"] += 1
            m = [sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"] for s in es]
            n, k = len(m), sum(lab)
            if kdecl != k:
                anomalies["k_decl_ne_truth"] += 1
            A = agg[run.name]
            A["q"] += 1
            A[f"n{n}k{k}"] += 1
            A["bits"] += n
            dec = pr["decisions"]["selected"]
            indep = ["PRESENT" if sc[s["slot_id"]]["PRESENT"] > sc[s["slot_id"]]["ABSENT"] else "ABSENT" for s in es]
            if [dec[s["slot_id"]] for s in es] != indep:
                anomalies["recorded_decision_ne_argmax"] += 1
            A["thr"] += sum((mm > 0) == l for mm, l in zip(m, lab))
            A["absent"] += sum(not l for l in lab)
            a = pair_auc(m, lab)
            aucs[run.name].append(a)
            if a < Fraction(1, 2):
                A["auc_lt"] += 1
            paucs[run.name].append(pair_auc([-i for i in range(n)], lab))
            od = [(mm, l) for mm, l, s in zip(m, lab, es) if s["coordinates"][0] != s["coordinates"][1]]
            offd[run.name].append(pair_auc([x[0] for x in od], [x[1] for x in od]))
            order = sorted(range(n), key=lambda i: m[i], reverse=True)
            top = set(order[:k])
            if m[order[k - 1]] == m[order[k]]:
                A["ties"] += 1
            h = sum(lab[i] for i in top)
            A["pk"] += h
            A["pkden"] += k
            A["exact"] += h == k
            A["bits_topk"] += sum((i in top) == lab[i] for i in range(n))
            A["diag_in_top"] += sum(1 for i in top if es[i]["coordinates"][0] == es[i]["coordinates"][1])
            exact_rand[run.name] += Fraction(1, math.comb(n, k))
            nod = sum(1 for s in es if s["coordinates"][0] != s["coordinates"][1])
            exact_rand_od[run.name] += Fraction(1, math.comb(nod, k))
            xq[run.name][0].extend(mm for mm, l in zip(m, lab) if l)
            xq[run.name][1].extend(mm for mm, l in zip(m, lab) if not l)
    print("anomalies", dict(anomalies))
    P = Counter()
    allA, allP, allO, gp, gn = [], [], [], [], []
    er = Fraction(0)
    ero = Fraction(0)
    for r in sorted(agg):
        A = agg[r]
        P.update(A)
        allA += aucs[r]; allP += paucs[r]; allO += offd[r]
        gp += xq[r][0]; gn += xq[r][1]
        er += exact_rand[r]; ero += exact_rand_od[r]
        shapes = {k2: v for k2, v in A.items() if k2[0] == "n" and k2[1].isdigit()}
        print(f"{r}: q={A['q']} shapes={shapes} meanAUC={float(sum(aucs[r]) / len(aucs[r])):.6f} "
              f"posAUC={float(sum(paucs[r]) / len(paucs[r])):.6f} offdiagAUC={float(sum(offd[r]) / len(offd[r])):.6f} "
              f"AUC<0.5 {A['auc_lt']}/{A['q']} P@k {A['pk']}/{A['pkden']}={f4(Fraction(A['pk'], A['pkden']))} "
              f"exact {A['exact']}/{A['q']} randExact={f4(exact_rand[r] / A['q'])} "
              f"thr {A['thr']}/{A['bits']}={f4(Fraction(A['thr'], A['bits']))} "
              f"topkbits {A['bits_topk']}/{A['bits']}={f4(Fraction(A['bits_topk'], A['bits']))} "
              f"xAUC={xauc(*xq[r]):.6f} ties={A['ties']} diagInTop={A['diag_in_top']}")
    q = P["q"]
    print("POOLED q", q)
    print(f"meanAUC={float(sum(allA) / len(allA)):.6f} posAUC={float(sum(allP) / len(allP)):.6f} "
          f"offdiagAUC={float(sum(allO) / len(allO)):.6f} AUC<0.5 {P['auc_lt']}/{q}")
    print(f"P@k {P['pk']}/{P['pkden']}={f4(Fraction(P['pk'], P['pkden']))}")
    print(f"exact {P['exact']}/{q} randExact={f4(er / q)} (expected count {float(er):.4f}); "
          f"off-diag random exact={f4(ero / q)} (count {float(ero):.4f})")
    print(f"thr {P['thr']}/{P['bits']}={f4(Fraction(P['thr'], P['bits']))} "
          f"topkbits {P['bits_topk']}/{P['bits']}={f4(Fraction(P['bits_topk'], P['bits']))} "
          f"always-absent {P['absent']}/{P['bits']}={f4(Fraction(P['absent'], P['bits']))} "
          f"xAUC={xauc(gp, gn):.6f} diagInTop={P['diag_in_top']}")
    tot = Fraction(0)
    den = 0
    for (es, lab, kd, _) in cache.values():
        n, k = len(lab), sum(lab)
        tot += Fraction(k * k, n)
        den += k
    print(f"unique questions {len(cache)}; random P@k = {f4(tot / den)}")
    ph = pe = pd = 0
    for (es, lab, kd, _) in cache.values():
        k = sum(lab)
        h = sum(lab[:k])
        ph += h; pd += k; pe += h == k
    print(f"position ranker (unique qs) P@k {ph}/{pd}={f4(Fraction(ph, pd))} exact {pe}/{len(cache)}")
    idx = Counter()
    diag_true = 0
    for (es, lab, kd, _) in cache.values():
        for i, l in enumerate(lab):
            if l:
                idx[(len(lab), i)] += 1
    print("true-edge positions (n,index):count", sorted(idx.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
