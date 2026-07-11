from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.user.models import User, UserCertRequest


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, user_id: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self._session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_account(self, account: str) -> User | None:
        if account != settings.ADMIN_ACCOUNT:
            return None
        user = await self.get_by_phone(settings.ADMIN_PHONE)
        return user if user is not None and user.role == "ADMIN" else None

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User) -> User:
        await self._session.merge(user)
        await self._session.flush()
        return user

    async def list_with_filter(
        self,
        *,
        role: str | None,
        status: str | None,
        keyword: str | None,
        offset: int,
        limit: int,
        user_id: str | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)
        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        if status:
            stmt = stmt.where(User.status == status)
            count_stmt = count_stmt.where(User.status == status)
        if user_id:
            stmt = stmt.where(User.id == user_id)
            count_stmt = count_stmt.where(User.id == user_id)
        if keyword:
            pattern = f"%{keyword}%"
            cond = or_(
                User.phone.like(pattern), User.nickname.like(pattern), User.campus_id.like(pattern)
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_active_ids(
        self, *, role: str | None = None, after_id: str | None = None, limit: int = 500
    ) -> list[str]:
        stmt = select(User.id).where(User.status == "ACTIVE")
        if role is not None:
            stmt = stmt.where(User.role == role)
        if after_id is not None:
            stmt = stmt.where(User.id > after_id)
        result = await self._session.execute(stmt.order_by(User.id).limit(limit))
        return list(result.scalars().all())


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
            .order_by(UserCertRequest.created_at.desc(), UserCertRequest.id.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, cert_id: str) -> UserCertRequest | None:
        result = await self._session.execute(
            select(UserCertRequest).where(UserCertRequest.id == cert_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, cert_id: str) -> UserCertRequest | None:
        result = await self._session.execute(
            select(UserCertRequest).where(UserCertRequest.id == cert_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_with_filter(
        self, *, review_status: str | None, offset: int, limit: int
    ) -> tuple[list[UserCertRequest], int]:
        stmt = select(UserCertRequest)
        count_stmt = select(func.count()).select_from(UserCertRequest)
        if review_status:
            stmt = stmt.where(UserCertRequest.review_status == review_status)
            count_stmt = count_stmt.where(UserCertRequest.review_status == review_status)
        stmt = stmt.order_by(UserCertRequest.created_at.desc()).offset(offset).limit(limit)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def update(self, cert_request: UserCertRequest) -> UserCertRequest:
        await self._session.merge(cert_request)
        await self._session.flush()
        return cert_request

    async def transition_pending(
        self,
        *,
        cert_id: str,
        review_status: str,
        review_comment: str | None,
        reviewer_id: str,
        reviewed_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(UserCertRequest)
            .where(
                UserCertRequest.id == cert_id,
                UserCertRequest.review_status == "PENDING",
            )
            .values(
                review_status=review_status,
                review_comment=review_comment,
                reviewer_id=reviewer_id,
                reviewed_at=reviewed_at,
                updated_at=func.now(),
            )
        )
        return bool(getattr(result, "rowcount", 0))
