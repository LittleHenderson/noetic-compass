import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

d0=np.load('/root/capture_W0_v2_mv/enabled_predicate_w0_all_layers_dataset.npz',allow_pickle=True)
d1=np.load('/root/capture_W1_v2_mv/enabled_predicate_w0_all_layers_dataset.npz',allow_pickle=True)
y=d0['labels_support_status']; yb=(y=='UNSUPPORTED').astype(int)
rd=np.load('/root/cas_hallucination_direction_L14.npy')
sm=np.load('/root/cas_hallucination_scaler_mean_L14.npy')
ss=np.load('/root/cas_hallucination_scaler_scale_L14.npy')
r0=((d0['features'][:,14,:]-sm)/ss)@rd
r1=((d1['features'][:,14,:]-sm)/ss)@rd
d01=r1-r0
cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
ts=[]; hs=[]
for tr,te in cv.split(d01.reshape(-1,1),yb):
    ct=LogisticRegression(C=0.5,max_iter=2000).fit(np.zeros((len(tr),1)),yb[tr])
    tp=ct.predict(np.zeros((len(te),1)))
    ts.append(((tp[yb[te]==1]==1).mean()+(tp[yb[te]==0]==0).mean())/2)
    ch=LogisticRegression(C=0.5,max_iter=2000).fit(d01[tr].reshape(-1,1),yb[tr])
    hp=ch.predict(d01[te].reshape(-1,1))
    hs.append(((hp[yb[te]==1]==1).mean()+(hp[yb[te]==0]==0).mean())/2)
tba=np.mean(ts); hba=np.mean(hs)
print(f"TEXT(maj): {tba:.4f}  DELTA: {hba:.4f}  MARGIN: {hba-tba:+.4f}")
print("DELTA WINS" if hba-tba>0.15 else "TEXT WINS" if hba<=tba else "CLOSE")
real=hba; pm=[]
for _ in range(100):
    yp=np.random.permutation(yb); ss=[]
    for tr,te in cv.split(d01.reshape(-1,1),yp):
        pp=LogisticRegression(C=0.5,max_iter=2000).fit(d01[tr].reshape(-1,1),yp[tr]).predict(d01[te].reshape(-1,1))
        # balanced accuracy under the permuted labels (per-class recall), not the constant-0.5 form
        ss.append(((pp[yp[te]==1]==1).mean()+(pp[yp[te]==0]==0).mean())/2)
    pm.append(np.mean(ss))
pv=(sum(s>=real for s in pm)+1)/101
print(f"p={pv:.4f} max_perm={max(pm):.4f} margin={real-max(pm):.4f}")
