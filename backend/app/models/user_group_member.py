from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.user_group import UserGroup
    from app.models.user import User


class UserGroupMember(Base, AuditMixin):
    """
    Association table for user group membership.
    Note: No TenantMixin - organization is derived from the group.
    """

    __tablename__ = "user_group_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optional: role within the group
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Optional: sequence or priority
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    group: Mapped["UserGroup"] = relationship("UserGroup", back_populates="members", foreign_keys=[group_id])
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<UserGroupMember(group_id={self.group_id}, user_id={self.user_id})>"
