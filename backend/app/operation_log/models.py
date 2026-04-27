from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    operator_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    operator_role: Mapped[str] = mapped_column(String(20), nullable=False)
    biz_type: Mapped[str] = mapped_column(String(30), nullable=False)
    biz_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
