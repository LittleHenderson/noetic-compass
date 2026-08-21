import sys, json, hashlib, pathlib
import numpy as np
REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
from app.runtime.open_weight.engine import (InterventionSpec, RuntimeLoadConfig,
    capture_greedy_trajectory, load_open_weight_runtime)
from app.runtime.open_weight.identity import LocalModelSnapshot

SP = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS\48bed170-da71-4777-8d00-6c209e1475ff\scratchpad")
STORAGE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"
SNAP = STORAGE / "snapshots" / REV
LSTAR = 6

print("loading runtime (full attestation)...", flush=True)
runtime = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=SNAP, model_storage_root=STORAGE),
    adapter_source_path=WORKER.parent / "api" / "services" / "cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
print("loaded. layers:", runtime.layer_count, "hidden:", runtime.hidden_size,
      "| weight manifest:", runtime.weight_value_manifest_sha256[:16], flush=True)

def cap(pid, prompt, iv=None):
    c = capture_greedy_trajectory(runtime, scenario_id=pid, prompt=prompt,
        max_new_tokens=2, intervention=iv, seed=0)
    return c

tok = runtime.tokenizer
def tid(word):
    ids = tok.encode(word)
    return ids[0] if len(ids) == 1 else None
POS = [w for w in (" good"," great"," wonderful"," amazing")]
NEG = [w for w in (" bad"," terrible"," awful"," horrible")]
pos_ids = {w: tid(w) for w in POS}; neg_ids = {w: tid(w) for w in NEG}
dropped = [w for w,d in {**pos_ids,**neg_ids}.items() if d is None]
pos_ids = {w:i for w,i in pos_ids.items() if i is not None}
neg_ids = {w:i for w,i in neg_ids.items() if i is not None}
print("valence tokens ok:", len(pos_ids), "pos /", len(neg_ids), "neg | dropped:", dropped, flush=True)

# --- build v from the contrast pair ---
cp = cap("contrast-pos", "I think this movie is absolutely wonderful")
cn = cap("contrast-neg", "I think this movie is absolutely terrible")
v = (cp.arrays["residual_states"][0, LSTAR, :] - cn.arrays["residual_states"][0, LSTAR, :]).astype(np.float64)
vnorm = float(np.linalg.norm(v))
rng = np.random.default_rng(1729)
r = rng.standard_normal(v.shape); r = r / np.linalg.norm(r) * vnorm
print(f"steering vector built: ||v|| = {vnorm:.6f}  cos(v,r) = {float(v@r/(vnorm*vnorm)):.6f}", flush=True)

def additive(vec):
    return InterventionSpec(mode="additive", layer_index=LSTAR, active_steps=(0,),
        vector=tuple(float(x) for x in vec), max_vector_norm=vnorm + 1e-6)

TESTS = {"T1":"Overall, the film was", "T2":"My honest review: the food tasted",
         "T3":"She looked at the painting and said it was"}
def margin(logits):
    return float(np.mean([logits[i] for i in pos_ids.values()]) - np.mean([logits[i] for i in neg_ids.values()]))

results = {"vector_norm": vnorm, "prompts": {}}
for name, prompt in TESTS.items():
    base = cap(f"{name}-base", prompt)
    bl = base.arrays["pre_selection_logits"][0].astype(np.float64)
    row = {"baseline_top": tok.decode([int(base.arrays["generated_token_ids"][0])]),
           "baseline_margin": margin(bl), "arms": {}}
    for arm, vec in (("+v", v), ("-v", -v), ("+r", r)):
        c = cap(f"{name}{arm}", prompt, additive(vec))
        L = c.arrays["pre_selection_logits"][0].astype(np.float64)
        row["arms"][arm] = {
            "dM": margin(L) - row["baseline_margin"],
            "l2": float(np.linalg.norm(L - bl)),
            "top": tok.decode([int(c.arrays["generated_token_ids"][0])]),
            "top_changed": bool(int(c.arrays["generated_token_ids"][0]) != int(base.arrays["generated_token_ids"][0])),
            "gen": c.generated_text}
    results["prompts"][name] = row
    print(f"{name} '{prompt}' base_top={row['baseline_top']!r} M={row['baseline_margin']:.4f}", flush=True)
    for a, d in row["arms"].items():
        print(f"   {a}: dM={d['dM']:+.4f} l2={d['l2']:.3f} top={d['top']!r} changed={d['top_changed']}", flush=True)

# engine controls on T1
base1 = cap("T1-base2", TESTS["T1"])
b1 = base1.arrays["pre_selection_logits"][0].astype(np.float64)
noop = cap("T1-noop", TESTS["T1"], InterventionSpec(mode="noop", layer_index=LSTAR, active_steps=(0,)))
zero = cap("T1-zero", TESTS["T1"], InterventionSpec(mode="zero", layer_index=LSTAR, active_steps=(0,)))
nL = noop.arrays["pre_selection_logits"][0].astype(np.float64)
zL = zero.arrays["pre_selection_logits"][0].astype(np.float64)
results["controls"] = {
    "noop_max_abs_delta": float(np.max(np.abs(nL - b1))),
    "zero_l2": float(np.linalg.norm(zL - b1)),
    "zero_top": tok.decode([int(zero.arrays["generated_token_ids"][0])])}
print("CONTROLS: noop max|d| =", results["controls"]["noop_max_abs_delta"],
      "| zero l2 =", f"{results['controls']['zero_l2']:.3f}",
      "| zero top =", repr(results["controls"]["zero_top"]), flush=True)

out = SP / "cav_results.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("results ->", out, "sha256", hashlib.sha256(out.read_bytes()).hexdigest()[:16], flush=True)
