"""
Work Order management endpoints with status workflow.
"""
from typing import Any, List, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, Pagination
from app.models.work_order import (
    WorkOrder,
    WorkOrderTask,
    LaborTransaction,
    MaterialTransaction,
    WorkOrderComment,
    WorkOrderStatusHistory,
    WorkOrderStatus,
    WorkOrderType,
    WorkOrderPriority,
)
from app.models.inventory import Part, StockLevel
from app.models.asset import Asset, AssetStatus, AssetCriticality
from app.models.user import User
from app.models.work_order_asset import WorkOrderAsset
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderResponse,
    WorkOrderDetailResponse,
    WorkOrderTaskCreate,
    WorkOrderTaskUpdate,
    WorkOrderTaskResponse,
    WorkOrderStatusUpdate,
    LaborTransactionCreate,
    LaborTransactionResponse,
    MaterialTransactionCreate,
    MaterialTransactionResponse,
    WorkOrderCommentCreate,
    WorkOrderCommentResponse,
    WorkOrderAssetResponse,
    WorkOrderStatusHistoryResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.work_order_service import WorkOrderService

router = APIRouter()


OPEN_WORK_ORDER_STATUSES = [
    WorkOrderStatus.DRAFT,
    WorkOrderStatus.WAITING_APPROVAL,
    WorkOrderStatus.APPROVED,
    WorkOrderStatus.SCHEDULED,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.ON_HOLD,
]

ALLOWED_OPERATORS = {"eq", "neq", "lt", "lte", "gt", "gte", "contains", "in"}

ADVANCED_FILTER_COLUMNS = {
    "status": WorkOrder.status,
    "work_type": WorkOrder.work_type,
    "priority": WorkOrder.priority,
    "assigned_team": WorkOrder.assigned_team,
    "asset_status": Asset.status,
    "asset_criticality": Asset.criticality,
    "asset_category": Asset.category,
    "asset_name": Asset.name,
    "asset_num": Asset.asset_num,
    "location_id": WorkOrder.location_id,
    "failure_code": WorkOrder.failure_code,
    "downtime_hours": WorkOrder.downtime_hours,
    "total_cost": WorkOrder.total_cost,
    "asset_was_down": WorkOrder.asset_was_down,
}


def _coerce_value(value: str) -> Any:
    """Best-effort conversion of string query values."""
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"true", "false"}:
            return lower == "true"
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value


def _build_condition(column, operator: str, raw_value: str):
    """Translate a column/operator/value triple into a SQLAlchemy expression."""
    if operator not in ALLOWED_OPERATORS:
        return None

    if operator == "in":
        values = [
            _coerce_value(v.strip())
            for v in raw_value.split(",")
            if v.strip()
        ]
        return column.in_(values) if values else None

    coerced = _coerce_value(raw_value)
    if operator == "eq":
        return column == coerced
    if operator == "neq":
        return column != coerced
    if operator == "lt":
        return column < coerced
    if operator == "lte":
        return column <= coerced
    if operator == "gt":
        return column > coerced
    if operator == "gte":
        return column >= coerced
    if operator == "contains":
        return column.ilike(f"%{raw_value}%")
    return None


def _parse_custom_filters(raw_filters: Optional[str]) -> List[str]:
    """Split pipe-separated custom filters into individual expressions."""
    if not raw_filters:
        return []
    return [segment.strip() for segment in raw_filters.split("|") if segment.strip()]


# Valid status transitions
STATUS_TRANSITIONS = {
    WorkOrderStatus.DRAFT: [WorkOrderStatus.WAITING_APPROVAL, WorkOrderStatus.APPROVED, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.WAITING_APPROVAL: [WorkOrderStatus.APPROVED, WorkOrderStatus.DRAFT, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.APPROVED: [WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.SCHEDULED: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.APPROVED, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.IN_PROGRESS: [WorkOrderStatus.ON_HOLD, WorkOrderStatus.COMPLETED],
    WorkOrderStatus.ON_HOLD: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
    WorkOrderStatus.COMPLETED: [WorkOrderStatus.CLOSED, WorkOrderStatus.IN_PROGRESS],
    WorkOrderStatus.CLOSED: [],  # Final state
    WorkOrderStatus.CANCELLED: [],  # Final state
}


async def generate_wo_number(db, org_id: int) -> str:
    """Generate next work order number."""
    result = await db.execute(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == org_id)
    )
    count = result.scalar() + 1
    return f"WO-{count:06d}"


@router.get("", response_model=PaginatedResponse[WorkOrderResponse])
async def list_work_orders(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    status: WorkOrderStatus = Query(None, description="Filter by status"),
    work_type: WorkOrderType = Query(None, description="Filter by work type"),
    priority: WorkOrderPriority = Query(None, description="Filter by priority"),
    asset_id: int = Query(None, description="Filter by asset"),
    location_id: int = Query(None, description="Filter by location"),
    assigned_to_id: int = Query(None, description="Filter by assigned user"),
    search: str = Query(None, description="Search by WO number or title"),
    created_from: date = Query(None, description="Filter by created date (start)"),
    created_to: date = Query(None, description="Filter by created date (end)"),
    due_from: date = Query(None, description="Filter by due date (start)"),
    due_to: date = Query(None, description="Filter by due date (end)"),
    completed_from: date = Query(None, description="Filter by completion date (start)"),
    completed_to: date = Query(None, description="Filter by completion date (end)"),
    updated_from: date = Query(None, description="Filter by last update (start)"),
    updated_to: date = Query(None, description="Filter by last update (end)"),
    assigned_team: str = Query(None, description="Filter by assigned team"),
    quick_filter: str = Query(None, description="Quick lookup key (overdue, my_open, etc.)"),
    downtime_only: bool = Query(False, description="Only include work orders flagged as downtime"),
    asset_status: AssetStatus = Query(None, description="Filter by linked asset status"),
    asset_criticality: AssetCriticality = Query(None, description="Filter by linked asset criticality"),
    asset_category: str = Query(None, description="Filter by asset category"),
    labor_user_id: int = Query(None, description="Work orders with labor logged by the specified user"),
    labor_craft: str = Query(None, description="Work orders where labor was logged for a craft"),
    custom_filters: str = Query(
        None,
        description="Pipe separated advanced filters in field:operator:value format",
    ),
) -> Any:
    """
    List work orders in the organization.
    """
    query = (
        select(WorkOrder)
        .outerjoin(Asset, WorkOrder.asset_id == Asset.id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    joined_labor = False

    if status:
        query = query.where(WorkOrder.status == status)

    if work_type:
        query = query.where(WorkOrder.work_type == work_type)

    if priority:
        query = query.where(WorkOrder.priority == priority)

    if asset_id:
        query = query.where(WorkOrder.asset_id == asset_id)

    if location_id:
        query = query.where(WorkOrder.location_id == location_id)

    if assigned_to_id:
        query = query.where(WorkOrder.assigned_to_id == assigned_to_id)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (WorkOrder.wo_number.ilike(search_filter))
            | (WorkOrder.title.ilike(search_filter))
        )

    if created_from:
        query = query.where(func.date(WorkOrder.created_at) >= created_from)
    if created_to:
        query = query.where(func.date(WorkOrder.created_at) <= created_to)
    if updated_from:
        query = query.where(func.date(WorkOrder.updated_at) >= updated_from)
    if updated_to:
        query = query.where(func.date(WorkOrder.updated_at) <= updated_to)
    if due_from:
        query = query.where(WorkOrder.due_date >= due_from)
    if due_to:
        query = query.where(WorkOrder.due_date <= due_to)
    if completed_from:
        query = query.where(func.date(WorkOrder.actual_end) >= completed_from)
    if completed_to:
        query = query.where(func.date(WorkOrder.actual_end) <= completed_to)

    if assigned_team:
        query = query.where(WorkOrder.assigned_team.ilike(f"%{assigned_team}%"))

    if downtime_only:
        query = query.where(WorkOrder.asset_was_down == True)  # noqa: E712

    if asset_status:
        query = query.where(Asset.status == asset_status)

    if asset_criticality:
        query = query.where(Asset.criticality == asset_criticality)

    if asset_category:
        query = query.where(Asset.category == asset_category)

    if quick_filter:
        quick = quick_filter.lower()
        today = date.today()
        if quick == "overdue":
            query = query.where(WorkOrder.status.in_(OPEN_WORK_ORDER_STATUSES))
            query = query.where(WorkOrder.due_date.isnot(None))
            query = query.where(WorkOrder.due_date < today)
        elif quick == "my_open":
            query = query.where(WorkOrder.status.notin_([WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]))
            query = query.where(WorkOrder.assigned_to_id == current_user.id)
        elif quick == "completed_last_7":
            window_start = today - timedelta(days=7)
            query = query.where(WorkOrder.status == WorkOrderStatus.COMPLETED)
            query = query.where(func.date(WorkOrder.actual_end) >= window_start)
        elif quick == "safety":
            query = query.where(WorkOrder.work_type == WorkOrderType.INSPECTION)

    if labor_user_id or labor_craft:
        query = query.join(LaborTransaction, LaborTransaction.work_order_id == WorkOrder.id)
        joined_labor = True
        if labor_user_id:
            query = query.where(LaborTransaction.user_id == labor_user_id)
        if labor_craft:
            query = query.where(LaborTransaction.craft.ilike(f"%{labor_craft}%"))

    for raw_filter in _parse_custom_filters(custom_filters):
        try:
            field, operator, value = raw_filter.split(":", 2)
        except ValueError:
            continue
        column = ADVANCED_FILTER_COLUMNS.get(field)
        if not column:
            continue
        condition = _build_condition(column, operator, value)
        if condition is not None:
            query = query.where(condition)

    if joined_labor:
        query = query.distinct()

    # Count total
    id_query = query.with_only_columns(WorkOrder.id).order_by(None)
    if joined_labor:
        id_query = id_query.distinct()
    count_subquery = id_query.subquery()
    total = await db.scalar(select(func.count()).select_from(count_subquery))

    # Get paginated results
    query = query.order_by(WorkOrder.created_at.desc()).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    work_orders = result.scalars().all()

    # Fetch assigned_group_name for work orders that have assigned_group_id
    from app.models.user_group import UserGroup
    group_ids = [wo.assigned_group_id for wo in work_orders if wo.assigned_group_id]
    group_names = {}
    if group_ids:
        group_result = await db.execute(
            select(UserGroup.id, UserGroup.name).where(UserGroup.id.in_(group_ids))
        )
        group_names = {row.id: row.name for row in group_result}

    # Build response with assigned_group_name
    items = []
    for wo in work_orders:
        wo_dict = {
            "id": wo.id,
            "wo_number": wo.wo_number,
            "organization_id": wo.organization_id,
            "title": wo.title,
            "description": wo.description,
            "work_type": wo.work_type,
            "priority": wo.priority,
            "status": wo.status,
            "asset_id": wo.asset_id,
            "location_id": wo.location_id,
            "assigned_to_id": wo.assigned_to_id,
            "assigned_team": wo.assigned_team,
            "assigned_group_id": wo.assigned_group_id,
            "assigned_group_name": group_names.get(wo.assigned_group_id) if wo.assigned_group_id else None,
            "scheduled_start": wo.scheduled_start,
            "scheduled_end": wo.scheduled_end,
            "due_date": wo.due_date,
            "estimated_hours": wo.estimated_hours,
            "estimated_cost": wo.estimated_cost,
            "actual_start": wo.actual_start,
            "actual_end": wo.actual_end,
            "actual_labor_hours": wo.actual_labor_hours,
            "actual_labor_cost": wo.actual_labor_cost,
            "actual_material_cost": wo.actual_material_cost,
            "total_cost": wo.total_cost,
            "downtime_hours": wo.downtime_hours,
            "asset_was_down": wo.asset_was_down,
            "pm_id": wo.pm_id,
            "parent_wo_id": wo.parent_wo_id,
            "failure_code": wo.failure_code,
            "failure_cause": wo.failure_cause,
            "failure_remedy": wo.failure_remedy,
            "completion_notes": wo.completion_notes,
            "completed_by_id": wo.completed_by_id,
            "created_at": wo.created_at,
            "updated_at": wo.updated_at,
        }
        items.append(WorkOrderResponse(**wo_dict))

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    db: DBSession,
    current_user: CurrentUser,
    wo_data: WorkOrderCreate,
) -> Any:
    """
    Create a new work order.
    """
    wo_number = await generate_wo_number(db, current_user.organization_id)

    # Extract tasks and multi-asset data
    tasks_data = wo_data.tasks
    asset_ids = wo_data.asset_ids or []
    wo_dict = wo_data.model_dump(exclude={"tasks", "asset_ids"})

    work_order = WorkOrder(
        organization_id=current_user.organization_id,
        wo_number=wo_number,
        status=WorkOrderStatus.DRAFT,
        created_by_id=current_user.id,
        **wo_dict,
    )

    db.add(work_order)
    await db.flush()

    # Add tasks
    for task_data in tasks_data:
        task = WorkOrderTask(
            work_order_id=work_order.id,
            created_by_id=current_user.id,
            **task_data.model_dump(),
        )
        db.add(task)

    # Handle multi-asset relationships
    for i, asset_id in enumerate(asset_ids):
        # Verify asset exists and belongs to organization
        result = await db.execute(
            select(Asset)
            .where(Asset.id == asset_id)
            .where(Asset.organization_id == current_user.organization_id)
        )
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found",
            )
        
        work_order_asset = WorkOrderAsset(
            work_order_id=work_order.id,
            asset_id=asset_id,
            sequence=i,
            created_by_id=current_user.id,
        )
        db.add(work_order_asset)

    # Record initial status
    status_history = WorkOrderStatusHistory(
        work_order_id=work_order.id,
        to_status=WorkOrderStatus.DRAFT.value,
        changed_by_id=current_user.id,
        created_by_id=current_user.id,
    )
    db.add(status_history)

    await db.commit()
    await db.refresh(work_order)

    return work_order


@router.get("/{wo_id}", response_model=WorkOrderDetailResponse)
async def get_work_order(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
) -> Any:
    """
    Get work order by ID with all related data.
    """
    result = await db.execute(
        select(WorkOrder)
        .options(
            selectinload(WorkOrder.tasks),
            selectinload(WorkOrder.labor_transactions),
            selectinload(WorkOrder.material_transactions),
            selectinload(WorkOrder.comments),
            selectinload(WorkOrder.status_history),
            selectinload(WorkOrder.multi_assets).selectinload(WorkOrderAsset.asset),
        )
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Fetch assigned_group_name separately if assigned_group_id is set
    assigned_group_name = None
    if work_order.assigned_group_id:
        from app.models.user_group import UserGroup
        group_result = await db.execute(
            select(UserGroup.name).where(UserGroup.id == work_order.assigned_group_id)
        )
        assigned_group_name = group_result.scalar_one_or_none()

    # Build response explicitly to handle nested relationships properly
    return WorkOrderDetailResponse(
        id=work_order.id,
        wo_number=work_order.wo_number,
        title=work_order.title,
        description=work_order.description,
        work_type=work_order.work_type,
        status=work_order.status,
        priority=work_order.priority,
        asset_id=work_order.asset_id,
        location_id=work_order.location_id,
        assigned_to_id=work_order.assigned_to_id,
        assigned_team=work_order.assigned_team,
        assigned_group_id=work_order.assigned_group_id,
        assigned_group_name=assigned_group_name,
        scheduled_start=work_order.scheduled_start,
        scheduled_end=work_order.scheduled_end,
        due_date=work_order.due_date,
        estimated_hours=work_order.estimated_hours,
        estimated_cost=work_order.estimated_cost,
        custom_fields=work_order.custom_fields,
        organization_id=work_order.organization_id,
        actual_start=work_order.actual_start,
        actual_end=work_order.actual_end,
        actual_labor_hours=work_order.actual_labor_hours,
        actual_labor_cost=work_order.actual_labor_cost,
        actual_material_cost=work_order.actual_material_cost,
        total_cost=work_order.total_cost,
        downtime_hours=work_order.downtime_hours,
        asset_was_down=work_order.asset_was_down,
        pm_id=work_order.pm_id,
        parent_wo_id=work_order.parent_wo_id,
        failure_code=work_order.failure_code,
        failure_cause=work_order.failure_cause,
        failure_remedy=work_order.failure_remedy,
        completion_notes=work_order.completion_notes,
        completed_by_id=work_order.completed_by_id,
        created_at=work_order.created_at,
        updated_at=work_order.updated_at,
        tasks=[WorkOrderTaskResponse.model_validate(t) for t in work_order.tasks],
        labor_transactions=[LaborTransactionResponse.model_validate(lt) for lt in work_order.labor_transactions],
        material_transactions=[MaterialTransactionResponse.model_validate(mt) for mt in work_order.material_transactions],
        comments=[WorkOrderCommentResponse.model_validate(c) for c in work_order.comments],
        status_history=[WorkOrderStatusHistoryResponse.model_validate(sh) for sh in work_order.status_history],
        multi_assets=[WorkOrderAssetResponse.from_work_order_asset(ma) for ma in work_order.multi_assets],
    )


@router.put("/{wo_id}", response_model=WorkOrderResponse)
async def update_work_order(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    wo_data: WorkOrderUpdate,
) -> Any:
    """
    Update work order.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Check if WO can be updated (not closed/cancelled) - unless user is admin
    if work_order.status in [WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update closed or cancelled work order",
            )

    update_data = wo_data.model_dump(exclude_unset=True)

    # Handle status change separately
    if "status" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use status endpoint to change work order status",
        )

    for field, value in update_data.items():
        setattr(work_order, field, value)

    work_order.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(work_order)

    return work_order


@router.delete("/{wo_id}", response_model=MessageResponse)
async def delete_work_order(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
) -> Any:
    """
    Delete a work order. Admin only.
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete work orders",
        )

    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Store work order number for response
    wo_number = work_order.wo_number

    # Delete the work order (cascade will handle related records)
    await db.delete(work_order)
    await db.commit()

    return {"message": f"Work order {wo_number} has been deleted"}


@router.put("/{wo_id}/status", response_model=WorkOrderResponse)
async def update_work_order_status(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    status_data: WorkOrderStatusUpdate,
) -> Any:
    """
    Update work order status with validation.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Validate transition
    allowed_transitions = STATUS_TRANSITIONS.get(work_order.status, [])
    if status_data.status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {work_order.status.value} to {status_data.status.value}",
        )

    old_status = work_order.status

    # Handle specific transitions
    if status_data.status == WorkOrderStatus.IN_PROGRESS and not work_order.actual_start:
        work_order.actual_start = datetime.utcnow()

    if status_data.status == WorkOrderStatus.COMPLETED:
        work_order.actual_end = datetime.utcnow()
        work_order.completed_by_id = current_user.id
        # Set completion details if provided
        if status_data.completion_notes is not None:
            work_order.completion_notes = status_data.completion_notes
        if status_data.failure_code is not None:
            work_order.failure_code = status_data.failure_code
        if status_data.failure_cause is not None:
            work_order.failure_cause = status_data.failure_cause
        if status_data.failure_remedy is not None:
            work_order.failure_remedy = status_data.failure_remedy
        if status_data.downtime_hours is not None:
            work_order.downtime_hours = status_data.downtime_hours
        if status_data.asset_was_down is not None:
            work_order.asset_was_down = status_data.asset_was_down

    work_order.status = status_data.status
    work_order.updated_by_id = current_user.id

    # Record status change
    status_history = WorkOrderStatusHistory(
        work_order_id=work_order.id,
        from_status=old_status.value,
        to_status=status_data.status.value,
        changed_by_id=current_user.id,
        reason=status_data.reason,
        created_by_id=current_user.id,
    )
    db.add(status_history)

    await db.commit()
    await db.refresh(work_order)

    return work_order


# Task endpoints

@router.post("/{wo_id}/tasks", response_model=WorkOrderTaskResponse, status_code=status.HTTP_201_CREATED)
async def add_work_order_task(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    task_data: WorkOrderTaskCreate,
) -> Any:
    """
    Add a task to a work order.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    task = WorkOrderTask(
        work_order_id=wo_id,
        created_by_id=current_user.id,
        **task_data.model_dump(),
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task


@router.put("/{wo_id}/tasks/{task_id}", response_model=WorkOrderTaskResponse)
async def update_work_order_task(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    task_id: int,
    task_data: WorkOrderTaskUpdate,
) -> Any:
    """
    Update a work order task.
    """
    result = await db.execute(
        select(WorkOrderTask)
        .join(WorkOrder)
        .where(WorkOrderTask.id == task_id)
        .where(WorkOrderTask.work_order_id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = task_data.model_dump(exclude_unset=True)

    # Handle completion
    if update_data.get("is_completed") and not task.is_completed:
        task.completed_at = datetime.utcnow()
        task.completed_by_id = current_user.id

    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(task)

    return task


# Labor transaction endpoints

@router.post("/{wo_id}/labor", response_model=LaborTransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_labor_transaction(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    labor_data: LaborTransactionCreate,
) -> Any:
    """
    Record labor time on a work order.
    User rate and craft are automatically pulled from the user's profile.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Determine which user to record labor for
    target_user_id = labor_data.user_id if labor_data.user_id else current_user.id

    # Fetch the target user to get their rate and craft
    result = await db.execute(
        select(User)
        .where(User.id == target_user_id)
        .where(User.organization_id == current_user.organization_id)
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Use provided values or fall back to user profile
    hourly_rate = labor_data.hourly_rate if labor_data.hourly_rate is not None else (target_user.hourly_rate or 0)
    craft = labor_data.craft if labor_data.craft else target_user.job_title

    # Calculate total cost
    total_cost = labor_data.hours * hourly_rate

    labor = LaborTransaction(
        organization_id=current_user.organization_id,
        work_order_id=wo_id,
        user_id=target_user_id,
        hours=labor_data.hours,
        labor_type=labor_data.labor_type,
        hourly_rate=hourly_rate,
        craft=craft,
        notes=labor_data.notes,
        total_cost=total_cost,
        created_by_id=current_user.id,
    )

    db.add(labor)

    # Update work order totals
    work_order.actual_labor_hours += labor_data.hours
    work_order.actual_labor_cost += total_cost
    work_order.total_cost = work_order.actual_labor_cost + work_order.actual_material_cost

    await db.commit()
    await db.refresh(labor)

    return labor


# Material transaction endpoints

@router.post("/{wo_id}/materials", response_model=MaterialTransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_material_transaction(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    material_data: MaterialTransactionCreate,
) -> Any:
    """
    Record material usage on a work order.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    # Verify part exists
    result = await db.execute(
        select(Part)
        .where(Part.id == material_data.part_id)
        .where(Part.organization_id == current_user.organization_id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )

    # Calculate total cost
    total_cost = material_data.quantity * material_data.unit_cost

    material = MaterialTransaction(
        organization_id=current_user.organization_id,
        work_order_id=wo_id,
        total_cost=total_cost,
        created_by_id=current_user.id,
        **material_data.model_dump(),
    )

    db.add(material)

    # Update stock if storeroom specified
    if material_data.storeroom_id and material_data.transaction_type == "ISSUE":
        result = await db.execute(
            select(StockLevel)
            .where(StockLevel.part_id == material_data.part_id)
            .where(StockLevel.storeroom_id == material_data.storeroom_id)
        )
        stock = result.scalar_one_or_none()

        if stock:
            stock.current_balance -= material_data.quantity
            stock.update_available()
            stock.last_issue_date = datetime.utcnow()

    # Update work order totals
    work_order.actual_material_cost += total_cost
    work_order.total_cost = work_order.actual_labor_cost + work_order.actual_material_cost

    await db.commit()
    await db.refresh(material)

    return material


# Comment endpoints

@router.post("/{wo_id}/comments", response_model=WorkOrderCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
    comment_data: WorkOrderCommentCreate,
) -> Any:
    """
    Add a comment to a work order.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    comment = WorkOrderComment(
        work_order_id=wo_id,
        user_id=current_user.id,
        created_by_id=current_user.id,
        **comment_data.model_dump(),
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment


@router.get("/{wo_id}/comments", response_model=List[WorkOrderCommentResponse])
async def get_comments(
    db: DBSession,
    current_user: CurrentUser,
    wo_id: int,
) -> Any:
    """
    Get all comments for a work order.
    """
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == wo_id)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found",
        )

    result = await db.execute(
        select(WorkOrderComment)
        .where(WorkOrderComment.work_order_id == wo_id)
        .order_by(WorkOrderComment.created_at.desc())
    )
    comments = result.scalars().all()

    return comments
