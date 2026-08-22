"""V25 -- COUNTERBALANCED v2: position removed AND the junction leak closed ($0, attested engine).

v24 failed: 'before and' vs 'after and' differ as n-grams, so a char-counter scored 1.000 and the
test proved nothing (residual 0.02776).

FIX (v25b): give BOTH markers an IDENTICAL local context. v25a still leaked because the
sentence-final ";" has no trailing char, so "before ; " gave the 4-gram "e ; " while "after ; " gave
"r ; ". Appending a trailing token ("done") puts a following character after BOTH markers, so each
sentence contains "e ; " and "r ; " and " ; t" and " ; d" exactly once -- bags match.
  A: "the scent of tar came before ; the memory of childhood came after ; done"
  B: "the scent of tar came after ; the memory of childhood came before ; done"
Each sentence now contains exactly one "came before ;" and one "came after ;", and each noun phrase
is followed by " came" in both -- so the n-gram BAGS should be identical while the BINDING differs.

Position stays counterbalanced: the sensory phrase is in slot 1 in BOTH members.
So the ONLY way to solve this is to bind before/after to the correct phrase across a long-range
dependency -- genuine role/binding reading, not slot reading and not surface counting.

BLOCKING GATE (the v24 lesson): abort BEFORE loading the model unless
  word multisets identical AND char-ngram bag residual <= 0.001.

PRE-REGISTERED EXPECTATION: if v23 was purely positional, accuracy here FALLS toward chance.
A fall is the honest expected outcome and will be reported as such.
"""
import sys, json, hashlib, pathlib, re
from collections import Counter
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
SP = pathlib.Path(__file__).resolve().parent
STORE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"

NOUNS = [
 ("scent of tar", "memory of childhood"), ("sound of the bell", "winter of her youth"),
 ("taste of burnt sugar", "kitchen of his mother"), ("smell of wet chalk", "classroom of that year"),
 ("creak of the gate", "summer of his boyhood"), ("colour of the dress", "evening of the party"),
 ("weight of the coat", "shape of his father"), ("hum of the engine", "drive along the coast"),
 ("grain of the wood", "hands of her grandfather"), ("chill of the water", "morning she had lost"),
 ("shape of the writing", "years of her schooling"), ("rhythm of the train", "town they had left"),
]
A = [f"the {s} came before ; the {m} came after ; done" for s, m in NOUNS]
B = [f"the {s} came after ; the {m} came before ; done" for s, m in NOUNS]
PAIRS = list(zip(A, B))

WORD = re.compile(r"[a-z']+")
def wm(x): return Counter(WORD.findall(x.lower()))
def ngm(x, ns=(2, 3, 4)):
    t = x.lower(); c = Counter()
    for n in ns:
        for i in range(len(t)-n+1): c[t[i:i+n]] += 1
    return c

print("=== BLOCKING PRE-FLIGHT GATE (runs BEFORE the model is loaded) ===", flush=True)
wbad = [i for i, (a, b) in enumerate(PAIRS) if wm(a) != wm(b)]
print(f"  word-multiset mismatches: {len(wbad)}")
resid = []
for a, b in PAIRS:
    ca, cb = ngm(a), ngm(b)
    resid.append((sum((ca-cb).values())+sum((cb-ca).values()))/(sum(ca.values())+sum(cb.values())))
rmean, rmax = float(np.mean(resid)), float(max(resid))
print(f"  char-ngram bag residual: mean {rmean:.6f}  max {rmax:.6f}   (gate: <= 0.001)")
print(f"  position counterbalanced: sensory phrase in slot 1 in BOTH members")
if wbad or rmax > 0.001:
    print("\n  GATE FAILED -> ABORT. Not spending compute on a surface-solvable set.")
    ex = PAIRS[0]; ca, cb = ngm(ex[0]), ngm(ex[1])
    print("  A-only n-grams:", dict((ca-cb)), "\n  B-only n-grams:", dict((cb-ca)))
    sys.exit(1)
print("  GATE PASSED -> both surface baselines are FORCED to 0.500. Proceeding.\n")

from app.runtime.open_weight.engine import (RuntimeLoadConfig, load_open_weight_runtime, capture_greedy_trajectory)
from app.runtime.open_weight.identity import LocalModelSnapshot
print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
def rv(p):
    cap = capture_greedy_trajectory(rt, scenario_id="v25", prompt=p, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)
RA = [rv(s) for s in A]; RB = [rv(s) for s in B]

def vf(c, voc):
    v = np.array([c.get(k, 0) for k in voc], dtype=np.float64); n = np.linalg.norm(v)
    return v/n if n > 0 else v
def loo(fa, fb):
    ok = tot = 0
    for i in range(len(PAIRS)):
        tr = [j for j in range(len(PAIRS)) if j != i]
        ca = np.mean([fa(j) for j in tr], axis=0); cb = np.mean([fb(j) for j in tr], axis=0)
        for f, lab in ((fa(i), "A"), (fb(i), "B")):
            ok += (("A" if np.linalg.norm(f-ca) < np.linalg.norm(f-cb) else "B") == lab); tot += 1
    return ok/tot
voc_w = sorted(set(k for s in A+B for k in wm(s)))
voc_n = sorted(set(k for s in A+B for k in ngm(s)))
res = {"design": "COUNTERBALANCED v2 -- position removed AND junction leak closed; only long-range before/after BINDING differs",
       "preregistered_expectation": "if v23 was purely positional, accuracy FALLS toward chance here",
       "model": "pythia-160m (reserialized, attested engine)", "n_pairs": len(PAIRS), "n_items": 2*len(PAIRS),
       "chance": 0.5, "protocol": "leave-one-PAIR-out nearest centroid", "layers": L,
       "position_counterbalanced": True,
       "char_ngram_bag_residual_mean": round(rmean, 6), "char_ngram_bag_residual_max": round(rmax, 6),
       "preflight_gate": "PASSED (word multisets identical AND ngram residual <= 0.001)"}
res["bag_of_words_baseline"] = round(loo(lambda j: vf(wm(A[j]), voc_w), lambda j: vf(wm(B[j]), voc_w)), 3)
res["char_ngram_baseline"] = round(loo(lambda j: vf(ngm(A[j]), voc_n), lambda j: vf(ngm(B[j]), voc_n)), 3)
pl = {li: round(loo(lambda j: RA[j][li], lambda j: RB[j][li]), 3) for li in range(L)}
bl = max(pl, key=pl.get)
res["activation_per_layer"] = pl; res["activation_best"] = pl[bl]; res["activation_best_layer"] = bl
res["activation_mean_over_layers"] = round(float(np.mean(list(pl.values()))), 3)
res["comparison"] = {"v23_best_positional": 1.0, "v23_mean": 0.938,
                     "delta_best_vs_v23": round(pl[bl]-1.0, 3),
                     "delta_mean_vs_v23": round(res["activation_mean_over_layers"]-0.938, 3)}
sm = max(res["char_ngram_baseline"], res["bag_of_words_baseline"])
gate = res["activation_best"] >= 0.70 and res["activation_best"]-sm >= 0.15
res["verdict"] = ("ROLE_BINDING_READ -- survives position counterbalance AND surface match" if gate
                  else ("WEAK_ABOVE_CHANCE" if res["activation_best"] > 0.6
                        else "FELL_TO_CHANCE -- v23 was POSITIONAL, as pre-registered"))
raw = json.dumps(res, indent=2, sort_keys=True).encode()
(SP/"detector_v25_counterbalanced_v2_results.json").write_bytes(raw)
print("\n==== COUNTERBALANCED v2 (position removed, surfaces matched) ====")
print(f"  bag-of-words {res['bag_of_words_baseline']:.3f}   char-ngram {res['char_ngram_baseline']:.3f}   (both forced to 0.500)")
print(f"  activation best {res['activation_best']:.3f} (L{bl})   mean over layers {res['activation_mean_over_layers']:.3f}")
print(f"  vs v23: best {res['comparison']['delta_best_vs_v23']:+.3f}  mean {res['comparison']['delta_mean_vs_v23']:+.3f}")
print(f"  VERDICT: {res['verdict']}")
print("sha256=" + hashlib.sha256(raw).hexdigest()[:16])
