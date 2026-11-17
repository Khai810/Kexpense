"""Receipt image entity model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.receipt import Receipt


class ReceiptImage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Image associated with a receipt (original, preprocessed, or attachment)."""

    __tablename__ = "receipt_images"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('original', 'processed', 'attachment')",
            name="chk_receipt_images_kind",
        ),
        Index(
            "uq_receipt_images_single_original",
            "receipt_id",
            unique=True,
            postgresql_where=text("kind = 'original'"),
        ),
        Index("ix_receipt_images_receipt_id", "receipt_id"),
    )

    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="images")
