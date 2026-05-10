"""Audit existing meta-logic training targets with strict validator.

Per user directive 2026-05-10 (post fractal audit commit 153dd49):
queue meta-logic audit BEFORE regeneration so we know whether the
v1d retrain bundle covers all weak categories or just fractal.

Stage-1 one-off audit. Reuses the parser from
``cas_native.inference.meta_logic_repair.parse_meta_logic`` since
that module already handles PartitionOf / CoverOf / Product +
NoeticCluster{…} parsing exactly the way we want.

Per-row strict checks:
  1. Relation type word in target matches source
     (PartitionOf -> partition / partitions / partitioning;
      CoverOf -> cover / covers / covered;
      Product -> product / products).
  2. Cluster cardinality matches: the rendered text claims the
     same number of groups/clusters/sets as the source has.
  3. Cluster membership: every Noetic in every source cluster has
     at least one indicator anywhere in the target text. (Strict
     version of the existing ClusterMemberDrift flag-only check.)

The audit is read-only — does not delete or rewrite any corpus
rows. Outputs JSONL + markdown matching the audit_fractal_targets
and audit_recipe_targets format.
"""
from __future__ import annotations

import json
import re
import sys
import types
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(SCAFFOLD_ROOT))

from cas_native.inference.meta_logic_repair import (  # noqa: E402
    parse_meta_logic,
)


CORPUS_FILES = [
    "cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl",
    "cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl",
    "cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl",
]
OUT_DIR = REPO_ROOT / "cas-synthetic/data/path_d"


# Relation indicators (mirrors meta_logic_repair patterns).
_RELATION_PATTERNS: dict[str, re.Pattern] = {
    "PartitionOf": re.compile(r"\bpartition\w*\b", re.IGNORECASE),
    "CoverOf":     re.compile(r"\bcover\w*\b",     re.IGNORECASE),
    "Product":     re.compile(r"\bproduct\w*\b",   re.IGNORECASE),
}

# Group-count detection. Three patterns (most specific first):
#   A. "<number> [adjective]{0,2} <group_noun>"   e.g. "three distinct groups"
#   B. ordinal-list: "<ordinal> ... <group_noun>" repeated  e.g. "the first group ... the second group ... the third group"
#   C. repetition: 2+ occurrences of "(a|the|another) [adj]{0,2} <group_noun>"
#                  e.g. "covers a group of three noetics ... cover a larger group of nine noetics"
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_GROUP_NOUNS = ("group", "groups", "cluster", "clusters", "set", "sets")
_GROUP_COUNT_RX_A = re.compile(
    r"\b(?P<num>" + "|".join(_NUMBER_WORDS.keys()) + r"|\d+)\b"
    r"(?:\s+\w+){0,2}"
    r"\s+(?:" + "|".join(_GROUP_NOUNS) + r")\b",
    re.IGNORECASE,
)
_ORDINAL_GROUP_RX = re.compile(
    r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+"
    r"(?:\w+\s+){0,2}"
    r"(?:" + "|".join(_GROUP_NOUNS) + r")\b",
    re.IGNORECASE,
)
_REPEAT_GROUP_RX = re.compile(
    r"\b(?:a|the|another|second|third)\s+"
    r"(?:\w+\s+){0,2}"
    r"(?:" + "|".join(_GROUP_NOUNS) + r")\b",
    re.IGNORECASE,
)

# Noetic indicators (same map as fractal_repair / meta_logic_repair).
_NOETIC_INDICATORS: dict[int, tuple[str, ...]] = {
    0: ("foundational thought", "an idea", "a thought", "in your head"),
    1: ("paying attention", "make up your mind", "cognitive attention"),
    2: ("drawn to", "speaks to", "attracted toward"),
    3: ("rubs the wrong way", "averse to", "repelled", "pushed away",
        "can't stomach"),
    4: ("struck a chord", "made an impression", "resonated"),
    5: ("who one is", "who you are", "shaped by experiences",
        "sum of experiences"),
    6: ("breaking it down", "unpacking", "pulling apart"),
    7: ("muscle memory", "practice makes perfect", "practiced rhythm",
        "practice-based"),
    8: ("that reminds", "one thing leads", "triggered a memory"),
    9: ("popped into mind", "popped to mind", "just clicked", "popped"),
}


def _detect_relation_in_target(target: str) -> str | None:
    """Return the relation type whose indicator appears earliest in
    target, or None if no relation indicator is found."""
    earliest_pos = None
    earliest_rel = None
    for rel, pat in _RELATION_PATTERNS.items():
        m = pat.search(target)
        if m is None:
            continue
        if earliest_pos is None or m.start() < earliest_pos:
            earliest_pos = m.start()
            earliest_rel = rel
    return earliest_rel


def _detect_cluster_count(target: str) -> int:
    """Best-effort cluster-cardinality estimate from the target text.

    Tries three patterns in order:
      A. ``<number> [adjective]{0,2} <group_noun>`` ("three distinct
         groups") — extracts the number directly.
      B. ordinal mentions ("first group / second group / third group")
         — counts the unique ordinals.
      C. repetition: count occurrences of ``a/the/another <group_noun>``
         when there are >= 2 hits.
    """
    # Pattern A — direct number + optional adjectives + group noun.
    m = _GROUP_COUNT_RX_A.search(target)
    if m is not None:
        word = m.group("num").lower()
        if word.isdigit():
            return int(word)
        if word in _NUMBER_WORDS:
            return _NUMBER_WORDS[word]
    # Pattern B — count unique ordinals modifying group nouns.
    ordinals_seen: set[str] = set()
    for om in _ORDINAL_GROUP_RX.finditer(target):
        ordinal = om.group(0).split()[0].lower()
        ordinals_seen.add(ordinal)
    if len(ordinals_seen) >= 2:
        return len(ordinals_seen)
    # Pattern C — repetition of "(a|the|another|second|third) ... <noun>".
    repetitions = list(_REPEAT_GROUP_RX.finditer(target))
    if len(repetitions) >= 2:
        return len(repetitions)
    return 0


def _noetic_present_in_target(noetic: int, target_lower: str) -> bool:
    indicators = _NOETIC_INDICATORS.get(noetic, ())
    return any(ind in target_lower for ind in indicators)


def audit_one_record(rec: dict) -> dict | None:
    # Filter to cas_to_english only — meta-logic shapes also appear
    # in invalid_to_explanation rows where the target is an
    # error-explanation, not a rendering of the relation.
    task_type = rec.get("v1mix_task_type") or rec.get("task_type") or ""
    if task_type and task_type != "cas_to_english":
        return None
    cas = rec.get("cas_expression", "")
    target = rec.get("reply_text", "")
    if not cas or not target:
        return None
    parsed = parse_meta_logic(cas)
    if parsed is None:
        return None
    target_lower = target.lower()

    detected_rel = _detect_relation_in_target(target)
    detected_count = _detect_cluster_count(target)
    expected_rel = parsed.relation_type
    expected_count = parsed.cluster_count

    relation_match = detected_rel == expected_rel
    cardinality_match = detected_count == expected_count

    # Membership: per-cluster, list missing Noetics
    membership_misses: list[dict] = []
    all_members_present = True
    for i, cluster in enumerate(parsed.clusters):
        missing = [
            n for n in cluster.noetics
            if not _noetic_present_in_target(n, target_lower)
        ]
        if missing:
            all_members_present = False
            membership_misses.append({
                "cluster_index": i,
                "expected_noetics": list(cluster.noetics),
                "missing_noetics": missing,
            })

    strict_match = relation_match and cardinality_match and all_members_present

    return {
        "id": rec.get("id", ""),
        "source_split": rec.get("__source_split", ""),
        "cas_expression": cas,
        "target_text": target,
        "expected_relation": expected_rel,
        "detected_relation": detected_rel,
        "expected_cluster_count": expected_count,
        "detected_cluster_count": detected_count,
        "relation_match": relation_match,
        "cardinality_match": cardinality_match,
        "all_members_present": all_members_present,
        "membership_misses": membership_misses,
        "strict_match": strict_match,
    }


def run_audit():
    rows = []
    files_scanned = []
    for rel in CORPUS_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            files_scanned.append((rel, 0, 0))
            continue
        n_rows = 0
        n_meta = 0
        split_name = path.stem.replace("v1_mix_nlgen_", "")
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rec["__source_split"] = split_name
                n_rows += 1
                row = audit_one_record(rec)
                if row is not None:
                    rows.append(row)
                    n_meta += 1
        files_scanned.append((rel, n_rows, n_meta))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUT_DIR / f"meta_logic_target_audit_{timestamp}.jsonl"
    md_path = OUT_DIR / f"meta_logic_target_audit_{timestamp}.md"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    md_path.write_text(render_markdown(rows, files_scanned), encoding="utf-8")
    return jsonl_path, md_path, rows


def render_markdown(rows, files_scanned) -> str:
    lines = ["# Meta-logic target audit", ""]
    lines.append(
        "Strict structural validation of every meta-logic-shaped "
        "(PartitionOf / CoverOf / Product) training row in the v1 mix."
    )
    lines.append("")
    lines.append("## Files scanned")
    lines.append("")
    lines.append("| File | Rows | Meta-logic rows |")
    lines.append("|---|---:|---:|")
    for path, n, n_m in files_scanned:
        lines.append(f"| `{path}` | {n} | {n_m} |")
    lines.append("")
    if not rows:
        lines.append("No meta-logic rows found.")
        return "\n".join(lines)
    total = len(rows)
    pct = lambda n: f"{100*n/total:.1f}%"

    strict = sum(1 for r in rows if r["strict_match"])
    rel_match = sum(1 for r in rows if r["relation_match"])
    card_match = sum(1 for r in rows if r["cardinality_match"])
    members_clean = sum(1 for r in rows if r["all_members_present"])

    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Total meta-logic rows: **{total}**")
    lines.append(f"- Strict match (all 3 checks pass): **{strict} ({pct(strict)})**")
    lines.append(f"- Relation type matches: {rel_match} ({pct(rel_match)})")
    lines.append(f"- Cluster cardinality matches: {card_match} ({pct(card_match)})")
    lines.append(f"- All cluster members present: {members_clean} ({pct(members_clean)})")
    lines.append("")

    # By relation type
    by_rel = Counter(r["expected_relation"] for r in rows)
    lines.append("## By relation type")
    lines.append("")
    lines.append("| Relation | Rows | Strict match |")
    lines.append("|---|---:|---:|")
    for rel in ("PartitionOf", "CoverOf", "Product"):
        bucket = [r for r in rows if r["expected_relation"] == rel]
        if not bucket:
            continue
        sm = sum(1 for r in bucket if r["strict_match"])
        sm_pct = f"{100*sm/len(bucket):.1f}%"
        lines.append(f"| {rel} | {len(bucket)} | {sm} ({sm_pct}) |")
    lines.append("")

    # By cluster count
    by_count = Counter(r["expected_cluster_count"] for r in rows)
    lines.append("## By cluster count")
    lines.append("")
    lines.append("| n_clusters | Rows | Strict match |")
    lines.append("|---:|---:|---:|")
    for n in sorted(by_count):
        bucket = [r for r in rows if r["expected_cluster_count"] == n]
        sm = sum(1 for r in bucket if r["strict_match"])
        sm_pct = f"{100*sm/len(bucket):.1f}%"
        lines.append(f"| {n} | {len(bucket)} | {sm} ({sm_pct}) |")
    lines.append("")

    # Worst offenders
    failing = [r for r in rows if not r["strict_match"]]
    if failing:
        worst = sorted(
            failing,
            key=lambda r: (
                int(not r["relation_match"])
                + int(not r["cardinality_match"])
                + int(not r["all_members_present"])
                + sum(len(m["missing_noetics"]) for m in r["membership_misses"])
            ),
            reverse=True,
        )[:6]
        lines.append("## Sample of worst offenders")
        lines.append("")
        for r in worst:
            lines.append(f"**id**: `{r['id']}` ({r['source_split']})")
            lines.append("")
            lines.append(f"- source: `{r['cas_expression'][:160]}`")
            lines.append(
                f"- checks: relation={r['relation_match']} "
                f"(expected {r['expected_relation']}, "
                f"detected {r['detected_relation']}), "
                f"cardinality={r['cardinality_match']} "
                f"(expected {r['expected_cluster_count']}, "
                f"detected {r['detected_cluster_count']}), "
                f"members={r['all_members_present']}"
            )
            for m in r["membership_misses"]:
                lines.append(
                    f"  - cluster {m['cluster_index']}: "
                    f"missing {m['missing_noetics']} from "
                    f"{m['expected_noetics']}"
                )
            lines.append(f"- target: {r['target_text'][:240]}")
            lines.append("")
    return "\n".join(lines)


def main():
    print("Auditing meta-logic training targets with strict validator...")
    jsonl_path, md_path, rows = run_audit()
    print()
    print(f"Audit JSONL: {jsonl_path}")
    print(f"Audit report: {md_path}")
    print()
    if rows:
        strict = sum(1 for r in rows if r["strict_match"])
        total = len(rows)
        print(
            f"Headline: {strict}/{total} ({100*strict/total:.1f}%) meta-logic "
            f"training rows pass strict structural validation."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
