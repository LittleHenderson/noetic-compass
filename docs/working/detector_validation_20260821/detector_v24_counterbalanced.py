"""V24 -- COUNTERBALANCED pairs: take POSITION out of the label ($0, attested engine, 160m).

v23 scored 1.000 with both surface baselines provably pinned -- but the label was POSITIONAL by
construction (class A always had the sensory phrase in slot 1), so position + noun identity was
enough. That is shallow. This is the named decisive follow-up.

FIX: the SENSORY phrase sits in slot 1 in BOTH members. What flips is which phrase the temporal
marker attaches to:

  A: "the scent of tar came before and the memory of childhood came after"   (scent first in TIME)
  B: "the scent of tar came after and the memory of childhood came before"   (memory first in TIME)

Now noun-type position is UNINFORMATIVE. Solving it requires binding 'before'/'after' to the right
phrase across a long-range dependency -- i.e. role reading, not slot reading.

PRE-REGISTERED EXPECTATION (stated before the run, per the honest-expectation rule): if v23 was
positional, accuracy should FALL toward chance here. A drop is the EXPECTED, honest outcome.

Both guarantees measured and reported: word-multiset identity, and char-ngram bag residual.
"""
import sys, json, hashlib, pathlib, re
from collections import Counter
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
from app.runtime.open_weight.engine import (RuntimeLoadConfig, load_open_weight_runtime, capture_greedy_trajectory)
from app.runtime.open_weight.identity import LocalModelSnapshot

SP = pathlib.Path(__file__).resolve().parent
STORE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"

NOUNS = [
 ("scent of tar", "memory of childhood"),
 ("sound of the bell", "winter of her youth"),
 ("taste of burnt sugar", "kitchen of his mother"),
 ("smell of wet chalk", "classroom of that year"),
 ("creak of the gate", "summer of his boyhood"),
 ("colour of the dress", "evening of the party"),
 ("weight of the coat", "shape of his father"),
 ("hum of the engine", "drive along the coast"),
 ("grain of the wood", "hands of her grandfather"),
 ("chill of the water", "morning she had lost"),
 ("shape of the writing", "years of her schooling"),
 ("rhythm of the train", "town they had left"),
]
# SENSORY phrase is in slot 1 in BOTH members; only the temporal binding flips.
A = [f"the {s} came before and the {m} came after" for s, m in NOUNS]   # sensory earlier in time
B = [f"the {s} came after and the {m} came before" for s, m in NOUNS]   # memory earlier in time
PAIRS = list(zip(A, B))

WORD = re.compile(r"[a-z']+")
def wmultiset(x): return Counter(WORD.findall(x.lower()))
def ngmultiset(x, ns=(2, 3, 4)):
    t = x.lower(); c = Counter()
    for n in ns:
        for i in range(len(t)-n+1): c[t[i:i+n]] += 1
    return c

print("VERIFYING GUARANTEES ...", flush=True)
wbad = [i for i, (a, b) in enumerate(PAIRS) if wmultiset(a) != wmultiset(b)]
if wbad: print(f"ABORT: {len(wbad)} pairs not word-matched"); sys.exit(1)
print(f"  [1] word multisets identical in all {len(PAIRS)} pairs -> bag-of-words FORCED to 0.500")
resid = []
for a, b in PAIRS:
    ca, cb = ngmultiset(a), ngmultiset(b)
    resid.append((sum((ca-cb).values())+sum((cb-ca).values()))/(sum(ca.values())+sum(cb.values())))
print(f"  [2] char-ngram bag residual: mean {np.mean(resid):.5f}, max {max(resid):.5f}  (junction n-grams may differ)")
print(f"  [3] POSITION COUNTERBALANCED: the sensory phrase is in slot 1 in BOTH members of every pair")

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
def rv(p):
    cap = capture_greedy_trajectory(rt, scenario_id="v24", prompt=p, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)
RA = [rv(s) for s in A]; RB = [rv(s) for s in B]

def vecfrom(counter, voc):
    v = np.array([counter.get(k, 0) for k in voc], dtype=np.float64)
    n = np.linalg.norm(v); return v/n if n > 0 else v
def loo(fa, fb):
    ok = tot = 0
    for i in range(len(PAIRS)):
        tr = [j for j in range(len(PAIRS)) if j != i]
        ca = np.mean([fa(j) for j in tr], axis=0); cb = np.mean([fb(j) for j in tr], axis=0)
        for f, lab in ((fa(i), "A"), (fb(i), "B")):
            ok += (("A" if np.linalg.norm(f-ca) < np.linalg.norm(f-cb) else "B") == lab); tot += 1
    return ok/tot

voc_w = sorted(set(k for s in A+B for k in wmultiset(s)))
voc_n = sorted(set(k for s in A+B for k in ngmultiset(s)))
res = {"design": "COUNTERBALANCED role pairs -- sensory phrase in slot 1 in BOTH members; only temporal binding flips",
       "preregistered_expectation": "if v23 was positional, accuracy FALLS toward chance here",
       "model": "pythia-160m (reserialized, attested engine)", "n_pairs": len(PAIRS), "n_items": 2*len(PAIRS),
       "chance": 0.5, "protocol": "leave-one-PAIR-out nearest centroid", "layers": L,
       "position_counterbalanced": True,
       "char_ngram_bag_residual_mean": round(float(np.mean(resid)), 5),
       "char_ngram_bag_residual_max": round(float(max(resid)), 5)}
res["bag_of_words_baseline"] = round(loo(lambda j: vecfrom(wmultiset(A[j]), voc_w), lambda j: vecfrom(wmultiset(B[j]), voc_w)), 3)
res["char_ngram_baseline"] = round(loo(lambda j: vecfrom(ngmultiset(A[j]), voc_n), lambda j: vecfrom(ngmultiset(B[j]), voc_n)), 3)
per_layer = {li: round(loo(lambda j: RA[j][li], lambda j: RB[j][li]), 3) for li in range(L)}
bl = max(per_layer, key=per_layer.get)
res["activation_per_layer"] = per_layer
res["activation_best"] = per_layer[bl]; res["activation_best_layer"] = bl
res["activation_mean_over_layers"] = round(float(np.mean(list(per_layer.values()))), 3)
res["v23_comparison"] = {"v23_activation_best": 1.0, "v23_mean_over_layers": 0.938,
                         "delta_best": round(per_layer[bl]-1.0, 3),
                         "delta_mean": round(res["activation_mean_over_layers"]-0.938, 3)}
surf_max = max(res["char_ngram_baseline"], res["bag_of_words_baseline"])
gate = res["activation_best"] >= 0.70 and res["activation_best"] - surf_max >= 0.15
res["verdict"] = ("ROLE_STRUCTURE_READ (survives position counterbalance)" if gate else
                  ("ABOVE_CHANCE_BUT_UNDER_GATE" if res["activation_best"] > 0.6 else
                   "FELL_TO_CHANCE -- v23 was POSITIONAL, as pre-registered"))
raw = json.dumps(res, indent=2, sort_keys=True).encode()
(SP/"detector_v24_counterbalanced_results.json").write_bytes(raw)
print("\n==== COUNTERBALANCED PAIRS (position removed from the label) ====")
print(f"  bag-of-words baseline : {res['bag_of_words_baseline']:.3f}   char-ngram baseline: {res['char_ngram_baseline']:.3f}")
print(f"  activation best layer : {res['activation_best']:.3f} (L{bl})   mean over layers {res['activation_mean_over_layers']:.3f}")
print(f"  vs v23: best {res['v23_comparison']['delta_best']:+.3f}   mean {res['v23_comparison']['delta_mean']:+.3f}")
print(f"  VERDICT: {res['verdict']}")
print("sha256=" + hashlib.sha256(raw).hexdigest()[:16])
