"""Round-33 audit, label `signal`. Read-only. Pure stdlib + project pure modules.
Within-question ranking signal of recorded PRESENT-ABSENT margins, per kind, six runs."""
from __future__ import annotations
import json, pathlib, sys, math
from collections import Counter, defaultdict

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
FIELD = {"edge_account": "edge", "parts": "node", "context": "participant"}


def truth_present(kind, slot, value):
    if kind == "edge_account":
        present = {(r["source"], r["target"]) for r in value["edges"]}
        return (slot["coordinates"][0], slot["coordinates"][1]) in present
    if kind == "parts":
        return slot["coordinates"][0] in set(value["nodes"])
    return slot["coordinates"][0] in set(value["participants"])


def auc(pos, neg):
    s = 0.0
    for p in pos:
        for n in neg:
            s += 1.0 if p > n else 0.5 if p == n else 0.0
    return s / (len(pos) * len(neg))


def auc_fast(pos, neg):
    # rank-based, ties 0.5, for large pooled sets
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum = 0.0
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0
        rank_sum += avg * sum(1 for x in allv[i:j] if x[1] == 1)
        i = j
    P, N = len(pos), len(neg)
    return (rank_sum - P * (P + 1) / 2.0) / (P * N)


def pct(x):
    return f"{100 * x:.4f}%"


def main():
    frozen, _t, _ = worker_contract.load_material(HOME)
    receipts = sorted(d for d in RECEIPTS.iterdir()
                      if d.is_dir() and (d / "collected/results/artifacts/final_predictions.json").is_file())
    print("runs:", [r.name for r in receipts], flush=True)
    cache = {}
    stats = defaultdict(lambda: defaultdict(Counter))
    lists = defaultdict(lambda: defaultdict(list))
    glob = defaultdict(lambda: defaultdict(lambda: ([], [])))
    for receipt in receipts:
        art = receipt / "collected/results/artifacts"
        preds = json.loads((art / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        for pr in preds:
            rid = pr["record_id"]
            if rid not in cache:
                packet = course.model_packet(frozen, rid)
                kind = packet["record"]["query"]["kind"]
                if kind not in FIELD:
                    cache[rid] = None
                    continue
                plan = slots.compile_slots(packet)
                value = checker.derive_target(packet["source"], packet["record"]["query"])["admissible_answers"][0]["value"]
                fs = [s for s in plan["slots"] if s["field"] == FIELD[kind]]
                cache[rid] = (kind, [(s["slot_id"], truth_present(kind, s, value)) for s in fs])
            if cache[rid] is None:
                continue
            kind, fs = cache[rid]
            sc = pr["scores"]
            m = [(sc[sid]["PRESENT"] - sc[sid]["ABSENT"], t, i) for i, (sid, t) in enumerate(fs)]
            st = stats[kind][receipt.name]
            n = len(m)
            k = sum(1 for x in m if x[1])
            st["q"] += 1
            st[f"shape n={n} k={k}"] += 1
            st["bits"] += n
            st["truebits"] += k
            gp, gn = glob[kind][receipt.name]
            gp.extend(x[0] for x in m if x[1])
            gn.extend(x[0] for x in m if not x[1])
            st["thr_hits"] += sum(1 for x in m if (x[0] > 0) == x[1])
            if k == 0 or k == n:
                st["skipped"] += 1
                continue
            pos = [x[0] for x in m if x[1]]
            neg = [x[0] for x in m if not x[1]]
            a = auc(pos, neg)
            lists[kind][run_key := receipt.name].append(a)
            ppos = [-x[2] for x in m if x[1]]
            pneg = [-x[2] for x in m if not x[1]]
            lists[kind + "#position"][run_key].append(auc(ppos, pneg))
            ranked = sorted(m, key=lambda x: x[0], reverse=True)
            hits = sum(1 for x in ranked[:k] if x[1])
            st["p_at_k_hits"] += hits
            st["p_at_k_den"] += k
            st["rand_hits_x1e9"] += round(1e9 * k * k / n)
            st["exact_topk"] += 1 if hits == k else 0
            st["exact_rand_x1e12"] += round(1e12 / math.comb(n, k))
            st["bits_topk"] += sum(1 for idx, x in enumerate(ranked) if (idx < k) == x[1])
            st["bits_eval"] += n
            st["boundary_ties"] += 1 if (k < n and ranked[k - 1][0] == ranked[k][0]) else 0
            st["auc_eq1"] += 1 if a == 1.0 else 0
            st["auc_le_half"] += 1 if a <= 0.5 else 0
            st["auc_lt_half"] += 1 if a < 0.5 else 0
            st["evaluated"] += 1

    for kind in FIELD:
        print("\n" + "=" * 110)
        print(f"KIND {kind}  field {FIELD[kind]}   (measured by this audit)")
        print("=" * 110)
        pooled = Counter()
        allA, allP, gpA, gnA = [], [], [], []
        for run in sorted(stats[kind]):
            st = stats[kind][run]
            A = lists[kind][run]
            P = lists[kind + "#position"][run]
            allA += A
            allP += P
            gp, gn = glob[kind][run]
            gpA += gp
            gnA += gn
            for key, v in st.items():
                pooled[key] += v
            shapes = ", ".join(f"{k2[6:]}:{v}" for k2, v in sorted(st.items()) if k2.startswith("shape"))
            print(f"{run}: q={st['q']} evaluated={st['evaluated']} skipped(all-true/all-false)={st['skipped']}  shapes [{shapes}]")
            print(f"    mean within-question AUC = {sum(A)/len(A):.6f}  (AUC=1 in {st['auc_eq1']}/{st['evaluated']}, "
                  f"AUC<0.5 in {st['auc_lt_half']}/{st['evaluated']}, AUC<=0.5 in {st['auc_le_half']}/{st['evaluated']})"
                  f"   slot-position baseline AUC = {sum(P)/len(P):.6f}")
            print(f"    precision@k = {st['p_at_k_hits']}/{st['p_at_k_den']} = {pct(st['p_at_k_hits']/st['p_at_k_den'])}"
                  f"   random expectation k/n = {pct(st['rand_hits_x1e9']/1e9/st['p_at_k_den'])}")
            print(f"    exact set under top-k(true k) = {st['exact_topk']}/{st['evaluated']} = {pct(st['exact_topk']/st['evaluated'])}"
                  f"   random-ranking expectation = {pct(st['exact_rand_x1e12']/1e12/st['evaluated'])}"
                  f"   boundary ties = {st['boundary_ties']}")
            print(f"    per-bit threshold(margin>0) = {st['thr_hits']}/{st['bits']} = {pct(st['thr_hits']/st['bits'])}"
                  f"   per-bit under top-k (evaluated qs) = {st['bits_topk']}/{st['bits_eval']} = {pct(st['bits_topk']/st['bits_eval'])}"
                  f"   cross-question AUC = {auc_fast(gp, gn):.6f}")
        ev = pooled["evaluated"]
        print(f"POOLED six runs: q={pooled['q']} evaluated={ev} skipped={pooled['skipped']}")
        print(f"    mean within-question AUC = {sum(allA)/len(allA):.6f}  (AUC<0.5 in {pooled['auc_lt_half']}/{ev})"
              f"   slot-position baseline AUC = {sum(allP)/len(allP):.6f}")
        print(f"    precision@k = {pooled['p_at_k_hits']}/{pooled['p_at_k_den']} = {pct(pooled['p_at_k_hits']/pooled['p_at_k_den'])}"
              f"   random = {pct(pooled['rand_hits_x1e9']/1e9/pooled['p_at_k_den'])}")
        print(f"    exact under top-k = {pooled['exact_topk']}/{ev} = {pct(pooled['exact_topk']/ev)}"
              f"   random-ranking expectation = {pct(pooled['exact_rand_x1e12']/1e12/ev)}")
        print(f"    per-bit under top-k = {pooled['bits_topk']}/{pooled['bits_eval']} = {pct(pooled['bits_topk']/pooled['bits_eval'])}")
        print(f"    cross-question AUC (threshold-free, pooled) = {auc_fast(gpA, gnA):.6f}")
        print(f"    per-bit threshold(margin>0) = {pooled['thr_hits']}/{pooled['bits']} = {pct(pooled['thr_hits']/pooled['bits'])}"
              f"   true-PRESENT rate = {pooled['truebits']}/{pooled['bits']} = {pct(pooled['truebits']/pooled['bits'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
