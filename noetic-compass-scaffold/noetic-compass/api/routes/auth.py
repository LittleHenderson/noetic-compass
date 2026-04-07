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

    token = create_token(sub=body.username, exp_minutes=settings.jwt_expiry_minutes)
    return TokenResponse(token=token, expires_in_minutes=settings.jwt_expiry_minutes)
