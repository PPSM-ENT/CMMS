"""
Audit Log model for tracking all data changes.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """
    Audit log tracks all significant data changes across the system.
    This is a comprehensive audit trail for compliance and troubleshooting.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # What entity was affected
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., "Asset", "User", "WorkOrder"
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Human-readable name at time of action

    # What action was taken
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, STATUS_CHANGE

    # Who performed the action
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Denormalized for history
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Denormalized for history

    # Organization context
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True, index=True
    )

    # Change details
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Specific field that changed
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Previous value (JSON for complex types)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # New value (JSON for complex types)

    # Full snapshot of changes (for UPDATE actions with multiple field changes)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Context and metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Human-readable description
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, entity={self.entity_type}:{self.entity_id}, action={self.action})>"
