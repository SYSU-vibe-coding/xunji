from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DurableJob(Base):
    __tablename__ = "durable_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('MATCH', 'CLASSIFY', 'SENSITIVE')",
            name="ck_durable_jobs_job_type",
        ),
        CheckConstraint(
            "biz_type IN ('LOST', 'FOUND')",
            name="ck_durable_jobs_biz_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_durable_jobs_status",
        ),
        UniqueConstraint(
            "job_type",
            "biz_type",
            "biz_id",
            "biz_version",
            name="uk_durable_job_type_biz_version",
        ),
        Index("idx_durable_jobs_claim", "status", "run_after", "created_at"),
        Index("idx_durable_jobs_biz", "biz_type", "biz_id", "biz_version"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    biz_type: Mapped[str] = mapped_column(String(20), nullable=False)
    biz_id: Mapped[str] = mapped_column(String(26), nullable=False)
    biz_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
