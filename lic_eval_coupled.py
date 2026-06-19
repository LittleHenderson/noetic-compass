"""LICENSE gate for the COUPLED detector: pre-answer hidden-state probe + semantic entropy.

Leakage-safe stacking: inside each fold, fit the hidden probe on train, read its score for
train/test, standardize the SE features on train, then fit a meta-logistic on
[hidden_score, SE_features]. Reports hidden-only, SE-only, and COUPLED balanced accuracy,
all against the same text controls + residual + held-out gates as lic_eval.py.

NOTE: the coupled detector reads generations (the K sampled answers feed semantic entropy),
so it is a HYBRID, not a pure pre-answer hidden-state detector. In closed-book this is NOT
label leakage (sampled answers do not contain ground truth), but the hybrid status is recorded.
REAL numbers only. LICENSED iff every gate passes.
"""
import sys, json
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score

KWIK = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '/root/kwik_14b.npz'
SE   = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else '/root/kwik_14b_se.npz'
RUN_PERM = '--perm' in sys.argv
NPERM = 1000
OUT = '/root/lic_report_coupled.json'
for a in sys.argv:
    if a.startswith('--out='): OUT = a.split('=',1)[1]

d = np.load(KWIK, allow_pickle=True); s = np.load(SE, allow_pickle=True)
n = int(s['n']) if 'n' in s.files else len(s['se_entropy'])
correct = d['correct'].astype(int)[:n]; y = (1 - correct).astype(int)
question = d['question'].astype(str)[:n]; qtype = d['qtype'].astype(str)[:n]
qlen = (d['qlen'].astype(float) if 'qlen' in d.files else np.zeros(len(correct)))[:n]
Flast = d['features'].astype(np.float32)[:n]
N, nL, H = Flast.shape
SEF = np.column_stack([s['se_entropy'][:n], s['se_nclusters'][:n], s['se_top_frac'][:n], s['se_uniq_frac'][:n]])
model_id = str(d['model_id']) if 'model_id' in d.files else KWIK
print(f"[data] model={model_id} N={N} layers={nL} INCORRECT(y=1)={int(y.sum())} CORRECT={int((1-y).sum())} "
      f"mean_entropy={SEF[:,0].mean():.3f}")

SCAN = list(range(max(1, nL//3), nL))
FOLDS = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=0).split(np.zeros(N), y))

def hid_ba(L, yy):
    bas = []
    for tr, te in FOLDS:
        sc = StandardScaler().fit(Flast[tr, L, :])
        c = LogisticRegression(C=0.25, max_iter=2000, class_weight='balanced').fit(sc.transform(Flast[tr, L, :]), yy[tr])
        bas.append(balanced_accuracy_score(yy[te], c.predict(sc.transform(Flast[te, L, :]))))
    return float(np.mean(bas))
per_layer = {L: hid_ba(L, y) for L in SCAN}
bestL = max(per_layer, key=per_layer.get); hid = per_layer[bestL]
print(f"[hidden] best layer L{bestL} = {hid:.4f}")

# SE-only detector (method B baseline)
se_bas = []
for tr, te in FOLDS:
    sc = StandardScaler().fit(SEF[tr])
    c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(sc.transform(SEF[tr]), y[tr])
    se_bas.append(balanced_accuracy_score(y[te], c.predict(sc.transform(SEF[te]))))
se_only = float(np.mean(se_bas)); print(f"[SE-only] BA = {se_only:.4f}")

# COUPLED detector (leakage-safe stacking) + OOF coupled score for residual
def coupled_oof(yy, L=bestL):
    oof = np.zeros(N); bas = []
    for tr, te in FOLDS:
        sc = StandardScaler().fit(Flast[tr, L, :])
        hp = LogisticRegression(C=0.25, max_iter=2000, class_weight='balanced').fit(sc.transform(Flast[tr, L, :]), yy[tr])
        htr = hp.decision_function(sc.transform(Flast[tr, L, :])); hte = hp.decision_function(sc.transform(Flast[te, L, :]))
        ss = StandardScaler().fit(SEF[tr])
        Xtr = np.column_stack([htr, ss.transform(SEF[tr])]); Xte = np.column_stack([hte, ss.transform(SEF[te])])
        meta = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(Xtr, yy[tr])
        oof[te] = meta.decision_function(Xte)
        bas.append(balanced_accuracy_score(yy[te], meta.predict(Xte)))
    return float(np.mean(bas)), oof
coupled, coupled_score = coupled_oof(y)
print(f"[COUPLED] hidden+SE BA = {coupled:.4f}")

# text / metadata controls
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
margin = coupled - ctrl_max
print("[controls] " + " ".join(f"{k}={v:.4f}" for k,v in controls.items()))
print(f"[margin] coupled({coupled:.4f}) - best_control({best_ctrl}={ctrl_max:.4f}) = {margin:+.4f}")

# residual: remove question text/length/qtype info from the coupled score
cv = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=8000).fit_transform(question)
svd = TruncatedSVD(n_components=min(60, cv.shape[1]-1)).fit_transform(cv)
qoh = OneHotEncoder(handle_unknown='ignore').fit_transform(qtype.reshape(-1,1)).toarray()
TI = np.column_stack([svd, qlen.reshape(-1,1), qoh])
res_bas = []
for tr, te in FOLDS:
    reg = LinearRegression().fit(TI[tr], coupled_score[tr])
    rtr = coupled_score[tr]-reg.predict(TI[tr]); rte = coupled_score[te]-reg.predict(TI[te])
    c = LogisticRegression(C=0.5, max_iter=2000).fit(rtr.reshape(-1,1), y[tr])
    res_bas.append(balanced_accuracy_score(y[te], c.predict(rte.reshape(-1,1))))
residual_ba = float(np.mean(res_bas)); print(f"[residual] coupled BA after removing text info = {residual_ba:.4f}")

# held-out qtype (coupled, refit per held-out type)
ho = {}
for t in sorted(set(qtype.tolist())):
    tr = np.where(qtype != t)[0]; te = np.where(qtype == t)[0]
    if len(set(y[te].tolist()))<2 or len(set(y[tr].tolist()))<2 or len(te)<20: ho[t]=None; continue
    sc = StandardScaler().fit(Flast[tr,bestL,:]); hp = LogisticRegression(C=0.25,max_iter=2000,class_weight='balanced').fit(sc.transform(Flast[tr,bestL,:]),y[tr])
    htr=hp.decision_function(sc.transform(Flast[tr,bestL,:])); hte=hp.decision_function(sc.transform(Flast[te,bestL,:]))
    ss=StandardScaler().fit(SEF[tr]); Xtr=np.column_stack([htr,ss.transform(SEF[tr])]); Xte=np.column_stack([hte,ss.transform(SEF[te])])
    meta=LogisticRegression(C=1.0,max_iter=3000,class_weight='balanced').fit(Xtr,y[tr])
    ho[t]=float(balanced_accuracy_score(y[te],meta.predict(Xte)))
ho_vals=[v for v in ho.values() if v is not None]; ho_mean=float(np.mean(ho_vals)) if ho_vals else 0.0
print("[held-out-qtype] " + " ".join(f"{t}={('%.3f'%v) if v is not None else 'NA'}" for t,v in ho.items()) + f" | mean={ho_mean:.4f}")

report = dict(model=model_id, detector='COUPLED hidden(pre-answer) + semantic-entropy(generations)', hybrid=True,
    N=N, incorrect=int(y.sum()), correct=int((1-y).sum()),
    hidden_only_BA=hid, SE_only_BA=se_only, coupled_BA=coupled, best_layer=int(bestL),
    controls=controls, best_control=best_ctrl, control_max=ctrl_max, margin=margin,
    residual_BA=residual_ba, heldout_qtype=ho, heldout_qtype_mean=ho_mean)

if RUN_PERM:
    rng=np.random.RandomState(0); pmax=[]
    real=coupled
    for i in range(NPERM):
        yp=rng.permutation(y); b,_=coupled_oof(yp); pmax.append(b)
        if (i+1)%50==0: print(f"[perm] {i+1}/{NPERM} pmax={max(pmax):.3f}", flush=True)
    pmax=np.array(pmax); p=(np.sum(pmax>=real)+1)/(NPERM+1)
    report.update(perm_p=float(p), perm_max=float(pmax.max()), nperm=NPERM)
    print(f"[perm] coupled p={p:.4f} perm_max={pmax.max():.4f}")

gates = dict(
  enough_data=(N>=800 and min(int(y.sum()),int((1-y).sum()))>=150),
  accuracy_floor=(coupled>=0.75),
  margin_over_text=(margin>=0.15),
  residual_proof=(residual_ba>=0.75),
  heldout_proof=(ho_mean>=0.75),
)
if RUN_PERM: gates['permutation_proof']=(report['perm_p']<0.001 if NPERM>=1000 else False)
report['gates']=gates; report['LICENSED']=bool(all(gates.values()))
print("[gates] " + " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k,v in gates.items()))
print(f"[VERDICT] LICENSED={report['LICENSED']}  (hybrid detector)")
open(OUT,'w').write(json.dumps(report,indent=2,default=float))
print(f"[saved] {OUT}")
