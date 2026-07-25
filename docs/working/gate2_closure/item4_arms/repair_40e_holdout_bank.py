"""Build item B1 — repair the 40-Element holdout bank's leaking splits.

MEASURED DEFECT (operator-verified before this script was written), on
`experiment/cas-probe-pythia:.../stage9_elements_pilot_20260517.jsonl`:

    total rows                       8,320
    unique `english` strings         5,920   -> duplication_factor 1.4054
    identical english train <-> test   160
    identical english train <-> val    160
    shared `base_sentence` train<->test 80

`research/reconciled/experiment_admissibility.py` requires duplication_factor
<= 1.0001, so the published bank is INADMISSIBLE as shipped. A probe trained on
these splits sees test prompts during training — the same class of defect that
invalidated the 2026-07-24 W0 runs, caught this time before any capture.

REPAIR, in two steps, both lossless and both verified by this script:

 1. DEDUPLICATE to unique `english` strings. This is only lossless if no
    duplicated string carries conflicting labels — the script CHECKS that and
    refuses to write if any conflict exists, rather than silently picking one.

 2. RE-PARTITION so that no `contrast_bundle_id` (falling back to
    `base_sentence`) spans two splits. Grouping by the contrast bundle is
    stricter than grouping by base sentence: a bundle holds a sentence together
    with its hard-contrast partners, and splitting a bundle would let the probe
    memorise one side of a minimal pair. Target proportions match the original
    (train .25 / val .1375 / test .3654 of unique rows, renormalised).

The script does not touch the original file. It writes a new bank plus a
manifest recording both sha256s, the measured before/after leakage, and the
admissibility verdict, so the repair is auditable rather than asserted.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

LABEL_FIELDS = (
    "element_label", "element_domain", "element_domain_name",
    "element_register", "element_register_name",
    "element_noetic_tks", "element_cas_noetic",
)
SPLITS = ("train", "val", "test")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def measure_leakage(rows: list[dict[str, Any]], *, key: str) -> dict[str, Any]:
    by_split: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        by_split[str(r.get("split"))].add(str(r.get(key)))
    pairs = {}
    for a in SPLITS:
        for b in SPLITS:
            if a < b:
                pairs[f"{a}<->{b}"] = len(by_split.get(a, set()) & by_split.get(b, set()))
    uniq = len({str(r.get(key)) for r in rows})
    return {
        "key": key,
        "row_count": len(rows),
        "unique_values": uniq,
        "duplication_factor": round(len(rows) / uniq, 6) if uniq else None,
        "shared_between_splits": pairs,
        "total_leaked_pairs": sum(pairs.values()),
    }


def check_dedup_is_lossless(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """A duplicated prompt is safe to collapse ONLY if its labels never conflict."""
    labels_by_text: dict[str, set[tuple]] = defaultdict(set)
    for r in rows:
        labels_by_text[str(r.get("english"))].add(tuple(str(r.get(f)) for f in LABEL_FIELDS))
    conflicts = {t: len(v) for t, v in labels_by_text.items() if len(v) > 1}
    return {
        "duplicated_texts": sum(1 for v in labels_by_text.values() if len(v) >= 1 and True) and
                            sum(1 for t, v in labels_by_text.items() if len(v) >= 1) - len(labels_by_text) + len(labels_by_text),
        "texts_with_conflicting_labels": len(conflicts),
        "conflict_examples": list(conflicts)[:5],
        "lossless": not conflicts,
    }


def group_key(row: dict[str, Any]) -> str:
    for field in ("contrast_bundle_id", "counterfactual_pair_id", "base_sentence"):
        v = row.get(field)
        if v:
            return f"{field}:{v}"
    return f"english:{row.get('english')}"


def repartition(rows: list[dict[str, Any]], *, seed: int, proportions: dict[str, float]) -> list[dict[str, Any]]:
    """Assign whole groups to splits, greedily filling toward target proportions.

    Deterministic: groups are ordered by a seeded hash of the group key, then
    each is placed in whichever split is furthest below its target share. No
    group is ever split, so a contrast bundle cannot straddle train and test.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[group_key(r)].append(r)

    def order(k: str) -> str:
        return hashlib.sha256(f"{seed}:{k}".encode("utf-8")).hexdigest()

    total = len(rows)
    targets = {s: proportions[s] * total for s in SPLITS}
    placed = {s: 0 for s in SPLITS}
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=order):
        members = groups[key]
        deficit = {s: (targets[s] - placed[s]) / max(targets[s], 1.0) for s in SPLITS}
        pick = max(SPLITS, key=lambda s: deficit[s])
        for r in members:
            row = dict(r)
            row["split"] = pick
            row["repartition_group"] = key
            out.append(row)
        placed[pick] += len(members)
    return out


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20260725)
    args = ap.parse_args()

    src_bytes = args.source.read_bytes()
    rows = load_rows(args.source)

    before_english = measure_leakage(rows, key="english")
    before_base = measure_leakage(rows, key="base_sentence")
    lossless = check_dedup_is_lossless(rows)
    if not lossless["lossless"]:
        print("REFUSING TO WRITE: duplicated prompts carry conflicting labels.")
        print(json.dumps(lossless, indent=2))
        return 2

    # Step 1 — deduplicate, keeping first occurrence (labels proven identical).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        t = str(r.get("english"))
        if t in seen:
            continue
        seen.add(t)
        deduped.append(r)

    # Step 2 — re-partition, preserving the original split proportions.
    orig = Counter(str(r.get("split")) for r in rows)
    props = {s: orig.get(s, 0) / len(rows) for s in SPLITS}
    repaired = repartition(deduped, seed=args.seed, proportions=props)

    after_english = measure_leakage(repaired, key="english")
    after_base = measure_leakage(repaired, key="base_sentence")
    after_group = measure_leakage(repaired, key="repartition_group")

    payload = "\n".join(json.dumps(r, sort_keys=True) for r in repaired) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    out_sha = sha256_bytes(args.output.read_bytes())

    admissible = (
        after_english["duplication_factor"] is not None
        and after_english["duplication_factor"] <= 1.0001
        and after_english["total_leaked_pairs"] == 0
        and after_group["total_leaked_pairs"] == 0
    )
    manifest = {
        "schema_version": "cas_harness_item4_bank_repair_manifest.v1",
        "build_item": "B1 — repaired 40-Element holdout bank",
        "created_at": datetime.now(UTC).isoformat(),
        "source_path": str(args.source),
        "source_sha256": sha256_bytes(src_bytes),
        "output_path": str(args.output),
        "output_sha256": out_sha,
        "seed": args.seed,
        "dedup_losslessness_check": lossless,
        "before": {"english": before_english, "base_sentence": before_base},
        "after": {"english": after_english, "base_sentence": after_base, "repartition_group": after_group},
        "split_counts_before": dict(sorted(orig.items())),
        "split_counts_after": dict(sorted(Counter(str(r["split"]) for r in repaired).items())),
        "admissible_after_repair": admissible,
        "grouping_rule": "whole contrast_bundle_id (fallback counterfactual_pair_id, then base_sentence) assigned to one split; no group is ever split",
        "honesty_note": (
            "This repair can only REDUCE effective sample size (8,320 rows -> 5,920 unique). "
            "It makes the test harder and fairer, never easier. The unique-prompt count is the "
            "honest denominator and must be the one reported."
        ),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"rows {len(rows)} -> {len(repaired)} unique")
    print(f"duplication_factor {before_english['duplication_factor']} -> {after_english['duplication_factor']}")
    print(f"english leaked pairs {before_english['total_leaked_pairs']} -> {after_english['total_leaked_pairs']}")
    print(f"base_sentence leaked {before_base['total_leaked_pairs']} -> {after_base['total_leaked_pairs']}")
    print(f"group leaked          -> {after_group['total_leaked_pairs']}")
    print(f"splits after: {manifest['split_counts_after']}")
    print(f"ADMISSIBLE AFTER REPAIR: {admissible}")
    print(f"output sha256 {out_sha}")
    return 0 if admissible else 1


if __name__ == "__main__":
    raise SystemExit(main())
