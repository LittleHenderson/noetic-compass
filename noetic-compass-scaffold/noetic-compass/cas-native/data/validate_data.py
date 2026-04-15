"""Data quality validation for generated training data."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def validate_dataset(path: str | Path) -> dict:
    """Run quality checks on a generated JSONL dataset."""
    path = Path(path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    total = len(entries)
    if total == 0:
        return {"error": "Empty dataset"}

    # 1. Expression validity
    valid_count = sum(1 for e in entries if e.get("compilation", {}).get("valid", False))

    # 2. Score consistency — operator in expression → score > 0
    score_consistent = 0
    for e in entries:
        scores = e.get("scores", {})
        op_scores = scores.get("operator_scores", [])
        expr = e.get("cas_expression", "")
        consistent = True
        for i, s in enumerate(op_scores):
            if s > 0 and f"CO-{i}" not in expr:
                pass  # score > 0 but not in expression — not necessarily wrong
            if f"CO-{i}^" in expr and s == 0:
                consistent = False
        if consistent:
            score_consistent += 1

    # 3. Distribution balance
    op_dist = Counter()
    dom_dist = Counter()
    drv_dist = Counter()
    complexity_dist = Counter()

    for e in entries:
        scores = e.get("scores", {})
        for i, s in enumerate(scores.get("operator_scores", [])):
            if s > 0:
                op_dist[i] += 1
        for i, s in enumerate(scores.get("domain_scores", [])):
            if s > 0:
                dom_dist[["P", "C", "E", "O"][i]] += 1
        for i, s in enumerate(scores.get("drive_scores", [])):
            if s > 0:
                drv_dist[i + 1] += 1
        complexity_dist[e.get("complexity", "unknown")] += 1

    # 4. Duplicates
    expressions = [e.get("cas_expression", "") for e in entries]
    unique_count = len(set(expressions))
    duplicate_count = total - unique_count

    # 5. English length stats
    lengths = [len(e.get("english_text", "").split()) for e in entries]
    avg_length = sum(lengths) / max(len(lengths), 1)

    # Warnings
    warnings = []
    expected_per_op = total / 10
    for op in range(10):
        count = op_dist.get(op, 0)
        if count < expected_per_op * 0.3:
            warnings.append(f"CO-{op} underrepresented: {count} (expected ~{expected_per_op:.0f})")

    return {
        "total": total,
        "valid_compilations": valid_count,
        "valid_rate": round(valid_count / total, 4),
        "score_consistent": score_consistent,
        "score_consistency_rate": round(score_consistent / total, 4),
        "unique_expressions": unique_count,
        "duplicate_count": duplicate_count,
        "duplicate_rate": round(duplicate_count / total, 4),
        "avg_english_length": round(avg_length, 1),
        "operator_distribution": dict(sorted(op_dist.items())),
        "domain_distribution": dict(sorted(dom_dist.items())),
        "drive_distribution": dict(sorted(drv_dist.items())),
        "complexity_distribution": dict(complexity_dist),
        "warnings": warnings,
    }
