"""build_dag_gpu_package.py -- Seals the AWS GPU Training Package for Stage v0.7.

Packages:
- JOB_SPEC.json
- dag_dataset_generator.py
- dag_proposer_model.py
- train_dag_proposer_job.py

Generates:
- SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip
- PACKAGE_MANIFEST.json
- PACKAGE_FREEZE.json
"""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_NAME = "SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip"
ZIP_PATH = HERE / PACKAGE_NAME
MANIFEST_PATH = HERE / "PACKAGE_MANIFEST.json"
FREEZE_PATH = HERE / "PACKAGE_FREEZE.json"

FILES_TO_PACK = [
    "JOB_SPEC.json",
    "dag_dataset_generator.py",
    "dag_proposer_model.py",
    "train_dag_proposer_job.py"
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    print(f"=== Building HELM Stage v0.7 GPU Training Package ===")
    manifest = {}

    for fname in FILES_TO_PACK:
        fpath = HERE / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing required file: {fname}")
        b = fpath.read_bytes()
        digest = sha256_bytes(b)
        manifest[fname] = {
            "size_bytes": len(b),
            "sha256": digest
        }
        print(f"  {fname:<30} {len(b):>8} bytes  sha256: {digest[:16]}...")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Build Zip archive
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname in FILES_TO_PACK:
            zf.write(HERE / fname, arcname=f"SCRIBE_V07_DAG_AWS_GPU/{fname}")

    zip_bytes = ZIP_PATH.read_bytes()
    zip_sha = sha256_bytes(zip_bytes)
    zip_size = len(zip_bytes)

    freeze_doc = {
        "package_name": PACKAGE_NAME,
        "zip_size_bytes": zip_size,
        "zip_sha256": zip_sha,
        "file_count": len(FILES_TO_PACK),
        "claim_ceiling": "ENGINEERED-NOT-VALIDATED",
        "claim_status": "SYNTHETIC_ONLY"
    }

    with open(FREEZE_PATH, "w", encoding="utf-8") as f:
        json.dump(freeze_doc, f, indent=2)

    print(f"\nSuccessfully sealed {PACKAGE_NAME}:")
    print(f"  Size: {zip_size} bytes")
    print(f"  SHA256: {zip_sha}")
    print(f"  Freeze recorded in: {FREEZE_PATH.name}")


if __name__ == "__main__":
    main()
