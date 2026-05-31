"""$0 local CPU text baseline on the REAL-TKS-definition Stage-9 40E fixture.

Purpose: answer "did the high recoverability lineage use the real TKS
definitions?" by measuring how much a bag-of-words classifier can recover the
40-element label from the prompt TEXT alone on the v1 fixture whose prompts
embed faithful real-TKS element glosses (the 95.625%-hidden lineage).

Contrast target: the dual_labeled marker-balanced null gave text ~1.5% because
it stripped the real meaning. If this real-definition fixture gives a much
higher text baseline, it confirms the fixture carries real TKS meaning (and
the nulls over-stripped). Hidden readout still needs GPU; this is the cheap
leakage cut only.

Text lane matches run_matched_taxonomy_control.py:
  CountVectorizer(1-2gram, max_features=2**14) + LogisticRegression(C=1.0,
  class_weight='balanced', lbfgs).
"""
import json
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

FIX = "docs/working/lsa_artifacts_20260530/stage9_elements_pilot_20260517.v1.jsonl"


def load():
    rows = [json.loads(l) for l in open(FIX, encoding="utf-8-sig")]
    return rows


def run(rows, text_key, label_key="element_label"):
    tr = [r for r in rows if r["split"] == "train"]
    te = [r for r in rows if r["split"] == "test"]
    classes = sorted({r[label_key] for r in rows})
    idx = {c: i for i, c in enumerate(classes)}
    ytr = np.array([idx[r[label_key]] for r in tr])
    yte = np.array([idx[r[label_key]] for r in te])
    vec = CountVectorizer(ngram_range=(1, 2), max_features=2 ** 14)
    Xtr = vec.fit_transform([r[text_key] for r in tr])
    Xte = vec.transform([r[text_key] for r in te])
    clf = LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    acc = accuracy_score(yte, pred)
    f1 = f1_score(yte, pred, average="macro")
    return acc, f1, len(classes), len(tr), len(te)


def main():
    rows = load()
    print(f"rows={len(rows)} splits={dict(Counter(r['split'] for r in rows))}")
    chance = 1.0 / len({r['element_label'] for r in rows})
    for key in ("english", "element_gloss"):
        acc, f1, nc, ntr, nte = run(rows, key)
        print(f"[text:{key:13s}] acc={acc:.4f} macroF1={f1:.4f} "
              f"({nc} cls, chance={chance:.4f}, train={ntr}, test={nte})")
    print("\nReference: dual_labeled marker-balanced null text acc = 0.0150 "
          "(1.5%) on its own 40E run. v1 lineage hidden readout = 0.95625.")


if __name__ == "__main__":
    main()
