"""Materialize + locally gate Control C (NC28_TOPIC_FUNCTION_NESTED_V1) for Condition-3.

Control B (NC40 = 8 topic_40 x 5 frame_40 = 40 cells) is the PRIMARY same-size
opponent and already balances 18/cell/split on the full 1440-row fixture (see
fixture_eligibility_gate_condition3.py). Control C is the SECONDARY opponent:
NC28 = 7 topic_7 x 4 function_4 = 28 cells, reconstructed from the secondary
non-CAS fields control_semantic.topic_7 + control_semantic.function_4.

WHY NC28 IS NOT BALANCED ON THE FULL SET (honest structural caveat)
-------------------------------------------------------------------
NC28 is a fold of the NC40 assignment, and two folds are many-to-one:
  topic_40:  customer_support + public_safety   -> topic_7  human_services
  frame_40:  procedure        + tradeoff_decision-> function_4 choose_action
So on the full 720-rows-per-split fixture the 28 NC28 cells come out at
18 / 36 / 72 rows (a (human_services, choose_action) cell collects 2x2=4 source
NC40 cells). Also 720 is NOT divisible by 28, so a uniform NC28 over the full set
is impossible by construction.

MATERIALIZATION (the honest fix)
--------------------------------
We carve a BALANCED NC28 view by downsampling every cell to the minimum cell
count (18) -> 18 x 28 = 504 rows per split (1008 total). Selection within each
cell is a CAS-BLIND seeded shuffle (sorted by sample_id, shuffled with a fixed
seed, first 18 kept) -- the selector never reads element_label or any CAS field,
so it cannot manufacture CAS<->NC28 correlation. We then re-run the four
eligibility checks ON THE VIEW:

  1. RECONSTRUCTS FROM NON-CAS FIELDS ONLY  -- the 28 cells rebuild from
     control_semantic.topic_7 + control_semantic.function_4 alone.
  2. BALANCED  -- every cell = 18 per split, 7 topics and 4 functions uniform.
  3. ORTHOGONAL TO CAS  -- NMI(element, nc28_cell) inside a permutation-null
     band on the view.
  4. ORDINARY CONTENT PRESENT  -- topic_7 and function_4 are text-recoverable
     from the prompt (train-view -> test-view) above 0.80.

Outputs:
  control_c_nc28_balanced_view_20260531.json  -- selected sample_ids per split +
      the check block + verdict (so the GPU Control-C arm uses EXACTLY this set).
"""
import argparse, json, random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
_FIX = _HERE / f"mtc_condition3_topical_scenarios_{_DATE}.jsonl"

_TOPIC7 = ("human_services", "law_policy", "learning_assessment", "market_transaction",
           "medical_care", "operations_planning", "technical_system")
_FUNCTION4 = ("choose_action", "describe_state", "evaluate_risk", "explain_cause")

# Control C assignment is forbidden to read any CAS field (prereg Section 5).
_PROHIBITED = ("element_label", "element_domain", "element_domain_name",
               "element_noetic_tks", "element_noetic_name", "element_cas_domain",
               "element_cas_noetic", "element_register", "pair_kind",
               "contrast_partner_element", "counterfactual_pair_id")


def _nc28_cell(r):
    cs = r["control_semantic"]
    return f"{cs['topic_7']}|{cs['function_4']}"


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


def _balanced_view(rows, seed):
    """CAS-blind downsample: per split, per NC28 cell, keep `target` rows where
    target = min cell count for that split. Selection sorts by sample_id then
    seeded-shuffles -- never reads a CAS field."""
    keep = []
    per_split_target = {}
    for split in ("train", "test"):
        srows = [r for r in rows if r["split"] == split]
        by_cell = defaultdict(list)
        for r in srows:
            by_cell[_nc28_cell(r)].append(r)
        target = min(len(v) for v in by_cell.values())
        per_split_target[split] = target
        rng = random.Random(seed)
        for cell in sorted(by_cell):
            pool = sorted(by_cell[cell], key=lambda r: r["sample_id"])
            rng.shuffle(pool)
            keep.extend(pool[:target])
    return keep, per_split_target


def _text_recover(view, key):
    tr = [r for r in view if r["split"] == "train"]
    te = [r for r in view if r["split"] == "test"]
    classes = sorted({r["control_semantic"][key] for r in view})
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
    ap.add_argument("--seed", type=int, default=20260531)
    args = ap.parse_args(argv)
    rows = [json.loads(l) for l in open(args.fixture, encoding="utf-8")]
    print(f"fixture: {Path(args.fixture).name}")
    print(f"rows={len(rows)} splits={dict(sorted(Counter(r['split'] for r in rows).items()))}")

    # Full-set NC28 distribution (documents the structural imbalance) ----------
    for split in ("train", "test"):
        cc = Counter(_nc28_cell(r) for r in rows if r["split"] == split)
        print(f"[full] {split}: nc28 cells={len(cc)} counts(min/max)="
              f"{min(cc.values())}/{max(cc.values())} (non-uniform by fold; 720 not divisible by 28)")

    view, targets = _balanced_view(rows, args.seed)
    print(f"\n[view] balanced NC28 view: {len(view)} rows "
          f"(train target={targets['train']}/cell, test target={targets['test']}/cell)")

    checks = {}

    # 1. Reconstructable from non-CAS fields only -----------------------------
    cells = {_nc28_cell(r) for r in view}
    expected = {f"{t}|{f}" for t in _TOPIC7 for f in _FUNCTION4}
    rebuilds = cells == expected
    checks["nc28_reconstructs_from_non_cas_fields_only"] = rebuilds
    print(f"[1] NC28 reconstructs from control_semantic.topic_7+function_4 only: "
          f"{len(cells)}/28 cells, exact set match={rebuilds}")

    # 2. Balanced (on the view) -----------------------------------------------
    bal_ok = True
    for split in ("train", "test"):
        cc = Counter(_nc28_cell(r) for r in view if r["split"] == split)
        tc = Counter(r["control_semantic"]["topic_7"] for r in view if r["split"] == split)
        fc = Counter(r["control_semantic"]["function_4"] for r in view if r["split"] == split)
        cell_uniform = len(set(cc.values())) == 1 and len(cc) == 28
        topic_uniform = len(set(tc.values())) == 1 and len(tc) == 7
        func_uniform = len(set(fc.values())) == 1 and len(fc) == 4
        bal_ok = bal_ok and cell_uniform and topic_uniform and func_uniform
        print(f"[2] {split}: nc28 cell uniform={cell_uniform} (per-cell={next(iter(cc.values()))}), "
              f"topic7 uniform={topic_uniform}, function4 uniform={func_uniform}")
    checks["nc28_balanced_per_split_on_view"] = bal_ok

    # 3. Orthogonal to CAS on the view (permutation-null band) ----------------
    cas = [r["element_label"] for r in view]
    nc = [_nc28_cell(r) for r in view]
    real = _nmi(cas, nc)
    null_mean, null_p975 = _nmi_null_band(cas, nc)
    ortho = real <= null_p975
    checks["nc28_orthogonal_within_null_band_on_view"] = ortho
    print(f"[3] NMI(CAS_element, NC28_cell)={real:.4f}  null_mean={null_mean:.4f}  "
          f"null_p97.5={null_p975:.4f}  within_band={ortho}")

    # 4. Ordinary content genuinely present in text (on the view) -------------
    t_acc, t_n = _text_recover(view, "topic_7")
    f_acc, f_n = _text_recover(view, "function_4")
    content_present = t_acc >= 0.80 and f_acc >= 0.80
    checks["ordinary_topic7_function4_content_present_in_text"] = content_present
    print(f"[4] text recovery topic_7={t_acc:.4f} ({t_n}-way, chance {1/t_n:.3f}), "
          f"function_4={f_acc:.4f} ({f_n}-way, chance {1/f_n:.3f}); present={content_present}")

    # Prohibited-field guard (documentary) ------------------------------------
    checks["assignment_uses_non_cas_fields_only"] = all(
        r["control_semantic"].get("assignment", "").startswith("cas_blind") for r in view)
    print(f"[guard] every view row's assignment provenance = cas_blind_*: "
          f"{checks['assignment_uses_non_cas_fields_only']} "
          f"(prohibited CAS fields never read: {', '.join(_PROHIBITED[:4])}, ...)")

    verdict = "ELIGIBLE_SECONDARY" if all(checks.values()) else "BLOCKED_CONTROL_C_NOT_ELIGIBLE"
    print(f"\nControl C (NC28) materialization gate: {verdict}")

    view_ids = {split: sorted(r["sample_id"] for r in view if r["split"] == split)
                for split in ("train", "test")}
    out = _HERE / f"control_c_nc28_balanced_view_{_DATE}.json"
    out.write_text(json.dumps({
        "fixture": Path(args.fixture).name,
        "control_c_class": "NC28_TOPIC_FUNCTION_NESTED_V1",
        "secondary_fields": ["control_semantic.topic_7", "control_semantic.function_4"],
        "selection": "cas_blind_seeded_shuffle_downsample_to_min_cell_per_split",
        "seed": args.seed,
        "per_split_target_per_cell": targets,
        "view_rows_per_split": {s: len(v) for s, v in view_ids.items()},
        "structural_caveat": ("NC28 folds two NC40 cells each (customer_support+public_safety"
                              "->human_services; procedure+tradeoff_decision->choose_action) and "
                              "720 is not divisible by 28, so full-set uniform NC28 is impossible; "
                              "this balanced 18/cell view is the fair secondary opponent."),
        "checks": checks,
        "nmi_real": round(real, 4),
        "nmi_null_p975": round(null_p975, 4),
        "topic7_text_acc": round(t_acc, 4),
        "function4_text_acc": round(f_acc, 4),
        "verdict": verdict,
        "view_sample_ids": view_ids,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out.name}")
    return 0 if verdict == "ELIGIBLE_SECONDARY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
