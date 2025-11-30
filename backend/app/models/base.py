"""
Base model with common fields and mixins.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

from app.core.database import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin(TimestampMixin):
    """Mixin for audit fields including created_by and updated_by."""

    @declared_attr
    def created_by_id(cls) -> Mapped[Optional[int]]:
        return mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    @declared_attr
    def updated_by_id(cls) -> Mapped[Optional[int]]:
        return mapped_column(Integer, ForeignKey("users.id"), nullable=True)


class TenantMixin:
    """Mixin for multi-tenancy support via organization_id."""

    @declared_attr
    def organization_id(cls) -> Mapped[int]:
        return mapped_column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
