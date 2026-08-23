# -*- coding: utf-8 -*-
"""Domain axis vs matched non-CAS four-level abstractness taxonomy (Tinbergen).

Frontier #1 lever (spec sheet 10.1): the domain axis on the SAME fixtures and SAME
activations, probed twice -- once with CAS domain labels (P/C/E/O), once with
Tinbergen's four questions assigned by a bijection FROZEN BEFORE CAPTURE in
PREREG_DOMAIN_VS_TINBERGEN_20260822.md. pythia-160m-reserialized, CPU, $0.
"""
import ast, sys, json, hashlib, math, pathlib
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
DET = REPO / "docs" / "working" / "detector_validation_20260821"
SP = pathlib.Path(__file__).resolve().parent
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
from app.runtime.open_weight.engine import RuntimeLoadConfig, load_open_weight_runtime, capture_greedy_trajectory
from app.runtime.open_weight.identity import LocalModelSnapshot

# ---- fixture: verbatim TOPICS from detector_validation_v4_domain.py (ast-extracted) ----
v4src = (DET / "detector_validation_v4_domain.py").read_text(encoding="utf-8")
mod = ast.parse(v4src)
TOPICS = None
for node in mod.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if getattr(t, "id", None) == "TOPICS":
                TOPICS = ast.literal_eval(node.value)
assert TOPICS is not None and len(TOPICS) == 8, "TOPICS extraction failed"
DOMAINS = ["P", "C", "E", "O"]
TOPIC_NAMES = list(TOPICS.keys())
TRAIN_TOPICS = TOPIC_NAMES[:6]
TEST_TOPICS = TOPIC_NAMES[6:]

FIXTURE = {"domains": DOMAINS, "topics": TOPICS}
fixture_bytes = json.dumps(FIXTURE, sort_keys=True, indent=1).encode("utf-8")
FIXTURE_SHA = hashlib.sha256(fixture_bytes).hexdigest()
(SP / "fixture_domain_v4.json").write_bytes(fixture_bytes)

# ---- bijections (frozen BEFORE capture; see prereg 3.3) ----
TIN_PRIMARY = {   # abstractness-aligned: CAS domain descent P>C>E>O maps onto
    "P": "phylogeny / evolutionary history",   # Tinbergen ultimate->proximate
    "C": "function / survival value",
    "E": "ontogeny / development",
    "O": "mechanism / proximate causation"}
TIN_SENSITIVITY = {  # positional, arm-E convention (first-listed -> first-listed)
    "P": "mechanism / proximate causation",
    "C": "ontogeny / development",
    "E": "function / survival value",
    "O": "phylogeny / evolutionary history"}
LABEL_ORDER = {"phylogeny / evolutionary history": 0, "function / survival value": 1,
               "ontogeny / development": 2, "mechanism / proximate causation": 3}

# ---- runtime ----
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"
STORE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS\48bed170-da71-4777-8d00-6c209e1475ff\scratchpad\models\alias--pythia-160m-reserialized")
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

def resid_all(prompt):
    cap = capture_greedy_trajectory(rt, scenario_id="dom4tin", prompt=prompt, max_new_tokens=1, seed=0)
    arr = cap.arrays if hasattr(cap, "arrays") else cap["arrays"]
    return np.asarray(arr["residual_states"])[0].astype(np.float64)  # (layers, hidden)

print("capturing 32 real residuals (8 topics x 4 domains), all layers...", flush=True)
X = {t: {d: resid_all(TOPICS[t][d]) for d in DOMAINS} for t in TOPIC_NAMES}

def nc_eval(labels_map, train_topics, test_topics, li, subspace=None, shuffle_seed=None):
    """Nearest-centroid 4-way eval at layer li. labels_map: domain -> label string."""
    labvals = sorted(set(labels_map.values()), key=lambda s: LABEL_ORDER.get(s, 99))
    def vec(t, d):
        v = X[t][d][li]
        return v @ subspace if subspace is not None else v
    cent = {lab: np.mean([vec(t, d) for t in train_topics for d in DOMAINS if labels_map[d] == lab], axis=0)
            for lab in labvals}
    test_items = [(t, d) for t in test_topics for d in DOMAINS]
    labels = [labels_map[d] for _, d in test_items]
    if shuffle_seed is not None:
        rng = np.random.default_rng(shuffle_seed)
        labels = list(labels); rng.shuffle(labels)
    y_true, y_pred = [], []
    for (t, d_orig), lab in zip(test_items, labels):
        v = vec(t, d_orig)
        pred = min(labvals, key=lambda s: np.linalg.norm(v - cent[s]))
        y_true.append(lab); y_pred.append(pred)
    return {"y_true": y_true, "y_pred": y_pred,
            "acc": float(np.mean([a == b for a, b in zip(y_true, y_pred)]))}

def mcnemar_exact_p(cas_right, tin_right):
    """Two-sided exact McNemar on paired item correctness. cas_right/tin_right: bool arrays."""
    b = sum(1 for c, t in zip(cas_right, tin_right) if c and not t)  # CAS right, TIN wrong
    c = sum(1 for c, t in zip(cas_right, tin_right) if not c and t)  # CAS wrong, TIN right
    n = b + c
    if n == 0:
        return 1.0, b, c
    p = sum(math.comb(n, k) for k in range(0, n + 1)
            if abs(2 * k - n) >= abs(2 * b - n)) / (2.0 ** n)
    return float(p), b, c

def run_arm(labels_map, name, n_shuffle=100):
    per = {}
    best = {"layer": None, "acc": -1.0}
    for li in range(L):
        real = nc_eval(labels_map, TRAIN_TOPICS, TEST_TOPICS, li)
        rng = np.random.default_rng(1729 + li)
        Q, _ = np.linalg.qr(rng.standard_normal((768, 4)))
        randsub = nc_eval(labels_map, TRAIN_TOPICS, TEST_TOPICS, li, subspace=Q)
        shuf_accs = [nc_eval(labels_map, TRAIN_TOPICS, TEST_TOPICS, li, shuffle_seed=20260822 + s)["acc"]
                     for s in range(n_shuffle)]
        per[li] = {"real": real["acc"], "random_subspace": randsub["acc"],
                   "shuffle_mean": float(np.mean(shuf_accs)),
                   "shuffle_max": float(np.max(shuf_accs)),
                   "y_true": real["y_true"], "y_pred": real["y_pred"]}
        if real["acc"] > best["acc"]:
            best = {"layer": li, "acc": real["acc"], "random_subspace": randsub["acc"],
                    "shuffle_mean": float(np.mean(shuf_accs)),
                    "y_true": real["y_true"], "y_pred": real["y_pred"]}
    lm = float(np.mean([per[li]["real"] for li in range(L)]))
    return {"name": name, "layer_sweep": {str(k): {kk: vv for kk, vv in v.items() if kk != "y_true" and kk != "y_pred"} for k, v in per.items()},
            "best_layer": best["layer"], "best_acc": best["acc"],
            "best_random_subspace": best["random_subspace"],
            "best_shuffle_mean": best["shuffle_mean"],
            "layer_mean": lm, "per_layer_preds": {str(k): v for k, v in per.items()}}

cas = run_arm({d: d for d in DOMAINS}, "CAS_DOMAIN_PCEO")
tin_primary = run_arm(TIN_PRIMARY, "TINBERGEN_ALIGNED_PRIMARY")
tin_sens = run_arm(TIN_SENSITIVITY, "TINBERGEN_POSITIONAL_SENSITIVITY")

# ---- McNemar at best CAS layer (pre-registered C4) ----
bl = cas["best_layer"]
cas_preds = cas["per_layer_preds"][str(bl)]
tin_preds = tin_primary["per_layer_preds"][str(bl)]
cas_right = [a == b for a, b in zip(cas_preds["y_true"], cas_preds["y_pred"])]
tin_right = [a == b for a, b in zip(tin_preds["y_true"], tin_preds["y_pred"])]
p_mcn, bdisc, cdisc = mcnemar_exact_p(cas_right, tin_right)

C1 = (cas["best_acc"] >= 0.50) and (cas["layer_mean"] >= 0.40)
C2 = tin_primary["layer_mean"] >= 0.40
C3 = (cas["layer_mean"] - tin_primary["layer_mean"]) >= 0.10
C4 = p_mcn <= 0.05
verdict = "DOMAIN_BEATS_MATCHED_ABSTRACTNESS" if (C1 and C2 and C3 and C4) else "DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS"

cap_blob = b"".join(X[t][d].tobytes() for t in TOPIC_NAMES for d in DOMAINS)
runner_sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
out = {
    "schema": "domain_vs_tinbergen_20260822.v1",
    "prereg": "PREREG_DOMAIN_VS_TINBERGEN_20260822.md",
    "fixture_sha256": FIXTURE_SHA,
    "runner_sha256": runner_sha,
    "captures_sha256": hashlib.sha256(cap_blob).hexdigest(),
    "model": {"model_id": "pythia-160m-reserialized", "revision": REV, "layers": L},
    "design": "nearest_centroid_4way_train6topics_test2topics_all12layers",
    "chance": 0.25, "n_test_items": 8,
    "bijection_primary": TIN_PRIMARY,
    "bijection_sensitivity": TIN_SENSITIVITY,
    "arms": {"CAS_DOMAIN": {k: v for k, v in cas.items() if k != "per_layer_preds"},
             "TIN_PRIMARY": {k: v for k, v in tin_primary.items() if k != "per_layer_preds"},
             "TIN_SENSITIVITY": {k: v for k, v in tin_sens.items() if k != "per_layer_preds"}},
    "mcnemar_at_best_cas_layer": {"layer": bl, "p": p_mcn, "cas_right_tin_wrong": bdisc, "cas_wrong_tin_right": cdisc},
    "criteria": {"C1_cas_sanity": bool(C1), "C2_tin_sanity": bool(C2),
                 "C3_cas_minus_tin_ge_010": bool(C3), "delta_layer_mean": cas["layer_mean"] - tin_primary["layer_mean"],
                 "C4_mcnemar_le_005": bool(C4), "mcnemar_p": p_mcn},
    "verdict": verdict,
}
raw = json.dumps(out, indent=2, sort_keys=True).encode("utf-8")
(SP / "domain_vs_tinbergen_results.json").write_bytes(raw)
print(json.dumps({"verdict": verdict, "C1": bool(C1), "C2": bool(C2), "C3": bool(C3),
                  "C4": bool(C4), "delta_lm": round(cas["layer_mean"] - tin_primary["layer_mean"], 6),
                  "cas_lm": round(cas["layer_mean"], 6), "tin_lm": round(tin_primary["layer_mean"], 6),
                  "cas_bl": round(cas["best_acc"], 6), "tin_bl": round(tin_primary["best_acc"], 6),
                  "mcnemar_p": p_mcn, "fixture_sha256": FIXTURE_SHA[:16], "runner_sha256": runner_sha[:16],
                  "captures_sha256": hashlib.sha256(cap_blob).hexdigest()[:16]}, indent=2))
