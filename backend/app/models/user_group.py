from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Boolean, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class UserGroup(Base, AuditMixin, TenantMixin):
    """
    User group for organizing users and assigning work.
    """

    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="groups")  # type: ignore
    members: Mapped[List["UserGroupMember"]] = relationship("UserGroupMember", back_populates="group", cascade="all, delete-orphan")  # type: ignore
    work_orders: Mapped[List["WorkOrder"]] = relationship("WorkOrder", back_populates="assigned_group")  # type: ignore

    def __repr__(self) -> str:
        return f"<UserGroup(id={self.id}, name='{self.name}')>"
