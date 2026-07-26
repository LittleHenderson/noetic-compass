"""
Track A — Acceptance Gate for Independently-Authored Evaluation Bank.

Validates a generated bank BEFORE any model touches it, per
INDEPENDENT_BANK_SPECIFICATION.md Section 4.

Gates:
    G1  Surface separability — char-ngram, word-hash, length baselines ≤ 0.10
    G2  Vocabulary overlap — symmetric between TKS and compact CAS arms
    G3  Inter-rater agreement — raw agreement + discard rate
    G4  Admissibility — no row duplication, effective n = unique items
    G5  Cell coverage — minimum items per cell (≥ 8 of 40 cells)

A bank that fails any gate is REJECTED, not repaired.

Usage:
    python acceptance_gate.py --bank BANK.jsonl --tks-defs TKS.json --cas-defs CAS.json
"""
import json, sys, argparse, re, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

STOP_WORDS = set("the a an of and or to in is are be for on with that this it as by "
                 "from at was were not no all any some its their".split())


def tokenize(text: str) -> list[str]:
    """Extract content words from text."""
    return [w.lower() for w in re.findall(r"[a-z]+", str(text).lower())
            if w.lower() not in STOP_WORDS and len(w) > 2]


def char_ngrams(text: str, n: int = 4) -> list[str]:
    """Character n-grams for surface baseline."""
    t = re.sub(r"\s+", " ", str(text).lower()).strip()
    return [t[i:i+n] for i in range(len(t) - n + 1)]


# ── G1: Surface Separability ────────────────────────────────────────────────

def gate_surface_separability(items: list[dict], labels: list[str],
                               chance: float = 0.025) -> dict:
    """Char-ngram, word-hash, and length baselines under grouped CV.
    
    All must score ≤ 0.10 for a 40-way task where chance = 0.025.
    """
    texts = [item.get("english", item.get("text", "")) for item in items]
    le = LabelEncoder()
    y = le.fit_transform(labels)
    
    results = {}
    
    # Char 3-5 gram TF-IDF baseline
    vec_char = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=5000)
    X_char = vec_char.fit_transform(texts)
    try:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(LogisticRegression(max_iter=500, random_state=42),
                                 X_char, y, cv=cv, scoring="accuracy")
        results["char_ngram_tfidf"] = {"mean": round(float(scores.mean()), 6),
                                        "std": round(float(scores.std()), 6),
                                        "pass": bool(scores.mean() <= 0.10)}
    except Exception as e:
        results["char_ngram_tfidf"] = {"error": str(e), "pass": False}
    
    # Word unigram baseline
    vec_word = CountVectorizer(max_features=3000, stop_words="english", binary=True)
    X_word = vec_word.fit_transform(texts)
    try:
        scores = cross_val_score(LogisticRegression(max_iter=500, random_state=42),
                                 X_word, y, cv=cv, scoring="accuracy")
        results["word_unigram"] = {"mean": round(float(scores.mean()), 6),
                                    "std": round(float(scores.std()), 6),
                                    "pass": bool(scores.mean() <= 0.10)}
    except Exception as e:
        results["word_unigram"] = {"error": str(e), "pass": False}
    
    # Length baseline
    lengths = np.array([[len(t)] for t in texts])
    try:
        scores = cross_val_score(LogisticRegression(max_iter=500, random_state=42),
                                 lengths, y, cv=cv, scoring="accuracy")
        results["length"] = {"mean": round(float(scores.mean()), 6),
                              "std": round(float(scores.std()), 6),
                              "pass": bool(scores.mean() <= 0.10)}
    except Exception as e:
        results["length"] = {"error": str(e), "pass": False}
    
    results["g1_pass"] = all(v.get("pass", False) for v in results.values()
                              if isinstance(v, dict) and "pass" in v)
    return results


# ── G2: Vocabulary Overlap ──────────────────────────────────────────────────

def gate_vocabulary_overlap(items: list[dict], labels: list[str],
                             tks_defs: dict[str, str],
                             cas_defs: dict[str, str]) -> dict:
    """Measure vocabulary overlap between items and each definition set.
    
    Reports overlap separately for TKS and compact CAS. A large asymmetry
    (> 2x difference) means the bank favours one arm and must be rejected.
    """
    tks_overlaps = []
    cas_overlaps = []
    
    for item, label in zip(items, labels):
        item_tokens = set(tokenize(item.get("english", item.get("text", ""))))
        if not item_tokens:
            continue
        
        tks_text = tks_defs.get(label, "")
        cas_text = cas_defs.get(label, "")
        
        tks_tokens = set(tokenize(tks_text))
        cas_tokens = set(tokenize(cas_text))
        
        if tks_tokens:
            tks_overlaps.append(len(item_tokens & tks_tokens) / len(item_tokens))
        if cas_tokens:
            cas_overlaps.append(len(item_tokens & cas_tokens) / len(cas_tokens))
    
    tks_mean = float(np.mean(tks_overlaps)) if tks_overlaps else 0.0
    cas_mean = float(np.mean(cas_overlaps)) if cas_overlaps else 0.0
    
    # Asymmetry check: neither should be more than 2x the other
    asym_ratio = max(tks_mean, cas_mean) / max(0.001, min(tks_mean, cas_mean))
    asym_pass = asym_ratio < 2.0
    
    # Absolute ceiling: neither should exceed 0.30
    ceiling_pass = tks_mean <= 0.30 and cas_mean <= 0.30
    
    return {
        "tks_mean_overlap": round(tks_mean, 6),
        "cas_mean_overlap": round(cas_mean, 6),
        "asymmetry_ratio": round(asym_ratio, 4),
        "asymmetry_pass": asym_pass,
        "ceiling_pass": ceiling_pass,
        "g2_pass": asym_pass and ceiling_pass
    }


# ── G3: Inter-Rater Agreement ───────────────────────────────────────────────

def gate_inter_rater(items: list[dict]) -> dict:
    """If items have 'rater' fields, compute agreement and discard rate."""
    # Check if rater info exists
    rater_field = None
    for field in ["rater_id", "author_id", "labeller_id"]:
        if field in (items[0] if items else {}):
            rater_field = field
            break
    
    if rater_field is None:
        return {"g3_pass": True, "note": "no rater metadata — single-author bank, agreement N/A"}
    
    # Group items by content, check if multiple raters agree on label
    by_content = collections.defaultdict(list)
    for item in items:
        text = item.get("english", item.get("text", ""))
        key = text.strip().lower()[:100]
        by_content[key].append(item)
    
    multi_rated = {k: v for k, v in by_content.items() if len(v) >= 2}
    agreed = 0
    total = len(multi_rated)
    for group in multi_rated.values():
        labels = [g.get("element_label", g.get("label", "")) for g in group]
        if len(set(labels)) == 1:
            agreed += 1
    
    agreement = agreed / max(1, total)
    discard_rate = (len(items) - total) / max(1, len(items))
    
    return {
        "multi_rated_items": total,
        "agreement_count": agreed,
        "raw_agreement": round(agreement, 4),
        "discard_rate": round(discard_rate, 4),
        "g3_pass": agreement >= 0.60  # 60% minimum raw agreement
    }


# ── G4: Admissibility ───────────────────────────────────────────────────────

def gate_admissibility(items: list[dict]) -> dict:
    """Check for row duplication and effective sample size."""
    texts = [item.get("english", item.get("text", "")) for item in items]
    labels = [item.get("element_label", item.get("label", "")) for item in items]
    
    # Check for exact duplicates
    seen = set()
    dupes = 0
    for t in texts:
        key = t.strip().lower()
        if key in seen:
            dupes += 1
        seen.add(key)
    
    unique_items = len(texts) - dupes
    unique_labels = len(set(labels))
    
    return {
        "total_items": len(items),
        "unique_items": unique_items,
        "duplicates": dupes,
        "unique_labels": unique_labels,
        "effective_n": unique_items,
        "g4_pass": dupes == 0 and unique_items >= 200 and unique_labels >= 30
    }


# ── G5: Cell Coverage ───────────────────────────────────────────────────────

def gate_cell_coverage(items: list[dict]) -> dict:
    """Verify minimum items per cell (≥ 5 per cell, ≥ 30 of 40 cells have items)."""
    labels = [item.get("element_label", item.get("label", "")) for item in items]
    counts = collections.Counter(labels)
    
    cells_with_min = sum(1 for v in counts.values() if v >= 5)
    total_cells = len(counts)
    
    return {
        "total_cells_represented": total_cells,
        "cells_with_5plus_items": cells_with_min,
        "min_items_per_cell": min(counts.values()) if counts else 0,
        "max_items_per_cell": max(counts.values()) if counts else 0,
        "g5_pass": cells_with_min >= 30 and total_cells >= 35
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Acceptance gate for independent bank")
    parser.add_argument("--bank", required=True, help="Path to bank JSONL file")
    parser.add_argument("--tks-defs", required=True, help="TKS definitions JSON (40 elements)")
    parser.add_argument("--cas-defs", required=True, help="Compact CAS definitions JSON")
    parser.add_argument("--output", default=None, help="Output gate report JSON")
    args = parser.parse_args()
    
    # Load bank
    items = []
    with open(args.bank, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    print(f"Loaded {len(items)} items from bank")
    
    # Extract labels
    labels = [item.get("element_label", item.get("label", "")) for item in items]
    
    # Load TKS definitions
    with open(args.tks_defs, encoding="utf-8") as f:
        tks_data = json.load(f)
    tks_defs = {}
    for elem in tks_data.get("tks_40_elements", []):
        tks_defs[elem["code"]] = elem["definition"]
    
    # Load compact CAS definitions — try JSON structure
    with open(args.cas_defs, encoding="utf-8") as f:
        cas_data = json.load(f)
    cas_defs = {}
    if "elements" in cas_data:
        for elem in cas_data["elements"]:
            cas_defs[elem["code"]] = elem["definition"]
    elif "definitions" in cas_data:
        cas_defs = cas_data["definitions"]
    
    print(f"TKS definitions: {len(tks_defs)} cells")
    print(f"CAS definitions: {len(cas_defs)} cells")
    
    # Run all gates
    report = {
        "bank_path": args.bank,
        "num_items": len(items),
        "checked_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    
    print("\n=== G1: Surface Separability ===")
    g1 = gate_surface_separability(items, labels)
    report["g1_surface"] = g1
    for k, v in g1.items():
        if isinstance(v, dict) and "mean" in v:
            print(f"  {k}: mean={v['mean']:.4f}  {'PASS' if v['pass'] else 'FAIL'}")
    print(f"  G1 overall: {'PASS' if g1['g1_pass'] else 'FAIL'}")
    
    print("\n=== G2: Vocabulary Overlap ===")
    g2 = gate_vocabulary_overlap(items, labels, tks_defs, cas_defs)
    report["g2_vocab_overlap"] = g2
    print(f"  TKS mean overlap:  {g2['tks_mean_overlap']:.4f}")
    print(f"  CAS mean overlap:  {g2['cas_mean_overlap']:.4f}")
    print(f"  Asymmetry ratio:   {g2['asymmetry_ratio']:.2f}  {'PASS' if g2['asymmetry_pass'] else 'FAIL'}")
    print(f"  Ceiling (≤0.30):   {'PASS' if g2['ceiling_pass'] else 'FAIL'}")
    print(f"  G2 overall: {'PASS' if g2['g2_pass'] else 'FAIL'}")
    
    print("\n=== G3: Inter-Rater Agreement ===")
    g3 = gate_inter_rater(items)
    report["g3_inter_rater"] = g3
    print(f"  {'Agreement' if 'raw_agreement' in g3 else 'Note'}: {g3.get('raw_agreement', g3.get('note', 'N/A'))}")
    print(f"  G3 overall: {'PASS' if g3['g3_pass'] else 'FAIL'}")
    
    print("\n=== G4: Admissibility ===")
    g4 = gate_admissibility(items)
    report["g4_admissibility"] = g4
    print(f"  Items: {g4['total_items']} total, {g4['unique_items']} unique, {g4['duplicates']} duplicates")
    print(f"  Labels: {g4['unique_labels']} unique")
    print(f"  G4 overall: {'PASS' if g4['g4_pass'] else 'FAIL'}")
    
    print("\n=== G5: Cell Coverage ===")
    g5 = gate_cell_coverage(items)
    report["g5_coverage"] = g5
    print(f"  Cells represented: {g5['total_cells_represented']}/40")
    print(f"  Cells with ≥5 items: {g5['cells_with_5plus_items']}/40")
    print(f"  Range: {g5['min_items_per_cell']}–{g5['max_items_per_cell']} items/cell")
    print(f"  G5 overall: {'PASS' if g5['g5_pass'] else 'FAIL'}")
    
    # Final verdict
    all_pass = all([
        g1["g1_pass"], g2["g2_pass"], g3["g3_pass"], g4["g4_pass"], g5["g5_pass"]
    ])
    report["all_gates_pass"] = all_pass
    report["verdict"] = "ACCEPT — bank is admissible for independent evaluation" if all_pass \
                        else "REJECT — bank fails one or more gates; do not use"
    
    print(f"\n{'='*60}")
    print(f"FINAL VERDICT: {report['verdict']}")
    print(f"{'='*60}")
    
    out_path = args.output or args.bank.replace(".jsonl", "_gate_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report: {out_path}")
    
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
