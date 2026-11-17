"""OCR scan job entity model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.ocr_engine_run import OCREngineRun
    from backend.app.models.entities.user import User


class OCRJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Parent job representing a receipt scanning session."""

    __tablename__ = "ocr_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'needs_review', 'failed')",
            name="chk_ocr_jobs_status",
        ),
        Index("ix_ocr_jobs_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    final_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ocr_jobs")
    runs: Mapped[list["OCREngineRun"]] = relationship(
        "OCREngineRun",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="OCREngineRun.attempt_no",
    )
