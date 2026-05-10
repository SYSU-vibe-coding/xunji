from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BizError, ErrorCode
from app.core.config import settings
from app.db.session import get_session
from app.user.repository import UserRepository

if TYPE_CHECKING:
    from app.user.schemas import CurrentUser

security_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: dict[str, Any]) -> str:
    """Create a JWT token with 7-day expiry."""
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode JWT; raises BizError(40002) on failure."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as exc:
        raise BizError(ErrorCode.UNAUTHORIZED) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    """FastAPI dependency: extract JWT and verify the user is active in DB."""
    from app.user.schemas import CurrentUser as _CurrentUser

    if credentials is None:
        raise BizError(ErrorCode.UNAUTHORIZED)
    payload = decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise BizError(ErrorCode.UNAUTHORIZED)

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise BizError(ErrorCode.UNAUTHORIZED)
    if user.status != "ACTIVE":
        raise BizError(ErrorCode.USER_DISABLED)

    return _CurrentUser(id=user.id, role=user.role, status=user.status)


def require_roles(*roles: str) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    """Return a dependency that checks CurrentUser.role is in the given set."""

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise BizError(ErrorCode.FORBIDDEN)
        if user.status != "ACTIVE":
            raise BizError(ErrorCode.USER_DISABLED)
        return user

    return _check
