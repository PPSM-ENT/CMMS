"""
Preventive Maintenance schemas.
"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict

from app.models.preventive_maintenance import PMFrequencyUnit, PMTriggerType, PMScheduleType


class JobPlanTaskCreate(BaseModel):
    """Job plan task creation schema."""
    sequence: int
    description: str
    instructions: Optional[str] = None
    task_type: str = "TASK"
    expected_value: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit_of_measure: Optional[str] = None
    estimated_hours: Optional[float] = None
    is_required: bool = True


class JobPlanTaskResponse(BaseModel):
    """Job plan task response schema."""
    id: int
    job_plan_id: int
    sequence: int
    description: str
    instructions: Optional[str] = None
    task_type: str
    expected_value: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit_of_measure: Optional[str] = None
    estimated_hours: Optional[float] = None
    is_required: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobPlanPartCreate(BaseModel):
    """Job plan part creation schema."""
    part_id: int
    quantity: float = 1
    is_required: bool = True
    notes: Optional[str] = None


class JobPlanPartResponse(BaseModel):
    """Job plan part response schema."""
    id: int
    job_plan_id: int
    part_id: int
    quantity: float
    is_required: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobPlanBase(BaseModel):
    """Base job plan schema."""
    code: str
    name: str
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    category: Optional[str] = None
    asset_category: Optional[str] = None
    required_craft: Optional[str] = None
    skill_level: Optional[str] = None
    safety_requirements: Optional[str] = None
    lockout_required: bool = False
    permits_required: Optional[str] = None


class JobPlanCreate(JobPlanBase):
    """Job plan creation schema."""
    tasks: List[JobPlanTaskCreate] = []
    parts: List[JobPlanPartCreate] = []


class JobPlanUpdate(BaseModel):
    """Job plan update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    category: Optional[str] = None
    asset_category: Optional[str] = None
    required_craft: Optional[str] = None
    skill_level: Optional[str] = None
    safety_requirements: Optional[str] = None
    lockout_required: Optional[bool] = None
    permits_required: Optional[str] = None
    is_active: Optional[bool] = None


class JobPlanResponse(JobPlanBase):
    """Job plan response schema."""
    id: int
    organization_id: int
    is_active: bool
    revision: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobPlanDetailResponse(JobPlanResponse):
    """Job plan with tasks and parts."""
    tasks: List[JobPlanTaskResponse] = []
    parts: List[JobPlanPartResponse] = []


class PMScheduleCreate(BaseModel):
    """PM schedule package creation schema."""
    name: str
    sequence: int = 0
    frequency: int
    frequency_unit: PMFrequencyUnit
    offset_days: int = 0
    job_plan_id: Optional[int] = None


class PMScheduleResponse(BaseModel):
    """PM schedule response schema."""
    id: int
    pm_id: int
    name: str
    sequence: int
    frequency: int
    frequency_unit: PMFrequencyUnit
    offset_days: int
    job_plan_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PMBase(BaseModel):
    """Base PM schema."""
    name: str
    description: Optional[str] = None
    asset_id: Optional[int] = None
    location_id: Optional[int] = None
    job_plan_id: Optional[int] = None
    trigger_type: PMTriggerType = PMTriggerType.TIME
    schedule_type: PMScheduleType = PMScheduleType.FIXED
    frequency: Optional[int] = None
    frequency_unit: Optional[PMFrequencyUnit] = None
    meter_id: Optional[int] = None
    meter_interval: Optional[float] = None
    condition_attribute: Optional[str] = None
    condition_operator: Optional[str] = None
    condition_value: Optional[float] = None
    lead_time_days: int = 7
    warning_days: int = 3
    assigned_to_id: Optional[int] = None
    assigned_team: Optional[str] = None
    priority: str = "MEDIUM"
    estimated_hours: Optional[float] = None
    seasonal_start_month: Optional[int] = None
    seasonal_end_month: Optional[int] = None
    excluded_days: Optional[dict] = None


class PMCreate(PMBase):
    """PM creation schema."""
    schedules: List[PMScheduleCreate] = []
    next_due_date: Optional[date] = None


class PMUpdate(BaseModel):
    """PM update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    asset_id: Optional[int] = None
    location_id: Optional[int] = None
    job_plan_id: Optional[int] = None
    trigger_type: Optional[PMTriggerType] = None
    schedule_type: Optional[PMScheduleType] = None
    frequency: Optional[int] = None
    frequency_unit: Optional[PMFrequencyUnit] = None
    meter_id: Optional[int] = None
    meter_interval: Optional[float] = None
    condition_attribute: Optional[str] = None
    condition_operator: Optional[str] = None
    condition_value: Optional[float] = None
    lead_time_days: Optional[int] = None
    warning_days: Optional[int] = None
    assigned_to_id: Optional[int] = None
    assigned_team: Optional[str] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None
    seasonal_start_month: Optional[int] = None
    seasonal_end_month: Optional[int] = None
    excluded_days: Optional[dict] = None
    is_active: Optional[bool] = None
    next_due_date: Optional[date] = None


class PMResponse(PMBase):
    """PM response schema."""
    id: int
    pm_number: str
    organization_id: int
    is_active: bool
    last_wo_date: Optional[date] = None
    last_wo_id: Optional[int] = None
    next_due_date: Optional[date] = None
    last_meter_reading: Optional[float] = None
    next_meter_reading: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PMDetailResponse(PMResponse):
    """PM with schedules."""
    schedules: List[PMScheduleResponse] = []
