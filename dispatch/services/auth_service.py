"""
SYSTVETAM — Auth Service
Zentraux Group LLC

JWT token issuance and verification.
Three access levels from Engineering Directive v1.0 Ticket 06:

  SUPERUSER (AGT-001 — Levi): Full access. All gates. All receipts. All crew.
  OPERATOR:  Task creation + dept view. No gate approval.
  VIEWER:    Read-only. Receipt vault + status. No actions.

Every gate approval endpoint requires role=SUPERUSER.
This enforces escalation doctrine at the API layer.
"""

import enum
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from dispatch.config import settings

logger = logging.getLogger("dispatch.auth")

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class Role(str, enum.Enum):
    SUPERUSER = "SUPERUSER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


# ---------------------------------------------------------------------------
# Hardcoded operator credentials (Phase 1 — no external IdP yet)
# In production this becomes SSO / API key lookup against DB.
# ---------------------------------------------------------------------------

OPERATOR_CREDENTIALS: dict[str, dict[str, Any]] = {
    "levi": {
        "password_hash": None,  # set via env or first-boot
        "agent_id": "AGT-001",
        "role": Role.SUPERUSER,
        "display_name": "Levi C. Haynes",
    },
    "agent-zero": {
        "password_hash": None,
        "agent_id": "AGT-016",
        "role": Role.OPERATOR,
        "display_name": "Agent Zero",
    },
    "viewer": {
        "password_hash": None,
        "agent_id": "VIEWER-001",
        "role": Role.VIEWER,
        "display_name": "Read-Only Viewer",
    },
}


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(
    agent_id: str,
    role: Role,
    display_name: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Issue a signed JWT containing agent identity and role.
    Token payload:
      sub:   agent_id (e.g., AGT-001)
      role:  SUPERUSER | OPERATOR | VIEWER
      name:  display name
      iat:   issued at
      exp:   expiration
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES))

    payload = {
        "sub": agent_id,
        "role": role.value,
        "name": display_name,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT. Raises HTTPException on failure.
    Returns the full payload dict.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI Dependencies — inject into protected routes
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """
    Dependency: extracts and validates JWT from Authorization header.
    Returns the decoded payload with agent_id, role, and name.

    Usage:
        @router.get("/protected")
        async def protected(user: dict = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_token(credentials.credentials)


async def require_superuser(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Dependency: requires SUPERUSER role (AGT-001 — Levi).
    Use on gate approval endpoints to enforce escalation doctrine.

    Usage:
        @router.post("/gates/{id}/approve")
        async def approve(user: dict = Depends(require_superuser)):
            ...
    """
    if user.get("role") != Role.SUPERUSER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This action requires SUPERUSER authority. "
                "Gate approvals are restricted to AGT-001 per escalation doctrine."
            ),
        )
    return user


async def require_operator_or_above(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Dependency: requires OPERATOR or SUPERUSER role.
    VIEWER cannot create tasks or trigger transitions.
    """
    if user.get("role") not in (Role.SUPERUSER.value, Role.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires OPERATOR or SUPERUSER role.",
        )
    return user


# ---------------------------------------------------------------------------
# Credential verification (Phase 1 — simple password check)
# ---------------------------------------------------------------------------

def verify_credentials(username: str, password: str) -> dict[str, Any] | None:
    """
    Verify username/password against operator credentials.
    Phase 1: password is checked against JWT_SECRET as a shared secret.
    Phase 2+: replace with bcrypt hashes or SSO callback.

    Returns operator dict if valid, None if invalid.
    """
    operator = OPERATOR_CREDENTIALS.get(username.lower())
    if operator is None:
        return None

    # Phase 1: use JWT_SECRET as the shared password for all operators.
    # This is temporary — replaced by per-user hashes in Phase 2.
    if password == settings.JWT_SECRET:
        return operator

    return None
