from sqlalchemy import or_, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session_factory
from app.db.ulid import generate_ulid
from app.user.models import User


async def ensure_default_admin() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User)
            .where(or_(User.phone == settings.ADMIN_PHONE, User.nickname == settings.ADMIN_ACCOUNT))
            .limit(1)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                id=generate_ulid(),
                phone=settings.ADMIN_PHONE,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                nickname=settings.ADMIN_ACCOUNT,
                role="ADMIN",
                cert_status="APPROVED",
                credit_score=100,
                status="ACTIVE",
            )
            session.add(admin)
        else:
            admin.nickname = settings.ADMIN_ACCOUNT
            admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
            admin.role = "ADMIN"
            admin.cert_status = "APPROVED"
            admin.status = "ACTIVE"
        await session.commit()
