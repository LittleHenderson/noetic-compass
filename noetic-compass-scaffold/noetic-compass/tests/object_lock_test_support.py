"""Explicit test-only authority seam for synthetic Object Lock receipts.

Production code must obtain an issuer attestation only in the two S3 adapters,
immediately after exact-VersionId ``get_object`` and ``head_object`` calls.  Unit
tests that exercise downstream gates use this visibly synthetic seam instead of
turning the public pure predicate into a receipt-minting oracle.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from api.services.cas_harness_retention_disclosure import (
    ObjectLockReceiptVerification,
    _issue_live_s3_object_lock_receipt,
)


def issue_test_object_lock_receipt(
    *,
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    verified_at: datetime | None = None,
    evaluated_at: datetime | None = None,
) -> ObjectLockReceiptVerification:
    """Mint synthetic authority for isolated downstream-gate tests only."""

    return _issue_live_s3_object_lock_receipt(
        expected=expected,
        observed=observed,
        verified_at=verified_at,
        evaluated_at=evaluated_at,
        _allow_ephemeral_for_tests=True,
    )
