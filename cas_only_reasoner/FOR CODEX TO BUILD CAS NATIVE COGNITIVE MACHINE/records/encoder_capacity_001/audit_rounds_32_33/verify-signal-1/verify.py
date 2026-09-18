"""Independent re-measure of auditor finding signal-2 (parts ranking signal). Read-only."""
import json, pathlib, sys, math, itertools
from fractions import Fraction
from collections import Counter, defaultdict

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa

def mw(pos, neg):
    s = Fraction(0)
    for p in pos:
        for n in neg:
            s += 1 if p > n else Fraction(1, 2) if p == n else 0
    return s / (len(pos) * len(neg))

def pc(a, b): return f"{a}/{b} = {100*a/b:.4f}%"

frozen, _t, _ = worker_contract.load_material(HOME)
R = HOME / "records/typed_matched_001"
receipts = sorted(d for d in R.iterdir() if d.is_dir() and (d/"collected/results/artifacts/final_predictions.json").is_file())
print("runs", [r.name for r in receipts])
cache = {}
glob = defaultdict(list)
out = {}
allpos, allneg = [], []
for rc in receipts:
    art = rc / "collected/results/artifacts"
    preds = json.loads((art/"final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    scor = {r["record_id"]: r for r in json.loads((art/"final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    S = Counter(); aucs = []; posaucs = []; revaucs = []
    for pr in preds:
        rid = pr["record_id"]
        if scor[rid]["kind"] != "parts": continue
        if rid not in cache:
            pk = course.model_packet(frozen, rid)
            q = pk["record"]["query"]
            plan = slots.compile_slots(pk)
            tgt = checker.derive_target(pk["source"], q)
            adm = [a["value"] for a in tgt["admissible_answers"]]
            truthset = set(adm[0]["nodes"])
            focus = next(w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
            whole = q["arguments"]["whole"]
            kdecl = sum(1 for e in focus["contains"] if e["source"] == whole)
            ns = [s for s in plan["slots"] if s["field"] == "node"]
            assert len(ns) == len(plan["slots"])
            cache[rid] = dict(pk=pk, adm=adm, truth=truthset, k=kdecl, ns=ns, whole=whole,
                              whole_in=any(s["coordinates"][0] == whole for s in ns))
        c = cache[rid]
        sc = pr["scores"]; ns = c["ns"]
        m = [sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"] for s in ns]
        t = [s["coordinates"][0] in c["truth"] for s in ns]
        n, k = len(ns), c["k"]
        S["q"] += 1; S["nadm>1"] += len(c["adm"]) > 1
        S["k_mismatch"] += (k != sum(t)); S["whole_in_slots"] += c["whole_in"]
        S["whole_true"] += any(tt and s["coordinates"][0] == c["whole"] for s, tt in zip(ns, t))
        S[f"n{n}k{k}"] += 1
        # as-is argmax (ties -> 'ABSENT' first in symbols? use record rule: max over symbols order)
        sel = [max(s["symbols"], key=lambda y: sc[s["slot_id"]][y]) == "PRESENT" for s in ns]
        S["asis_exact"] += sel == t
        S["bits"] += n; S["asis_bits"] += sum(a == b for a, b in zip(sel, t)); S["true_bits"] += sum(t)
        # top-k by margin (stable, plan order for ties)
        order = sorted(range(n), key=lambda i: m[i], reverse=True)
        top = set(order[:k])
        S["ties_at_boundary"] += (0 < k < n and m[order[k-1]] == m[order[k]])
        hits = sum(1 for i in top if t[i])
        S["pk_hits"] += hits; S["pk_den"] += k
        S["topk_exact"] += (hits == k)
        # verify via project assembly
        dec = {**pr["decisions"], "selected": {s["slot_id"]: ("PRESENT" if i in top else "ABSENT") for i, s in enumerate(ns)}}
        v = slots.assemble_answer(c["pk"], dec)["value"]
        S["topk_exact_assembled"] += any(json.dumps(v, sort_keys=True) == json.dumps(a, sort_keys=True) for a in c["adm"])
        S["rand_exact_num"] = S.get("rand_exact_num", 0)
        glob[rc.name].append((Fraction(1, math.comb(n, k)), Fraction(k, n) * k, n, k))
        # random excluding the whole (truth-free heuristic)
        nn = n - (1 if c["whole_in"] else 0)
        glob[rc.name + "#nowhole"].append(Fraction(1, math.comb(nn, k)))
        # position rankings
        if 0 < k < n:
            pos = [m[i] for i in range(n) if t[i]]; neg = [m[i] for i in range(n) if not t[i]]
            a = mw(pos, neg); aucs.append(a)
            S["auc1"] += a == 1; S["auclt"] += a < Fraction(1, 2)
            posaucs.append(mw([-i for i in range(n) if t[i]], [-i for i in range(n) if not t[i]]))
            allpos += pos; allneg += neg
            # reversed plan order top-k exact
            S["revpos_exact"] += set(range(n - k, n)) == {i for i in range(n) if t[i]}
            S["fwdpos_exact"] += set(range(k)) == {i for i in range(n) if t[i]}
        else:
            S["skipped"] += 1
    rs = glob[rc.name]
    out[rc.name] = (S, aucs, posaucs, sum(x[0] for x in rs), sum(x[1] for x in rs), sum(glob[rc.name + "#nowhole"]))
    print(f"\n{rc.name}: {dict(S)}")
    print("  meanAUC", float(sum(aucs)/len(aucs)), " posAUC", float(sum(posaucs)/len(posaucs)))
    print("  topk exact", pc(S["topk_exact"], S["q"]), " asis exact", pc(S["asis_exact"], S["q"]),
          " asis bits", pc(S["asis_bits"], S["bits"]), " P@k", pc(S["pk_hits"], S["pk_den"]))
    print("  E[random exact]", float(out[rc.name][3]/S["q"]), " E[random exact excl whole]", float(out[rc.name][5]/S["q"]))

T = Counter(); A = []; P = []; re = Fraction(0); rp = Fraction(0); rnw = Fraction(0)
for name, (S, aucs, posaucs, r1, r2, r3) in out.items():
    T.update(S); A += aucs; P += posaucs; re += r1; rp += r2; rnw += r3
print("\nPOOLED", dict(T))
print("mean within-q AUC", float(sum(A)/len(A)), "over", len(A))
print("pos AUC", float(sum(P)/len(P)), " reversed-pos AUC", float(1 - sum(P)/len(P)))
print("topk exact", pc(T["topk_exact"], T["q"]), "assembled", pc(T["topk_exact_assembled"], T["q"]))
print("asis exact", pc(T["asis_exact"], T["q"]))
print("P@k", pc(T["pk_hits"], T["pk_den"]), " random k/n expectation", float(rp / T["pk_den"]) * 100)
print("E random exact", float(re / T["q"]) * 100, " E random exact excluding whole", float(rnw / T["q"]) * 100)
print("reversed-plan-order exact", pc(T["revpos_exact"], T["q"]), " forward", pc(T["fwdpos_exact"], T["q"]))
# cross-question AUC via rank
v = sorted([(x, 1) for x in allpos] + [(x, 0) for x in allneg])
rsum = 0.0; i = 0
while i < len(v):
    j = i
    while j < len(v) and v[j][0] == v[i][0]: j += 1
    rsum += (i + 1 + j) / 2 * sum(1 for z in v[i:j] if z[1]); i = j
Pn, Nn = len(allpos), len(allneg)
print("cross-question AUC", (rsum - Pn*(Pn+1)/2) / (Pn*Nn))
