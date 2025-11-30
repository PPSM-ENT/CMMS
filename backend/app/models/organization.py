"""
Organization model for multi-tenancy support.
"""
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.location import Location
    from app.models.asset import Asset
    from app.models.user_group import UserGroup


class Organization(Base, TimestampMixin):
    """
    Organization represents a tenant in the CMMS system.
    All data is isolated by organization for multi-tenancy.
    """

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Settings stored as JSON
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    date_format: Mapped[str] = mapped_column(String(20), default="YYYY-MM-DD", nullable=False)

    # Contact information
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    locations: Mapped[List["Location"]] = relationship("Location", back_populates="organization")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="organization")
    groups: Mapped[List["UserGroup"]] = relationship("UserGroup", back_populates="organization")  # type: ignore

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, code='{self.code}', name='{self.name}')>"
