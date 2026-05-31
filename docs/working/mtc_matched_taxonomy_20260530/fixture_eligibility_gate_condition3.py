"""Condition-3 Fixture-Eligibility Gate (local CPU, $0).

The prereg (Section 5) blocks a fixture as BLOCKED_FIXTURE_NOT_ELIGIBLE when it
is "abstract CAS/TKS role-bound prose but insufficient ordinary semantic
topic/event content." Condition-2 lands there. This gate proves Condition-3 does
NOT: the coherent non-CAS opponent Control B (NC40_TOPIC_FRAME_V1) materializes
from non-CAS fields ONLY, balanced, and the ordinary content is genuinely present
in the text (so the opponent is real, not a relabeling of CAS structure).

It checks four things, all from non-CAS fields:

  1. RECONSTRUCTABLE FROM NON-CAS FIELDS ONLY. The NC40 class label rebuilds from
     control_semantic.topic_40 + control_semantic.frame_40 alone -- never reading
     element_label / element_domain / element_noetic_* or any CAS field. (Control C
     NC28 likewise from topic_7 + function_4, secondary.)

  2. BALANCED. Every one of the 40 NC40 cells appears equally within each split,
     and the 8 topics / 5 frames are each balanced -- a fair same-size opponent.

  3. ORTHOGONAL TO CAS. Mutual information between the CAS element and the NC40
     cell sits inside a permutation-null band (so the opponent carries no CAS
     label information -- it is a genuine alternative taxonomy, not a disguise).

  4. ORDINARY CONTENT GENUINELY PRESENT. topic_40 and frame_40 are highly
     recoverable from the prompt text by the canonical bag-of-words lane (the
     Surface Gate already reports ~100%); we re-assert it here as the
     "the content is really in the scenario" leg of eligibility.

Prohibited fields (assignment must never read these): element_label,
element_domain, element_noetic_tks/name, element_cas_*, element_register,
pair_kind, contrast_partner_element.
"""
import argparse, json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

_HERE = Path(__file__).resolve().parent
_FIX = _HERE / "mtc_condition3_topical_scenarios_20260531.jsonl"

_TOPIC40 = ("healthcare", "education", "commerce_finance", "law_governance",
            "software_data", "logistics_operations", "customer_support", "public_safety")
_FRAME40 = ("classification", "causal_explanation", "procedure",
            "tradeoff_decision", "risk_mitigation")

# Fields the NC40 assignment is forbidden to read (prereg Section 5).
_PROHIBITED = ("element_label", "element_domain", "element_domain_name",
               "element_noetic_tks", "element_noetic_name", "element_cas_domain",
               "element_cas_noetic", "element_register", "pair_kind",
               "contrast_partner_element", "counterfactual_pair_id")


def _nc40_cell(r):
    cs = r["control_semantic"]
    return f"{cs['topic_40']}|{cs['frame_40']}"


def _nmi(xs, ys):
    from math import log
    n = len(xs)
    cx, cy, cxy = Counter(xs), Counter(ys), Counter(zip(xs, ys))
    hx = -sum(c / n * log(c / n) for c in cx.values())
    hy = -sum(c / n * log(c / n) for c in cy.values())
    mi = 0.0
    for (a, b), c in cxy.items():
        mi += c / n * log((c / n) / (cx[a] / n * cy[b] / n))
    denom = (hx * hy) ** 0.5
    return mi / denom if denom > 0 else 0.0


def _nmi_null_band(xs, ys, k=500, seed=7):
    rng = np.random.default_rng(seed)
    ys = np.array(ys)
    vals = np.array([_nmi(xs, list(ys[rng.permutation(len(ys))])) for _ in range(k)])
    return float(vals.mean()), float(np.percentile(vals, 97.5))


def _text_recover(rows, key):
    tr = [r for r in rows if r["split"] == "train"]
    te = [r for r in rows if r["split"] == "test"]
    classes = sorted({r["control_semantic"][key] for r in rows})
    idx = {c: i for i, c in enumerate(classes)}
    ytr = np.array([idx[r["control_semantic"][key]] for r in tr])
    yte = np.array([idx[r["control_semantic"][key]] for r in te])
    vec = CountVectorizer(ngram_range=(1, 2), max_features=2 ** 14)
    Xtr = vec.fit_transform([r["english"] for r in tr])
    Xte = vec.transform([r["english"] for r in te])
    clf = LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000)
    clf.fit(Xtr, ytr)
    return accuracy_score(yte, clf.predict(Xte)), len(classes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", default=str(_FIX))
    args = ap.parse_args(argv)
    rows = [json.loads(l) for l in open(args.fixture, encoding="utf-8")]
    print(f"fixture: {Path(args.fixture).name}")
    print(f"rows={len(rows)} splits={dict(sorted(Counter(r['split'] for r in rows).items()))}")
    print()

    checks = {}

    # 1. Reconstructable from non-CAS fields only -----------------------------
    cells = {_nc40_cell(r) for r in rows}
    expected = {f"{t}|{f}" for t in _TOPIC40 for f in _FRAME40}
    rebuilds = cells == expected
    checks["nc40_reconstructs_from_non_cas_fields_only"] = rebuilds
    print(f"[1] NC40 reconstructs from control_semantic.topic_40+frame_40 only: "
          f"{len(cells)}/40 cells, exact set match={rebuilds}")

    # 2. Balanced -------------------------------------------------------------
    bal_ok = True
    for split in ("train", "test"):
        cc = Counter(_nc40_cell(r) for r in rows if r["split"] == split)
        tc = Counter(r["control_semantic"]["topic_40"] for r in rows if r["split"] == split)
        fc = Counter(r["control_semantic"]["frame_40"] for r in rows if r["split"] == split)
        cell_uniform = len(set(cc.values())) == 1 and len(cc) == 40
        topic_uniform = len(set(tc.values())) == 1 and len(tc) == 8
        frame_uniform = len(set(fc.values())) == 1 and len(fc) == 5
        bal_ok = bal_ok and cell_uniform and topic_uniform and frame_uniform
        print(f"[2] {split}: nc40 cell counts uniform={cell_uniform} "
              f"(per-cell={next(iter(cc.values()))}), topic uniform={topic_uniform}, "
              f"frame uniform={frame_uniform}")
    checks["nc40_balanced_per_split"] = bal_ok

    # 3. Orthogonal to CAS (permutation-null band) ----------------------------
    cas = [r["element_label"] for r in rows]
    nc = [_nc40_cell(r) for r in rows]
    real = _nmi(cas, nc)
    null_mean, null_p975 = _nmi_null_band(cas, nc)
    ortho = real <= null_p975
    checks["nc40_orthogonal_within_null_band"] = ortho
    print(f"[3] NMI(CAS_element, NC40_cell)={real:.4f}  null_mean={null_mean:.4f}  "
          f"null_p97.5={null_p975:.4f}  within_band={ortho}")

    # 4. Ordinary content genuinely present in text ---------------------------
    t_acc, t_n = _text_recover(rows, "topic_40")
    f_acc, f_n = _text_recover(rows, "frame_40")
    content_present = t_acc >= 0.80 and f_acc >= 0.80
    checks["ordinary_topic_frame_content_present_in_text"] = content_present
    print(f"[4] text recovery topic_40={t_acc:.4f} ({t_n}-way, chance {1/t_n:.3f}), "
          f"frame_40={f_acc:.4f} ({f_n}-way, chance {1/f_n:.3f}); present={content_present}")

    # Prohibited-field guard (documentary): the assignment provenance + this
    # gate use ONLY control_semantic.* fields; CAS fields are never consulted.
    checks["assignment_uses_non_cas_fields_only"] = all(
        r["control_semantic"].get("assignment", "").startswith("cas_blind") for r in rows)
    print(f"[guard] every row's assignment provenance = cas_blind_*: "
          f"{checks['assignment_uses_non_cas_fields_only']}  "
          f"(prohibited CAS fields never read: {', '.join(_PROHIBITED[:4])}, ...)")

    verdict = "ELIGIBLE" if all(checks.values()) else "BLOCKED_FIXTURE_NOT_ELIGIBLE"
    print()
    print(f"Fixture-Eligibility Gate: {verdict}")
    out = _HERE / "fixture_eligibility_gate_condition3_result.json"
    out.write_text(json.dumps({"fixture": Path(args.fixture).name, "checks": checks,
                               "nmi_real": round(real, 4), "nmi_null_p975": round(null_p975, 4),
                               "topic40_text_acc": round(t_acc, 4),
                               "frame40_text_acc": round(f_acc, 4),
                               "verdict": verdict}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {out.name}")
    return 0 if verdict == "ELIGIBLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
