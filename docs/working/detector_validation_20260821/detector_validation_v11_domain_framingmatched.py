"""Framing-matched Domain-4 control -- does P/C/E/O read real domain structure or giveaway words?

Today's pythia-6.9b run left Domain-4 flagged SURFACE-LEXICAL (activation 1.000 but char-ngram
0.875). v4/v9 already noted the framings carry lexical signatures (ought->P, first/then->O,
superlatives->E, declaratives->C). This is the test those results pointed at: TRAIN the
activation detector on the original framing-RICH Domain sentences (8 topics), TEST on 4 NEW
topics whose sentences STRIP the giveaway markers -- duty by action (no must/ought), evaluation
without superlatives, procedure without first/then. Compare on the SAME stripped test set
against a char-ngram (n=2,3,4) surface baseline. HARDENED only if activation beats surface.
This controls BOTH topic (new content) and framing (stripped markers) at once. Real
pythia-160m, attested engine, CPU, $0.

Honesty note (learned from v10): the activation figure is best-of-L-layers selected on the
test set; the char-ngram baseline gets no such selection. Reported inline.
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
DOMAINS = ["P", "C", "E", "O"]

# TRAIN: original framing-RICH stimuli (the v4/v9 set) -- giveaway markers present
TRAIN = {
 "cooking":{"P":"A cook must never knowingly serve food that is unsafe to eat","C":"Water boils at one hundred degrees Celsius at sea level","E":"This risotto is the most delicious dish on the whole menu","O":"First dice the onion, then fry it slowly until it turns golden"},
 "medicine":{"P":"A doctor is obligated to protect the confidentiality of every patient","C":"The human heart has four chambers that pump blood through the body","E":"This new treatment is far superior to the older, harsher one","O":"First clean the wound, then apply the dressing and secure it"},
 "finance":{"P":"An advisor ought to disclose every conflict of interest honestly","C":"Compound interest grows a balance faster than simple interest does","E":"This fund is a poor choice with mediocre returns and high fees","O":"First open the account, then transfer the funds and confirm the balance"},
 "law":{"P":"A witness has a duty to tell the whole truth under oath","C":"A contract requires an offer, acceptance, and consideration to be valid","E":"This ruling is a brilliant and well reasoned piece of jurisprudence","O":"First file the motion, then serve the notice on the opposing party"},
 "sports":{"P":"Athletes should compete fairly and never use banned substances","C":"A marathon covers a distance of just over forty two kilometres","E":"That was the greatest comeback victory the sport has ever seen","O":"First stretch your muscles, then jog a slow lap to warm up"},
 "music":{"P":"A performer should credit every artist whose work they sample","C":"An octave spans twelve equal semitones in standard tuning","E":"This symphony is a sublime and deeply moving masterpiece","O":"First tune the strings, then set the tempo and begin the piece"},
 "gardening":{"P":"A gardener ought to avoid pesticides that harm pollinating bees","C":"Photosynthesis converts sunlight and water into sugars for the plant","E":"This rose garden is the most breathtaking display in the city","O":"First loosen the soil, then plant the seed and water it gently"},
 "travel":{"P":"A traveller should respect the customs and laws of every host country","C":"The Earth is divided into twenty four standard time zones","E":"This coastal town is the loveliest place I have ever visited","O":"First pack your bag, then check in online and print the boarding pass"},
}

# TEST: 4 NEW topics, framing-STRIPPED -- domain conveyed WITHOUT the giveaway markers.
# P: duty shown by choosing the principled action over convenience (no must/ought/should/never/duty).
# C: plain factual declarative (the neutral baseline; all four are declaratives here to avoid giving C away).
# E: positive/negative evaluation WITHOUT superlatives (no most/greatest/best/finest).
# O: imperative procedure WITHOUT sequence words (no first/then/next).
TEST = {
 "aviation":{"P":"The captain reported the cracked windscreen instead of flying on to stay on schedule","C":"A jet engine pushes air backward to drive the aircraft forward","E":"The crew handled the storm in a way that put every passenger at ease","O":"Lower the landing gear. Line up with the runway. Ease back on the throttle."},
 "carpentry":{"P":"The carpenter turned the job down rather than build with timber he knew was rotten","C":"Oak is denser and heavier than pine of the same size","E":"The finish on that cabinet is a pleasure to run your hand across","O":"Measure the plank twice. Cut along the marked line. Sand the edge smooth."},
 "banking":{"P":"The teller flagged the odd transfer even though it slowed the line behind her","C":"A savings account pays interest on the money that is held in it","E":"Working with that advisor left the family feeling genuinely looked after","O":"Enter the amount. Confirm the account number. Approve the transfer."},
 "teaching":{"P":"The teacher reported the leaked exam rather than let the result stand","C":"The alphabet used to write English is made up of twenty six letters","E":"Her class was the part of the day the children looked forward to","O":"Hand out the worksheets. Read the instructions aloud. Collect the answers at the end."},
}
TR_T = list(TRAIN); TE_T = list(TEST)

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
        cap = capture_greedy_trajectory(rt, scenario_id="v11", prompt=prompt, max_new_tokens=1, seed=0)
        arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
        _cache[prompt] = np.asarray(arr["residual_states"])[0].astype(np.float64)  # (layers,hidden)
    return _cache[prompt]

def cngram(text, vocab):
    t = text.lower(); c = {}
    for n in (2,3,4):
        for i in range(len(t)-n+1): c[t[i:i+n]] = c.get(t[i:i+n],0)+1
    v = np.array([c.get(g,0) for g in vocab], dtype=np.float64); z = np.linalg.norm(v)
    return v/z if z>0 else v
def vocab_of(texts):
    s=set()
    for t in texts:
        t=t.lower()
        for n in (2,3,4):
            for i in range(len(t)-n+1): s.add(t[i:i+n])
    return sorted(s)
def nc_multi(train_map, test_map, featfn):
    cent = {c: np.mean([featfn(x) for x in train_map[c]], axis=0) for c in train_map}
    correct=total=0; per={d:[0,0] for d in DOMAINS}; conf={}
    for c, items in test_map.items():
        for x in items:
            v = featfn(x)
            pred = min(cent, key=lambda k: np.linalg.norm(v-cent[k]))
            ok = (pred==c); correct += ok; total += 1
            per[c][0]+=ok; per[c][1]+=1
            conf[f"{c}->{pred}"] = conf.get(f"{c}->{pred}",0)+1
    return correct/total, per, conf

# capture all
for t in TR_T:
    for d in DOMAINS: resid_all(TRAIN[t][d])
for t in TE_T:
    for d in DOMAINS: resid_all(TEST[t][d])

# activation: best layer selected on the test set (caveat recorded), + label-shuffle null
best=(-1,None,None,None)
for li in range(L):
    tr={d:[resid_all(TRAIN[t][d])[li] for t in TR_T] for d in DOMAINS}
    te={d:[resid_all(TEST[t][d])[li] for t in TE_T] for d in DOMAINS}
    a,per,conf=nc_multi(tr,te,lambda v:v)
    if a>best[0]: best=(a,li,per,conf)
act,act_layer,act_per,act_conf = best

# label-shuffle null at the selected layer
rng=np.random.default_rng(20260821)
tr_sel={d:[resid_all(TRAIN[t][d])[act_layer] for t in TR_T] for d in DOMAINS}
te_items=[(resid_all(TEST[t][d])[act_layer],d) for t in TE_T for d in DOMAINS]
cent={d:np.mean(tr_sel[d],axis=0) for d in DOMAINS}
shuf_labels=[d for _,d in te_items]; rng.shuffle(shuf_labels)
shuf=np.mean([(min(cent,key=lambda k:np.linalg.norm(v-cent[k]))==sl) for (v,_),sl in zip(te_items,shuf_labels)])

# char-ngram surface baseline: vocab from TRAIN only, same protocol
voc=vocab_of([TRAIN[t][d] for t in TR_T for d in DOMAINS])
trx={d:[TRAIN[t][d] for t in TR_T] for d in DOMAINS}; tex={d:[TEST[t][d] for t in TE_T] for d in DOMAINS}
ng,ng_per,ng_conf=nc_multi(trx,tex,lambda x:cngram(x,voc))

hardened = act >= 0.60 and (act - ng) >= 0.15
out={"axis":"Domain-4 P/C/E/O, framing-matched (train framing-rich, test framing-STRIPPED new topics)",
     "model":"pythia-160m (reserialized, attested engine)","layers":L,"chance":0.25,
     "n_train_per_class":len(TR_T),"n_test_per_class":len(TE_T),"n_test_total":len(TE_T)*4,
     "activation_best":round(act,3),"best_layer_selected_on_test":act_layer,
     "activation_per_domain":{d:f"{act_per[d][0]}/{act_per[d][1]}" for d in DOMAINS},
     "activation_confusion":act_conf,
     "label_shuffle_null":round(float(shuf),3),
     "char_ngram_surface":round(ng,3),
     "char_ngram_per_domain":{d:f"{ng_per[d][0]}/{ng_per[d][1]}" for d in DOMAINS},
     "activation_minus_surface":round(act-ng,3),
     "activation_beats_surface":bool(act>ng),
     "verdict":("DOMAIN4_STRUCTURE_HARDENED" if hardened else
                ("BEATS_SURFACE_WEAK" if act>ng else "SURFACE_CONFOUNDED_CONFIRMED")),
     "rule":"HARDENED iff activation >= 0.60 AND beats char-ngram surface by >= 0.15",
     "caveat":"activation best-of-%d-layers selected on the 16-item test set; surface gets no selection; n=4 held-out topics per domain"%L}
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"detector_validation_v11_domain_framingmatched_results.json").write_bytes(raw)
print("\n==== FRAMING-MATCHED DOMAIN-4 CONTROL (train framing-rich, test framing-stripped new topics) ====")
print(f"  activation best   : {act:.3f} (L{act_layer})   per-domain {out['activation_per_domain']}")
print(f"  label-shuffle null: {shuf:.3f}")
print(f"  char-ngram surface: {ng:.3f}   per-domain {out['char_ngram_per_domain']}")
print(f"  activation - surface: {act-ng:+.3f}   (chance 0.25)")
print(f"  VERDICT: {out['verdict']}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
