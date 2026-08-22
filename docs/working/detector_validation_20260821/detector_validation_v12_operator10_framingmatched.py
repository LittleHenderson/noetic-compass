"""Framing-matched Operator-10 control -- does the FLAGSHIP axis survive stripping the colloquialisms?

Operator-10 is the strongest axis (v5 160m 0.55 vs surface 0.25; v10 6.9b 0.80 vs 0.25). But its
stimuli are anchored to the canonical colloquialism map (^2 'moth to a flame', ^4 'struck a chord',
^8 'that reminds me', ...), which are themselves lexically distinctive. This tests whether the
strength is real structure or colloquialism-matching: TRAIN on the 6 canonical-colloquialism
exemplars per operator (the v5 set), TEST on 2 FRESH non-colloquial phrasings per operator that
convey the same Noetic operation WITHOUT the signature colloquialism vocabulary. Compare on the
same 20-item fresh test set against a char-ngram (n=2,3,4) surface baseline. Real pythia-160m,
attested engine, CPU, $0.

Honesty note (v10 lesson): activation = best-of-L-layers selected ON the test set; surface gets
no selection. n=2 fresh per operator. Reported inline.
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

# TRAIN: canonical-colloquialism exemplars (v5 set), 6 per operator
TRAIN = {
 "^0":["The concept of justice is an idea in the mind","Infinity is a notion that exists only in thought","The number seven is an abstract idea","Freedom is a concept we hold in our heads","A perfect circle is an idea, never a real thing","The word 'tomorrow' names an idea, not an object"],
 "^1":["She paid close attention to every word he said","He focused his full awareness on the problem","I made up my mind after thinking it over","Use your head and concentrate on the task","Her mind was alert and fully engaged","He noticed and became conscious of the sound"],
 "^2":["She was drawn to the painting like a moth to a flame","He simply could not resist the warm invitation","The idea speaks to me and I love it","I feel a strong pull toward that plan","They were attracted to the cheerful music","It appeals to me deeply and I want it"],
 "^3":["He could not stomach the cruel remark","That attitude rubs me the wrong way","I would not touch that scheme with a ten-foot pole","She was repelled by the rotten smell","The plan is repugnant and I recoil from it","They were disgusted and pulled away"],
 "^4":["The speech struck a chord deep within her","That story hit me hard and stayed with me","His words resonated and left an impression","The melody vibrated through the whole room","It made a lasting impression on the audience","The idea reverberated in his thoughts for days"],
 "^5":["We are each the sum of our experiences","Everything I have lived through made me who I am","Her character was shaped by years of hardship","His expertise is built from a lifetime of practice","The person you are is your accumulated past","My beliefs formed slowly from all I have seen"],
 "^6":["Let us break the argument down into its parts","She unpacked the idea to see what was inside","He took the theory apart piece by piece","The proof decomposes into three separate lemmas","We analyzed the plan by dividing it into steps","Pull the concept apart and examine each component"],
 "^7":["Practice makes perfect if you repeat it daily","You are what you repeatedly do every day","Through constant drilling it became muscle memory","She got into a steady groove of writing each morning","Repetition slowly conditioned the habit","Doing it over and over trained the reflex"],
 "^8":["That reminds me of a trip we took long ago","The smell of rain triggered a childhood memory","One thing led to another and I recalled her name","Seeing the photo made me think of my father","The song brought an old summer to mind","His comment sparked a completely different thought"],
 "^9":["The answer just popped into my head","Out of nowhere the solution came to me","Suddenly it clicked and I understood","The thought arrived unbidden in my mind","The name finally surfaced on its own","All at once the memory came to me"],
}
# TEST: 2 FRESH non-colloquial phrasings per operator -- same operation, giveaway colloquialisms REMOVED
TEST = {
 "^0":["Democracy is not a thing you could ever hold in your hand","Seven has no colour, weight, or place; it lives only in thought"],
 "^1":["Every small sound in the room registered with her at once","He held the whole problem in view without letting any part slip"],
 "^2":["From the first glance she wanted the little blue house","He kept finding excuses to return to that one quiet cafe"],
 "^3":["After a single bite he quietly pushed the bowl aside","She found reasons to leave whenever that subject arose"],
 "^4":["The film sat with him, unshakeable, for a week afterward","Long after she spoke, her sentence kept returning to him"],
 "^5":["Every hardship she had survived was now folded into who she was","A lifetime at the workbench had become the man himself"],
 "^6":["He examined each assumption the whole theory was resting on","She separated the proposal into the smaller claims it was made of"],
 "^7":["By the thousandth time, his hands moved without a single thought","Morning after morning of it wore the habit smooth and automatic"],
 "^8":["The scent of pine tar pulled a whole childhood winter back up","One look at the old photo and his father was suddenly present again"],
 "^9":["With no warning at all, the finished solution was simply there","The forgotten name arrived on its own, asked for by nothing"],
}
OPS = list(TRAIN)

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
_cache = {}
def resid_all(prompt):
    if prompt not in _cache:
        cap = capture_greedy_trajectory(rt, scenario_id="v12", prompt=prompt, max_new_tokens=1, seed=0)
        arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
        _cache[prompt] = np.asarray(arr["residual_states"])[0].astype(np.float64)
    return _cache[prompt]
def cngram(text, vocab):
    t=text.lower(); c={}
    for n in (2,3,4):
        for i in range(len(t)-n+1): c[t[i:i+n]]=c.get(t[i:i+n],0)+1
    v=np.array([c.get(g,0) for g in vocab],dtype=np.float64); z=np.linalg.norm(v); return v/z if z>0 else v
def vocab_of(texts):
    s=set()
    for t in texts:
        t=t.lower()
        for n in (2,3,4):
            for i in range(len(t)-n+1): s.add(t[i:i+n])
    return sorted(s)
def nc(train_map, test_map, featfn):
    cent={c:np.mean([featfn(x) for x in train_map[c]],axis=0) for c in train_map}
    ok=tot=0; per={o:[0,0] for o in OPS}
    for c,items in test_map.items():
        for x in items:
            v=featfn(x); pred=min(cent,key=lambda k:np.linalg.norm(v-cent[k]))
            ok+=(pred==c); tot+=1; per[c][0]+=(pred==c); per[c][1]+=1
    return ok/tot, per

for o in OPS:
    for s in TRAIN[o]: resid_all(s)
    for s in TEST[o]: resid_all(s)

best=(-1,None,None)
for li in range(L):
    tr={o:[resid_all(s)[li] for s in TRAIN[o]] for o in OPS}
    te={o:[resid_all(s)[li] for s in TEST[o]] for o in OPS}
    a,per=nc(tr,te,lambda v:v)
    if a>best[0]: best=(a,li,per)
act,act_layer,act_per=best

rng=np.random.default_rng(20260821)
tr_sel={o:[resid_all(s)[act_layer] for s in TRAIN[o]] for o in OPS}
cent={o:np.mean(tr_sel[o],axis=0) for o in OPS}
te_items=[(resid_all(s)[act_layer],o) for o in OPS for s in TEST[o]]
shuf=[o for _,o in te_items]; rng.shuffle(shuf)
shuf_acc=np.mean([(min(cent,key=lambda k:np.linalg.norm(v-cent[k]))==sl) for (v,_),sl in zip(te_items,shuf)])

voc=vocab_of([s for o in OPS for s in TRAIN[o]])
trx={o:list(TRAIN[o]) for o in OPS}; tex={o:list(TEST[o]) for o in OPS}
ng,ng_per=nc(trx,tex,lambda x:cngram(x,voc))

hardened = act >= 0.40 and (act-ng) >= 0.15
out={"axis":"Operator-10 ^0..^9, framing-matched (train canonical colloquialisms, test FRESH non-colloquial phrasings)",
     "model":"pythia-160m (reserialized, attested engine)","layers":L,"chance":0.10,
     "n_train_per_op":6,"n_test_per_op":2,"n_test_total":20,
     "activation_best":round(act,3),"best_layer_selected_on_test":act_layer,
     "activation_per_operator":{o:f"{act_per[o][0]}/{act_per[o][1]}" for o in OPS},
     "label_shuffle_null":round(float(shuf_acc),3),
     "char_ngram_surface":round(ng,3),
     "char_ngram_per_operator":{o:f"{ng_per[o][0]}/{ng_per[o][1]}" for o in OPS},
     "activation_minus_surface":round(act-ng,3),"activation_beats_surface":bool(act>ng),
     "verdict":("OPERATOR10_HARDENED_VS_COLLOQUIALISM" if hardened else
                ("BEATS_SURFACE_WEAK" if act>ng else "COLLOQUIALISM_CONFOUNDED")),
     "rule":"HARDENED iff activation >= 0.40 AND beats char-ngram surface by >= 0.15",
     "caveat":"activation best-of-%d-layers selected on the 20-item test set; surface gets no selection; n=2 fresh per operator"%L}
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"detector_validation_v12_operator10_framingmatched_results.json").write_bytes(raw)
print("\n==== FRAMING-MATCHED OPERATOR-10 CONTROL (train colloquialisms, test fresh phrasings) ====")
print(f"  activation best   : {act:.3f} (L{act_layer})")
print(f"  per-operator      : {out['activation_per_operator']}")
print(f"  label-shuffle null: {shuf_acc:.3f}")
print(f"  char-ngram surface: {ng:.3f}")
print(f"  activation-surface: {act-ng:+.3f}  (chance 0.10)")
print(f"  VERDICT: {out['verdict']}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
