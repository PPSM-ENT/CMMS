"""
Work Order models including tasks, labor, materials, and status history.
"""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, Float, Date, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.user import User
    from app.models.inventory import Part


class WorkOrderType(str, enum.Enum):
    """Type of work order."""
    CORRECTIVE = "CORRECTIVE"  # Reactive/breakdown maintenance
    PREVENTIVE = "PREVENTIVE"  # Scheduled PM
    PREDICTIVE = "PREDICTIVE"  # Condition-based
    EMERGENCY = "EMERGENCY"  # Urgent breakdown
    PROJECT = "PROJECT"  # Capital project work
    INSPECTION = "INSPECTION"  # Routine inspection
    CALIBRATION = "CALIBRATION"  # Instrument calibration


class WorkOrderStatus(str, enum.Enum):
    """Work order lifecycle status."""
    DRAFT = "DRAFT"  # Initial creation
    WAITING_APPROVAL = "WAITING_APPROVAL"  # Pending approval
    APPROVED = "APPROVED"  # Approved, ready to schedule
    SCHEDULED = "SCHEDULED"  # Scheduled with date/assignee
    IN_PROGRESS = "IN_PROGRESS"  # Work started
    ON_HOLD = "ON_HOLD"  # Paused (waiting for parts, etc.)
    COMPLETED = "COMPLETED"  # Work finished, pending review
    CLOSED = "CLOSED"  # Fully closed
    CANCELLED = "CANCELLED"  # Cancelled


class WorkOrderPriority(str, enum.Enum):
    """Work order priority level."""
    EMERGENCY = "EMERGENCY"  # P1 - Immediate
    HIGH = "HIGH"  # P2 - Within 24 hours
    MEDIUM = "MEDIUM"  # P3 - Within 1 week
    LOW = "LOW"  # P4 - When convenient
    SCHEDULED = "SCHEDULED"  # P5 - Per schedule


class WorkOrder(Base, AuditMixin, TenantMixin):
    """
    Work Order represents a maintenance task to be performed.
    """

    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wo_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    work_type: Mapped[WorkOrderType] = mapped_column(
        SQLEnum(WorkOrderType), default=WorkOrderType.CORRECTIVE, nullable=False
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        SQLEnum(WorkOrderStatus), default=WorkOrderStatus.DRAFT, nullable=False, index=True
    )
    priority: Mapped[WorkOrderPriority] = mapped_column(
        SQLEnum(WorkOrderPriority), default=WorkOrderPriority.MEDIUM, nullable=False
    )

    # Asset and location
    # Single asset_id is kept for backward compatibility and primary asset
    asset_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=True, index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True, index=True
    )

    # Multiple assets (for multi-asset work orders)
    multi_assets: Mapped[List["WorkOrderAsset"]] = relationship(
        "WorkOrderAsset", back_populates="work_order", cascade="all, delete-orphan"
    )

    # Assignment
    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    assigned_team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user_groups.id"), nullable=True, index=True
    )

    # Scheduling
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Actual times
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Estimates
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Actuals (computed from transactions)
    actual_labor_hours: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    actual_labor_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    actual_material_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    # Downtime tracking
    downtime_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    asset_was_down: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # PM link
    pm_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("preventive_maintenance.id"), nullable=True, index=True
    )

    # Parent work order (for child WOs)
    parent_wo_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True
    )

    # Failure tracking
    failure_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_remedy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Completion
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Custom fields
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[asset_id])
    location: Mapped[Optional["Location"]] = relationship("Location", foreign_keys=[location_id])
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    completed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[completed_by_id])
    assigned_group: Mapped[Optional["UserGroup"]] = relationship("UserGroup", back_populates="work_orders")
    parent_wo: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", remote_side="WorkOrder.id", back_populates="child_work_orders"
    )
    child_work_orders: Mapped[List["WorkOrder"]] = relationship("WorkOrder", back_populates="parent_wo")
    tasks: Mapped[List["WorkOrderTask"]] = relationship(
        "WorkOrderTask", back_populates="work_order", cascade="all, delete-orphan"
    )
    labor_transactions: Mapped[List["LaborTransaction"]] = relationship(
        "LaborTransaction", back_populates="work_order", cascade="all, delete-orphan"
    )
    material_transactions: Mapped[List["MaterialTransaction"]] = relationship(
        "MaterialTransaction", back_populates="work_order", cascade="all, delete-orphan"
    )
    comments: Mapped[List["WorkOrderComment"]] = relationship(
        "WorkOrderComment", back_populates="work_order", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["WorkOrderStatusHistory"]] = relationship(
        "WorkOrderStatusHistory", back_populates="work_order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorkOrder(id={self.id}, wo_number='{self.wo_number}', status='{self.status}')>"

    def calculate_totals(self) -> None:
        """Recalculate total costs from transactions."""
        self.actual_labor_hours = sum(t.hours for t in self.labor_transactions)
        self.actual_labor_cost = sum(t.total_cost for t in self.labor_transactions)
        self.actual_material_cost = sum(t.total_cost for t in self.material_transactions)
        self.total_cost = self.actual_labor_cost + self.actual_material_cost


class WorkOrderTask(Base, AuditMixin):
    """
    Individual tasks/operations within a work order.
    """

    __tablename__ = "work_order_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Task type for checklists
    task_type: Mapped[str] = mapped_column(String(50), default="TASK", nullable=False)  # TASK, CHECKBOX, READING, SIGNATURE

    # Completion
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # For reading tasks
    reading_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Time estimates
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="tasks")
    completed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[completed_by_id])

    def __repr__(self) -> str:
        return f"<WorkOrderTask(wo_id={self.work_order_id}, seq={self.sequence})>"


class LaborTransaction(Base, AuditMixin, TenantMixin):
    """
    Labor time recorded against work orders.
    """

    __tablename__ = "labor_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # Time
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hours: Mapped[float] = mapped_column(Float, nullable=False)

    # Labor type
    labor_type: Mapped[str] = mapped_column(String(50), default="REGULAR", nullable=False)  # REGULAR, OVERTIME, DOUBLE_TIME
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Work classification
    craft: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Electrician, Mechanic, etc.
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="labor_transactions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<LaborTransaction(wo_id={self.work_order_id}, hours={self.hours})>"


class MaterialTransaction(Base, AuditMixin, TenantMixin):
    """
    Materials/parts used on work orders.
    """

    __tablename__ = "material_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parts.id"), nullable=False, index=True
    )

    # Quantity and cost
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Storeroom issued from
    storeroom_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("storerooms.id"), nullable=True
    )

    # Transaction type
    transaction_type: Mapped[str] = mapped_column(String(50), default="ISSUE", nullable=False)  # ISSUE, RETURN
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="material_transactions")
    part: Mapped["Part"] = relationship("Part", foreign_keys=[part_id])

    def __repr__(self) -> str:
        return f"<MaterialTransaction(wo_id={self.work_order_id}, part_id={self.part_id})>"


class WorkOrderComment(Base, AuditMixin):
    """
    Comments/notes on work orders for communication.
    """

    __tablename__ = "work_order_comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Internal vs external visibility

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="comments")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<WorkOrderComment(wo_id={self.work_order_id}, user_id={self.user_id})>"


class WorkOrderStatusHistory(Base, AuditMixin):
    """
    Audit trail of work order status changes.
    """

    __tablename__ = "work_order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="status_history")
    changed_by: Mapped["User"] = relationship("User", foreign_keys=[changed_by_id])

    def __repr__(self) -> str:
        return f"<WorkOrderStatusHistory(wo_id={self.work_order_id}, {self.from_status}->{self.to_status})>"


# Import Location for type hints
from app.models.location import Location
