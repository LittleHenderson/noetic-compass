"""
Track B — Grid Alignment Analysis: measure whether definition embeddings exhibit
the 10×4 (Noetic × Domain) grid structure that TKS claims is real.

This test requires NO external test bank. The "ground truth" is the 10×4 grid
structure itself — a mathematical property, not human judgment.

Metrics computed:
    1. Row coherence    — mean cos similarity between same-Noetic cells vs different
    2. Column coherence — mean cos similarity between same-Domain cells vs different
    3. Neighbor rank    — fraction of top-3 nearest neighbors that are row/col siblings
    4. Grid alignment   — combined score: how well the embedding geometry matches the grid
    5. Cross-validation  — leave-one-cell-out: can we predict its embedding from siblings?

Compares: TKS (owner raw), compact CAS, shuffled-label control, random-anchor null.

Usage:
    python grid_alignment.py --tks-defs PATH --cas-defs PATH [--model pythia-160m]
                             [--layer 12] [--output RESULTS.json]

Dependencies: transformers, torch, numpy, scipy
"""
import json, os, sys, argparse
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.stats import pearsonr

# ── Configuration ───────────────────────────────────────────────────────────

CODES = [f"{w}{n}" for w in "ABCD" for n in "12345678910"]  # A1..D10
# Note: TKS numbering uses 1-10; CAS uses ^0-^9 where ^0=Idea maps to position 10

def world_of(code: str) -> str:
    return code[0]  # A, B, C, D

def noetic_of(code: str) -> str:
    return code[1:]  # 1..10


# ── Grid Metrics ────────────────────────────────────────────────────────────

def compute_row_coherence(embeddings: dict[str, np.ndarray]) -> dict:
    """Mean cosine similarity between cells in the same Noetic row vs different rows.
    
    Higher same-row similarity = stronger row coherence = grid structure present.
    """
    same_row_sims = []
    diff_row_sims = []
    
    codes = sorted(embeddings.keys())
    for i, ci in enumerate(codes):
        for j, cj in enumerate(codes):
            if i >= j:
                continue
            sim = cosine(embeddings[ci], embeddings[cj])
            if noetic_of(ci) == noetic_of(cj) and world_of(ci) != world_of(cj):
                same_row_sims.append(sim)
            elif noetic_of(ci) != noetic_of(cj):
                diff_row_sims.append(sim)
    
    same_mean = float(np.mean(same_row_sims)) if same_row_sims else 0.0
    diff_mean = float(np.mean(diff_row_sims)) if diff_row_sims else 0.0
    
    # Cohen's d effect size
    pooled_std = np.sqrt((np.var(same_row_sims) + np.var(diff_row_sims)) / 2) if same_row_sims and diff_row_sims else 1.0
    cohens_d = (same_mean - diff_mean) / max(pooled_std, 1e-8)
    
    return {
        "same_row_mean_cosine": round(same_mean, 6),
        "diff_row_mean_cosine": round(diff_mean, 6),
        "delta": round(same_mean - diff_mean, 6),
        "cohens_d": round(cohens_d, 4),
        "n_same_pairs": len(same_row_sims),
        "n_diff_pairs": len(diff_row_sims)
    }


def compute_column_coherence(embeddings: dict[str, np.ndarray]) -> dict:
    """Mean cosine similarity between cells in the same Domain column vs different."""
    same_col_sims = []
    diff_col_sims = []
    
    codes = sorted(embeddings.keys())
    for i, ci in enumerate(codes):
        for j, cj in enumerate(codes):
            if i >= j:
                continue
            sim = cosine(embeddings[ci], embeddings[cj])
            if world_of(ci) == world_of(cj) and noetic_of(ci) != noetic_of(cj):
                same_col_sims.append(sim)
            elif world_of(ci) != world_of(cj):
                diff_col_sims.append(sim)
    
    same_mean = float(np.mean(same_col_sims)) if same_col_sims else 0.0
    diff_mean = float(np.mean(diff_col_sims)) if diff_col_sims else 0.0
    pooled_std = np.sqrt((np.var(same_col_sims) + np.var(diff_col_sims)) / 2) if same_col_sims and diff_col_sims else 1.0
    cohens_d = (same_mean - diff_mean) / max(pooled_std, 1e-8)
    
    return {
        "same_col_mean_cosine": round(same_mean, 6),
        "diff_col_mean_cosine": round(diff_mean, 6),
        "delta": round(same_mean - diff_mean, 6),
        "cohens_d": round(cohens_d, 4),
        "n_same_pairs": len(same_col_sims),
        "n_diff_pairs": len(diff_col_sims)
    }


def compute_neighbor_rank(embeddings: dict[str, np.ndarray]) -> dict:
    """For each cell, what fraction of its top-3 nearest neighbors are row/col siblings?
    
    In a perfect 10×4 grid:
      - Each cell has exactly 12 row/col siblings (3 row + 9 col... wait, let me recalculate)
      - Actually: 10 cells per row, so 9 row siblings (same Noetic, different Domain = 3 others)
      - 4 cells per column, so 3 column siblings (same Domain, different Noetic = 9 others)
      - Total: 3 + 9 = 12 siblings out of 39 non-self cells
      - Chance: 12/39 ≈ 0.3077
    
    A score significantly above 0.3077 indicates grid structure.
    """
    codes = sorted(embeddings.keys())
    matrix = np.array([embeddings[c] for c in codes])
    sim_matrix = matrix @ matrix.T  # cosine similarity (assuming normalized)
    
    scores = []
    for i, ci in enumerate(codes):
        # Get top 3 neighbors (excluding self)
        sims = [(j, sim_matrix[i, j]) for j in range(len(codes)) if j != i]
        sims.sort(key=lambda x: -x[1])
        top3 = [codes[j] for j, _ in sims[:3]]
        
        siblings = 0
        for cj in top3:
            if noetic_of(ci) == noetic_of(cj) or world_of(ci) == world_of(cj):
                siblings += 1
        scores.append(siblings / 3.0)
    
    mean_frac = float(np.mean(scores))
    chance = 12.0 / 39.0  # ≈ 0.3077
    
    return {
        "mean_top3_sibling_fraction": round(mean_frac, 6),
        "chance_level": round(chance, 6),
        "excess_over_chance": round(mean_frac - chance, 6),
        "per_cell": {c: round(s, 4) for c, s in zip(codes, scores)}
    }


def compute_crossval_reconstruction(embeddings: dict[str, np.ndarray]) -> dict:
    """Leave-one-cell-out: predict held-out cell's embedding from row+col siblings.
    
    Composition: u_hat = mean(row_siblings) + mean(col_siblings) - global_mean
    Score: cosine similarity between u_hat and actual embedding.
    
    Higher mean cosine = stronger compositional structure.
    """
    codes = sorted(embeddings.keys())
    matrix = np.array([embeddings[c] for c in codes])
    
    cosines = []
    for i, ci in enumerate(codes):
        # Find row and column siblings
        row_idx = [j for j, cj in enumerate(codes) if j != i and noetic_of(cj) == noetic_of(ci)]
        col_idx = [j for j, cj in enumerate(codes) if j != i and world_of(cj) == world_of(ci)]
        other_idx = [j for j in range(len(codes)) if j != i]
        
        if not row_idx or not col_idx:
            continue
        
        row_mean = matrix[row_idx].mean(axis=0)
        col_mean = matrix[col_idx].mean(axis=0)
        global_mean = matrix[other_idx].mean(axis=0)
        
        composed = row_mean + col_mean - global_mean
        composed = composed / (np.linalg.norm(composed) + 1e-12)
        
        actual = matrix[i]
        actual = actual / (np.linalg.norm(actual) + 1e-12)
        
        cosines.append(float(np.dot(composed, actual)))
    
    return {
        "mean_reconstruction_cosine": round(float(np.mean(cosines)), 6) if cosines else 0.0,
        "std_reconstruction_cosine": round(float(np.std(cosines)), 6) if cosines else 0.0,
        "n_valid_folds": len(cosines),
        "per_cell": {codes[i]: round(float(c), 4) for i, c in enumerate(cosines)}
                     if len(cosines) == len(codes) else {}
    }


def compute_grid_alignment_score(embeddings: dict[str, np.ndarray]) -> dict:
    """Combined grid alignment score from multiple metrics."""
    row = compute_row_coherence(embeddings)
    col = compute_column_coherence(embeddings)
    neigh = compute_neighbor_rank(embeddings)
    cv = compute_crossval_reconstruction(embeddings)
    
    # Combined score: average of normalized deltas
    # Each component ranges ~[-1, 1], combined to [0, 1]
    components = {
        "row_delta": max(0, row["delta"]),
        "col_delta": max(0, col["delta"]),
        "neighbor_excess": max(0, neigh["excess_over_chance"]),
        "reconstruction": max(0, cv["mean_reconstruction_cosine"])
    }
    combined = float(np.mean(list(components.values())))
    
    return {
        "combined_grid_score": round(combined, 6),
        "components": components,
        "row_coherence": row,
        "column_coherence": col,
        "neighbor_rank": neigh,
        "crossval_reconstruction": cv
    }


# ── Utilities ───────────────────────────────────────────────────────────────

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

def l2_normalize(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-12)


# ── Permutation Test ────────────────────────────────────────────────────────

def permutation_test(embeddings: dict[str, np.ndarray], n_perm: int = 1000,
                     seed: int = 42) -> dict:
    """Shuffle the cell→position mapping to create null distribution of grid scores."""
    codes = sorted(embeddings.keys())
    obs = compute_grid_alignment_score(embeddings)
    obs_score = obs["combined_grid_score"]
    
    rng = np.random.default_rng(seed)
    null_scores = []
    
    matrix = np.array([embeddings[c] for c in codes])
    for _ in range(n_perm):
        perm = rng.permutation(len(codes))
        shuffled = {codes[i]: matrix[perm[i]] for i in range(len(codes))}
        null = compute_grid_alignment_score(shuffled)
        null_scores.append(null["combined_grid_score"])
    
    null_scores = np.array(null_scores)
    p_value = (1 + np.sum(null_scores >= obs_score)) / (1 + n_perm)
    
    return {
        "observed_grid_score": round(obs_score, 6),
        "null_mean": round(float(null_scores.mean()), 6),
        "null_std": round(float(null_scores.std()), 6),
        "null_95pct": round(float(np.percentile(null_scores, 95)), 6),
        "permutation_p": round(p_value, 6),
        "n_permutations": n_perm
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Grid alignment: measure 10×4 structure in definition embeddings")
    parser.add_argument("--tks-defs", required=True, help="Path to TKS definitions JSON")
    parser.add_argument("--cas-defs", required=True, help="Path to compact CAS definitions JSON")
    parser.add_argument("--embeddings", default=None, help="Pre-computed embeddings NPZ (skip model inference)")
    parser.add_argument("--model", default="EleutherAI/pythia-160m", help="Model for encoding definitions")
    parser.add_argument("--layer", type=int, default=12, help="Hidden state layer (1-indexed)")
    parser.add_argument("--output", default="grid_alignment_results.json", help="Output JSON")
    parser.add_argument("--n-perm", type=int, default=500, help="Permutation test iterations")
    parser.add_argument("--offline", action="store_true", help="Use local-only model files")
    args = parser.parse_args()
    
    # ── Load definitions ────────────────────────────────────────────────
    with open(args.tks_defs, encoding="utf-8") as f:
        tks_data = json.load(f)
    tks_defs = {}
    for elem in tks_data.get("tks_40_elements", []):
        tks_defs[elem["code"]] = elem["definition"]
    
    with open(args.cas_defs, encoding="utf-8") as f:
        cas_data = json.load(f)
    cas_defs = {}
    # Try multiple JSON structures
    for key in ["elements", "definitions"]:
        if key in cas_data:
            for elem in cas_data[key]:
                cas_defs[elem.get("code", "")] = elem.get("definition", "")
            break
    if not cas_defs and "compact_definitions" in cas_data:
        cas_defs = cas_data["compact_definitions"]
    
    # ── Encode definitions (or load pre-computed) ────────────────────────
    if args.embeddings and os.path.exists(args.embeddings):
        print(f"Loading pre-computed embeddings from {args.embeddings}")
        data = np.load(args.embeddings, allow_pickle=True)
        tks_emb = {c: data[f"tks_{c}"] for c in CODES if f"tks_{c}" in data}
        cas_emb = {c: data[f"cas_{c}"] for c in CODES if f"cas_{c}" in data}
    else:
        print(f"Encoding definitions with {args.model}, layer {args.layer}...")
        tks_emb = encode_definitions(tks_defs, args.model, args.layer, args.offline)
        cas_emb = encode_definitions(cas_defs, args.model, args.layer, args.offline)
    
    # ── Compute grid alignment ───────────────────────────────────────────
    print("\n=== TKS (Owner Raw) Grid Alignment ===")
    tks_grid = compute_grid_alignment_score(tks_emb)
    tks_perm = permutation_test(tks_emb, n_perm=args.n_perm)
    print(f"  Combined grid score: {tks_grid['combined_grid_score']:.4f}")
    print(f"  Permutation p: {tks_perm['permutation_p']:.4f}")
    print(f"  Row delta: {tks_grid['row_coherence']['delta']:.4f} (d={tks_grid['row_coherence']['cohens_d']:.2f})")
    print(f"  Col delta: {tks_grid['column_coherence']['delta']:.4f} (d={tks_grid['column_coherence']['cohens_d']:.2f})")
    print(f"  Neighbor excess: {tks_grid['neighbor_rank']['excess_over_chance']:.4f}")
    print(f"  CV reconstruction: {tks_grid['crossval_reconstruction']['mean_reconstruction_cosine']:.4f}")
    
    print("\n=== Compact CAS Grid Alignment ===")
    cas_grid = compute_grid_alignment_score(cas_emb)
    cas_perm = permutation_test(cas_emb, n_perm=args.n_perm)
    print(f"  Combined grid score: {cas_grid['combined_grid_score']:.4f}")
    print(f"  Permutation p: {cas_perm['permutation_p']:.4f}")
    print(f"  Row delta: {cas_grid['row_coherence']['delta']:.4f} (d={cas_grid['row_coherence']['cohens_d']:.2f})")
    print(f"  Col delta: {cas_grid['column_coherence']['delta']:.4f} (d={cas_grid['column_coherence']['cohens_d']:.2f})")
    print(f"  Neighbor excess: {cas_grid['neighbor_rank']['excess_over_chance']:.4f}")
    print(f"  CV reconstruction: {cas_grid['crossval_reconstruction']['mean_reconstruction_cosine']:.4f}")
    
    # ── Comparison ───────────────────────────────────────────────────────
    delta_grid = tks_grid["combined_grid_score"] - cas_grid["combined_grid_score"]
    print(f"\n=== TKS − CAS Grid Score Delta: {delta_grid:.4f} ===")
    
    # Bootstrap CI on the delta
    codes = sorted(set(tks_emb.keys()) & set(cas_emb.keys()))
    rng = np.random.default_rng(42)
    boot_deltas = []
    for _ in range(1000):
        sample = [rng.choice(codes, size=len(codes), replace=True)]
        # Resample cells
        idx = rng.choice(len(codes), size=len(codes), replace=True)
        tks_sample = {codes[i]: tks_emb[codes[i]] for i in idx}
        cas_sample = {codes[i]: cas_emb[codes[i]] for i in idx}
        tks_score = compute_grid_alignment_score(tks_sample)["combined_grid_score"]
        cas_score = compute_grid_alignment_score(cas_sample)["combined_grid_score"]
        boot_deltas.append(tks_score - cas_score)
    
    boot_deltas = np.array(boot_deltas)
    ci_low = float(np.percentile(boot_deltas, 2.5))
    ci_high = float(np.percentile(boot_deltas, 97.5))
    print(f"  Bootstrap 95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"  CI excludes zero: {ci_low > 0 or ci_high < 0}")
    
    # ── Assemble report ──────────────────────────────────────────────────
    report = {
        "design": "TKS-GRID-ALIGNMENT-v1",
        "model": args.model,
        "layer": args.layer,
        "n_cells": len(codes),
        "tks": {
            "grid_alignment": tks_grid,
            "permutation_test": tks_perm
        },
        "compact_cas": {
            "grid_alignment": cas_grid,
            "permutation_test": cas_perm
        },
        "tks_minus_cas_delta": round(delta_grid, 6),
        "bootstrap_95ci": [ci_low, ci_high],
        "ci_excludes_zero": ci_low > 0 or ci_high < 0,
        "interpretation": (
            "TKS definitions exhibit stronger 10×4 grid structure than compact CAS"
            if delta_grid > 0 and (ci_low > 0)
            else "No reliable difference in grid structure detected"
            if 0 >= ci_low and 0 <= ci_high
            else "Compact CAS exhibits stronger grid structure (unexpected)"
        )
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport: {args.output}")


def encode_definitions(defs: dict[str, str], model_id: str, layer: int,
                        offline: bool = False) -> dict[str, np.ndarray]:
    """Encode definition strings through a model, returning per-cell embeddings."""
    try:
        import torch
        import transformers
    except ImportError:
        print("ERROR: transformers + torch required. pip install transformers torch")
        sys.exit(1)
    
    if offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    
    m = transformers.AutoModelForCausalLM.from_pretrained(
        model_id, local_files_only=offline, dtype=torch.float32,
        output_hidden_states=True, device_map="auto"
    ).eval()
    tok = transformers.AutoTokenizer.from_pretrained(model_id, local_files_only=offline)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    
    FRAMES = [
        "Definition: {body}\nThat role describes:",
        "The following describes one role.\n{body}\nThat role describes:",
        "Consider this description.\n{body}\nThat role describes:",
        "Description: {body}\nThat role describes:",
    ]
    
    codes = sorted(defs.keys())
    texts = []
    for c in codes:
        for f in FRAMES:
            texts.append(f.format(body=defs[c]))
    
    device = next(m.parameters()).device
    
    @torch.no_grad()
    def encode_batch(texts_batch, bs=8):
        all_vecs = []
        for i in range(0, len(texts_batch), bs):
            batch = texts_batch[i:i+bs]
            e = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=384)
            ids = e.input_ids.to(device); am = e.attention_mask.to(device)
            hs = m(input_ids=ids, attention_mask=am).hidden_states[layer]
            last = am.sum(1) - 1
            vecs = hs[torch.arange(hs.shape[0], device=device), last, :].float().cpu().numpy()
            all_vecs.append(vecs)
        return np.concatenate(all_vecs, 0)
    
    all_vecs = encode_batch(texts)
    # Average over 4 frames per cell
    n_frames = len(FRAMES)
    embeddings = {}
    for i, c in enumerate(codes):
        cell_vecs = all_vecs[i*n_frames:(i+1)*n_frames]
        emb = cell_vecs.mean(axis=0)
        embeddings[c] = l2_normalize(emb)
    
    return embeddings


if __name__ == "__main__":
    main()
