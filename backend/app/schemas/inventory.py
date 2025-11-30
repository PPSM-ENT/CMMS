"""
Inventory schemas for parts, vendors, storerooms, and purchase orders.
"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict

from app.models.inventory import PartStatus, POStatus


class PartCategoryCreate(BaseModel):
    """Part category creation schema."""
    name: str
    code: str
    description: Optional[str] = None
    parent_id: Optional[int] = None


class PartCategoryResponse(BaseModel):
    """Part category response schema."""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorBase(BaseModel):
    """Base vendor schema."""
    code: str
    name: str
    description: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: Optional[int] = None
    currency: str = "USD"
    rating: Optional[int] = None


class VendorCreate(VendorBase):
    """Vendor creation schema."""
    pass


class VendorUpdate(BaseModel):
    """Vendor update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: Optional[int] = None
    currency: Optional[str] = None
    rating: Optional[int] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None


class VendorResponse(VendorBase):
    """Vendor response schema."""
    id: int
    organization_id: int
    is_active: bool
    is_approved: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreroomBase(BaseModel):
    """Base storeroom schema."""
    code: str
    name: str
    description: Optional[str] = None
    location_id: Optional[int] = None
    is_default: bool = False


class StoreroomCreate(StoreroomBase):
    """Storeroom creation schema."""
    pass


class StoreroomUpdate(BaseModel):
    """Storeroom update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class StoreroomResponse(StoreroomBase):
    """Storeroom response schema."""
    id: int
    organization_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockLevelResponse(BaseModel):
    """Stock level response schema."""
    id: int
    part_id: int
    storeroom_id: int
    current_balance: float
    reserved_quantity: float
    available_quantity: float
    reorder_point: Optional[float] = None
    reorder_quantity: Optional[float] = None
    min_level: Optional[float] = None
    max_level: Optional[float] = None
    safety_stock: Optional[float] = None
    bin_location: Optional[str] = None
    last_receipt_date: Optional[datetime] = None
    last_issue_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockLevelUpdate(BaseModel):
    """Stock level update schema."""
    reorder_point: Optional[float] = None
    reorder_quantity: Optional[float] = None
    min_level: Optional[float] = None
    max_level: Optional[float] = None
    safety_stock: Optional[float] = None
    bin_location: Optional[str] = None


class PartBase(BaseModel):
    """Base part schema."""
    part_number: str
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    part_type: str = "STOCK"
    uom: str = "EA"
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    primary_vendor_id: Optional[int] = None
    vendor_part_number: Optional[str] = None
    unit_cost: float = 0
    barcode: Optional[str] = None
    weight: Optional[float] = None
    weight_uom: Optional[str] = None
    dimensions: Optional[str] = None
    custom_fields: Optional[dict] = None


class PartCreate(PartBase):
    """Part creation schema."""
    initial_stock: Optional[List[dict]] = None  # [{storeroom_id, quantity, bin_location}]


class PartUpdate(BaseModel):
    """Part update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    part_type: Optional[str] = None
    uom: Optional[str] = None
    status: Optional[PartStatus] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    primary_vendor_id: Optional[int] = None
    vendor_part_number: Optional[str] = None
    unit_cost: Optional[float] = None
    barcode: Optional[str] = None
    weight: Optional[float] = None
    weight_uom: Optional[str] = None
    dimensions: Optional[str] = None
    custom_fields: Optional[dict] = None


class PartResponse(PartBase):
    """Part response schema."""
    id: int
    organization_id: int
    status: PartStatus
    average_cost: float
    last_cost: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartDetailResponse(PartResponse):
    """Part with stock levels."""
    stock_levels: List[StockLevelResponse] = []
    total_on_hand: float = 0
    total_available: float = 0


class PurchaseOrderLineCreate(BaseModel):
    """Purchase order line creation schema."""
    line_number: int
    part_id: int
    description: Optional[str] = None
    quantity_ordered: float
    unit_cost: float
    storeroom_id: Optional[int] = None
    notes: Optional[str] = None


class PurchaseOrderLineResponse(BaseModel):
    """Purchase order line response schema."""
    id: int
    purchase_order_id: int
    line_number: int
    part_id: int
    description: Optional[str] = None
    quantity_ordered: float
    quantity_received: float
    unit_cost: float
    total_cost: float
    storeroom_id: Optional[int] = None
    is_received: bool
    received_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderBase(BaseModel):
    """Base purchase order schema."""
    description: Optional[str] = None
    vendor_id: int
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    ship_to_storeroom_id: Optional[int] = None
    shipping_method: Optional[str] = None
    tax: float = 0
    shipping_cost: float = 0
    currency: str = "USD"
    payment_terms: Optional[str] = None
    requisition_number: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Purchase order creation schema."""
    lines: List[PurchaseOrderLineCreate] = []


class PurchaseOrderUpdate(BaseModel):
    """Purchase order update schema."""
    description: Optional[str] = None
    vendor_id: Optional[int] = None
    status: Optional[POStatus] = None
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    ship_to_storeroom_id: Optional[int] = None
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    tax: Optional[float] = None
    shipping_cost: Optional[float] = None
    currency: Optional[str] = None
    payment_terms: Optional[str] = None
    requisition_number: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(PurchaseOrderBase):
    """Purchase order response schema."""
    id: int
    po_number: str
    organization_id: int
    status: POStatus
    received_date: Optional[date] = None
    tracking_number: Optional[str] = None
    subtotal: float
    total: float
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    """Purchase order with lines."""
    lines: List[PurchaseOrderLineResponse] = []


class ReceiveLineRequest(BaseModel):
    """Receive PO line schema."""
    line_id: int
    quantity_received: float
    storeroom_id: Optional[int] = None
    notes: Optional[str] = None
