"""Framing/surface hardening -- do the validated detectors beat a char-ngram baseline?

The mandatory char-level surface control (a prior W0 detector was WITHDRAWN for failing this).
For two validated axes, train the activation detector on EXPLICIT stimuli, then test on an
IMPLICIT set where the construct is conveyed WITHOUT the training vocabulary:
  * valence ^2/^3: implicit = scenario valence (no good/bad adjectives)
  * cause/effect ^8/^9: implicit = connective-stripped bare clauses (no because/so/therefore)
The activation nearest-centroid is compared, on the SAME implicit test set, against a
char-ngram (n=2,3,4) nearest-centroid surface baseline. HARDENED only if activations beat the
surface baseline. Real pythia-160m through the attested engine, CPU, $0.
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

# ---- VALENCE ^2/^3 ----
VAL_TRAIN_POS = ["I absolutely love this","This is wonderful and delightful","A fantastic and joyful day",
    "The music was beautiful and uplifting","It tasted delicious and satisfying","A truly excellent result",
    "The gift was charming and heartfelt","A gorgeous and serene view","She felt cheerful and glad","A splendid and pleasant evening"]
VAL_TRAIN_NEG = ["I absolutely hate this","This is awful and disgusting","A terrible and miserable day",
    "The music was grating and unbearable","It tasted rotten and revolting","A truly dreadful result",
    "The insult was vicious and hurtful","A filthy and menacing view","She felt bitter and sad","A wretched and hostile evening"]
# implicit: valence via situation, NO explicit valence adjectives
VAL_TEST_POS = ["She opened the letter and saw she had been accepted",
    "After years of trying, they finally held their newborn",
    "He crossed the finish line as the crowd rose to their feet",
    "The scholarship would cover every remaining cost",
    "The test came back clear and the doctor smiled",
    "They were reunited at the gate after the long deployment",
    "Her name was the first one called for the prize",
    "The offer arrived with more than she had asked for"]
VAL_TEST_NEG = ["She opened the letter and saw she had been rejected",
    "After years of trying, the treatment had failed once more",
    "He collapsed before the finish line as the crowd fell silent",
    "The bill would take everything they had left",
    "The test came back and the doctor looked away",
    "They stood at the gate but no one came off the plane",
    "Her name was the only one missing from the list",
    "The letter arrived with a notice of termination"]

# ---- CAUSE/EFFECT ^8/^9 ----
CE_TRAIN_CAUSE = ["Because the rain kept falling","Since the alarm never rang","Because the funding was cut",
    "Since the bridge had collapsed","Because the yeast was fresh","Since the drought had lasted months",
    "Because the password was leaked","Since the engine had overheated","Because the referee missed the foul","Since the vaccine was distributed"]
CE_TRAIN_EFFECT = ["so the streets were soon flooded","and therefore she overslept badly","so the whole project was cancelled",
    "and so the traffic was diverted","so the bread rose beautifully","and therefore the crops all failed",
    "so the account was quickly hijacked","and so the car finally stalled","so the goal was allowed to stand","and therefore the outbreak subsided"]
# implicit: connective-STRIPPED bare clauses (no because/so/therefore) -- tests causal ROLE not markers
CE_TEST_CAUSE = ["The dam upstream had burst overnight","A spark landed in the dry brush",
    "The supplier doubled its prices","The keystone had cracked years earlier",
    "The virus mutated in the spring","The pilot ignored the warning light",
    "The seeds were planted too late","The contract omitted a penalty clause"]
CE_TEST_EFFECT = ["The valley below lay under water by dawn","The whole hillside was ash by morning",
    "The store shelves emptied within a week","The tower leaned further each passing year",
    "Hospitals filled past capacity by June","The aircraft lost power over the ridge",
    "The harvest came in thin and small","Disputes dragged through the courts for years"]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))

def resid(prompt):
    cap = capture_greedy_trajectory(rt, scenario_id="hard", prompt=prompt, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0, LSTAR, :].astype(np.float64)

def char_ngram_vec(text, vocab):
    t = text.lower()
    counts = {}
    for n in (2, 3, 4):
        for i in range(len(t) - n + 1):
            g = t[i:i+n]; counts[g] = counts.get(g, 0) + 1
    v = np.array([counts.get(g, 0) for g in vocab], dtype=np.float64)
    nrm = np.linalg.norm(v)
    return v / nrm if nrm > 0 else v

def build_vocab(texts):
    seen = set()
    for t in texts:
        t = t.lower()
        for n in (2, 3, 4):
            for i in range(len(t) - n + 1):
                seen.add(t[i:i+n])
    return sorted(seen)

def nn_acc(train_pos, train_neg, test_pos, test_neg, featfn):
    cp = np.mean([featfn(t) for t in train_pos], axis=0)
    cn = np.mean([featfn(t) for t in train_neg], axis=0)
    correct = 0; total = 0
    for t, lab in [(x, 1) for x in test_pos] + [(x, 0) for x in test_neg]:
        v = featfn(t)
        pred = 1 if np.linalg.norm(v - cp) < np.linalg.norm(v - cn) else 0
        correct += (pred == lab); total += 1
    return correct / total

def run_axis(name, tr_pos, tr_neg, te_pos, te_neg):
    # activation detector: train on explicit, test on implicit
    act_acc = nn_acc(tr_pos, tr_neg, te_pos, te_neg, resid)
    # char-ngram surface baseline: vocab from TRAIN only (fair), same protocol
    vocab = build_vocab(tr_pos + tr_neg)
    cng = lambda t: char_ngram_vec(t, vocab)
    ngram_acc = nn_acc(tr_pos, tr_neg, te_pos, te_neg, cng)
    # shuffle null on activations
    rng = np.random.default_rng(20260821)
    labels = [1]*len(te_pos) + [0]*len(te_neg); rng.shuffle(labels)
    cp = np.mean([resid(t) for t in tr_pos], axis=0); cn = np.mean([resid(t) for t in tr_neg], axis=0)
    tests = te_pos + te_neg
    sh = np.mean([ (1 if np.linalg.norm(resid(t)-cp) < np.linalg.norm(resid(t)-cn) else 0) == lab
                   for t, lab in zip(tests, labels)])
    hardened = act_acc >= 0.70 and act_acc - ngram_acc >= 0.10
    return {"axis": name, "activation_acc_on_implicit": round(act_acc,3),
            "char_ngram_surface_acc": round(ngram_acc,3), "shuffle_null": round(float(sh),3),
            "activation_beats_surface": bool(act_acc > ngram_acc),
            "hardened": bool(hardened)}

print("running valence hardening (36 passes) ...", flush=True)
r_val = run_axis("^2/^3 valence (implicit scenario)", VAL_TRAIN_POS, VAL_TRAIN_NEG, VAL_TEST_POS, VAL_TEST_NEG)
print("running cause/effect hardening (36 passes) ...", flush=True)
r_ce = run_axis("^8/^9 cause_effect (connective-stripped)", CE_TRAIN_CAUSE, CE_TRAIN_EFFECT, CE_TEST_CAUSE, CE_TEST_EFFECT)

out = {"layer": LSTAR, "axes": [r_val, r_ce],
       "rule": "HARDENED iff activation acc >= 0.70 AND beats char-ngram surface baseline by >= 0.10"}
raw = json.dumps(out, indent=2, sort_keys=True).encode()
(SP/"detector_validation_v6_hardening_results.json").write_bytes(raw)

print("\n==== FRAMING / SURFACE HARDENING (train=explicit, test=implicit, layer 6) ====")
for r in (r_val, r_ce):
    print(f"\n  {r['axis']}")
    print(f"    activation detector on implicit set : {r['activation_acc_on_implicit']:.3f}")
    print(f"    char-ngram SURFACE baseline         : {r['char_ngram_surface_acc']:.3f}")
    print(f"    shuffle null                        : {r['shuffle_null']:.3f}")
    print(f"    activation beats surface            : {r['activation_beats_surface']}")
    print(f"    VERDICT                             : {'HARDENED' if r['hardened'] else 'NOT HARDENED (surface-confounded or weak)'}")
print(f"\nsha256={hashlib.sha256(raw).hexdigest()[:16]}")
