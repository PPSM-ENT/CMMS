"""
Asset models including specifications, meters, and documents.
"""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, Float, Date, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.location import Location


class AssetStatus(str, enum.Enum):
    """Asset operational status."""
    OPERATING = "OPERATING"
    NOT_OPERATING = "NOT_OPERATING"
    DECOMMISSIONED = "DECOMMISSIONED"
    IN_REPAIR = "IN_REPAIR"
    STANDBY = "STANDBY"


class AssetCriticality(str, enum.Enum):
    """Asset criticality for prioritization."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MeterType(str, enum.Enum):
    """Types of meters for asset monitoring."""
    CONTINUOUS = "CONTINUOUS"  # Always increasing (runtime hours, odometer)
    GAUGE = "GAUGE"  # Can go up or down (temperature, pressure)
    CHARACTERISTIC = "CHARACTERISTIC"  # Non-numeric (color, condition)


class Asset(Base, AuditMixin, TenantMixin):
    """
    Asset represents equipment, machinery, or any maintainable item.
    Supports hierarchical parent-child relationships and pre-computed ancestors.
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_num: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Hierarchy
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=True, index=True
    )
    hierarchy_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Location
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True, index=True
    )

    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    asset_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Status
    status: Mapped[AssetStatus] = mapped_column(
        SQLEnum(AssetStatus), default=AssetStatus.OPERATING, nullable=False
    )
    criticality: Mapped[AssetCriticality] = mapped_column(
        SQLEnum(AssetCriticality), default=AssetCriticality.MEDIUM, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Financial
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    warranty_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    residual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    useful_life_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    depreciation_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # straight_line, declining_balance

    # Installation
    install_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    commissioned_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Custom fields stored as JSON
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # QR/Barcode
    barcode: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="assets")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="assets")
    parent: Mapped[Optional["Asset"]] = relationship(
        "Asset", remote_side="Asset.id", back_populates="children"
    )
    children: Mapped[List["Asset"]] = relationship("Asset", back_populates="parent")
    specifications: Mapped[List["AssetSpecification"]] = relationship(
        "AssetSpecification", back_populates="asset", cascade="all, delete-orphan"
    )
    meters: Mapped[List["Meter"]] = relationship(
        "Meter", back_populates="asset", cascade="all, delete-orphan"
    )
    documents: Mapped[List["AssetDocument"]] = relationship(
        "AssetDocument", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, asset_num='{self.asset_num}', name='{self.name}')>"

    def update_hierarchy(self) -> None:
        """Update hierarchy path and level based on parent."""
        if self.parent:
            parent_path = self.parent.hierarchy_path or str(self.parent.id)
            self.hierarchy_path = f"{parent_path}/{self.id}"
            self.hierarchy_level = self.parent.hierarchy_level + 1
        else:
            self.hierarchy_path = str(self.id)
            self.hierarchy_level = 0


class AssetSpecification(Base, AuditMixin):
    """
    Custom specifications/attributes for assets.
    Uses EAV pattern for flexible attribute definition.
    """

    __tablename__ = "asset_specifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attribute_name: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attribute_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)  # text, number, date, boolean
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="specifications")

    def __repr__(self) -> str:
        return f"<AssetSpecification(asset_id={self.asset_id}, attr='{self.attribute_name}')>"


class Meter(Base, AuditMixin, TenantMixin):
    """
    Meter for tracking asset usage and triggering condition-based maintenance.
    Types: CONTINUOUS (runtime hours), GAUGE (temperature), CHARACTERISTIC (condition)
    """

    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    meter_type: Mapped[MeterType] = mapped_column(
        SQLEnum(MeterType), default=MeterType.CONTINUOUS, nullable=False
    )
    unit_of_measure: Mapped[str] = mapped_column(String(50), nullable=False)  # hours, miles, cycles

    # Current reading
    last_reading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_reading_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rollover handling for continuous meters
    rollover_point: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    average_units_per_day: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Alert thresholds
    warning_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    critical_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="meters")
    readings: Mapped[List["MeterReading"]] = relationship(
        "MeterReading", back_populates="meter", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Meter(id={self.id}, code='{self.code}', asset_id={self.asset_id})>"


class MeterReading(Base, AuditMixin):
    """
    Historical meter readings for tracking asset usage over time.
    """

    __tablename__ = "meter_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_value: Mapped[float] = mapped_column(Float, nullable=False)
    reading_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Change from previous reading
    source: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False)  # MANUAL, IOT, IMPORT
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    meter: Mapped["Meter"] = relationship("Meter", back_populates="readings")

    def __repr__(self) -> str:
        return f"<MeterReading(meter_id={self.meter_id}, value={self.reading_value})>"


class AssetDocument(Base, AuditMixin):
    """
    Documents attached to assets (manuals, drawings, photos).
    """

    __tablename__ = "asset_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MANUAL, DRAWING, PHOTO, OTHER
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="documents")

    def __repr__(self) -> str:
        return f"<AssetDocument(asset_id={self.asset_id}, name='{self.name}')>"
