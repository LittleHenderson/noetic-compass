"""V26 -- CAS-PINNED: the ^8/^9 role assignment under the v25 proof-level design ($0, attested engine).

v25 proved the instrument: on pairs where bag-of-words AND char-ngram are FORCED to chance and
position is counterbalanced, the model recovers a long-range binding at 1.000. But v25's task was
"which came earlier in time" -- not a CAS construct.

This points the SAME instrument at an actual CAS contrast. Canonical definitions (Clarification 1):
  ^8 Above/Cause  = an Idea that TRIGGERS a different Idea to come to Mind
  ^9 Below/Effect = the Idea BROUGHT TO MIND by that trigger

So the question is: which phrase is the TRIGGER (^8) and which is the ARRIVAL (^9)?

  A: "the {sensory} : triggered ; the {memory} : arrived ; done"   (sensory = ^8, memory = ^9)
  B: "the {sensory} : arrived ; the {memory} : triggered ; done"   (memory = ^8, sensory = ^9)

Identical word multisets. The ' : ' and ' ; ' separators give BOTH verbs identical local context, so
the char-ngram bags should match too. The sensory phrase is in slot 1 in BOTH members, so position
is uninformative. The ONLY signal is which phrase holds the ^8 role.

BLOCKING PRE-FLIGHT GATE: abort before loading the model unless word multisets identical AND
char-ngram bag residual <= 0.001.

PRE-REGISTERED HONESTY NOTE (write it before the result): a pass shows the model recovers the
TRIGGER-vs-ARRIVAL role assignment. CAS asserts (Clarification 1) that this relation IS ^8/^9, so
reading it is reading the CAS relation. A skeptic may answer that this is ordinary syntactic/
semantic role assignment that CAS has merely NAMED. That objection is legitimate and must be
recorded either way -- this test cannot settle it. What it CAN settle is whether the relation is
present and readable at all under proof-level surface control.
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
A = [f"the {s} : triggered ; the {m} : arrived ; done" for s, m in NOUNS]  # sensory = ^8
B = [f"the {s} : arrived ; the {m} : triggered ; done" for s, m in NOUNS]  # memory  = ^8
PAIRS = list(zip(A, B))

WORD = re.compile(r"[a-z']+")
def wm(x): return Counter(WORD.findall(x.lower()))
def ngm(x, ns=(2, 3, 4)):
    t = x.lower(); c = Counter()
    for n in ns:
        for i in range(len(t)-n+1): c[t[i:i+n]] += 1
    return c

print("=== BLOCKING PRE-FLIGHT GATE (before the model loads) ===", flush=True)
wbad = [i for i, (a, b) in enumerate(PAIRS) if wm(a) != wm(b)]
resid = []
for a, b in PAIRS:
    ca, cb = ngm(a), ngm(b)
    resid.append((sum((ca-cb).values())+sum((cb-ca).values()))/(sum(ca.values())+sum(cb.values())))
rmean, rmax = float(np.mean(resid)), float(max(resid))
print(f"  word-multiset mismatches : {len(wbad)}")
print(f"  char-ngram bag residual  : mean {rmean:.6f}  max {rmax:.6f}   (gate <= 0.001)")
print(f"  position counterbalanced : sensory phrase in slot 1 in BOTH members")
if wbad or rmax > 0.001:
    ex = PAIRS[0]; ca, cb = ngm(ex[0]), ngm(ex[1])
    print("\n  GATE FAILED -> ABORT (no compute spent).")
    print("  A-only:", dict(ca-cb), "\n  B-only:", dict(cb-ca)); sys.exit(1)
print("  GATE PASSED -> both surface baselines FORCED to 0.500.\n")

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
tok = rt.tokenizer
lenbad = sum(1 for a, b in PAIRS if len(tok.encode(a)) != len(tok.encode(b)))
print(f"  token-length mismatches  : {lenbad}/{len(PAIRS)}  (0 = no length artifact)")

def rv(p):
    cap = capture_greedy_trajectory(rt, scenario_id="v26", prompt=p, max_new_tokens=1, seed=0)
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
res = {"design": "CAS-PINNED ^8/^9 role assignment under the v25 proof-level design",
       "cas_mapping": "^8 Above/Cause = the TRIGGER phrase; ^9 Below/Effect = the ARRIVAL phrase (Clarification 1)",
       "skeptic_objection_preregistered": "a pass may be read as ordinary syntactic/semantic role assignment that CAS has NAMED; this test cannot settle that, and the objection is recorded either way",
       "model": "pythia-160m (reserialized, attested engine)", "n_pairs": len(PAIRS), "n_items": 2*len(PAIRS),
       "chance": 0.5, "protocol": "leave-one-PAIR-out nearest centroid", "layers": L,
       "position_counterbalanced": True, "token_length_mismatches": lenbad,
       "char_ngram_bag_residual_mean": round(rmean, 6), "char_ngram_bag_residual_max": round(rmax, 6),
       "preflight_gate": "PASSED"}
res["bag_of_words_baseline"] = round(loo(lambda j: vf(wm(A[j]), voc_w), lambda j: vf(wm(B[j]), voc_w)), 3)
res["char_ngram_baseline"] = round(loo(lambda j: vf(ngm(A[j]), voc_n), lambda j: vf(ngm(B[j]), voc_n)), 3)
pl = {li: round(loo(lambda j: RA[j][li], lambda j: RB[j][li]), 3) for li in range(L)}
bl = max(pl, key=pl.get)
res["activation_per_layer"] = pl; res["activation_best"] = pl[bl]; res["activation_best_layer"] = bl
res["activation_mean_over_layers"] = round(float(np.mean(list(pl.values()))), 3)
sm = max(res["char_ngram_baseline"], res["bag_of_words_baseline"])
gate = res["activation_best"] >= 0.70 and res["activation_best"]-sm >= 0.15
res["verdict"] = ("CAS_8_9_ROLE_READ_UNDER_PROOF_LEVEL_CONTROL" if gate
                  else ("WEAK_ABOVE_CHANCE" if res["activation_best"] > 0.6 else "NOT_READ -- falls to chance"))
raw = json.dumps(res, indent=2, sort_keys=True).encode()
(SP/"detector_v26_cas_pinned_results.json").write_bytes(raw)
print("\n==== CAS-PINNED ^8/^9 ROLE ASSIGNMENT ====")
print(f"  bag-of-words {res['bag_of_words_baseline']:.3f}   char-ngram {res['char_ngram_baseline']:.3f}   (both forced)")
print(f"  activation best {res['activation_best']:.3f} (L{bl})   mean over layers {res['activation_mean_over_layers']:.3f}")
print(f"  VERDICT: {res['verdict']}")
print("sha256=" + hashlib.sha256(raw).hexdigest()[:16])
