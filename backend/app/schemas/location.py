"""
Location schemas.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LocationBase(BaseModel):
    """Base location schema."""
    code: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    location_type: str = "OPERATING"
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class LocationCreate(LocationBase):
    """Location creation schema."""
    pass


class LocationUpdate(BaseModel):
    """Location update schema."""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    location_type: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase):
    """Location response schema."""
    id: int
    organization_id: int
    is_active: bool
    hierarchy_path: Optional[str] = None
    hierarchy_level: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationTreeResponse(LocationResponse):
    """Location with children for tree view."""
    children: List["LocationTreeResponse"] = []


# Update forward reference
LocationTreeResponse.model_rebuild()
