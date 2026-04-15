"""Token generation endpoint for dashboard login."""

from pydantic import BaseModel
from fastapi import APIRouter

from api.middleware.auth import create_token

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    username: str = "dashboard-user"


class TokenResponse(BaseModel):
    token: str
    expires_in_minutes: int


@router.post("/auth/token", response_model=TokenResponse)
async def generate_token(body: TokenRequest) -> TokenResponse:
    """Issue a JWT signed with the server's secret. For dev/demo use."""
    from api.config import settings

    normalized = body.username.strip() or "dashboard-user"
    api_key = f"dashboard:{normalized.lower()}"
    token = create_token(sub=normalized, api_key=api_key, exp_minutes=settings.jwt_expiry_minutes)
    return TokenResponse(token=token, expires_in_minutes=settings.jwt_expiry_minutes)
