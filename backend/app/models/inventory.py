"""
Inventory models including parts, storerooms, and purchase orders.
"""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, Float, Date, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin

if TYPE_CHECKING:
    from app.models.location import Location


class PartStatus(str, enum.Enum):
    """Part inventory status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OBSOLETE = "OBSOLETE"


class POStatus(str, enum.Enum):
    """Purchase order status."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ORDERED = "ORDERED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TransactionType(str, enum.Enum):
    """Inventory transaction types."""
    RECEIPT = "RECEIPT"  # From PO
    ISSUE = "ISSUE"  # To work order
    RETURN = "RETURN"  # Return from work order
    ADJUSTMENT = "ADJUSTMENT"  # Manual adjustment
    TRANSFER = "TRANSFER"  # Between storerooms
    CYCLE_COUNT = "CYCLE_COUNT"  # Inventory count
    SCRAP = "SCRAP"  # Write-off


class PartCategory(Base, AuditMixin, TenantMixin):
    """
    Category for organizing parts.
    """

    __tablename__ = "part_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("part_categories.id"), nullable=True
    )

    # Relationships
    parent: Mapped[Optional["PartCategory"]] = relationship(
        "PartCategory", remote_side="PartCategory.id", back_populates="children"
    )
    children: Mapped[List["PartCategory"]] = relationship("PartCategory", back_populates="parent")
    parts: Mapped[List["Part"]] = relationship("Part", back_populates="category")

    def __repr__(self) -> str:
        return f"<PartCategory(code='{self.code}', name='{self.name}')>"


class Vendor(Base, AuditMixin, TenantMixin):
    """
    Vendor/supplier for parts procurement.
    """

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Contact information
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Terms
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Net 30, etc.
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Rating
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="vendor")

    def __repr__(self) -> str:
        return f"<Vendor(code='{self.code}', name='{self.name}')>"


class Part(Base, AuditMixin, TenantMixin):
    """
    Part/inventory item master record.
    """

    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("part_categories.id"), nullable=True, index=True
    )
    part_type: Mapped[str] = mapped_column(String(50), default="STOCK", nullable=False)  # STOCK, NON_STOCK, SPECIAL

    # Unit of measure
    uom: Mapped[str] = mapped_column(String(20), default="EA", nullable=False)  # EA, BOX, CASE, etc.

    # Status
    status: Mapped[PartStatus] = mapped_column(
        SQLEnum(PartStatus), default=PartStatus.ACTIVE, nullable=False
    )

    # Manufacturer info
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manufacturer_part_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Primary vendor
    primary_vendor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vendors.id"), nullable=True
    )
    vendor_part_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Costing
    unit_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    average_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    last_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    # Identification
    barcode: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Specifications
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_uom: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dimensions: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Custom fields
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    category: Mapped[Optional["PartCategory"]] = relationship("PartCategory", back_populates="parts", foreign_keys=[category_id])
    primary_vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", foreign_keys=[primary_vendor_id])
    stock_levels: Mapped[List["StockLevel"]] = relationship(
        "StockLevel", back_populates="part", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["PartTransaction"]] = relationship(
        "PartTransaction", back_populates="part", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Part(part_number='{self.part_number}', name='{self.name}')>"


class Storeroom(Base, AuditMixin, TenantMixin):
    """
    Storeroom/warehouse where parts are stored.
    """

    __tablename__ = "storerooms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Location link
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True
    )

    # Default storeroom for organization
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    location: Mapped[Optional["Location"]] = relationship("Location", foreign_keys=[location_id])
    stock_levels: Mapped[List["StockLevel"]] = relationship(
        "StockLevel", back_populates="storeroom", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Storeroom(code='{self.code}', name='{self.name}')>"


class StockLevel(Base, AuditMixin):
    """
    Stock level of a part in a specific storeroom.
    """

    __tablename__ = "stock_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storeroom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("storerooms.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Current balance
    current_balance: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    reserved_quantity: Mapped[float] = mapped_column(Float, default=0, nullable=False)  # Reserved for WOs
    available_quantity: Mapped[float] = mapped_column(Float, default=0, nullable=False)  # current - reserved

    # Reorder settings
    reorder_point: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reorder_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # EOQ
    min_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    safety_stock: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Location within storeroom
    bin_location: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Shelf/bin location

    # Last activity
    last_receipt_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_count_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    part: Mapped["Part"] = relationship("Part", back_populates="stock_levels")
    storeroom: Mapped["Storeroom"] = relationship("Storeroom", back_populates="stock_levels")

    def __repr__(self) -> str:
        return f"<StockLevel(part_id={self.part_id}, storeroom_id={self.storeroom_id}, qty={self.current_balance})>"

    def update_available(self) -> None:
        """Update available quantity."""
        self.available_quantity = self.current_balance - self.reserved_quantity

    def needs_reorder(self) -> bool:
        """Check if reorder is needed."""
        if self.reorder_point is None:
            return False
        return self.available_quantity <= self.reorder_point


class PartTransaction(Base, AuditMixin, TenantMixin):
    """
    Inventory transaction history for parts.
    """

    __tablename__ = "part_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storeroom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("storerooms.id"), nullable=False, index=True
    )

    # Transaction details
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Balance after transaction
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Reference documents
    work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True
    )
    purchase_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=True
    )

    # For transfers
    to_storeroom_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("storerooms.id"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    part: Mapped["Part"] = relationship("Part", back_populates="transactions")
    storeroom: Mapped["Storeroom"] = relationship("Storeroom", foreign_keys=[storeroom_id])
    to_storeroom: Mapped[Optional["Storeroom"]] = relationship("Storeroom", foreign_keys=[to_storeroom_id])

    def __repr__(self) -> str:
        return f"<PartTransaction(part_id={self.part_id}, type={self.transaction_type}, qty={self.quantity})>"


class PurchaseOrder(Base, AuditMixin, TenantMixin):
    """
    Purchase order for parts procurement.
    """

    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Vendor
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendors.id"), nullable=False, index=True
    )

    # Status
    status: Mapped[POStatus] = mapped_column(
        SQLEnum(POStatus), default=POStatus.DRAFT, nullable=False
    )

    # Dates
    order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    received_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Delivery
    ship_to_storeroom_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("storerooms.id"), nullable=True
    )
    shipping_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Totals
    subtotal: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    tax: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Payment
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Approval
    approved_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reference
    requisition_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="purchase_orders", foreign_keys=[vendor_id])
    ship_to_storeroom: Mapped[Optional["Storeroom"]] = relationship("Storeroom", foreign_keys=[ship_to_storeroom_id])
    lines: Mapped[List["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder(po_number='{self.po_number}', status={self.status})>"

    def calculate_totals(self) -> None:
        """Recalculate PO totals from lines."""
        self.subtotal = sum(line.total_cost for line in self.lines)
        self.total = self.subtotal + self.tax + self.shipping_cost


class PurchaseOrderLine(Base, AuditMixin):
    """
    Line item on a purchase order.
    """

    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Part
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parts.id"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quantities
    quantity_ordered: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_received: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    # Pricing
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Storeroom for this line (override PO default)
    storeroom_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("storerooms.id"), nullable=True
    )

    # Status
    is_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    received_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")
    part: Mapped["Part"] = relationship("Part", foreign_keys=[part_id])
    storeroom: Mapped[Optional["Storeroom"]] = relationship("Storeroom", foreign_keys=[storeroom_id])

    def __repr__(self) -> str:
        return f"<PurchaseOrderLine(po_id={self.purchase_order_id}, line={self.line_number})>"


# Import for type hints
from app.models.location import Location
