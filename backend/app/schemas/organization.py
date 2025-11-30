"""
Organization schemas.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str
    code: str
    description: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "USD"
    date_format: str = "YYYY-MM-DD"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Organization creation schema."""
    pass


class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    date_format: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
