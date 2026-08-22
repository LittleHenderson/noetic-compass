"""Operator-10 probe on real activations -- the d=10 middle rung of the 40/10/4 ladder.

The generative roadmap's keystone build. A 10-way classifier over the canonical CAS
Noetic operators ^0..^9 on real pythia-160m activations. 6 exemplars per operator = 60
real forward passes, grounded in the canonical colloquialism map (CLAUDE.md). Stratified
4-train / 2-test per operator, nearest-centroid, chance=0.10. Reported PER-OPERATOR with a
confusion matrix + label-shuffle null -- self-duals (^0/^1/^4/^7) may under-separate, and a
per-operator NULL is a load-bearing result, not a blanket failure. Real weights, CPU, $0.
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

# 6 exemplars per Noetic, anchored to the canonical colloquialism / definition (CLAUDE.md).
OPS = {
 "^0_Idea": [  # the bare concept/thing held in mind ("it's all in your head")
    "The concept of justice is an idea in the mind",
    "Infinity is a notion that exists only in thought",
    "The number seven is an abstract idea",
    "Freedom is a concept we hold in our heads",
    "A perfect circle is an idea, never a real thing",
    "The word 'tomorrow' names an idea, not an object"],
 "^1_Mind": [  # awareness/attention that processes ("paying attention", "using your head")
    "She paid close attention to every word he said",
    "He focused his full awareness on the problem",
    "I made up my mind after thinking it over",
    "Use your head and concentrate on the task",
    "Her mind was alert and fully engaged",
    "He noticed and became conscious of the sound"],
 "^2_Positive": [  # affinity/attraction ("drawn to it", "can't resist")
    "She was drawn to the painting like a moth to a flame",
    "He simply could not resist the warm invitation",
    "The idea speaks to me and I love it",
    "I feel a strong pull toward that plan",
    "They were attracted to the cheerful music",
    "It appeals to me deeply and I want it"],
 "^3_Negative": [  # aversion/repulsion ("can't stomach it", "rubs me the wrong way")
    "He could not stomach the cruel remark",
    "That attitude rubs me the wrong way",
    "I would not touch that scheme with a ten-foot pole",
    "She was repelled by the rotten smell",
    "The plan is repugnant and I recoil from it",
    "They were disgusted and pulled away"],
 "^4_Vibration": [  # resonance/impression ("struck a chord", "made an impression")
    "The speech struck a chord deep within her",
    "That story hit me hard and stayed with me",
    "His words resonated and left an impression",
    "The melody vibrated through the whole room",
    "It made a lasting impression on the audience",
    "The idea reverberated in his thoughts for days"],
 "^5_Female": [  # the Mind as accumulated experience ("we are the sum of our experiences")
    "We are each the sum of our experiences",
    "Everything I have lived through made me who I am",
    "Her character was shaped by years of hardship",
    "His expertise is built from a lifetime of practice",
    "The person you are is your accumulated past",
    "My beliefs formed slowly from all I have seen"],
 "^6_Male": [  # an Idea composed of other Ideas; decomposition ("unpacking", "breaking it down")
    "Let us break the argument down into its parts",
    "She unpacked the idea to see what was inside",
    "He took the theory apart piece by piece",
    "The proof decomposes into three separate lemmas",
    "We analyzed the plan by dividing it into steps",
    "Pull the concept apart and examine each component"],
 "^7_Rhythm": [  # rate/pattern of exposure, conditioning ("practice makes perfect", "muscle memory")
    "Practice makes perfect if you repeat it daily",
    "You are what you repeatedly do every day",
    "Through constant drilling it became muscle memory",
    "She got into a steady groove of writing each morning",
    "Repetition slowly conditioned the habit",
    "Doing it over and over trained the reflex"],
 "^8_AboveCause": [  # associative trigger ("that reminds me", "one thing leads to another")
    "That reminds me of a trip we took long ago",
    "The smell of rain triggered a childhood memory",
    "One thing led to another and I recalled her name",
    "Seeing the photo made me think of my father",
    "The song brought an old summer to mind",
    "His comment sparked a completely different thought"],
 "^9_BelowEffect": [  # the triggered idea landing ("it just popped into my head", "it clicked")
    "The answer just popped into my head",
    "Out of nowhere the solution came to me",
    "Suddenly it clicked and I understood",
    "The thought arrived unbidden in my mind",
    "The name finally surfaced on its own",
    "All at once the memory came to me"],
}
OP_NAMES = list(OPS.keys())

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
    cap = capture_greedy_trajectory(rt, scenario_id="op10", prompt=prompt, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)  # (layers, hidden)

print("capturing 60 real residuals (10 operators x 6), all layers...", flush=True)
# E[op] = list of 6 (layers,hidden)
E = {op: [resid_all(s) for s in OPS[op]] for op in OP_NAMES}

def eval_layer(li, shuffle=False):
    # stratified split: first 4 train, last 2 test per operator
    cent = {op: np.mean([E[op][i][li] for i in range(4)], axis=0) for op in OP_NAMES}
    test = [(op, i) for op in OP_NAMES for i in (4, 5)]
    labels = [op for op, _ in test]
    if shuffle:
        rng = np.random.default_rng(20260821); labels = list(labels); rng.shuffle(labels)
    correct = 0; per_op = {op: [0, 0] for op in OP_NAMES}; conf = {}
    for (op, i), lab in zip(test, labels):
        v = E[op][i][li]
        pred = min(OP_NAMES, key=lambda o: np.linalg.norm(v - cent[o]))
        per_op[lab][1] += 1
        if pred == lab: correct += 1; per_op[lab][0] += 1
        conf[(lab, pred)] = conf.get((lab, pred), 0) + 1
    acc = correct / len(test)
    return acc, per_op, conf

per_layer = {}
best = {"layer": None, "acc": -1}
for li in range(L):
    acc, per_op, conf = eval_layer(li)
    shuf, _, _ = eval_layer(li, shuffle=True)
    per_layer[li] = {"acc": acc, "shuffle": shuf}
    if acc > best["acc"]:
        best = {"layer": li, "acc": acc, "shuffle": shuf, "per_op": per_op, "conf": conf}

# per-operator accuracy at best layer
per_op_acc = {op: (best["per_op"][op][0] / best["per_op"][op][1] if best["per_op"][op][1] else 0.0)
              for op in OP_NAMES}
separated = [op for op, a in per_op_acc.items() if a >= 0.5]
chance = 0.10
P1 = best["acc"] >= 0.30           # macro accuracy well above 10-way chance
P3 = best["shuffle"] <= 0.20       # shuffle collapses toward chance
verdict = ("OPERATOR10_PARTIAL_DECODABLE" if (P1 and P3 and len(separated) >= 5)
           else ("NULL_OPERATOR10" if best["acc"] < 0.20 else "OPERATOR10_WEAK_PARTIAL"))

out = {"design": "operator10_nearest_centroid_stratified_4train_2test",
       "operators": OP_NAMES, "chance_level": chance, "n_test": len(OP_NAMES)*2,
       "best_layer": best["layer"], "best_accuracy": best["acc"],
       "best_shuffle": best["shuffle"],
       "per_operator_accuracy_at_best_layer": per_op_acc,
       "operators_separated_ge_0.5": separated,
       "confusion_at_best_layer": {f"{k[0]}->{k[1]}": v for k, v in best["conf"].items()},
       "layer_sweep": {str(k): v for k, v in per_layer.items()},
       "verdict": verdict}
raw = json.dumps(out, indent=2, sort_keys=True).encode()
(SP/"detector_validation_v5_operator10_results.json").write_bytes(raw)

print("\n==== OPERATOR-10 PROBE (10-way, chance=0.10, 20 held-out items) ====")
print("layer  macro-acc  shuffle")
for li in range(L):
    r = per_layer[li]; print(f"  {li:2d}   {r['acc']:.3f}      {r['shuffle']:.3f}")
print(f"\nbest layer {best['layer']}: macro-acc={best['acc']:.3f} shuffle={best['shuffle']:.3f}")
print("per-operator accuracy at best layer:")
for op in OP_NAMES:
    mark = "  <-- separated" if per_op_acc[op] >= 0.5 else ""
    print(f"   {op:15} {per_op_acc[op]:.2f}{mark}")
print(f"\noperators separated (>=0.5): {len(separated)}/10 -> {separated}")
print(f"VERDICT: {verdict}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
