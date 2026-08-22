"""V22 -- MATCHED MINIMAL PAIRS: the one test a lexicon CANNOT pass ($0, attested engine, 160m).

Every reading result this session died because the stimuli were solvable from words alone (v19-v21).
This is the fix the spec sheet has flagged as missing since L3 ("INCONCLUSIVE BY DESIGN"): ROLE-SWAP
pairs built from an IDENTICAL WORD MULTISET.

  A: "The scent of pine tar pulled his whole childhood back up"   (sensory cue is the TRIGGER)
  B: "His whole childhood pulled the scent of pine tar back up"   (memory is the TRIGGER)

Same words, different structure. A bag-of-words model is MATHEMATICALLY FORCED to tie at chance.
A hand lexicon is forced to tie. Only a reader sensitive to ORDER/ROLE can split them. So any
activation accuracy above chance here is BEYOND-LEXICAL by construction.

The multiset identity is VERIFIED IN CODE and the run ABORTS if any pair fails.
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

# A = sensory cue is the TRIGGER ; B = memory is the TRIGGER. Identical word multisets.
PAIRS = [
 ("The scent of pine tar pulled his whole childhood back up",
  "His whole childhood pulled the scent of pine tar back up"),
 ("The sound of that bell dragged her first winter into view",
  "Her first winter dragged the sound of that bell into view"),
 ("The taste of burnt sugar carried the old kitchen to him",
  "The old kitchen carried the taste of burnt sugar to him"),
 ("The smell of wet chalk summoned that classroom for her",
  "That classroom summoned the smell of wet chalk for her"),
 ("The creak of the gate opened his entire summer again",
  "His entire summer opened the creak of the gate again"),
 ("The colour of that dress returned the whole evening to her",
  "The whole evening returned the colour of that dress to her"),
 ("The weight of the old coat brought his father near",
  "His father brought the weight of the old coat near"),
 ("The hum of the engine unlocked that long drive for him",
  "That long drive unlocked the hum of the engine for him"),
 ("The grain of the wood recalled her grandfather at once",
  "Her grandfather recalled the grain of the wood at once"),
 ("The chill of the water woke that lost morning in him",
  "That lost morning woke the chill of the water in him"),
 ("The shape of the handwriting raised her whole youth again",
  "Her whole youth raised the shape of the handwriting again"),
 ("The rhythm of the train loosened his early years there",
  "His early years loosened the rhythm of the train there"),
]

WORD = re.compile(r"[a-z']+")
def wmultiset(s): return Counter(WORD.findall(s.lower()))

print("verifying identical word multisets ...", flush=True)
bad = [(i, a, b) for i, (a, b) in enumerate(PAIRS) if wmultiset(a) != wmultiset(b)]
if bad:
    for i, a, b in bad:
        d1 = wmultiset(a) - wmultiset(b); d2 = wmultiset(b) - wmultiset(a)
        print(f"  PAIR {i} MISMATCH  A-only={dict(d1)}  B-only={dict(d2)}")
    print(f"ABORT: {len(bad)}/{len(PAIRS)} pairs are not word-matched. Fix before running.")
    sys.exit(1)
print(f"  OK: all {len(PAIRS)} pairs have IDENTICAL word multisets -> any bag-of-words rule MUST tie at 0.500")

A = [a for a, b in PAIRS]; B = [b for a, b in PAIRS]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)

def resid(p):
    cap = capture_greedy_trajectory(rt, scenario_id="v22", prompt=p, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)

RA = [resid(s) for s in A]; RB = [resid(s) for s in B]

def bow(s, voc):
    c = wmultiset(s); v = np.array([c.get(w, 0) for w in voc], dtype=np.float64)
    n = np.linalg.norm(v); return v/n if n > 0 else v
def cng(s, voc):
    t = s.lower(); c = {}
    for n in (2, 3, 4):
        for i in range(len(t)-n+1): c[t[i:i+n]] = c.get(t[i:i+n], 0) + 1
    v = np.array([c.get(g, 0) for g in voc], dtype=np.float64)
    z = np.linalg.norm(v); return v/z if z > 0 else v
def cngvoc(ss):
    s = set()
    for t in ss:
        t = t.lower()
        for n in (2, 3, 4):
            for i in range(len(t)-n+1): s.add(t[i:i+n])
    return sorted(s)

# LEAVE-ONE-PAIR-OUT: train on the other 11 pairs, test on the held-out pair (both sentences)
def loo(featA, featB):
    ok = tot = 0
    for i in range(len(PAIRS)):
        tr = [j for j in range(len(PAIRS)) if j != i]
        ca = np.mean([featA(j) for j in tr], axis=0); cb = np.mean([featB(j) for j in tr], axis=0)
        for f, lab in ((featA(i), "A"), (featB(i), "B")):
            pred = "A" if np.linalg.norm(f-ca) < np.linalg.norm(f-cb) else "B"
            ok += (pred == lab); tot += 1
    return ok/tot

res = {"design": "role-swap matched minimal pairs; identical word multisets VERIFIED in code",
       "model": "pythia-160m (reserialized, attested engine)", "n_pairs": len(PAIRS),
       "n_items": 2*len(PAIRS), "chance": 0.5,
       "protocol": "leave-one-PAIR-out nearest centroid", "layers": L}
per_layer = {}
for li in range(L):
    per_layer[li] = round(loo(lambda j: RA[j][li], lambda j: RB[j][li]), 3)
best_layer = max(per_layer, key=per_layer.get)
res["activation_per_layer"] = per_layer
res["activation_best"] = per_layer[best_layer]
res["activation_best_layer"] = best_layer
res["activation_mean_over_layers"] = round(float(np.mean(list(per_layer.values()))), 3)
voc_w = sorted(set(w for s in A+B for w in wmultiset(s)))
res["bag_of_words_baseline"] = round(loo(lambda j: bow(A[j], voc_w), lambda j: bow(B[j], voc_w)), 3)
voc_c = cngvoc(A+B)
res["char_ngram_baseline"] = round(loo(lambda j: cng(A[j], voc_c), lambda j: cng(B[j], voc_c)), 3)
gate = res["activation_best"] >= 0.70 and res["activation_best"] - res["char_ngram_baseline"] >= 0.15
res["verdict"] = ("BEYOND_LEXICAL_STRUCTURE_READ" if gate else
                  ("ABOVE_CHANCE_BUT_UNDER_GATE" if res["activation_best"] > 0.5 else "NO_STRUCTURAL_READ"))
res["gate"] = "BEYOND-LEXICAL iff best-layer activation >= 0.70 AND beats char-ngram by >= 0.15"
raw = json.dumps(res, indent=2, sort_keys=True).encode()
(SP/"detector_v22_minimal_pairs_results.json").write_bytes(raw)
print("\n==== MATCHED MINIMAL PAIRS (role-swap, identical word multisets) ====")
print(f"  bag-of-words baseline : {res['bag_of_words_baseline']:.3f}   (MUST be 0.500 by construction)")
print(f"  char-ngram baseline   : {res['char_ngram_baseline']:.3f}   (can exceed 0.5 -- captures local order)")
print(f"  activation best layer : {res['activation_best']:.3f} (L{best_layer})   mean over layers {res['activation_mean_over_layers']:.3f}")
print(f"  VERDICT: {res['verdict']}")
print("sha256=" + hashlib.sha256(raw).hexdigest()[:16])
