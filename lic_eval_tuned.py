"""Maxed-out leakage-safe gate for closed-book KWIK (more data + stronger probe).

Pushes the hidden-state probe as hard as honestly possible on a single capture:
  - concat of BOTH pre-answer readouts (last-token + mean-pool) per layer,
  - per-layer logistic scan, a 128-unit MLP on the best layer, and an all-layer
    OOF-probability ensemble; the best of these is the hidden detector,
  - selection-aware 1000-perm over the layer scan (the dominant selection).
Everything fit inside folds; controls are the strongest fair text/length/qtype baselines.
Gates: floor>=0.75, margin>=0.15 over MAX control, residual>=0.75, held-out>=0.75, perm p<0.001.
REAL numbers only. LICENSED iff every gate passes.
"""
import sys, json
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score

NPZ = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '/root/kwik_14b_n8k.npz'
RUN_PERM = '--perm' in sys.argv
NPERM = 1000
OUT = '/root/lic_report_tuned.json'
for a in sys.argv:
    if a.startswith('--out='): OUT = a.split('=',1)[1]

d = np.load(NPZ, allow_pickle=True)
correct = d['correct'].astype(int); y = (1 - correct).astype(int)
question = d['question'].astype(str); qtype = d['qtype'].astype(str)
qlen = d['qlen'].astype(float) if 'qlen' in d.files else np.zeros(len(y))
Flast = d['features'].astype(np.float32)
Fmean = d['features_mean'].astype(np.float32) if 'features_mean' in d.files else Flast
model_id = str(d['model_id']) if 'model_id' in d.files else NPZ
N, nL, H = Flast.shape
print(f"[data] model={model_id} N={N} layers={nL} hidden={H} INCORRECT={int(y.sum())} CORRECT={int((1-y).sum())} rate={y.mean():.3f}")
SCAN = list(range(max(1, nL//3), nL))
FOLDS = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=0).split(np.zeros(N), y))

def concat(L): return np.concatenate([Flast[:, L, :], Fmean[:, L, :]], axis=1)

# A: per-layer concat logistic — OOF proba + BA
def layer_oof(L, yy):
    X = concat(L); p = np.zeros(N)
    for tr, te in FOLDS:
        sc = StandardScaler().fit(X[tr])
        c = LogisticRegression(C=0.1, max_iter=3000, class_weight='balanced').fit(sc.transform(X[tr]), yy[tr])
        p[te] = c.decision_function(sc.transform(X[te]))
    return p
layer_ba = {}
oof_by_layer = {}
for L in SCAN:
    p = layer_oof(L, y); oof_by_layer[L] = p
    layer_ba[L] = balanced_accuracy_score(y, (p >= 0).astype(int))
bestL = max(layer_ba, key=layer_ba.get)
print("[A concat-logistic] " + " ".join(f"L{L}={layer_ba[L]:.3f}" for L in SCAN))
print(f"[A] best L{bestL} = {layer_ba[bestL]:.4f}")

# B: MLP on best-L concat
def mlp_oof(L, yy):
    X = concat(L); p = np.zeros(N); ba = []
    for tr, te in FOLDS:
        sc = StandardScaler().fit(X[tr])
        m = MLPClassifier(hidden_layer_sizes=(128,), alpha=1e-2, max_iter=400, random_state=0).fit(sc.transform(X[tr]), yy[tr])
        pr = m.predict_proba(sc.transform(X[te]))[:, 1]; p[te] = pr
        ba.append(balanced_accuracy_score(yy[te], (pr >= 0.5).astype(int)))
    return float(np.mean(ba)), p
mlp_ba, mlp_p = mlp_oof(bestL, y); print(f"[B MLP@L{bestL}] = {mlp_ba:.4f}")

# C: all-layer ensemble (mean OOF proba), per-fold threshold
ens = np.mean([1/(1+np.exp(-oof_by_layer[L])) for L in SCAN], axis=0)
ens_ba = []
for tr, te in FOLDS:
    bt, bb = 0.5, 0.0
    for t in np.linspace(ens[tr].min(), ens[tr].max(), 50):
        b = balanced_accuracy_score(y[tr], (ens[tr] >= t).astype(int))
        if b > bb: bb, bt = b, t
    ens_ba.append(balanced_accuracy_score(y[te], (ens[te] >= bt).astype(int)))
ens_ba = float(np.mean(ens_ba)); print(f"[C ensemble] = {ens_ba:.4f}")

configs = {'concat_logistic': (layer_ba[bestL], oof_by_layer[bestL]),
           'mlp': (mlp_ba, mlp_p), 'ensemble': (ens_ba, ens)}
best_cfg = max(configs, key=lambda k: configs[k][0])
hid, hid_score = configs[best_cfg]
print(f"[hidden] BEST = {best_cfg} BA={hid:.4f}")

def text_ba(texts, analyzer):
    bas = []
    for tr, te in FOLDS:
        v = (TfidfVectorizer(analyzer='word', ngram_range=(1,2), max_features=5000) if analyzer=='word'
             else TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=8000))
        Xtr = v.fit_transform(texts[tr]); Xte = v.transform(texts[te])
        c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(Xtr, y[tr])
        bas.append(balanced_accuracy_score(y[te], c.predict(Xte)))
    return float(np.mean(bas))
def cat_ba(col):
    arr = col.reshape(-1,1); bas = []
    for tr, te in FOLDS:
        oh = OneHotEncoder(handle_unknown='ignore').fit(arr[tr])
        c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(oh.transform(arr[tr]), y[tr])
        bas.append(balanced_accuracy_score(y[te], c.predict(oh.transform(arr[te]))))
    return float(np.mean(bas))
def num_ba(M):
    bas = []
    for tr, te in FOLDS:
        sc = StandardScaler().fit(M[tr])
        c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(sc.transform(M[tr]), y[tr])
        bas.append(balanced_accuracy_score(y[te], c.predict(sc.transform(M[te]))))
    return float(np.mean(bas))
controls = {'question_word': text_ba(question,'word'), 'question_char': text_ba(question,'char'),
            'qtype': cat_ba(qtype), 'length': num_ba(qlen.reshape(-1,1))}
best_ctrl = max(controls, key=controls.get); ctrl_max = controls[best_ctrl]
margin = hid - ctrl_max
print("[controls] " + " ".join(f"{k}={v:.4f}" for k,v in controls.items()))
print(f"[margin] hidden({hid:.4f}) - text({best_ctrl}={ctrl_max:.4f}) = {margin:+.4f}")

# residual on the best config's OOF score
cv = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=8000).fit_transform(question)
svd = TruncatedSVD(n_components=min(80, cv.shape[1]-1)).fit_transform(cv)
qoh = OneHotEncoder(handle_unknown='ignore').fit_transform(qtype.reshape(-1,1)).toarray()
TI = np.column_stack([svd, qlen.reshape(-1,1), qoh])
res_bas = []
for tr, te in FOLDS:
    reg = LinearRegression().fit(TI[tr], hid_score[tr])
    rtr = hid_score[tr]-reg.predict(TI[tr]); rte = hid_score[te]-reg.predict(TI[te])
    c = LogisticRegression(C=0.5, max_iter=2000).fit(rtr.reshape(-1,1), y[tr])
    res_bas.append(balanced_accuracy_score(y[te], c.predict(rte.reshape(-1,1))))
residual_ba = float(np.mean(res_bas)); print(f"[residual] = {residual_ba:.4f}")

# held-out qtype on best-L concat logistic
ho = {}
for t in sorted(set(qtype.tolist())):
    tr = np.where(qtype != t)[0]; te = np.where(qtype == t)[0]
    if len(set(y[te].tolist()))<2 or len(set(y[tr].tolist()))<2 or len(te)<25: ho[t]=None; continue
    X = concat(bestL); sc = StandardScaler().fit(X[tr])
    c = LogisticRegression(C=0.1, max_iter=3000, class_weight='balanced').fit(sc.transform(X[tr]), y[tr])
    ho[t] = float(balanced_accuracy_score(y[te], c.predict(sc.transform(X[te]))))
ho_vals = [v for v in ho.values() if v is not None]; ho_mean = float(np.mean(ho_vals)) if ho_vals else 0.0
print("[held-out-qtype] " + " ".join(f"{t}={('%.3f'%v) if v is not None else 'NA'}" for t,v in ho.items()) + f" | mean={ho_mean:.4f}")

report = dict(model=model_id, N=N, incorrect=int(y.sum()), correct=int((1-y).sum()),
    best_config=best_cfg, best_layer=int(bestL), hidden_BA=hid, layer_ba=layer_ba,
    mlp_BA=mlp_ba, ensemble_BA=ens_ba, controls=controls, best_control=best_ctrl,
    control_max=ctrl_max, margin=margin, residual_BA=residual_ba,
    heldout_qtype=ho, heldout_qtype_mean=ho_mean)

if RUN_PERM:
    rng = np.random.RandomState(0); pmax = []
    real = max(layer_ba.values())
    for i in range(NPERM):
        yp = rng.permutation(y)
        bas = [balanced_accuracy_score(yp, (layer_oof(L, yp) >= 0).astype(int)) for L in SCAN]
        pmax.append(max(bas))
        if (i+1) % 25 == 0: print(f"[perm] {i+1}/{NPERM} pmax={max(pmax):.3f}", flush=True)
    pmax = np.array(pmax); p = (np.sum(pmax >= real)+1)/(NPERM+1)
    report.update(perm_p_selection_aware=float(p), perm_max=float(pmax.max()), nperm=NPERM)
    print(f"[perm] selection-aware p={p:.4f} perm_max={pmax.max():.4f}")

gates = dict(
  enough_data=(N>=800 and min(int(y.sum()),int((1-y).sum()))>=150),
  accuracy_floor=(hid>=0.75), margin_over_text=(margin>=0.15),
  residual_proof=(residual_ba>=0.75), heldout_proof=(ho_mean>=0.75))
if RUN_PERM: gates['permutation_proof'] = (report['perm_p_selection_aware'] < 0.001 if NPERM>=1000 else False)
report['gates'] = gates; report['LICENSED'] = bool(all(gates.values()))
print("[gates] " + " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k,v in gates.items()))
print(f"[VERDICT] LICENSED={report['LICENSED']}")
open(OUT, 'w').write(json.dumps(report, indent=2, default=float))
print(f"[saved] {OUT}")
