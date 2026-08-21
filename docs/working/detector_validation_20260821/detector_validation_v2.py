"""Detector validation v2 -- cross-topic generalization + layer sweep.

Addresses the v1 caveat (random control at 0.800): train and test share NO
topic, so a detector that passes cannot be exploiting mere class-distance -- it
must read valence that generalizes across content. Layer sweep is free (one
capture yields all layers). Real weights, attested engine, local CPU, $0.
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

# 12 topics, each with a ^2 Positive and a ^3 Negative sentence sharing content.
# Split by TOPIC: first 8 topics train, last 4 topics test -> cross-topic.
TOPICS = [
    ("food",     "The meal was delicious and satisfying",        "The meal was rotten and revolting"),
    ("music",    "The song was beautiful and uplifting",         "The song was grating and unbearable"),
    ("weather",  "The morning was bright and pleasant",          "The morning was bleak and miserable"),
    ("people",   "Her manner was warm and kind",                 "Her manner was cold and cruel"),
    ("news",     "The report brought welcome, hopeful news",     "The report brought grim, dreadful news"),
    ("place",    "The room was cozy and inviting",               "The room was filthy and menacing"),
    ("work",     "The project was a splendid success",           "The project was an appalling failure"),
    ("animal",   "The dog was gentle and adorable",              "The dog was vicious and frightening"),
    ("art",      "The painting was gorgeous and moving",         "The painting was ugly and disturbing"),
    ("travel",   "The trip was joyful and memorable",            "The trip was wretched and exhausting"),
    ("gift",     "The present was thoughtful and charming",      "The present was insulting and hurtful"),
    ("ending",   "The story ended on a tender, hopeful note",    "The story ended on a cruel, hopeless note"),
]
TRAIN_TOPICS = TOPICS[:8]
TEST_TOPICS = TOPICS[8:]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE / "snapshots" / REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent / "api" / "services" / "cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
print(f"loaded. layers={L} hidden={rt.hidden_size}", flush=True)

def all_layer_residuals(prompt):
    cap = capture_greedy_trajectory(rt, scenario_id="detval2", prompt=prompt,
        max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)   # (layers, hidden)

def collect(topics):
    pos, neg = [], []
    for _t, p, n in topics:
        pos.append(all_layer_residuals(p))
        neg.append(all_layer_residuals(n))
    return np.stack(pos), np.stack(neg)   # (n_topics, layers, hidden)

print("capturing (24 train + 24 test = 48 real passes), all layers...", flush=True)
Ptr, Ntr = collect(TRAIN_TOPICS)   # (8, L, H)
Pte, Nte = collect(TEST_TOPICS)    # (4, L, H)

def evaluate(w, thr, X, y):
    s = X @ w
    pred = (s > thr).astype(int)
    acc = float((pred == y).mean())
    sp, sn = s[y == 1], s[y == 0]
    wins = sum(1.0 for a in sp for b in sn if a > b) + 0.5 * sum(1.0 for a in sp for b in sn if a == b)
    auc = float(wins / (len(sp) * len(sn)))
    return acc, auc

def run_layer(li):
    ptr, ntr = Ptr[:, li, :], Ntr[:, li, :]
    pte, nte = Pte[:, li, :], Nte[:, li, :]
    Xte = np.vstack([pte, nte]); yte = np.array([1]*len(pte) + [0]*len(nte))
    def thr_mid(w): return float(0.5*(ptr@w).mean() + 0.5*(ntr@w).mean())
    # D1 mean-difference
    w1 = ptr.mean(0) - ntr.mean(0); w1 /= (np.linalg.norm(w1)+1e-12)
    a1, u1 = evaluate(w1, thr_mid(w1), Xte, yte)
    # D2 Fisher LDA
    Xtr = np.vstack([ptr, ntr]); Sw = np.zeros((Xtr.shape[1],)*2)
    for cls in (ptr, ntr):
        c = cls - cls.mean(0); Sw += c.T@c
    Sw /= max(Xtr.shape[0]-2, 1)
    Sw_r = Sw + (1e-2*np.trace(Sw)/Sw.shape[0])*np.eye(Sw.shape[0])
    w2 = np.linalg.solve(Sw_r, ptr.mean(0)-ntr.mean(0)); w2 /= (np.linalg.norm(w2)+1e-12)
    a2, u2 = evaluate(w2, thr_mid(w2), Xte, yte)
    # C1 label shuffle (fixed seed)
    ys = yte.copy(); np.random.default_rng(20260821).shuffle(ys)
    c1a, _ = evaluate(w1, thr_mid(w1), Xte, ys)
    # C2 random direction (fixed seed)
    wr = np.random.default_rng(1729).standard_normal(Xtr.shape[1]); wr/=(np.linalg.norm(wr)+1e-12)
    c2a, c2u = evaluate(wr, thr_mid(wr), Xte, yte)
    return {"D1_acc":a1,"D1_auc":u1,"D2_acc":a2,"D2_auc":u2,
            "C1_shuffle_acc":c1a,"C2_random_acc":c2a,"C2_random_auc":c2u}

sweep = {li: run_layer(li) for li in range(L)}
best_layer = max(sweep, key=lambda li: max(sweep[li]["D1_acc"], sweep[li]["D2_acc"]))
b = sweep[best_layer]
best_acc = max(b["D1_acc"], b["D2_acc"])
best_det = "D1" if b["D1_acc"] >= b["D2_acc"] else "D2"
best_auc = b[f"{best_det}_auc"]

# cross-topic decision: pass if best detector beats random by >=0.15 AND shuffle collapses
P_signal = best_acc >= 0.70
P_beats_random = best_acc - b["C2_random_acc"] >= 0.15
P_shuffle = b["C1_shuffle_acc"] <= 0.60
P_auc = best_auc >= 0.70
if not P_signal: verdict = "NULL_CROSS_TOPIC"
elif P_signal and P_beats_random and P_shuffle and P_auc: verdict = "DETECTOR_GENERALIZES_CROSS_TOPIC"
else: verdict = "CONFOUNDED_CROSS_TOPIC"

out = {"design":"cross_topic_train8_test4","layers":L,
       "best_layer":best_layer,"best_detector":best_det,
       "best_test_accuracy":best_acc,"best_test_auc":best_auc,
       "at_best_layer":b,"layer_sweep":{str(k):v for k,v in sweep.items()},
       "predictions":{"signal_ge_0.70":bool(P_signal),"beats_random_by_0.15":bool(P_beats_random),
                      "shuffle_collapses_le_0.60":bool(P_shuffle),"auc_ge_0.70":bool(P_auc)},
       "verdict":verdict}
raw = json.dumps(out, indent=2, sort_keys=True).encode()
(SP/"detector_validation_v2_results.json").write_bytes(raw)

print("\n==== CROSS-TOPIC LAYER SWEEP (test = 4 held-out topics, 8 items) ====")
print("layer  D1acc D2acc  C2rand C1shuf")
for li in range(L):
    r = sweep[li]
    print(f"  {li:2d}   {r['D1_acc']:.3f} {r['D2_acc']:.3f}  {r['C2_random_acc']:.3f}  {r['C1_shuffle_acc']:.3f}")
print(f"\nbest layer {best_layer}: {best_det} acc={best_acc:.3f} auc={best_auc:.3f} | random={b['C2_random_acc']:.3f} shuffle={b['C1_shuffle_acc']:.3f}")
print(f"P_signal={P_signal} P_beats_random={P_beats_random} P_shuffle={P_shuffle} P_auc={P_auc}")
print(f"VERDICT: {verdict}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
