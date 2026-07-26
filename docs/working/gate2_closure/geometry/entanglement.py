"""NOETIC-ENTANGLEMENT-v1 — Hail Mary. Pre-registered BEFORE this ran.

Mathematical foundation: CAS v7.4 Master, Chapter 20 (Density Matrix Formalism).

  Theorem 20.38 (Information Loss under Partial Trace):
    S(ρ) ≤ S(ρ_World) + S(ρ_Element)
    Equality iff ρ = ρ_World ⊗ ρ_Element (no World-Element correlations).
    The difference is the quantum mutual information I(W;E) ≥ 0.

Claim under test:
  TKS definitions are DERIVED by composing World × Noetic. The composition
  generates entailments neither component alone contains. If true, the
  definition embeddings should show World-Element ENTANGLEMENT — the embedding
  of B5 (Mental Female) cannot be expressed as "Female-ness" + "Mental-ness"
  because the composition creates genuinely new content ("open-mindedness").

  Compact CAS definitions are CONCATENATED: Noetic boilerplate + Domain suffix.
  They SHOULD be factorizable — the embedding of B5_compact ≈ Female_def +
  Mental_qualifier, with no interaction term.

Test:
  1. Encode all 40 definitions through the model.
  2. Compute the 40×40 Gram matrix G[i,j] = cos(e_i, e_j).
  3. Construct density matrix ρ = G / Tr(G) on the 40-dim space indexed by |W,n⟩.
  4. Partial trace over Elements → ρ_World (4×4).
  5. Partial trace over Worlds → ρ_Element (10×10).
  6. Von Neumann entropy S(σ) = -Σ λ_k log λ_k (λ_k = eigenvalues of σ).
  7. Mutual information: I = S(ρ_World) + S(ρ_Element) - S(ρ).

Prediction:
  TKS:       I > 0  (World-Element entanglement present)
  compact:   I ≈ 0  (factorizable, additive structure)
  shuffled:  I ≈ 0  (random assignment destroys structure)

Lexical baseline: same construction on bag-of-words vectors.
  Prediction: lexical TKS I > lexical compact I (TKS text is more varied),
  but the MODEL should AMPLIFY the TKS-compact I-difference if compositional
  structure is genuinely semantic, not just lexical.

Degeneracy guard:
  If S(ρ) < 0.5 (near-pure state, all embeddings nearly identical), VOID.
  If both TKS and compact have I < 0.01, VOID (undetectable).
"""
import os, json, re, collections
import numpy as np
os.environ.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","TOKENIZERS_PARALLELISM":"false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
L = 12
tks = json.load(open("/workspace/item4/tks_defs.json", encoding="utf-8"))
cmp_ = json.load(open("/workspace/item4/cas_defs.json", encoding="utf-8"))
codes = sorted(tks)
rng0 = np.random.default_rng(20260725)
perm0 = rng0.permutation(len(codes))
shuf = {codes[i]: tks[codes[perm0[i]]] for i in range(len(codes))}

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
FRAMES = ("Definition: {b}\nThat role describes:",
          "The following describes one role.\n{b}\nThat role describes:",
          "Consider this description.\n{b}\nThat role describes:",
          "Description: {b}\nThat role describes:")

@torch.no_grad()
def encode(defs):
    texts = [f.format(b=defs[c]) for c in codes for f in FRAMES]
    out = []
    for i in range(0, len(texts), 32):
        e = tok(texts[i:i+32], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0"); am = e.attention_mask.to("cuda:0")
        hs = m(input_ids=ids, attention_mask=am).hidden_states[L]
        last = am.sum(1) - 1
        out.append(hs[torch.arange(hs.shape[0], device=hs.device), last, :].float().cpu().numpy())
    return np.concatenate(out, 0).reshape(len(codes), len(FRAMES), -1).mean(1)

# ═══════════════════════════════════════════════════════════════════════════
# QUANTUM MUTUAL INFORMATION
# ═══════════════════════════════════════════════════════════════════════════

# Index mapping: codes are A1..A10, B1..B10, C1..C10, D1..D10
worlds = ["A","B","C","D"]
noetics = ["1","2","3","4","5","6","7","8","9","10"]
code_to_idx = {c: i for i, c in enumerate(codes)}

def build_density_matrix(embeddings_dict):
    """Construct ρ = G/Tr(G) from the 40×40 Gram matrix of normalized embeddings."""
    M = np.array([embeddings_dict[c] for c in codes])  # (40, d)
    M = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
    G = M @ M.T  # 40×40 Gram matrix
    rho = G / np.trace(G)  # unit trace
    return rho

def partial_trace_world(rho):
    """Tr_Element: trace over Noetic index → 4×4 World density matrix.
    
    rho is indexed as rho[(w,n), (w',n')].
    ρ_World[w, w'] = Σ_n rho[(w,n), (w',n)].
    """
    rho_w = np.zeros((4, 4))
    for wi, w in enumerate(worlds):
        for wj, wp in enumerate(worlds):
            s = 0.0
            for n in noetics:
                i = code_to_idx[f"{w}{n}"]
                j = code_to_idx[f"{wp}{n}"]
                s += rho[i, j]
            rho_w[wi, wj] = s
    return rho_w

def partial_trace_element(rho):
    """Tr_World: trace over World index → 10×10 Element density matrix.
    
    ρ_Element[n, n'] = Σ_w rho[(w,n), (w,n')].
    """
    rho_e = np.zeros((10, 10))
    for ni, n in enumerate(noetics):
        for nj, np_ in enumerate(noetics):
            s = 0.0
            for w in worlds:
                i = code_to_idx[f"{w}{n}"]
                j = code_to_idx[f"{w}{np_}"]
                s += rho[i, j]
            rho_e[ni, nj] = s
    return rho_e

def von_neumann_entropy(rho):
    """S(ρ) = -Σ λ_k log λ_k for eigenvalues λ_k > 0."""
    eigvals = np.linalg.eigvalsh(rho)
    eigvals = eigvals[eigvals > 1e-12]  # discard numerical zeros
    if len(eigvals) == 0:
        return 0.0
    return float(-np.sum(eigvals * np.log(eigvals)))

def mutual_information(embeddings_dict):
    """Compute I(World;Element) from definition embeddings."""
    rho = build_density_matrix(embeddings_dict)
    rho_w = partial_trace_world(rho)
    rho_e = partial_trace_element(rho)
    
    S_total = von_neumann_entropy(rho)
    S_world = von_neumann_entropy(rho_w)
    S_elem  = von_neumann_entropy(rho_e)
    
    I_WE = S_world + S_elem - S_total
    # Clamp to [0, ∞) — numerical errors can produce tiny negatives
    I_WE = max(0.0, I_WE)
    
    return {
        "S_total": round(S_total, 6),
        "S_world": round(S_world, 6),
        "S_element": round(S_elem, 6),
        "I_mutual": round(I_WE, 6),
        "max_possible_I": round(min(np.log(4), np.log(10)), 6),  # min(log|W|, log|E|)
        "eigenvalues_total": [round(float(v), 6) for v in 
                              sorted(np.linalg.eigvalsh(rho), reverse=True)[:5]],
        "rho_world_diag": [round(float(rho_w[i,i]), 6) for i in range(4)],
        "rho_element_diag": [round(float(rho_e[i,i]), 6) for i in range(10)],
    }

# ═══════════════════════════════════════════════════════════════════════════
# MODEL
# ═══════════════════════════════════════════════════════════════════════════

print("Encoding definitions...", flush=True)
E_t, E_c, E_s = encode(tks), encode(cmp_), encode(shuf)

emb_t = {c: E_t[i] for i, c in enumerate(codes)}
emb_c = {c: E_c[i] for i, c in enumerate(codes)}
emb_s = {c: E_s[i] for i, c in enumerate(codes)}

print("\n=== MUTUAL INFORMATION (Model) ===", flush=True)
mi_t = mutual_information(emb_t)
mi_c = mutual_information(emb_c)
mi_s = mutual_information(emb_s)

for name, mi in [("TKS", mi_t), ("compact", mi_c), ("shuffled", mi_s)]:
    print(f"  {name:10s}  I={mi['I_mutual']:.6f}  "
          f"S_tot={mi['S_total']:.4f}  S_w={mi['S_world']:.4f}  S_e={mi['S_element']:.4f}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# LEXICAL BASELINE
# ═══════════════════════════════════════════════════════════════════════════

STOP = set("the a an of and or to in is are be for on with that this it as by "
           "from at was were not no all any some its their".split())
all_texts = [tks[c] for c in codes] + [cmp_[c] for c in codes]
all_words = set()
for t in all_texts:
    all_words.update(w.lower() for w in re.findall(r"[a-z]+", str(t).lower())
                     if w.lower() not in STOP and len(w) > 2)
vocab = sorted(all_words)
w2i = {w: i for i, w in enumerate(vocab)}

def bow(text):
    v = np.zeros(len(vocab))
    for w in re.findall(r"[a-z]+", str(text).lower()):
        if w.lower() not in STOP and len(w) > 2 and w.lower() in w2i:
            v[w2i[w.lower()]] += 1
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

print("\n=== MUTUAL INFORMATION (Lexical) ===", flush=True)
lex_t = {c: bow(tks[c]) for c in codes}
lex_c = {c: bow(cmp_[c]) for c in codes}
lex_s = {c: bow(shuf[c]) for c in codes}

mi_lex_t = mutual_information(lex_t)
mi_lex_c = mutual_information(lex_c)
mi_lex_s = mutual_information(lex_s)

for name, mi in [("TKS_lex", mi_lex_t), ("compact_lex", mi_lex_c), ("shuffled_lex", mi_lex_s)]:
    print(f"  {name:10s}  I={mi['I_mutual']:.6f}  "
          f"S_tot={mi['S_total']:.4f}  S_w={mi['S_world']:.4f}  S_e={mi['S_element']:.4f}", flush=True)

# ═══════════════════════════════════════════════════════════════════════════
# CRITERIA
# ═══════════════════════════════════════════════════════════════════════════

I_tks   = mi_t["I_mutual"]
I_cmp   = mi_c["I_mutual"]
I_shuf  = mi_s["I_mutual"]
I_lex_t = mi_lex_t["I_mutual"]
I_lex_c = mi_lex_c["I_mutual"]
S_tks   = mi_t["S_total"]
S_cmp   = mi_c["S_total"]
S_shuf  = mi_s["S_total"]

# E1: TKS shows entanglement (I > 0.01)
E1 = bool(I_tks > 0.01)

# E2: TKS more entangled than compact (I_tks > I_cmp + 0.01)
E2 = bool(I_tks > I_cmp + 0.01)

# E3: TKS more entangled than its own shuffle (grid structure matters)
E3 = bool(I_tks > I_shuf + 0.01)

# E4: Compact approximately factorizable (I_cmp < 0.05)
E4 = bool(I_cmp < 0.05)

# E5: Model-amplified entanglement: model I-delta > lexical I-delta
#      (TKS-compact I difference is larger in model than in words)
I_delta_model = I_tks - I_cmp
I_delta_lex   = I_lex_t - I_lex_c
E5 = bool(I_delta_model > I_delta_lex + 0.01)

# V1: Non-degenerate density matrix (sufficient entropy)
V1 = bool(S_tks > 0.5 and S_cmp > 0.5 and S_shuf > 0.5)

# V2: Lexical baseline shows the predicted direction (TKS_lex > compact_lex)
V2 = bool(I_lex_t > I_lex_c)

# V3: Shuffled has low I (scrambling destroys structure)
V3 = bool(I_shuf < 0.05)

criteria = {
    "E1_TKS_entangled": E1,
    "E2_TKS_more_entangled_than_compact": E2,
    "E3_TKS_more_entangled_than_shuffled": E3,
    "E4_compact_approximately_factorizable": E4,
    "E5_model_amplifies_entanglement": E5,
    "V1_non_degenerate": V1,
    "V2_lexical_direction_confirmed": V2,
    "V3_shuffled_has_low_I": V3,
}

print("\n=== CRITERIA ===", flush=True)
for k, v in criteria.items():
    print(f"  {k:45s} {'PASS' if v else 'FAIL'}", flush=True)

print(f"\n  I(TKS)       = {I_tks:.6f}", flush=True)
print(f"  I(compact)   = {I_cmp:.6f}", flush=True)
print(f"  I(shuffled)  = {I_shuf:.6f}", flush=True)
print(f"  I(lex TKS)   = {I_lex_t:.6f}", flush=True)
print(f"  I(lex comp)  = {I_lex_c:.6f}", flush=True)
print(f"  model ΔI     = {I_delta_model:.6f}", flush=True)
print(f"  lexical ΔI   = {I_delta_lex:.6f}", flush=True)
print(f"  S(TKS)       = {S_tks:.4f}  (need > 0.5)", flush=True)
print(f"  S(compact)   = {S_cmp:.4f}", flush=True)
print(f"  max possible I = {mi_t['max_possible_I']:.4f}", flush=True)

V_ok = V1 and V2 and V3
E_ok = E1 and E2 and E3 and E4

if not V_ok:
    verdict = "VOID"
elif E_ok:
    verdict = "ENTANGLEMENT_CONFIRMED"
elif E1 and E3:
    verdict = "ENTANGLEMENT_PRESENT_BUT_COMPACT_NOT_FACTORIZABLE"
else:
    verdict = "NOT_LICENSED"

print(f"\nVERDICT: {verdict}", flush=True)

out = {
    "design": "NOETIC-ENTANGLEMENT-v1",
    "model": "EleutherAI/pythia-1b",
    "layer": L,
    "model_mutual_information": {
        "TKS": mi_t, "compact": mi_c, "shuffled": mi_s
    },
    "lexical_mutual_information": {
        "TKS": mi_lex_t, "compact": mi_lex_c, "shuffled": mi_lex_s
    },
    "deltas": {
        "model_TKS_minus_compact": round(I_delta_model, 6),
        "lexical_TKS_minus_compact": round(I_delta_lex, 6),
        "amplification": round(I_delta_model - I_delta_lex, 6),
    },
    "criteria": criteria,
    "verdict": verdict,
}
json.dump(out, open("/workspace/item4/entanglement_results.json", "w"),
          indent=2, sort_keys=True)
print("WROTE entanglement_results.json", flush=True)
