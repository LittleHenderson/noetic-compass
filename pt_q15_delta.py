import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold

d0=np.load('/root/capture_hall_q15_v2_W0/enabled_predicate_w0_all_layers_dataset.npz',allow_pickle=True)
d1=np.load('/root/capture_hall_q15_v2_W1/enabled_predicate_w0_all_layers_dataset.npz',allow_pickle=True)
mask=d0['labels_challenge_mode']=='stale_majority_vote'
y=d0['labels_support_status'][mask]; yb=(y=='UNSUPPORTED').astype(int)
print(f"Q15 MV: {mask.sum()} S={sum(yb==0)} U={sum(yb==1)}")

for L in [14,16,18,20,22,24,26,27]:
    X0=d0['features'][mask,L,:]; X1=d1['features'][mask,L,:]
    sc=StandardScaler().fit(X0)
    rd=LogisticRegression(C=0.25,max_iter=1000,class_weight='balanced').fit(sc.transform(X0),yb).coef_[0]
    r0=sc.transform(X0)@rd; r1=sc.transform(X1)@rd; d01=r1-r0
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
    hs=[]; ts=[]
    for tr,te in cv.split(d01.reshape(-1,1),yb):
        # balanced accuracy = mean of per-class recall (NOT (acc+(1-acc))/2, which is always 0.5)
        tp=LogisticRegression(C=0.5,max_iter=2000).fit(np.zeros((len(tr),1)),yb[tr]).predict(np.zeros((len(te),1)))
        ts.append(((tp[yb[te]==1]==1).mean()+(tp[yb[te]==0]==0).mean())/2)
        hp=LogisticRegression(C=0.5,max_iter=2000).fit(d01[tr].reshape(-1,1),yb[tr]).predict(d01[te].reshape(-1,1))
        hs.append(((hp[yb[te]==1]==1).mean()+(hp[yb[te]==0]==0).mean())/2)
    tba=np.mean(ts); hba=np.mean(hs)
    print(f"L{L}: DELTA={hba:.4f} MAJ={tba:.4f} MARG={hba-tba:+.4f}")
