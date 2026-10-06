"""Shared private identity derivations for the dark Harness-v2 route.

These deterministic identifiers are routing and storage keys only.  They are
not signatures, execution attestations, scientific identities, or licence and
disclosure authorities.
"""

from __future__ import annotations

import hashlib
import re


_ROUTE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class HarnessV2IdentityError(ValueError):
    """A route identity was malformed or did not obey the joint contract."""


def require_route_id(value: object, field: str) -> str:
    if type(value) is not str or not _ROUTE_ID_RE.fullmatch(value):
        raise HarnessV2IdentityError(f"{field} is not an exact route identifier.")
    return value


def prospective_run_id(job_id: str) -> str:
    """Derive the lifecycle run ID from one exact job subject."""

    job = require_route_id(job_id, "job_id")
    return "h2run_" + hashlib.sha256(job.encode("utf-8")).hexdigest()


def route_context_trace_id(job_id: str) -> str:
    """Derive the immutable request-context trace key for one job subject."""

    job = require_route_id(job_id, "job_id")
    return "h2ctx_" + hashlib.sha256(
        f"{job}:prospective-route-context:v1".encode("utf-8")
    ).hexdigest()


def require_joint_run_identity(
    *,
    job_id: str,
    subject_id: str,
    authorization_id: str,
    run_id: str,
) -> None:
    """Fail closed unless route, lifecycle, and strict-carrier identities agree."""

    job = require_route_id(job_id, "job_id")
    subject = require_route_id(subject_id, "subject_id")
    authorization = require_route_id(authorization_id, "authorization_id")
    expected_run = prospective_run_id(job)
    if not (job == subject == authorization):
        raise HarnessV2IdentityError(
            "job_id, subject_id, and authorization_id must be exactly equal."
        )
    if run_id != expected_run:
        raise HarnessV2IdentityError(
            "run_id does not match the deterministic prospective job identity."
        )


__all__ = [
    "HarnessV2IdentityError",
    "prospective_run_id",
    "require_joint_run_identity",
    "require_route_id",
    "route_context_trace_id",
]
