"""Usage counter entity for persistent rate limiting and cost protection."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.entities.user import User


class UsageCounter(Base):
    """Aggregated daily usage metrics per user."""

    __tablename__ = "usage_counters"
    __table_args__ = (PrimaryKeyConstraint("user_id", "day", name="pk_usage_counters"),)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    scans: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gemini_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.0"), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_counters")
