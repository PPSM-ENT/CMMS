"""
Scheduler control flags for pausing background generators.
"""
from sqlalchemy import Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SchedulerControl(Base):
    """
    Per-organization scheduler control to pause WO/PM or cycle-count generation.
    """

    __tablename__ = "scheduler_controls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), unique=True, nullable=False)

    pause_pm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pause_cycle_counts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<SchedulerControl(org={self.organization_id}, pm={self.pause_pm}, cc={self.pause_cycle_counts})>"
