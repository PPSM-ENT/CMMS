"""
Pydantic schemas for API request/response validation.
"""
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.auth import Token, TokenPayload, LoginRequest
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.schemas.user import UserCreate, UserUpdate, UserResponse, RoleResponse, PermissionResponse
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse,
    MeterCreate, MeterUpdate, MeterResponse,
    MeterReadingCreate, MeterReadingResponse,
)
from app.schemas.work_order import (
    WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse,
    WorkOrderTaskCreate, WorkOrderTaskUpdate, WorkOrderTaskResponse,
    LaborTransactionCreate, LaborTransactionResponse,
    MaterialTransactionCreate, MaterialTransactionResponse,
)
from app.schemas.preventive_maintenance import (
    PMCreate, PMUpdate, PMResponse,
    JobPlanCreate, JobPlanUpdate, JobPlanResponse,
)
from app.schemas.inventory import (
    PartCreate, PartUpdate, PartResponse,
    VendorCreate, VendorUpdate, VendorResponse,
    StoreroomCreate, StoreroomUpdate, StoreroomResponse,
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
)

__all__ = [
    "PaginatedResponse",
    "MessageResponse",
    "Token",
    "TokenPayload",
    "LoginRequest",
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationResponse",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "RoleResponse",
    "PermissionResponse",
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "AssetCreate",
    "AssetUpdate",
    "AssetResponse",
    "MeterCreate",
    "MeterUpdate",
    "MeterResponse",
    "MeterReadingCreate",
    "MeterReadingResponse",
    "WorkOrderCreate",
    "WorkOrderUpdate",
    "WorkOrderResponse",
    "WorkOrderTaskCreate",
    "WorkOrderTaskUpdate",
    "WorkOrderTaskResponse",
    "LaborTransactionCreate",
    "LaborTransactionResponse",
    "MaterialTransactionCreate",
    "MaterialTransactionResponse",
    "PMCreate",
    "PMUpdate",
    "PMResponse",
    "JobPlanCreate",
    "JobPlanUpdate",
    "JobPlanResponse",
    "PartCreate",
    "PartUpdate",
    "PartResponse",
    "VendorCreate",
    "VendorUpdate",
    "VendorResponse",
    "StoreroomCreate",
    "StoreroomUpdate",
    "StoreroomResponse",
    "PurchaseOrderCreate",
    "PurchaseOrderUpdate",
    "PurchaseOrderResponse",
]
