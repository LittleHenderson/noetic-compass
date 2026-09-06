"""Join a candidate package to independently anchored learning evidence.

This is an admission step for fresh reuse experiments, not skill promotion.
The caller supplies audit trust anchors separately from the package. We rerun
the evidence reader; a package's own claimed receipt cannot authorize itself.
No checkpoint is loaded and no program is executed or stored here.
"""
from . import learned_package as packages
from . import learning_evidence as evidence


class HandoffError(ValueError):
    pass


def prepare_reuse_candidate(package, *, expected_digest, trusted_compatibility,
        permitted_cjts, expected_parent_digest, expected_version,
        inspection_bytes, expected_inspection_sha256, stored_audit_bytes,
        expected_stored_audit_sha256, index_bytes, predictions_bytes,
        checkpoints_bytes, trusted_source_sha, arm, case_index,
        minimum_correct_gain=1):
    """Return detached data bound to successful, caller-trusted audit bytes.

    Trust anchors, compatibility, permissions and lineage must be obtained by
    the consumer independently of the candidate. Positive learning evidence
    applies to the source experiment, not to future reuse or a new domain.
    """
    if trusted_source_sha != packages.META2_SOURCE_SHA:
        raise HandoffError("UNSUPPORTED_LEARNING_SOURCE")
    options = dict(expected_digest=expected_digest,
        trusted_compatibility=trusted_compatibility, permitted_cjts=permitted_cjts,
        expected_parent_digest=expected_parent_digest, expected_version=expected_version)
    admitted = packages.validate_package(package, **options)
    # Derive the action from the admitted package. Never accept a second,
    # independently supplied action which could belong to another package.
    proof = evidence.bind_learning_evidence(
        inspection_bytes=inspection_bytes,
        expected_inspection_sha256=expected_inspection_sha256,
        stored_audit_bytes=stored_audit_bytes,
        expected_stored_audit_sha256=expected_stored_audit_sha256,
        index_bytes=index_bytes, predictions_bytes=predictions_bytes,
        checkpoints_bytes=checkpoints_bytes, trusted_source_sha=trusted_source_sha,
        arm=arm, case_index=case_index,
        expected_action={"program": admitted["program"], "binding": admitted["binding"]},
        minimum_correct_gain=minimum_correct_gain)
    for field in ("source_program_sha256", "policy_source_sha256",
                  "policy_checkpoint_sha256", "producer_source_sha"):
        if admitted["provenance"][field] != proof[field]:
            raise HandoffError("LEARNING_PROVENANCE_MISMATCH:" + field)
    if admitted["provenance"]["producer_evidence_sha256"] != proof["receipt_sha256"]:
        raise HandoffError("LEARNING_EVIDENCE_RECEIPT_MISMATCH")
    admission = packages.admission_receipt(admitted, **options)
    body = {
        "schema": "cas-meta3-learned-handoff/0.1",
        "status": "READY_FOR_FRESH_REUSE_TESTS",
        "package_sha256": expected_digest,
        "package": admitted,
        "package_admission": admission,
        "learning_evidence": proof,
        "learning_provenance_bound": True,
        "qualification_status": "UNQUALIFIED",
        "promotion_granted": False,
        "execution_performed": False,
        "storage_performed": False,
        "fresh_native_reuse_tested": False,
        "retention_tested": False,
        "rollback_tested": False,
        "parent_evidence_verified": False,
        "boundary": "Source learning evidence is bound. Fresh reuse, retention, rollback, ancestry and skill qualification remain unproven.",
    }
    return {**body, "receipt_sha256": evidence.digest(body)}
