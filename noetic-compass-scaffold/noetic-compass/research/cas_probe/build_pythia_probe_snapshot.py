"""Build the frozen Pythia probe label snapshot.

Joins Wave 3 ``cas_to_english`` records (each carries a model-generated
natural-English description) with the seed file (each seed carries a
clean CAS expression + axis labels). Filters to records eligible for a
single-noetic linear probe and writes a frozen jsonl + manifest.

Run from the repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/build_pythia_probe_snapshot.py

The output is deterministic given the same source files: re-running with
the same inputs produces a byte-identical snapshot and manifest. The
manifest records source-file sha256s so a later audit can confirm the
inputs are unchanged.

This script reads files only — no Pythia imports, no network. Safe to
run on any host.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
# Paths — repo-rooted so the script is portable across hosts.
# --------------------------------------------------------------------------- #

_HERE = Path(__file__).resolve().parent
# research/cas_probe → research → noetic-compass → noetic-compass-scaffold → tksCAS
_REPO_ROOT = _HERE.parents[3]

_WAVE3_PATH = (
    _REPO_ROOT
    / "cas-synthetic" / "data" / "path_d" / "wave3_full"
    / "wave3_smoke_20260507T232622Z.jsonl"
)
_SEEDS_PATH = (
    _REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "seeds.jsonl"
)

_TODAY = "20260515"
_OUT_LABELS = _HERE / f"pythia_probe_labels_{_TODAY}.jsonl"
_OUT_MANIFEST = _HERE / f"pythia_probe_manifest_{_TODAY}.json"


# --------------------------------------------------------------------------- #
# Extraction rules — keep these in sync with the manifest.
# --------------------------------------------------------------------------- #

EXTRACTION_RULES: list[str] = [
    "Source: cas_to_english records from wave3_smoke_20260507T232622Z.jsonl "
    "joined to seeds.jsonl by sample_id.source_id == seed.seed_id.",
    "Pythia input: the natural-English description in the wave3 record's "
    "'raw_response' field (the model-generated paraphrase of the seed CAS).",
    "Label: seed.axes.noetics_used[0], which is one of 0..9.",
    "Filter — single noetic only: seed.axes.noetics_used must have length "
    "exactly 1. Records with 0 noetics (e.g. domain-only expressions) or "
    "multiple noetics (compound expressions) are excluded for the v1 "
    "single-label probe.",
    "Filter — compiler-validated SEED: seed.compiler_validated must be True. "
    "Note: the wave3 cas_to_english record's own compiler_validated field is "
    "always None (it produces English, not CAS, so there is nothing to "
    "compile). The validity check rides on the seed expression.",
    "Filter — no leakage: wave3 record's leakage_in_reply must be False "
    "(CAS notation did not bleed into the English description).",
    "Filter — non-empty english: raw_response must be a non-empty string "
    "after stripping whitespace.",
    "Filter — minimum length: raw_response must be at least 20 characters "
    "after stripping (rejects empty / trivial / one-word responses).",
    "Random selection: NONE. The script is deterministic; full set of "
    "eligible records is emitted in the order they appear in the wave3 "
    "source.",
]


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _index_seeds_by_id(seeds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for seed in seeds:
        sid = seed.get("seed_id")
        if isinstance(sid, str):
            out[sid] = seed
    return out


def build() -> dict[str, Any]:
    if not _WAVE3_PATH.is_file():
        raise SystemExit(f"missing wave3 source: {_WAVE3_PATH}")
    if not _SEEDS_PATH.is_file():
        raise SystemExit(f"missing seeds source: {_SEEDS_PATH}")

    wave3 = _load_jsonl(_WAVE3_PATH)
    seeds = _load_jsonl(_SEEDS_PATH)
    seeds_by_id = _index_seeds_by_id(seeds)

    rejected = Counter()
    rows: list[dict[str, Any]] = []

    for r in wave3:
        if r.get("slot") != "cas_to_english":
            rejected["wrong_slot"] += 1
            continue
        # NOTE: r["compiler_validated"] is None for cas_to_english records
        # (the model produces English, not CAS). The compiler-validation
        # check rides on the SEED's expression, applied below.
        if r.get("leakage_in_reply"):
            rejected["cas_leaked_into_english"] += 1
            continue

        english = (r.get("raw_response") or "").strip()
        if not english or len(english) < 20:
            rejected["english_too_short_or_empty"] += 1
            continue

        source_id = r.get("source_id")
        if not isinstance(source_id, str):
            rejected["missing_source_id"] += 1
            continue

        seed = seeds_by_id.get(source_id)
        if seed is None:
            rejected["seed_not_found"] += 1
            continue

        # Seed-side compiler validation gate.
        if not seed.get("compiler_validated"):
            rejected["seed_not_compiler_validated"] += 1
            continue

        noetics_used = (seed.get("axes") or {}).get("noetics_used") or []
        if len(noetics_used) != 1:
            rejected[f"noetics_count_{len(noetics_used)}"] += 1
            continue

        try:
            noetic_label = int(noetics_used[0])
        except (TypeError, ValueError):
            rejected["noetic_label_not_int"] += 1
            continue
        if noetic_label < 0 or noetic_label > 9:
            rejected[f"noetic_label_out_of_range_{noetic_label}"] += 1
            continue

        rows.append({
            "sample_id": r.get("sample_id"),
            "source_seed_id": source_id,
            "english": english,
            "noetic_label": noetic_label,
            "source_cas_expression": seed.get("expression"),
            "grammar_category": seed.get("grammar_category"),
        })

    # Write the snapshot.
    with _OUT_LABELS.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    class_dist = Counter(row["noetic_label"] for row in rows)

    manifest = {
        "schema_version": "pythia_probe_snapshot.v1",
        "snapshot_id": f"pythia_probe_labels_{_TODAY}",
        "built_at_utc": datetime.now(tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "snapshot_file": _OUT_LABELS.name,
        "snapshot_sha256": _sha256_of_file(_OUT_LABELS),
        "record_count": len(rows),
        "class_distribution": {
            str(label): count for label, count in sorted(class_dist.items())
        },
        "chance_baseline_per_class": (
            1.0 / 10 if class_dist else None
        ),
        "rejected_counts": dict(rejected),
        "source_files": [
            {
                "path": str(_WAVE3_PATH.relative_to(_REPO_ROOT)),
                "sha256": _sha256_of_file(_WAVE3_PATH),
                "record_count": len(wave3),
            },
            {
                "path": str(_SEEDS_PATH.relative_to(_REPO_ROOT)),
                "sha256": _sha256_of_file(_SEEDS_PATH),
                "record_count": len(seeds),
            },
        ],
        "extraction_rules": EXTRACTION_RULES,
        "guardrails": [
            "This snapshot is research-only, used ONLY by code under "
            "noetic-compass-scaffold/noetic-compass/research/cas_probe/.",
            "Pythia weights and any probe artifacts derived from this "
            "snapshot must never enter the production CAS Native stack.",
        ],
    }

    with _OUT_MANIFEST.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    return manifest


def main() -> int:
    manifest = build()
    print(f"snapshot written: {_OUT_LABELS}")
    print(f"manifest written: {_OUT_MANIFEST}")
    print(f"record_count: {manifest['record_count']}")
    print("class_distribution:")
    for label, count in manifest["class_distribution"].items():
        print(f"  ^{label}: {count}")
    print(f"rejected (total {sum(manifest['rejected_counts'].values())}):")
    for reason, count in sorted(
        manifest["rejected_counts"].items(), key=lambda kv: -kv[1]
    ):
        print(f"  {reason}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
