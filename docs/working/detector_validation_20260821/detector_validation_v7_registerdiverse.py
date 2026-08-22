"""Register-diverse hardening -- can a valence detector trained on BOTH registers
generalize to HELD-OUT implicit scenarios and beat the char-ngram surface baseline?

The fix v6 pointed to. Train the activation detector on explicit + implicit-A valence
(register-diverse), test on implicit-B (NEW scenarios, never seen), compare on the same
held-out set against a char-ngram (n=2,3,4) surface baseline trained on the same train text.
HARDENED iff activation >= 0.70 AND beats surface by >= 0.10. Residuals cached (each unique
sentence captured once). Real pythia-160m, attested engine, CPU, $0.
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

EXPL_POS = ["I absolutely love this","This is wonderful and delightful","A fantastic and joyful day",
    "The music was beautiful and uplifting","It tasted delicious and satisfying","A truly excellent result",
    "The gift was charming and heartfelt","A gorgeous and serene view","She felt cheerful and glad","A splendid and pleasant evening"]
EXPL_NEG = ["I absolutely hate this","This is awful and disgusting","A terrible and miserable day",
    "The music was grating and unbearable","It tasted rotten and revolting","A truly dreadful result",
    "The insult was vicious and hurtful","A filthy and menacing view","She felt bitter and sad","A wretched and hostile evening"]
IMPL_A_POS = ["She opened the letter and saw she had been accepted","After years of trying, they finally held their newborn",
    "He crossed the finish line as the crowd rose to their feet","The scholarship would cover every remaining cost",
    "The test came back clear and the doctor smiled","They were reunited at the gate after the long deployment",
    "Her name was the first one called for the prize","The offer arrived with more than she had asked for"]
IMPL_A_NEG = ["She opened the letter and saw she had been rejected","After years of trying, the treatment had failed once more",
    "He collapsed before the finish line as the crowd fell silent","The bill would take everything they had left",
    "The test came back and the doctor looked away","They stood at the gate but no one came off the plane",
    "Her name was the only one missing from the list","The letter arrived with a notice of termination"]
# HELD-OUT implicit test set (B) -- new scenarios, never in training
IMPL_B_POS = ["The jury foreman stood and read the single word they had hoped for",
    "Her hands shook as she unfolded the acceptance she had waited on",
    "The surgeon pulled off the mask and gave a thumbs up",
    "The last payment cleared and the house was finally theirs",
    "The coach put her in for the final minute and she scored",
    "He found the ring still in his coat and she said yes",
    "The rescue team reached them just as the light returned",
    "The results posted and her name sat at the very top"]
IMPL_B_NEG = ["The jury foreman stood and read the word they had feared",
    "Her hands shook as she unfolded the notice she had dreaded",
    "The surgeon pulled off the mask and shook his head slowly",
    "The final notice cleared out what little they had saved",
    "The coach kept her on the bench as the clock ran out",
    "He found the ring still in his coat and she walked away",
    "The rescue team arrived after the light had gone",
    "The results posted and her name was nowhere on the page"]

print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(),
    device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))

_cache = {}
def resid(prompt):
    if prompt not in _cache:
        cap = capture_greedy_trajectory(rt, scenario_id="rd", prompt=prompt, max_new_tokens=1, seed=0)
        arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
        _cache[prompt] = np.asarray(arr["residual_states"])[0, LSTAR, :].astype(np.float64)
    return _cache[prompt]

def char_vec(text, vocab):
    t = text.lower(); c = {}
    for n in (2,3,4):
        for i in range(len(t)-n+1): c[t[i:i+n]] = c.get(t[i:i+n],0)+1
    v = np.array([c.get(g,0) for g in vocab], dtype=np.float64); nz = np.linalg.norm(v)
    return v/nz if nz>0 else v
def vocab_of(texts):
    s=set()
    for t in texts:
        t=t.lower()
        for n in (2,3,4):
            for i in range(len(t)-n+1): s.add(t[i:i+n])
    return sorted(s)

def nn(train_pos, train_neg, test_pos, test_neg, featfn):
    cp = np.mean([featfn(t) for t in train_pos],axis=0); cn = np.mean([featfn(t) for t in train_neg],axis=0)
    correct=total=0
    for t,lab in [(x,1) for x in test_pos]+[(x,0) for x in test_neg]:
        v=featfn(t); pred = 1 if np.linalg.norm(v-cp)<np.linalg.norm(v-cn) else 0
        correct+=(pred==lab); total+=1
    return correct/total

# register-diverse training
TR_POS = EXPL_POS + IMPL_A_POS
TR_NEG = EXPL_NEG + IMPL_A_NEG
print(f"capturing residuals (train {len(TR_POS)+len(TR_NEG)} + test {len(IMPL_B_POS)+len(IMPL_B_NEG)}) ...", flush=True)
for t in TR_POS+TR_NEG+IMPL_B_POS+IMPL_B_NEG: resid(t)

# activation detector, register-diverse train -> held-out implicit test
act = nn(TR_POS, TR_NEG, IMPL_B_POS, IMPL_B_NEG, resid)
# char-ngram surface baseline, same protocol
vocab = vocab_of(TR_POS+TR_NEG); cng = lambda t: char_vec(t, vocab)
ngram = nn(TR_POS, TR_NEG, IMPL_B_POS, IMPL_B_NEG, cng)
# shuffle null
rng = np.random.default_rng(20260821); labels=[1]*len(IMPL_B_POS)+[0]*len(IMPL_B_NEG); rng.shuffle(labels)
cp=np.mean([resid(t) for t in TR_POS],axis=0); cn=np.mean([resid(t) for t in TR_NEG],axis=0)
tests=IMPL_B_POS+IMPL_B_NEG
sh=np.mean([(1 if np.linalg.norm(resid(t)-cp)<np.linalg.norm(resid(t)-cn) else 0)==lab for t,lab in zip(tests,labels)])

# for comparison: the v6 EXPLICIT-ONLY detector on the SAME held-out implicit-B set
act_explonly = nn(EXPL_POS, EXPL_NEG, IMPL_B_POS, IMPL_B_NEG, resid)

hardened = act >= 0.70 and act - ngram >= 0.10
out = {"layer":LSTAR,"axis":"^2/^3 valence, register-diverse train -> held-out implicit test",
       "register_diverse_activation_acc": round(act,3),
       "explicit_only_activation_acc_same_test": round(act_explonly,3),
       "char_ngram_surface_acc": round(ngram,3), "shuffle_null": round(float(sh),3),
       "activation_beats_surface": bool(act>ngram),
       "improvement_over_explicit_only": round(act-act_explonly,3),
       "hardened": bool(hardened),
       "rule":"HARDENED iff register-diverse activation >= 0.70 AND beats char-ngram by >= 0.10"}
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"detector_validation_v7_registerdiverse_results.json").write_bytes(raw)

print("\n==== REGISTER-DIVERSE HARDENING (valence, held-out implicit test, layer 6) ====")
print(f"  register-diverse activation detector : {act:.3f}")
print(f"  explicit-only detector (v6-style)    : {act_explonly:.3f}   (same held-out test)")
print(f"  improvement from adding implicit train: {act-act_explonly:+.3f}")
print(f"  char-ngram SURFACE baseline          : {ngram:.3f}")
print(f"  shuffle null                         : {sh:.3f}")
print(f"  activation beats surface             : {act>ngram}")
print(f"  VERDICT                              : {'HARDENED' if hardened else 'NOT HARDENED'}")
print(f"sha256={hashlib.sha256(raw).hexdigest()[:16]}")
