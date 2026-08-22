"""Scale test: the CAS detector suite on pythia-6.9b (real weights, GPU).

Runs on a rented A40. Direct transformers capture (residual stream via forward hooks) --
NOT the attested-engine wrapper (that wrapper is for canary integrity; this is a research
data run, labeled as such). Same detector logic as the local pythia-160m v-series so the
comparison is apples-to-apples. Emits one JSON to stdout between markers.
"""
import sys, json, subprocess
def pip(*args):
    # PEP 668 (Debian externally-managed): the pod's system Python refuses plain installs.
    # The pod is disposable, so --break-system-packages is fine here.
    subprocess.run([sys.executable,"-m","pip","install","-q","--break-system-packages",*args],check=False)
try:
    import transformers  # noqa
except Exception:
    pip("transformers")
    import transformers  # raise loudly if the install did not take
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
print(f"transformers {transformers.__version__}, torch {torch.__version__}", file=sys.stderr, flush=True)

MODEL="EleutherAI/pythia-6.9b"
DEV="cuda" if torch.cuda.is_available() else "cpu"
print(f"loading {MODEL} on {DEV} ...", file=sys.stderr, flush=True)
tok=AutoTokenizer.from_pretrained(MODEL)
try:  # transformers 5.x uses dtype=, 4.x uses torch_dtype=
    model=AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).to(DEV).eval()
except TypeError:
    model=AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16).to(DEV).eval()
NL=model.config.num_hidden_layers; H=model.config.hidden_size
print(f"loaded. layers={NL} hidden={H}", file=sys.stderr, flush=True)

_layers=model.gpt_neox.layers
def resid_all(prompt):
    grabbed={}
    hooks=[]
    def mk(i):
        def hook(mod,inp,out):
            hs=out[0] if isinstance(out,tuple) else out
            grabbed[i]=hs[0,-1,:].detach().float().cpu().numpy()
        return hook
    for i,l in enumerate(_layers): hooks.append(l.register_forward_hook(mk(i)))
    with torch.no_grad():
        ids=tok(prompt,return_tensors="pt").to(DEV)
        model(**ids)
    for h in hooks: h.remove()
    return np.stack([grabbed[i] for i in range(NL)]).astype(np.float64)  # (layers,hidden)

def logits_with_add(prompt, layer, vec):
    v=torch.tensor(vec,dtype=torch.float16,device=DEV)
    def hook(mod,inp,out):
        if isinstance(out,tuple):
            hs=out[0]; hs[0,-1,:]=hs[0,-1,:]+v; return (hs,)+out[1:]
        out[0,-1,:]=out[0,-1,:]+v; return out
    h=_layers[layer].register_forward_hook(hook)
    with torch.no_grad():
        ids=tok(prompt,return_tensors="pt").to(DEV)
        lg=model(**ids).logits[0,-1,:].detach().float().cpu().numpy()
    h.remove(); return lg

# ---- stimuli (compact, same constructs as the 160m v-series) ----
VAL_EXP_POS=["I absolutely love this","This is wonderful and delightful","A fantastic and joyful day","The music was beautiful and uplifting","It tasted delicious and satisfying","A truly excellent result","The gift was charming and heartfelt","A gorgeous and serene view","She felt cheerful and glad","A splendid and pleasant evening"]
VAL_EXP_NEG=["I absolutely hate this","This is awful and disgusting","A terrible and miserable day","The music was grating and unbearable","It tasted rotten and revolting","A truly dreadful result","The insult was vicious and hurtful","A filthy and menacing view","She felt bitter and sad","A wretched and hostile evening"]
VAL_IMP_POS=["She opened the letter and saw she had been accepted","After years of trying they finally held their newborn","He crossed the finish line as the crowd rose to their feet","The test came back clear and the doctor smiled","They were reunited at the gate after the long deployment","Her name was the first one called for the prize","The jury foreman read the single word they had hoped for","The last payment cleared and the house was finally theirs"]
VAL_IMP_NEG=["She opened the letter and saw she had been rejected","After years of trying the treatment had failed once more","He collapsed before the finish line as the crowd fell silent","The test came back and the doctor looked away","They stood at the gate but no one came off the plane","Her name was the only one missing from the list","The jury foreman read the word they had feared","The final notice cleared out what little they had saved"]
CE_POS=[("Because the rain kept falling","cause"),("Since the alarm never rang","cause"),("Because the funding was cut","cause"),("Since the bridge had collapsed","cause"),("Because the yeast was fresh","cause"),("Since the drought had lasted months","cause"),("Because the password was leaked","cause"),("Since the engine had overheated","cause"),("Because the referee missed the foul","cause"),("Since the vaccine was distributed","cause")]
CE_EFF=[("so the streets were soon flooded","eff"),("and therefore she overslept badly","eff"),("so the whole project was cancelled","eff"),("and so the traffic was diverted","eff"),("so the bread rose beautifully","eff"),("and therefore the crops all failed","eff"),("so the account was quickly hijacked","eff"),("and so the car finally stalled","eff"),("so the goal was allowed to stand","eff"),("and therefore the outbreak subsided","eff")]
CE_IMP_CAUSE=["The dam upstream had burst overnight","A spark landed in the dry brush","The supplier doubled its prices","The virus mutated in the spring","The pilot ignored the warning light","The seeds were planted too late"]
CE_IMP_EFF=["The valley below lay under water by dawn","The whole hillside was ash by morning","The store shelves emptied within a week","Hospitals filled past capacity by June","The aircraft lost power over the ridge","The harvest came in thin and small"]
DOM={"P":["A cook must never serve food that is unsafe","A doctor must protect every patient's confidentiality","An advisor ought to disclose every conflict of interest","A witness has a duty to tell the whole truth","Athletes should never use banned substances","A gardener ought to avoid pesticides that harm bees","A traveller should respect the customs of every country","A performer should credit every artist they sample"],
     "C":["Water boils at one hundred degrees at sea level","The human heart has four chambers","Compound interest grows faster than simple interest","A contract requires offer, acceptance, and consideration","A marathon covers just over forty two kilometres","Photosynthesis converts sunlight into sugars","The Earth has twenty four standard time zones","An octave spans twelve equal semitones"],
     "E":["This risotto is the most delicious dish here","This treatment is far superior to the old one","This fund is a poor choice with high fees","This ruling is a brilliant piece of jurisprudence","That was the greatest comeback the sport has seen","This rose garden is the most breathtaking in the city","This coastal town is the loveliest I have visited","This symphony is a sublime masterpiece"],
     "O":["First dice the onion, then fry it until golden","First clean the wound, then apply the dressing","First open the account, then transfer the funds","First file the motion, then serve the notice","First stretch, then jog a slow warm-up lap","First loosen the soil, then plant the seed","First pack your bag, then check in online","First tune the strings, then set the tempo"]}
OPS={"^0":["The concept of justice is an idea in the mind","Infinity is a notion that exists only in thought","The number seven is an abstract idea","Freedom is a concept we hold in our heads","A perfect circle is an idea not a real thing","The word tomorrow names an idea not an object"],
 "^1":["She paid close attention to every word","He focused his full awareness on the problem","I made up my mind after thinking it over","Use your head and concentrate on the task","Her mind was alert and fully engaged","He noticed and became conscious of the sound"],
 "^2":["She was drawn to it like a moth to a flame","He could not resist the warm invitation","The idea speaks to me and I love it","I feel a strong pull toward that plan","They were attracted to the cheerful music","It appeals to me deeply and I want it"],
 "^3":["He could not stomach the cruel remark","That attitude rubs me the wrong way","I would not touch that scheme with a pole","She was repelled by the rotten smell","The plan is repugnant and I recoil from it","They were disgusted and pulled away"],
 "^4":["The speech struck a chord deep within her","That story hit me hard and stayed with me","His words resonated and left an impression","The melody vibrated through the whole room","It made a lasting impression on the audience","The idea reverberated in his thoughts for days"],
 "^5":["We are each the sum of our experiences","Everything I lived through made me who I am","Her character was shaped by years of hardship","His skill is built from a lifetime of practice","The person you are is your accumulated past","My beliefs formed slowly from all I have seen"],
 "^6":["Let us break the argument into its parts","She unpacked the idea to see what was inside","He took the theory apart piece by piece","The proof decomposes into three lemmas","We analyzed the plan by dividing it into steps","Pull the concept apart and examine each part"],
 "^7":["Practice makes perfect if you repeat it daily","You are what you repeatedly do every day","Through constant drilling it became muscle memory","She got into a steady groove each morning","Repetition slowly conditioned the habit","Doing it over and over trained the reflex"],
 "^8":["That reminds me of a trip long ago","The smell of rain triggered a memory","One thing led to another and I recalled it","Seeing the photo made me think of my father","The song brought an old summer to mind","His comment sparked a different thought"],
 "^9":["The answer just popped into my head","Out of nowhere the solution came to me","Suddenly it clicked and I understood","The thought arrived unbidden in my mind","The name finally surfaced on its own","All at once the memory came to me"]}

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
def nc(trainmap,testmap,feat):
    cent={c:np.mean([feat(x) for x in trainmap[c]],axis=0) for c in trainmap}
    ok=tot=0
    for c,items in testmap.items():
        for x in items:
            v=feat(x);pred=min(cent,key=lambda k:np.linalg.norm(v-cent[k]));ok+=(pred==c);tot+=1
    return ok/tot

# cache residuals
CACHE={}
def R(p):
    if p not in CACHE: CACHE[p]=resid_all(p)
    return CACHE[p]

res={"model":MODEL,"layers":NL,"hidden":H,"transformers_version":transformers.__version__,"torch_version":torch.__version__}

# ---- 2-class axes: valence & cause-effect, cross-register + surface control ----
def two_class(train_pos,train_neg,test_pos,test_neg,name):
    best=(-1,None)
    for li in range(NL):
        tr={"pos":[R(p)[li] for p in train_pos],"neg":[R(p)[li] for p in train_neg]}
        te={"pos":[R(p)[li] for p in test_pos],"neg":[R(p)[li] for p in test_neg]}
        a=nc(tr,te,lambda v:v)
        if a>best[0]:best=(a,li)
    voc=voc_of(train_pos+train_neg)
    ng=nc({"pos":train_pos,"neg":train_neg},{"pos":test_pos,"neg":test_neg},lambda x:cngram(x,voc))
    return {"activation":round(best[0],3),"best_layer":best[1],"char_ngram_surface":round(ng,3)}

# valence cross-register (train explicit, test implicit) = the surface-control question at scale
res["valence_surface_control"]=two_class(VAL_EXP_POS,VAL_EXP_NEG,VAL_IMP_POS,VAL_IMP_NEG,"valence")
res["cause_effect_surface_control"]=two_class([x[0] for x in CE_POS],[x[0] for x in CE_EFF],CE_IMP_CAUSE,CE_IMP_EFF,"ce")

# ---- multi-class: Domain-4 (train 6/test 2 by index) & Operator-10 (4/2) + surface ----
def multi(classmap,ntr,name,chance):
    best=(-1,None)
    for li in range(NL):
        tr={c:[R(classmap[c][i])[li] for i in range(ntr)] for c in classmap}
        te={c:[R(classmap[c][i])[li] for i in range(ntr,len(classmap[c]))] for c in classmap}
        a=nc(tr,te,lambda v:v)
        if a>best[0]:best=(a,li)
    voc=voc_of([classmap[c][i] for c in classmap for i in range(ntr)])
    trx={c:[classmap[c][i] for i in range(ntr)] for c in classmap};tex={c:[classmap[c][i] for i in range(ntr,len(classmap[c]))] for c in classmap}
    ng=nc(trx,tex,lambda x:cngram(x,voc))
    return {"activation":round(best[0],3),"best_layer":best[1],"char_ngram_surface":round(ng,3),"chance":chance}
res["domain4"]=multi(DOM,6,"domain4",0.25)
res["operator10"]=multi(OPS,4,"operator10",0.10)

# ---- causal steering of the valence direction (v8 at scale) ----
li=best_layer=res["valence_surface_control"]["best_layer"] or NL//2
mu_p=np.mean([R(p)[li] for p in VAL_EXP_POS],axis=0);mu_n=np.mean([R(p)[li] for p in VAL_EXP_NEG],axis=0)
w=mu_p-mu_n;w=w/np.linalg.norm(w)*6.0
POS=[" good"," great"," wonderful"," amazing"];NEG=[" bad"," terrible"," awful"," horrible"]
def tid(x):
    e=tok.encode(x);return e[0] if len(e)==1 else None
pid=[tid(x) for x in POS if tid(x) is not None];nid=[tid(x) for x in NEG if tid(x) is not None]
NEUT=["Overall, the situation was","My honest assessment is that it was","In the end it turned out to be","When it was all over, things felt"]
def margin(lg):return float(np.mean([lg[i] for i in pid])-np.mean([lg[i] for i in nid]))
sw=[margin(logits_with_add(p,li,w))-margin(logits_with_add(p,li,-w)) for p in NEUT]
rng=np.random.default_rng(1729);null=[]
for k in range(12):
    r=rng.standard_normal(w.shape);r=r/np.linalg.norm(r)*6.0
    null.append(np.mean([margin(logits_with_add(p,li,r))-margin(logits_with_add(p,li,-r)) for p in NEUT]))
null=np.array(null)
res["causal_valence"]={"layer":li,"swing":round(float(np.mean(sw)),3),"per_prompt":[round(x,2) for x in sw],
    "null_mean":round(float(null.mean()),3),"null_max_abs":round(float(np.abs(null).max()),3),
    "z_over_null":round(float((np.mean(sw)-null.mean())/(null.std()+1e-9)),2),
    "directional_all_positive":bool(all(s>0 for s in sw))}

print("<<<RESULTS_JSON>>>")
print(json.dumps(res))
print("<<<END_RESULTS_JSON>>>")
