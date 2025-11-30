"""
Preventive Maintenance endpoints.
"""
from typing import Any, List
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, Pagination
from app.models.preventive_maintenance import (
    PreventiveMaintenance,
    PMSchedule,
    JobPlan,
    JobPlanTask,
    JobPlanPart,
    PMTriggerType,
    PMFrequencyUnit,
)
from app.models.work_order import WorkOrder, WorkOrderTask, WorkOrderStatus, WorkOrderType
from app.schemas.preventive_maintenance import (
    PMCreate,
    PMUpdate,
    PMResponse,
    PMDetailResponse,
    JobPlanCreate,
    JobPlanUpdate,
    JobPlanResponse,
    JobPlanDetailResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


async def generate_pm_number(db, org_id: int) -> str:
    """Generate next PM number."""
    result = await db.execute(
        select(func.count())
        .select_from(PreventiveMaintenance)
        .where(PreventiveMaintenance.organization_id == org_id)
    )
    count = result.scalar() + 1
    return f"PM-{count:06d}"


def calculate_next_due_date(
    pm: PreventiveMaintenance,
    last_date: date = None,
) -> date:
    """Calculate next due date based on PM configuration."""
    base_date = last_date or date.today()

    if pm.frequency is None or pm.frequency_unit is None:
        return None

    if pm.frequency_unit == PMFrequencyUnit.DAYS:
        return base_date + timedelta(days=pm.frequency)
    elif pm.frequency_unit == PMFrequencyUnit.WEEKS:
        return base_date + timedelta(weeks=pm.frequency)
    elif pm.frequency_unit == PMFrequencyUnit.MONTHS:
        # Add months
        month = base_date.month + pm.frequency
        year = base_date.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(base_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return date(year, month, day)
    elif pm.frequency_unit == PMFrequencyUnit.YEARS:
        return date(base_date.year + pm.frequency, base_date.month, base_date.day)

    return None


# PM endpoints

@router.get("", response_model=PaginatedResponse[PMResponse])
async def list_pms(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    asset_id: int = Query(None, description="Filter by asset"),
    location_id: int = Query(None, description="Filter by location"),
    is_active: bool = Query(None, description="Filter by active status"),
    due_before: date = Query(None, description="Filter by due date"),
    search: str = Query(None, description="Search by PM number or name"),
) -> Any:
    """
    List preventive maintenance schedules.
    """
    query = select(PreventiveMaintenance).where(
        PreventiveMaintenance.organization_id == current_user.organization_id
    )

    if asset_id:
        query = query.where(PreventiveMaintenance.asset_id == asset_id)

    if location_id:
        query = query.where(PreventiveMaintenance.location_id == location_id)

    if is_active is not None:
        query = query.where(PreventiveMaintenance.is_active == is_active)

    if due_before:
        query = query.where(PreventiveMaintenance.next_due_date <= due_before)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (PreventiveMaintenance.pm_number.ilike(search_filter))
            | (PreventiveMaintenance.name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(PreventiveMaintenance.next_due_date).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    pms = result.scalars().all()

    return PaginatedResponse(
        items=pms,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/due", response_model=List[PMResponse])
async def get_due_pms(
    db: DBSession,
    current_user: CurrentUser,
    days_ahead: int = Query(7, description="Days to look ahead"),
) -> Any:
    """
    Get PMs due within specified days.
    """
    cutoff_date = date.today() + timedelta(days=days_ahead)

    result = await db.execute(
        select(PreventiveMaintenance)
        .where(PreventiveMaintenance.organization_id == current_user.organization_id)
        .where(PreventiveMaintenance.is_active == True)
        .where(PreventiveMaintenance.next_due_date <= cutoff_date)
        .order_by(PreventiveMaintenance.next_due_date)
    )
    pms = result.scalars().all()

    return pms


@router.post("", response_model=PMResponse, status_code=status.HTTP_201_CREATED)
async def create_pm(
    db: DBSession,
    current_user: CurrentUser,
    pm_data: PMCreate,
) -> Any:
    """
    Create a new preventive maintenance schedule.
    """
    pm_number = await generate_pm_number(db, current_user.organization_id)

    # Extract schedules
    schedules_data = pm_data.schedules
    pm_dict = pm_data.model_dump(exclude={"schedules"})

    pm = PreventiveMaintenance(
        organization_id=current_user.organization_id,
        pm_number=pm_number,
        created_by_id=current_user.id,
        **pm_dict,
    )

    # Calculate initial next due date if not provided
    if pm.next_due_date is None and pm.trigger_type in [PMTriggerType.TIME, PMTriggerType.TIME_OR_METER]:
        pm.next_due_date = calculate_next_due_date(pm)

    db.add(pm)
    await db.flush()

    # Add schedule packages
    for schedule_data in schedules_data:
        schedule = PMSchedule(
            pm_id=pm.id,
            created_by_id=current_user.id,
            **schedule_data.model_dump(),
        )
        db.add(schedule)

    await db.commit()
    await db.refresh(pm)

    return pm


@router.get("/{pm_id}", response_model=PMDetailResponse)
async def get_pm(
    db: DBSession,
    current_user: CurrentUser,
    pm_id: int,
) -> Any:
    """
    Get PM by ID with schedules.
    """
    result = await db.execute(
        select(PreventiveMaintenance)
        .options(selectinload(PreventiveMaintenance.schedules))
        .where(PreventiveMaintenance.id == pm_id)
        .where(PreventiveMaintenance.organization_id == current_user.organization_id)
    )
    pm = result.scalar_one_or_none()

    if not pm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PM not found",
        )

    return pm


@router.put("/{pm_id}", response_model=PMResponse)
async def update_pm(
    db: DBSession,
    current_user: CurrentUser,
    pm_id: int,
    pm_data: PMUpdate,
) -> Any:
    """
    Update PM.
    """
    result = await db.execute(
        select(PreventiveMaintenance)
        .where(PreventiveMaintenance.id == pm_id)
        .where(PreventiveMaintenance.organization_id == current_user.organization_id)
    )
    pm = result.scalar_one_or_none()

    if not pm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PM not found",
        )

    update_data = pm_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pm, field, value)

    pm.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(pm)

    return pm


@router.delete("/{pm_id}", response_model=MessageResponse)
async def delete_pm(
    db: DBSession,
    current_user: CurrentUser,
    pm_id: int,
) -> Any:
    """
    Deactivate PM (soft delete).
    """
    result = await db.execute(
        select(PreventiveMaintenance)
        .where(PreventiveMaintenance.id == pm_id)
        .where(PreventiveMaintenance.organization_id == current_user.organization_id)
    )
    pm = result.scalar_one_or_none()

    if not pm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PM not found",
        )

    pm.is_active = False
    await db.commit()

    return MessageResponse(message="PM deactivated successfully")


@router.post("/{pm_id}/generate-wo", response_model=dict)
async def generate_work_order(
    db: DBSession,
    current_user: CurrentUser,
    pm_id: int,
) -> Any:
    """
    Manually generate a work order from a PM.
    """
    result = await db.execute(
        select(PreventiveMaintenance)
        .options(selectinload(PreventiveMaintenance.job_plan).selectinload(JobPlan.tasks))
        .where(PreventiveMaintenance.id == pm_id)
        .where(PreventiveMaintenance.organization_id == current_user.organization_id)
    )
    pm = result.scalar_one_or_none()

    if not pm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PM not found",
        )

    # Generate WO number
    wo_count = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == current_user.organization_id)
    )
    wo_number = f"WO-{wo_count + 1:06d}"

    # Create work order
    work_order = WorkOrder(
        organization_id=current_user.organization_id,
        wo_number=wo_number,
        title=f"PM: {pm.name}",
        description=pm.description,
        work_type=WorkOrderType.PREVENTIVE,
        status=WorkOrderStatus.APPROVED,
        priority=pm.priority,
        asset_id=pm.asset_id,
        location_id=pm.location_id,
        assigned_to_id=pm.assigned_to_id,
        assigned_team=pm.assigned_team,
        estimated_hours=pm.estimated_hours,
        pm_id=pm.id,
        due_date=pm.next_due_date,
        created_by_id=current_user.id,
    )

    db.add(work_order)
    await db.flush()

    # Copy tasks from job plan
    if pm.job_plan:
        for task in pm.job_plan.tasks:
            wo_task = WorkOrderTask(
                work_order_id=work_order.id,
                sequence=task.sequence,
                description=task.description,
                instructions=task.instructions,
                task_type=task.task_type,
                expected_value=task.expected_value,
                estimated_hours=task.estimated_hours,
                created_by_id=current_user.id,
            )
            db.add(wo_task)

    # Update PM tracking
    pm.last_wo_date = date.today()
    pm.last_wo_id = work_order.id

    # Calculate next due date
    if pm.schedule_type.value == "FIXED":
        pm.next_due_date = calculate_next_due_date(pm, pm.next_due_date)
    else:  # FLOATING
        pm.next_due_date = calculate_next_due_date(pm, date.today())

    await db.commit()

    return {
        "message": "Work order generated successfully",
        "work_order_id": work_order.id,
        "wo_number": wo_number,
        "next_due_date": pm.next_due_date.isoformat() if pm.next_due_date else None,
    }


# Job Plan endpoints

@router.get("/job-plans", response_model=PaginatedResponse[JobPlanResponse])
async def list_job_plans(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    category: str = Query(None, description="Filter by category"),
    search: str = Query(None, description="Search by code or name"),
) -> Any:
    """
    List job plans.
    """
    query = select(JobPlan).where(JobPlan.organization_id == current_user.organization_id)

    if category:
        query = query.where(JobPlan.category == category)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (JobPlan.code.ilike(search_filter))
            | (JobPlan.name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(JobPlan.code).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    job_plans = result.scalars().all()

    return PaginatedResponse(
        items=job_plans,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("/job-plans", response_model=JobPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_job_plan(
    db: DBSession,
    current_user: CurrentUser,
    jp_data: JobPlanCreate,
) -> Any:
    """
    Create a new job plan.
    """
    # Check code uniqueness
    result = await db.execute(
        select(JobPlan)
        .where(JobPlan.organization_id == current_user.organization_id)
        .where(JobPlan.code == jp_data.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job plan code already exists",
        )

    # Extract tasks and parts
    tasks_data = jp_data.tasks
    parts_data = jp_data.parts
    jp_dict = jp_data.model_dump(exclude={"tasks", "parts"})

    job_plan = JobPlan(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **jp_dict,
    )

    db.add(job_plan)
    await db.flush()

    # Add tasks
    for task_data in tasks_data:
        task = JobPlanTask(
            job_plan_id=job_plan.id,
            created_by_id=current_user.id,
            **task_data.model_dump(),
        )
        db.add(task)

    # Add parts
    for part_data in parts_data:
        part = JobPlanPart(
            job_plan_id=job_plan.id,
            created_by_id=current_user.id,
            **part_data.model_dump(),
        )
        db.add(part)

    await db.commit()
    await db.refresh(job_plan)

    return job_plan


@router.get("/job-plans/{jp_id}", response_model=JobPlanDetailResponse)
async def get_job_plan(
    db: DBSession,
    current_user: CurrentUser,
    jp_id: int,
) -> Any:
    """
    Get job plan by ID with tasks and parts.
    """
    result = await db.execute(
        select(JobPlan)
        .options(
            selectinload(JobPlan.tasks),
            selectinload(JobPlan.parts),
        )
        .where(JobPlan.id == jp_id)
        .where(JobPlan.organization_id == current_user.organization_id)
    )
    job_plan = result.scalar_one_or_none()

    if not job_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job plan not found",
        )

    return job_plan


@router.put("/job-plans/{jp_id}", response_model=JobPlanResponse)
async def update_job_plan(
    db: DBSession,
    current_user: CurrentUser,
    jp_id: int,
    jp_data: JobPlanUpdate,
) -> Any:
    """
    Update job plan.
    """
    result = await db.execute(
        select(JobPlan)
        .where(JobPlan.id == jp_id)
        .where(JobPlan.organization_id == current_user.organization_id)
    )
    job_plan = result.scalar_one_or_none()

    if not job_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job plan not found",
        )

    update_data = jp_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job_plan, field, value)

    # Increment revision
    job_plan.revision += 1
    job_plan.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(job_plan)

    return job_plan
