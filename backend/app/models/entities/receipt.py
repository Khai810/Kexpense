"""Receipt entity model."""

from datetime import date, datetime, time
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.merchant import Merchant
    from backend.app.models.entities.receipt_correction import ReceiptCorrection
    from backend.app.models.entities.receipt_image import ReceiptImage
    from backend.app.models.entities.receipt_item import ReceiptItem
    from backend.app.models.entities.receipt_ocr_data import ReceiptOCRData
    from backend.app.models.entities.user import User


class Receipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Receipt / Expense entity (scanned from camera/file or manually entered)."""

    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="chk_receipts_total_amount_non_negative"),
        CheckConstraint("discount >= 0", name="chk_receipts_discount_non_negative"),
        CheckConstraint("service_charge >= 0", name="chk_receipts_service_charge_non_negative"),
        CheckConstraint("subtotal IS NULL OR subtotal >= 0", name="chk_receipts_subtotal_non_negative"),
        CheckConstraint("tax_amount IS NULL OR tax_amount >= 0", name="chk_receipts_tax_amount_non_negative"),
        CheckConstraint(
            "source IN ('camera', 'upload', 'manual', 'recurring')",
            name="chk_receipts_source",
        ),
        CheckConstraint(
            "engine_used IN ('google_vision', 'gemini_fallback', 'manual')",
            name="chk_receipts_engine_used",
        ),
        CheckConstraint(
            "status IN ('draft', 'confirmed')",
            name="chk_receipts_status",
        ),
        CheckConstraint(
            "source != 'manual' OR (engine_used = 'manual' AND content_hash IS NULL AND validation_status IS NULL AND needs_review = false)",
            name="chk_receipts_manual_source",
        ),
        Index("ix_receipts_user_date", "user_id", "invoice_date"),
        Index("ix_receipts_user_hash", "user_id", "content_hash"),
        Index("ix_receipts_user_merchant", "user_id", "merchant_id"),
        Index("ix_receipts_user_source", "user_id", "source"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    merchant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    merchant_tax_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    invoice_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)

    # Monetary amounts stored strictly as integer VND (ADR-004)
    subtotal: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    discount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    service_charge: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="camera", nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_job_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    engine_used: Mapped[str] = mapped_column(String(50), default="google_vision", nullable=False)
    categorizer_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    recurring_rule_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="receipts")
    merchant: Mapped["Merchant | None"] = relationship("Merchant", back_populates="receipts")
    items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptItem.line_no",
    )
    images: Mapped[list["ReceiptImage"]] = relationship(
        "ReceiptImage",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
    ocr_data: Mapped["ReceiptOCRData | None"] = relationship(
        "ReceiptOCRData",
        back_populates="receipt",
        uselist=False,
        cascade="all, delete-orphan",
    )
    corrections: Mapped[list["ReceiptCorrection"]] = relationship(
        "ReceiptCorrection",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
