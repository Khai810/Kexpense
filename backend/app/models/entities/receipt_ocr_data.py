"""Receipt heavy OCR raw and snapshot data entity."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.entities.receipt import Receipt


class ReceiptOCRData(Base, TimestampMixin):
    """Raw and snapshot OCR payload decoupled from primary receipt entity."""

    __tablename__ = "receipt_ocr_data"

    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    raw_ocr: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ocr_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="ocr_data")
