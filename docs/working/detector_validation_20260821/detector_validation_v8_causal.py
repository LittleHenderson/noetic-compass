"""Causal sufficiency of the VALIDATED valence probe direction -- is it load-bearing?

v6/v7 asked "can the direction READ valence" (correlational). This asks the different,
stronger question: does INJECTING the validated probe direction into the residual stream
during generation CAUSALLY steer the model's valence output -- more than a norm-matched
random direction? Direction w = mean(explicit-pos) - mean(explicit-neg) at layer 6 (the same
detector direction from v1). Additive intervention through the attested engine, +w and -w on
neutral prompts, vs a permutation null over K random norm-matched directions. Real
pythia-160m, CPU, $0.
"""
import sys, json, hashlib, pathlib
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
from app.runtime.open_weight.engine import (InterventionSpec, RuntimeLoadConfig,
    capture_greedy_trajectory, load_open_weight_runtime)
from app.runtime.open_weight.identity import LocalModelSnapshot

SP = pathlib.Path(__file__).resolve().parent
STORE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"
LSTAR = 6
ALPHA = 6.0          # injection norm
K_NULL = 16          # random directions in the permutation null

EXPL_POS = ["I absolutely love this","This is wonderful and delightful","A fantastic and joyful day",
    "The music was beautiful and uplifting","It tasted delicious and satisfying","A truly excellent result",
    "The gift was charming and heartfelt","A gorgeous and serene view","She felt cheerful and glad","A splendid and pleasant evening"]
EXPL_NEG = ["I absolutely hate this","This is awful and disgusting","A terrible and miserable day",
    "The music was grating and unbearable","It tasted rotten and revolting","A truly dreadful result",
    "The insult was vicious and hurtful","A filthy and menacing view","She felt bitter and sad","A wretched and hostile evening"]
# neutral prompts where the next-token valence is up for grabs
NEUTRAL = ["Overall, the situation was", "My honest assessment is that it was",
           "In the end it turned out to be", "When it was all over, things felt"]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
tok = rt.tokenizer

def cap(prompt, iv=None):
    return capture_greedy_trajectory(rt, scenario_id="causal", prompt=prompt,
        max_new_tokens=1, intervention=iv, seed=0)

def resid(prompt):
    return cap(prompt).arrays["residual_states"][0, LSTAR, :].astype(np.float64)

def tid(w):
    ids = tok.encode(w); return ids[0] if len(ids) == 1 else None
POS = [" good"," great"," wonderful"," amazing"]; NEG = [" bad"," terrible"," awful"," horrible"]
pos_ids = [tid(w) for w in POS if tid(w) is not None]; neg_ids = [tid(w) for w in NEG if tid(w) is not None]
print(f"valence tokens: {len(pos_ids)} pos / {len(neg_ids)} neg", flush=True)

def margin(prompt, iv=None):
    lg = cap(prompt, iv).arrays["pre_selection_logits"][0]
    return float(np.mean([lg[i] for i in pos_ids]) - np.mean([lg[i] for i in neg_ids]))

def spec(vec):
    return InterventionSpec(mode="additive", layer_index=LSTAR, active_steps=(0,),
        vector=tuple(float(x) for x in vec), max_vector_norm=float(np.linalg.norm(vec))+1e-6)

# --- validated probe direction (v1 mean-difference) ---
print("building the validated probe direction...", flush=True)
mu_pos = np.mean([resid(p) for p in EXPL_POS], axis=0)
mu_neg = np.mean([resid(p) for p in EXPL_NEG], axis=0)
w = mu_pos - mu_neg; w = w / np.linalg.norm(w) * ALPHA

def directional_swing(direction):
    # mean over neutral prompts of [ M(+dir) - M(-dir) ]
    sw = []
    for p in NEUTRAL:
        sw.append(margin(p, spec(direction)) - margin(p, spec(-direction)))
    return float(np.mean(sw)), sw

print("measuring probe-direction causal swing...", flush=True)
S_w, sw_w = directional_swing(w)

print(f"running permutation null (K={K_NULL} random norm-matched directions)...", flush=True)
rng = np.random.default_rng(1729)
null = []
for k in range(K_NULL):
    r = rng.standard_normal(w.shape); r = r / np.linalg.norm(r) * ALPHA
    S_r, _ = directional_swing(r)
    null.append(S_r)
null = np.array(null)

# one-sided: is the probe swing more positive (valence-increasing for +w) than random?
p_val = float((np.sum(null >= S_w) + 1) / (K_NULL + 1))
# and two-sided magnitude
p_mag = float((np.sum(np.abs(null) >= abs(S_w)) + 1) / (K_NULL + 1))
directional_ok = all(s > 0 for s in sw_w)   # +w raised valence on every neutral prompt

out = {"layer": LSTAR, "alpha": ALPHA, "n_neutral_prompts": len(NEUTRAL), "k_null": K_NULL,
       "probe_direction_swing_S_w": round(S_w, 4),
       "per_prompt_swings": [round(x, 4) for x in sw_w],
       "null_mean": round(float(null.mean()), 4), "null_std": round(float(null.std()), 4),
       "null_max_abs": round(float(np.abs(null).max()), 4),
       "p_value_one_sided": round(p_val, 4), "p_value_two_sided_magnitude": round(p_mag, 4),
       "directional_all_positive": bool(directional_ok),
       "verdict": ("CAUSALLY_LOAD_BEARING" if (p_mag <= 0.10 and directional_ok)
                   else ("DIRECTIONAL_BUT_NOT_SIGNIFICANT" if directional_ok
                         else "NOT_DISTINGUISHED_FROM_RANDOM"))}
raw = json.dumps(out, indent=2, sort_keys=True).encode()
(SP/"detector_validation_v8_causal_results.json").write_bytes(raw)

print("\n==== CAUSAL SUFFICIENCY OF THE VALENCE PROBE DIRECTION (layer 6) ====")
print(f"  probe-direction swing S_w (mean over {len(NEUTRAL)} neutral prompts) : {S_w:+.4f}")
print(f"  per-prompt swings                                    : {[round(x,3) for x in sw_w]}")
print(f"  +w raised valence on every prompt                    : {directional_ok}")
print(f"  random-direction null: mean={null.mean():+.4f} std={null.std():.4f} max|.|={np.abs(null).max():.4f}")
print(f"  p-value (two-sided magnitude, K={K_NULL})            : {p_mag:.4f}")
print(f"  VERDICT: {out['verdict']}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
