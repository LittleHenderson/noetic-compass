"""CAS-specificity via precedence: does the model's domain geometry respect P>C>E>O?

CAS claims a total order on domains P(Principled) > C(Cognitive) > E(Evaluative) >
O(Operational), with descent P->C->E->O. Geometric prediction: nearby-in-order domains
should be nearby-in-space (P-C close, P-O far), and the 4 domain centroids should line up
monotonically on a descent axis. Test on the real 20B captures whether CAS's specific
order fits better than the other orderings (exact test over the 12 distinct orders).
Pure numpy on captured activations; no model/GPU.
"""
import numpy as np, itertools, json

P = r'D:/tksCAS-archive/condition3_mtc_capture_20260531/'
d = np.load(P + 'condition3_gptneox20b_activations_20260531.npz', allow_pickle=True)
F = d['features']
dom = np.array([str(x) for x in d['labels_domain']])
DOMS = ['P', 'C', 'E', 'O']
CAS = ['P', 'C', 'E', 'O']
nL = F.shape[1]
print('domain counts:', {dm: int((dom == dm).sum()) for dm in DOMS}, 'layers:', nL, flush=True)


def sep4(X):
    """4-way domain separability (held-out balanced acc, nearest-centroid)."""
    rng = np.random.RandomState(0)
    idx = rng.permutation(len(X)); c = len(X) // 2
    tr, te = idx[:c], idx[c:]
    cent = {dm: X[tr][dom[tr] == dm].mean(0) for dm in DOMS}
    C = np.stack([cent[dm] for dm in DOMS])
    pred = [DOMS[np.argmin(((C - X[i]) ** 2).sum(1))] for i in te]
    accs = [np.mean([pred[k] == dom[te][k] for k in range(len(te)) if dom[te][k] == dm]) for dm in DOMS]
    return float(np.mean(accs))


rows = []
distinct_orders = []
seen = set()
for perm in itertools.permutations(DOMS):
    key = min(perm, tuple(reversed(perm)))
    if key not in seen:
        seen.add(key); distinct_orders.append(perm)   # 12 distinct up to reversal

for L in range(nL):
    X = F[:, L, :].astype(np.float32)
    cent = {dm: X[dom == dm].mean(0) for dm in DOMS}
    pairs = list(itertools.combinations(DOMS, 2))
    dists = {p: float(np.linalg.norm(cent[p[0]] - cent[p[1]])) for p in pairs}

    def fit(order):
        rank = {dm: i for i, dm in enumerate(order)}
        gaps = [abs(rank[a] - rank[b]) for a, b in pairs]
        dd = [dists[p] for p in pairs]
        if np.std(dd) < 1e-9 or np.std(gaps) < 1e-9:
            return 0.0
        return float(np.corrcoef(dd, gaps)[0, 1])

    cas_fit = fit(CAS)
    fits = sorted(((fit(o), o) for o in distinct_orders), reverse=True)
    cas_key = min(tuple(CAS), tuple(reversed(CAS)))
    cas_rank = [i for i, (f, o) in enumerate(fits) if min(o, tuple(reversed(o))) == cas_key][0]
    # monotonic projection on the P->O axis
    axis = cent['O'] - cent['P']; axis = axis / (np.linalg.norm(axis) + 1e-9)
    proj = {dm: float(cent[dm] @ axis) for dm in DOMS}
    order_proj = tuple(sorted(DOMS, key=lambda dm: proj[dm]))
    monotone = order_proj in (tuple(CAS), tuple(reversed(CAS)))
    rows.append((L, cas_fit, cas_rank, monotone, order_proj, sep4(X)))

best = max(rows, key=lambda r: r[1])   # best adjacency-fit layer
print("\n=== DOMAIN PRECEDENCE (P>C>E>O) — real 20B geometry ===")
print(" layer | CAS-order fit | CAS rank/12 | monotone P..O | proj order | 4-way domain sep")
for L, cf, cr, mono, op, sep in rows:
    star = " <--" if L == best[0] else ""
    print(f"  {L:3d}  |    {cf:+.3f}    |    {cr+1:2d}/12    |    {str(mono):5s}    | {''.join(op)} | {sep:.3f}{star}")
L, cf, cr, mono, op, sep = best
print(f"\nBEST-FIT LAYER {L}: CAS order fit r={cf:+.3f}, ranks {cr+1}/12 among distinct orders "
      f"(1 = best fit). Monotone on P->O axis: {mono} (proj order {''.join(op)}). domain sep {sep:.3f}")
top3 = sum(1 for r in rows if r[2] <= 2)
mono_layers = sum(1 for r in rows if r[3])
print(f"  CAS order in top-3 fits on {top3}/{nL} layers; monotone P..O on {mono_layers}/{nL} layers")
json.dump([{"layer": L, "cas_fit": cf, "cas_rank": cr, "monotone": mono,
            "proj_order": ''.join(op), "domain_sep4": sep} for L, cf, cr, mono, op, sep in rows],
          open("cas_precedence_result.json", "w"), indent=2)
print("wrote cas_precedence_result.json")
