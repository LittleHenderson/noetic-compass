"""generate_pathb.py -- deterministic PATH B dataset builder (CJT-T2).

Writes train.jsonl (families A,B) and val.jsonl (family C) with canonical
LF bytes; generates the protected split (family D) IN MEMORY ONLY, counts and
digests it, and never writes it (v1 law). The protected derivation for the
DEV round uses a DISPOSABLE TEST SALT, clearly labeled non-claim-bearing; the
real owner-salt derivation is registered later by commitment only (owner D5).

Every record must pass the independent round-trip checker; failures are
EXCLUDED, never relabeled (construction-gold law). If clean coverage cannot
reach the registered counts within the attempt budget:
INSUFFICIENT_PATH_B_CLEAN_COVERAGE (owner D4 caveat).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
from exec.fsio import write_utf8_lf  # noqa: E402

from pathb_core import QFAMS, SPLIT_FAMILY, build_record  # noqa: E402
from pathb_roundtrip import check_record  # noqa: E402

SIZES = {"train": 12000, "val": 1500, "protected": 1500}
SEED_STREAM = "PATHB_V03_20260831"
TEST_SALT = "PATHB_TEST_SALT_NON_CLAIM_BEARING_v1"     # dev-only, disposable
ATTEMPT_FACTOR = 3


def canonical_line(rec) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))


def build_split(split, mutation=None):
    fams = SPLIT_FAMILY[split]
    per = SIZES[split] // (len(fams) * len(QFAMS))
    stream = SEED_STREAM if split != "protected" \
        else f"{SEED_STREAM}|SALT:{TEST_SALT}"
    records, excluded = [], 0
    for fam in fams:
        for qf in QFAMS:
            got, idx = 0, 0
            while got < per:
                if idx >= per * ATTEMPT_FACTOR:
                    raise SystemExit(
                        f"INSUFFICIENT_PATH_B_CLEAN_COVERAGE: {split}/{fam}/"
                        f"{qf} got {got}/{per} after {idx} attempts")
                rec = build_record(stream, split, fam, qf, idx)
                idx += 1
                if rec is None:
                    excluded += 1
                    continue
                if mutation is not None:
                    rec = mutation(rec)
                ok, why = check_record(rec) if mutation is None else (True, "")
                if not ok:
                    excluded += 1
                    continue
                rec["passage_id"] = f"{split[0]}{fam}{got:06d}"
                records.append(rec)
                got += 1
    return records, excluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(HERE / "data"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    manifest = {"manifest_id": "PATHB_DATASET_MANIFEST_v0_3",
                "non_claim_bearing": True, "seed_stream": SEED_STREAM,
                "protected_derivation":
                    {"mode": "TEST_SALT_NON_CLAIM_BEARING",
                     "test_salt_sha256": hashlib.sha256(
                         TEST_SALT.encode()).hexdigest(),
                     "owner_salt_commitment": "TO_BE_REGISTERED (owner D5); "
                     "the dev protected split is NON-claim-bearing"},
                "splits": {}, "files": {}}
    for split in ("train", "val", "protected"):
        records, excluded = build_split(split)
        body = "\n".join(canonical_line(r) for r in records) + "\n"
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        manifest["splits"][split] = {
            "passages": len(records), "excluded": excluded,
            "content_sha256": digest,
            "families": list(SPLIT_FAMILY[split])}
        if split != "protected":                       # protected NEVER written
            write_utf8_lf(out / f"{split}.jsonl", body)
            manifest["files"][f"data/{split}.jsonl"] = digest
        print(f"[{split}] {len(records)} accepted, {excluded} excluded, "
              f"sha {digest[:16]}...")
    write_utf8_lf(HERE / "PATHB_DATASET_MANIFEST.json",
                  json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("manifest written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
