from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user.models import User, UserCertRequest


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self._session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User) -> User:
        await self._session.merge(user)
        await self._session.flush()
        return user


class UserCertRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, cert_request: UserCertRequest) -> UserCertRequest:
        self._session.add(cert_request)
        await self._session.flush()
        return cert_request

    async def has_pending(self, user_id: str) -> bool:
        stmt = select(UserCertRequest).where(
            UserCertRequest.user_id == user_id,
            UserCertRequest.review_status == "PENDING",
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_latest_by_user(self, user_id: str) -> UserCertRequest | None:
        stmt = (
            select(UserCertRequest)
            .where(UserCertRequest.user_id == user_id)
            .order_by(UserCertRequest.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
