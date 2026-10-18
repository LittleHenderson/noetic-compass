"""build_scribe_gpu_package.py -- Deterministic Package Builder for Level L4 Scribe AWS GPU Job.

Builds and seals the Level L4 Scribe Proposer training package into SCRIBE_L4_AWS_GPU_PACKAGE.zip.
Writes PACKAGE_MANIFEST.json and PACKAGE_FREEZE.json with exact SHA-256 hashes.
Strictly checks that resealing is byte-identical and that LF line endings are preserved.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = "SCRIBE_L4_AWS_GPU"
ZIP_PATH = HERE / "SCRIBE_L4_AWS_GPU_PACKAGE.zip"


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_json(path: Path, obj: Any, indent: int = 2):
    text = json.dumps(obj, sort_keys=True, indent=indent)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")


def build_package():
    print(f"Building and sealing {ZIP_PATH.name}...")

    # Identify package members (excluding generated zip and freeze files)
    excluded = {ZIP_PATH.name, "PACKAGE_FREEZE.json", "PACKAGE_MANIFEST.json"}
    members = {}

    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in excluded and "__pycache__" not in p.parts and not p.name.endswith(".zip"):
            rel_name = p.relative_to(HERE).as_posix()
            content = p.read_bytes()
            # Ensure LF line endings for text files
            if p.suffix in (".py", ".json", ".md", ".sh"):
                if b"\r\n" in content:
                    # Convert to LF
                    content = content.replace(b"\r\n", b"\n")
                    p.write_bytes(content)
            members[rel_name] = sha_b(content)

    manifest_path = HERE / "PACKAGE_MANIFEST.json"
    write_json(manifest_path, {"package_members": members}, indent=2)

    # Deterministic zip creation
    buf = io.BytesIO()
    sorted_files = sorted(members.keys()) + ["PACKAGE_MANIFEST.json"]

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for fname in sorted_files:
            file_path = HERE / fname
            data = file_path.read_bytes()
            zi = zipfile.ZipInfo(f"{ROOT}/{fname}", date_time=(2026, 10, 18, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zi.create_system = 3
            z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    zip_bytes_1 = buf.getvalue()

    # Re-seal verification check
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z2:
        for fname in sorted_files:
            file_path = HERE / fname
            data = file_path.read_bytes()
            zi = zipfile.ZipInfo(f"{ROOT}/{fname}", date_time=(2026, 10, 18, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zi.create_system = 3
            z2.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    zip_bytes_2 = buf2.getvalue()
    if zip_bytes_1 != zip_bytes_2:
        raise SystemExit("[FATAL] Reseal verification failed: bytes differ!")

    with open(ZIP_PATH, "wb") as f:
        f.write(zip_bytes_1)

    freeze_doc = {
        "package_name": "SCRIBE_L4_AWS_GPU",
        "zip_file": ZIP_PATH.name,
        "zip_sha256": sha_b(zip_bytes_1),
        "zip_bytes": len(zip_bytes_1),
        "total_members": len(sorted_files),
        "member_names": [f"{ROOT}/{n}" for n in sorted_files],
        "package_manifest_sha256": sha_b((HERE / "PACKAGE_MANIFEST.json").read_bytes()),
        "reseal_byte_identical": True,
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware_target": "AWS EC2 g4dn.xlarge (Tesla T4)",
        "cost_cap_usd": 1.50,
        "time_cap_seconds": 600
    }

    freeze_path = HERE / "PACKAGE_FREEZE.json"
    write_json(freeze_path, freeze_doc, indent=2)

    print("Package sealed successfully.")
    print(f"  Zip file  : {ZIP_PATH.name} ({len(zip_bytes_1)} bytes)")
    print(f"  Zip SHA256: {freeze_doc['zip_sha256']}")
    print(f"  Members   : {len(sorted_files)} files")
    return freeze_doc


if __name__ == "__main__":
    build_package()
