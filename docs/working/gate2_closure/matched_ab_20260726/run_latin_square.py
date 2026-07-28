"""LATIN-SQUARE-SUCCESSOR-v1 — prereg committed before this ran.

Fixes the structurally unidentifiable World endpoint from SMALL-MODEL-RECOVERY-v1,
where GroupKFold put every same-World group in one fold so each test fold held a
World absent from its own training set (world = 0.0000 exactly = void, not negative).

Frozen Latin square: fold = (world_index + drive_index) mod 4.
Every test fold gets all 7 drives AND all 4 Worlds. Siblings never separate.

Controls, both able to VOID the run:
  C-PERM  labels permuted AT GROUP LEVEL (siblings keep the same permuted label)
  C-BODY  every row fed the SAME constant token; no metadata reaches the extractor
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_matched_ab as R  # noqa: E402

LETTERS = "abcd"
PERM = 10_000
BOOT = 10_000
SEED = 20260727
DRIVE_CHANCE = 1 / 7
WORLD_CHANCE = 1 / 4


def fold_of(legacy: str) -> int:
    """FROZEN Latin square. Explicit, not library ordering."""
    return (LETTERS.index(legacy[1]) + (int(legacy[0]) - 1)) % 4


def fold_table():
    return {f"{d}{w}": fold_of(f"{d}{w}") for d in "1234567" for w in LETTERS}


def load():
    items = [i for i in R.read_json(HERE / "spec_authored_items.json")
             if i.get("truth") and i.get("scenario")]
    X = [i["scenario"] for i in items]
    g = np.array([i["target_legacy"] for i in items])
    return items, X, g, np.array([c[0] for c in g]), np.array([c[1] for c in g])


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
            e = tok(t, return_tensors="pt", truncation=True, max_length=512)
            h = m(**e).hidden_states[layer][0]
            out.append(h[e["attention_mask"][0].bool()].mean(0).float().numpy())
    return np.vstack(out)


def cv(feat, y, folds):
    """Latin-square CV. feat(tr, te) -> (Xtr, Xte). Baselines fit inside train fold only."""
    from sklearn.linear_model import LogisticRegression
    pred = np.empty(len(y), dtype=object)
    for f in range(4):
        te = np.where(folds == f)[0]
        tr = np.where(folds != f)[0]
        Xtr, Xte = feat(tr, te)
        pred[te] = LogisticRegression(max_iter=3000, C=1.0).fit(Xtr, y[tr]).predict(Xte)
    return (pred == y).astype(float), pred


def dense(M):
    return lambda tr, te: (M[tr], M[te])


def tfidf(texts, kw):
    from sklearn.feature_extraction.text import TfidfVectorizer

    def f(tr, te):
        v = TfidfVectorizer(**kw).fit([texts[i] for i in tr])
        return (v.transform([texts[i] for i in tr]).toarray(),
                v.transform([texts[i] for i in te]).toarray())
    return f


def group_boot(a, b, groups, rng):
    u = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in u}
    d = [(lambda s: a[s].mean() - b[s].mean())(
        np.concatenate([idx[g] for g in rng.choice(u, len(u), replace=True)]))
        for _ in range(BOOT)]
    d = np.sort(np.array(d))
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main() -> int:
    items, X, groups, drive, world = load()
    folds = np.array([fold_of(g) for g in groups])
    rng = np.random.default_rng(SEED)

    print("LATIN-SQUARE-SUCCESSOR-v1")
    print(f"{len(X)} items / {len(np.unique(groups))} groups\n")
    print("FROZEN fold table (drive x world -> fold):")
    print("      " + "  ".join(f" {w} " for w in LETTERS))
    for d in "1234567":
        print(f"   {d}  " + "  ".join(f"F{fold_of(d + w)}" for w in LETTERS))

    # ---- L3 STRUCTURAL CHECK, before any scoring
    ok = True
    print("\nL3 identifiability check:")
    for f in range(4):
        te = folds == f
        tr = folds != f
        w_te, w_tr = set(world[te]), set(world[tr])
        d_te, d_tr = set(drive[te]), set(drive[tr])
        good = w_te <= w_tr and d_te <= d_tr and len(w_te) >= 2
        ok &= good
        print(f"   fold {f}: test worlds={sorted(w_te)} drives={len(d_te)}  "
              f"all present in train: {w_te <= w_tr and d_te <= d_tr}  {'OK' if good else 'FAIL'}")
    if not ok:
        print("\nVOID: fold construction still unidentifiable")
        return 1

    res = {}
    for name, kw in (("char_3_5gram", dict(analyzer="char_wb", ngram_range=(3, 5))),
                     ("word_tfidf", dict(analyzer="word", ngram_range=(1, 1)))):
        hd, _ = cv(tfidf(X, kw), drive, folds)
        hw, _ = cv(tfidf(X, kw), world, folds)
        res[name] = {"drive": float(hd.mean()), "world": float(hw.mean()), "hits": hd}
        print(f"\n  {name:14s} drive={hd.mean():.4f}  world={hw.mean():.4f}")

    M = embed(X, "EleutherAI/pythia-160m", 6)
    hd, pdrive = cv(dense(M), drive, folds)
    hw, _ = cv(dense(M), world, folds)
    res["pythia160m_L6"] = {"drive": float(hd.mean()), "world": float(hw.mean()), "hits": hd}
    print(f"  pythia-160m L6 drive={hd.mean():.4f}  world={hw.mean():.4f}")

    # ---- C-PERM: permute labels AT GROUP LEVEL (siblings keep the same label)
    u = np.unique(groups)
    perm_lab = dict(zip(u, rng.permutation([g[0] for g in u])))
    y_perm = np.array([perm_lab[g] for g in groups])
    hp, _ = cv(dense(M), y_perm, folds)

    # ---- C-BODY: identical constant text for every row, nothing else reaches the extractor
    Mb = embed(["text"] * len(X), "EleutherAI/pythia-160m", 6)
    hb, _ = cv(dense(Mb), drive, folds)
    from collections import Counter
    majority = Counter(drive).most_common(1)[0][1] / len(drive)

    prim = res["pythia160m_L6"]
    bl = max(("char_3_5gram", "word_tfidf"), key=lambda k: res[k]["drive"])
    margin = prim["drive"] - res[bl]["drive"]
    lo, hi = group_boot(prim["hits"], res[bl]["hits"], groups, rng)
    obs = prim["drive"]
    p = float((sum((rng.random(len(drive)) < DRIVE_CHANCE).mean() >= obs
                   for _ in range(PERM)) + 1) / (PERM + 1))

    crit = {
        "L1_drive_above_chance": bool(obs > DRIVE_CHANCE and p < 0.01),
        "L2_drive_beats_lexical": bool(margin >= 0.10 and lo > 0),
        "L3_world_identifiable": bool(ok),
        "L4_world_above_chance": bool(prim["world"] > WORLD_CHANCE),
        "L5_perm_returns_to_chance": bool(0.05 <= hp.mean() <= 0.25),
        "L6_body_returns_to_chance": bool(hb.mean() <= majority + 1e-9),
    }
    verdict = ("VOID_PIPELINE_LEAKAGE"
               if not (crit["L5_perm_returns_to_chance"] and crit["L6_body_returns_to_chance"])
               else "LICENSED" if (crit["L1_drive_above_chance"] and crit["L2_drive_beats_lexical"])
               else "NOT_LICENSED_LEXICAL" if crit["L1_drive_above_chance"] else "NOT_LICENSED")

    print(f"\n  C-PERM group-level permuted drive = {hp.mean():.4f}  (expect ~{DRIVE_CHANCE:.4f})")
    print(f"  C-BODY constant-text drive        = {hb.mean():.4f}  (majority {majority:.4f})")
    print(f"\n  DESCRIPTIVE ordering: pythia {obs:.4f} vs best lexical {bl} {res[bl]['drive']:.4f}")
    print(f"  margin {margin:+.4f}  (significance reported separately: CI [{lo:+.4f}, {hi:+.4f}])")
    print(f"  permutation p vs chance = {p:.4f}")
    print(f"  world = {prim['world']:.4f} ** carries the disclosed 56% World-name leak **\n")
    for k, v in crit.items():
        print(f"  {k:30s} {'PASS' if v else 'FAIL'}")
    print("\nVERDICT:", verdict)

    R.write_json(HERE / "latin_square_results.json", {
        "design": "LATIN-SQUARE-SUCCESSOR-v1", "fold_table": fold_table(),
        "n_items": len(X), "n_groups": int(len(u)),
        "arms": {k: {"drive": v["drive"], "world": v["world"]} for k, v in res.items()},
        "controls": {"C_PERM_group_level_drive": float(hp.mean()),
                     "C_BODY_constant_text_drive": float(hb.mean()), "majority_rate": majority},
        "descriptive_ordering": {"pythia160m_L6": obs, "best_lexical": res[bl]["drive"],
                                 "best_lexical_source": bl, "margin": margin},
        "significance_reported_separately": {"group_bootstrap_ci": [lo, hi],
                                             "permutation_p_vs_chance": p},
        "reporting_rule": "Statistical uncertainty cannot convert 'did not exceed' into 'exceeded'.",
        "world_caveat": "47/84 (56%) of scenarios contain the literal World name; never report alone.",
        "not_runnable": "supervised 28-way CV — one sibling group per Foundation means the held-out "
                        "class is absent from training. Needs 28 x 4 independent plans x 3 = 336.",
        "criteria": crit, "verdict": verdict,
    })
    print("WROTE latin_square_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
