"""
User schemas.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class PermissionResponse(BaseModel):
    """Permission response schema."""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    category: str

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    """Base role schema."""
    name: str
    code: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Role creation schema."""
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    """Role update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(RoleBase):
    """Role response schema."""
    id: int
    is_system: bool
    permissions: List[PermissionResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    job_title: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str
    role_ids: List[int] = []
    hourly_rate: Optional[float] = None


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None
    hourly_rate: Optional[float] = None


class UserResponse(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    is_superuser: bool
    email_verified: bool
    last_login: Optional[datetime] = None
    hourly_rate: Optional[float] = None
    organization_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserWithRolesResponse(UserResponse):
    """User response with roles."""
    roles: List[RoleResponse] = []
