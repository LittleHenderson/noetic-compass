"""CAS-specificity via RELATIONAL structure: the involution test.

Flat 40-way CAS detection collapses to chance on leakage-controlled fixtures. But CAS's
real claim is RELATIONAL: the involution pairs ^2<->^3, ^5<->^6, ^8<->^9 are OPPOSITES.
Test on the Condition-3 20B activations whether CAS's SPECIFIC pairing of the 6 involved
operators is geometrically more ANTIPODAL than the other 14 ways to pair those 6 operators
(an exact 15-matching permutation test) -- and whether involution pairs are more separable.
A generic relabeling has no reason to make THESE pairs opposite. Pure numpy; no model/GPU.
"""
import numpy as np, re, itertools, json

P = r'D:/tksCAS-archive/condition3_mtc_capture_20260531/'
d = np.load(P + 'condition3_gptneox20b_activations_20260531.npz', allow_pickle=True)
F = d['features']                     # (1440, 44, 6144) float16
noetic = d['labels_noetic']
domain = d['labels_domain']

def op_of(s):
    m = re.search(r'(\d)', str(s));  return int(m.group(1)) if m else -1
ops = np.array([op_of(x) for x in noetic])
nL = F.shape[1]
INVOL = [(2, 3), (5, 6), (8, 9)]
INVOLVED = [2, 3, 5, 6, 8, 9]
print('op counts:', {i: int((ops == i).sum()) for i in range(10)}, 'layers:', nL, flush=True)


def perfect_matchings(items):
    if not items:
        yield []; return
    a = items[0]
    for i in range(1, len(items)):
        rest = items[1:i] + items[i + 1:]
        for m in perfect_matchings(rest):
            yield [(a, items[i])] + m

ALL_MATCHINGS = list(perfect_matchings(INVOLVED))   # 15 for 6 items
TRUE = [tuple(sorted(p)) for p in INVOL]


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def sep_acc(X, yi, yj, i, j, seed=0):
    """held-out balanced acc separating operator i vs j via diff-of-means direction."""
    Xi, Xj = X[ops == i], X[ops == j]
    rng = np.random.RandomState(seed)
    def split(A):
        idx = rng.permutation(len(A)); c = len(A) // 2; return A[idx[:c]], A[idx[c:]]
    Xi_tr, Xi_te = split(Xi); Xj_tr, Xj_te = split(Xj)
    dvec = Xi_tr.mean(0) - Xj_tr.mean(0); dvec /= (np.linalg.norm(dvec) + 1e-9)
    thr = (Xi_tr.mean(0) @ dvec + Xj_tr.mean(0) @ dvec) / 2
    acc_i = (Xi_te @ dvec > thr).mean(); acc_j = (Xj_te @ dvec < thr).mean()
    return float((acc_i + acc_j) / 2)


rows = []
for L in range(nL):
    X = F[:, L, :].astype(np.float32)
    g = X.mean(0)
    cent = {o: X[ops == o].mean(0) - g for o in INVOLVED}
    # antipodality: exact 15-matching test
    scores = []
    for match in ALL_MATCHINGS:
        m_norm = [tuple(sorted(p)) for p in match]
        val = np.mean([cos(cent[i], cent[j]) for i, j in match])   # lower (more negative) = more antipodal
        scores.append((val, m_norm))
    scores.sort(key=lambda s: s[0])                # most antipodal first
    ranks = {tuple(sorted(m)): r for r, (v, m) in enumerate(scores)}   # 0 = most antipodal
    true_rank = ranks[tuple(TRUE)]
    true_val = [v for v, m in scores if m == TRUE][0]
    # separability of the 3 involution pairs vs mean of all involved-op pairs
    inv_sep = np.mean([sep_acc(X, None, None, i, j) for i, j in INVOL])
    all_sep = np.mean([sep_acc(X, None, None, i, j) for i, j in itertools.combinations(INVOLVED, 2)])
    rows.append((L, true_rank, true_val, inv_sep, all_sep))

# best layer by antipodal rank of the true matching (lower rank = better)
best = min(rows, key=lambda r: (r[1], r[2]))
print("\n=== INVOLUTION ANTIPODALITY (exact 15-matching test; rank 0 = MOST antipodal of 15) ===")
print(" layer | true_rank/15 | true_meancos | inv_pair_sep | all_pair_sep")
for L, tr, tv, isep, asep in rows:
    star = " <--" if L == best[0] else ""
    print(f"  {L:3d}  |     {tr:2d}/14     |   {tv:+.4f}   |    {isep:.3f}    |   {asep:.3f}{star}")
L, tr, tv, isep, asep = best
print(f"\nBEST LAYER {L}: CAS involution matching ranks {tr}/14 in antipodality "
      f"(0 = most antipodal). p ~= {(tr+1)/15:.3f} (exact, 15 matchings).")
print(f"  involution-pair separability {isep:.3f} vs all-involved-pair {asep:.3f}")
# how often across layers is the true matching in the top-3 most antipodal?
top3 = sum(1 for r in rows if r[1] <= 2)
print(f"  true matching in top-3 antipodal on {top3}/{nL} layers")
json.dump([{"layer": L, "true_rank": tr, "true_meancos": tv, "inv_sep": isep, "all_sep": asep}
           for L, tr, tv, isep, asep in rows],
          open("cas_involution_result.json", "w"), indent=2)
print("wrote cas_involution_result.json")
