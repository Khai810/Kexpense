"""Receipt correction audit entity model."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.receipt import Receipt


class ReceiptCorrection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User edits made on AI-extracted values (used to measure edit rate and improve parsers)."""

    __tablename__ = "receipt_corrections"
    __table_args__ = (
        Index("ix_receipt_corrections_receipt_id", "receipt_id"),
        Index("ix_receipt_corrections_field_path", "field_path"),
    )

    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_path: Mapped[str] = mapped_column(String(200), nullable=False)
    ai_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    user_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="corrections")
