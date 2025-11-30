"""
Inventory management endpoints.
"""
from typing import Any, List
from datetime import datetime

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
)
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
)
from app.schemas.common import PaginatedResponse, MessageResponse

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
