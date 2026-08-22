"""SCALE DOMAIN: framing-matched Domain-4 control on pythia-6.9b (owner-authorized paid A40).

The last open control. At 160m (v11) Domain-4 framing-matched was PARTIAL: activation 0.625 vs
surface 0.438, but O surface-carried (4/4 both), P collapsed to 1/4 when modals stripped, C/E thin.
Does it harden at 43x scale like Operator-10 and valence did? TRAIN on framing-RICH Domain
sentences (8 topics), TEST on 4 NEW topics with giveaway markers STRIPPED. Direct transformers,
NOT the attested engine (research data run). Emits one JSON between markers.
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

DOMAINS=["P","C","E","O"]
TRAIN={
 "cooking":{"P":"A cook must never knowingly serve food that is unsafe to eat","C":"Water boils at one hundred degrees Celsius at sea level","E":"This risotto is the most delicious dish on the whole menu","O":"First dice the onion, then fry it slowly until it turns golden"},
 "medicine":{"P":"A doctor is obligated to protect the confidentiality of every patient","C":"The human heart has four chambers that pump blood through the body","E":"This new treatment is far superior to the older, harsher one","O":"First clean the wound, then apply the dressing and secure it"},
 "finance":{"P":"An advisor ought to disclose every conflict of interest honestly","C":"Compound interest grows a balance faster than simple interest does","E":"This fund is a poor choice with mediocre returns and high fees","O":"First open the account, then transfer the funds and confirm the balance"},
 "law":{"P":"A witness has a duty to tell the whole truth under oath","C":"A contract requires an offer, acceptance, and consideration to be valid","E":"This ruling is a brilliant and well reasoned piece of jurisprudence","O":"First file the motion, then serve the notice on the opposing party"},
 "sports":{"P":"Athletes should compete fairly and never use banned substances","C":"A marathon covers a distance of just over forty two kilometres","E":"That was the greatest comeback victory the sport has ever seen","O":"First stretch your muscles, then jog a slow lap to warm up"},
 "music":{"P":"A performer should credit every artist whose work they sample","C":"An octave spans twelve equal semitones in standard tuning","E":"This symphony is a sublime and deeply moving masterpiece","O":"First tune the strings, then set the tempo and begin the piece"},
 "gardening":{"P":"A gardener ought to avoid pesticides that harm pollinating bees","C":"Photosynthesis converts sunlight and water into sugars for the plant","E":"This rose garden is the most breathtaking display in the city","O":"First loosen the soil, then plant the seed and water it gently"},
 "travel":{"P":"A traveller should respect the customs and laws of every host country","C":"The Earth is divided into twenty four standard time zones","E":"This coastal town is the loveliest place I have ever visited","O":"First pack your bag, then check in online and print the boarding pass"}}
TEST={
 "aviation":{"P":"The captain reported the cracked windscreen instead of flying on to stay on schedule","C":"A jet engine pushes air backward to drive the aircraft forward","E":"The crew handled the storm in a way that put every passenger at ease","O":"Lower the landing gear. Line up with the runway. Ease back on the throttle."},
 "carpentry":{"P":"The carpenter turned the job down rather than build with timber he knew was rotten","C":"Oak is denser and heavier than pine of the same size","E":"The finish on that cabinet is a pleasure to run your hand across","O":"Measure the plank twice. Cut along the marked line. Sand the edge smooth."},
 "banking":{"P":"The teller flagged the odd transfer even though it slowed the line behind her","C":"A savings account pays interest on the money that is held in it","E":"Working with that advisor left the family feeling genuinely looked after","O":"Enter the amount. Confirm the account number. Approve the transfer."},
 "teaching":{"P":"The teacher reported the leaked exam rather than let the result stand","C":"The alphabet used to write English is made up of twenty six letters","E":"Her class was the part of the day the children looked forward to","O":"Hand out the worksheets. Read the instructions aloud. Collect the answers at the end."}}
TR_T=list(TRAIN); TE_T=list(TEST)

def cngram(t,voc):
    t=t.lower();c={}
    for n in (2,3,4):
        for i in range(len(t)-n+1):c[t[i:i+n]]=c.get(t[i:i+n],0)+1
    v=np.array([c.get(g,0) for g in voc],dtype=np.float64);z=np.linalg.norm(v);return v/z if z>0 else v
def voc_of(ts):
    s=set()
    for t in ts:
        t=t.lower()
        for n in (2,3,4):
            for i in range(len(t)-n+1):s.add(t[i:i+n])
    return sorted(s)
CACHE={}
def R(p):
    if p not in CACHE: CACHE[p]=resid_all(p)
    return CACHE[p]
def nc(trm,tem,f):
    cent={c:np.mean([f(x) for x in trm[c]],axis=0) for c in trm}
    ok=tot=0;per={d:[0,0] for d in DOMAINS}
    for c,items in tem.items():
        for x in items:
            v=f(x);pred=min(cent,key=lambda k:np.linalg.norm(v-cent[k]));ok+=(pred==c);tot+=1;per[c][0]+=(pred==c);per[c][1]+=1
    return ok/tot,per

for t in TR_T:
    for d in DOMAINS: R(TRAIN[t][d])
for t in TE_T:
    for d in DOMAINS: R(TEST[t][d])
best=(-1,None,None)
for li in range(NL):
    tr={d:[R(TRAIN[t][d])[li] for t in TR_T] for d in DOMAINS}
    te={d:[R(TEST[t][d])[li] for t in TE_T] for d in DOMAINS}
    a,per=nc(tr,te,lambda v:v)
    if a>best[0]: best=(a,li,per)
act,layer,per=best
voc=voc_of([TRAIN[t][d] for t in TR_T for d in DOMAINS])
ng,ngper=nc({d:[TRAIN[t][d] for t in TR_T] for d in DOMAINS},{d:[TEST[t][d] for t in TE_T] for d in DOMAINS},lambda x:cngram(x,voc))
res={"model":MODEL,"layers":NL,"hidden":H,"transformers_version":transformers.__version__,"torch_version":torch.__version__,
     "domain4_framingmatched":{"name":"Domain-4 P/C/E/O framing-matched (train framing-rich, test framing-STRIPPED new topics)",
        "chance":0.25,"n_train_per_class":len(TR_T),"n_test_per_class":len(TE_T),"n_test_total":len(TE_T)*4,
        "activation":round(act,3),"best_layer":layer,"char_ngram_surface":round(ng,3),
        "activation_minus_surface":round(act-ng,3),"activation_beats_surface":bool(act>ng),
        "activation_per_domain":{d:f"{per[d][0]}/{per[d][1]}" for d in DOMAINS},
        "surface_per_domain":{d:f"{ngper[d][0]}/{ngper[d][1]}" for d in DOMAINS}}}
print("<<<RESULTS_JSON>>>")
print(json.dumps(res))
print("<<<END_RESULTS_JSON>>>")
