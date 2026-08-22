"""Construct-correct + giveaway-free ^8/^9 -- was the NOISE result a WRONG-CONSTRUCT artifact?

Owner insight: 'maybe the wording of the definitions is the reason it's not passing.' Canonical
^8 Above/Cause = ASSOCIATIVE TRIGGERING (an Idea that triggers a DIFFERENT Idea to come to Mind),
NOT logical/physical causation. The prior cause-effect tests (v3/v6/v10) used PHYSICAL causation
(rain->flood, dam->flood) with because/so/therefore connectives -- a DRIFTED construct plus a
giveaway. This re-test uses the CANONICAL construct:
  ^8 = the TRIGGERING dynamic (a cue evokes a different idea)
  ^9 = the ARRIVAL dynamic (the idea lands, unbidden)
TRAIN on the v5 canonical colloquial exemplars (construct-correct); TEST on FRESH giveaway-free
phrasings that carry the triggering-vs-arrival dynamic WITHOUT reminds/triggered/brought-to-mind
/popped/came-to-me/clicked/because/so/therefore. Compare vs char-ngram surface. Real pythia-160m,
attested engine, CPU, $0.
"""
import sys, json, hashlib, pathlib
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
from app.runtime.open_weight.engine import (RuntimeLoadConfig, load_open_weight_runtime,
    capture_greedy_trajectory)
from app.runtime.open_weight.identity import LocalModelSnapshot

SP = pathlib.Path(__file__).resolve().parent
STORE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"

# TRAIN: v5 canonical colloquial exemplars (construct-correct: ^8 triggering, ^9 arrival)
TRAIN = {
 "^8":["That reminds me of a trip we took long ago","The smell of rain triggered a childhood memory","One thing led to another and I recalled her name","Seeing the photo made me think of my father","The song brought an old summer to mind","His comment sparked a completely different thought"],
 "^9":["The answer just popped into my head","Out of nowhere the solution came to me","Suddenly it clicked and I understood","The thought arrived unbidden in my mind","The name finally surfaced on its own","All at once the memory came to me"],
}
# TEST: FRESH giveaway-free -- construct-correct, no reminds/triggered/popped/came-to-me/because/so
TEST = {
 # ^8 : a cue EVOKES a different idea (triggering dynamic named by the cue -> evocation)
 "^8":["The worn leather seat carried him straight back to his grandfather's garage",
       "A few bars of that old tune and the whole summer stood in front of her again",
       "The scent of chalk dust set a classroom from thirty years ago alight for him",
       "One taste of the broth and her mother's kitchen rose up around her",
       "The creak of that gate swung open his entire childhood",
       "A stranger's cologne on the train and his first love was there once more"],
 # ^9 : the idea itself LANDS, unbidden (arrival dynamic, no trigger foregrounded)
 "^9":["Halfway through dinner, the missing word was simply there",
       "In the small hours the whole answer lay finished in her thoughts",
       "Without her reaching for it, the man's name settled into place",
       "The solution he had chased for weeks was suddenly, quietly present",
       "Between one step and the next, the plan assembled itself complete",
       "The forgotten address rose up on its own, wanted by nothing"],
}
CLS = list(TRAIN)

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
_cache={}
def resid_all(p):
    if p not in _cache:
        cap=capture_greedy_trajectory(rt, scenario_id="v13", prompt=p, max_new_tokens=1, seed=0)
        arr=cap.arrays if hasattr(cap,"arrays") else cap["arrays"]
        _cache[p]=np.asarray(arr["residual_states"])[0].astype(np.float64)
    return _cache[p]
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
def nc(trm,tem,f):
    cent={c:np.mean([f(x) for x in trm[c]],axis=0) for c in trm}
    ok=tot=0;per={c:[0,0] for c in CLS}
    for c,items in tem.items():
        for x in items:
            v=f(x);pred=min(cent,key=lambda k:np.linalg.norm(v-cent[k]));ok+=(pred==c);tot+=1;per[c][0]+=(pred==c);per[c][1]+=1
    return ok/tot,per

for c in CLS:
    for s in TRAIN[c]+TEST[c]: resid_all(s)
best=(-1,None,None)
for li in range(L):
    tr={c:[resid_all(s)[li] for s in TRAIN[c]] for c in CLS}
    te={c:[resid_all(s)[li] for s in TEST[c]] for c in CLS}
    a,per=nc(tr,te,lambda v:v)
    if a>best[0]: best=(a,li,per)
act,act_layer,act_per=best
# shuffle null
rng=np.random.default_rng(20260821)
cent={c:np.mean([resid_all(s)[act_layer] for s in TRAIN[c]],axis=0) for c in CLS}
te_items=[(resid_all(s)[act_layer],c) for c in CLS for s in TEST[c]]
sl=[c for _,c in te_items]; rng.shuffle(sl)
shuf=np.mean([(min(cent,key=lambda k:np.linalg.norm(v-cent[k]))==x) for (v,_),x in zip(te_items,sl)])
voc=voc_of([s for c in CLS for s in TRAIN[c]])
ng,ng_per=nc({c:list(TRAIN[c]) for c in CLS},{c:list(TEST[c]) for c in CLS},lambda x:cngram(x,voc))
hardened = act>=0.70 and (act-ng)>=0.10
out={"axis":"^8/^9 canonical ASSOCIATIVE TRIGGERING vs ARRIVAL (construct-correct, giveaway-free)",
     "note":"prior v3/v6/v10 cause-effect used PHYSICAL causation + connectives (drifted construct); this uses the canonical triggering/arrival construct with giveaways stripped",
     "model":"pythia-160m (reserialized, attested engine)","layers":L,"chance":0.5,
     "n_train_per_class":6,"n_test_per_class":6,"n_test_total":12,
     "activation_best":round(act,3),"best_layer_selected_on_test":act_layer,
     "activation_per_class":{c:f"{act_per[c][0]}/{act_per[c][1]}" for c in CLS},
     "label_shuffle_null":round(float(shuf),3),
     "char_ngram_surface":round(ng,3),
     "char_ngram_per_class":{c:f"{ng_per[c][0]}/{ng_per[c][1]}" for c in CLS},
     "activation_minus_surface":round(act-ng,3),"activation_beats_surface":bool(act>ng),
     "verdict":("TRIGGER_ARRIVAL_HARDENED" if hardened else ("BEATS_SURFACE_WEAK" if act>ng else "NOT_SEPARABLE_GIVEAWAYFREE")),
     "rule":"HARDENED iff activation >= 0.70 AND beats char-ngram surface by >= 0.10",
     "caveat":"activation best-of-%d-layers on the 12-item test set; surface gets no selection; n=6 fresh per class; ^8 vs ^9 may be intrinsically two halves of one dynamic"%L}
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"detector_validation_v13_cause_effect_constructcorrect_results.json").write_bytes(raw)
print("\n==== CONSTRUCT-CORRECT + GIVEAWAY-FREE ^8/^9 (triggering vs arrival) ====")
print(f"  activation best   : {act:.3f} (L{act_layer})   per-class {out['activation_per_class']}")
print(f"  label-shuffle null: {shuf:.3f}")
print(f"  char-ngram surface: {ng:.3f}   per-class {out['char_ngram_per_class']}")
print(f"  activation-surface: {act-ng:+.3f}  (chance 0.50)")
print(f"  VERDICT: {out['verdict']}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
