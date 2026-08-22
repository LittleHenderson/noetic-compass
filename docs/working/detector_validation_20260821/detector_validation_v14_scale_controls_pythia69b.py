"""SCALE THE CONTROLS: framing-matched Operator-10 + construct-correct ^8/^9 on pythia-6.9b.

Owner-authorized paid A40 run. The two controls that LOST to surface at 160m (v12 Operator-10
colloquialism-confounded 0.500<0.550; v13 ^8/^9 construct-correct 0.667<0.833) re-run at 43x
scale, to test whether they beat the char-ngram surface baseline at scale the way VALENCE did
(valence only separated from surface at 6.9b: 0.938 vs 0.500). Direct transformers forward hooks,
NOT the attested engine (research data run, labeled as such). Emits one JSON between markers.
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

MODEL="EleutherAI/pythia-6.9b"
DEV="cuda" if torch.cuda.is_available() else "cpu"
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

# ---- Operator-10 framing-matched (v12): train canonical colloquialisms, test FRESH phrasings ----
OP_TRAIN={
 "^0":["The concept of justice is an idea in the mind","Infinity is a notion that exists only in thought","The number seven is an abstract idea","Freedom is a concept we hold in our heads","A perfect circle is an idea, never a real thing","The word tomorrow names an idea, not an object"],
 "^1":["She paid close attention to every word he said","He focused his full awareness on the problem","I made up my mind after thinking it over","Use your head and concentrate on the task","Her mind was alert and fully engaged","He noticed and became conscious of the sound"],
 "^2":["She was drawn to the painting like a moth to a flame","He simply could not resist the warm invitation","The idea speaks to me and I love it","I feel a strong pull toward that plan","They were attracted to the cheerful music","It appeals to me deeply and I want it"],
 "^3":["He could not stomach the cruel remark","That attitude rubs me the wrong way","I would not touch that scheme with a ten-foot pole","She was repelled by the rotten smell","The plan is repugnant and I recoil from it","They were disgusted and pulled away"],
 "^4":["The speech struck a chord deep within her","That story hit me hard and stayed with me","His words resonated and left an impression","The melody vibrated through the whole room","It made a lasting impression on the audience","The idea reverberated in his thoughts for days"],
 "^5":["We are each the sum of our experiences","Everything I have lived through made me who I am","Her character was shaped by years of hardship","His expertise is built from a lifetime of practice","The person you are is your accumulated past","My beliefs formed slowly from all I have seen"],
 "^6":["Let us break the argument down into its parts","She unpacked the idea to see what was inside","He took the theory apart piece by piece","The proof decomposes into three separate lemmas","We analyzed the plan by dividing it into steps","Pull the concept apart and examine each component"],
 "^7":["Practice makes perfect if you repeat it daily","You are what you repeatedly do every day","Through constant drilling it became muscle memory","She got into a steady groove of writing each morning","Repetition slowly conditioned the habit","Doing it over and over trained the reflex"],
 "^8":["That reminds me of a trip we took long ago","The smell of rain triggered a childhood memory","One thing led to another and I recalled her name","Seeing the photo made me think of my father","The song brought an old summer to mind","His comment sparked a completely different thought"],
 "^9":["The answer just popped into my head","Out of nowhere the solution came to me","Suddenly it clicked and I understood","The thought arrived unbidden in my mind","The name finally surfaced on its own","All at once the memory came to me"]}
OP_TEST={
 "^0":["Democracy is not a thing you could ever hold in your hand","Seven has no colour, weight, or place; it lives only in thought"],
 "^1":["Every small sound in the room registered with her at once","He held the whole problem in view without letting any part slip"],
 "^2":["From the first glance she wanted the little blue house","He kept finding excuses to return to that one quiet cafe"],
 "^3":["After a single bite he quietly pushed the bowl aside","She found reasons to leave whenever that subject arose"],
 "^4":["The film sat with him, unshakeable, for a week afterward","Long after she spoke, her sentence kept returning to him"],
 "^5":["Every hardship she had survived was now folded into who she was","A lifetime at the workbench had become the man himself"],
 "^6":["He examined each assumption the whole theory was resting on","She separated the proposal into the smaller claims it was made of"],
 "^7":["By the thousandth time, his hands moved without a single thought","Morning after morning of it wore the habit smooth and automatic"],
 "^8":["The scent of pine tar pulled a whole childhood winter back up","One look at the old photo and his father was suddenly present again"],
 "^9":["With no warning at all, the finished solution was simply there","The forgotten name arrived on its own, asked for by nothing"]}

# ---- ^8/^9 construct-correct + giveaway-free (v13) ----
CE_TRAIN={
 "^8":OP_TRAIN["^8"], "^9":OP_TRAIN["^9"]}
CE_TEST={
 "^8":["The worn leather seat carried him straight back to his grandfather's garage",
       "A few bars of that old tune and the whole summer stood in front of her again",
       "The scent of chalk dust set a classroom from thirty years ago alight for him",
       "One taste of the broth and her mother's kitchen rose up around her",
       "The creak of that gate swung open his entire childhood",
       "A stranger's cologne on the train and his first love was there once more"],
 "^9":["Halfway through dinner, the missing word was simply there",
       "In the small hours the whole answer lay finished in her thoughts",
       "Without her reaching for it, the man's name settled into place",
       "The solution he had chased for weeks was suddenly, quietly present",
       "Between one step and the next, the plan assembled itself complete",
       "The forgotten address rose up on its own, wanted by nothing"]}

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
    ok=tot=0;per={c:[0,0] for c in trm}
    for c,items in tem.items():
        for x in items:
            v=f(x);pred=min(cent,key=lambda k:np.linalg.norm(v-cent[k]));ok+=(pred==c);tot+=1;per[c][0]+=(pred==c);per[c][1]+=1
    return ok/tot,per

def run_control(TRAIN,TEST,chance,name):
    cls=list(TRAIN)
    for c in cls:
        for s in TRAIN[c]+TEST[c]: R(s)
    best=(-1,None,None)
    for li in range(NL):
        tr={c:[R(s)[li] for s in TRAIN[c]] for c in cls}
        te={c:[R(s)[li] for s in TEST[c]] for c in cls}
        a,per=nc(tr,te,lambda v:v)
        if a>best[0]: best=(a,li,per)
    act,layer,per=best
    voc=voc_of([s for c in cls for s in TRAIN[c]])
    ng,ngper=nc({c:list(TRAIN[c]) for c in cls},{c:list(TEST[c]) for c in cls},lambda x:cngram(x,voc))
    return {"name":name,"chance":chance,"activation":round(act,3),"best_layer":layer,
            "char_ngram_surface":round(ng,3),"activation_minus_surface":round(act-ng,3),
            "activation_beats_surface":bool(act>ng),
            "activation_per_class":{c:f"{per[c][0]}/{per[c][1]}" for c in cls},
            "surface_per_class":{c:f"{ngper[c][0]}/{ngper[c][1]}" for c in cls}}

res={"model":MODEL,"layers":NL,"hidden":H,"transformers_version":transformers.__version__,"torch_version":torch.__version__}
res["operator10_framingmatched"]=run_control(OP_TRAIN,OP_TEST,0.10,"Operator-10 framing-matched (train colloquial, test fresh)")
res["cause_effect_constructcorrect"]=run_control(CE_TRAIN,CE_TEST,0.50,"^8/^9 construct-correct + giveaway-free")
print("<<<RESULTS_JSON>>>")
print(json.dumps(res))
print("<<<END_RESULTS_JSON>>>")
