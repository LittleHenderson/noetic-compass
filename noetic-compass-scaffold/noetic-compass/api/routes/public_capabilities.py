"""Secret-free deployment capabilities used before Atlas account auth renders."""

from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from api.config import settings
from api.middleware.auth import PUBLIC_ACCOUNT_CAPABILITIES_PATH

router = APIRouter(tags=["public-capabilities"])

_SECRET_FREE_JSON_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Content-Type-Options": "nosniff",
}


class PublicAccountCapabilities(BaseModel):
    """The complete public account-mode handshake contract.

    Keep this response intentionally narrow.  Atlas needs only the deployment's
    account-mode boolean before it decides whether a customer login state may
    render; provider names, endpoints, credentials, and storage details do not
    belong on this unauthenticated surface.
    """

    model_config = ConfigDict(extra="forbid")

    accounts_enabled: bool


@router.get(
    PUBLIC_ACCOUNT_CAPABILITIES_PATH,
    response_model=PublicAccountCapabilities,
)
async def get_public_capabilities(response: Response) -> PublicAccountCapabilities:
    """Return the exact boolean Atlas must match before enabling account auth."""

    response.headers.update(_SECRET_FREE_JSON_HEADERS)
    return PublicAccountCapabilities(accounts_enabled=settings.accounts_enabled)
