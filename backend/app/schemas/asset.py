"""
Asset schemas including meters and specifications.
"""
from typing import Optional, List, Any
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict

from app.models.asset import AssetStatus, AssetCriticality, MeterType


class AssetSpecificationCreate(BaseModel):
    """Asset specification creation schema."""
    attribute_name: str
    attribute_value: Optional[str] = None
    attribute_type: str = "text"
    unit_of_measure: Optional[str] = None
    display_order: int = 0


class AssetSpecificationResponse(AssetSpecificationCreate):
    """Asset specification response schema."""
    id: int
    asset_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetBase(BaseModel):
    """Base asset schema."""
    asset_num: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    location_id: Optional[int] = None
    category: Optional[str] = None
    asset_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    status: AssetStatus = AssetStatus.OPERATING
    criticality: AssetCriticality = AssetCriticality.MEDIUM
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    warranty_expiry: Optional[date] = None
    residual_value: Optional[float] = None
    useful_life_years: Optional[int] = None
    depreciation_method: Optional[str] = None
    install_date: Optional[date] = None
    commissioned_date: Optional[date] = None
    barcode: Optional[str] = None
    custom_fields: Optional[dict] = None


class AssetCreate(AssetBase):
    """Asset creation schema."""
    specifications: List[AssetSpecificationCreate] = []


class AssetUpdate(BaseModel):
    """Asset update schema."""
    asset_num: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    location_id: Optional[int] = None
    category: Optional[str] = None
    asset_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[AssetStatus] = None
    criticality: Optional[AssetCriticality] = None
    is_active: Optional[bool] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    warranty_expiry: Optional[date] = None
    residual_value: Optional[float] = None
    useful_life_years: Optional[int] = None
    depreciation_method: Optional[str] = None
    install_date: Optional[date] = None
    commissioned_date: Optional[date] = None
    barcode: Optional[str] = None
    custom_fields: Optional[dict] = None


class AssetResponse(AssetBase):
    """Asset response schema."""
    id: int
    organization_id: int
    is_active: bool
    hierarchy_path: Optional[str] = None
    hierarchy_level: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetDetailResponse(AssetResponse):
    """Asset with related data."""
    specifications: List[AssetSpecificationResponse] = []
    meters: List["MeterResponse"] = []


class AssetTreeResponse(AssetResponse):
    """Asset with children for tree view."""
    children: List["AssetTreeResponse"] = []


# Meter schemas

class MeterBase(BaseModel):
    """Base meter schema."""
    name: str
    code: str
    description: Optional[str] = None
    meter_type: MeterType = MeterType.CONTINUOUS
    unit_of_measure: str
    rollover_point: Optional[float] = None
    average_units_per_day: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


class MeterCreate(MeterBase):
    """Meter creation schema."""
    asset_id: int


class MeterUpdate(BaseModel):
    """Meter update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    unit_of_measure: Optional[str] = None
    rollover_point: Optional[float] = None
    average_units_per_day: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    is_active: Optional[bool] = None


class MeterResponse(MeterBase):
    """Meter response schema."""
    id: int
    asset_id: int
    organization_id: int
    is_active: bool
    last_reading: Optional[float] = None
    last_reading_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Meter reading schemas

class MeterReadingCreate(BaseModel):
    """Meter reading creation schema."""
    meter_id: int
    reading_value: float
    reading_date: datetime
    source: str = "MANUAL"
    notes: Optional[str] = None


class MeterReadingResponse(BaseModel):
    """Meter reading response schema."""
    id: int
    meter_id: int
    reading_value: float
    reading_date: datetime
    delta: Optional[float] = None
    source: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Update forward references
AssetDetailResponse.model_rebuild()
AssetTreeResponse.model_rebuild()
