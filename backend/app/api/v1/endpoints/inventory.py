"""
Inventory management endpoints.
"""
from typing import Any, List, Optional, Dict
from datetime import datetime, timedelta, date

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, Pagination
from app.models.inventory import (
    Part,
    PartCategory,
    Vendor,
    Storeroom,
    StockLevel,
    PartTransaction,
    PurchaseOrder,
    PurchaseOrderLine,
    PartStatus,
    POStatus,
    TransactionType,
    CycleCount,
    CycleCountLine,
    CycleCountPlan,
    CycleCountStatus,
)
from app.models.scheduler_control import SchedulerControl
from app.schemas.inventory import (
    PartCreate,
    PartUpdate,
    PartResponse,
    PartDetailResponse,
    PartCategoryCreate,
    PartCategoryResponse,
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    StoreroomCreate,
    StoreroomUpdate,
    StoreroomResponse,
    StockLevelResponse,
    StockLevelUpdate,
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderDetailResponse,
    ReceiveLineRequest,
    CycleCountCreate,
    CycleCountResponse,
    CycleCountDetailResponse,
    CycleCountPlanCreate,
    CycleCountPlanResponse,
    CycleCountRecordRequest,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.models.work_order import MaterialTransaction

router = APIRouter()


# Part endpoints

@router.get("/parts", response_model=PaginatedResponse[PartResponse])
async def list_parts(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    category_id: int = Query(None, description="Filter by category"),
    status: PartStatus = Query(None, description="Filter by status"),
    low_stock: bool = Query(False, description="Show only low stock parts"),
    search: str = Query(None, description="Search by part number or name"),
) -> Any:
    """
    List parts in the organization.
    """
    query = select(Part).where(Part.organization_id == current_user.organization_id)

    if category_id:
        query = query.where(Part.category_id == category_id)

    if status:
        query = query.where(Part.status == status)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Part.part_number.ilike(search_filter))
            | (Part.name.ilike(search_filter))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(Part.part_number).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    parts = result.scalars().all()

    return PaginatedResponse(
        items=parts,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/parts/low-stock", response_model=List[PartDetailResponse])
async def get_low_stock_parts(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get parts below reorder point.
    """
    result = await db.execute(
        select(Part)
        .options(selectinload(Part.stock_levels))
        .where(Part.organization_id == current_user.organization_id)
        .where(Part.status == PartStatus.ACTIVE)
    )
    parts = result.scalars().all()

    low_stock_parts = []
    for part in parts:
        for stock in part.stock_levels:
            if stock.needs_reorder():
                part_response = PartDetailResponse.model_validate(part)
                part_response.total_on_hand = sum(s.current_balance for s in part.stock_levels)
                part_response.total_available = sum(s.available_quantity for s in part.stock_levels)
                low_stock_parts.append(part_response)
                break

    return low_stock_parts


async def generate_part_number(db, org_id: int) -> str:
    """Generate next part number."""
    result = await db.execute(
        select(func.count())
        .select_from(Part)
        .where(Part.organization_id == org_id)
    )
    count = result.scalar() + 1
    return f"P-{count:06d}"


@router.post("/parts", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
async def create_part(
    db: DBSession,
    current_user: CurrentUser,
    part_data: PartCreate,
) -> Any:
    """
    Create a new part.
    """
    # Check part_number uniqueness
    result = await db.execute(
        select(Part)
        .where(Part.organization_id == current_user.organization_id)
        .where(Part.part_number == part_data.part_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part number already exists",
        )

    initial_stock = part_data.initial_stock
    part_dict = part_data.model_dump(exclude={"initial_stock"})

    part = Part(
        organization_id=current_user.organization_id,
        status=PartStatus.ACTIVE,
        average_cost=part_data.unit_cost,
        last_cost=part_data.unit_cost,
        created_by_id=current_user.id,
        **part_dict,
    )

    db.add(part)
    await db.flush()

    # Create initial stock levels if provided
    if initial_stock:
        for stock_data in initial_stock:
            stock = StockLevel(
                part_id=part.id,
                storeroom_id=stock_data["storeroom_id"],
                current_balance=stock_data.get("quantity", 0),
                available_quantity=stock_data.get("quantity", 0),
                bin_location=stock_data.get("bin_location"),
                created_by_id=current_user.id,
            )
            db.add(stock)

    await db.commit()
    await db.refresh(part)

    return part


@router.get("/parts/{part_id}", response_model=PartDetailResponse)
async def get_part(
    db: DBSession,
    current_user: CurrentUser,
    part_id: int,
) -> Any:
    """
    Get part by ID with stock levels.
    """
    result = await db.execute(
        select(Part)
        .options(selectinload(Part.stock_levels))
        .where(Part.id == part_id)
        .where(Part.organization_id == current_user.organization_id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )

    response = PartDetailResponse.model_validate(part)
    response.total_on_hand = sum(s.current_balance for s in part.stock_levels)
    response.total_available = sum(s.available_quantity for s in part.stock_levels)

    return response


@router.put("/parts/{part_id}", response_model=PartResponse)
async def update_part(
    db: DBSession,
    current_user: CurrentUser,
    part_id: int,
    part_data: PartUpdate,
) -> Any:
    """
    Update part.
    """
    result = await db.execute(
        select(Part)
        .where(Part.id == part_id)
        .where(Part.organization_id == current_user.organization_id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )

    update_data = part_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(part, field, value)

    part.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(part)

    return part


# Storeroom endpoints

@router.get("/storerooms", response_model=List[StoreroomResponse])
async def list_storerooms(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    List storerooms.
    """
    result = await db.execute(
        select(Storeroom)
        .where(Storeroom.organization_id == current_user.organization_id)
        .order_by(Storeroom.code)
    )
    storerooms = result.scalars().all()
    return storerooms


@router.post("/storerooms", response_model=StoreroomResponse, status_code=status.HTTP_201_CREATED)
async def create_storeroom(
    db: DBSession,
    current_user: CurrentUser,
    storeroom_data: StoreroomCreate,
) -> Any:
    """
    Create a new storeroom.
    """
    storeroom = Storeroom(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **storeroom_data.model_dump(),
    )

    db.add(storeroom)
    await db.commit()
    await db.refresh(storeroom)

    return storeroom


@router.get("/storerooms/{storeroom_id}/stock", response_model=List[StockLevelResponse])
async def get_storeroom_stock(
    db: DBSession,
    current_user: CurrentUser,
    storeroom_id: int,
) -> Any:
    """
    Get all stock levels in a storeroom.
    """
    # Verify storeroom access
    result = await db.execute(
        select(Storeroom)
        .where(Storeroom.id == storeroom_id)
        .where(Storeroom.organization_id == current_user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storeroom not found",
        )

    result = await db.execute(
        select(StockLevel)
        .where(StockLevel.storeroom_id == storeroom_id)
    )
    stock_levels = result.scalars().all()

    return stock_levels


@router.put("/stock/{stock_id}", response_model=StockLevelResponse)
async def update_stock_settings(
    db: DBSession,
    current_user: CurrentUser,
    stock_id: int,
    stock_data: StockLevelUpdate,
) -> Any:
    """
    Update stock level settings (reorder points, bin location).
    """
    result = await db.execute(
        select(StockLevel)
        .join(Part)
        .where(StockLevel.id == stock_id)
        .where(Part.organization_id == current_user.organization_id)
    )
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock level not found",
        )

    update_data = stock_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stock, field, value)

    stock.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(stock)

    return stock


@router.post("/stock/adjust", response_model=MessageResponse)
async def adjust_stock(
    db: DBSession,
    current_user: CurrentUser,
    part_id: int = Query(...),
    storeroom_id: int = Query(...),
    quantity: float = Query(...),
    reason: str = Query(None),
) -> Any:
    """
    Adjust stock quantity (inventory count, correction).
    """
    # Get or create stock level
    result = await db.execute(
        select(StockLevel)
        .join(Part)
        .where(StockLevel.part_id == part_id)
        .where(StockLevel.storeroom_id == storeroom_id)
        .where(Part.organization_id == current_user.organization_id)
    )
    stock = result.scalar_one_or_none()

    if not stock:
        # Create new stock level
        stock = StockLevel(
            part_id=part_id,
            storeroom_id=storeroom_id,
            current_balance=0,
            available_quantity=0,
            created_by_id=current_user.id,
        )
        db.add(stock)
        await db.flush()

    # Get part for cost
    result = await db.execute(
        select(Part).where(Part.id == part_id)
    )
    part = result.scalar_one()

    old_balance = stock.current_balance
    adjustment = quantity - old_balance

    # Record transaction
    transaction = PartTransaction(
        organization_id=current_user.organization_id,
        part_id=part_id,
        storeroom_id=storeroom_id,
        transaction_type=TransactionType.ADJUSTMENT,
        quantity=adjustment,
        unit_cost=part.average_cost,
        total_cost=abs(adjustment) * part.average_cost,
        balance_after=quantity,
        notes=reason,
        created_by_id=current_user.id,
    )
    db.add(transaction)

    # Update stock
    stock.current_balance = quantity
    stock.update_available()
    stock.last_count_date = datetime.utcnow()

    await db.commit()

    return MessageResponse(
        message=f"Stock adjusted from {old_balance} to {quantity}",
        data={"adjustment": adjustment, "new_balance": quantity}
    )


def _cycle_count_payload(
    cycle_count: CycleCount,
    storeroom_lookup: Optional[Dict[int, Dict[str, str]]] = None,
    include_lines: bool = False,
) -> dict[str, Any]:
    """Build a serializable payload for cycle count responses."""
    storeroom_info = storeroom_lookup.get(cycle_count.storeroom_id) if storeroom_lookup else {}
    base_payload = {
        "id": cycle_count.id,
        "name": cycle_count.name,
        "description": cycle_count.description,
        "status": cycle_count.status,
        "storeroom_id": cycle_count.storeroom_id,
        "storeroom_name": storeroom_info.get("name") if storeroom_info else None,
        "storeroom_code": storeroom_info.get("code") if storeroom_info else None,
        "scheduled_date": cycle_count.scheduled_date,
        "started_at": cycle_count.started_at,
        "completed_at": cycle_count.completed_at,
        "bin_prefix": cycle_count.bin_prefix,
        "category_ids": cycle_count.category_ids,
        "part_type_filter": cycle_count.part_type_filter,
        "used_in_last_days": cycle_count.used_in_last_days,
        "usage_start_date": cycle_count.usage_start_date,
    "usage_end_date": cycle_count.usage_end_date,
    "include_zero_movement": cycle_count.include_zero_movement,
    "transacted_only": cycle_count.transacted_only,
    "line_limit": cycle_count.line_limit,
    "total_lines": cycle_count.total_lines,
    "total_variance": cycle_count.total_variance,
        "created_at": cycle_count.created_at,
        "updated_at": cycle_count.updated_at,
    }
    if include_lines:
        base_payload["lines"] = cycle_count.lines
    return base_payload


@router.get("/cycle-counts", response_model=PaginatedResponse[CycleCountResponse])
async def list_cycle_counts(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    status: CycleCountStatus = Query(None, description="Filter by status"),
    storeroom_id: int = Query(None, description="Filter by storeroom"),
    scheduled_from: date = Query(None, description="Scheduled date from"),
    scheduled_to: date = Query(None, description="Scheduled date to"),
) -> Any:
    """
    List cycle count sessions for the organization.
    """
    query = select(CycleCount).where(CycleCount.organization_id == current_user.organization_id)

    if status:
        query = query.where(CycleCount.status == status)

    if storeroom_id:
        query = query.where(CycleCount.storeroom_id == storeroom_id)

    if scheduled_from:
        query = query.where(CycleCount.scheduled_date >= scheduled_from)

    if scheduled_to:
        query = query.where(CycleCount.scheduled_date <= scheduled_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(CycleCount.created_at.desc()).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    cycle_counts = result.scalars().all()

    storeroom_ids = [cc.storeroom_id for cc in cycle_counts]
    storeroom_lookup: dict[int, dict[str, str]] = {}
    if storeroom_ids:
        storeroom_rows = await db.execute(
            select(Storeroom.id, Storeroom.code, Storeroom.name).where(Storeroom.id.in_(storeroom_ids))
        )
        storeroom_lookup = {row.id: {"code": row.code, "name": row.name} for row in storeroom_rows}

    items = [
        CycleCountResponse(**_cycle_count_payload(cc, storeroom_lookup))
        for cc in cycle_counts
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("/cycle-counts", response_model=CycleCountDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_cycle_count(
    db: DBSession,
    current_user: CurrentUser,
    count_data: CycleCountCreate,
) -> Any:
    """
    Create a cycle count session with optional filters (bin, category, usage windows).
    """
    # Verify storeroom exists
    result = await db.execute(
        select(Storeroom)
        .where(Storeroom.id == count_data.storeroom_id)
        .where(Storeroom.organization_id == current_user.organization_id)
    )
    storeroom = result.scalar_one_or_none()
    if not storeroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storeroom not found",
        )

    # Build stock selection query
    stock_query = (
        select(StockLevel, Part)
        .join(Part, StockLevel.part_id == Part.id)
        .where(StockLevel.storeroom_id == count_data.storeroom_id)
        .where(Part.organization_id == current_user.organization_id)
    )

    if count_data.bin_prefix:
        stock_query = stock_query.where(StockLevel.bin_location.ilike(f"{count_data.bin_prefix}%"))

    if count_data.category_ids:
        stock_query = stock_query.where(Part.category_id.in_(count_data.category_ids))

    if count_data.part_type:
        stock_query = stock_query.where(Part.part_type == count_data.part_type)

    # Usage-based filtering
    if count_data.used_in_last_days or count_data.usage_start_date or count_data.usage_end_date or count_data.transacted_only:
        usage_query = select(MaterialTransaction.part_id).where(
            MaterialTransaction.organization_id == current_user.organization_id
        )
        if count_data.storeroom_id:
            usage_query = usage_query.where(MaterialTransaction.storeroom_id == count_data.storeroom_id)
        if count_data.used_in_last_days:
            start_dt = datetime.utcnow() - timedelta(days=count_data.used_in_last_days)
            usage_query = usage_query.where(MaterialTransaction.created_at >= start_dt)
        if count_data.usage_start_date:
            usage_query = usage_query.where(func.date(MaterialTransaction.created_at) >= count_data.usage_start_date)
        if count_data.usage_end_date:
            usage_query = usage_query.where(func.date(MaterialTransaction.created_at) <= count_data.usage_end_date)
        if count_data.transacted_only:
            usage_query = usage_query.where(MaterialTransaction.transaction_type == "ISSUE")

        usage_query = usage_query.distinct()
        stock_query = stock_query.where(StockLevel.part_id.in_(usage_query))
    elif not count_data.include_zero_movement:
        stock_query = stock_query.where(
            (StockLevel.last_issue_date.isnot(None)) | (StockLevel.last_receipt_date.isnot(None))
        )

    if count_data.line_limit:
        stock_query = stock_query.limit(count_data.line_limit)

    result = await db.execute(stock_query)
    stock_rows = result.all()

    if not stock_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stock levels matched the selection criteria",
        )

    count_name = count_data.name or f"Cycle Count - {storeroom.code} - {datetime.utcnow().date().isoformat()}"

    cycle_count = CycleCount(
        organization_id=current_user.organization_id,
        name=count_name,
        description=count_data.description,
        status=CycleCountStatus.PLANNED,
        storeroom_id=count_data.storeroom_id,
        scheduled_date=count_data.scheduled_date,
        bin_prefix=count_data.bin_prefix,
        category_ids=count_data.category_ids,
        part_type_filter=count_data.part_type,
        used_in_last_days=count_data.used_in_last_days,
        usage_start_date=count_data.usage_start_date,
        usage_end_date=count_data.usage_end_date,
        include_zero_movement=count_data.include_zero_movement,
        transacted_only=count_data.transacted_only,
        line_limit=count_data.line_limit,
        total_lines=len(stock_rows),
        created_by_id=current_user.id,
    )

    db.add(cycle_count)
    await db.flush()

    for stock, part in stock_rows:
        line = CycleCountLine(
            organization_id=current_user.organization_id,
            cycle_count_id=cycle_count.id,
            part_id=part.id,
            stock_level_id=stock.id,
            expected_quantity=stock.current_balance,
            bin_location=stock.bin_location,
            needs_recount=False,
            part_number=part.part_number,
            part_name=part.name,
            part_type=part.part_type,
            part_category_id=part.category_id,
            last_issue_date=stock.last_issue_date,
            last_receipt_date=stock.last_receipt_date,
            created_by_id=current_user.id,
        )
        db.add(line)

    await db.commit()
    await db.refresh(cycle_count)
    await db.refresh(storeroom)

    # Reload with lines for response
    result = await db.execute(
        select(CycleCount)
        .options(selectinload(CycleCount.lines))
        .where(CycleCount.id == cycle_count.id)
    )
    cycle_count = result.scalar_one()

    payload = _cycle_count_payload(
        cycle_count,
        {storeroom.id: {"code": storeroom.code, "name": storeroom.name}},
        include_lines=True,
    )
    return CycleCountDetailResponse(**payload)


# Cycle count control endpoints (must be defined before parameterized routes)
@router.post("/cycle-counts/pause", response_model=MessageResponse)
async def pause_cycle_counts(
    db: DBSession,
    current_user: CurrentUser,
    paused: bool = Query(True, description="Pause or resume all scheduled cycle counts"),
) -> Any:
    """
    Pause or resume scheduled cycle count generation for this organization.
    """
    control = await _get_or_create_scheduler_control(db, current_user.organization_id)
    control.pause_cycle_counts = paused
    await db.commit()
    return MessageResponse(message="Cycle counts paused" if paused else "Cycle counts resumed")


@router.get("/cycle-counts/status", response_model=dict)
async def get_cycle_count_scheduler_status(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    Get pause status for cycle count scheduler.
    """
    result = await db.execute(
        select(SchedulerControl).where(SchedulerControl.organization_id == current_user.organization_id)
    )
    control = result.scalar_one_or_none()
    return {"pause_cycle_counts": bool(control.pause_cycle_counts) if control else False}


@router.get("/cycle-counts/{cycle_count_id}", response_model=CycleCountDetailResponse)
async def get_cycle_count(
    db: DBSession,
    current_user: CurrentUser,
    cycle_count_id: int,
) -> Any:
    """
    Get a cycle count with line items.
    """
    result = await db.execute(
        select(CycleCount)
        .options(selectinload(CycleCount.lines))
        .where(CycleCount.id == cycle_count_id)
        .where(CycleCount.organization_id == current_user.organization_id)
    )
    cycle_count = result.scalar_one_or_none()

    if not cycle_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cycle count not found",
        )

    storeroom_info = await db.execute(
        select(Storeroom.id, Storeroom.code, Storeroom.name).where(Storeroom.id == cycle_count.storeroom_id)
    )
    storeroom_row = storeroom_info.first()
    storeroom_lookup = {}
    if storeroom_row:
        storeroom_lookup = {storeroom_row.id: {"code": storeroom_row.code, "name": storeroom_row.name}}

    payload = _cycle_count_payload(cycle_count, storeroom_lookup, include_lines=True)
    return CycleCountDetailResponse(**payload)


@router.post("/cycle-counts/{cycle_count_id}/record", response_model=CycleCountDetailResponse)
async def record_cycle_count(
    db: DBSession,
    current_user: CurrentUser,
    cycle_count_id: int,
    record_data: CycleCountRecordRequest,
) -> Any:
    """
    Record counted quantities for a cycle count and apply variances to stock.
    """
    result = await db.execute(
        select(CycleCount)
        .options(selectinload(CycleCount.lines))
        .where(CycleCount.id == cycle_count_id)
        .where(CycleCount.organization_id == current_user.organization_id)
    )
    cycle_count = result.scalar_one_or_none()

    if not cycle_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cycle count not found",
        )

    line_map = {line.id: line for line in cycle_count.lines}
    if not record_data.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No lines provided",
        )

    for entry in record_data.lines:
        line = line_map.get(entry.line_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Line {entry.line_id} not found on this cycle count",
            )

        stock_result = await db.execute(
            select(StockLevel).where(StockLevel.id == line.stock_level_id)
        )
        stock = stock_result.scalar_one_or_none()
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock level {line.stock_level_id} not found",
            )

        part_result = await db.execute(
            select(Part).where(Part.id == line.part_id)
        )
        part = part_result.scalar_one_or_none()
        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Part {line.part_id} not found",
            )

        previous_balance = stock.current_balance
        counted_quantity = entry.counted_quantity
        adjustment = counted_quantity - previous_balance

        transaction = PartTransaction(
            organization_id=current_user.organization_id,
            part_id=line.part_id,
            storeroom_id=cycle_count.storeroom_id,
            transaction_type=TransactionType.CYCLE_COUNT,
            quantity=adjustment,
            unit_cost=part.average_cost,
            total_cost=abs(adjustment) * part.average_cost,
            balance_after=counted_quantity,
            notes=entry.notes,
            created_by_id=current_user.id,
        )
        db.add(transaction)

        stock.current_balance = counted_quantity
        stock.update_available()
        stock.last_count_date = datetime.utcnow()

        line.counted_quantity = counted_quantity
        line.variance = counted_quantity - line.expected_quantity
        line.notes = entry.notes
        line.needs_recount = entry.needs_recount or False
        line.updated_by_id = current_user.id

    cycle_count.started_at = cycle_count.started_at or datetime.utcnow()

    all_counted = all(line.counted_quantity is not None for line in cycle_count.lines)
    if all_counted:
        cycle_count.status = CycleCountStatus.COMPLETED
        cycle_count.completed_at = datetime.utcnow()
    else:
        cycle_count.status = CycleCountStatus.IN_PROGRESS

    cycle_count.total_variance = sum(
        (line.counted_quantity - line.expected_quantity)
        for line in cycle_count.lines
        if line.counted_quantity is not None
    )
    cycle_count.updated_by_id = current_user.id

    await db.commit()

    # Reload with lines
    result = await db.execute(
        select(CycleCount)
        .options(selectinload(CycleCount.lines))
        .where(CycleCount.id == cycle_count.id)
    )
    cycle_count = result.scalar_one()

    storeroom_info = await db.execute(
        select(Storeroom.id, Storeroom.code, Storeroom.name).where(Storeroom.id == cycle_count.storeroom_id)
    )
    storeroom_row = storeroom_info.first()
    storeroom_lookup = {}
    if storeroom_row:
        storeroom_lookup = {storeroom_row.id: {"code": storeroom_row.code, "name": storeroom_row.name}}

    payload = _cycle_count_payload(cycle_count, storeroom_lookup, include_lines=True)
    return CycleCountDetailResponse(**payload)


# Cycle Count Plans / Scheduling

@router.get("/cycle-count-plans", response_model=List[CycleCountPlanResponse])
async def list_cycle_count_plans(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    List recurring/scheduled cycle count plans.
    """
    result = await db.execute(
        select(CycleCountPlan)
        .where(CycleCountPlan.organization_id == current_user.organization_id)
        .order_by(CycleCountPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [
        CycleCountPlanResponse.model_validate(plan)
        for plan in plans
    ]


@router.post("/cycle-count-plans", response_model=CycleCountPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_cycle_count_plan(
    db: DBSession,
    current_user: CurrentUser,
    plan_data: CycleCountPlanCreate,
) -> Any:
    """
    Create a scheduled cycle count plan (recurring).
    """
    plan = CycleCountPlan(
        organization_id=current_user.organization_id,
        name=plan_data.name,
        description=plan_data.description,
        storeroom_id=plan_data.storeroom_id,
        is_active=True,
        is_paused=False,
        frequency_value=plan_data.frequency_value,
        frequency_unit=plan_data.frequency_unit,
        next_run_date=plan_data.next_run_date or date.today(),
        bin_prefix=plan_data.bin_prefix,
        category_ids=plan_data.category_ids,
        part_type_filter=plan_data.part_type,
        used_in_last_days=plan_data.used_in_last_days,
        usage_start_date=plan_data.usage_start_date,
        usage_end_date=plan_data.usage_end_date,
        include_zero_movement=plan_data.include_zero_movement,
        transacted_only=plan_data.transacted_only,
        line_limit=plan_data.line_limit,
        template_type=plan_data.template_type,
        created_by_id=current_user.id,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return CycleCountPlanResponse.model_validate(plan)


@router.post("/cycle-count-plans/{plan_id}/pause", response_model=CycleCountPlanResponse)
async def pause_cycle_count_plan(
    db: DBSession,
    current_user: CurrentUser,
    plan_id: int,
    paused: bool = Query(True, description="Pause or resume the plan"),
) -> Any:
    """
    Pause or resume a cycle count plan.
    """
    result = await db.execute(
        select(CycleCountPlan)
        .where(CycleCountPlan.id == plan_id)
        .where(CycleCountPlan.organization_id == current_user.organization_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    plan.is_paused = paused
    plan.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(plan)
    return CycleCountPlanResponse.model_validate(plan)


async def _get_or_create_scheduler_control(db, org_id: int) -> SchedulerControl:
    result = await db.execute(
        select(SchedulerControl).where(SchedulerControl.organization_id == org_id)
    )
    control = result.scalar_one_or_none()
    if not control:
        control = SchedulerControl(organization_id=org_id)
        db.add(control)
        await db.flush()
    return control


# Vendor endpoints

@router.get("/vendors", response_model=PaginatedResponse[VendorResponse])
async def list_vendors(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    is_active: bool = Query(None),
    search: str = Query(None),
) -> Any:
    """
    List vendors.
    """
    query = select(Vendor).where(Vendor.organization_id == current_user.organization_id)

    if is_active is not None:
        query = query.where(Vendor.is_active == is_active)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Vendor.code.ilike(search_filter))
            | (Vendor.name.ilike(search_filter))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Vendor.code).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    vendors = result.scalars().all()

    return PaginatedResponse(
        items=vendors,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    db: DBSession,
    current_user: CurrentUser,
    vendor_data: VendorCreate,
) -> Any:
    """
    Create a new vendor.
    """
    vendor = Vendor(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **vendor_data.model_dump(),
    )

    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)

    return vendor


# Purchase Order endpoints

async def generate_po_number(db, org_id: int) -> str:
    """Generate next PO number."""
    result = await db.execute(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(PurchaseOrder.organization_id == org_id)
    )
    count = result.scalar() + 1
    return f"PO-{count:06d}"


@router.get("/purchase-orders", response_model=PaginatedResponse[PurchaseOrderResponse])
async def list_purchase_orders(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    status: POStatus = Query(None),
    vendor_id: int = Query(None),
    search: str = Query(None),
) -> Any:
    """
    List purchase orders.
    """
    query = select(PurchaseOrder).where(PurchaseOrder.organization_id == current_user.organization_id)

    if status:
        query = query.where(PurchaseOrder.status == status)

    if vendor_id:
        query = query.where(PurchaseOrder.vendor_id == vendor_id)

    if search:
        query = query.where(PurchaseOrder.po_number.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(PurchaseOrder.created_at.desc()).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    purchase_orders = result.scalars().all()

    return PaginatedResponse(
        items=purchase_orders,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    db: DBSession,
    current_user: CurrentUser,
    po_data: PurchaseOrderCreate,
) -> Any:
    """
    Create a new purchase order.
    """
    po_number = await generate_po_number(db, current_user.organization_id)

    lines_data = po_data.lines
    po_dict = po_data.model_dump(exclude={"lines"})

    po = PurchaseOrder(
        organization_id=current_user.organization_id,
        po_number=po_number,
        status=POStatus.DRAFT,
        created_by_id=current_user.id,
        **po_dict,
    )

    db.add(po)
    await db.flush()

    # Add lines
    subtotal = 0
    for line_data in lines_data:
        line = PurchaseOrderLine(
            purchase_order_id=po.id,
            total_cost=line_data.quantity_ordered * line_data.unit_cost,
            created_by_id=current_user.id,
            **line_data.model_dump(),
        )
        db.add(line)
        subtotal += line.total_cost

    po.subtotal = subtotal
    po.total = subtotal + po.tax + po.shipping_cost

    await db.commit()
    await db.refresh(po)

    return po


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderDetailResponse)
async def get_purchase_order(
    db: DBSession,
    current_user: CurrentUser,
    po_id: int,
) -> Any:
    """
    Get purchase order by ID with lines.
    """
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po_id)
        .where(PurchaseOrder.organization_id == current_user.organization_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found",
        )

    return po


@router.put("/purchase-orders/{po_id}/status", response_model=PurchaseOrderResponse)
async def update_po_status(
    db: DBSession,
    current_user: CurrentUser,
    po_id: int,
    new_status: POStatus = Query(...),
) -> Any:
    """
    Update purchase order status.
    """
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .where(PurchaseOrder.organization_id == current_user.organization_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found",
        )

    # Handle approval
    if new_status == POStatus.APPROVED:
        po.approved_by_id = current_user.id
        po.approved_at = datetime.utcnow()

    po.status = new_status
    po.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(po)

    return po


@router.post("/purchase-orders/{po_id}/receive", response_model=MessageResponse)
async def receive_po_lines(
    db: DBSession,
    current_user: CurrentUser,
    po_id: int,
    receive_data: List[ReceiveLineRequest],
) -> Any:
    """
    Receive items from a purchase order.
    """
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po_id)
        .where(PurchaseOrder.organization_id == current_user.organization_id)
    )
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found",
        )

    if po.status not in [POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PO must be in ORDERED or PARTIALLY_RECEIVED status",
        )

    line_map = {line.id: line for line in po.lines}
    received_count = 0

    for receive in receive_data:
        line = line_map.get(receive.line_id)
        if not line:
            continue

        storeroom_id = receive.storeroom_id or line.storeroom_id or po.ship_to_storeroom_id
        if not storeroom_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No storeroom specified for line {line.line_number}",
            )

        # Update line
        line.quantity_received += receive.quantity_received
        if line.quantity_received >= line.quantity_ordered:
            line.is_received = True
            line.received_date = datetime.utcnow()

        # Update stock
        result = await db.execute(
            select(StockLevel)
            .where(StockLevel.part_id == line.part_id)
            .where(StockLevel.storeroom_id == storeroom_id)
        )
        stock = result.scalar_one_or_none()

        if not stock:
            stock = StockLevel(
                part_id=line.part_id,
                storeroom_id=storeroom_id,
                current_balance=0,
                available_quantity=0,
                created_by_id=current_user.id,
            )
            db.add(stock)
            await db.flush()

        stock.current_balance += receive.quantity_received
        stock.update_available()
        stock.last_receipt_date = datetime.utcnow()

        # Record transaction
        transaction = PartTransaction(
            organization_id=current_user.organization_id,
            part_id=line.part_id,
            storeroom_id=storeroom_id,
            transaction_type=TransactionType.RECEIPT,
            quantity=receive.quantity_received,
            unit_cost=line.unit_cost,
            total_cost=receive.quantity_received * line.unit_cost,
            balance_after=stock.current_balance,
            purchase_order_id=po.id,
            notes=receive.notes,
            created_by_id=current_user.id,
        )
        db.add(transaction)

        # Update part average cost
        result = await db.execute(select(Part).where(Part.id == line.part_id))
        part = result.scalar_one()
        part.last_cost = line.unit_cost

        received_count += 1

    # Update PO status
    all_received = all(line.is_received for line in po.lines)
    if all_received:
        po.status = POStatus.RECEIVED
        po.received_date = datetime.utcnow().date()
    else:
        po.status = POStatus.PARTIALLY_RECEIVED

    await db.commit()

    return MessageResponse(message=f"Received {received_count} line(s)")


# Part Category endpoints

@router.get("/categories", response_model=List[PartCategoryResponse])
async def list_categories(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    List part categories.
    """
    result = await db.execute(
        select(PartCategory)
        .where(PartCategory.organization_id == current_user.organization_id)
        .order_by(PartCategory.code)
    )
    categories = result.scalars().all()
    return categories


@router.post("/categories", response_model=PartCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    db: DBSession,
    current_user: CurrentUser,
    category_data: PartCategoryCreate,
) -> Any:
    """
    Create a new part category.
    """
    category = PartCategory(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **category_data.model_dump(),
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return category
