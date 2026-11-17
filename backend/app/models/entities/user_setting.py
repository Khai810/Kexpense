"""User settings model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.entities.user import User


class UserSetting(Base):
    """User preferences, locale, timezone, and consent settings."""

    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint(
            "month_start_day >= 1 AND month_start_day <= 28",
            name="chk_user_settings_month_start_day",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Ho_Chi_Minh", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="vi-VN", nullable=False)
    month_start_day: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    small_number_as_thousand: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_prefs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    consent_ocr_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")
