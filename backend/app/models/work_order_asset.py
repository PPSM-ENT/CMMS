from typing import Optional
from sqlalchemy import Integer, String, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkOrderAsset(Base):
    """
    Association table for multi-asset work orders.
    """

    __tablename__ = "work_order_assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=False, index=True
    )
    # Optional: sequence or priority for the asset in the work order
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Optional: specific instructions for this asset
    instructions: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="multi_assets")
    asset: Mapped["Asset"] = relationship("Asset")

    def __repr__(self) -> str:
        return f"<WorkOrderAsset(wo_id={self.work_order_id}, asset_id={self.asset_id})>"
