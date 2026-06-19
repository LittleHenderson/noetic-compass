#!/usr/bin/env python3
"""
LICENSE-gate evaluation for hidden-state hallucination detection (pre-answer).

Runs on the pod against the Qwen-1.5B captures. Everything is leakage-safe:
  - matched exact-prompt groups only (same prompt -> both labels)
  - GroupKFold (prompt groups never split across train/test)
  - the W0->W1 risk direction is trained INSIDE each train fold (no test leakage)
  - every text/metadata control is fit inside the train fold too

Gates evaluated: accuracy floor (delta BA>=0.75), margin over text (>=0.15 over the
MAX of all controls), grouped validation, residual-removal proof, held-out-topic proof.
Permutation (1000-shuffle, selection-aware) is a separate flag (--perm) so the fast
gates can be read first.

Usage on pod:  python3 lic_eval.py            # fast gates + JSON report
               python3 lic_eval.py --perm     # adds 1000-shuffle selection-aware p
"""
import sys, json, collections
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import GroupKFold
from sklearn.metrics import balanced_accuracy_score

W0='/root/capture_hall_q15_v2_W0/enabled_predicate_w0_all_layers_dataset.npz'
W1='/root/capture_hall_q15_v2_W1/enabled_predicate_w0_all_layers_dataset.npz'
SCAN_LAYERS=[12,14,16,18,20,22,24,26,27]
NSPL=5
RUN_PERM='--perm' in sys.argv
NPERM=1000

d0=np.load(W0,allow_pickle=True); d1=np.load(W1,allow_pickle=True)
prompts=d0['prompts'].astype(str)
sup=d0['labels_support_status'].astype(str)
topic=d0['labels_topic'].astype(str); domain=d0['labels_domain'].astype(str)
def getf(d,n,default=''):
    return d[n].astype(str) if n in d.files else np.array([default]*len(prompts))
retr=getf(d0,'labels_retrieval_condition'); rbucket=getf(d0,'labels_retrieval_score_bucket')
pref=getf(d1,'generated_prefix_texts')
plen=d0['prompt_token_counts'].astype(float) if 'prompt_token_counts' in d0.files else np.zeros(len(prompts))
prefn=d1['generated_prefix_token_counts'].astype(float) if 'generated_prefix_token_counts' in d1.files else np.zeros(len(prompts))

# ---- matched exact-prompt groups (same prompt produced both labels) ----
byp=collections.defaultdict(list)
for i,p in enumerate(prompts.tolist()): byp[p].append(i)
keep=sorted(i for p,idx in byp.items() if len({sup[j] for j in idx})==2 for i in idx)
keep=np.array(keep)
pid={p:k for k,p in enumerate(sorted(byp))}
groups=np.array([pid[prompts[i]] for i in keep])
y=(sup[keep]=='UNSUPPORTED').astype(int)
F0=d0['features'][keep]; F1=d1['features'][keep]
prompts_k=prompts[keep]; pref_k=pref[keep]; topic_k=topic[keep]; domain_k=domain[keep]
retr_k=retr[keep]; rb_k=rbucket[keep]
plen_k=plen[keep]; prefn_k=prefn[keep]
N=len(keep); ng=len(set(groups.tolist()))
print(f"[data] matched rows={N} groups={ng} U={int(y.sum())} S={int((1-y).sum())} topics={dict(collections.Counter(topic_k.tolist()))}")

def folds():
    return list(GroupKFold(n_splits=NSPL).split(np.zeros(N), y, groups))
FOLDS=folds()

# ---- the hidden-state delta detector (leakage-safe, per-fold direction) ----
def delta_ba(Lidx, yy, FF=FOLDS):
    bas=[]
    for tr,te in FF:
        sc=StandardScaler().fit(F0[tr,Lidx,:])
        rd=LogisticRegression(C=0.25,max_iter=1000,class_weight='balanced').fit(sc.transform(F0[tr,Lidx,:]),yy[tr]).coef_[0]
        dtr=(sc.transform(F1[tr,Lidx,:])@rd)-(sc.transform(F0[tr,Lidx,:])@rd)
        dte=(sc.transform(F1[te,Lidx,:])@rd)-(sc.transform(F0[te,Lidx,:])@rd)
        c=LogisticRegression(C=0.5,max_iter=2000).fit(dtr.reshape(-1,1),yy[tr])
        bas.append(balanced_accuracy_score(yy[te],c.predict(dte.reshape(-1,1))))
    return float(np.mean(bas))

per_layer={L:delta_ba(L,y) for L in SCAN_LAYERS}
bestL=max(per_layer,key=per_layer.get); hid=per_layer[bestL]
print(f"[hidden] per-layer delta BA: "+" ".join(f"L{L}={per_layer[L]:.4f}" for L in SCAN_LAYERS))
print(f"[hidden] best layer L{bestL} = {hid:.4f}")

# ---- text / metadata controls (all leakage-safe, GroupKFold) ----
def text_ba(texts, analyzer):
    bas=[]
    for tr,te in FOLDS:
        v=TfidfVectorizer(analyzer='word',max_features=3000) if analyzer=='word' else TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),max_features=8000)
        Xtr=v.fit_transform(texts[tr]); Xte=v.transform(texts[te])
        c=LogisticRegression(C=1.0,max_iter=3000,class_weight='balanced').fit(Xtr,y[tr])
        bas.append(balanced_accuracy_score(y[te],c.predict(Xte)))
    return float(np.mean(bas))
def cat_ba(*cols):
    arr=np.column_stack(cols)
    bas=[]
    for tr,te in FOLDS:
        oh=OneHotEncoder(handle_unknown='ignore').fit(arr[tr])
        c=LogisticRegression(C=1.0,max_iter=3000,class_weight='balanced').fit(oh.transform(arr[tr]),y[tr])
        bas.append(balanced_accuracy_score(y[te],c.predict(oh.transform(arr[te]))))
    return float(np.mean(bas))
def num_ba(M):
    bas=[]
    for tr,te in FOLDS:
        sc=StandardScaler().fit(M[tr]);
        c=LogisticRegression(C=1.0,max_iter=3000,class_weight='balanced').fit(sc.transform(M[tr]),y[tr])
        bas.append(balanced_accuracy_score(y[te],c.predict(sc.transform(M[te]))))
    return float(np.mean(bas))
def layer0_ba():
    bas=[]
    for tr,te in FOLDS:
        sc=StandardScaler().fit(F1[tr,0,:])
        c=LogisticRegression(C=0.5,max_iter=2000,class_weight='balanced').fit(sc.transform(F1[tr,0,:]),y[tr])
        bas.append(balanced_accuracy_score(y[te],c.predict(sc.transform(F1[te,0,:]))))
    return float(np.mean(bas))

controls={
 'prompt_word': text_ba(prompts_k,'word'),
 'prompt_char': text_ba(prompts_k,'char'),
 'genprefix_word': text_ba(pref_k,'word'),
 'genprefix_char': text_ba(pref_k,'char'),
 'token_identity': cat_ba(np.array([p.strip() for p in pref_k]).reshape(-1,1)),
 'layer0': layer0_ba(),
 'length': num_ba(np.column_stack([plen_k,prefn_k])),
 'topic': cat_ba(topic_k.reshape(-1,1)),
 'domain': cat_ba(domain_k.reshape(-1,1)),
 'retrieval_meta': cat_ba(retr_k.reshape(-1,1), rb_k.reshape(-1,1)),
}
best_ctrl=max(controls,key=controls.get); ctrl_max=controls[best_ctrl]
margin=hid-ctrl_max
print("[controls] "+" ".join(f"{k}={v:.4f}" for k,v in controls.items()))
print(f"[margin] hidden({hid:.4f}) - best_control({best_ctrl}={ctrl_max:.4f}) = {margin:+.4f}")

# ---- residual proof: remove text/prefix/meta info from the delta, re-test ----
def best_delta_vector(yy):
    # out-of-fold delta at bestL
    dvec=np.zeros(N)
    for tr,te in FOLDS:
        sc=StandardScaler().fit(F0[tr,bestL,:])
        rd=LogisticRegression(C=0.25,max_iter=1000,class_weight='balanced').fit(sc.transform(F0[tr,bestL,:]),yy[tr]).coef_[0]
        dvec[te]=(sc.transform(F1[te,bestL,:])@rd)-(sc.transform(F0[te,bestL,:])@rd)
    return dvec
dvec=best_delta_vector(y)
# build a text-information matrix (prefix char SVD + length + onehots)
def textinfo_matrix():
    v=TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),max_features=8000).fit_transform(pref_k)
    k=min(50, v.shape[1]-1) if v.shape[1]>1 else 1
    svd=TruncatedSVD(n_components=max(1,k)).fit_transform(v) if v.shape[1]>1 else np.zeros((N,1))
    oh=OneHotEncoder(handle_unknown='ignore').fit_transform(np.column_stack([topic_k,domain_k,retr_k,rb_k])).toarray()
    return np.column_stack([svd, plen_k, prefn_k, oh, F1[:,0,:] @ np.random.RandomState(0).randn(F1.shape[2], 30)])  # +layer0 random proj
TI=textinfo_matrix()
res_bas=[]
for tr,te in FOLDS:
    reg=LinearRegression().fit(TI[tr], dvec[tr])
    rtr=dvec[tr]-reg.predict(TI[tr]); rte=dvec[te]-reg.predict(TI[te])
    c=LogisticRegression(C=0.5,max_iter=2000).fit(rtr.reshape(-1,1),y[tr])
    res_bas.append(balanced_accuracy_score(y[te],c.predict(rte.reshape(-1,1))))
residual_ba=float(np.mean(res_bas))
print(f"[residual] delta BA after removing text/prefix/meta info = {residual_ba:.4f}")

# ---- held-out topic proof ----
ho={}
for t in sorted(set(topic_k.tolist())):
    tr=np.where(topic_k!=t)[0]; te=np.where(topic_k==t)[0]
    if len(set(y[te].tolist()))<2 or len(set(y[tr].tolist()))<2:
        ho[t]=None; continue
    sc=StandardScaler().fit(F0[tr,bestL,:])
    rd=LogisticRegression(C=0.25,max_iter=1000,class_weight='balanced').fit(sc.transform(F0[tr,bestL,:]),y[tr]).coef_[0]
    dtr=(sc.transform(F1[tr,bestL,:])@rd)-(sc.transform(F0[tr,bestL,:])@rd)
    dte=(sc.transform(F1[te,bestL,:])@rd)-(sc.transform(F0[te,bestL,:])@rd)
    c=LogisticRegression(C=0.5,max_iter=2000).fit(dtr.reshape(-1,1),y[tr])
    ho[t]=float(balanced_accuracy_score(y[te],c.predict(dte.reshape(-1,1))))
ho_vals=[v for v in ho.values() if v is not None]
ho_mean=float(np.mean(ho_vals)) if ho_vals else 0.0
print(f"[held-out-topic] per-topic BA: "+" ".join(f"{t}={('%.4f'%v) if v is not None else 'NA'}" for t,v in ho.items())+f" | mean={ho_mean:.4f}")

report=dict(model='Qwen2.5-1.5B-Instruct', window='W0->W1 delta (pre-answer)',
    matched_rows=N, groups=ng, unsupported=int(y.sum()), topics=dict(collections.Counter(topic_k.tolist())),
    scan_layers=SCAN_LAYERS, per_layer=per_layer, best_layer=int(bestL), hidden_BA=hid,
    controls=controls, best_control=best_ctrl, control_max=ctrl_max, margin=margin,
    residual_BA=residual_ba, heldout_topic=ho, heldout_topic_mean=ho_mean)

if RUN_PERM:
    rng=np.random.RandomState(0); pmax=[]; pbest=[]
    real_max=max(per_layer.values())
    for i in range(NPERM):
        yp=rng.permutation(y)
        bas=[delta_ba(L,yp) for L in SCAN_LAYERS]
        pmax.append(max(bas)); pbest.append(bas[SCAN_LAYERS.index(bestL)])
    pmax=np.array(pmax); pbest=np.array(pbest)
    p_sel=(np.sum(pmax>=real_max)+1)/(NPERM+1)
    p_naive=(np.sum(pbest>=per_layer[bestL])+1)/(NPERM+1)
    report.update(perm_p_selection_aware=float(p_sel), perm_p_naive=float(p_naive),
                  perm_max=float(pmax.max()), nperm=NPERM)
    print(f"[perm] selection-aware p={p_sel:.4f} naive p={p_naive:.4f} perm_max={pmax.max():.4f} (N={NPERM})")

# ---- gate verdict ----
gates=dict(
  enough_data=(int(y.sum())>=80 and ng>=40),
  accuracy_floor=(hid>=0.75),
  margin_over_text=(margin>=0.15),
  residual_proof=(residual_ba>=0.75),
  heldout_proof=(ho_mean>=0.75),
)
if RUN_PERM: gates['permutation_proof']=(report['perm_p_selection_aware']<0.001 if NPERM>=1000 else False)
report['gates']=gates
report['LICENSED']=all(gates.values())
print("[gates] "+" ".join(f"{k}={'PASS' if v else 'FAIL'}" for k,v in gates.items()))
print(f"[VERDICT] LICENSED={report['LICENSED']}")
open('/root/lic_report_q15.json','w').write(json.dumps(report,indent=2,default=float))
print("[saved] /root/lic_report_q15.json")
