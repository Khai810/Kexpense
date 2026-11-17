"""OCR individual engine run attempt model."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.ocr_job import OCRJob


class OCREngineRun(Base, UUIDPrimaryKeyMixin):
    """Execution metrics and audit details for an individual OCR engine attempt."""

    __tablename__ = "ocr_engine_runs"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_no", name="uq_ocr_engine_runs_job_attempt"),
        Index("ix_ocr_engine_runs_job_id", "job_id"),
    )

    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ocr_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    validation_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    job: Mapped["OCRJob"] = relationship("OCRJob", back_populates="runs")
