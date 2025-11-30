"""
Preventive Maintenance models including schedules and job plans.
"""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, Float, Date, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin

if TYPE_CHECKING:
    from app.models.asset import Asset, Meter
    from app.models.user import User
    from app.models.inventory import Part


class PMFrequencyUnit(str, enum.Enum):
    """Units for time-based PM scheduling."""
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


class PMTriggerType(str, enum.Enum):
    """What triggers PM work order generation."""
    TIME = "TIME"  # Calendar-based
    METER = "METER"  # Usage-based
    CONDITION = "CONDITION"  # Threshold-based
    TIME_OR_METER = "TIME_OR_METER"  # First trigger wins
    TIME_AND_METER = "TIME_AND_METER"  # Both must be met


class PMScheduleType(str, enum.Enum):
    """How the next date is calculated."""
    FIXED = "FIXED"  # From scheduled date
    FLOATING = "FLOATING"  # From completion date


class PreventiveMaintenance(Base, AuditMixin, TenantMixin):
    """
    Preventive Maintenance schedule definition.
    Generates work orders based on time, meter readings, or conditions.
    """

    __tablename__ = "preventive_maintenance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pm_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Asset association
    asset_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=True, index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True, index=True
    )

    # Job plan template
    job_plan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("job_plans.id"), nullable=True
    )

    # Trigger configuration
    trigger_type: Mapped[PMTriggerType] = mapped_column(
        SQLEnum(PMTriggerType), default=PMTriggerType.TIME, nullable=False
    )
    schedule_type: Mapped[PMScheduleType] = mapped_column(
        SQLEnum(PMScheduleType), default=PMScheduleType.FIXED, nullable=False
    )

    # Time-based scheduling
    frequency: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frequency_unit: Mapped[Optional[PMFrequencyUnit]] = mapped_column(
        SQLEnum(PMFrequencyUnit), nullable=True
    )

    # Meter-based scheduling
    meter_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("meters.id"), nullable=True
    )
    meter_interval: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Trigger every X units

    # Condition-based (threshold triggers)
    condition_attribute: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    condition_operator: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # >, <, =, >=, <=
    condition_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Schedule tracking
    last_wo_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_wo_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("work_orders.id"), nullable=True)
    next_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    last_meter_reading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    next_meter_reading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Lead time and warnings
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)  # Days before due to generate WO
    warning_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # Days before to show warning

    # Assignment defaults
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Seasonal restrictions
    seasonal_start_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-12
    seasonal_end_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    excluded_days: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"weekdays": [6, 7], "dates": ["2024-12-25"]}

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[asset_id])
    location: Mapped[Optional["Location"]] = relationship("Location", foreign_keys=[location_id])
    meter: Mapped[Optional["Meter"]] = relationship("Meter", foreign_keys=[meter_id])
    job_plan: Mapped[Optional["JobPlan"]] = relationship("JobPlan", back_populates="pms")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    schedules: Mapped[List["PMSchedule"]] = relationship(
        "PMSchedule", back_populates="pm", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PreventiveMaintenance(id={self.id}, pm_number='{self.pm_number}')>"


class PMSchedule(Base, AuditMixin):
    """
    Multiple schedule packages for a PM (like SAP maintenance strategies).
    Allows different intervals for different types of work on same asset.
    """

    __tablename__ = "pm_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("preventive_maintenance.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Schedule package
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency_unit: Mapped[PMFrequencyUnit] = mapped_column(SQLEnum(PMFrequencyUnit), nullable=False)

    # Offset from base schedule
    offset_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Override job plan tasks
    job_plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("job_plans.id"), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    pm: Mapped["PreventiveMaintenance"] = relationship("PreventiveMaintenance", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<PMSchedule(pm_id={self.pm_id}, name='{self.name}')>"


class JobPlan(Base, AuditMixin, TenantMixin):
    """
    Job Plan template defining standard work procedures.
    Used by PMs and can be applied to work orders.
    """

    __tablename__ = "job_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Default estimates
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    asset_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Applicable asset types

    # Craft/skill requirements
    required_craft: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    skill_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Safety requirements
    safety_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lockout_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permits_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    tasks: Mapped[List["JobPlanTask"]] = relationship(
        "JobPlanTask", back_populates="job_plan", cascade="all, delete-orphan"
    )
    parts: Mapped[List["JobPlanPart"]] = relationship(
        "JobPlanPart", back_populates="job_plan", cascade="all, delete-orphan"
    )
    pms: Mapped[List["PreventiveMaintenance"]] = relationship("PreventiveMaintenance", back_populates="job_plan")

    def __repr__(self) -> str:
        return f"<JobPlan(id={self.id}, code='{self.code}')>"


class JobPlanTask(Base, AuditMixin):
    """
    Standard task/step within a job plan.
    """

    __tablename__ = "job_plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Task type
    task_type: Mapped[str] = mapped_column(String(50), default="TASK", nullable=False)  # TASK, CHECKBOX, READING, SIGNATURE, PHOTO

    # For reading tasks
    expected_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Conditional logic
    condition_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    condition_operator: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    condition_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Time estimates
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    job_plan: Mapped["JobPlan"] = relationship("JobPlan", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<JobPlanTask(job_plan_id={self.job_plan_id}, seq={self.sequence})>"


class JobPlanPart(Base, AuditMixin):
    """
    Parts required for a job plan.
    """

    __tablename__ = "job_plan_parts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parts.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    job_plan: Mapped["JobPlan"] = relationship("JobPlan", back_populates="parts")
    part: Mapped["Part"] = relationship("Part", foreign_keys=[part_id])

    def __repr__(self) -> str:
        return f"<JobPlanPart(job_plan_id={self.job_plan_id}, part_id={self.part_id})>"


# Import for type hints
from app.models.location import Location
