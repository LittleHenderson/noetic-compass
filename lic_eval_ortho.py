"""Text-orthogonalized KWIK gate + cleaner labels — attacks the residual gate directly.

Two upgrades over lic_eval_fast.py, both targeting the binding residual gate:
 1. CLEANER LABELS: re-judge correctness from the generations file with relaxed matching
    (containment either direction + numeric/year match + token-set Jaccard) to remove the
    paraphrase false-negatives ("deep sea" vs alias "undersea") that add label noise and
    cap every metric.
 2. TEXT-ORTHOGONAL PROBE: build a text-information matrix T (question word+char SVD, length,
    qtype), and INSIDE each fold regress every hidden dimension on T and keep only the residual
    (the part of the hidden state text cannot linearly predict). Probing those residual features
    IS the residual proof done thoroughly. If it stays >=0.75, residual passes honestly.

Reported gates: accuracy_floor (raw concat probe), margin_over_text (raw - best text control),
residual_proof (text-orthogonal probe BA), held-out (qtype), permutation (selection-aware).
Everything fit inside folds; PCA-256 for speed. REAL numbers only. No fabrication.

Usage: python3 lic_eval_ortho.py <kwik_npz> <gens_jsonl> [--perm] [--out=...]
"""
import sys, json, re, string
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score
from sklearn.pipeline import make_pipeline

NPZ = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '/root/kwik_14b_n8k.npz'
GENS = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else '/root/kwik_14b_n8k_gens.jsonl'
RUN_PERM = '--perm' in sys.argv
NPERM = 1000; NPCA = 256
OUT = '/root/lic_report_ortho.json'
for a in sys.argv:
    if a.startswith('--out='): OUT = a.split('=', 1)[1]

ARTICLES = re.compile(r"\b(a|an|the)\b"); PUNCT = set(string.punctuation)
def norm(s):
    s = s.lower(); s = ARTICLES.sub(" ", s)
    s = "".join(ch for ch in s if ch not in PUNCT)
    return re.sub(r"\s+", " ", s).strip()
def nums(s): return set(re.findall(r"\d+", s))
def clean_correct(gen, aliases):
    ng = norm(gen); gtok = set(ng.split()); gn = nums(gen)
    if not ng: return 0
    for a in aliases:
        na = norm(a)
        if not na: continue
        if na in ng or (len(na) >= 4 and ng in na): return 1          # containment either way
        atok = set(na.split())
        if atok and len(gtok & atok) / len(atok) >= 0.75: return 1      # token-set overlap
        an = nums(a)
        if an and an <= gn and len(an) >= 1: return 1                   # all alias numbers present (years)
    return 0

d = np.load(NPZ, allow_pickle=True)
Flast = d['features'].astype(np.float32)
Fmean = d['features_mean'].astype(np.float32) if 'features_mean' in d.files else Flast
question = d['question'].astype(str); qtype = d['qtype'].astype(str)
qlen = d['qlen'].astype(float) if 'qlen' in d.files else np.zeros(len(question))
model_id = str(d['model_id']) if 'model_id' in d.files else NPZ
N, nL, H = Flast.shape

gens = [json.loads(l) for l in open(GENS) if l.strip()][:N]
y_old = (1 - d['correct'].astype(int))
y_clean = np.array([1 - clean_correct(g.get('gen', ''), g.get('aliases', [])) for g in gens], dtype=int)
flipped = int((y_clean != y_old[:len(gens)]).sum())
y = y_clean
print(f"[labels] N={N} old_incorrect={int(y_old.sum())} clean_incorrect={int(y.sum())} relabeled={flipped}")
print(f"[data] model={model_id} layers={nL} hidden={H}")

FOLDS = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=0).split(np.zeros(N), y))
lo = max(1, nL // 2)
SCAN = sorted(set(list(range(lo, nL, max(1, (nL - lo) // 10))) + [nL-1, nL-2, nL-3]))
def concat(L): return np.concatenate([Flast[:, L, :], Fmean[:, L, :]], axis=1)

# text-information matrix (for orthogonalization + control)
wv = TfidfVectorizer(analyzer='word', ngram_range=(1,2), max_features=4000).fit_transform(question)
cvz = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=6000).fit_transform(question)
Tword = TruncatedSVD(n_components=80, random_state=0).fit_transform(wv)
Tchar = TruncatedSVD(n_components=80, random_state=0).fit_transform(cvz)
qoh = OneHotEncoder(handle_unknown='ignore').fit_transform(qtype.reshape(-1,1)).toarray()
T = np.column_stack([Tword, Tchar, qlen.reshape(-1,1), qoh])

def raw_oof(L, yy):
    X = concat(L); s = np.zeros(N)
    for tr, te in FOLDS:
        pipe = make_pipeline(StandardScaler(), TruncatedSVD(NPCA, random_state=0),
                             LogisticRegression(C=0.5, max_iter=1000, class_weight='balanced'))
        pipe.fit(X[tr], yy[tr]); s[te] = pipe.decision_function(X[te])
    return s
def ortho_oof(L, yy):
    """probe on hidden features with text-predictable directions regressed out (per fold)."""
    X = concat(L); s = np.zeros(N)
    for tr, te in FOLDS:
        sc = StandardScaler().fit(X[tr]); Xtr = sc.transform(X[tr]); Xte = sc.transform(X[te])
        svd = TruncatedSVD(NPCA, random_state=0).fit(Xtr); Ztr = svd.transform(Xtr); Zte = svd.transform(Xte)
        reg = LinearRegression().fit(T[tr], Ztr)                 # predict hidden-PCA from text
        Rtr = Ztr - reg.predict(T[tr]); Rte = Zte - reg.predict(T[te])   # text-orthogonal residual
        c = LogisticRegression(C=0.5, max_iter=1000, class_weight='balanced').fit(Rtr, yy[tr])
        s[te] = c.decision_function(Rte)
    return s

raw_ba = {L: balanced_accuracy_score(y, (raw_oof(L, y) >= 0).astype(int)) for L in SCAN}
bestL = max(raw_ba, key=raw_ba.get); hid = raw_ba[bestL]
print("[raw] " + " ".join(f"L{L}={raw_ba[L]:.3f}" for L in SCAN))
ortho_s = ortho_oof(bestL, y); ortho_ba = balanced_accuracy_score(y, (ortho_s >= 0).astype(int))
print(f"[hidden] raw best L{bestL}={hid:.4f}  text-orthogonal={ortho_ba:.4f}")

def text_ba(analyzer):
    bas = []
    for tr, te in FOLDS:
        v = (TfidfVectorizer(analyzer='word', ngram_range=(1,2), max_features=5000) if analyzer=='word'
             else TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=8000))
        Xtr = v.fit_transform(question[tr]); Xte = v.transform(question[te])
        c = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced').fit(Xtr, y[tr])
        bas.append(balanced_accuracy_score(y[te], c.predict(Xte)))
    return float(np.mean(bas))
controls = {'question_word': text_ba('word'), 'question_char': text_ba('char')}
ctrl_max = max(controls.values()); margin = hid - ctrl_max
print(f"[controls] {controls}  margin={margin:+.4f}")

# held-out qtype on text-orthogonal probe (the hard generalization + text-blind test)
ho = {}
for t in sorted(set(qtype.tolist())):
    tr = np.where(qtype != t)[0]; te = np.where(qtype == t)[0]
    if len(set(y[te].tolist()))<2 or len(set(y[tr].tolist()))<2 or len(te)<40: ho[t]=None; continue
    X = concat(bestL); sc = StandardScaler().fit(X[tr])
    Xtr = sc.transform(X[tr]); Xte = sc.transform(X[te])
    svd = TruncatedSVD(NPCA, random_state=0).fit(Xtr); Ztr=svd.transform(Xtr); Zte=svd.transform(Xte)
    reg = LinearRegression().fit(T[tr], Ztr); Rtr=Ztr-reg.predict(T[tr]); Rte=Zte-reg.predict(T[te])
    c = LogisticRegression(C=0.5,max_iter=1000,class_weight='balanced').fit(Rtr,y[tr])
    ho[t] = float(balanced_accuracy_score(y[te], c.predict(Rte)))
ho_vals=[v for v in ho.values() if v is not None]; ho_mean=float(np.mean(ho_vals)) if ho_vals else 0.0
print("[held-out] " + " ".join(f"{t}={('%.3f'%v) if v is not None else 'NA'}" for t,v in ho.items()) + f" mean={ho_mean:.4f}")

report = dict(model=model_id, N=N, relabeled=flipped, incorrect=int(y.sum()),
    raw_ba=raw_ba, best_layer=int(bestL), hidden_BA=hid, ortho_BA=ortho_ba,
    controls=controls, control_max=ctrl_max, margin=margin,
    residual_BA=ortho_ba, heldout_qtype=ho, heldout_qtype_mean=ho_mean)

if RUN_PERM:
    rng=np.random.RandomState(0); pmax=[]; real=max(raw_ba.values())
    for i in range(NPERM):
        yp=rng.permutation(y); bas=[balanced_accuracy_score(yp,(raw_oof(L,yp)>=0).astype(int)) for L in SCAN]
        pmax.append(max(bas))
        if (i+1)%25==0: print(f"[perm] {i+1}/{NPERM} pmax={max(pmax):.3f}", flush=True)
    pmax=np.array(pmax); p=(np.sum(pmax>=real)+1)/(NPERM+1)
    report.update(perm_p_selection_aware=float(p), perm_max=float(pmax.max()), nperm=NPERM)
    print(f"[perm] p={p:.4f} perm_max={pmax.max():.4f}")

gates = dict(enough_data=(N>=800 and min(int(y.sum()),int((1-y).sum()))>=150),
  accuracy_floor=(hid>=0.75), margin_over_text=(margin>=0.15),
  residual_proof=(ortho_ba>=0.75), heldout_proof=(ho_mean>=0.75))
if RUN_PERM: gates['permutation_proof']=(report['perm_p_selection_aware']<0.001 if NPERM>=1000 else False)
report['gates']=gates; report['LICENSED']=bool(all(gates.values()))
print("[gates] " + " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k,v in gates.items()))
print(f"[VERDICT] LICENSED={report['LICENSED']}")
open(OUT,'w').write(json.dumps(report,indent=2,default=float))
print(f"[saved] {OUT}")
