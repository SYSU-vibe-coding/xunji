import asyncio
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.core.auth import create_access_token
from app.core.object_storage import get_object_storage
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.user.models import User
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# In-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    import app.admin.models
    import app.claim.models
    import app.credit.models
    import app.item.models
    import app.job.models
    import app.match.models
    import app.notification.models
    import app.operation_log.models
    import app.user.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as s:
        yield s


@pytest.fixture
async def seeded_users(session: AsyncSession) -> None:
    session.add_all(
        [
            User(
                id="01TESTUSER000000000000001",
                phone="13810000001",
                password_hash="",
                nickname="测试用户",
                role="USER",
                cert_status="UNVERIFIED",
                credit_score=100,
                status="ACTIVE",
            ),
            User(
                id="01TESTADMIN00000000000001",
                phone="13810000002",
                password_hash="",
                nickname="测试管理员",
                role="ADMIN",
                cert_status="APPROVED",
                credit_score=100,
                status="ACTIVE",
            ),
            User(
                id="01TESTSTAFF00000000000001",
                phone="13810000003",
                password_hash="",
                nickname="测试员工",
                role="STAFF",
                cert_status="APPROVED",
                credit_score=100,
                status="ACTIVE",
            ),
        ]
    )
    await session.commit()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def user_token() -> str:
    """JWT for a test user."""
    return create_access_token(
        {"sub": "01TESTUSER000000000000001", "role": "USER", "status": "ACTIVE"}
    )


@pytest.fixture
def admin_token() -> str:
    """JWT for a test admin."""
    return create_access_token(
        {"sub": "01TESTADMIN00000000000001", "role": "ADMIN", "status": "ACTIVE"}
    )


@pytest.fixture
def staff_token() -> str:
    """JWT for a test staff user."""
    return create_access_token(
        {"sub": "01TESTSTAFF00000000000001", "role": "STAFF", "status": "ACTIVE"}
    )


@pytest.fixture
def auth_headers(seeded_users: None, user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(seeded_users: None, admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def staff_headers(seeded_users: None, staff_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {staff_token}"}


@pytest.fixture(autouse=True)
def mock_minio(monkeypatch):
    """Keep all object-storage calls deterministic and off the network."""
    storage = get_object_storage()
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.stat_object.return_value = SimpleNamespace(size=128)
    client.presigned_get_object.side_effect = (
        lambda bucket, key, **kwargs: f"http://minio:9000/{bucket}/{key}?signature=ai-test"
    )
    signer = MagicMock()
    signer.presigned_get_object.side_effect = (
        lambda bucket, key, **kwargs: f"https://signed.test/{bucket}/{key}?signature=test"
    )
    monkeypatch.setattr(storage, "_client", client)
    monkeypatch.setattr(storage, "_signing_client", signer)
    return SimpleNamespace(storage=storage, client=client, signer=signer)
