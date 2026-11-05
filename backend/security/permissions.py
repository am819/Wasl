"""
RBAC permission helpers.

Provides FastAPI dependencies that enforce role-based access control.
Every protected endpoint imports one of the `require_*` dependencies.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security.jwt_utils import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _get_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Extract the raw Bearer token from the Authorization header."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Missing or invalid token"},
        )
    return credentials.credentials


def get_current_user(
    token: str = Depends(_get_token),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT, load user from DB. Raises 401 on any token problem."""
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Access token has expired"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_INVALID",
                "message": "Token is invalid or tampered",
            },
        )

    user_id: int = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "User not found"},
        )
    return user


# ---------------------------------------------------------------------------
# Role-specific dependencies — import these in routers
# ---------------------------------------------------------------------------

def _require_role(required: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"This endpoint requires role '{required}'",
                },
            )
        return user
    dependency.__name__ = f"require_{required}"
    return dependency


require_merchant = _require_role("merchant")
require_driver = _require_role("driver")
require_admin = _require_role("admin")
