"""Multi-axis detector validation -- two CAS involution pairs on real weights.

Extends the ^2/^3 (valence) result to a second axis, ^8 Above/Cause vs ^9
Below/Effect (associative trigger vs the idea it lands), through the same
attested engine. Cross-topic split, same two detectors, same two null
controls. Real weights, local CPU, $0, no pod. See PREREG (v1) for the method.
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

# Axis 1: ^2 Positive / ^3 Negative (valence) -- reference, 12 topics.
VALENCE = [
    ("The meal was delicious and satisfying",   "The meal was rotten and revolting"),
    ("The song was beautiful and uplifting",    "The song was grating and unbearable"),
    ("The morning was bright and pleasant",     "The morning was bleak and miserable"),
    ("Her manner was warm and kind",            "Her manner was cold and cruel"),
    ("The report brought hopeful news",         "The report brought dreadful news"),
    ("The room was cozy and inviting",          "The room was filthy and menacing"),
    ("The project was a splendid success",      "The project was an appalling failure"),
    ("The dog was gentle and adorable",         "The dog was vicious and frightening"),
    ("The painting was gorgeous and moving",    "The painting was ugly and disturbing"),
    ("The trip was joyful and memorable",       "The trip was wretched and exhausting"),
    ("The present was thoughtful and charming", "The present was insulting and hurtful"),
    ("It ended on a tender, hopeful note",      "It ended on a cruel, hopeless note"),
]
# Axis 2: ^8 Above/Cause (the trigger clause) / ^9 Below/Effect (the landed result).
# Positive class = CAUSE language; negative class = EFFECT language, same content.
CAUSE_EFFECT = [
    ("Because the rain kept falling",           "so the streets were soon flooded"),
    ("Since the alarm never rang",              "and therefore she overslept badly"),
    ("Because the funding was cut",             "so the whole project was cancelled"),
    ("Since the bridge had collapsed",          "and so the traffic was diverted"),
    ("Because the yeast was fresh",             "so the bread rose beautifully"),
    ("Since the drought had lasted months",     "and therefore the crops all failed"),
    ("Because the password was leaked",         "so the account was quickly hijacked"),
    ("Since the engine had overheated",         "and so the car finally stalled"),
    ("Because the referee missed the foul",     "so the goal was allowed to stand"),
    ("Since the vaccine was distributed",       "and therefore the outbreak subsided"),
    ("Because the manuscript was lost",         "so the launch had to be delayed"),
    ("Since the river had frozen solid",        "and so the ferry stopped running"),
]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE / "snapshots" / REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent / "api" / "services" / "cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
print(f"loaded. layers={L}", flush=True)

def resid_all_layers(prompt):
    cap = capture_greedy_trajectory(rt, scenario_id="detval3", prompt=prompt, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)   # (layers, hidden)

def collect(pairs):
    pos = np.stack([resid_all_layers(p) for p, _ in pairs])   # (n, L, H)
    neg = np.stack([resid_all_layers(n) for _, n in pairs])
    return pos, neg

def auc(s, y):
    sp, sn = s[y==1], s[y==0]
    wins = sum(1.0 for a in sp for b in sn if a>b) + 0.5*sum(1.0 for a in sp for b in sn if a==b)
    return float(wins/(len(sp)*len(sn)))

def eval_axis(pos, neg, name):
    # cross-topic split: first 8 topics train, last 4 test
    ptr, pte = pos[:8], pos[8:]
    ntr, nte = neg[:8], neg[8:]
    best = {"layer":None,"det":None,"acc":-1,"auc":0,"rand":0,"shuf":0}
    per_layer = {}
    for li in range(L):
        a_tr, b_tr = ptr[:,li,:], ntr[:,li,:]
        a_te, b_te = pte[:,li,:], nte[:,li,:]
        Xte = np.vstack([a_te,b_te]); yte = np.array([1]*len(a_te)+[0]*len(b_te))
        thr = lambda w: float(0.5*(a_tr@w).mean()+0.5*(b_tr@w).mean())
        # D1 mean-difference
        w1 = a_tr.mean(0)-b_tr.mean(0); w1/=np.linalg.norm(w1)+1e-12
        s1=Xte@w1; acc1=float(((s1>thr(w1)).astype(int)==yte).mean()); auc1=auc(s1,yte)
        # D2 Fisher
        Xtr=np.vstack([a_tr,b_tr]); Sw=np.zeros((Xtr.shape[1],)*2)
        for cls in (a_tr,b_tr):
            c=cls-cls.mean(0); Sw+=c.T@c
        Sw/=max(Xtr.shape[0]-2,1); Sw+= (1e-2*np.trace(Sw)/Sw.shape[0])*np.eye(Sw.shape[0])
        w2=np.linalg.solve(Sw, a_tr.mean(0)-b_tr.mean(0)); w2/=np.linalg.norm(w2)+1e-12
        s2=Xte@w2; acc2=float(((s2>thr(w2)).astype(int)==yte).mean()); auc2=auc(s2,yte)
        # controls
        ys=yte.copy(); np.random.default_rng(20260821).shuffle(ys)
        shuf=float(((s1>thr(w1)).astype(int)==ys).mean())
        wr=np.random.default_rng(1729).standard_normal(Xtr.shape[1]); wr/=np.linalg.norm(wr)+1e-12
        sr=Xte@wr; rand=float(((sr>thr(wr)).astype(int)==yte).mean())
        per_layer[li]={"D1":acc1,"D2":acc2,"rand":rand,"shuf":shuf}
        for det,acc,a in (("D1",acc1,auc1),("D2",acc2,auc2)):
            if acc>best["acc"]:
                best={"layer":li,"det":det,"acc":acc,"auc":a,"rand":rand,"shuf":shuf}
    P1=best["acc"]>=0.70; P2=best["acc"]-best["rand"]>=0.15; P3=best["shuf"]<=0.60; P4=best["auc"]>=0.70
    verdict = "GENERALIZES" if (P1 and P2 and P3 and P4) else ("NULL" if not P1 else "CONFOUNDED")
    return {"axis":name,"best":best,"predictions":{"P1":P1,"P2":P2,"P3":P3,"P4":P4},
            "verdict":verdict,"per_layer":{str(k):v for k,v in per_layer.items()}}

print("capturing valence axis (24 passes)...", flush=True)
vp, vn = collect(VALENCE)
print("capturing cause/effect axis (24 passes)...", flush=True)
cp, cn = collect(CAUSE_EFFECT)

r_val = eval_axis(vp, vn, "^2/^3 valence")
r_ce  = eval_axis(cp, cn, "^8/^9 cause_effect")

out = {"axes":[r_val, r_ce]}
raw = json.dumps(out, indent=2, sort_keys=True).encode()
(SP/"detector_validation_v3_results.json").write_bytes(raw)

print("\n==== MULTI-AXIS DETECTOR VALIDATION (cross-topic, test = 4 held-out topics) ====")
for r in (r_val, r_ce):
    b=r["best"]
    print(f"\n  AXIS {r['axis']}: VERDICT {r['verdict']}")
    print(f"    best: layer {b['layer']} {b['det']} acc={b['acc']:.3f} auc={b['auc']:.3f} "
          f"| random={b['rand']:.3f} shuffle={b['shuf']:.3f}")
    print(f"    predictions P1={r['predictions']['P1']} P2={r['predictions']['P2']} "
          f"P3={r['predictions']['P3']} P4={r['predictions']['P4']}")
print(f"\nsha256={hashlib.sha256(raw).hexdigest()[:16]}")
