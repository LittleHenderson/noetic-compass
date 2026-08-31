"""container_prep.py -- the CONTAINER-PREP orchestration driver (GATE 1A.2R s.6-7).

Runs under a SIGNED CONTAINER_PREP approval and does ONLY what that approval
permits: verify the approval FIRST, resolve the exact model revision, hash every
model + tokenizer file, construct the alternative-taxonomy (S7) table at the
registered location, resolve the dependency lock, measure prep cost/time, and
emit CONTAINER_PREP_RECEIPT.json + the resolved identities that later fill the
EXECUTION approval. It authorizes no training, no protected read, no claim.

The model download and container build are REAL/AWS operations unreachable in
Gate 1A.2; every external effect is an injected hook (resolve_model, s3_get,
uploader) so the prep LOGIC is exercised with fakes in the REAL-branch
conformance tests -- no model, GPU, or AWS. The S7-table construction is fully
committed and runs deterministically here.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tools"))

from exec.fsio import write_utf8_lf  # noqa: E402

# the 16 registered head verbs (must equal ALTERNATIVE_TAXONOMY_MANIFEST_CANDIDATE)
REGISTERED_VERBS = ["drawn", "pulled", "felt", "captured", "withdrew", "repelled",
                    "recoiled", "backed", "broke", "lay", "split", "made",
                    "brought", "thought", "reminded", "summoned"]


class ContainerPrepViolation(RuntimeError):
    pass


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_alternative_taxonomy_table(manifest_path: Path, out_path: Path) -> str:
    """Construct the S7 SINGLE_ALTERNATIVE_TAXONOMY table deterministically from
    the registered head_verb_table (the manifest's executable fallback: assign
    the 16 verbs to 4 balanced classes by their frozen order, 4 per class).
    Writes derived/alternative_taxonomy_table.json; returns its sha256."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    table = manifest["construction_law"]["head_verb_table"]
    verbs = []
    for cls in ("^2", "^3", "^6", "^8"):
        for fam in ("A", "B", "C", "D"):
            verbs.append(table[cls][fam])
    if sorted(verbs) != sorted(REGISTERED_VERBS):
        raise ContainerPrepViolation(
            "TAXONOMY_VERB_SET_MISMATCH: head_verb_table != registered verbs")
    # executable fallback: 16 verbs, 4 balanced classes, frozen order (4 each)
    verb_to_class = {v: (i // 4) for i, v in enumerate(verbs)}
    obj = {"table_id": "ALTERNATIVE_TAXONOMY_TABLE",
           "construction": "frozen head-verb order, 4 balanced classes",
           "verb_to_class": verb_to_class}
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    write_utf8_lf(out_path, text)
    return _sha256_bytes(text.encode("utf-8"))


def resolve_dependency_lock(freeze_path: Path) -> str:
    """Hash the resolved pip freeze the container build produced."""
    return _sha256_bytes(Path(freeze_path).read_bytes())


def run_container_prep(*, approval_path: Path, package_root: Path,
                       expected_commit: str, mode: str,
                       resolve_model, freeze_path: Path,
                       container_image_digest: str, receipt_out: Path,
                       uploader=None) -> dict:
    """Verify the prep approval, resolve identities, build S7, emit the receipt.

    resolve_model() -> {"revision_sha", "model_weight_sha256s",
                        "tokenizer_file_sha256s"} (REAL: download+hash the pinned
    revision; conformance: a fake resolver). No training, no protected read."""
    from verify_phase_approval import verify_container_prep
    package_root = Path(package_root)
    approval = json.loads(Path(approval_path).read_text(encoding="utf-8"))
    verify_container_prep(approval, package_root, expected_commit, mode,
                          approval_path=approval_path)      # FIRST -- fail closed
    identities = resolve_model()
    for k in ("revision_sha", "model_weight_sha256s", "tokenizer_file_sha256s"):
        if k not in identities:
            raise ContainerPrepViolation(f"resolve_model missing {k}")
    s7_sha = build_alternative_taxonomy_table(
        package_root / "ALTERNATIVE_TAXONOMY_MANIFEST_CANDIDATE.json",
        package_root / "derived" / "alternative_taxonomy_table.json")
    dep_lock_sha = resolve_dependency_lock(freeze_path)
    receipt = {"receipt_id": "CONTAINER_PREP_RECEIPT",
               "non_claim_bearing": True,
               "package_commit_sha": expected_commit,
               "model_revision_sha": identities["revision_sha"],
               "model_weight_sha256s": identities["model_weight_sha256s"],
               "tokenizer_file_sha256s": identities["tokenizer_file_sha256s"],
               "dependency_lock_sha256": dep_lock_sha,
               "container_image_digest": container_image_digest,
               "s7_control_table_sha256": s7_sha}
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    write_utf8_lf(Path(receipt_out), text)
    receipt["_receipt_sha256"] = _sha256_bytes(text.encode("utf-8"))
    if uploader is not None:
        uploader(Path(receipt_out))
    return receipt
