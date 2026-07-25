"""Independently recompute every byte-binding asserted by the CANDIDATE
TKS/CAS semantic source registry.

Scope: verification only. This script does NOT sign, promote, or mutate the
registry. It recomputes:

  1. sha256 of every entry in `sources[]` and compares to the recorded value;
  2. the D3DA-vs-A124 definition-string difference counts asserted in
     known_conflicts[owner_payload_D3DA_vs_deployed_A124];
  3. whether canon_subfoundations_28_defs.json is absent from canon_index.json,
     as asserted in known_conflicts[normalized_rich_28_defs_missing_from_index].

Exit code 0 iff every recomputed value reproduces the registry assertion.

Usage:
    python docs/working/gate2_closure/verify_registry_bindings.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / "docs" / "working" / "TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json"

D3DA_PATH = REPO / "docs" / "working" / "tks_owner_locked_definitions_20260603.json"
A124_PATH = Path(
    r"C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass"
    r"/api/resources/tks_owner_locked_definitions_20260603.json"
)
CANON_INDEX = Path(
    r"C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_index.json"
)

EXPECTED_ELEMENT_DIFFS = 20
EXPECTED_FOUNDATION_DIFFS = 8


def sha256_upper(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    failures: list[str] = []
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    print(f"registry: {REGISTRY}")
    print(f"registry sha256: {sha256_upper(REGISTRY)}")
    print(f"registry status: {registry['status']}")
    print()

    print("--- 1. source hash verification ---")
    for entry in registry["sources"]:
        path = Path(entry["path"])
        if not path.exists():
            failures.append(f"MISSING source file: {entry['id']} -> {path}")
            print(f"MISSING  {entry['id']}")
            continue
        actual = sha256_upper(path)
        recorded = entry["sha256"].upper()
        if actual == recorded:
            print(f"MATCH    {entry['id']}")
        else:
            failures.append(
                f"HASH MISMATCH {entry['id']}: registry={recorded} actual={actual}"
            )
            print(f"MISMATCH {entry['id']}: registry={recorded} actual={actual}")
    print()

    print("--- 2. D3DA vs A124 definition-string differences ---")
    left = json.loads(D3DA_PATH.read_text(encoding="utf-8"))
    right = json.loads(A124_PATH.read_text(encoding="utf-8"))
    expected = {
        "tks_40_elements": EXPECTED_ELEMENT_DIFFS,
        "tks_28_foundations": EXPECTED_FOUNDATION_DIFFS,
    }
    for key, want in expected.items():
        a = {r["code"]: r for r in left[key]}
        b = {r["code"]: r for r in right[key]}
        if sorted(a) != sorted(b):
            failures.append(f"{key}: code sets are not identical")
        got = sum(1 for c in a if a[c]["definition"] != b[c]["definition"])
        print(f"{key}: {got} of {len(a)} definition strings differ (registry asserts {want})")
        if got != want:
            failures.append(f"{key}: expected {want} differing definitions, recomputed {got}")
    print()

    print("--- 3. canon_index membership ---")
    canon_index = json.loads(CANON_INDEX.read_text(encoding="utf-8"))
    listed = "canon_subfoundations_28_defs.json" in canon_index.get("files", [])
    print(f"canon_index version: {canon_index.get('version')}")
    print(f"canon_subfoundations_28_defs.json listed: {listed}")
    if listed:
        failures.append(
            "canon_subfoundations_28_defs.json IS listed in canon_index.json; "
            "the registry's normalized_rich_28_defs_missing_from_index finding no longer holds"
        )
    print()

    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("RESULT: all registry byte-bindings and difference counts reproduced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
