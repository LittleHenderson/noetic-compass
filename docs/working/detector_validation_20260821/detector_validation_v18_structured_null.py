"""Structured non-CAS null -- is the CAS Domain partition PRIVILEGED, or just one coherent partition?

The v17 verifier's demand: beating a char-ngram surface control (or a random null) does NOT show
CAS-specificity -- it must beat a STRUCTURED non-CAS control. This runs it on the READING side.
Fixed 32-sentence grid (8 topics x 4 CAS-Domains). Compare how well the model's activations
separate:
  * the CAS partition (by Domain P/C/E/O), vs
  * several coherent NON-CAS partitions of the SAME 32 sentences (topic-pairings; sentence-length
    quartiles) -- each a balanced 4-way partition.
For each partition: over R random 24-train/8-test splits (SAME splits across partitions), best-
layer nearest-centroid accuracy + a char-ngram surface baseline. If CAS-Domain reads no better
(beyond surface) than arbitrary coherent non-CAS partitions, CAS is NOT privileged -> specificity
unsupported. Real pythia-160m, attested engine, CPU, $0.
"""
import sys, json, hashlib, pathlib
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
from app.runtime.open_weight.engine import (RuntimeLoadConfig, load_open_weight_runtime, capture_greedy_trajectory)
from app.runtime.open_weight.identity import LocalModelSnapshot
SP = pathlib.Path(__file__).resolve().parent
STORE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"

TOPICS = ["cooking","medicine","finance","law","sports","music","gardening","travel"]
DOMS = ["P","C","E","O"]
GRID = {
 "cooking":{"P":"A cook must never knowingly serve food that is unsafe to eat","C":"Water boils at one hundred degrees Celsius at sea level","E":"This risotto is the most delicious dish on the whole menu","O":"First dice the onion, then fry it slowly until it turns golden"},
 "medicine":{"P":"A doctor is obligated to protect the confidentiality of every patient","C":"The human heart has four chambers that pump blood through the body","E":"This new treatment is far superior to the older, harsher one","O":"First clean the wound, then apply the dressing and secure it"},
 "finance":{"P":"An advisor ought to disclose every conflict of interest honestly","C":"Compound interest grows a balance faster than simple interest does","E":"This fund is a poor choice with mediocre returns and high fees","O":"First open the account, then transfer the funds and confirm the balance"},
 "law":{"P":"A witness has a duty to tell the whole truth under oath","C":"A contract requires an offer, acceptance, and consideration to be valid","E":"This ruling is a brilliant and well reasoned piece of jurisprudence","O":"First file the motion, then serve the notice on the opposing party"},
 "sports":{"P":"Athletes should compete fairly and never use banned substances","C":"A marathon covers a distance of just over forty two kilometres","E":"That was the greatest comeback victory the sport has ever seen","O":"First stretch your muscles, then jog a slow lap to warm up"},
 "music":{"P":"A performer should credit every artist whose work they sample","C":"An octave spans twelve equal semitones in standard tuning","E":"This symphony is a sublime and deeply moving masterpiece","O":"First tune the strings, then set the tempo and begin the piece"},
 "gardening":{"P":"A gardener ought to avoid pesticides that harm pollinating bees","C":"Photosynthesis converts sunlight and water into sugars for the plant","E":"This rose garden is the most breathtaking display in the city","O":"First loosen the soil, then plant the seed and water it gently"},
 "travel":{"P":"A traveller should respect the customs and laws of every host country","C":"The Earth is divided into twenty four standard time zones","E":"This coastal town is the loveliest place I have ever visited","O":"First pack your bag, then check in online and print the boarding pass"}}
# flat list of (sentence, topic, domain)
ITEMS = [(GRID[t][d], t, d) for t in TOPICS for d in DOMS]  # 32
SENTS = [x[0] for x in ITEMS]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
def resid_all(p):
    cap=capture_greedy_trajectory(rt, scenario_id="v18", prompt=p, max_new_tokens=1, seed=0)
    arr=cap.arrays if hasattr(cap,"arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)
R = [resid_all(s) for s in SENTS]  # 32 x (L,H)

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

# --- partitions: each maps item-index -> class label (4 balanced classes of 8) ---
def part_domain(): return {i:ITEMS[i][2] for i in range(32)}
def part_topicpair(pairs):
    lab={}
    for gi,pair in enumerate(pairs):
        for i in range(32):
            if ITEMS[i][1] in pair: lab[i]=f"G{gi}"
    return lab
def part_lenq():
    order=sorted(range(32), key=lambda i: len(SENTS[i]))
    lab={}
    for rank,i in enumerate(order): lab[i]=f"Q{rank//8}"
    return lab
PARTS = {
 "CAS_domain": part_domain(),
 "topicpair_A": part_topicpair([("cooking","medicine"),("finance","law"),("sports","music"),("gardening","travel")]),
 "topicpair_B": part_topicpair([("cooking","finance"),("medicine","sports"),("law","gardening"),("music","travel")]),
 "topicpair_C": part_topicpair([("cooking","law"),("medicine","travel"),("finance","music"),("sports","gardening")]),
 "sentence_length_quartile": part_lenq(),
}

def nc_split(labels, tr_idx, te_idx, feat):
    classes=sorted(set(labels.values()))
    cent={}
    for c in classes:
        members=[i for i in tr_idx if labels[i]==c]
        if not members: return None
        cent[c]=np.mean([feat(i) for i in members],axis=0)
    ok=0
    for i in te_idx:
        v=feat(i); pred=min(cent,key=lambda k:np.linalg.norm(v-cent[k])); ok+=(pred==labels[i])
    return ok/len(te_idx)

Rsplits=20; rng=np.random.default_rng(20260821)
splits=[]
for _ in range(Rsplits):
    perm=rng.permutation(32); splits.append((sorted(perm[:24].tolist()), sorted(perm[24:].tolist())))

out={"model":"pythia-160m (reserialized, attested engine)","layers":L,"n_items":32,"chance":0.25,
     "R_splits":Rsplits,"partitions":{}}
for name,labels in PARTS.items():
    act_accs=[]; surf_accs=[]
    for tr,te in splits:
        # activation: best layer on this split's test (same freedom for every partition)
        best=-1
        for li in range(L):
            a=nc_split(labels,tr,te,lambda i:R[i][li])
            if a is not None and a>best: best=a
        act_accs.append(best)
        voc=voc_of(tr)
        surf_accs.append(nc_split(labels,tr,te,lambda i:cngram(SENTS[i],voc)) or 0.0)
    out["partitions"][name]={"activation_mean":round(float(np.mean(act_accs)),3),
        "activation_std":round(float(np.std(act_accs)),3),
        "surface_mean":round(float(np.mean(surf_accs)),3),
        "act_minus_surface":round(float(np.mean(act_accs)-np.mean(surf_accs)),3)}
# is CAS privileged? compare its act and act-minus-surface to the non-CAS partitions
cas=out["partitions"]["CAS_domain"]; noncas=[v for k,v in out["partitions"].items() if k!="CAS_domain"]
nc_act=[v["activation_mean"] for v in noncas]; nc_ams=[v["act_minus_surface"] for v in noncas]
out["cas_activation"]=cas["activation_mean"]; out["noncas_activation_max"]=round(max(nc_act),3); out["noncas_activation_mean"]=round(float(np.mean(nc_act)),3)
out["cas_act_minus_surface"]=cas["act_minus_surface"]; out["noncas_act_minus_surface_max"]=round(max(nc_ams),3)
out["cas_privileged"]=bool(cas["activation_mean"]>max(nc_act) and cas["act_minus_surface"]>max(nc_ams))
out["verdict"]=("CAS_PARTITION_PRIVILEGED" if out["cas_privileged"] else "CAS_NOT_PRIVILEGED_OVER_NONCAS")
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"detector_validation_v18_structured_null_results.json").write_bytes(raw)
print("\n==== STRUCTURED NON-CAS NULL (reading side, 160m) ====")
for name,v in out["partitions"].items():
    tag=" <-- CAS" if name=="CAS_domain" else ""
    print(f"  {name:26} act {v['activation_mean']:.3f}+-{v['activation_std']:.3f}  surf {v['surface_mean']:.3f}  act-surf {v['act_minus_surface']:+.3f}{tag}")
print(f"\n  CAS act {out['cas_activation']:.3f} vs non-CAS max {out['noncas_activation_max']:.3f} / mean {out['noncas_activation_mean']:.3f}")
print(f"  CAS act-surf {out['cas_act_minus_surface']:+.3f} vs non-CAS max {out['noncas_act_minus_surface_max']:+.3f}")
print(f"  VERDICT: {out['verdict']}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
