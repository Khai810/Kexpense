"""User model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.entities.audit_log import AuditLog
    from backend.app.models.entities.category import Category
    from backend.app.models.entities.category_rule import CategoryRule
    from backend.app.models.entities.idempotency_key import IdempotencyKey
    from backend.app.models.entities.merchant import Merchant
    from backend.app.models.entities.ocr_job import OCRJob
    from backend.app.models.entities.receipt import Receipt
    from backend.app.models.entities.session import Session
    from backend.app.models.entities.usage_counter import UsageCounter
    from backend.app.models.entities.user_setting import UserSetting


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    settings: Mapped["UserSetting"] = relationship(
        "UserSetting",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    receipts: Mapped[list["Receipt"]] = relationship(
        "Receipt",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    merchants: Mapped[list["Merchant"]] = relationship(
        "Merchant",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    category_rules: Mapped[list["CategoryRule"]] = relationship(
        "CategoryRule",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ocr_jobs: Mapped[list["OCRJob"]] = relationship(
        "OCRJob",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    usage_counters: Mapped[list["UsageCounter"]] = relationship(
        "UsageCounter",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    idempotency_keys: Mapped[list["IdempotencyKey"]] = relationship(
        "IdempotencyKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
