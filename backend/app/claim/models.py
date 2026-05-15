from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimRequest(Base):
    __tablename__ = "claim_requests"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    match_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    found_item_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    claimant_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    verify_level: Mapped[str] = mapped_column(String(20), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    reject_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proof_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    appeal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ClaimAnswer(Base):
    __tablename__ = "claim_answers"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(26), nullable=False)
    question_text: Mapped[str] = mapped_column(String(255), nullable=False)
    answer_text: Mapped[str] = mapped_column(String(255), nullable=False)
    match_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class HandoverRecord(Base):
    __tablename__ = "handover_records"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(26), nullable=False, unique=True, index=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    handover_location: Mapped[str] = mapped_column(String(255), nullable=False)
    handover_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    owner_confirmed: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    finder_confirmed: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
