"""identity.py -- executable model/container/AWS identity checks (GATE 1A.2 s.8).

REAL mode requires independently verified AWS identity -- the EC2 IMDSv2
instance-identity document and an STS caller-identity call -- never an
environment variable saying AWS=true, and a local CUDA device NEVER satisfies
the real campaign gate. SYNTHETIC_CONFORMANCE mode accepts only the registered
synthetic fixture object (marked synthetic=true), which the real gate refuses.

Container-prep mode writes CONTAINER_PREP_RECEIPT.json; execution verification
re-reads it and independently recomputes every resolved identity before any
training.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


class IdentityViolation(RuntimeError):
    pass


def _fail(msg):
    raise IdentityViolation(f"IDENTITY_VIOLATION: {msg}")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_file_map(root: Path, expected: dict, what: str):
    """Every expected file must exist and hash exactly; no expected file may be
    missing. Placeholder values never pass (64-hex enforced upstream)."""
    if not isinstance(expected, dict) or not expected:
        _fail(f"{what}: expected file map is empty")
    for fname, want in sorted(expected.items()):
        f = Path(root) / fname
        if not f.is_file():
            _fail(f"{what}: file missing: {fname}")
        got = sha256_file(f)
        if got != want:
            _fail(f"{what}: {fname} sha {got} != bound {want}")
    return True


def verify_model_identity(model_dir: Path, approval: dict):
    """Resolved revision + every weight file + every tokenizer file."""
    rev_file = Path(model_dir) / "REVISION_SHA"
    if not rev_file.is_file():
        _fail("model revision record missing (REVISION_SHA)")
    resolved = rev_file.read_text(encoding="utf-8").strip()
    if resolved != approval["model_revision_sha"]:
        _fail(f"MODEL_IDENTITY_MISMATCH: resolved revision {resolved} != "
              f"signed {approval['model_revision_sha']}")
    verify_file_map(model_dir, approval["model_weight_sha256s"], "model weights")
    verify_file_map(model_dir, approval["tokenizer_file_sha256s"], "tokenizer")
    return True


def verify_container_identity(container_receipt: dict, approval: dict):
    if container_receipt.get("container_image_digest") \
            != approval["container_image_digest"]:
        _fail("CONTAINER_IDENTITY_MISMATCH: image digest differs from the "
              "signed approval")
    if container_receipt.get("dependency_lock_sha256") \
            != approval["dependency_lock_sha256"]:
        _fail("CONTAINER_IDENTITY_MISMATCH: dependency lock differs")
    return True


def verify_s7_table(table_path: Path, approval: dict):
    p = Path(table_path)
    if not p.is_file():
        _fail("S7 alternative-taxonomy table missing")
    got = sha256_file(p)
    if got != approval["s7_control_table_sha256"]:
        _fail(f"TAXONOMY_IDENTITY_MISMATCH: table sha {got} != signed value")
    return True


def verify_git_state(repo_root: Path, expected_commit: str,
                     package_relpath: str):
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                          capture_output=True, text=True, check=True
                          ).stdout.strip()
    if head != expected_commit:
        _fail(f"checked-out commit {head} != expected {expected_commit}")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", package_relpath],
                           cwd=repo_root, capture_output=True, text=True,
                           check=True).stdout.strip()
    if dirty:
        _fail(f"package working tree is not clean:\n{dirty}")
    return True


def fetch_real_aws_identity():
    """IMDSv2 instance-identity document + STS caller identity. Only callable
    on a real EC2 instance; every failure is a refusal, never a fallback."""
    import urllib.request
    try:
        tok_req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "300"})
        token = urllib.request.urlopen(tok_req, timeout=3).read().decode()
        doc_req = urllib.request.Request(
            "http://169.254.169.254/latest/dynamic/instance-identity/document",
            headers={"X-aws-ec2-metadata-token": token})
        doc = json.loads(urllib.request.urlopen(doc_req, timeout=3).read())
    except Exception as exc:
        _fail(f"IMDSv2 instance identity unavailable ({type(exc).__name__}): "
              "not running on a verifiable EC2 instance")
    try:
        import boto3
        caller = boto3.client("sts", region_name=doc.get("region")) \
            .get_caller_identity()
    except Exception as exc:
        _fail(f"STS caller identity unavailable ({type(exc).__name__})")
    return {"synthetic": False, "account_id": doc.get("accountId"),
            "region": doc.get("region"), "instance_id": doc.get("instanceId"),
            "instance_type": doc.get("instanceType"),
            "sts_account": caller.get("Account")}


def verify_aws_identity(identity: dict, approval: dict, mode: str):
    """REAL: identity must come from fetch_real_aws_identity (synthetic=False,
    account cross-checked against STS). SYNTHETIC_CONFORMANCE: only the
    registered synthetic fixture (synthetic=True) passes -- and it can never
    pass in REAL mode."""
    if mode == "REAL":
        if identity.get("synthetic") is not False:
            _fail("REAL mode requires independently verified AWS identity, not "
                  "a synthetic fixture or an environment flag")
        if identity.get("account_id") != approval["aws_account_id"] \
                or identity.get("sts_account") != approval["aws_account_id"]:
            _fail(f"wrong AWS account {identity.get('account_id')!r} "
                  f"(STS {identity.get('sts_account')!r}) != signed "
                  f"{approval['aws_account_id']}")
    elif mode == "SYNTHETIC_CONFORMANCE":
        if identity.get("synthetic") is not True:
            _fail("synthetic mode requires the registered synthetic fixture")
        if identity.get("account_id") != approval["aws_account_id"]:
            _fail("synthetic fixture account differs from the (test) approval")
    else:
        _fail(f"unknown mode {mode!r}")
    if identity.get("region") != approval["region"]:
        _fail(f"wrong region {identity.get('region')!r}")
    if identity.get("instance_type") != approval["instance_type"]:
        _fail(f"wrong instance type {identity.get('instance_type')!r} != "
              f"signed {approval['instance_type']}")
    if not str(identity.get("instance_id", "")).startswith("i-"):
        _fail("missing EC2 instance id")
    return True


def verify_gpu(approval: dict, mode: str, aws_identity_verified: bool):
    """REAL: CUDA must be available AND the device must be the required A10G
    class AND the AWS identity must already be verified -- a local CUDA card
    without verified AWS identity never satisfies the campaign gate."""
    if mode == "SYNTHETIC_CONFORMANCE":
        return True                     # no GPU claim is ever made in synthetic
    if not aws_identity_verified:
        _fail("GPU gate refused: AWS identity not verified -- a local CUDA "
              "device never satisfies the real campaign gate")
    import torch
    if not torch.cuda.is_available():
        _fail("GPU_REQUIRED: no CUDA device")
    name = torch.cuda.get_device_name(0)
    if "A10G" not in name:
        _fail(f"wrong GPU class {name!r}; the approval requires "
              f"{approval['required_gpu_type']}")
    return True
