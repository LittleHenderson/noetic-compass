"""V23 -- ORDER-MATCHED minimal pairs: force CHAR N-GRAMS to tie as well ($0, attested engine, 160m).

v22 proved the activations beat any WORD-based rule (bag-of-words pinned at 0.500 by construction),
but char n-grams reached 0.875 -- so word-ORDER statistics were not ruled out.

This closes that hole. Design: put the role difference at a range LONGER than the n-gram window,
inside a symmetric frame, so BOTH members contain the SAME BAG of char n-grams:

  A: "the scent of tar came first and the memory of childhood came second"
  B: "the memory of childhood came first and the scent of tar came second"

A bag of n-grams records WHICH n-grams occur, not which were adjacent to which. Both sentences
contain one "came first" and one "came second" and both noun phrases, so the BAGS are (near)
identical -- while the ROLE assignment (which came first) is only recoverable from long-range order.

BOTH guarantees are VERIFIED IN CODE and the run reports the exact residual n-gram distance.
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

# A = sensory cue came FIRST (cue is the trigger) ; B = memory came FIRST. Symmetric frame.
FRAME = "the {x} came first and the {y} came second"
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
PAIRS = [(FRAME.format(x=a, y=b), FRAME.format(x=b, y=a)) for a, b in NOUNS]

WORD = re.compile(r"[a-z']+")
def wmultiset(s): return Counter(WORD.findall(s.lower()))
def ngmultiset(s, ns=(2, 3, 4)):
    t = s.lower(); c = Counter()
    for n in ns:
        for i in range(len(t)-n+1): c[t[i:i+n]] += 1
    return c

print("VERIFYING BOTH GUARANTEES ...", flush=True)
wbad = [i for i, (a, b) in enumerate(PAIRS) if wmultiset(a) != wmultiset(b)]
if wbad:
    print(f"ABORT: {len(wbad)} pairs not word-matched"); sys.exit(1)
print(f"  [1] word multisets identical in all {len(PAIRS)} pairs -> bag-of-words MUST tie at 0.500")
# n-gram residual: how different are the char-ngram bags within a pair?
resid = []
for a, b in PAIRS:
    ca, cb = ngmultiset(a), ngmultiset(b)
    diff = sum((ca-cb).values()) + sum((cb-ca).values())
    total = sum(ca.values()) + sum(cb.values())
    resid.append(diff/total)
print(f"  [2] char-ngram bag residual within pairs: mean {np.mean(resid):.4f}, max {max(resid):.4f}")
print(f"      (0.0000 = bags identical -> char-ngram FORCED to 0.500 too)")

A = [a for a, b in PAIRS]; B = [b for a, b in PAIRS]
print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
def resid_vec(p):
    cap = capture_greedy_trajectory(rt, scenario_id="v23", prompt=p, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)
RA = [resid_vec(s) for s in A]; RB = [resid_vec(s) for s in B]

def vecfrom(counter, voc):
    v = np.array([counter.get(k, 0) for k in voc], dtype=np.float64)
    n = np.linalg.norm(v); return v/n if n > 0 else v
def loo(fa, fb):
    ok = tot = 0
    for i in range(len(PAIRS)):
        tr = [j for j in range(len(PAIRS)) if j != i]
        ca = np.mean([fa(j) for j in tr], axis=0); cb = np.mean([fb(j) for j in tr], axis=0)
        for f, lab in ((fa(i), "A"), (fb(i), "B")):
            pred = "A" if np.linalg.norm(f-ca) < np.linalg.norm(f-cb) else "B"
            ok += (pred == lab); tot += 1
    return ok/tot

voc_w = sorted(set(k for s in A+B for k in wmultiset(s)))
voc_n = sorted(set(k for s in A+B for k in ngmultiset(s)))
res = {"design": "ORDER-MATCHED role-swap inside a symmetric frame; word multisets AND char-ngram bags matched",
       "model": "pythia-160m (reserialized, attested engine)", "n_pairs": len(PAIRS), "n_items": 2*len(PAIRS),
       "chance": 0.5, "protocol": "leave-one-PAIR-out nearest centroid", "layers": L,
       "char_ngram_bag_residual_mean": round(float(np.mean(resid)), 5),
       "char_ngram_bag_residual_max": round(float(max(resid)), 5)}
res["bag_of_words_baseline"] = round(loo(lambda j: vecfrom(wmultiset(A[j]), voc_w), lambda j: vecfrom(wmultiset(B[j]), voc_w)), 3)
res["char_ngram_baseline"] = round(loo(lambda j: vecfrom(ngmultiset(A[j]), voc_n), lambda j: vecfrom(ngmultiset(B[j]), voc_n)), 3)
per_layer = {li: round(loo(lambda j: RA[j][li], lambda j: RB[j][li]), 3) for li in range(L)}
best_layer = max(per_layer, key=per_layer.get)
res["activation_per_layer"] = per_layer
res["activation_best"] = per_layer[best_layer]; res["activation_best_layer"] = best_layer
res["activation_mean_over_layers"] = round(float(np.mean(list(per_layer.values()))), 3)
gate = res["activation_best"] >= 0.70 and res["activation_best"] - max(res["char_ngram_baseline"], res["bag_of_words_baseline"]) >= 0.15
res["verdict"] = ("ORDER_STRUCTURE_READ_BEYOND_SURFACE" if gate else
                  ("ABOVE_CHANCE_BUT_UNDER_GATE" if res["activation_best"] > 0.5 else "NO_STRUCTURAL_READ"))
res["gate"] = "PASS iff best-layer activation >= 0.70 AND beats BOTH surface baselines by >= 0.15"
raw = json.dumps(res, indent=2, sort_keys=True).encode()
(SP/"detector_v23_order_matched_results.json").write_bytes(raw)
print("\n==== ORDER-MATCHED MINIMAL PAIRS ====")
print(f"  bag-of-words baseline : {res['bag_of_words_baseline']:.3f}  (forced to 0.500 by construction)")
print(f"  char-ngram baseline   : {res['char_ngram_baseline']:.3f}  (bag residual {res['char_ngram_bag_residual_mean']:.5f})")
print(f"  activation best layer : {res['activation_best']:.3f} (L{best_layer})   mean over layers {res['activation_mean_over_layers']:.3f}")
print(f"  VERDICT: {res['verdict']}")
print("sha256=" + hashlib.sha256(raw).hexdigest()[:16])
