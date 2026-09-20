"""Teacher-side committed-source training bundle builder; never shipped to GPU.

No curriculum generator or final evaluation file is read. Real construction
requires a complete source-freeze commit. Injected blob readers are synthetic
unit-test seams, explicitly identified in their receipts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from . import worker_contract as contract

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / "records/teaching_cycle_001"
MATERIAL = "records/teaching_cycle_001/material_001/teaching/"
WHEEL_SOURCE = "CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/casformer_reference-0.1.0-py3-none-any.whl"


def _git(arguments):
    process = subprocess.run(["git", *arguments], cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=30,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    contract.require(process.returncode == 0, "COMMITTED_GIT_READ_FAILED")
    return process.stdout


def _prefix():
    return _git(["rev-parse", "--show-prefix"]).decode("utf-8").strip()


def _git_blob(source_sha, repository_path):
    """Read exact regular-file blob bytes; never consult working-tree content."""
    tree = _git(["ls-tree", "--full-tree", "-z", source_sha, "--", ":(literal)" + repository_path])
    rows = tree.rstrip(b"\0").split(b"\0")
    contract.require(len(rows) == 1 and b"\t" in rows[0], "COMMITTED_FILE_REQUIRED:" + repository_path)
    info, name = rows[0].split(b"\t", 1)
    mode, kind, object_id = info.split(b" ")
    contract.require(mode in (b"100644", b"100755") and kind == b"blob"
                     and name.decode("utf-8") == repository_path, "COMMITTED_REGULAR_FILE_REQUIRED")
    size = int(_git(["cat-file", "-s", object_id.decode("ascii")]))
    contract.require(0 < size <= contract.FILE_BYTES_MAX, "COMMITTED_FILE_BYTES_BOUND")
    raw = _git(["cat-file", "blob", object_id.decode("ascii")])
    contract.require(len(raw) == size, "COMMITTED_BLOB_SIZE_CHANGED")
    return raw


def _write(path, raw):
    with contract.safe_path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    contract.require(path.read_bytes() == raw, "PACKAGE_WRITE_READBACK")


def build_bundle(source_sha, output, *, _read_blob=None):
    """Build once from a commit; output must be a fresh teaching-record path."""
    contract.require(contract._pin(source_sha, 40), "COMMIT_SHA_REQUIRED")
    output = contract.safe_path(output)
    records = contract.safe_path(RECORDS)
    contract.require(output.is_relative_to(records) and output != records and
                     not output.exists() and output.parent.is_dir(), "FRESH_TEACHING_OUTPUT_REQUIRED")
    if _read_blob is None:
        actual = _git(["rev-parse", "--verify", source_sha + "^{commit}"]).decode("ascii").strip()
        contract.require(actual == source_sha, "EXACT_COMMIT_REQUIRED")
    reader = _read_blob or _git_blob
    prefix = _prefix()
    paths = {name: prefix + name for name in contract.WORKER_FILES}
    paths.update({name: prefix + MATERIAL + name for name in contract.CASE_FILES})
    paths[contract.WHEEL_NAME] = str(PurePosixPath(prefix).parent / WHEEL_SOURCE)
    payloads = {name: reader(source_sha, path) for name, path in sorted(paths.items())}
    contract.require(all(type(raw) is bytes for raw in payloads.values()), "GIT_BLOB_BYTES_REQUIRED")
    training = contract.decode_json(payloads["train.json"])
    development = contract.decode_json(payloads["development.json"])
    contract.require(type(training) is list and all(type(c) is dict and "family_id" in c for c in training),
                     "TRAINING_CASES_REQUIRED")
    manifest = {"schema": contract.SCHEMA, "source_commit": source_sha,
        "source_sha256": contract.canonical_sha256({name: contract.digest(payloads[name]) for name in contract.WORKER_FILES}),
        "training_cases_sha256": contract.canonical_sha256(sorted(training, key=lambda c: c["family_id"])),
        "development_cases_sha256": contract.canonical_sha256(development),
        "profile": deepcopy(contract.PROFILE),
        "files": {name: {"sha256": contract.digest(raw), "bytes": len(raw)} for name, raw in payloads.items()}}
    manifest_raw = contract.canonical(manifest) + b"\n"
    manifest_sha = contract.digest(manifest_raw)
    contract.validate_payloads(manifest_raw, payloads, manifest_sha)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as zipped:
        for name, raw in sorted({contract.MANIFEST_NAME: manifest_raw, **payloads}.items()):
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = ZIP_DEFLATED
            zipped.writestr(entry, raw)
    archive_raw = buffer.getvalue()
    contract.require(len(archive_raw) <= contract.ARCHIVE_BYTES_MAX, "ARCHIVE_BYTES_BOUND")
    output.mkdir()
    archive_path = output / "training.zip"
    _write(archive_path, archive_raw)
    _write(output / "manifest.json", manifest_raw)
    contract.archive_payloads(archive_path, contract.digest(archive_raw), manifest_sha)
    receipt = {"schema": "cas-meta2-teaching-cycle-training-package-receipt/1",
        "status": "TRAINING_SOURCE_ONLY_NO_LAUNCH", "source_commit": source_sha,
        "source_reader": "git_committed_blobs" if _read_blob is None else "synthetic_injected_blob_reader",
        "archive": str(archive_path), "archive_sha256": contract.digest(archive_raw),
        "archive_bytes": len(archive_raw), "manifest_sha256": manifest_sha,
        "member_count": len(contract.ALL_FILES), "source_sha256": manifest["source_sha256"],
        "training_cases_sha256": manifest["training_cases_sha256"],
        "development_cases_sha256": manifest["development_cases_sha256"],
        "counts": {"training": len(training), "development": len(development)},
        "profile": manifest["profile"], "provider_calls": 0, "reservation_created": False}
    _write(output / "receipt.json", contract.canonical(receipt) + b"\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args(argv)
    print(json.dumps(build_bundle(arguments.source_sha, arguments.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
