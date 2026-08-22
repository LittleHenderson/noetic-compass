"""Domain-4 probe on real activations -- the d=4 coarse rung of the granularity ladder.

The deep-dive's #1 action: build a Domain-level (P/C/E/O) probe on real weights, the
prerequisite that starts the 40/10/4 ladder T4 needs. 8 content topics x 4 CAS Domains,
parallel framings of the same subject; train on 6 topics, test on 2 UNSEEN topics
(cross-topic, so a pass reflects the Domain axis, not topic). Nearest-centroid 4-way
classifier + two null controls. Real pythia-160m through the attested engine, CPU, $0.

CAS Domains (canonical, CLAUDE.md): P Principled (values/ought), C Cognitive (fact/reason),
E Evaluative (judgment/quality), O Operational (procedure/how-to).
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
DOMAINS = ["P", "C", "E", "O"]

# 8 topics x 4 Domains. Each row: same subject, one framing per Domain.
# P = principled/ought, C = cognitive/fact, E = evaluative/judgment, O = operational/procedure.
TOPICS = {
 "cooking":  {"P":"A cook must never knowingly serve food that is unsafe to eat",
              "C":"Water boils at one hundred degrees Celsius at sea level",
              "E":"This risotto is the most delicious dish on the whole menu",
              "O":"First dice the onion, then fry it slowly until it turns golden"},
 "medicine": {"P":"A doctor is obligated to protect the confidentiality of every patient",
              "C":"The human heart has four chambers that pump blood through the body",
              "E":"This new treatment is far superior to the older, harsher one",
              "O":"First clean the wound, then apply the dressing and secure it"},
 "finance":  {"P":"An advisor ought to disclose every conflict of interest honestly",
              "C":"Compound interest grows a balance faster than simple interest does",
              "E":"This fund is a poor choice with mediocre returns and high fees",
              "O":"First open the account, then transfer the funds and confirm the balance"},
 "law":      {"P":"A witness has a duty to tell the whole truth under oath",
              "C":"A contract requires an offer, acceptance, and consideration to be valid",
              "E":"This ruling is a brilliant and well reasoned piece of jurisprudence",
              "O":"First file the motion, then serve the notice on the opposing party"},
 "sports":   {"P":"Athletes should compete fairly and never use banned substances",
              "C":"A marathon covers a distance of just over forty two kilometres",
              "E":"That was the greatest comeback victory the sport has ever seen",
              "O":"First stretch your muscles, then jog a slow lap to warm up"},
 "music":    {"P":"A performer should credit every artist whose work they sample",
              "C":"An octave spans twelve equal semitones in standard tuning",
              "E":"This symphony is a sublime and deeply moving masterpiece",
              "O":"First tune the strings, then set the tempo and begin the piece"},
 "gardening":{"P":"A gardener ought to avoid pesticides that harm pollinating bees",
              "C":"Photosynthesis converts sunlight and water into sugars for the plant",
              "E":"This rose garden is the most breathtaking display in the city",
              "O":"First loosen the soil, then plant the seed and water it gently"},
 "travel":   {"P":"A traveller should respect the customs and laws of every host country",
              "C":"The Earth is divided into twenty four standard time zones",
              "E":"This coastal town is the loveliest place I have ever visited",
              "O":"First pack your bag, then check in online and print the boarding pass"},
}
TOPIC_NAMES = list(TOPICS.keys())
TRAIN_TOPICS = TOPIC_NAMES[:6]
TEST_TOPICS = TOPIC_NAMES[6:]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L = int(rt.layer_count)
print(f"loaded. layers={L}", flush=True)

def resid_all(prompt):
    cap = capture_greedy_trajectory(rt, scenario_id="dom4", prompt=prompt, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)  # (layers, hidden)

print("capturing 32 real residuals (8 topics x 4 domains), all layers...", flush=True)
# X[topic][domain] = (layers, hidden)
X = {t: {d: resid_all(TOPICS[t][d]) for d in DOMAINS} for t in TOPIC_NAMES}

def nearest_centroid_eval(train_topics, test_topics, li, subspace=None, shuffle=False):
    # centroids per domain from train topics at layer li
    def vec(t, d):
        v = X[t][d][li]
        return v @ subspace if subspace is not None else v
    cent = {d: np.mean([vec(t, d) for t in train_topics], axis=0) for d in DOMAINS}
    y_true, y_pred = [], []
    rng = np.random.default_rng(20260821)
    test_items = [(t, d) for t in test_topics for d in DOMAINS]
    labels = [d for _, d in test_items]
    if shuffle:
        labels = list(labels); rng.shuffle(labels)
    for (t, d_orig), lab in zip(test_items, labels):
        v = vec(t, d_orig)
        pred = min(DOMAINS, key=lambda d: np.linalg.norm(v - cent[d]))
        y_true.append(lab); y_pred.append(pred)
    acc = float(np.mean([a == b for a, b in zip(y_true, y_pred)]))
    return acc

per_layer = {}
best = {"layer": None, "acc": -1}
for li in range(L):
    real = nearest_centroid_eval(TRAIN_TOPICS, TEST_TOPICS, li)
    shuf = nearest_centroid_eval(TRAIN_TOPICS, TEST_TOPICS, li, shuffle=True)
    # random-subspace control: project to a random 4-dim subspace (same dim as #domains)
    rng = np.random.default_rng(1729 + li)
    Q, _ = np.linalg.qr(rng.standard_normal((768, 4)))
    randsub = nearest_centroid_eval(TRAIN_TOPICS, TEST_TOPICS, li, subspace=Q)
    per_layer[li] = {"real": real, "shuffle": shuf, "random_subspace": randsub}
    if real > best["acc"]:
        best = {"layer": li, "acc": real, "shuffle": shuf, "random_subspace": randsub}

# chance for a 4-way balanced classifier is 0.25
P1 = best["acc"] >= 0.50               # well above 4-way chance (0.25)
P2 = best["acc"] - best["random_subspace"] >= 0.15
P3 = best["shuffle"] <= 0.45           # shuffle collapses toward chance
verdict = "DOMAIN4_DECODABLE_CROSS_TOPIC" if (P1 and P2 and P3) else ("NULL_DOMAIN4" if not P1 else "CONFOUNDED_DOMAIN4")

out = {"design": "domain4_nearest_centroid_cross_topic_train6_test2",
       "domains": DOMAINS, "chance_level": 0.25, "n_test_items": len(TEST_TOPICS)*4,
       "best_layer": best["layer"], "best_accuracy": best["acc"],
       "at_best_layer": best, "layer_sweep": {str(k): v for k, v in per_layer.items()},
       "predictions": {"P1_acc_ge_0.50": bool(P1), "P2_beats_random_subspace_0.15": bool(P2),
                       "P3_shuffle_le_0.45": bool(P3)}, "verdict": verdict}
raw = json.dumps(out, indent=2, sort_keys=True).encode()
(SP/"detector_validation_v4_domain_results.json").write_bytes(raw)

print("\n==== DOMAIN-4 PROBE (cross-topic, test = 2 held-out topics, 8 items, 4-way, chance=0.25) ====")
print("layer  real  shuffle  rand-subspace")
for li in range(L):
    r = per_layer[li]
    print(f"  {li:2d}   {r['real']:.3f}  {r['shuffle']:.3f}   {r['random_subspace']:.3f}")
print(f"\nbest layer {best['layer']}: real={best['acc']:.3f} | shuffle={best['shuffle']:.3f} random_subspace={best['random_subspace']:.3f}")
print(f"P1(>=.50)={P1} P2(beats rand>=.15)={P2} P3(shuffle<=.45)={P3}")
print(f"VERDICT: {verdict}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
