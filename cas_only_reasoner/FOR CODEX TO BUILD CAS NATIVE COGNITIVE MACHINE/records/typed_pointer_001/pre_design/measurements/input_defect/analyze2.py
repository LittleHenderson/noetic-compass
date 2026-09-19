"""Stage 2 (defect2): measurements (a)-(e) on build2.pkl. Pure Python, standard library only. $0.

Run: python -B analyze2.py > analyze2_out.txt
"""
import sys
sys.dont_write_bytecode = True
import pickle, math, statistics, random, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = pickle.loads((HERE / "build2.pkl").read_bytes())
P, S, RV = d["packets"], d["slots"], d["rowvec"]
D = 64
KINDS4 = ("parts", "context", "role_set", "edge_account")
QTAGS = {"RECORD", "QUERY", "SUPPORT"}
CAT = {"FORMAT": "shared_context", "ALIASES": "shared_context", "POLICY": "shared_context", "WORLD": "shared_context",
       "SOURCE": "focus_source", "BINDINGS": "packet_digests", "RECORD": "question", "QUERY": "question",
       "SUPPORT": "question", "START": "markers", "END": "markers"}


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def nrm(a):
    return math.sqrt(dot(a, a))


def cos(a, b):
    return dot(a, b) / (nrm(a) * nrm(b))


def unit(v):
    n = nrm(v)
    return [x / n for x in v]


def mmm(xs):
    xs = sorted(xs)
    return "n=%d min=%.6f median=%.6f max=%.6f" % (len(xs), xs[0], statistics.median(xs), xs[-1])


def pct(x):
    return "%.4f%%" % (100.0 * x)


print("GATE", d["gate"])
rids = sorted(P)
split = {r: P[r]["split"] for r in rids}
print("records", Counter(split.values()))
print()

# ---------------- (a) worlds per packet; row composition ----------------
print("=" * 100)
print("(a) WORLDS PER PACKET AND FRAME-ROW COMPOSITION (all 564 packets)")
print("n_worlds per packet:", Counter(P[r]["n_worlds"] for r in rids))
print("WORLD rows per packet:", Counter(sum(1 for x in P[r]["rows"] if x["tag"] == "WORLD") for r in rids))
print("total rows per packet (incl START/END):", sorted(Counter(len(P[r]["rows"]) for r in rids).items()))
tagcount = Counter()
distinct = defaultdict(set)
for r in rids:
    for x in P[r]["rows"]:
        tagcount[x["tag"]] += 1
        distinct[x["tag"]].add(x["key"])
print("tag: rows over course | distinct row byte-keys (ordinal,scope,token_ids) across 564 packets")
for t in ("START", "FORMAT", "BINDINGS", "ALIASES", "POLICY", "SOURCE", "WORLD", "RECORD", "QUERY", "SUPPORT", "END"):
    print("  %-8s %6d | %6d" % (t, tagcount[t], len(distinct[t])))
# is the shared-context block identical in every packet?
shared_sig = Counter(tuple(x["key"] for x in P[r]["rows"] if CAT[x["tag"]] == "shared_context") for r in rids)
print("distinct shared-context blocks (FORMAT+ALIASES+POLICY*+WORLD*) across packets:", len(shared_sig))
focus_src = defaultdict(set)
for r in rids:
    for x in P[r]["rows"]:
        if x["tag"] == "SOURCE":
            focus_src[P[r]["focus"]].add(x["key"])
print("SOURCE row: distinct keys", len(distinct["SOURCE"]), "focus worlds", len(focus_src),
      "max distinct SOURCE keys per focus world", max(len(v) for v in focus_src.values()))
print("focus == source_world_id for all packets:", all(P[r]["focus"] == P[r]["source_world"] for r in rids))
qshare_rows, qshare_tok = [], []
cat_rows = defaultdict(list)
for r in rids:
    rows = P[r]["rows"]
    nq = sum(1 for x in rows if x["tag"] in QTAGS)
    qshare_rows.append(nq / len(rows))
    qshare_tok.append(sum(x["count"] for x in rows if x["tag"] in QTAGS) / sum(x["count"] for x in rows))
    for cname in ("shared_context", "focus_source", "packet_digests", "question", "markers"):
        cat_rows[cname].append(sum(1 for x in rows if CAT[x["tag"]] == cname))
print("question-specific rows (RECORD+QUERY+SUPPORT) per packet:", sorted(Counter(cat_rows["question"]).items()))
print("question-specific ROW share:", mmm(qshare_rows))
print("question-specific TOKEN share:", mmm(qshare_tok))
for cname in ("shared_context", "focus_source", "packet_digests", "markers"):
    print("  rows in %-15s per packet: %s" % (cname, sorted(Counter(cat_rows[cname]).items())))
print()

# ---------------- (b) packet-vector cosines ----------------
print("=" * 100)
print("(b) COSINE BETWEEN PACKET VECTORS (all 158766 unordered pairs of 564 packets)")
pv = {r: P[r]["pv"] for r in rids}
same_f, diff_f, same_q, diff_q_same_f = [], [], [], []
for i in range(len(rids)):
    a = rids[i]
    for j in range(i + 1, len(rids)):
        b = rids[j]
        cv = dot(pv[a], pv[b])  # both unit
        if P[a]["focus"] == P[b]["focus"]:
            same_f.append(cv)
            if P[a]["query_id"] == P[b]["query_id"]:
                same_q.append(cv)
            else:
                diff_q_same_f.append(cv)
        else:
            diff_f.append(cv)
print("same focus world  :", mmm(same_f))
print("   same question  :", mmm(same_q))
print("   diff question  :", mmm(diff_q_same_f))
print("different focus   :", mmm(diff_f))
# held vs trained packets
hp_ = [r for r in rids if split[r] == "held"]
tp_ = [r for r in rids if split[r] == "trained"]
nn_h = [max(dot(pv[a], pv[b]) for b in tp_) for a in hp_]
nn_t = [max(dot(pv[a], pv[b]) for b in tp_ if b != a) for a in tp_]
print("held packet -> nearest TRAINED packet cos   :", mmm(nn_h))
print("trained packet -> nearest OTHER trained cos :", mmm(nn_t))
# centred cosines: remove the course-mean packet vector
mean_pv = [sum(pv[r][k] for r in rids) / len(rids) for k in range(D)]
print("norm of course-mean packet vector (1.0 = all identical):", "%.6f" % nrm(mean_pv))
cen = {r: [pv[r][k] - mean_pv[k] for k in range(D)] for r in rids}
res_norm = [nrm(cen[r]) for r in rids]
print("norm of packet residual after removing course mean:", mmm(res_norm))
sf, df = [], []
for i in range(len(rids)):
    a = rids[i]
    for j in range(i + 1, len(rids)):
        b = rids[j]
        (sf if P[a]["focus"] == P[b]["focus"] else df).append(cos(cen[a], cen[b]))
print("CENTRED cos same focus     :", mmm(sf))
print("CENTRED cos different focus:", mmm(df))
print()

# ---------------- (c) squared-norm share of question rows ----------------
print("=" * 100)
print("(c) SQUARED-NORM SHARE OF ROW CATEGORIES INSIDE THE PACKET VECTOR")
print("s = sum of unit row vectors (packet vector = s/|s|). share_add(C) = <s_C, s>/|s|^2 (sums to 1 over C);")
print("share_own(C) = |s_C|^2/|s|^2 (the category alone).")
add_share = defaultdict(list)
own_share = defaultdict(list)
cos_q = []
for r in rids:
    sc = defaultdict(lambda: [0.0] * D)
    for x in P[r]["rows"]:
        v = RV[x["key"]]
        acc = sc[CAT[x["tag"]]]
        for k in range(D):
            acc[k] += v[k]
    s = [sum(sc[cn][k] for cn in sc) for k in range(D)]
    ss = dot(s, s)
    for cn in ("shared_context", "focus_source", "packet_digests", "question", "markers"):
        add_share[cn].append(dot(sc[cn], s) / ss)
        own_share[cn].append(dot(sc[cn], sc[cn]) / ss)
    cos_q.append(cos(sc["question"], s))
    # check reconstruction
    u = unit(s)
    assert max(abs(u[k] - pv[r][k]) for k in range(D)) < 1e-12
for cn in ("shared_context", "focus_source", "packet_digests", "question", "markers"):
    print("  %-15s add: %s" % (cn, mmm(add_share[cn])))
    print("  %-15s own: %s" % ("", mmm(own_share[cn])))
print("cos(question-rows sum, packet vector):", mmm(cos_q))
# share inside the encoded slot vector enc = unit(p + q)
enc_q_share, enc_question_share = [], []
qsum_unit = {}
for r in rids:
    sq = [0.0] * D
    s = [0.0] * D
    for x in P[r]["rows"]:
        v = RV[x["key"]]
        for k in range(D):
            s[k] += v[k]
            if x["tag"] in QTAGS:
                sq[k] += v[k]
    ns = nrm(s)
    qsum_unit[r] = [x / ns for x in sq]  # question part of the (unit) packet vector
for sl in S:
    p = pv[sl["record_id"]]
    q = sl["qv"]
    e = [p[k] + q[k] for k in range(D)]
    ee = dot(e, e)
    enc_q_share.append(dot(q, e) / ee)
    enc_question_share.append(dot(qsum_unit[sl["record_id"]], e) / ee)
print("inside enc = unit(p+q), additive share of the slot query q      :", mmm(enc_q_share))
print("inside enc = unit(p+q), additive share of question frame rows    :", mmm(enc_question_share))
print()

# ---------------- (d) query-vector nearest neighbours ----------------
print("=" * 100)
print("(d) SLOT QUERY VECTORS: held-world slots vs trained slots (cos = (64 - 2*popcount(xor))/64)")
held_sl = [s for s in S if s["split"] == "held"]
tr_sl = [s for s in S if s["split"] == "trained"]
print("slots: held", len(held_sl), "trained", len(tr_sl), "excluded", sum(1 for s in S if s["split"] == "excluded"))
spec_mask = {}
for s in S:
    if s["spec_c"] in spec_mask:
        assert spec_mask[s["spec_c"]] == s["mask"]
    spec_mask[s["spec_c"]] = s["mask"]
tr_masks = Counter(s["mask"] for s in tr_sl)
tr_specs = set(s["spec_c"] for s in tr_sl)
dm = list(tr_masks)
print("distinct trained query vectors:", len(dm), " distinct trained specs:", len(tr_specs))
print("held slots whose exact spec occurs among trained slots:", sum(1 for s in held_sl if s["spec_c"] in tr_specs))
print("held slots whose query vector equals a trained query vector:", sum(1 for s in held_sl if s["mask"] in tr_masks))
held_alias = set()
for s in held_sl:
    held_alias.add(s["scope_alias"])
print("held slot scope aliases:", sorted(held_alias))
print("trained slots with a held-world scope alias:", sum(1 for s in tr_sl if s["scope_alias"] in held_alias))


def best_over(mask, pool, skip_self):
    best = -65
    for m in pool:
        if skip_self and m == mask:
            continue
        v = 64 - 2 * (mask ^ m).bit_count()
        if v > best:
            best = v
    return best / 64.0


best_other = {}
for m in dm:
    best_other[m] = best_over(m, dm, True)
held_best_cache = {}
held_max = []
for s in held_sl:
    if s["mask"] not in held_best_cache:
        held_best_cache[s["mask"]] = best_over(s["mask"], dm, False)
    held_max.append(held_best_cache[s["mask"]])
tr_max_incl = [1.0 if tr_masks[s["mask"]] > 1 else best_other[s["mask"]] for s in tr_sl]
tr_max_excl = [best_other[s["mask"]] for s in tr_sl]
print("held slot -> max cos to any TRAINED slot query           :", mmm(held_max))
print("trained slot -> max cos to any OTHER trained slot query  :", mmm(tr_max_incl))
print("   share of trained slots with an identical query vector in another trained slot:",
      pct(sum(1 for s in tr_sl if tr_masks[s["mask"]] > 1) / len(tr_sl)))
print("trained slot -> max cos to a DIFFERENT trained query vector:", mmm(tr_max_excl))
rng = random.Random(20260919)
rand_max = [best_over(rng.getrandbits(64), dm, False) for _ in range(500)]
print("control: 500 seeded random +-1/8 vectors -> max cos to trained queries:", mmm(rand_max))
# the full encoded input: labelled slots only (the (e) population), exact float64
print()
print("(d') FULL ENCODED SLOT INPUT enc = unit(p+q), per-bit-kind slots only")
enc = {}
for s in S:
    if s["label"] is None:
        continue
    p = pv[s["record_id"]]
    enc[id(s)] = unit([p[k] + s["qv"][k] for k in range(D)])
lab = [s for s in S if s["label"] is not None]
lab_h = [s for s in lab if s["split"] == "held"]
lab_t = [s for s in lab if s["split"] == "trained"]
hm, tm_incl, tm_excl_same_packet = [], [], []
for s in lab_h:
    hm.append(max(dot(enc[id(s)], enc[id(t)]) for t in lab_t))
for s in lab_t:
    tm_incl.append(max(dot(enc[id(s)], enc[id(t)]) for t in lab_t if t is not s))
    tm_excl_same_packet.append(max(dot(enc[id(s)], enc[id(t)]) for t in lab_t
                                   if t["record_id"] != s["record_id"] and t["spec_c"] != s["spec_c"]))
print("held slot -> max cos(enc) to any trained slot                     :", mmm(hm))
print("trained slot -> max cos(enc) to any other trained slot             :", mmm(tm_incl))
print("trained slot -> max cos(enc), other packet AND different spec      :", mmm(tm_excl_same_packet))
print()

# ---------------- (e) linear probes: fit on TRAINED worlds, test on HELD worlds ----------------
print("=" * 100)
print("(e) PER-BIT LINEAR PROBES, fit on trained-record slots, tested on held-world slots")


def solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-300:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv_ = M[col][col]
        for r in range(n):
            if r != col and M[r][col] != 0.0:
                f = M[r][col] / pv_
                Mr, Mc = M[r], M[col]
                for c2 in range(col, n + 1):
                    Mr[c2] -= f * Mc[c2]
    return [M[i][n] / M[i][i] for i in range(n)]


def ridge_fit(X, y, lam):
    n = len(X[0]) + 1
    A = [[0.0] * n for _ in range(n)]
    b = [0.0] * n
    for x, t in zip(X, y):
        z = x + [1.0]
        for i in range(n):
            zi = z[i]
            if zi == 0.0:
                continue
            b[i] += zi * t
            Ai = A[i]
            for j in range(n):
                Ai[j] += zi * z[j]
    for i in range(n - 1):  # bias unregularised
        A[i][i] += lam
    return solve(A, b)


def ridge_acc(w, X, y):
    hits = 0
    for x, t in zip(X, y):
        sc = sum(wi * xi for wi, xi in zip(w, x)) + w[-1]
        hits += 1 if (1.0 if sc >= 0 else -1.0) == t else 0
    return hits / len(X)


def lda_fit(X, y, ridge=1e-3):
    """Same estimator as records/encoder_capacity_001/measure_binding_variants.py:153-183."""
    Pp = [x for x, t in zip(X, y) if t > 0]
    Aa = [x for x, t in zip(X, y) if t < 0]
    if not Pp or not Aa:
        return None
    mp = [sum(x[k] for x in Pp) / len(Pp) for k in range(D)]
    ma = [sum(x[k] for x in Aa) / len(Aa) for k in range(D)]
    pooled = [[0.0] * D for _ in range(D)]
    for x, t in zip(X, y):
        c0 = mp if t > 0 else ma
        dl = [x[k] - c0[k] for k in range(D)]
        for i in range(D):
            di = dl[i]
            row = pooled[i]
            for j in range(D):
                row[j] += di * dl[j]
    sc = 1.0 / max(1, len(X) - 2)
    for i in range(D):
        for j in range(D):
            pooled[i][j] *= sc
        pooled[i][i] += ridge
    w = solve(pooled, [mp[k] - ma[k] for k in range(D)])
    if w is None:
        return None
    centre = [(mp[k] + ma[k]) / 2 for k in range(D)]
    return w, centre


def lda_acc(model, X, y):
    w, centre = model
    hits = 0
    for x, t in zip(X, y):
        sc = sum(w[k] * (x[k] - centre[k]) for k in range(D))
        hits += 1 if (1.0 if sc >= 0 else -1.0) == t else 0
    return hits / len(X)


def feats(s, which):
    p = pv[s["record_id"]]
    if which == "enc":
        return enc[id(s)]
    if which == "q":
        return list(s["qv"])
    if which == "p":
        return list(p)
    raise ValueError(which)


def maj_rate(y):
    c = Counter(y)
    return max(c.values()) / len(y)


def const_acc(ytrain, ytest):
    m = Counter(ytrain).most_common(1)[0][0]
    return sum(1 for t in ytest if t == m) / len(ytest)


def packet_ceiling(sl):
    """Best accuracy of ANY rule that gives one answer per packet (i.e. ignores the slot query q)."""
    by = defaultdict(Counter)
    for s in sl:
        by[s["record_id"]][s["label"]] += 1
    return sum(max(c.values()) for c in by.values()) / len(sl)


def knn_acc(train, test, k):
    hits = 0
    for s in test:
        e = enc[id(s)]
        sims = sorted(((dot(e, enc[id(t)]), t["label"]) for t in train), reverse=True)[:k]
        vote = Counter(l for _, l in sims).most_common()
        guess = vote[0][0]
        hits += 1 if guess == s["label"] else 0
    return hits / len(test)


def lookup_acc(train, test):
    table = defaultdict(Counter)
    overall = Counter()
    for s in train:
        key = (s["scope_alias"], tuple(s["coordinates"]))
        table[key][s["label"]] += 1
        overall[s["label"]] += 1
    fb = overall.most_common(1)[0][0]
    cov = sum(1 for s in test if (s["scope_alias"], tuple(s["coordinates"])) in table)
    hits = sum(1 for s in test if (table[(s["scope_alias"], tuple(s["coordinates"]))].most_common(1)[0][0]
                                   if (s["scope_alias"], tuple(s["coordinates"])) in table else fb) == s["label"])
    return hits / len(test), cov / len(test)


Y = lambda sl: [1.0 if s["label"] == "PRESENT" else -1.0 for s in sl]
LAMS = (1e-3, 1e-1, 1.0, 10.0)
summary = {}
for kind in KINDS4:
    tr = [s for s in lab_t if s["kind"] == kind]
    he = [s for s in lab_h if s["kind"] == kind]
    ytr, yhe = Y(tr), Y(he)
    print("-" * 100)
    print("kind %-13s trained slots %5d (records %d, PRESENT %s) | held slots %4d (records %d, PRESENT %s)" % (
        kind, len(tr), len({s['record_id'] for s in tr}), pct(sum(1 for t in ytr if t > 0) / len(ytr)),
        len(he), len({s['record_id'] for s in he}), pct(sum(1 for t in yhe if t > 0) / len(yhe))))
    print("   held majority-class rate %s | train-majority constant on held %s | per-packet ceiling (any q-blind rule) on held %s"
          % (pct(maj_rate(yhe)), pct(const_acc(ytr, yhe)), pct(packet_ceiling(he))))
    row = {"held_majority": maj_rate(yhe), "train_const_on_held": const_acc(ytr, yhe),
           "held_packet_ceiling": packet_ceiling(he), "n_train": len(tr), "n_held": len(he)}
    for which in ("enc", "q", "p"):
        Xtr = [feats(s, which) for s in tr]
        Xhe = [feats(s, which) for s in he]
        for lam in LAMS:
            w = ridge_fit(Xtr, ytr, lam)
            a_tr, a_he = ridge_acc(w, Xtr, ytr), ridge_acc(w, Xhe, yhe)
            print("   ridge-LS %-3s lam=%-6g train %s  held %s" % (which, lam, pct(a_tr), pct(a_he)))
            row["ridge_%s_%g" % (which, lam)] = (a_tr, a_he)
        m = lda_fit(Xtr, ytr)
        if m is not None:
            a_tr, a_he = lda_acc(m, Xtr, ytr), lda_acc(m, Xhe, yhe)
            print("   ridgeLDA %-3s (published estimator) train %s  held %s" % (which, pct(a_tr), pct(a_he)))
            row["lda_%s" % which] = (a_tr, a_he)
    for k in (1, 5):
        a = knn_acc(tr, he, k)
        print("   %d-NN cosine on enc: held %s" % (k, pct(a)))
        row["knn%d" % k] = a
    la, cov = lookup_acc(tr, he)
    print("   lookup memoriser (scope alias, coordinates): held %s, key coverage %s" % (pct(la), pct(cov)))
    row["lookup"] = (la, cov)
    summary[kind] = row
print()

# ---------------- calibration: the same probe IN-WORLD (published design) ----------------
print("=" * 100)
print("CALIBRATION: same estimators, 5-fold IN-WORLD over all 564 records (fold = record index % 5,")
print("records sorted by record_id; published design used prediction order index % 5)")
for kind in KINDS4:
    allk = [s for s in lab if s["kind"] == kind]
    order = {r: i for i, r in enumerate(sorted({s["record_id"] for s in allk}))}
    accs = defaultdict(list)
    for fold in range(5):
        tr = [s for s in allk if order[s["record_id"]] % 5 != fold]
        te = [s for s in allk if order[s["record_id"]] % 5 == fold]
        for which in ("enc", "q"):
            Xtr = [feats(s, which) for s in tr]
            Xte = [feats(s, which) for s in te]
            m = lda_fit(Xtr, Y(tr))
            accs["lda_" + which].append(lda_acc(m, Xte, Y(te)))
            w = ridge_fit(Xtr, Y(tr), 1e-3)
            accs["ridge_" + which].append(ridge_acc(w, Xte, Y(te)))
        accs["lookup"].append(lookup_acc(tr, te)[0])
        accs["const"].append(const_acc(Y(tr), Y(te)))
    print("  %-13s slots %5d  " % (kind, len(allk)) + "  ".join(
        "%s %s" % (k, pct(sum(v) / len(v))) for k, v in sorted(accs.items())))
    summary[kind]["inworld"] = {k: sum(v) / len(v) for k, v in accs.items()}
print()

# ---------------- control: leave-5-TRAINED-worlds-out ----------------
print("=" * 100)
print("CONTROL: leave five TRAINED focus worlds out (10 seeded draws); fit on the other trained-world slots,")
print("test on the left-out worlds' slots. Tests whether failure is about ANY unseen world, not these five.")
tr_worlds = sorted({s["focus"] for s in lab_t})
rng = random.Random(20260919)
for kind in KINDS4:
    res = defaultdict(list)
    for draw in range(10):
        out5 = set(rng.sample(tr_worlds, 5))
        tr = [s for s in lab_t if s["kind"] == kind and s["focus"] not in out5]
        te = [s for s in lab_t if s["kind"] == kind and s["focus"] in out5]
        if not te or len({s["label"] for s in tr}) < 2:
            continue
        Xtr = [enc[id(s)] for s in tr]
        Xte = [enc[id(s)] for s in te]
        w = ridge_fit(Xtr, Y(tr), 1e-3)
        res["ridge_enc_train"].append(ridge_acc(w, Xtr, Y(tr)))
        res["ridge_enc_test"].append(ridge_acc(w, Xte, Y(te)))
        m = lda_fit(Xtr, Y(tr))
        res["lda_enc_test"].append(lda_acc(m, Xte, Y(te)))
        res["test_majority"].append(maj_rate(Y(te)))
        res["train_const_on_test"].append(const_acc(Y(tr), Y(te)))
        res["n_test"].append(len(te))
    print("  %-13s draws %d  " % (kind, len(res["n_test"])) + "  ".join(
        "%s %s" % (k, pct(sum(v) / len(v)) if k != "n_test" else str(sum(v))) for k, v in sorted(res.items())))
    summary[kind]["leave5"] = {k: sum(v) / len(v) for k, v in res.items()}

(HERE / "analyze2_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
print("\nwrote analyze2_summary.json")
