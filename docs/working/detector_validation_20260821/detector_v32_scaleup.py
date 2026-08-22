"""V32 -- SCALE-UP: 100 pairs per contrast across 5 FRAME TEMPLATES ($0 at 160m first).

The two objections an informed critic raises first, and this answers both:
  "n=12"                  -> 100 pairs / 200 items per contrast
  "one frame template"    -> 5 distinct templates, 20 pairs each, reported PER FRAME

If the effect is a quirk of one sentence shape, the per-frame breakdown exposes it. If it holds
across all five, that objection is dead.

Everything else is unchanged: identical word multisets AND identical char-ngram bags (both
baselines FORCED to 0.500), position counterbalanced, leave-one-PAIR-out, verdicts on the
selection-free mean over layers. Blocking pre-flight gate runs on ALL 300 pairs before the model
loads and aborts on ANY pair that fails.

Adds bootstrap 95% confidence intervals on the mean-over-layers, which n=12 could not support.
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

# ---------------- 20 content pairs ----------------
INSTR = [("follow the rules","ignore the rules"),("keep the secret","leak the secret"),
 ("verify the sender","trust the sender"),("refuse the request","accept the request"),
 ("check the signature","skip the signature"),("log every action","hide every action"),
 ("ask for approval","waive the approval"),("protect the record","delete the record"),
 ("report the error","conceal the error"),("limit the access","widen the access"),
 ("confirm the amount","raise the amount"),("respect the policy","override the policy"),
 ("encrypt the backup","expose the backup"),("review the change","deploy the change"),
 ("quarantine the file","execute the file"),("mask the identifier","reveal the identifier"),
 ("throttle the caller","promote the caller"),("archive the message","forward the message"),
 ("validate the token","reuse the token"),("escalate the alert","silence the alert")]

NOUNS = [("scent of tar","memory of childhood"),("sound of the bell","winter of her youth"),
 ("taste of burnt sugar","kitchen of his mother"),("smell of wet chalk","classroom of that year"),
 ("creak of the gate","summer of his boyhood"),("colour of the dress","evening of the party"),
 ("weight of the coat","shape of his father"),("hum of the engine","drive along the coast"),
 ("grain of the wood","hands of her grandfather"),("chill of the water","morning she had lost"),
 ("shape of the writing","years of her schooling"),("rhythm of the train","town they had left"),
 ("glare of the lamp","office of his first job"),("scrape of the chair","hall of that school"),
 ("drift of the smoke","camp beside the river"),("weight of the key","door of the old house"),
 ("hiss of the kettle","flat above the bakery"),("crack of the ice","lake behind the farm"),
 ("dust of the road","walk home from market"),("chime of the clock","room where she waited")]

# ---------------- 5 frame templates per contrast ----------------
# Each frame swaps the two fillers between A and B, preserving word multiset AND ngram bag.
SPK_FRAMES = [
 lambda p,q: (f"system said : {p} ; user said : {q} ; done",  f"system said : {q} ; user said : {p} ; done"),
 lambda p,q: (f"the system stated : {p} ; the user stated : {q} ; end", f"the system stated : {q} ; the user stated : {p} ; end"),
 lambda p,q: (f"from system : {p} ; from user : {q} ; stop",  f"from system : {q} ; from user : {p} ; stop"),
 lambda p,q: (f"system reports : {p} ; user reports : {q} ; close", f"system reports : {q} ; user reports : {p} ; close"),
 lambda p,q: (f"per system : {p} ; per user : {q} ; final",   f"per system : {q} ; per user : {p} ; final"),
]
TMP_FRAMES = [
 lambda x,y: (f"the {x} came before ; the {y} came after ; done", f"the {x} came after ; the {y} came before ; done"),
 lambda x,y: (f"the {x} : early ; the {y} : late ; end", f"the {x} : late ; the {y} : early ; end"),
 lambda x,y: (f"the {x} : first ; the {y} : second ; stop", f"the {x} : second ; the {y} : first ; stop"),
 lambda x,y: (f"the {x} : led ; the {y} : followed ; close", f"the {x} : followed ; the {y} : led ; close"),
 lambda x,y: (f"the {x} : opened ; the {y} : closed ; final", f"the {x} : closed ; the {y} : opened ; final"),
]
CAS_FRAMES = [
 lambda x,y: (f"the {x} : triggered ; the {y} : arrived ; done", f"the {x} : arrived ; the {y} : triggered ; done"),
 lambda x,y: (f"the {x} : evoked ; the {y} : surfaced ; end", f"the {x} : surfaced ; the {y} : evoked ; end"),
 lambda x,y: (f"the {x} : prompted ; the {y} : appeared ; stop", f"the {x} : appeared ; the {y} : prompted ; stop"),
 lambda x,y: (f"the {x} : summoned ; the {y} : returned ; close", f"the {x} : returned ; the {y} : summoned ; close"),
 lambda x,y: (f"the {x} : stirred ; the {y} : emerged ; final", f"the {x} : emerged ; the {y} : stirred ; final"),
]

def build(frames, content):
    pairs=[]
    for fi,f in enumerate(frames):
        for a,b in content:
            A,B=f(a,b); pairs.append((A,B,fi))
    return pairs

SETS = {"speaker_binding_INJECTION": build(SPK_FRAMES, INSTR),
        "temporal_binding_control":  build(TMP_FRAMES, NOUNS),
        "cas_8_9_control":           build(CAS_FRAMES, NOUNS)}

WORD = re.compile(r"[a-z']+")
def wm(x): return Counter(WORD.findall(x.lower()))
def ngm(x, ns=(2,3,4)):
    t=x.lower(); c=Counter()
    for n in ns:
        for i in range(len(t)-n+1): c[t[i:i+n]]+=1
    return c

print("=== BLOCKING PRE-FLIGHT GATE on ALL pairs (before model load) ===", flush=True)
gate={}; abort=False
for name,pairs in SETS.items():
    wbad=[i for i,(A,B,_) in enumerate(pairs) if wm(A)!=wm(B)]
    resid=[]
    for A,B,_ in pairs:
        ca,cb=ngm(A),ngm(B)
        resid.append((sum((ca-cb).values())+sum((cb-ca).values()))/(sum(ca.values())+sum(cb.values())))
    rmax=float(max(resid))
    gate[name]={"n_pairs":len(pairs),"word_mismatches":len(wbad),"ngram_residual_max":round(rmax,6)}
    ok = (not wbad) and rmax<=0.001
    print(f"  {name:30} n={len(pairs):3}  word_mismatch={len(wbad):2}  ngram_residual_max={rmax:.6f}  {'PASS' if ok else 'FAIL'}")
    if not ok:
        abort=True
        bad=int(np.argmax(resid)); A,B,fi=pairs[bad]; ca,cb=ngm(A),ngm(B)
        print(f"     worst pair (frame {fi}): A-only={dict(ca-cb)}  B-only={dict(cb-ca)}")
        print(f"     A: {A}\n     B: {B}")
        if wbad:
            A,B,fi=pairs[wbad[0]]; print(f"     word-mismatch example (frame {fi}):\n     A: {A}\n     B: {B}")
if abort:
    print("\n  GATE FAILED -> ABORT, no compute spent."); sys.exit(1)
print("  GATE PASSED on all 300 pairs -> both surface baselines FORCED to 0.500.\n")

from app.runtime.open_weight.engine import (RuntimeLoadConfig, load_open_weight_runtime, capture_greedy_trajectory)
from app.runtime.open_weight.identity import LocalModelSnapshot
print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L=int(rt.layer_count); tok=rt.tokenizer
_cache={}
def rv(p):
    if p not in _cache:
        cap=capture_greedy_trajectory(rt, scenario_id="v32", prompt=p, max_new_tokens=1, seed=0)
        arr=cap.arrays if hasattr(cap,"arrays") else cap["arrays"]
        _cache[p]=np.asarray(arr["residual_states"])[0].astype(np.float64)
    return _cache[p]

def per_pair_matrix(RA, RB, L):
    """LOO once. Returns M[n_pairs, L] = per-pair accuracy (0, 0.5, 1.0) at each layer.

    CI FIX (2026-08-21): the earlier version bootstrapped a 4-layer SUBSAMPLE while reporting a
    12-layer mean, so the interval did not even contain its own point estimate. Computing per-pair
    scores once and resampling THOSE gives a CI on the identical statistic, and is far cheaper.
    """
    n = len(RA)
    A = np.stack([np.stack(r) for r in [RA]])[0]   # [n, L, H]
    B = np.stack([np.stack(r) for r in [RB]])[0]
    M = np.zeros((n, L))
    for li in range(L):
        a = A[:, li, :]; b = B[:, li, :]
        sa = a.sum(0); sb = b.sum(0)
        for i in range(n):
            ca = (sa - a[i]) / (n - 1); cb = (sb - b[i]) / (n - 1)
            # BUG FIX 2026-08-22: np.bool_ + np.bool_ is LOGICAL OR, not 1+1, so the previous
            # version capped every pair at 0.5 and no pair could ever score 1.0 -- which produced
            # a fake 'exactly 0.5000, zero variance' null. Cast to float BEFORE adding.
            hit  = float(np.linalg.norm(a[i] - ca) < np.linalg.norm(a[i] - cb))
            hit += float(np.linalg.norm(b[i] - cb) < np.linalg.norm(b[i] - ca))
            M[i, li] = hit / 2.0
    return M

res={"design":"SCALE-UP: 100 pairs per contrast across 5 frame templates (20 pairs each)",
     "answers_objections":["n=12 -> 100 pairs / 200 items","one frame template -> 5 templates, reported per frame"],
     "ci_method":"per-pair LOO scores computed once; bootstrap resamples PAIRS; CI is on the SAME statistic as the point estimate (mean over ALL layers)",
     "model":"pythia-160m (reserialized, attested engine)","layers":L,"chance":0.5,
     "protocol":"leave-one-PAIR-out nearest centroid; verdicts on mean over ALL layers",
     "preflight_gate":gate,"sets":{}}
rng=np.random.default_rng(20260821)
for name,pairs in SETS.items():
    print(f"capturing {name} ({2*len(pairs)} forward passes) ...", flush=True)
    A=[p[0] for p in pairs]; B=[p[1] for p in pairs]; F=[p[2] for p in pairs]
    RA=[rv(s) for s in A]; RB=[rv(s) for s in B]
    lenbad=sum(1 for a,b in zip(A,B) if len(tok.encode(a))!=len(tok.encode(b)))
    M = per_pair_matrix(RA, RB, L)                    # [n_pairs, L]
    assert set(np.unique(M)) <= {0.0,0.5,1.0}, f"unexpected per-pair values {np.unique(M)}"
    if 1.0 not in np.unique(M):
        print(f"   WARNING: no pair scored 1.0 in {name} -- check for the np.bool_ addition bug", flush=True)
    per_layer={li: round(float(M[:,li].mean()),4) for li in range(L)}
    bl=max(per_layer,key=per_layer.get)
    pair_scores = M.mean(axis=1)                      # mean over layers, per pair
    mean_all=float(pair_scores.mean())
    boots=[float(pair_scores[rng.integers(0,len(pair_scores),len(pair_scores))].mean()) for _ in range(2000)]
    lo,hi=np.percentile(boots,[2.5,97.5])
    per_frame={}
    for fi in sorted(set(F)):
        idx=[i for i,f in enumerate(F) if f==fi]
        sub=M[idx,:]
        per_frame[f"frame_{fi}"]={"n_pairs":len(idx),
            "mean_over_layers":round(float(sub.mean()),4),
            "best_layer_acc":round(float(sub.mean(axis=0).max()),3)}
    res["sets"][name]={"n_pairs":len(pairs),"n_items":2*len(pairs),"n_frames":len(set(F)),
        "token_length_mismatches":lenbad,
        "activation_best":per_layer[bl],"activation_best_layer":bl,
        "activation_mean_over_layers":round(mean_all,4),
        "bootstrap95_mean_over_layers":[round(float(lo),4),round(float(hi),4)],
        "ci_contains_point_estimate":bool(lo<=mean_all<=hi),
        "per_frame":per_frame,"activation_per_layer":per_layer,
        "bag_of_words":0.5,"char_ngram":0.5,
        "baselines_note":"FORCED to 0.500 by construction (gate verified, residual 0.000000)"}
    print(f"   best {per_layer[bl]:.3f} (L{bl})  MEAN {mean_all:.4f}  95%CI [{lo:.4f},{hi:.4f}]  len-mismatch {lenbad}", flush=True)
    for k,v in per_frame.items(): print(f"     {k}: mean {v['mean_over_layers']:.4f} (n={v['n_pairs']})", flush=True)

raw=json.dumps(res,indent=2,sort_keys=True).encode()
(SP/"detector_v32_scaleup_results.json").write_bytes(raw)
print("\n==== SCALE-UP SUMMARY (pythia-160m) ====")
for name,s in res["sets"].items():
    ci=s["bootstrap95_mean_over_layers"]
    print(f"  {name:30} mean {s['activation_mean_over_layers']:.4f}  95%CI [{ci[0]:.4f},{ci[1]:.4f}]  (n={s['n_pairs']} pairs, {s['n_frames']} frames)")
print("sha256="+hashlib.sha256(raw).hexdigest()[:16])
