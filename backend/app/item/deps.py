from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.item.service import ItemService


async def get_item_service(session: AsyncSession = Depends(get_session)) -> ItemService:
    return ItemService(session)
