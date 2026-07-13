"""Platform-authority tenant provisioning routes.

This surface is deliberately separate from customer account RBAC. Possession of an owner/admin
JWT grants no access here; the caller must present the server-only platform provisioning secret.
"""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api.config import settings
from api.services.accounts.store import AccountStore
from api.services.accounts.tenant_provisioning import (
    TenantProvisioningError,
    provision_tenant_owner,
)


router = APIRouter(prefix="/platform", tags=["platform-accounts"])


class PlatformTenantOwnerRequest(BaseModel):
    tenant_id: str = Field(
        ..., min_length=2, max_length=63, pattern=r"^[a-z0-9][a-z0-9_-]{1,62}$"
    )
    email_or_username: str = Field(..., min_length=1, max_length=320)
    api_credential: str = Field(
        ...,
        min_length=49,
        max_length=134,
        pattern=r"^casak_[A-Za-z0-9_-]{43,128}$",
    )
    display_name: Optional[str] = Field(default=None, max_length=200)


class PlatformOwnerResponse(BaseModel):
    account_id: str
    email_or_username: str
    role: str
    tenant_id: str
    status: str
    display_name: Optional[str] = None
    created_at: str
    updated_at: str


class PlatformTenantProvisioningResponse(BaseModel):
    provisioning_id: str
    receipt_id: str
    completed_at: str
    owner: PlatformOwnerResponse


def _account_store(request: Request) -> AccountStore:
    store = getattr(request.app.state, "account_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Platform tenant provisioning is unavailable.",
        )
    return store


@router.post(
    "/tenants",
    response_model=PlatformTenantProvisioningResponse,
)
async def provision_platform_tenant(
    body: PlatformTenantOwnerRequest,
    request: Request,
    response: Response,
    platform_secret: Optional[str] = Header(
        default=None, alias="X-Platform-Provisioning-Secret"
    ),
) -> PlatformTenantProvisioningResponse:
    """Create one new tenant owner through platform authority, never customer RBAC."""
    response.headers["Cache-Control"] = "no-store"
    configured = settings.platform_tenant_provisioning_secret
    supplied = platform_secret or ""
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Platform tenant provisioning is unavailable.",
        )
    if not hmac.compare_digest(
        configured.encode("utf-8"), supplied.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Platform provisioning credentials are invalid.",
        )
    if body.tenant_id == settings.accounts_bootstrap_tenant_id.strip().lower():
        raise HTTPException(
            status_code=409,
            detail="Tenant could not be provisioned.",
        )
    try:
        result = provision_tenant_owner(
            _account_store(request),
            tenant_id=body.tenant_id,
            email_or_username=body.email_or_username,
            api_credential=body.api_credential,
            display_name=body.display_name,
            request_id=str(getattr(request.state, "request_id", "") or "") or None,
        )
    except TenantProvisioningError as exc:
        raise HTTPException(
            status_code=409,
            detail="Tenant could not be provisioned.",
        ) from exc
    return PlatformTenantProvisioningResponse(
        provisioning_id=result.provisioning_id,
        receipt_id=result.receipt_id,
        completed_at=result.completed_at,
        owner=PlatformOwnerResponse(**result.account.to_dict()),
    )
