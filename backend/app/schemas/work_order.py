"""
Work Order schemas.
"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict

from app.models.work_order import WorkOrderType, WorkOrderStatus, WorkOrderPriority


class WorkOrderTaskCreate(BaseModel):
    """Work order task creation schema."""
    sequence: int
    description: str
    instructions: Optional[str] = None
    task_type: str = "TASK"
    expected_value: Optional[str] = None
    estimated_hours: Optional[float] = None


class WorkOrderTaskUpdate(BaseModel):
    """Work order task update schema."""
    sequence: Optional[int] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    is_completed: Optional[bool] = None
    reading_value: Optional[str] = None


class WorkOrderTaskResponse(BaseModel):
    """Work order task response schema."""
    id: int
    work_order_id: int
    sequence: int
    description: str
    instructions: Optional[str] = None
    task_type: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    completed_by_id: Optional[int] = None
    reading_value: Optional[str] = None
    expected_value: Optional[str] = None
    estimated_hours: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LaborTransactionCreate(BaseModel):
    """Labor transaction creation schema."""
    hours: float
    labor_type: str = "REGULAR"
    notes: Optional[str] = None
    # Optional - if not provided, uses current user
    user_id: Optional[int] = None
    # Optional overrides - if not provided, pulled from user profile
    hourly_rate: Optional[float] = None
    craft: Optional[str] = None


class LaborTransactionResponse(BaseModel):
    """Labor transaction response schema."""
    id: int
    work_order_id: int
    user_id: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hours: float
    labor_type: str
    hourly_rate: float
    total_cost: float
    craft: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialTransactionCreate(BaseModel):
    """Material transaction creation schema."""
    part_id: int
    quantity: float
    unit_cost: float
    storeroom_id: Optional[int] = None
    transaction_type: str = "ISSUE"
    notes: Optional[str] = None


class MaterialTransactionResponse(BaseModel):
    """Material transaction response schema."""
    id: int
    work_order_id: int
    part_id: int
    quantity: float
    unit_cost: float
    total_cost: float
    storeroom_id: Optional[int] = None
    transaction_type: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkOrderCommentCreate(BaseModel):
    """Work order comment creation schema."""
    comment: str
    is_internal: bool = False


class WorkOrderCommentResponse(BaseModel):
    """Work order comment response schema."""
    id: int
    work_order_id: int
    user_id: int
    comment: str
    is_internal: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkOrderStatusHistoryResponse(BaseModel):
    """Work order status history response schema."""
    id: int
    work_order_id: int
    from_status: Optional[str] = None
    to_status: str
    changed_by_id: int
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkOrderBase(BaseModel):
    """Base work order schema."""
    title: str
    description: Optional[str] = None
    work_type: WorkOrderType = WorkOrderType.CORRECTIVE
    priority: WorkOrderPriority = WorkOrderPriority.MEDIUM
    asset_id: Optional[int] = None  # Primary asset
    location_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    assigned_team: Optional[str] = None
    assigned_group_id: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    custom_fields: Optional[dict] = None
    # For multi-asset work orders
    asset_ids: Optional[List[int]] = None  # Additional assets for the work order


class WorkOrderCreate(WorkOrderBase):
    """Work order creation schema."""
    tasks: List[WorkOrderTaskCreate] = []


class WorkOrderUpdate(BaseModel):
    """Work order update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    work_type: Optional[WorkOrderType] = None
    priority: Optional[WorkOrderPriority] = None
    status: Optional[WorkOrderStatus] = None
    asset_id: Optional[int] = None
    location_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    assigned_team: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    downtime_hours: Optional[float] = None
    asset_was_down: Optional[bool] = None
    failure_code: Optional[str] = None
    failure_cause: Optional[str] = None
    failure_remedy: Optional[str] = None
    completion_notes: Optional[str] = None
    custom_fields: Optional[dict] = None


class WorkOrderStatusUpdate(BaseModel):
    """Work order status change schema."""
    status: WorkOrderStatus
    reason: Optional[str] = None
    # Completion fields (used when transitioning to COMPLETED status)
    completion_notes: Optional[str] = None
    failure_code: Optional[str] = None
    failure_cause: Optional[str] = None
    failure_remedy: Optional[str] = None
    downtime_hours: Optional[float] = None
    asset_was_down: Optional[bool] = None


class WorkOrderResponse(WorkOrderBase):
    """Work order response schema."""
    id: int
    wo_number: str
    organization_id: int
    status: WorkOrderStatus
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_labor_hours: float
    actual_labor_cost: float
    actual_material_cost: float
    total_cost: float
    downtime_hours: Optional[float] = None
    asset_was_down: bool
    pm_id: Optional[int] = None
    parent_wo_id: Optional[int] = None
    failure_code: Optional[str] = None
    failure_cause: Optional[str] = None
    failure_remedy: Optional[str] = None
    completion_notes: Optional[str] = None
    completed_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    assigned_group_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


from app.models.work_order_asset import WorkOrderAsset


class WorkOrderAssetResponse(BaseModel):
    """Work order to asset relationship response schema."""
    id: int
    asset_id: int
    sequence: int
    instructions: Optional[str] = None
    asset_name: Optional[str] = None
    asset_num: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_work_order_asset(cls, woa: "WorkOrderAsset") -> "WorkOrderAssetResponse":
        """Create response from WorkOrderAsset with nested asset data."""
        return cls(
            id=woa.id,
            asset_id=woa.asset_id,
            sequence=woa.sequence,
            instructions=woa.instructions,
            asset_name=woa.asset.name if woa.asset else None,
            asset_num=woa.asset.asset_num if woa.asset else None,
        )


class WorkOrderDetailResponse(WorkOrderResponse):
    """Work order with related data."""
    tasks: List[WorkOrderTaskResponse] = []
    labor_transactions: List[LaborTransactionResponse] = []
    material_transactions: List[MaterialTransactionResponse] = []
    comments: List[WorkOrderCommentResponse] = []
    status_history: List[WorkOrderStatusHistoryResponse] = []
    multi_assets: List[WorkOrderAssetResponse] = []
