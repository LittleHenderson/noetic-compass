"""SCALE CAUSAL: is the valence direction a causal LEVER at 6.9b? (owner-authorized paid A40)

The v10/v14 causal came out null ONLY because alpha=6.0 (tuned for 160m's 768-dim residual) is
negligible in 6.9b's 4096-dim residual. Fix: inject the NATURAL-magnitude valence direction
w_raw = mean(explicit-pos) - mean(explicit-neg) at the layer, and SWEEP a multiplier m in
{1,2,4,8}. For each layer x m: measure the valence-margin swing on neutral prompts under +m*w_raw
vs -m*w_raw, against a norm-MATCHED random-direction null (K=8). Reports the residual norm for
context and the swing/z curve. CONFIRMS the CORRECTION half of Claim B iff swing rises with m,
is directionally correct, and clears the matched-random null. Direct transformers, NOT the
attested engine (research data run). Emits one JSON between markers.
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

def logits_with_add(prompt, layer, vec):
    v=torch.tensor(vec,dtype=torch.float16,device=DEV)
    def hook(m,inp,out):
        if isinstance(out,tuple):
            hs=out[0]; hs[0,-1,:]=hs[0,-1,:]+v; return (hs,)+out[1:]
        out[0,-1,:]=out[0,-1,:]+v; return out
    h=_layers[layer].register_forward_hook(hook)
    with torch.no_grad():
        ids=tok(prompt,return_tensors="pt").to(DEV)
        lg=model(**ids).logits[0,-1,:].detach().float().cpu().numpy()
    h.remove(); return lg

EXPL_POS=["I absolutely love this","This is wonderful and delightful","A fantastic and joyful day","The music was beautiful and uplifting","It tasted delicious and satisfying","A truly excellent result","The gift was charming and heartfelt","A gorgeous and serene view","She felt cheerful and glad","A splendid and pleasant evening"]
EXPL_NEG=["I absolutely hate this","This is awful and disgusting","A terrible and miserable day","The music was grating and unbearable","It tasted rotten and revolting","A truly dreadful result","The insult was vicious and hurtful","A filthy and menacing view","She felt bitter and sad","A wretched and hostile evening"]
NEUTRAL=["Overall, the situation was","My honest assessment is that it was","In the end it turned out to be","When it was all over, things felt"]
POS=[" good"," great"," wonderful"," amazing"]; NEG=[" bad"," terrible"," awful"," horrible"]
def tid(x):
    e=tok.encode(x); return e[0] if len(e)==1 else None
pid=[tid(x) for x in POS if tid(x) is not None]; nid=[tid(x) for x in NEG if tid(x) is not None]
def margin(lg): return float(np.mean([lg[i] for i in pid])-np.mean([lg[i] for i in nid]))

LAYERS=[6,16]           # valence-readable layer + a mid layer
MULTS=[1.0,2.0,4.0,8.0] # multiplier on the NATURAL mean-difference magnitude
K=8                     # matched-norm random null

res={"model":MODEL,"layers":NL,"hidden":H,"transformers_version":transformers.__version__,"torch_version":torch.__version__,
     "valence_tokens":{"pos":len(pid),"neg":len(nid)},"sweep":{}}
rng=np.random.default_rng(1729)
# capture explicit residuals once (all layers)
allpos=[resid_all(p) for p in EXPL_POS]; allneg=[resid_all(p) for p in EXPL_NEG]
for L in LAYERS:
    mu_p=np.mean([a[L] for a in allpos],axis=0); mu_n=np.mean([a[L] for a in allneg],axis=0)
    w_raw=mu_p-mu_n; wn=float(np.linalg.norm(w_raw))
    # typical residual norm at this layer (from explicit + neutral)
    hnorm=float(np.mean([np.linalg.norm(a[L]) for a in allpos+allneg]))
    layer_out={"raw_diff_norm":round(wn,3),"typical_resid_norm":round(hnorm,3),"per_mult":{}}
    for m in MULTS:
        w=w_raw*m; nrm=float(np.linalg.norm(w))
        sw=[margin(logits_with_add(p,L,w))-margin(logits_with_add(p,L,-w)) for p in NEUTRAL]
        null=[]
        for k in range(K):
            r=rng.standard_normal(w.shape); r=r/np.linalg.norm(r)*nrm
            null.append(float(np.mean([margin(logits_with_add(p,L,r))-margin(logits_with_add(p,L,-r)) for p in NEUTRAL])))
        null=np.array(null); s=float(np.mean(sw))
        layer_out["per_mult"][str(m)]={"inject_norm":round(nrm,2),"swing":round(s,3),
            "per_prompt":[round(x,3) for x in sw],
            "null_mean":round(float(null.mean()),3),"null_std":round(float(null.std()),3),
            "null_max_abs":round(float(np.abs(null).max()),3),
            "z_over_null":round(float((s-null.mean())/(null.std()+1e-9)),2),
            "directional_all_positive":bool(all(x>0 for x in sw)),
            "beats_null_max":bool(s>np.abs(null).max())}
    res["sweep"][f"L{L}"]=layer_out
# verdict: any (layer,mult) with z>=2, directional, and beats null max
best=None
for L,lo in res["sweep"].items():
    for m,d in lo["per_mult"].items():
        if d["directional_all_positive"] and d["z_over_null"]>=2.0 and d["beats_null_max"]:
            if best is None or d["z_over_null"]>best[2]: best=(L,m,d["z_over_null"],d["swing"])
res["verdict"]=("CAUSALLY_LOAD_BEARING_AT_SCALE" if best else "NOT_DISTINGUISHED_FROM_RANDOM")
res["best_hit"]=({"layer":best[0],"mult":best[1],"z":best[2],"swing":best[3]} if best else None)
print("<<<RESULTS_JSON>>>")
print(json.dumps(res))
print("<<<END_RESULTS_JSON>>>")
