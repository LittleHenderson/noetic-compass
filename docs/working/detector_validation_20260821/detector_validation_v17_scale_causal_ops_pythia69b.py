"""SCALE CAUSAL OPS: do NON-valence directions (Domain P/O, Operator ^2/^3) also steer output? (paid A40)

v16 showed the valence direction is a causal lever at 6.9b. This asks whether OTHER CAS directions
are levers too. The honest constraint: valence had clean output tokens (good/bad); Operator/Domain
need CLASS-CHARACTERISTIC tokens. Two contrasts, each with its own signature output words:
  * Domain P vs O: P={must,should,ought,shall} vs O={first,then,next,step}
  * Operator ^2(attraction) vs ^3(aversion): pos={good,great,love,wonderful} vs neg={bad,awful,hate,terrible}
For each: build d = mean(A resid) - mean(B resid) at a layer, inject +d/-d at natural magnitude
swept x1..x8, measure the A-vs-B output-token margin swing on neutral prompts, vs a norm-matched
random null (K=8). A positive result = injecting the direction causally increases class-A-
characteristic output (a real, specific form of steering). Direct transformers, NOT the attested
engine. Emits one JSON between markers.
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
def tid(x):
    e=tok.encode(x); return e[0] if len(e)==1 else None
def toks(words): return [t for t in (tid(w) for w in words) if t is not None]

# Domain P vs O
DOM_P=["A cook must never knowingly serve food that is unsafe to eat","A doctor is obligated to protect the confidentiality of every patient","An advisor ought to disclose every conflict of interest honestly","A witness has a duty to tell the whole truth under oath","Athletes should compete fairly and never use banned substances","A performer should credit every artist whose work they sample","A gardener ought to avoid pesticides that harm pollinating bees","A traveller should respect the customs and laws of every host country"]
DOM_O=["First dice the onion, then fry it slowly until it turns golden","First clean the wound, then apply the dressing and secure it","First open the account, then transfer the funds and confirm the balance","First file the motion, then serve the notice on the opposing party","First stretch your muscles, then jog a slow lap to warm up","First tune the strings, then set the tempo and begin the piece","First loosen the soil, then plant the seed and water it gently","First pack your bag, then check in online and print the boarding pass"]
DOM_A_TOK=toks([" must"," should"," ought"," shall"]); DOM_B_TOK=toks([" first"," then"," next"," step"])
DOM_NEUT=["In this situation, one","Regarding the task, the key is to","When handling this, you","The important thing here is to"]
# Operator ^2 vs ^3
OP2=["She was drawn to the painting like a moth to a flame","He simply could not resist the warm invitation","The idea speaks to me and I love it","I feel a strong pull toward that plan","They were attracted to the cheerful music","It appeals to me deeply and I want it"]
OP3=["He could not stomach the cruel remark","That attitude rubs me the wrong way","I would not touch that scheme with a ten-foot pole","She was repelled by the rotten smell","The plan is repugnant and I recoil from it","They were disgusted and pulled away"]
OP_A_TOK=toks([" good"," great"," love"," wonderful"]); OP_B_TOK=toks([" bad"," awful"," hate"," terrible"])
OP_NEUT=["Overall, the situation was","My honest assessment is that it was","In the end it turned out to be","When it was all over, things felt"]

LAYERS=[6,16]; MULTS=[1.0,2.0,4.0,8.0]; K=8
rng=np.random.default_rng(1729)
def run_contrast(A_prompts,B_prompts,A_tok,B_tok,NEUT,name):
    def margin(lg): return float(np.mean([lg[i] for i in A_tok])-np.mean([lg[i] for i in B_tok]))
    ra=[resid_all(p) for p in A_prompts]; rb=[resid_all(p) for p in B_prompts]
    out={"name":name,"n_A_tok":len(A_tok),"n_B_tok":len(B_tok),"sweep":{}}
    for L in LAYERS:
        d=np.mean([a[L] for a in ra],axis=0)-np.mean([b[L] for b in rb],axis=0); dn=float(np.linalg.norm(d))
        hnorm=float(np.mean([np.linalg.norm(a[L]) for a in ra+rb]))
        lo={"raw_diff_norm":round(dn,3),"typical_resid_norm":round(hnorm,3),"per_mult":{}}
        for m in MULTS:
            w=d*m; nrm=float(np.linalg.norm(w))
            sw=[margin(logits_with_add(p,L,w))-margin(logits_with_add(p,L,-w)) for p in NEUT]
            null=[]
            for k in range(K):
                r=rng.standard_normal(w.shape); r=r/np.linalg.norm(r)*nrm
                null.append(float(np.mean([margin(logits_with_add(p,L,r))-margin(logits_with_add(p,L,-r)) for p in NEUT])))
            null=np.array(null); s=float(np.mean(sw))
            lo["per_mult"][str(m)]={"inject_norm":round(nrm,2),"swing":round(s,3),
                "per_prompt":[round(x,3) for x in sw],
                "null_mean":round(float(null.mean()),3),"null_std":round(float(null.std()),3),
                "null_max_abs":round(float(np.abs(null).max()),3),
                "z_over_null":round(float((s-null.mean())/(null.std()+1e-9)),2),
                "directional_all_positive":bool(all(x>0 for x in sw)),
                "beats_null_max":bool(s>np.abs(null).max())}
        out["sweep"][f"L{L}"]=lo
    best=None
    for L,lo in out["sweep"].items():
        for m,dd in lo["per_mult"].items():
            if dd["directional_all_positive"] and dd["z_over_null"]>=2.0 and dd["beats_null_max"]:
                if best is None or dd["z_over_null"]>best[2]: best=(L,m,dd["z_over_null"],dd["swing"])
    out["verdict"]=("CAUSALLY_LOAD_BEARING_AT_SCALE" if best else "NOT_DISTINGUISHED_FROM_RANDOM")
    out["best_hit"]=({"layer":best[0],"mult":best[1],"z":best[2],"swing":best[3]} if best else None)
    return out

res={"model":MODEL,"layers":NL,"hidden":H,"transformers_version":transformers.__version__,"torch_version":torch.__version__,
     "note":"class-characteristic output tokens (function/valence words); a positive = the direction causally raises class-A-characteristic output"}
res["domain_P_vs_O"]=run_contrast(DOM_P,DOM_O,DOM_A_TOK,DOM_B_TOK,DOM_NEUT,"Domain P (principled) vs O (operational) output steering")
res["operator_2_vs_3"]=run_contrast(OP2,OP3,OP_A_TOK,OP_B_TOK,OP_NEUT,"Operator ^2 (attraction) vs ^3 (aversion) output steering")
print("<<<RESULTS_JSON>>>")
print(json.dumps(res))
print("<<<END_RESULTS_JSON>>>")
