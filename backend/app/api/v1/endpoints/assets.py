"""
Asset management endpoints.
"""
from typing import Any, List, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, Pagination
from app.models.asset import (
    Asset,
    AssetSpecification,
    Meter,
    MeterReading,
    AssetStatus,
    AssetCriticality,
)
from app.models.work_order import WorkOrder, WorkOrderStatus
from app.services.audit_service import log_create, log_update, log_delete
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetDetailResponse,
    AssetTreeResponse,
    MeterCreate,
    MeterUpdate,
    MeterResponse,
    MeterReadingCreate,
    MeterReadingResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()

ASSET_ALLOWED_OPERATORS = {"eq", "neq", "lt", "lte", "gt", "gte", "contains", "in"}
ASSET_FILTER_COLUMNS = {
    "status": Asset.status,
    "criticality": Asset.criticality,
    "category": Asset.category,
    "manufacturer": Asset.manufacturer,
    "model": Asset.model,
    "location_id": Asset.location_id,
    "asset_num": Asset.asset_num,
    "name": Asset.name,
}

ASSET_OPEN_WO_STATUSES = [
    WorkOrderStatus.DRAFT,
    WorkOrderStatus.WAITING_APPROVAL,
    WorkOrderStatus.APPROVED,
    WorkOrderStatus.SCHEDULED,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.ON_HOLD,
]


def _coerce_value(value: str):
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


def _build_asset_condition(column, operator: str, raw_value: str):
    if operator not in ASSET_ALLOWED_OPERATORS:
        return None

    if operator == "in":
        options = [
            _coerce_value(segment.strip())
            for segment in raw_value.split(",")
            if segment.strip()
        ]
        return column.in_(options) if options else None

    coerced = _coerce_value(raw_value)
    if operator == "eq":
        return column == coerced
    if operator == "neq":
        return column != coerced
    if operator in {"lt", "lte", "gt", "gte"}:
        op_map = {
            "lt": column < coerced,
            "lte": column <= coerced,
            "gt": column > coerced,
            "gte": column >= coerced,
        }
        return op_map[operator]
    if operator == "contains":
        return column.ilike(f"%{raw_value}%")
    return None


def _parse_custom_filters(raw_filters: Optional[str]) -> List[str]:
    if not raw_filters:
        return []
    return [segment.strip() for segment in raw_filters.split("|") if segment.strip()]


@router.get("", response_model=PaginatedResponse[AssetResponse])
async def list_assets(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    location_id: int = Query(None, description="Filter by location"),
    category: str = Query(None, description="Filter by category"),
    status: AssetStatus = Query(None, description="Filter by status"),
    criticality: str = Query(None, description="Filter by criticality"),
    is_active: bool = Query(None, description="Filter by active status"),
    search: str = Query(None, description="Search by asset_num, name, or serial"),
    status_in: str = Query(None, description="Comma separated list of statuses"),
    criticality_in: str = Query(None, description="Comma separated criticalities"),
    location_ids: str = Query(None, description="Comma separated location IDs"),
    created_from: date = Query(None, description="Created on/after date"),
    created_to: date = Query(None, description="Created on/before date"),
    install_from: date = Query(None, description="Install date on/after"),
    install_to: date = Query(None, description="Install date on/before"),
    warranty_before: date = Query(None, description="Warranty expiry on/before date"),
    quick_filter: str = Query(None, description="Quick preset (critical, down, warranty_90, recent)"),
    has_open_work_orders: bool = Query(False, description="Only assets with open work orders"),
    custom_filters: str = Query(None, description="Pipe separated advanced filters field:operator:value"),
) -> Any:
    """
    List assets in the organization.
    """
    query = select(Asset).where(Asset.organization_id == current_user.organization_id)

    if location_id:
        query = query.where(Asset.location_id == location_id)

    if location_ids:
        ids = [int(loc.strip()) for loc in location_ids.split(",") if loc.strip().isdigit()]
        if ids:
            query = query.where(Asset.location_id.in_(ids))

    if category:
        query = query.where(Asset.category == category)

    if status:
        query = query.where(Asset.status == status)

    if status_in:
        raw_statuses = [s.strip() for s in status_in.split(",") if s.strip()]
        statuses = []
        for raw in raw_statuses:
            try:
                statuses.append(AssetStatus(raw))
            except ValueError:
                continue
        if statuses:
            query = query.where(Asset.status.in_(statuses))

    if criticality:
        query = query.where(Asset.criticality == criticality)

    if criticality_in:
        raw_crit = [s.strip() for s in criticality_in.split(",") if s.strip()]
        crit_values = []
        for raw in raw_crit:
            try:
                crit_values.append(AssetCriticality(raw))
            except ValueError:
                continue
        if crit_values:
            query = query.where(Asset.criticality.in_(crit_values))

    if is_active is not None:
        query = query.where(Asset.is_active == is_active)

    if created_from:
        query = query.where(func.date(Asset.created_at) >= created_from)
    if created_to:
        query = query.where(func.date(Asset.created_at) <= created_to)
    if install_from:
        query = query.where(Asset.install_date >= install_from)
    if install_to:
        query = query.where(Asset.install_date <= install_to)
    if warranty_before:
        query = query.where(Asset.warranty_expiry.isnot(None))
        query = query.where(Asset.warranty_expiry <= warranty_before)

    if quick_filter:
        quick = quick_filter.lower()
        today = date.today()
        if quick == "critical":
            query = query.where(Asset.criticality.in_([AssetCriticality.CRITICAL, AssetCriticality.HIGH]))
        elif quick == "down":
            query = query.where(Asset.status.in_([AssetStatus.NOT_OPERATING, AssetStatus.IN_REPAIR]))
        elif quick == "warranty_90":
            query = query.where(Asset.warranty_expiry.isnot(None))
            query = query.where(Asset.warranty_expiry <= today + timedelta(days=90))
        elif quick == "recent":
            query = query.where(func.date(Asset.created_at) >= today - timedelta(days=30))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Asset.asset_num.ilike(search_filter))
            | (Asset.name.ilike(search_filter))
            | (Asset.serial_number.ilike(search_filter))
        )

    joined_work_orders = False
    if has_open_work_orders:
        query = query.join(
            WorkOrder,
            (WorkOrder.asset_id == Asset.id) & (WorkOrder.status.in_(ASSET_OPEN_WO_STATUSES)),
        )
        joined_work_orders = True

    for raw_filter in _parse_custom_filters(custom_filters):
        try:
            field, operator, value = raw_filter.split(":", 2)
        except ValueError:
            continue
        column = ASSET_FILTER_COLUMNS.get(field)
        if not column:
            continue
        condition = _build_asset_condition(column, operator, value)
        if condition is not None:
            query = query.where(condition)

    if joined_work_orders:
        query = query.distinct()

    # Count total
    count_ids = query.with_only_columns(Asset.id).order_by(None)
    if joined_work_orders:
        count_ids = count_ids.distinct()
    total = await db.scalar(select(func.count()).select_from(count_ids.subquery()))

    # Get paginated results
    query = query.order_by(Asset.hierarchy_path).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    assets = result.scalars().all()

    return PaginatedResponse(
        items=assets,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/tree", response_model=List[AssetTreeResponse])
async def get_asset_tree(
    db: DBSession,
    current_user: CurrentUser,
    location_id: int = Query(None, description="Filter by location"),
) -> Any:
    """
    Get assets as a hierarchical tree.
    """
    query = (
        select(Asset)
        .where(Asset.organization_id == current_user.organization_id)
        .where(Asset.is_active == True)
    )

    if location_id:
        query = query.where(Asset.location_id == location_id)

    query = query.order_by(Asset.hierarchy_path)
    result = await db.execute(query)
    all_assets = result.scalars().all()

    # Build tree structure
    asset_map = {a.id: AssetTreeResponse.model_validate(a) for a in all_assets}

    root_assets = []
    for asset in all_assets:
        asset_response = asset_map[asset.id]
        if asset.parent_id and asset.parent_id in asset_map:
            parent = asset_map[asset.parent_id]
            parent.children.append(asset_response)
        else:
            root_assets.append(asset_response)

    return root_assets


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    db: DBSession,
    current_user: CurrentUser,
    asset_data: AssetCreate,
) -> Any:
    """
    Create a new asset.
    """
    # Check asset_num uniqueness within organization
    result = await db.execute(
        select(Asset)
        .where(Asset.organization_id == current_user.organization_id)
        .where(Asset.asset_num == asset_data.asset_num)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset number already exists",
        )

    # Extract specifications
    specs_data = asset_data.specifications
    asset_dict = asset_data.model_dump(exclude={"specifications"})

    # Validate parent if provided
    parent = None
    if asset_data.parent_id:
        result = await db.execute(
            select(Asset)
            .where(Asset.id == asset_data.parent_id)
            .where(Asset.organization_id == current_user.organization_id)
        )
        parent = result.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent asset not found",
            )

    asset = Asset(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **asset_dict,
    )

    if parent:
        asset.parent = parent
    asset.update_hierarchy()

    db.add(asset)
    await db.flush()

    # Add specifications
    for spec in specs_data:
        asset_spec = AssetSpecification(
            asset_id=asset.id,
            created_by_id=current_user.id,
            **spec.model_dump(),
        )
        db.add(asset_spec)

    # Log audit
    await log_create(
        db=db,
        entity=asset,
        entity_type="Asset",
        user=current_user,
        entity_name=f"{asset.asset_num} - {asset.name}",
        description=f"Created asset {asset.asset_num}",
    )

    await db.commit()
    await db.refresh(asset)

    return asset


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset(
    db: DBSession,
    current_user: CurrentUser,
    asset_id: int,
) -> Any:
    """
    Get asset by ID with specifications and meters.
    """
    result = await db.execute(
        select(Asset)
        .options(
            selectinload(Asset.specifications),
            selectinload(Asset.meters),
        )
        .where(Asset.id == asset_id)
        .where(Asset.organization_id == current_user.organization_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    db: DBSession,
    current_user: CurrentUser,
    asset_id: int,
    asset_data: AssetUpdate,
) -> Any:
    """
    Update asset.
    """
    result = await db.execute(
        select(Asset)
        .where(Asset.id == asset_id)
        .where(Asset.organization_id == current_user.organization_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Capture old values for audit
    old_values = {
        "name": asset.name,
        "description": asset.description,
        "status": asset.status,
        "category": asset.category,
        "criticality": asset.criticality,
        "location_id": asset.location_id,
        "parent_id": asset.parent_id,
        "is_active": asset.is_active,
        "serial_number": asset.serial_number,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "install_date": asset.install_date,
        "warranty_expiry": asset.warranty_expiry,
        "purchase_cost": asset.purchase_cost,
    }

    update_data = asset_data.model_dump(exclude_unset=True)

    # Handle parent change
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]
        if new_parent_id:
            if new_parent_id == asset_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Asset cannot be its own parent",
                )

            result = await db.execute(
                select(Asset)
                .where(Asset.id == new_parent_id)
                .where(Asset.organization_id == current_user.organization_id)
            )
            parent = result.scalar_one_or_none()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent asset not found",
                )
            asset.parent = parent
        else:
            asset.parent = None

    for field, value in update_data.items():
        if field != "parent_id":
            setattr(asset, field, value)

    asset.updated_by_id = current_user.id
    asset.update_hierarchy()

    # Log audit
    await log_update(
        db=db,
        entity=asset,
        entity_type="Asset",
        old_values=old_values,
        new_values=update_data,
        user=current_user,
        entity_name=f"{asset.asset_num} - {asset.name}",
    )

    await db.commit()
    await db.refresh(asset)

    return asset


@router.delete("/{asset_id}", response_model=MessageResponse)
async def delete_asset(
    db: DBSession,
    current_user: CurrentUser,
    asset_id: int,
) -> Any:
    """
    Deactivate asset (soft delete).
    """
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.children))
        .where(Asset.id == asset_id)
        .where(Asset.organization_id == current_user.organization_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Check for active children
    if asset.children:
        active_children = [c for c in asset.children if c.is_active]
        if active_children:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete asset with active child assets",
            )

    # Log audit before change
    await log_delete(
        db=db,
        entity_type="Asset",
        entity_id=asset.id,
        user=current_user,
        entity_name=f"{asset.asset_num} - {asset.name}",
        description=f"Deactivated asset {asset.asset_num}",
        deleted_data={
            "asset_num": asset.asset_num,
            "name": asset.name,
            "status": asset.status.value if asset.status else None,
            "category": asset.category,
        },
    )

    asset.is_active = False
    asset.status = AssetStatus.DECOMMISSIONED
    await db.commit()

    return MessageResponse(message="Asset deactivated successfully")


@router.get("/barcode/{barcode}", response_model=AssetResponse)
async def get_asset_by_barcode(
    db: DBSession,
    current_user: CurrentUser,
    barcode: str,
) -> Any:
    """
    Get asset by barcode/QR code.
    """
    result = await db.execute(
        select(Asset)
        .where(Asset.organization_id == current_user.organization_id)
        .where(Asset.barcode == barcode)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return asset


# Meter endpoints

@router.post("/meters", response_model=MeterResponse, status_code=status.HTTP_201_CREATED)
async def create_meter(
    db: DBSession,
    current_user: CurrentUser,
    meter_data: MeterCreate,
) -> Any:
    """
    Create a new meter for an asset.
    """
    # Verify asset exists and belongs to organization
    result = await db.execute(
        select(Asset)
        .where(Asset.id == meter_data.asset_id)
        .where(Asset.organization_id == current_user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset not found",
        )

    meter = Meter(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **meter_data.model_dump(),
    )

    db.add(meter)
    await db.commit()
    await db.refresh(meter)

    return meter


@router.get("/meters/{meter_id}", response_model=MeterResponse)
async def get_meter(
    db: DBSession,
    current_user: CurrentUser,
    meter_id: int,
) -> Any:
    """
    Get meter by ID.
    """
    result = await db.execute(
        select(Meter)
        .where(Meter.id == meter_id)
        .where(Meter.organization_id == current_user.organization_id)
    )
    meter = result.scalar_one_or_none()

    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )

    return meter


@router.put("/meters/{meter_id}", response_model=MeterResponse)
async def update_meter(
    db: DBSession,
    current_user: CurrentUser,
    meter_id: int,
    meter_data: MeterUpdate,
) -> Any:
    """
    Update meter.
    """
    result = await db.execute(
        select(Meter)
        .where(Meter.id == meter_id)
        .where(Meter.organization_id == current_user.organization_id)
    )
    meter = result.scalar_one_or_none()

    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )

    update_data = meter_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meter, field, value)

    meter.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(meter)

    return meter


@router.post("/meters/readings", response_model=MeterReadingResponse, status_code=status.HTTP_201_CREATED)
async def record_meter_reading(
    db: DBSession,
    current_user: CurrentUser,
    reading_data: MeterReadingCreate,
) -> Any:
    """
    Record a new meter reading.
    """
    # Get meter
    result = await db.execute(
        select(Meter)
        .where(Meter.id == reading_data.meter_id)
        .where(Meter.organization_id == current_user.organization_id)
    )
    meter = result.scalar_one_or_none()

    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )

    # Calculate delta from last reading
    delta = None
    if meter.last_reading is not None:
        delta = reading_data.reading_value - meter.last_reading
        # Handle rollover for continuous meters
        if delta < 0 and meter.rollover_point:
            delta = (meter.rollover_point - meter.last_reading) + reading_data.reading_value

    reading = MeterReading(
        meter_id=meter.id,
        reading_value=reading_data.reading_value,
        reading_date=reading_data.reading_date,
        delta=delta,
        source=reading_data.source,
        notes=reading_data.notes,
        created_by_id=current_user.id,
    )

    db.add(reading)

    # Update meter's last reading
    meter.last_reading = reading_data.reading_value
    meter.last_reading_date = reading_data.reading_date

    await db.commit()
    await db.refresh(reading)

    return reading


@router.get("/meters/{meter_id}/readings", response_model=List[MeterReadingResponse])
async def get_meter_readings(
    db: DBSession,
    current_user: CurrentUser,
    meter_id: int,
    limit: int = Query(100, le=500),
) -> Any:
    """
    Get meter reading history.
    """
    # Verify meter access
    result = await db.execute(
        select(Meter)
        .where(Meter.id == meter_id)
        .where(Meter.organization_id == current_user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )

    result = await db.execute(
        select(MeterReading)
        .where(MeterReading.meter_id == meter_id)
        .order_by(MeterReading.reading_date.desc())
        .limit(limit)
    )
    readings = result.scalars().all()

    return readings
