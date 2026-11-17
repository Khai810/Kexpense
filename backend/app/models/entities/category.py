"""Expense category model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.category_rule import CategoryRule
    from backend.app.models.entities.receipt_item import ReceiptItem
    from backend.app.models.entities.user import User


class Category(Base, UUIDPrimaryKeyMixin):
    """Expense categories (system defaults and user customized)."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_categories_user_slug"),)

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="categories")
    receipt_items: Mapped[list["ReceiptItem"]] = relationship("ReceiptItem", back_populates="category")
    rules: Mapped[list["CategoryRule"]] = relationship(
        "CategoryRule",
        back_populates="category",
        cascade="all, delete-orphan",
    )
