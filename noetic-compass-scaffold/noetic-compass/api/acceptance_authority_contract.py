"""Public read contract for customer-production acceptance evidence.

The acceptance verifier has to dereference a stable HTTPS JSON document without
carrying a production bearer token.  This module is intentionally tiny so the
route, authentication middleware, rate limiter, persistence service, and tests
share one exact path allowlist.

``root_ci_protected_deploy`` is deliberately absent.  GitHub/Render aggregate
proof remains signed-receipt-only because this API is not an independent
authority for GitHub branch protection or Actions identity.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from types import MappingProxyType


PRODUCTION_API_ORIGIN = "https://cas-harness-customer-api.onrender.com"

# Canonical gate name -> exact public, read-only path.  Do not replace this with
# a broad ``/internal/acceptance`` prefix: a future management/write route must
# never become anonymous by inheritance.
ACCEPTANCE_AUTHORITY_PATH_BY_GATE: Mapping[str, str] = MappingProxyType(
    {
        "runtime_worm": "/internal/acceptance/runtime-worm",
        "hosted_customer_journey": "/internal/acceptance/customer-journey",
        "accounts_billing": "/internal/acceptance/accounts-billing",
        "legal_publication_approval": (
            "/internal/acceptance/legal-publication-approval"
        ),
        "support_crm": "/internal/acceptance/support-crm",
        "incident_tabletop": "/internal/acceptance/incident-tabletop",
        "alert_delivery": "/internal/acceptance/alert-delivery",
        "claim_honesty": "/internal/acceptance/claim-honesty",
        "release_decision": "/internal/acceptance/release-decision",
    }
)

ACCEPTANCE_AUTHORITY_GATE_BY_PATH: Mapping[str, str] = MappingProxyType(
    {path: gate for gate, path in ACCEPTANCE_AUTHORITY_PATH_BY_GATE.items()}
)
ACCEPTANCE_AUTHORITY_PUBLIC_PATHS = frozenset(
    ACCEPTANCE_AUTHORITY_GATE_BY_PATH
)

# One immutable publication-authorization record is addressed only by its
# lowercase canonical-body SHA-256.  Keep this separate from the gate paths:
# the record authorizes a publication operation; it is not gate evidence or a
# legal/product/release approval.
ACCEPTANCE_PUBLICATION_AUTHORIZATION_PATH_PREFIX = (
    "/internal/acceptance-authorizations/"
)
ACCEPTANCE_PUBLICATION_AUTHORIZATION_PATH_PATTERN = re.compile(
    r"^/internal/acceptance-authorizations/(?P<authorization_sha256>[0-9a-f]{64})$"
)


def acceptance_authority_url(gate: str) -> str:
    """Return the one canonical production URL for a live-authority gate."""

    try:
        path = ACCEPTANCE_AUTHORITY_PATH_BY_GATE[gate]
    except KeyError as exc:
        raise ValueError(f"gate {gate!r} has no live acceptance authority") from exc
    return f"{PRODUCTION_API_ORIGIN}{path}"


def acceptance_publication_authorization_url(authorization_sha256: str) -> str:
    """Return the exact public URI for one content-addressed authorization."""

    if re.fullmatch(r"[0-9a-f]{64}", authorization_sha256) is None:
        raise ValueError("authorization_sha256 must be lowercase SHA-256")
    return (
        f"{PRODUCTION_API_ORIGIN}"
        f"{ACCEPTANCE_PUBLICATION_AUTHORIZATION_PATH_PREFIX}"
        f"{authorization_sha256}"
    )


__all__ = [
    "ACCEPTANCE_AUTHORITY_GATE_BY_PATH",
    "ACCEPTANCE_AUTHORITY_PATH_BY_GATE",
    "ACCEPTANCE_AUTHORITY_PUBLIC_PATHS",
    "ACCEPTANCE_PUBLICATION_AUTHORIZATION_PATH_PATTERN",
    "ACCEPTANCE_PUBLICATION_AUTHORIZATION_PATH_PREFIX",
    "PRODUCTION_API_ORIGIN",
    "acceptance_authority_url",
    "acceptance_publication_authorization_url",
]
