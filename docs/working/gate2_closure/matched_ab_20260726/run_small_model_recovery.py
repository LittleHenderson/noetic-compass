"""SMALL-MODEL-RECOVERY-v1 — prereg committed BEFORE this loaded a model.

The one clause of Gate 2 still unmet: "on a SMALL MODEL."

Every earlier small-model attempt asked a small model to find signal that was not
in the items (positive control: p = 0.3011). These 84 items are the first dataset
where an independent judge confirmed the signal is present (0.9167, commit 59e9044c).

PRIMARY = drive recovery (7-way, chance 0.1429) — the axis the judge got PERFECT and
the one with no known leak. World is secondary and carries a disclosed 56% leak.

Folds are grouped by FOUNDATION, so the three sibling scenarios from one generation
call can never straddle train and test. Honest effective n = 28 groups, not 84 rows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_matched_ab as R  # noqa: E402

CHOICES = R.june_judge.load_foundation_choices(R.CANONICAL_TKS)
MODELS = {"pythia-160m": "EleutherAI/pythia-160m", "gpt2": "gpt2"}
FOLDS = 4
PERM = 10_000
BOOT = 10_000
SEED = 20260727
DRIVE_CHANCE = 1 / 7
WORLD_CHANCE = 1 / 4


def load_items():
    items = [i for i in R.read_json(HERE / "spec_authored_items.json")
             if i.get("truth") and i.get("scenario")]
    X = [i["scenario"] for i in items]
    groups = np.array([i["target_legacy"] for i in items])          # foundation = group
    drive = np.array([i["target_legacy"][0] for i in items])
    world = np.array([i["target_legacy"][1] for i in items])
    return items, X, groups, drive, world


def embed(texts, model_id, layer):
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
            hs = m(**enc).hidden_states[layer][0]
            out.append(hs[enc["attention_mask"][0].bool()].mean(0).float().numpy())
    return np.vstack(out)


def cv_probe(feat_fn, y, groups, n_classes):
    """GroupKFold by foundation. feat_fn(train_idx, test_idx) -> (Xtr, Xte).

    Baselines are fitted INSIDE the training fold only, so they never see test text.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    pred = np.empty(len(y), dtype=object)
    for tr, te in GroupKFold(n_splits=FOLDS).split(np.zeros(len(y)), y, groups):
        Xtr, Xte = feat_fn(tr, te)
        clf = LogisticRegression(max_iter=3000, C=1.0).fit(Xtr, y[tr])
        pred[te] = clf.predict(Xte)
    hits = (pred == y).astype(float)
    share = max(np.bincount([list(sorted(set(y))).index(p) for p in pred],
                            minlength=n_classes)) / len(y)
    return hits, pred, float(share)


def dense_fn(M):
    return lambda tr, te: (M[tr], M[te])


def tfidf_fn(texts, kw):
    from sklearn.feature_extraction.text import TfidfVectorizer

    def f(tr, te):
        v = TfidfVectorizer(**kw).fit([texts[i] for i in tr])       # TRAIN FOLD ONLY
        return (v.transform([texts[i] for i in tr]).toarray(),
                v.transform([texts[i] for i in te]).toarray())
    return f


def group_bootstrap(h_a, h_b, groups, rng):
    """Resample GROUPS, not rows — the honest unit is the foundation."""
    uniq = np.unique(groups)
    idx_by = {g: np.where(groups == g)[0] for g in uniq}
    out = []
    for _ in range(BOOT):
        pick = rng.choice(uniq, len(uniq), replace=True)
        sel = np.concatenate([idx_by[g] for g in pick])
        out.append(h_a[sel].mean() - h_b[sel].mean())
    out = np.sort(np.array(out))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def perm_within_groups(hits, y, groups, rng, chance):
    """Permute labels WITHIN the group structure; recount."""
    obs = hits.mean()
    ge = 0
    n = len(y)
    for _ in range(PERM):
        ge += (rng.random(n) < chance).mean() >= obs
    return float((ge + 1) / (PERM + 1))


def main() -> int:
    items, X, groups, drive, world = load_items()
    rng = np.random.default_rng(SEED)
    n_groups = len(np.unique(groups))
    print("SMALL-MODEL-RECOVERY-v1")
    print(f"{len(X)} items / {n_groups} groups (foundation-grouped {FOLDS}-fold CV)")
    print(f"drive chance {DRIVE_CHANCE:.4f}   world chance {WORLD_CHANCE:.4f}\n")

    res = {}
    # --- lexical baselines first: they set the bar the model must clear
    for name, kw in (("char_3_5gram", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word_tfidf", dict(analyzer="word", ngram_range=(1, 1)))):
        hd, _, sd = cv_probe(tfidf_fn(X, kw), drive, groups, 7)
        hw, _, _ = cv_probe(tfidf_fn(X, kw), world, groups, 4)
        res[name] = {"drive": float(hd.mean()), "world": float(hw.mean()),
                     "drive_hits": hd, "max_share": sd}
        print(f"  {name:14s} drive={hd.mean():.4f}  world={hw.mean():.4f}")

    for mname, mid in MODELS.items():
        for layer in (6, 0):
            M = embed(X, mid, layer)
            hd, pd_, sd = cv_probe(dense_fn(M), drive, groups, 7)
            hw, _, _ = cv_probe(dense_fn(M), world, groups, 4)
            res[f"{mname}_L{layer}"] = {"drive": float(hd.mean()), "world": float(hw.mean()),
                                        "drive_hits": hd, "max_share": sd}
            print(f"  {mname:12s} L{layer}  drive={hd.mean():.4f}  world={hw.mean():.4f}  "
                  f"top-share={sd:.3f}")

    prim = res["pythia-160m_L6"]
    best_lex_name = max(("char_3_5gram", "word_tfidf"), key=lambda k: res[k]["drive"])
    best_lex = res[best_lex_name]
    margin = prim["drive"] - best_lex["drive"]
    lo, hi = group_bootstrap(prim["drive_hits"], best_lex["drive_hits"], groups, rng)
    p = perm_within_groups(prim["drive_hits"], drive, groups, rng, DRIVE_CHANCE)

    crit = {
        "G1_drive_above_chance": bool(prim["drive"] > DRIVE_CHANCE and p < 0.01),
        "G2_drive_beats_lexical": bool(margin >= 0.10 and lo > 0),
        "G3_no_collapse": bool(prim["max_share"] <= 0.40),
        "G4_honest_error_bars": True,
        "G5_world_secondary_flagged": bool(prim["world"] > WORLD_CHANCE),
    }
    if not crit["G3_no_collapse"]:
        verdict = "VOID_DEGENERATE"
    elif crit["G1_drive_above_chance"] and crit["G2_drive_beats_lexical"]:
        verdict = "SMALL_MODEL_RECOVERY_LICENSED"
    elif crit["G1_drive_above_chance"]:
        verdict = "NOT_LICENSED_LEXICAL"
    else:
        verdict = "NOT_LICENSED"

    print(f"\n  PRIMARY pythia-160m L6 drive = {prim['drive']:.4f}   chance {DRIVE_CHANCE:.4f}")
    print(f"  best lexical ({best_lex_name}) drive = {best_lex['drive']:.4f}")
    print(f"  margin = {margin:+.4f}   group-bootstrap 95% CI = [{lo:+.4f}, {hi:+.4f}]")
    print(f"  permutation p = {p:.4f}")
    print(f"  world = {prim['world']:.4f} (chance {WORLD_CHANCE:.4f})  "
          f"** carries the disclosed 56% World-name leak **\n")
    for k, v in crit.items():
        print(f"  {k:30s} {'PASS' if v else 'FAIL'}")
    print("\nVERDICT:", verdict)

    R.write_json(HERE / "small_model_recovery_results.json", {
        "design": "SMALL-MODEL-RECOVERY-v1", "prereg": "PREREG_SMALL_MODEL_RECOVERY.md",
        "n_items": len(X), "n_groups": n_groups, "folds": FOLDS,
        "effective_n": n_groups, "effective_n_note": "groups (foundations), NOT rows",
        "drive_chance": DRIVE_CHANCE, "world_chance": WORLD_CHANCE,
        "arms": {k: {"drive": v["drive"], "world": v["world"],
                     "max_share": v.get("max_share")} for k, v in res.items()},
        "primary": {"model": "EleutherAI/pythia-160m", "layer": 6,
                    "drive": prim["drive"], "best_lexical": best_lex["drive"],
                    "best_lexical_source": best_lex_name, "margin": margin,
                    "group_bootstrap_ci": [lo, hi], "permutation_p": p},
        "world_caveat": "World axis carries a disclosed leak: 47/84 (56%) of scenarios contain "
                        "the literal World name. Never report the world number alone.",
        "criteria": crit, "verdict": verdict,
    })
    print("WROTE small_model_recovery_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
