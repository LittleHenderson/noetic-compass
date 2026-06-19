"""Enhanced-probe ceiling check on cached KWIK activations (no recapture).

Tests whether a stronger probe (leakage-free layer ENSEMBLE across all upper layers +
both readouts, and a nonlinear MLP on the best single layer) can push pre-answer hidden
BA past the level (~0.78) needed for the residual/floor gates to clear at 0.75. If not,
the closed-book KWIK ceiling is confirmed and more model size won't bridge the gate.
Leakage-free: ensemble averages per-fold OOF probabilities (NO layer selection on full
data); MLP is fit inside each train fold. REAL numbers only.
"""
import sys, json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score

NPZ = sys.argv[1]
d = np.load(NPZ, allow_pickle=True)
correct = d['correct'].astype(int); y = (1 - correct).astype(int)
question = d['question'].astype(str)
READOUTS = {'last': d['features'].astype(np.float32)}
if 'features_mean' in d.files: READOUTS['mean'] = d['features_mean'].astype(np.float32)
N, nL, H = READOUTS['last'].shape
SCAN = list(range(max(1, nL//3), nL))
FOLDS = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=0).split(np.zeros(N), y))
print(f"[data] {d['model_id'] if 'model_id' in d.files else NPZ} N={N} layers={nL} y1={int(y.sum())} y0={int((1-y).sum())}")

# ---- text control (strongest fair baseline) ----
def text_ba():
    best = 0.0
    for an, kw in [('word', dict(analyzer='word', ngram_range=(1,2), max_features=5000)),
                   ('char', dict(analyzer='char_wb', ngram_range=(2,5), max_features=8000))]:
        bas = []
        for tr, te in FOLDS:
            v = TfidfVectorizer(**kw); Xtr = v.fit_transform(question[tr]); Xte = v.transform(question[te])
            c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(Xtr, y[tr])
            bas.append(balanced_accuracy_score(y[te], c.predict(Xte)))
        best = max(best, float(np.mean(bas)))
    return best
txt = text_ba(); print(f"[text] best question control BA = {txt:.4f}")

# ---- per-layer OOF probability (leakage-free), for ensemble ----
def oof_proba(F, L):
    p = np.zeros(N)
    for tr, te in FOLDS:
        sc = StandardScaler().fit(F[tr, L, :])
        c = LogisticRegression(C=0.25, max_iter=2000, class_weight='balanced').fit(sc.transform(F[tr, L, :]), y[tr])
        p[te] = c.predict_proba(sc.transform(F[te, L, :]))[:, 1]
    return p

# single-layer best (reference)
single = {}
for rn, F in READOUTS.items():
    for L in SCAN:
        pr = oof_proba(F, L)
        single[(rn, L)] = balanced_accuracy_score(y, (pr >= 0.5).astype(int))
(brn, bL) = max(single, key=single.get)
print(f"[single] best readout={brn} L{bL} BA={single[(brn,bL)]:.4f}")

# ensemble: mean OOF proba across ALL (readout x upper-layer) cells -> threshold at 0.5 via per-fold calib
ens = np.zeros(N); cells = 0
for rn, F in READOUTS.items():
    for L in SCAN:
        ens += oof_proba(F, L); cells += 1
ens /= cells
# pick threshold per-fold (leakage-free) to maximize train BA, apply to test
ens_bas = []
for tr, te in FOLDS:
    ths = np.unique(ens[tr]); best_t, best_b = 0.5, 0.0
    for t in np.linspace(ens[tr].min(), ens[tr].max(), 50):
        b = balanced_accuracy_score(y[tr], (ens[tr] >= t).astype(int))
        if b > best_b: best_b, best_t = b, t
    ens_bas.append(balanced_accuracy_score(y[te], (ens[te] >= best_t).astype(int)))
ens_ba = float(np.mean(ens_bas)); print(f"[ensemble] all-layer mean-proba BA = {ens_ba:.4f} (cells={cells})")

# MLP on best single layer
mlp_bas = []
Fb = READOUTS[brn]
for tr, te in FOLDS:
    sc = StandardScaler().fit(Fb[tr, bL, :])
    m = MLPClassifier(hidden_layer_sizes=(64,), alpha=1e-2, max_iter=300, random_state=0).fit(sc.transform(Fb[tr, bL, :]), y[tr])
    mlp_bas.append(balanced_accuracy_score(y[te], m.predict(sc.transform(Fb[te, bL, :]))))
mlp_ba = float(np.mean(mlp_bas)); print(f"[mlp] 64-unit MLP on best layer BA = {mlp_ba:.4f}")

best_hidden = max(single[(brn, bL)], ens_ba, mlp_ba)
print(f"[BEST HIDDEN] {best_hidden:.4f}  margin_over_text = {best_hidden - txt:+.4f}  (need +0.15)")
print(f"[ceiling] need hidden>=~0.78 for residual/floor 0.75 to be reachable -> {'POSSIBLE' if best_hidden>=0.78 else 'NOT REACHED'}")
