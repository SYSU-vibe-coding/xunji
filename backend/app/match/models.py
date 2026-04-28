from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    lost_item_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    found_item_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    image_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    text_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    location_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    time_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, index=True
    )
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
