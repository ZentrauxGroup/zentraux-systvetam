"""
SYSTVETAM — Auth Router
Zentraux Group LLC

JWT token issuance endpoint. Phase 1: shared secret auth.
Phase 2+: per-user bcrypt hashes or SSO integration.

Endpoints:
  POST  /auth/token    Issue JWT (username + password)
  GET   /auth/me       Verify token + return current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from dispatch.services.auth_service import (
    Role,
    create_access_token,
    get_current_user,
    verify_credentials,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    """POST /auth/token request body."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=200)


class TokenResponse(BaseModel):
    """POST /auth/token response."""
    access_token: str
    token_type: str = "bearer"
    agent_id: str
    role: str
    display_name: str


class MeResponse(BaseModel):
    """GET /auth/me response — decoded token payload."""
    agent_id: str
    role: str
    display_name: str


# ---------------------------------------------------------------------------
# POST /auth/token — Issue JWT
# ---------------------------------------------------------------------------

@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest):
    """
    Authenticate and receive a JWT.

    Phase 1: username + shared secret (JWT_SECRET as password).
    Phase 2+: per-user bcrypt or SSO callback.

    Valid usernames: levi, agent-zero, viewer
    """
    operator = verify_credentials(body.username, body.password)

    if operator is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        agent_id=operator["agent_id"],
        role=operator["role"],
        display_name=operator["display_name"],
    )

    return TokenResponse(
        access_token=token,
        agent_id=operator["agent_id"],
        role=operator["role"].value,
        display_name=operator["display_name"],
    )


# ---------------------------------------------------------------------------
# GET /auth/me — Verify token + return user
# ---------------------------------------------------------------------------

@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)):
    """
    Verify the current JWT and return the decoded identity.
    Used by Tower Dashboard on connect to confirm auth state.
    """
    return MeResponse(
        agent_id=user["sub"],
        role=user["role"],
        display_name=user["name"],
    )
