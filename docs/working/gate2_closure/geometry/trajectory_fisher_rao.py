"""GRID-LAYER-TRAJECTORY-v1 — FISHER-RAO SIMPLEX VARIANT

Extends the embedding-space trajectory experiment by projecting definition
embeddings onto the 39-dimensional open probability simplex (the cognitive
state space specified in CAS v7.4, Correction 4) and measuring reconstruction
via the Bhattacharyya coefficient under the Fisher-Rao metric.

Key difference from embedding-space cosine reconstruction:
  - Cosine: measures vector alignment in Euclidean space
  - Fisher-Rao/BC: measures distribution overlap on the probability simplex
  - The simplex creates competition between states — probability mass is conserved
  - The Fisher-Rao metric weights differences by 1/pk — high-probability states
    contribute more to the distance than low-probability ones

This is the NATURAL metric for the cognitive state space per the Noetic Topos
paper (peer_review/noetic_topos_extracted_structure_20260523.md, §5-6).
"""
import os, json, sys, collections, re
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
TAU = 0.2          # softmax temperature — pre-registered, not tuned
EPSILON = 1e-8     # ensures open simplex: all pk > 0

tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token

FRAMES = ("Definition: {b}\nThat role describes:",
          "The following describes one role.\n{b}\nThat role describes:",
          "Consider this description.\n{b}\nThat role describes:",
          "Description: {b}\nThat role describes:")

# ═══════════════════════════════════════════════════════════════════════════
# FISHER-RAO / SIMPLEX MATH
# ═══════════════════════════════════════════════════════════════════════════

def embeddings_to_simplex(embeddings_dict):
    """Project 40 definition embeddings onto the 39-simplex.

    For each definition i, compute cosine similarity to all 40 definitions,
    apply softmax with temperature τ, add ε for open-simplex constraint,
    and renormalize.

    Returns: dict {code: 40-dim probability vector}
    """
    codes_sorted = sorted(embeddings_dict.keys())
    M = np.array([embeddings_dict[c] for c in codes_sorted])  # (40, d)
    # Normalize rows
    M = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
    # Cosine similarity matrix
    C = M @ M.T  # (40, 40)
    # Softmax with temperature
    C_scaled = C / TAU
    # Subtract max per row for numerical stability
    C_stable = C_scaled - C_scaled.max(axis=1, keepdims=True)
    P = np.exp(C_stable)
    P = P / P.sum(axis=1, keepdims=True)
    # Add epsilon and renormalize (open simplex: pk > 0)
    P = P + EPSILON
    P = P / P.sum(axis=1, keepdims=True)
    return {c: P[i] for i, c in enumerate(codes_sorted)}


def bhattacharyya_coefficient(p, q):
    """BC(p,q) = Σ_k √(p_k · q_k) ∈ [EPSILON, 1.0]"""
    bc = np.sum(np.sqrt(p * q))
    return float(np.clip(bc, 0.0, 1.0))


def geodesic_distance(p, q):
    """d(p,q) = 2·arccos(BC(p,q)) ∈ [0, π]"""
    bc = bhattacharyya_coefficient(p, q)
    return float(2.0 * np.arccos(np.clip(bc, 0.0, 1.0)))


def simplex_reconstruction(simplex_dict):
    """Leave-one-cell-out reconstruction on the simplex.

    For held-out cell c:
      p_row = mean of row siblings' probability vectors
      p_col = mean of column siblings' probability vectors
      p_all = mean of all other cells' probability vectors
      p_pred = normalize(p_row + p_col - p_all)
    Score: BC(p_pred, p_actual).

    Returns: mean BC across all 40 folds.
    """
    codes_sorted = sorted(simplex_dict.keys())
    P = np.array([simplex_dict[c] for c in codes_sorted])  # (40, 40)
    bcs = []
    for i, ci in enumerate(codes_sorted):
        ri = [j for j, cj in enumerate(codes_sorted) if j != i and cj[1:] == ci[1:]]
        cl = [j for j, cj in enumerate(codes_sorted) if j != i and cj[0] == ci[0]]
        oi = [j for j in range(len(codes_sorted)) if j != i]
        if not ri or not cl:
            continue
        p_row = P[ri].mean(axis=0)
        p_col = P[cl].mean(axis=0)
        p_all = P[oi].mean(axis=0)
        # Compose in simplex space
        p_pred = p_row + p_col - p_all
        # Clamp negative values to epsilon (open simplex constraint)
        p_pred = np.maximum(p_pred, EPSILON)
        p_pred = p_pred / p_pred.sum()
        # Score
        bc = bhattacharyya_coefficient(p_pred, P[i])
        bcs.append(bc)
    return float(np.mean(bcs)) if bcs else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# ENCODING (same as trajectory.py)
# ═══════════════════════════════════════════════════════════════════════════

@torch.no_grad()
def encode_all_layers(defs):
    texts = [f.format(b=defs[c]) for c in codes for f in FRAMES]
    all_hidden = []
    for i in range(0, len(texts), 32):
        e = tok(texts[i:i+32], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0"); am = e.attention_mask.to("cuda:0")
        out = m(input_ids=ids, attention_mask=am)
        last_pos = am.sum(1) - 1
        layer_vecs = []
        for layer_hs in out.hidden_states:
            vecs = layer_hs[torch.arange(layer_hs.shape[0], device=layer_hs.device), last_pos, :].float().cpu().numpy()
            layer_vecs.append(vecs)
        all_hidden.append(layer_vecs)
    n_layers = len(all_hidden[0])
    layers = []
    for li in range(n_layers):
        layer_data = np.concatenate([batch[li] for batch in all_hidden], 0)
        M = layer_data.reshape(len(codes), len(FRAMES), -1).mean(1)
        layers.append({c: M[i] for i, c in enumerate(codes)})
    return layers


# ═══════════════════════════════════════════════════════════════════════════
# LEXICAL BASELINE (bag-of-words on simplex)
# ═══════════════════════════════════════════════════════════════════════════

STOP = set("the a an of and or to in is are be for on with that this it as by "
           "from at was were not no all any some its their".split())

# Build vocabulary
all_texts = [tks[c] for c in codes] + [cmp_[c] for c in codes]
all_words = set()
for t in all_texts:
    all_words.update(w.lower() for w in re.findall(r"[a-z]+", str(t).lower())
                     if w.lower() not in STOP and len(w) > 2)
vocab = sorted(all_words)
word_to_idx = {w: i for i, w in enumerate(vocab)}

def bow_to_array(text):
    vec = np.zeros(len(vocab))
    for w in re.findall(r"[a-z]+", str(text).lower()):
        if w.lower() not in STOP and len(w) > 2 and w.lower() in word_to_idx:
            vec[word_to_idx[w.lower()]] += 1
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

lex_emb_tks = {c: bow_to_array(tks[c]) for c in codes}
lex_emb_cmp = {c: bow_to_array(cmp_[c]) for c in codes}
lex_sim_tks = embeddings_to_simplex(lex_emb_tks)
lex_sim_cmp = embeddings_to_simplex(lex_emb_cmp)
lex_tks_recon = simplex_reconstruction(lex_sim_tks)
lex_cmp_recon = simplex_reconstruction(lex_sim_cmp)

print(f"LEXICAL (simplex)  TKS BC reconstruction     {lex_tks_recon:.6f}", flush=True)
print(f"LEXICAL (simplex)  compact CAS BC             {lex_cmp_recon:.6f}", flush=True)
print(f"LEXICAL (simplex)  margin (CAS - TKS)         {lex_cmp_recon - lex_tks_recon:+.6f}", flush=True)
print(f"LEXICAL (simplex)  flat across layers         by construction", flush=True)
print(flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# MODEL ENCODING
# ═══════════════════════════════════════════════════════════════════════════

print("Encoding all layers...", flush=True)
layers_tks = encode_all_layers(tks)
layers_cmp = encode_all_layers(cmp_)
print(f"  {len(layers_tks)} layers captured", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# COMPUTE RECONSTRUCTION AT EACH LAYER
# ═══════════════════════════════════════════════════════════════════════════

n_transformer_layers = len(layers_tks) - 1
results = []
for li in range(1, n_transformer_layers + 1):
    sim_tks = embeddings_to_simplex(layers_tks[li])
    sim_cmp = embeddings_to_simplex(layers_cmp[li])
    rt = simplex_reconstruction(sim_tks)
    rc = simplex_reconstruction(sim_cmp)
    results.append({"layer": li, "tks_bc": round(rt, 6), "compact_bc": round(rc, 6),
                    "margin": round(rt - rc, 6)})
    print(f"  L{li:2d}  TKS_BC={rt:.6f}  compact_BC={rc:.6f}  margin={rt-rc:+.6f}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# CRITERIA
# ═══════════════════════════════════════════════════════════════════════════

from scipy import stats as sp_stats

layers_arr = np.array([r["layer"] for r in results])
tks_arr = np.array([r["tks_bc"] for r in results])
cmp_arr = np.array([r["compact_bc"] for r in results])
gap_arr = cmp_arr - tks_arr  # positive = compact ahead

# T1: TKS slope positive
rho_tks, p_tks = sp_stats.spearmanr(layers_arr, tks_arr)
p_tks_one = p_tks / 2 if rho_tks > 0 else 1.0 - p_tks / 2
T1 = bool(rho_tks > 0 and p_tks_one < 0.05)

# T2: TKS slope > compact slope
beta_tks, _ = np.polyfit(layers_arr, tks_arr, 1)
beta_cmp, _ = np.polyfit(layers_arr, cmp_arr, 1)
beta_diff = beta_tks - beta_cmp
rng = np.random.default_rng(42)
boot_diffs = []
for _ in range(1000):
    idx = rng.choice(len(layers_arr), size=len(layers_arr), replace=True)
    b1, _ = np.polyfit(layers_arr[idx], tks_arr[idx], 1)
    b2, _ = np.polyfit(layers_arr[idx], cmp_arr[idx], 1)
    boot_diffs.append(b1 - b2)
boot_diffs = np.array(boot_diffs)
ci_low = float(np.percentile(boot_diffs, 2.5))
ci_high = float(np.percentile(boot_diffs, 97.5))
T2 = bool(ci_low > 0.005)

# T3: gap compresses
gap_l1 = gap_arr[0]
gap_l12 = gap_arr[-1]
T3 = bool(gap_l1 > gap_l12)

# T4: lexical flat
lex_arr = np.full_like(layers_arr, lex_tks_recon, dtype=float)
rho_lex, p_lex = sp_stats.spearmanr(layers_arr, lex_arr)
T4 = bool(abs(rho_lex) < 0.3 or p_lex > 0.05)

# V1: lexical ordering confirmed
V1 = bool(lex_cmp_recon > lex_tks_recon)

# V2: metric content-dependent
rng2 = np.random.default_rng(11)
perm_pvals = []
for li in range(1, n_transformer_layers + 1):
    sim = embeddings_to_simplex(layers_tks[li])
    obs = simplex_reconstruction(sim)
    null = []
    for _ in range(200):
        perm = rng2.permutation(len(codes))
        # Shuffle which cell has which probability vector
        P = np.array([sim[c] for c in codes])
        P_shuf = P[perm]
        sim_shuf = {codes[i]: P_shuf[i] for i in range(len(codes))}
        null.append(simplex_reconstruction(sim_shuf))
    null = np.array(null)
    pv = (1 + int((null >= obs).sum())) / (1 + len(null))
    perm_pvals.append(pv)
perm_pvals = np.array(perm_pvals)
floor = 1 / 201
n_content_dependent = int(np.sum((perm_pvals > floor) & (perm_pvals < 1.0)))
V2 = bool(n_content_dependent >= 2)

# V3: no ceiling collapse (BC ceiling is 1.0, but with ε it's slightly below)
n_below_ceiling = int(np.sum((tks_arr < 0.999) & (cmp_arr < 0.999)))
V3 = bool(n_below_ceiling >= 6)

# V4 (NEW): simplex not degenerate — the probability distributions should not
# be uniform. A uniform distribution means every definition relates equally to
# all others, which means the softmax collapsed.
# Check: mean entropy across all 40 definitions at layer 6 (midpoint)
mid_layer = layers_tks[6]
sim_mid = embeddings_to_simplex(mid_layer)
entropies = []
for c in codes:
    p = sim_mid[c]
    ent = -np.sum(p * np.log(p + 1e-12))
    entropies.append(ent)
max_entropy = np.log(40)  # ~3.689 — uniform distribution
mean_entropy = float(np.mean(entropies))
V4 = bool(mean_entropy < 0.95 * max_entropy)  # at least 5% below uniform

criteria = {
    "T1_tks_slope_positive": T1,
    "T2_tks_slope_exceeds_compact": T2,
    "T3_gap_compresses": T3,
    "T4_lexical_flat": T4,
    "V1_lexical_ordering_confirmed": V1,
    "V2_metric_content_dependent": V2,
    "V3_no_ceiling_collapse": V3,
    "V4_simplex_not_degenerate": V4,
}

print("\n=== CRITERIA (Fisher-Rao simplex) ===", flush=True)
for k, v in criteria.items():
    print(f"  {k:40s} {'PASS' if v else 'FAIL'}", flush=True)

print(f"\n  Spearman rho(TKS, layer)   = {rho_tks:.4f}  p_one = {p_tks_one:.4f}", flush=True)
print(f"  beta TKS     = {beta_tks:.6f}/layer", flush=True)
print(f"  beta compact = {beta_cmp:.6f}/layer", flush=True)
print(f"  beta diff    = {beta_diff:.6f}/layer  95% CI [{ci_low:.6f}, {ci_high:.6f}]", flush=True)
print(f"  gap(L1)      = {gap_l1:.6f}  gap(L12) = {gap_l12:.6f}", flush=True)
print(f"  mid-layer entropy = {mean_entropy:.4f}  (max uniform = {max_entropy:.4f})", flush=True)
print(f"  n layers below BC ceiling: {n_below_ceiling}/12", flush=True)
print(f"  n layers content-dependent: {n_content_dependent}/12", flush=True)
print(f"  temperature τ = {TAU}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════════════════════════

V_gates_ok = V1 and V2 and V3 and V4
T_gates_ok = T1 and T2 and T3
if not V_gates_ok:
    verdict = "VOID"
elif T_gates_ok:
    verdict = "TRAJECTORY_CONFIRMED"
else:
    verdict = "NOT_LICENSED"

print(f"\nVERDICT: {verdict}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

out = {
    "design": "GRID-LAYER-TRAJECTORY-FISHER-RAO-v1",
    "model": "EleutherAI/pythia-1b",
    "n_layers": n_transformer_layers,
    "temperature": TAU,
    "epsilon": EPSILON,
    "lexical": {"tks_bc": round(lex_tks_recon, 6),
                "compact_bc": round(lex_cmp_recon, 6),
                "margin": round(lex_cmp_recon - lex_tks_recon, 6)},
    "per_layer": results,
    "statistics": {
        "spearman_rho_tks": round(float(rho_tks), 6),
        "spearman_p_one_tailed": round(float(p_tks_one), 6),
        "beta_tks_per_layer": round(float(beta_tks), 6),
        "beta_compact_per_layer": round(float(beta_cmp), 6),
        "beta_diff": round(float(beta_diff), 6),
        "beta_diff_95ci_low": ci_low,
        "beta_diff_95ci_high": ci_high,
        "gap_L1": round(float(gap_l1), 6),
        "gap_L12": round(float(gap_l12), 6),
        "mid_layer_mean_entropy": round(mean_entropy, 6),
        "max_uniform_entropy": round(max_entropy, 6),
        "n_content_dependent_layers": n_content_dependent,
        "n_below_ceiling_layers": n_below_ceiling,
    },
    "criteria": criteria,
    "verdict": verdict,
}
json.dump(out, open("/workspace/item4/trajectory_fisher_rao_results.json", "w"),
          indent=2, sort_keys=True)
print("WROTE trajectory_fisher_rao_results.json", flush=True)
