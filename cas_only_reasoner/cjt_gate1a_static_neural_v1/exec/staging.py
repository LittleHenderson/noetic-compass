"""staging.py -- committed boto3 staging program (GATE 1A.2R section 2).

Replaces the `aws s3 cp/sync` shell calls the frozen image did not install.
Uses the already-pinned boto3 (requirements.lock) to download the detached
approvals, the container-prep receipt, the exact model-file set, and the S7
table into the campaign working directory, verifying every declared digest and
creating no unregistered file. The container recipe therefore no longer depends
on an `aws` executable that the image does not provide.

Nothing here runs in Gate 1A.2 (no AWS call). The REAL-branch conformance tests
inject a fake S3 adapter (get_object/download) so the staging LOGIC -- destination
resolution, digest verification, allow-list enforcement -- is exercised without
any AWS call, model, or GPU.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


class StagingViolation(RuntimeError):
    pass


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def stage_object(s3_get, s3_uri: str, dest: Path,
                 expected_sha256: str = None) -> str:
    """Download one object via the injected s3_get(uri)->bytes; verify digest if
    given; write to dest through no other path. Returns the object's sha256."""
    data = s3_get(s3_uri)
    got = _sha256(data)
    if expected_sha256 is not None and got != expected_sha256:
        raise StagingViolation(f"STAGING_DIGEST_MISMATCH: {s3_uri} sha {got} != "
                               f"expected {expected_sha256}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return got


def stage_model(s3_get, model_s3_prefix: str, model_dir: Path,
                weight_sha256s: dict, tokenizer_sha256s: dict,
                revision_sha: str) -> dict:
    """Download EXACTLY the declared model + tokenizer file set (allow-list) and
    verify each digest. Any file not in the signed maps is never fetched; the
    resolved revision is written for identity verification."""
    model_dir = Path(model_dir)
    staged = {}
    for fname, want in {**weight_sha256s, **tokenizer_sha256s}.items():
        uri = model_s3_prefix.rstrip("/") + "/" + fname
        staged[fname] = stage_object(s3_get, uri, model_dir / fname, want)
    (model_dir / "REVISION_SHA").write_text(revision_sha + "\n", encoding="utf-8")
    return staged


def default_s3_get(region: str):
    """Production s3_get: boto3 get_object. Only built inside the container."""
    import boto3
    client = boto3.client("s3", region_name=region)

    def get(uri: str) -> bytes:
        assert uri.startswith("s3://")
        bucket, key = uri[len("s3://"):].split("/", 1)
        return client.get_object(Bucket=bucket, Key=key)["Body"].read()
    return get
