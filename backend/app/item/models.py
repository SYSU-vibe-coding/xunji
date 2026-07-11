from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LostItem(Base):
    __tablename__ = "lost_items"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lost_time_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lost_time_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lost_location: Mapped[str] = mapped_column(String(255), nullable=False)
    subscribe_match: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SEARCHING")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED")
    review_comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_tags: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FoundItem(Base):
    __tablename__ = "found_items"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    found_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    found_location: Mapped[str] = mapped_column(String(255), nullable=False)
    is_sensitive: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    custody_type: Mapped[str] = mapped_column(String(30), nullable=False)
    contact_preference: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED")
    review_comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_tags: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ItemImage(Base):
    __tablename__ = "item_images"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    biz_type: Mapped[str] = mapped_column(String(20), nullable=False)
    biz_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    masked_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class VerifyQuestion(Base):
    __tablename__ = "verify_questions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    found_item_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(String(255), nullable=False)
    answer_keywords: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
