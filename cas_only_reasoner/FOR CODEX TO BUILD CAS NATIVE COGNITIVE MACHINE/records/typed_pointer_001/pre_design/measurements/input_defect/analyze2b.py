"""Stage 3 (defect2): follow-ups on build2.pkl. Pure Python. $0.

1. held-world aliases computed from the 5 frozen HELD_WORLDS ids (analyze2 printed slot scope aliases, which
   include correspondence/analogy target worlds);
2. distinct specs per kind (capacity of a 65-parameter linear fit);
3. NULL for (e): re-draw every held slot's query vector as a fresh seeded random +-1/8 vector (one per spec),
   keep the trained fit fixed, 300 draws; where does the observed held accuracy fall?
4. in-world calibration split into test slots whose exact spec WAS / WAS NOT seen in the training folds.
Run: python -B analyze2b.py > analyze2b_out.txt
"""
import sys
sys.dont_write_bytecode = True
import pickle, math, statistics, random
from collections import Counter, defaultdict
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
d = pickle.loads((HERE / "build2.pkl").read_bytes())
P, S = d["packets"], d["slots"]
D = 64
KINDS4 = ("parts", "context", "role_set", "edge_account")

# reuse estimators from analyze2 without re-running it: copy the pure functions
src = (HERE / "analyze2.py").read_text(encoding="utf-8")
ns = {}
start = src.index("def solve(A, b):")
end = src.index("def feats(s, which):")
exec(compile("import math\nfrom collections import Counter, defaultdict\nD = 64\n" + src[start:end], "analyze2_fns", "exec"), ns)
solve, ridge_fit, ridge_acc, lda_fit, lda_acc = ns["solve"], ns["ridge_fit"], ns["ridge_acc"], ns["lda_fit"], ns["lda_acc"]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def unit(v):
    n = math.sqrt(dot(v, v))
    return [x / n for x in v]


def pct(x):
    return "%.4f%%" % (100.0 * x)


pv = {r: P[r]["pv"] for r in P}
held_ids = set(d["held_worlds"])
alias_of = {}
for s in S:
    alias_of.setdefault(s["scope_world"], s["scope_alias"])
held_alias = sorted(alias_of[w] for w in held_ids if w in alias_of)
print("1. held world aliases (from the 5 frozen ids):", held_alias)
tr = [s for s in S if s["split"] == "trained"]
he = [s for s in S if s["split"] == "held"]
print("   trained slots scoped to a held world:", sum(1 for s in tr if s["scope_world"] in held_ids))
print("   trained slot specs containing a held alias token '\"Wk/' or '\"Wk\"':",
      sum(1 for s in tr if any(('"%s/' % a) in s["spec_c"] or ('"%s"' % a) in s["spec_c"] for a in held_alias)))
print("   held slots scoped to a held world:", sum(1 for s in he if s["scope_world"] in held_ids), "of", len(he))
print("   held slots by kind:", dict(Counter(s["kind"] for s in he)))
print()

print("2. distinct query specs per kind among labelled TRAINED slots (a 65-parameter linear fit can shatter <=65)")
lab = [s for s in S if s["label"] is not None]
for k in KINDS4:
    t = [s for s in lab if s["kind"] == k and s["split"] == "trained"]
    h = [s for s in lab if s["kind"] == k and s["split"] == "held"]
    spec_labels = defaultdict(set)
    for s in t:
        spec_labels[s["spec_c"]].add(s["label"])
    print("   %-13s trained slots %4d distinct specs %4d (specs with BOTH labels across records: %d) | held slots %3d distinct specs %3d"
          % (k, len(t), len(spec_labels), sum(1 for v in spec_labels.values() if len(v) > 1), len(h),
             len({s["spec_c"] for s in h})))
print()

print("3. NULL: held query vectors replaced by fresh random +-1/8 vectors (one per spec), trained fit fixed, 300 draws (1-NN: first 50 draws)")
rng = random.Random(20260920)


def enc_of(s, q):
    p = pv[s["record_id"]]
    return unit([p[k] + q[k] for k in range(D)])


Y = lambda sl: [1.0 if s["label"] == "PRESENT" else -1.0 for s in sl]


def nn1(train_X, train_y, x):
    best, lab_ = -9, None
    for tx, ty in zip(train_X, train_y):
        v = dot(tx, x)
        if v > best:
            best, lab_ = v, ty
    return lab_


for k in KINDS4:
    t = [s for s in lab if s["kind"] == k and s["split"] == "trained"]
    h = [s for s in lab if s["kind"] == k and s["split"] == "held"]
    Xt = [enc_of(s, s["qv"]) for s in t]
    yt, yh = Y(t), Y(h)
    Xh_real = [enc_of(s, s["qv"]) for s in h]
    models = {"ridge_enc_1e-3": ("ridge", ridge_fit(Xt, yt, 1e-3)), "ridge_enc_1": ("ridge", ridge_fit(Xt, yt, 1.0)),
              "lda_enc": ("lda", lda_fit(Xt, yt)), "1nn_enc": ("nn", None)}

    def acc(name, Xh):
        kind_, m = models[name]
        if kind_ == "ridge":
            return ridge_acc(m, Xh, yh)
        if kind_ == "lda":
            return lda_acc(m, Xh, yh)
        return sum(1 for x, y in zip(Xh, yh) if nn1(Xt, yt, x) == y) / len(yh)

    obs = {name: acc(name, Xh_real) for name in models}
    null = defaultdict(list)
    for draw in range(300):
        qs = {}
        Xh = []
        for s in h:
            if s["spec_c"] not in qs:
                qs[s["spec_c"]] = [0.125 if rng.getrandbits(1) else -0.125 for _ in range(D)]
            Xh.append(enc_of(s, qs[s["spec_c"]]))
        for name in models:
            if name == "1nn_enc" and draw >= 50:
                continue
            null[name].append(acc(name, Xh))
    maj = max(Counter(yh).values()) / len(yh)
    print("   %-13s held n=%d majority %s" % (k, len(h), pct(maj)))
    for name in models:
        xs = sorted(null[name])
        ge = sum(1 for x in xs if x >= obs[name]) / len(xs)
        print("      %-15s observed %s | null median %s  5th %s  95th %s  max %s | P(null >= observed) = %.4f"
              % (name, pct(obs[name]), pct(statistics.median(xs)), pct(xs[int(0.05 * len(xs))]),
                 pct(xs[int(0.95 * len(xs)) - 1]), pct(xs[-1]), ge))
print()

print("4. IN-WORLD calibration (5 folds, record index % 5 over sorted record ids), test slots split by whether their")
print("   exact query spec occurred in the training folds. ridge-LS lam=1e-3 on enc and on q.")
for k in KINDS4:
    allk = [s for s in lab if s["kind"] == k]
    order = {r: i for i, r in enumerate(sorted({s["record_id"] for s in allk}))}
    tally = defaultdict(lambda: [0, 0])
    maj = defaultdict(Counter)
    for fold in range(5):
        trn = [s for s in allk if order[s["record_id"]] % 5 != fold]
        tst = [s for s in allk if order[s["record_id"]] % 5 == fold]
        seen = {s["spec_c"] for s in trn}
        for which in ("enc", "q"):
            f = (lambda s: enc_of(s, s["qv"])) if which == "enc" else (lambda s: list(s["qv"]))
            w = ridge_fit([f(s) for s in trn], Y(trn), 1e-3)
            for s in tst:
                x = f(s)
                sc = sum(wi * xi for wi, xi in zip(w, x)) + w[-1]
                hit = (1.0 if sc >= 0 else -1.0) == (1.0 if s["label"] == "PRESENT" else -1.0)
                grp = "seen" if s["spec_c"] in seen else "unseen"
                tally[(which, grp)][0] += hit
                tally[(which, grp)][1] += 1
                if which == "enc":
                    maj[grp][s["label"]] += 1
    parts_ = []
    for grp in ("seen", "unseen"):
        n = tally[("enc", grp)][1]
        if n == 0:
            parts_.append("%s n=0" % grp)
            continue
        parts_.append("%s n=%d enc %s q %s majority %s" % (
            grp, n, pct(tally[("enc", grp)][0] / n), pct(tally[("q", grp)][0] / n),
            pct(max(maj[grp].values()) / sum(maj[grp].values()))))
    print("   %-13s " % k + " | ".join(parts_))
