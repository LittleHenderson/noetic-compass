"""DECISIVE NULL: is CAS-Domain a PRIVILEGED partition at 6.9b? (owner-authorized paid A40)

Fixes v18's three confounds: (1) 6.9b (activation clears surface); (2) framing-STRIPPED stimuli
(domain giveaway markers removed, so domain surface is low -- no ceiling asymmetry from stereotyped
markers); (3) report the ceiling-NORMALIZED metric (act-surf)/(1-surf) alongside raw, with every
partition's surface shown, so the reader sees whether surfaces overlap. 8 topics x 4 CAS-Domains =
32 framing-stripped sentences. Compare how well activations separate the CAS-Domain partition vs
non-CAS partitions (topic-pairings, sentence-length) of the SAME sentences. Direct transformers,
NOT the attested engine. Emits one JSON between markers.

Honest residual caveat (recorded, not hidden): framing-stripping removes DOMAIN markers but not
TOPIC markers, so topic partitions keep a lexical signature -- the normalized metric is the
comparator, and surfaces are reported for transparency.
"""
import sys, json, subprocess
def pip(*a):
    subprocess.run([sys.executable,"-m","pip","install","-q","--break-system-packages",*a],check=False)
try:
    import transformers
except Exception:
    pip("transformers"); import transformers
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
print(f"transformers {transformers.__version__}, torch {torch.__version__}", file=sys.stderr, flush=True)
MODEL="EleutherAI/pythia-6.9b"; DEV="cuda" if torch.cuda.is_available() else "cpu"
print(f"loading {MODEL} on {DEV} ...", file=sys.stderr, flush=True)
tok=AutoTokenizer.from_pretrained(MODEL)
try:
    model=AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).to(DEV).eval()
except TypeError:
    model=AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16).to(DEV).eval()
NL=model.config.num_hidden_layers; H=model.config.hidden_size
print(f"loaded. layers={NL} hidden={H}", file=sys.stderr, flush=True)
_layers=model.gpt_neox.layers
def resid_all(prompt):
    grabbed={}; hooks=[]
    def mk(i):
        def hook(m,inp,out):
            hs=out[0] if isinstance(out,tuple) else out
            grabbed[i]=hs[0,-1,:].detach().float().cpu().numpy()
        return hook
    for i,l in enumerate(_layers): hooks.append(l.register_forward_hook(mk(i)))
    with torch.no_grad():
        ids=tok(prompt,return_tensors="pt").to(DEV); model(**ids)
    for h in hooks: h.remove()
    return np.stack([grabbed[i] for i in range(NL)]).astype(np.float64)

DOMS=["P","C","E","O"]
# 8 topics x 4 domains, FRAMING-STRIPPED (P by action not modals; C plain fact; E no superlatives; O no first/then)
GRID={
 "aviation":{"P":"The captain reported the cracked windscreen instead of flying on to stay on schedule","C":"A jet engine pushes air backward to drive the aircraft forward","E":"The crew handled the storm in a way that put every passenger at ease","O":"Lower the landing gear. Line up with the runway. Ease back on the throttle."},
 "carpentry":{"P":"The carpenter turned the job down rather than build with timber he knew was rotten","C":"Oak is denser and heavier than pine of the same size","E":"The finish on that cabinet is a pleasure to run your hand across","O":"Measure the plank twice. Cut along the marked line. Sand the edge smooth."},
 "banking":{"P":"The teller flagged the odd transfer even though it slowed the line behind her","C":"A savings account pays interest on the money that is held in it","E":"Working with that advisor left the family feeling genuinely looked after","O":"Enter the amount. Confirm the account number. Approve the transfer."},
 "teaching":{"P":"The teacher reported the leaked exam rather than let the result stand","C":"The alphabet used to write English is made up of twenty six letters","E":"Her class was the part of the day the children looked forward to","O":"Hand out the worksheets. Read the instructions aloud. Collect the answers at the end."},
 "astronomy":{"P":"The astronomer published the null result even though it undercut her own famous prediction","C":"Light from the sun takes about eight minutes to reach the Earth","E":"The view through that telescope was one you would not soon forget","O":"Uncap the lens. Align the finder scope. Bring the star into focus."},
 "plumbing":{"P":"The plumber replaced the corroded pipe he found rather than paper over it and move on","C":"Water expands as it freezes, which is why unprotected pipes can burst","E":"The way he sealed that joint was a quietly satisfying piece of work","O":"Shut off the mains valve. Drain the line. Fit the new washer."},
 "retail":{"P":"The clerk pointed out the cheaper equivalent instead of ringing up the pricier item","C":"A barcode encodes a product number as a pattern of light and dark bars","E":"Shopping in that little store was a pleasure you looked forward to","O":"Scan each item. Total the basket. Hand back the change."},
 "coaching":{"P":"The coach benched his star player for the foul rather than let the win excuse it","C":"A muscle grows stronger by repairing the tiny tears that exercise causes","E":"Her sessions were the hour of the week the team most looked forward to","O":"Warm up the legs. Drill the passing. Cool down with a slow jog."}}
TOPICS=list(GRID)
ITEMS=[(GRID[t][d],t,d) for t in TOPICS for d in DOMS]  # 32
SENTS=[x[0] for x in ITEMS]
R=[resid_all(s) for s in SENTS]

def cngram(t,voc):
    t=t.lower();c={}
    for n in (2,3,4):
        for i in range(len(t)-n+1):c[t[i:i+n]]=c.get(t[i:i+n],0)+1
    v=np.array([c.get(g,0) for g in voc],dtype=np.float64);z=np.linalg.norm(v);return v/z if z>0 else v
def voc_of(idx):
    s=set()
    for i in idx:
        t=SENTS[i].lower()
        for n in (2,3,4):
            for j in range(len(t)-n+1):s.add(t[j:j+n])
    return sorted(s)
def part_domain(): return {i:ITEMS[i][2] for i in range(32)}
def part_topicpair(pairs):
    lab={}
    for gi,pair in enumerate(pairs):
        for i in range(32):
            if ITEMS[i][1] in pair: lab[i]=f"G{gi}"
    return lab
def part_lenq():
    order=sorted(range(32),key=lambda i:len(SENTS[i])); lab={}
    for rank,i in enumerate(order): lab[i]=f"Q{rank//8}"
    return lab
PARTS={"CAS_domain":part_domain(),
 "topicpair_A":part_topicpair([("aviation","carpentry"),("banking","teaching"),("astronomy","plumbing"),("retail","coaching")]),
 "topicpair_B":part_topicpair([("aviation","banking"),("carpentry","astronomy"),("teaching","retail"),("plumbing","coaching")]),
 "topicpair_C":part_topicpair([("aviation","plumbing"),("carpentry","retail"),("banking","astronomy"),("teaching","coaching")]),
 "sentence_length_quartile":part_lenq()}
def nc_split(labels,tr,te,feat):
    classes=sorted(set(labels.values())); cent={}
    for c in classes:
        mem=[i for i in tr if labels[i]==c]
        if not mem: return None
        cent[c]=np.mean([feat(i) for i in mem],axis=0)
    ok=sum(min(cent,key=lambda k:np.linalg.norm(feat(i)-cent[k]))==labels[i] for i in te)
    return ok/len(te)
Rsplits=20; rng=np.random.default_rng(20260821)
splits=[]
for _ in range(Rsplits):
    perm=rng.permutation(32); splits.append((sorted(perm[:24].tolist()),sorted(perm[24:].tolist())))
res={"model":MODEL,"layers":NL,"hidden":H,"transformers_version":transformers.__version__,"torch_version":torch.__version__,
     "note":"framing-STRIPPED 8x4 grid; primary comparator is ceiling-normalized (act-surf)/(1-surf); surfaces reported for transparency; residual confound: stripping removes DOMAIN markers not TOPIC markers",
     "chance":0.25,"n_items":32,"R_splits":Rsplits,"partitions":{}}
for name,labels in PARTS.items():
    aa=[];sa=[]
    for tr,te in splits:
        best=-1
        for li in range(NL):
            a=nc_split(labels,tr,te,lambda i:R[i][li])
            if a is not None and a>best: best=a
        aa.append(best); voc=voc_of(tr); sa.append(nc_split(labels,tr,te,lambda i:cngram(SENTS[i],voc)) or 0.0)
    act=float(np.mean(aa)); surf=float(np.mean(sa))
    norm=(act-surf)/(1-surf) if surf<1 else 0.0
    res["partitions"][name]={"activation":round(act,3),"activation_std":round(float(np.std(aa)),3),
        "surface":round(surf,3),"act_minus_surface":round(act-surf,3),"normalized_gain":round(float(norm),3)}
cas=res["partitions"]["CAS_domain"]; noncas={k:v for k,v in res["partitions"].items() if k!="CAS_domain"}
nc_norm=[v["normalized_gain"] for v in noncas.values()]; nc_act=[v["activation"] for v in noncas.values()]
res["cas_normalized_gain"]=cas["normalized_gain"]; res["noncas_normalized_gain_max"]=round(max(nc_norm),3); res["noncas_normalized_gain_mean"]=round(float(np.mean(nc_norm)),3)
res["cas_activation"]=cas["activation"]; res["noncas_activation_max"]=round(max(nc_act),3)
res["cas_surface"]=cas["surface"]; res["noncas_surface_range"]=[round(min(v["surface"] for v in noncas.values()),3),round(max(v["surface"] for v in noncas.values()),3)]
res["cas_privileged_normalized"]=bool(cas["normalized_gain"]>max(nc_norm))
res["verdict"]=("CAS_PRIVILEGED_NORMALIZED" if res["cas_privileged_normalized"] else "CAS_NOT_PRIVILEGED_NORMALIZED")
print("<<<RESULTS_JSON>>>")
print(json.dumps(res))
print("<<<END_RESULTS_JSON>>>")
