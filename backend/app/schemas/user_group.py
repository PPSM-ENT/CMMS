from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserGroupMemberCreate(BaseModel):
    """User group member creation schema."""
    user_id: int
    role: Optional[str] = None
    sequence: Optional[int] = 0


class UserGroupMemberResponse(BaseModel):
    """User group member response schema."""
    id: int
    user_id: int
    role: Optional[str] = None
    sequence: int
    user_name: str
    user_email: str

    model_config = ConfigDict(from_attributes=True)


class UserGroupCreate(BaseModel):
    """User group creation schema."""
    name: str
    description: Optional[str] = None
    members: List[UserGroupMemberCreate] = []


class UserGroupUpdate(BaseModel):
    """User group update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UserGroupResponse(BaseModel):
    """User group response schema."""
    id: int
    organization_id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserGroupDetailResponse(UserGroupResponse):
    """User group with members."""
    members: List[UserGroupMemberResponse] = []