"""tier_c_ronly_probe.py -- the R-only shortcut adversary (G-C0-7).

Owner law: on EVERY primary task family, an adversary receiving ONLY the
ordered clause class sequence + R features + candidate position -- NO entity
identities, NO candidate types, NO clause text -- must score
<= candidate-chance + 0.05, else the relational table has become another
answer key (RONLY_SHORTCUT_DETECTED).

Registered feature set per (record, candidate):
  * class sequence one-hot (6 clauses x 4 classes = 24 dims)  [the labels]
  * candidate position j / (n_candidates - 1)                  [1 dim]
R-derived pair features are deterministic functions of the class sequence
(phi is a frozen lookup), so the class sequence is the maximal R-only
information; adding phi columns adds no information the MLP cannot derive.
Candidate TYPE is deliberately excluded: the answer's entity type is a
task-structural given already measured by the B-MEMBER/B-KEY references,
not a relational-table leak (registered rationale, spec section 5).

Adversary: the same MLP family as the frozen B-KEY gate
(sklearn MLPClassifier (64, 32), max_iter 300, random_state 0), per-candidate
binary scoring, argmax per record. Train on train.jsonl primary families,
evaluate per family on val.jsonl. Raw accuracies persisted.

Development-only, non-claim-bearing. CPU.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPClassifier

HERE = Path(__file__).resolve().parent
PRIMARY = ("QB_REL", "QB_COMP", "QB_INT")
CLASSES = ("^2", "^3", "^6", "^8")
MARGIN = 0.05


def _load(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["question_type"] in PRIMARY:
                out.append(rec)
    return out


def _feats(rec):
    seq = np.zeros(24, dtype=np.float32)
    for k, c in enumerate(rec["idea_labels"][:6]):
        seq[k * 4 + CLASSES.index(c)] = 1.0
    n = len(rec["candidates"])
    rows, ys = [], []
    for j, cand in enumerate(rec["candidates"]):
        pos = j / (n - 1) if n > 1 else 0.0
        rows.append(np.concatenate([seq, [pos]]))
        ys.append(1 if cand == rec["answer"] else 0)
    return rows, ys


def run_probe(train_path, val_path):
    train = _load(train_path)
    val = _load(val_path)
    xt, yt = [], []
    for rec in train:
        r, y = _feats(rec)
        xt.extend(r)
        yt.extend(y)
    clf = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300,
                        random_state=0)
    clf.fit(np.array(xt), np.array(yt))
    per_fam = {}
    for fam in PRIMARY:
        recs = [r for r in val if r["question_type"] == fam]
        hits = 0
        for rec in recs:
            rows, _ = _feats(rec)
            p = clf.predict_proba(np.array(rows))[:, 1]
            hits += int(rec["candidates"][int(np.argmax(p))]
                        == rec["answer"])
        chance = sum(1.0 / len(r["candidates"]) for r in recs) / len(recs)
        acc = hits / len(recs)
        per_fam[fam] = {"n": len(recs), "accuracy": acc,
                        "candidate_chance": chance,
                        "bound": chance + MARGIN,
                        "within_bound": acc <= chance + MARGIN}
    return {"probe_id": "TIERC_RONLY_PROBE_v1", "non_claim_bearing": True,
            "feature_set": "class-seq one-hot (24) + candidate position (1); "
                           "no entities, no candidate types, no text",
            "adversary": "MLPClassifier (64,32) max_iter=300 seed=0 "
                         "(the frozen B-KEY family)",
            "margin": MARGIN, "per_family": per_fam,
            "pass": all(v["within_bound"] for v in per_fam.values()),
            "fail_status": "RONLY_SHORTCUT_DETECTED"}
