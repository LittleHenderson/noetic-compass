"""SMALL-MODEL-SEMANTIC-MATCH-v1 — prereg committed BEFORE this loaded a model.

Closes the two gaps that block any Gate 2 claim from the positive control:
  1. gemini-2.5-flash is not a small model   -> pythia-160m (+ gpt2 replication)
  2. no tier separated strings from meaning  -> compact vs TKS phrasings of the
     SAME cell, measured word overlap mean Jaccard 0.0209

Task: 28x28 cosine similarity, top-1 in both directions, n = 56 queries.
Fair comparison: char 3-5-gram TF-IDF and word TF-IDF on identical items.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_matched_ab as R  # noqa: E402

CHANCE = 1.0 / 28.0
BOOT = 10_000
PERM = 10_000
SEED = 20260727
MODELS = {"pythia-160m": "EleutherAI/pythia-160m", "gpt2": "gpt2"}


def load_pairs():
    tks = R.june_judge.load_foundation_choices(R.CANONICAL_TKS)
    comp = R.compact_foundation_choices()
    fs = sorted(tks)
    return fs, [tks[f]["meaning"] for f in fs], [comp[f]["meaning"] for f in fs], \
        [tks[f]["drive"] for f in fs], [tks[f]["register"] for f in fs]


def cos_matrix(A, B):
    A = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return A @ B.T


def embed_model(texts, model_id, layer):
    import torch
    import transformers
    tok = transformers.AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    m = transformers.AutoModel.from_pretrained(model_id, output_hidden_states=True).eval()
    out = []
    with torch.no_grad():
        for t in texts:
            enc = tok(t, return_tensors="pt", truncation=True, max_length=512)
            hs = m(**enc).hidden_states[layer][0]          # (seq, hidden)
            mask = enc["attention_mask"][0].bool()
            out.append(hs[mask].mean(0).float().numpy())
    return np.vstack(out)


def embed_surface(a_texts, b_texts, mode):
    from sklearn.feature_extraction.text import TfidfVectorizer
    kw = dict(analyzer="char_wb", ngram_range=(3, 5)) if mode == "char" \
        else dict(analyzer="word", ngram_range=(1, 1))
    v = TfidfVectorizer(**kw).fit(list(a_texts) + list(b_texts))
    return v.transform(a_texts).toarray(), v.transform(b_texts).toarray()


def top1_both(S):
    """S[i,j] = sim(compact_i, tks_j). Returns per-query correctness, n=56."""
    fwd = S.argmax(axis=1)                 # compact -> TKS
    bwd = S.argmax(axis=0)                 # TKS -> compact
    n = S.shape[0]
    hits = np.concatenate([(fwd == np.arange(n)), (bwd == np.arange(n))])
    return hits.astype(float), np.concatenate([fwd, bwd])


def group_acc(preds, labels):
    n = len(labels)
    truth = np.array(labels + labels)
    got = np.array([labels[p] for p in preds])
    return float((truth == got).mean())


def boot_diff(a, b, rng):
    n = len(a)
    d = []
    for _ in range(BOOT):
        idx = rng.integers(0, n, n)
        d.append(a[idx].mean() - b[idx].mean())
    d = np.sort(np.array(d))
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def perm_p(hits, rng):
    """Label-preserving: permute the key assignment, recount top-1."""
    obs = hits.mean()
    n = len(hits)
    ge = 0
    for _ in range(PERM):
        # under the null the query-key pairing is arbitrary: each query is
        # correct with probability 1/28 independently
        ge += (rng.random(n) < CHANCE).mean() >= obs
    return float((ge + 1) / (PERM + 1))


def main() -> int:
    fs, tks_txt, comp_txt, drives, regs = load_pairs()
    rng = np.random.default_rng(SEED)

    # tier-validity evidence, recomputed here and reported
    def words(s): return set(re.findall(r"[a-z]+", s.lower()))
    jac = [len(words(a) & words(b)) / max(1, len(words(a) | words(b)))
           for a, b in zip(tks_txt, comp_txt)]

    print("SMALL-MODEL-SEMANTIC-MATCH-v1")
    print(f"n=56 queries (28 each direction)  chance={CHANCE:.4f}")
    print(f"tier overlap: mean Jaccard={np.mean(jac):.4f} max={np.max(jac):.4f}\n")

    res = {}
    # --- surface controls first: they can VOID the run on their own (S3)
    for mode in ("char", "word"):
        A, B = embed_surface(comp_txt, tks_txt, mode)
        hits, preds = top1_both(cos_matrix(A, B))
        res[f"surface_{mode}"] = {
            "top1": float(hits.mean()), "hits": hits.tolist(),
            "drive_acc": group_acc(preds, drives), "register_acc": group_acc(preds, regs),
        }
        print(f"  surface {mode:5s} top1={hits.mean():.4f}")

    best_surface = max(res["surface_char"]["top1"], res["surface_word"]["top1"])
    best_key = "surface_char" if res["surface_char"]["top1"] >= res["surface_word"]["top1"] else "surface_word"

    for name, mid in MODELS.items():
        for layer, tag in ((6, "L6"), (0, "L0")):
            A = embed_model(comp_txt, mid, layer)
            B = embed_model(tks_txt, mid, layer)
            hits, preds = top1_both(cos_matrix(A, B))
            share = max(np.bincount(preds, minlength=28)) / len(preds)
            res[f"{name}_{tag}"] = {
                "top1": float(hits.mean()), "hits": hits.tolist(),
                "drive_acc": group_acc(preds, drives), "register_acc": group_acc(preds, regs),
                "max_single_foundation_share": float(share),
            }
            print(f"  {name:12s} {tag}  top1={hits.mean():.4f}  "
                  f"drive={res[f'{name}_{tag}']['drive_acc']:.4f}  "
                  f"reg={res[f'{name}_{tag}']['register_acc']:.4f}  "
                  f"top-share={share:.3f}")

    prim = res["pythia-160m_L6"]
    ph = np.array(prim["hits"])
    sh = np.array(res[best_key]["hits"])
    lo, hi = boot_diff(ph, sh, rng)
    p = perm_p(ph, rng)
    margin = prim["top1"] - best_surface

    crit = {
        "S1_beats_surface": bool(margin >= 0.10 and lo > 0),
        "S2_above_chance": bool(p < 0.01),
        "S3_tier_valid": bool(best_surface <= 0.15),
        "S4_no_collapse": bool(prim["max_single_foundation_share"] <= 0.30),
        "S5_depth_contributes": bool(prim["top1"] > res["pythia-160m_L0"]["top1"]),
    }
    if not crit["S3_tier_valid"]:
        verdict = "VOID_TIER_CONTAMINATED"
    elif not crit["S4_no_collapse"]:
        verdict = "VOID_DEGENERATE"
    elif crit["S1_beats_surface"] and crit["S2_above_chance"]:
        verdict = "LICENSED"
    else:
        verdict = "NOT_LICENSED"

    print(f"\n  primary  pythia-160m L6 top1={prim['top1']:.4f}")
    print(f"  best surface ({best_key}) = {best_surface:.4f}")
    print(f"  margin = {margin:+.4f}   bootstrap 95% CI = [{lo:+.4f}, {hi:+.4f}]")
    print(f"  permutation p = {p:.4f}   (chance {CHANCE:.4f})\n")
    for k, v in crit.items():
        print(f"  {k:26s} {'PASS' if v else 'FAIL'}")
    print("\nVERDICT:", verdict)

    R.write_json(HERE / "small_model_semantic_results.json", {
        "design": "SMALL-MODEL-SEMANTIC-MATCH-v1",
        "n_queries": 56, "chance": round(CHANCE, 6),
        "tier_overlap_jaccard": {"mean": float(np.mean(jac)), "max": float(np.max(jac))},
        "results": {k: {kk: vv for kk, vv in v.items() if kk != "hits"} for k, v in res.items()},
        "primary": {
            "model": "EleutherAI/pythia-160m", "layer": 6, "top1": prim["top1"],
            "best_surface": best_surface, "best_surface_source": best_key,
            "margin": margin, "bootstrap_ci": [lo, hi], "permutation_p": p,
        },
        "criteria": crit, "verdict": verdict,
    })
    print("WROTE small_model_semantic_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
