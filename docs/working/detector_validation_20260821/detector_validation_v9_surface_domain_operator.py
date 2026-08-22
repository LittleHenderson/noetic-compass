"""Surface control for Domain-4 and Operator-10 -- do they beat a char-ngram baseline?

Honesty completion: v6/v7 showed valence and cause-effect are surface-confounded. Domain-4 (v4,
'perfect') and Operator-10 (v5, 7/10) were claimed without this control. Here each is re-run with
a char-ngram (n=2,3,4) nearest-centroid surface baseline on the SAME train->test split. If the
activation detector does not beat surface, the 'validation' was surface. Real pythia-160m, CPU, $0.
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

# ---- Domain-4 stimuli (v4) ----
DOMAINS = ["P","C","E","O"]
TOPICS = {
 "cooking":{"P":"A cook must never knowingly serve food that is unsafe to eat","C":"Water boils at one hundred degrees Celsius at sea level","E":"This risotto is the most delicious dish on the whole menu","O":"First dice the onion, then fry it slowly until it turns golden"},
 "medicine":{"P":"A doctor is obligated to protect the confidentiality of every patient","C":"The human heart has four chambers that pump blood through the body","E":"This new treatment is far superior to the older, harsher one","O":"First clean the wound, then apply the dressing and secure it"},
 "finance":{"P":"An advisor ought to disclose every conflict of interest honestly","C":"Compound interest grows a balance faster than simple interest does","E":"This fund is a poor choice with mediocre returns and high fees","O":"First open the account, then transfer the funds and confirm the balance"},
 "law":{"P":"A witness has a duty to tell the whole truth under oath","C":"A contract requires an offer, acceptance, and consideration to be valid","E":"This ruling is a brilliant and well reasoned piece of jurisprudence","O":"First file the motion, then serve the notice on the opposing party"},
 "sports":{"P":"Athletes should compete fairly and never use banned substances","C":"A marathon covers a distance of just over forty two kilometres","E":"That was the greatest comeback victory the sport has ever seen","O":"First stretch your muscles, then jog a slow lap to warm up"},
 "music":{"P":"A performer should credit every artist whose work they sample","C":"An octave spans twelve equal semitones in standard tuning","E":"This symphony is a sublime and deeply moving masterpiece","O":"First tune the strings, then set the tempo and begin the piece"},
 "gardening":{"P":"A gardener ought to avoid pesticides that harm pollinating bees","C":"Photosynthesis converts sunlight and water into sugars for the plant","E":"This rose garden is the most breathtaking display in the city","O":"First loosen the soil, then plant the seed and water it gently"},
 "travel":{"P":"A traveller should respect the customs and laws of every host country","C":"The Earth is divided into twenty four standard time zones","E":"This coastal town is the loveliest place I have ever visited","O":"First pack your bag, then check in online and print the boarding pass"},
}
TOPIC_NAMES = list(TOPICS); TR_T, TE_T = TOPIC_NAMES[:6], TOPIC_NAMES[6:]

# ---- Operator-10 stimuli (v5), 6 each ----
OPS = {
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
OP_NAMES = list(OPS)

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
        cap = capture_greedy_trajectory(rt, scenario_id="v9", prompt=prompt, max_new_tokens=1, seed=0)
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

def nc_multi(classes_train, classes_test, featfn):
    cent = {c: np.mean([featfn(x) for x in classes_train[c]], axis=0) for c in classes_train}
    correct=total=0
    for c, items in classes_test.items():
        for x in items:
            v = featfn(x)
            pred = min(cent, key=lambda k: np.linalg.norm(v-cent[k]))
            correct += (pred==c); total += 1
    return correct/total

# ---- Domain-4 ----
print("capturing Domain-4 (32) ...", flush=True)
for t in TOPIC_NAMES:
    for d in DOMAINS: resid_all(TOPICS[t][d])
def dom_best():
    best_act=(-1,None);
    for li in range(L):
        tr={d:[resid_all(TOPICS[t][d])[li] for t in TR_T] for d in DOMAINS}
        te={d:[resid_all(TOPICS[t][d])[li] for t in TE_T] for d in DOMAINS}
        a=nc_multi(tr,te,lambda v:v)
        if a>best_act[0]: best_act=(a,li)
    # char-ngram baseline at that best layer's split
    vtxt=[TOPICS[t][d] for t in TR_T for d in DOMAINS]; voc=vocab_of(vtxt)
    trx={d:[TOPICS[t][d] for t in TR_T] for d in DOMAINS}; tex={d:[TOPICS[t][d] for t in TE_T] for d in DOMAINS}
    ng=nc_multi(trx,tex,lambda x:cngram(x,voc))
    return best_act[0],best_act[1],ng
dom_act,dom_layer,dom_ng = dom_best()

# ---- Operator-10 ----
print("capturing Operator-10 (60) ...", flush=True)
for op in OP_NAMES:
    for s in OPS[op]: resid_all(s)
def op_best():
    best=(-1,None)
    for li in range(L):
        tr={op:[resid_all(OPS[op][i])[li] for i in range(4)] for op in OP_NAMES}
        te={op:[resid_all(OPS[op][i])[li] for i in (4,5)] for op in OP_NAMES}
        a=nc_multi(tr,te,lambda v:v)
        if a>best[0]: best=(a,li)
    vtxt=[OPS[op][i] for op in OP_NAMES for i in range(4)]; voc=vocab_of(vtxt)
    trx={op:[OPS[op][i] for i in range(4)] for op in OP_NAMES}; tex={op:[OPS[op][i] for i in (4,5)] for op in OP_NAMES}
    ng=nc_multi(trx,tex,lambda x:cngram(x,voc))
    return best[0],best[1],ng
op_act,op_layer,op_ng = op_best()

def verdict(act, ng, bar):
    return "SURFACE_ROBUST" if (act>=bar and act-ng>=0.15) else ("BEATS_SURFACE_WEAK" if act>ng else "SURFACE_CONFOUNDED")
out={"domain4":{"activation_best":round(dom_act,3),"best_layer":dom_layer,"char_ngram_surface":round(dom_ng,3),
        "chance":0.25,"verdict":verdict(dom_act,dom_ng,0.60)},
     "operator10":{"activation_best":round(op_act,3),"best_layer":op_layer,"char_ngram_surface":round(op_ng,3),
        "chance":0.10,"verdict":verdict(op_act,op_ng,0.40)}}
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"detector_validation_v9_surface_results.json").write_bytes(raw)
print("\n==== SURFACE CONTROL for Domain-4 and Operator-10 ====")
for name,r in out.items():
    print(f"\n  {name}: activation {r['activation_best']:.3f} (L{r['best_layer']}) vs char-ngram surface {r['char_ngram_surface']:.3f} (chance {r['chance']})")
    print(f"    VERDICT: {r['verdict']}")
print(f"\nsha256={hashlib.sha256(raw).hexdigest()[:16]}")
