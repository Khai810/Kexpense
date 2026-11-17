"""Receipt line item entity model."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.category import Category
    from backend.app.models.entities.receipt import Receipt


class ReceiptItem(Base, UUIDPrimaryKeyMixin):
    """Line item belonging to a receipt."""

    __tablename__ = "receipt_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_receipt_items_quantity_positive"),
        CheckConstraint("line_total >= 0", name="chk_receipt_items_line_total_non_negative"),
        CheckConstraint("allocated_amount >= 0", name="chk_receipt_items_allocated_amount_non_negative"),
        CheckConstraint("discount >= 0", name="chk_receipt_items_discount_non_negative"),
        CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0",
            name="chk_receipt_items_unit_price_non_negative",
        ),
        Index("ix_receipt_items_receipt_id", "receipt_id"),
        Index("ix_receipt_items_category_id", "category_id"),
    )

    receipt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("1.0"), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Unit price and line total in integer VND
    unit_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    line_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # ADR-010: Allocated actual expenditure share in integer VND (sum(allocated_amount) == receipt.total_amount)
    allocated_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    category_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="items")
    category: Mapped["Category | None"] = relationship("Category", back_populates="receipt_items")
