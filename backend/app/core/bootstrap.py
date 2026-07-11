from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session_factory
from app.db.ulid import generate_ulid
from app.user.models import User


async def ensure_default_admin() -> None:
    if not settings.BOOTSTRAP_ADMIN_ENABLED:
        return
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.phone == settings.ADMIN_PHONE))
        admin = result.scalar_one_or_none()
        if admin is not None:
            if admin.role != "ADMIN":
                raise RuntimeError("ADMIN_PHONE is already assigned to a non-admin user")
            return

        session.add(
            User(
                id=generate_ulid(),
                phone=settings.ADMIN_PHONE,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                nickname=settings.ADMIN_ACCOUNT,
                role="ADMIN",
                cert_status="APPROVED",
                credit_score=100,
                status="ACTIVE",
            )
        )
        await session.commit()
