"""Detector validation on real activations through the attested engine.

Goal step 6: one clean capture set, one control set, each detector on its own.
Local CPU, $0, no pod. See PREREG_DETECTOR_VALIDATION.md.
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
LSTAR = 6

# ---- the clean capture set: 20 ^2 Positive (affinity) + 20 ^3 Negative (aversion) ----
POSITIVE = [
    "I absolutely love this",
    "This is wonderful and delightful",
    "What a fantastic and joyful day",
    "She felt drawn to it and adored it",
    "The music was beautiful and uplifting",
    "He was thrilled and deeply pleased",
    "It tasted delicious and satisfying",
    "They welcomed the warm and kind news",
    "The garden looked gorgeous and serene",
    "A truly excellent and admirable result",
    "I am grateful and genuinely happy",
    "The gift was charming and heartfelt",
    "Everyone cheered with pure delight",
    "The sunrise was stunning and glorious",
    "Her smile was radiant and inviting",
    "This success is marvelous and rewarding",
    "The puppy was adorable and sweet",
    "We enjoyed a splendid and cheerful evening",
    "The story ended on a hopeful, tender note",
    "A comforting and pleasant embrace",
]
NEGATIVE = [
    "I absolutely hate this",
    "This is awful and disgusting",
    "What a terrible and miserable day",
    "She felt repelled by it and loathed it",
    "The music was grating and unbearable",
    "He was furious and deeply upset",
    "It tasted rotten and revolting",
    "They dreaded the cruel and harsh news",
    "The alley looked filthy and menacing",
    "A truly dreadful and shameful result",
    "I am resentful and genuinely angry",
    "The insult was vicious and hurtful",
    "Everyone recoiled with pure disgust",
    "The wreckage was grim and horrifying",
    "Her scowl was cold and threatening",
    "This failure is appalling and punishing",
    "The wound was gruesome and painful",
    "We endured a wretched and bitter evening",
    "The story ended on a hopeless, cruel note",
    "A suffocating and hostile confrontation",
]
assert len(POSITIVE) == 20 and len(NEGATIVE) == 20

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE / "snapshots" / REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent / "api" / "services" / "cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
print(f"loaded. layers={rt.layer_count} hidden={rt.hidden_size} "
      f"weight_manifest={rt.weight_value_manifest_sha256[:16]}", flush=True)

def residual(prompt):
    cap = capture_greedy_trajectory(rt, scenario_id="detval", prompt=prompt,
        max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0, LSTAR, :].astype(np.float64)

print("capturing 40 real residuals at layer 6...", flush=True)
Xpos = np.stack([residual(p) for p in POSITIVE])   # (20, hidden)
Xneg = np.stack([residual(p) for p in NEGATIVE])
print(f"captured pos={Xpos.shape} neg={Xneg.shape}", flush=True)

# fixed split: first 10 train, last 10 test, per class
ptr, pte = Xpos[:10], Xpos[10:]
ntr, nte = Xneg[:10], Xneg[10:]
Xte = np.vstack([pte, nte]); yte = np.array([1]*10 + [0]*10)   # 1 = ^2 Positive

def evaluate(w, thr, X, y):
    s = X @ w
    pred = (s > thr).astype(int)
    acc = float((pred == y).mean())
    # exact AUC (Mann-Whitney)
    sp, sn = s[y == 1], s[y == 0]
    wins = sum(1.0 for a in sp for b in sn if a > b) + 0.5 * sum(1.0 for a in sp for b in sn if a == b)
    auc = float(wins / (len(sp) * len(sn)))
    pooled_sd = float(np.sqrt(0.5 * (sp.var() + sn.var())) + 1e-12)
    margin = float((sp.mean() - sn.mean()) / pooled_sd)
    return {"accuracy": acc, "auc": auc, "margin": margin}, s

def midpoint_threshold(w, Ptr, Ntr):
    return float(0.5 * (Ptr @ w).mean() + 0.5 * (Ntr @ w).mean())

results = {}

# ---- D1: mean-difference (CAS drive-direction) detector ----
w1 = ptr.mean(0) - ntr.mean(0)
w1 = w1 / (np.linalg.norm(w1) + 1e-12)
thr1 = midpoint_threshold(w1, ptr, ntr)
results["D1_mean_difference"], _ = evaluate(w1, thr1, Xte, yte)

# ---- D2: Fisher LDA detector ----
Xtr = np.vstack([ptr, ntr])
mu = Xtr.mean(0)
Sw = np.zeros((Xtr.shape[1],) * 2)
for cls in (ptr, ntr):
    c = cls - cls.mean(0)
    Sw += c.T @ c
Sw /= (Xtr.shape[0] - 2)
ridge = 1e-2 * np.trace(Sw) / Sw.shape[0]
Sw_r = Sw + ridge * np.eye(Sw.shape[0])
w2 = np.linalg.solve(Sw_r, ptr.mean(0) - ntr.mean(0))
w2 = w2 / (np.linalg.norm(w2) + 1e-12)
thr2 = midpoint_threshold(w2, ptr, ntr)
results["D2_fisher_lda"], _ = evaluate(w2, thr2, Xte, yte)

# ---- C1: label-shuffle control (fixed seed) ----
rng = np.random.default_rng(20260821)
yte_shuf = yte.copy(); rng.shuffle(yte_shuf)
c1 = {}
for name, w, thr in (("D1_mean_difference", w1, thr1), ("D2_fisher_lda", w2, thr2)):
    m, _ = evaluate(w, thr, Xte, yte_shuf)
    c1[name] = m["accuracy"]

# ---- C2: random-direction control (fixed seed, same-norm unit vector) ----
rng2 = np.random.default_rng(1729)
wr = rng2.standard_normal(Xtr.shape[1]); wr = wr / (np.linalg.norm(wr) + 1e-12)
thrr = midpoint_threshold(wr, ptr, ntr)
c2, _ = evaluate(wr, thrr, Xte, yte)

# ---- decision rule ----
best = max(results, key=lambda k: results[k]["accuracy"])
b = results[best]
P1 = b["accuracy"] >= 0.70
P2 = b["accuracy"] - c2["accuracy"] >= 0.15
P3 = c1[best] <= 0.60
P4 = b["auc"] >= 0.70
if not P1:
    verdict = "NULL"
elif P1 and P2 and P3 and P4:
    verdict = "DETECTOR_VALIDATED_ON_REAL_ACTIVATIONS"
else:
    verdict = "CONFOUNDED"

out = {
    "model_id": "EleutherAI/pythia-160m",
    "revision": "50f5173d932e8e61f858120bcb800b97af589f46",
    "reserialized_snapshot_sha256": REV,
    "weight_value_manifest_sha256": rt.weight_value_manifest_sha256,
    "layer": LSTAR, "hidden": int(rt.hidden_size),
    "n_train_per_class": 10, "n_test_per_class": 10,
    "detectors": results,
    "controls": {"C1_label_shuffle_accuracy": c1, "C2_random_direction": c2},
    "best_detector": best,
    "predictions": {"P1_acc_ge_0.70": bool(P1), "P2_beats_random_by_0.15": bool(P2),
                    "P3_shuffle_collapses_le_0.60": bool(P3), "P4_auc_ge_0.70": bool(P4)},
    "verdict": verdict,
}
res_path = SP / "detector_validation_results.json"
raw = json.dumps(out, indent=2, sort_keys=True).encode()
res_path.write_bytes(raw)

print("\n==== RESULTS ====")
for name, m in results.items():
    print(f"  {name:20} acc={m['accuracy']:.3f} auc={m['auc']:.3f} margin={m['margin']:+.3f}")
print(f"  C1 label-shuffle acc : {c1}")
print(f"  C2 random-direction  : acc={c2['accuracy']:.3f} auc={c2['auc']:.3f}")
print(f"  best detector        : {best}")
print(f"  P1 acc>=.70={P1}  P2 beats-rand>=.15={P2}  P3 shuffle<=.60={P3}  P4 auc>=.70={P4}")
print(f"  VERDICT: {verdict}")
print(f"  results -> {res_path}  sha256={hashlib.sha256(raw).hexdigest()[:16]}")
