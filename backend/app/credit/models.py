from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CreditLog(Base):
    __tablename__ = "credit_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "biz_type", "biz_id", "reason_code", name="uk_credit_dedup"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    delta_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reason_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    biz_type: Mapped[str] = mapped_column(String(30), nullable=False)
    biz_id: Mapped[str] = mapped_column(String(26), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
