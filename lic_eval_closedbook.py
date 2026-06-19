"""LICENSE gate for the closed-book KWIK hallucination probe (leakage-safe).

Pre-answer windows: last-prompt-token AND mean-pooled-over-prompt readouts (both are
strictly pre-answer — no answer token is in the context). Every question is unique, so
there is NO same-prompt cross-label leakage by construction; we still use StratifiedKFold
and fit every text/length control INSIDE each train fold.

Selection is honest: the hidden probe is chosen over the FULL (readout x layer) grid, and
the permutation test is selection-aware over that same grid (max BA across the whole grid
per shuffle). Gates mirror lic_eval.py:
  accuracy_floor (hidden BA>=0.75), margin_over_text (>=0.15 over MAX control),
  residual_proof (>=0.75 after removing text/length/qtype info), heldout_proof
  (mean BA>=0.75 across held-out question-types), permutation_proof (1000-shuffle p<0.001).
REAL numbers only. LICENSED iff every gate passes.
"""
import sys, json, collections
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score

NPZ = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '/root/kwik_15b.npz'
RUN_PERM = '--perm' in sys.argv
NPERM = 1000
OUT = '/root/lic_report_kwik.json'
for a in sys.argv:
    if a.startswith('--out='): OUT = a.split('=',1)[1]

d = np.load(NPZ, allow_pickle=True)
correct = d['correct'].astype(int)
y = (1 - correct).astype(int)                      # detection target: 1 = INCORRECT (hallucination)
qtype = d['qtype'].astype(str); question = d['question'].astype(str)
qlen = d['qlen'].astype(float) if 'qlen' in d.files else np.zeros(len(y))
model_id = str(d['model_id']) if 'model_id' in d.files else NPZ
READOUTS = {'last': d['features'].astype(np.float32)}
if 'features_mean' in d.files:
    READOUTS['mean'] = d['features_mean'].astype(np.float32)
N, nL, H = READOUTS['last'].shape
print(f"[data] model={model_id} N={N} layers={nL} hidden={H} readouts={list(READOUTS)} "
      f"INCORRECT(y=1)={int(y.sum())} CORRECT={int((1-y).sum())} incorrect_rate={y.mean():.3f}")

NSPL = 5
SCAN = list(range(max(1, nL//3), nL))              # upper ~2/3 layers
FOLDS = list(StratifiedKFold(n_splits=NSPL, shuffle=True, random_state=0).split(np.zeros(N), y))

def hid_ba(F, L, yy, FF=FOLDS):
    bas = []
    for tr, te in FF:
        sc = StandardScaler().fit(F[tr, L, :])
        c = LogisticRegression(C=0.25, max_iter=2000, class_weight='balanced').fit(sc.transform(F[tr, L, :]), yy[tr])
        bas.append(balanced_accuracy_score(yy[te], c.predict(sc.transform(F[te, L, :]))))
    return float(np.mean(bas))

grid = {}                                           # (readout,L) -> BA
for rname, F in READOUTS.items():
    for L in SCAN:
        grid[(rname, L)] = hid_ba(F, L, y)
for rname in READOUTS:
    print(f"[hidden:{rname}] " + " ".join(f"L{L}={grid[(rname,L)]:.3f}" for L in SCAN))
(best_readout, bestL) = max(grid, key=grid.get); hid = grid[(best_readout, bestL)]
Fbest = READOUTS[best_readout]
print(f"[hidden] best = readout={best_readout} L{bestL} = {hid:.4f}")

def text_ba(texts, analyzer):
    bas = []
    for tr, te in FOLDS:
        v = (TfidfVectorizer(analyzer='word', ngram_range=(1,2), max_features=5000) if analyzer=='word'
             else TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=8000))
        Xtr = v.fit_transform(texts[tr]); Xte = v.transform(texts[te])
        c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(Xtr, y[tr])
        bas.append(balanced_accuracy_score(y[te], c.predict(Xte)))
    return float(np.mean(bas))
def cat_ba(*cols):
    arr = np.column_stack(cols); bas = []
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

controls = {
 'question_word': text_ba(question, 'word'),
 'question_char': text_ba(question, 'char'),
 'qtype': cat_ba(qtype.reshape(-1,1)),
 'length': num_ba(qlen.reshape(-1,1)),
}
best_ctrl = max(controls, key=controls.get); ctrl_max = controls[best_ctrl]
margin = hid - ctrl_max
print("[controls] " + " ".join(f"{k}={v:.4f}" for k,v in controls.items()))
print(f"[margin] hidden({hid:.4f}) - best_control({best_ctrl}={ctrl_max:.4f}) = {margin:+.4f}")

# ---- residual proof: remove text/length/qtype info from the best hidden OOF score ----
def hid_oof(F, L, yy):
    s = np.zeros(N)
    for tr, te in FOLDS:
        sc = StandardScaler().fit(F[tr, L, :])
        c = LogisticRegression(C=0.25, max_iter=2000, class_weight='balanced').fit(sc.transform(F[tr, L, :]), yy[tr])
        s[te] = c.decision_function(sc.transform(F[te, L, :]))
    return s
hscore = hid_oof(Fbest, bestL, y)
cv = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=8000).fit_transform(question)
svd = TruncatedSVD(n_components=min(60, cv.shape[1]-1)).fit_transform(cv)
qoh = OneHotEncoder(handle_unknown='ignore').fit_transform(qtype.reshape(-1,1)).toarray()
TI = np.column_stack([svd, qlen.reshape(-1,1), qoh])
res_bas = []
for tr, te in FOLDS:
    reg = LinearRegression().fit(TI[tr], hscore[tr])
    rtr = hscore[tr] - reg.predict(TI[tr]); rte = hscore[te] - reg.predict(TI[te])
    c = LogisticRegression(C=0.5, max_iter=2000).fit(rtr.reshape(-1,1), y[tr])
    res_bas.append(balanced_accuracy_score(y[te], c.predict(rte.reshape(-1,1))))
residual_ba = float(np.mean(res_bas))
print(f"[residual] hidden BA after removing question text/length/qtype info = {residual_ba:.4f}")

# ---- held-out question-type proof ----
ho = {}
for t in sorted(set(qtype.tolist())):
    tr = np.where(qtype != t)[0]; te = np.where(qtype == t)[0]
    if len(set(y[te].tolist())) < 2 or len(set(y[tr].tolist())) < 2 or len(te) < 20:
        ho[t] = None; continue
    sc = StandardScaler().fit(Fbest[tr, bestL, :])
    c = LogisticRegression(C=0.25, max_iter=2000, class_weight='balanced').fit(sc.transform(Fbest[tr, bestL, :]), y[tr])
    ho[t] = float(balanced_accuracy_score(y[te], c.predict(sc.transform(Fbest[te, bestL, :]))))
ho_vals = [v for v in ho.values() if v is not None]
ho_mean = float(np.mean(ho_vals)) if ho_vals else 0.0
print("[held-out-qtype] " + " ".join(f"{t}={('%.3f'%v) if v is not None else 'NA'}" for t,v in ho.items()) + f" | mean={ho_mean:.4f}")

report = dict(model=model_id, window='last-token + mean-pool (W0 pre-answer)', framing='closed-book KWIK / TriviaQA',
    N=N, incorrect=int(y.sum()), correct=int((1-y).sum()), incorrect_rate=float(y.mean()),
    scan_layers=SCAN, readouts=list(READOUTS),
    per_grid={f"{r}:L{L}": grid[(r,L)] for (r,L) in grid},
    best_readout=best_readout, best_layer=int(bestL), hidden_BA=hid,
    controls=controls, best_control=best_ctrl, control_max=ctrl_max, margin=margin,
    residual_BA=residual_ba, heldout_qtype=ho, heldout_qtype_mean=ho_mean)

if RUN_PERM:
    rng = np.random.RandomState(0); pmax = []
    real_max = max(grid.values())
    for i in range(NPERM):
        yp = rng.permutation(y)
        bas = [hid_ba(READOUTS[r], L, yp) for (r, L) in grid]
        pmax.append(max(bas))
        if (i+1) % 50 == 0: print(f"[perm] {i+1}/{NPERM} pmax_so_far={max(pmax):.3f}", flush=True)
    pmax = np.array(pmax)
    p_sel = (np.sum(pmax >= real_max)+1)/(NPERM+1)
    report.update(perm_p_selection_aware=float(p_sel), perm_max=float(pmax.max()), nperm=NPERM)
    print(f"[perm] selection-aware p={p_sel:.4f} perm_max={pmax.max():.4f} (grid={len(grid)} cells)")

gates = dict(
  enough_data=(N >= 800 and min(int(y.sum()), int((1-y).sum())) >= 150),
  accuracy_floor=(hid >= 0.75),
  margin_over_text=(margin >= 0.15),
  residual_proof=(residual_ba >= 0.75),
  heldout_proof=(ho_mean >= 0.75),
)
if RUN_PERM: gates['permutation_proof'] = (report['perm_p_selection_aware'] < 0.001 if NPERM >= 1000 else False)
report['gates'] = gates
report['LICENSED'] = bool(all(gates.values()))
print("[gates] " + " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k,v in gates.items()))
print(f"[VERDICT] LICENSED={report['LICENSED']}")
open(OUT, 'w').write(json.dumps(report, indent=2, default=float))
print(f"[saved] {OUT}")
