"""Merchant entity model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.category import Category
    from backend.app.models.entities.receipt import Receipt
    from backend.app.models.entities.user import User


class Merchant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized merchant entity."""

    __tablename__ = "merchants"
    __table_args__ = (
        UniqueConstraint("user_id", "name_normalized", name="uq_merchants_user_normalized"),
        Index(
            "uq_merchants_user_tax_code",
            "user_id",
            "tax_code",
            unique=True,
            postgresql_where=text("tax_code IS NOT NULL"),
        ),
        Index("ix_merchants_user_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_category_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="merchants")
    default_category: Mapped["Category | None"] = relationship("Category")
    receipts: Mapped[list["Receipt"]] = relationship("Receipt", back_populates="merchant")
