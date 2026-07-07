import asyncio
from logging.config import fileConfig

from alembic import context

# Import ALL models here so Alembic sees them for autogenerate
from app.admin.models import Announcement, Report  # noqa: F401
from app.claim.models import ClaimAnswer, ClaimRequest, HandoverRecord  # noqa: F401
from app.core.config import settings
from app.credit.models import CreditLog  # noqa: F401
from app.db.base import Base
from app.item.models import FoundItem, ItemImage, LostItem, VerifyQuestion  # noqa: F401
from app.match.models import MatchResult  # noqa: F401
from app.notification.models import Notification  # noqa: F401
from app.operation_log.models import OperationLog  # noqa: F401
from app.user.models import User, UserCertRequest  # noqa: F401
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return settings.DATABASE_URL_OVERRIDE or settings.database_url


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(_database_url())
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
