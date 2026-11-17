"""Category rule entity for rule-first auto-categorization."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.category import Category
    from backend.app.models.entities.user import User


class CategoryRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Rule mapping merchants or keywords to a specific category."""

    __tablename__ = "category_rules"
    __table_args__ = (
        CheckConstraint(
            "match_type IN ('merchant', 'keyword')",
            name="chk_category_rules_match_type",
        ),
        CheckConstraint(
            "source IN ('seed', 'learned', 'user')",
            name="chk_category_rules_source",
        ),
        UniqueConstraint(
            "user_id",
            "match_type",
            "pattern",
            name="uq_category_rules_user_match_pattern",
        ),
        Index("ix_category_rules_user_priority", "user_id", "priority"),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    pattern: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="category_rules")
    category: Mapped["Category"] = relationship("Category", back_populates="rules")
